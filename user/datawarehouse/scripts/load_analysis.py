from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "analysis"


# ── helpers ───────────────────────────────────────────────────────────────────

def _table_exists(cur: psycopg.Cursor, schema: str, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"{schema}.{table}",))
    return cur.fetchone()[0] is not None


def db_config(db_name: str) -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host":     os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port":     int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user":     os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname":   db_name,
    }


# ── fact_scheduled_stop_events ────────────────────────────────────────────────
# Handles GTFS 36-hour times: a 25:30 departure on service_date Monday becomes
# scheduled_departure_ts = Tuesday 01:30, but service_date stays Monday.
# calendar_dates is optional — sydneytrains omits the file entirely.

def _fact_scheduled_stop_events(has_calendar_dates: bool, has_bikes_allowed: bool = True) -> str:
    if has_calendar_dates:
        exception_filter = """\
    AND NOT EXISTS (
        SELECT 1 FROM core.calendar_dates cd
        WHERE cd.service_id   = c.service_id
          AND cd.date          = gs.d::date
          AND cd.exception_type = 2
    )"""
        added_dates = """\
    UNION ALL
    SELECT service_id, date AS service_date
    FROM   core.calendar_dates
    WHERE  exception_type = 1"""
    else:
        exception_filter = ""
        added_dates = ""

    return f"""\
CREATE TABLE analysis.fact_scheduled_stop_events AS
WITH service_dates AS (
    SELECT c.service_id, gs.d::date AS service_date
    FROM core.calendar c
    CROSS JOIN LATERAL
        generate_series(c.start_date::timestamp, c.end_date::timestamp, '1 day') AS gs(d)
    WHERE (
        (EXTRACT(ISODOW FROM gs.d) = 1 AND c.monday    = 1) OR
        (EXTRACT(ISODOW FROM gs.d) = 2 AND c.tuesday   = 1) OR
        (EXTRACT(ISODOW FROM gs.d) = 3 AND c.wednesday = 1) OR
        (EXTRACT(ISODOW FROM gs.d) = 4 AND c.thursday  = 1) OR
        (EXTRACT(ISODOW FROM gs.d) = 5 AND c.friday    = 1) OR
        (EXTRACT(ISODOW FROM gs.d) = 6 AND c.saturday  = 1) OR
        (EXTRACT(ISODOW FROM gs.d) = 7 AND c.sunday    = 1)
    ){exception_filter}{added_dates}
)
SELECT
    sd.service_date,
    r.route_id,
    COALESCE(r.route_short_name, r.route_long_name, r.route_id) AS route_name,
    r.route_type,
    r.route_color,
    t.trip_id,
    t.trip_headsign,
    t.direction_id,
    t.service_id,
    t.shape_id,
    st.stop_id,
    s.stop_name,
    s.stop_lat,
    s.stop_lon,
    st.stop_sequence,
    (sd.service_date::timestamp + make_interval(
        hours := SPLIT_PART(st.arrival_time,   ':', 1)::int,
        mins  := SPLIT_PART(st.arrival_time,   ':', 2)::int,
        secs  := SPLIT_PART(st.arrival_time,   ':', 3)::int
    )) AS scheduled_arrival_ts,
    (sd.service_date::timestamp + make_interval(
        hours := SPLIT_PART(st.departure_time, ':', 1)::int,
        mins  := SPLIT_PART(st.departure_time, ':', 2)::int,
        secs  := SPLIT_PART(st.departure_time, ':', 3)::int
    )) AS scheduled_departure_ts,
    SPLIT_PART(st.departure_time, ':', 1)::int % 24 AS departure_hour,
    t.wheelchair_accessible,
    s.wheelchair_boarding,
    {'t.bikes_allowed' if has_bikes_allowed else 'NULL::smallint AS bikes_allowed'},
    st.pickup_type,
    st.drop_off_type
FROM service_dates sd
JOIN core.trips      t  ON t.service_id  = sd.service_id
JOIN core.stop_times st ON st.trip_id    = t.trip_id
JOIN core.stops      s  ON s.stop_id     = st.stop_id
JOIN core.routes     r  ON r.route_id    = t.route_id
WHERE st.arrival_time   IS NOT NULL
  AND st.departure_time IS NOT NULL
  AND st.arrival_time   ~ '^\\d+:\\d{{2}}:\\d{{2}}$'
  AND st.departure_time ~ '^\\d+:\\d{{2}}:\\d{{2}}$'
"""


# ── standard analytics tables ─────────────────────────────────────────────────

_FACT_ROUTE_FREQUENCY = """\
CREATE TABLE analysis.fact_route_frequency AS
WITH ordered_deps AS (
    SELECT
        route_id, stop_id, service_date, direction_id,
        departure_hour AS hour_of_day,
        CASE WHEN EXTRACT(ISODOW FROM service_date) IN (6, 7)
             THEN 'weekend' ELSE 'weekday' END AS day_type,
        scheduled_departure_ts,
        LAG(scheduled_departure_ts) OVER (
            PARTITION BY route_id, stop_id, service_date, direction_id
            ORDER BY scheduled_departure_ts
        ) AS prev_dep_ts
    FROM analysis.fact_scheduled_stop_events
),
headways AS (
    SELECT
        route_id, stop_id, direction_id, hour_of_day, day_type,
        EXTRACT(EPOCH FROM (scheduled_departure_ts - prev_dep_ts)) / 60.0 AS headway_minutes
    FROM ordered_deps
    WHERE prev_dep_ts IS NOT NULL
      AND scheduled_departure_ts - prev_dep_ts <  INTERVAL '3 hours'
      AND scheduled_departure_ts - prev_dep_ts >  INTERVAL '0'
)
SELECT
    route_id, stop_id, direction_id, hour_of_day, day_type,
    COUNT(*)                                                                    AS sample_count,
    ROUND(AVG(headway_minutes)::numeric, 1)                                     AS avg_headway_minutes,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY headway_minutes)::numeric, 1)
                                                                                AS median_headway_minutes,
    ROUND((60.0 / NULLIF(AVG(headway_minutes), 0))::numeric, 1)                AS services_per_hour
FROM headways
GROUP BY route_id, stop_id, direction_id, hour_of_day, day_type
"""

_FACT_TRIP_RUNTIME = """\
CREATE TABLE analysis.fact_trip_runtime AS
WITH bounds AS (
    SELECT
        trip_id, route_id, service_date, service_id, direction_id,
        COUNT(*)                    AS stop_count,
        MIN(stop_sequence)          AS first_seq,
        MAX(stop_sequence)          AS last_seq,
        MIN(scheduled_departure_ts) AS first_departure_ts,
        MAX(scheduled_arrival_ts)   AS last_arrival_ts
    FROM analysis.fact_scheduled_stop_events
    GROUP BY trip_id, route_id, service_date, service_id, direction_id
),
first_stop AS (
    SELECT DISTINCT ON (e.trip_id, e.service_date)
        e.trip_id, e.service_date, e.stop_id AS first_stop_id
    FROM analysis.fact_scheduled_stop_events e
    JOIN bounds b ON b.trip_id = e.trip_id AND b.service_date = e.service_date
    WHERE e.stop_sequence = b.first_seq
    ORDER BY e.trip_id, e.service_date
),
last_stop AS (
    SELECT DISTINCT ON (e.trip_id, e.service_date)
        e.trip_id, e.service_date, e.stop_id AS last_stop_id
    FROM analysis.fact_scheduled_stop_events e
    JOIN bounds b ON b.trip_id = e.trip_id AND b.service_date = e.service_date
    WHERE e.stop_sequence = b.last_seq
    ORDER BY e.trip_id, e.service_date
)
SELECT
    b.trip_id, b.route_id, b.service_date, b.service_id, b.direction_id,
    b.stop_count, b.first_departure_ts, b.last_arrival_ts,
    ROUND(EXTRACT(EPOCH FROM (b.last_arrival_ts - b.first_departure_ts)) / 60) AS runtime_minutes,
    f.first_stop_id,
    l.last_stop_id
FROM bounds b
JOIN first_stop f ON f.trip_id = b.trip_id AND f.service_date = b.service_date
JOIN last_stop  l ON l.trip_id = b.trip_id AND l.service_date = b.service_date
"""

# transfer_score = routes × log(avg_daily_departures)
_FACT_STOP_CONNECTIVITY = """\
CREATE TABLE analysis.fact_stop_connectivity AS
SELECT
    stop_id,
    MAX(stop_name)                                                         AS stop_name,
    MAX(stop_lat)                                                          AS stop_lat,
    MAX(stop_lon)                                                          AS stop_lon,
    COUNT(DISTINCT route_id)                                               AS route_count,
    COUNT(DISTINCT trip_id)                                                AS trip_count,
    COUNT(DISTINCT service_date)                                           AS service_days,
    COUNT(scheduled_departure_ts)                                          AS total_departures,
    COUNT(scheduled_arrival_ts)                                            AS total_arrivals,
    ROUND(
        COUNT(scheduled_departure_ts)::numeric /
        NULLIF(COUNT(DISTINCT service_date), 0), 1
    )                                                                      AS avg_daily_departures,
    ROUND(
        COUNT(DISTINCT route_id) *
        LOG(GREATEST(
            COUNT(scheduled_departure_ts)::numeric /
            NULLIF(COUNT(DISTINCT service_date), 0), 1
        )), 2
    )                                                                      AS transfer_score
FROM analysis.fact_scheduled_stop_events
GROUP BY stop_id
"""

# express_flag: stop_count < 60% of the most-stops pattern on the same route
_DIM_SERVICE_PATTERNS = """\
CREATE TABLE analysis.dim_service_patterns AS
WITH unique_stops AS (
    SELECT DISTINCT trip_id, route_id, stop_id, stop_sequence
    FROM   analysis.fact_scheduled_stop_events
),
trip_patterns AS (
    SELECT
        trip_id, route_id,
        STRING_AGG(stop_id, ',' ORDER BY stop_sequence) AS stop_pattern,
        COUNT(*)                                          AS stop_count
    FROM unique_stops
    GROUP BY trip_id, route_id
),
route_max AS (
    SELECT route_id, MAX(stop_count) AS max_stop_count
    FROM   trip_patterns GROUP BY route_id
),
patterns AS (
    SELECT
        tp.route_id, tp.stop_pattern, tp.stop_count,
        MD5(tp.route_id || '|' || tp.stop_pattern)   AS pattern_id,
        COUNT(DISTINCT tp.trip_id)                    AS trips_using_pattern,
        tp.stop_count < (rm.max_stop_count * 0.6)     AS express_flag
    FROM trip_patterns tp
    JOIN route_max rm ON rm.route_id = tp.route_id
    GROUP BY tp.route_id, tp.stop_pattern, tp.stop_count, rm.max_stop_count
)
SELECT pattern_id, route_id, stop_pattern, stop_count, express_flag, trips_using_pattern
FROM   patterns
ORDER BY route_id, trips_using_pattern DESC
"""

# Cross-route transfers at shared stops: 2–60 min window.
_FACT_TRANSFER_OPPORTUNITIES = """\
CREATE TABLE analysis.fact_transfer_opportunities AS
WITH arrivals AS (
    SELECT stop_id, trip_id, route_id, service_date, scheduled_arrival_ts
    FROM   analysis.fact_scheduled_stop_events
    WHERE  scheduled_arrival_ts IS NOT NULL
),
departures AS (
    SELECT stop_id, trip_id, route_id, service_date, scheduled_departure_ts
    FROM   analysis.fact_scheduled_stop_events
    WHERE  scheduled_departure_ts IS NOT NULL
)
SELECT
    a.service_date,
    a.stop_id,
    a.trip_id                                                        AS from_trip_id,
    a.route_id                                                       AS from_route_id,
    d.trip_id                                                        AS to_trip_id,
    d.route_id                                                       AS to_route_id,
    a.scheduled_arrival_ts                                           AS arrival_ts,
    d.scheduled_departure_ts                                         AS departure_ts,
    ROUND(EXTRACT(EPOCH FROM
        (d.scheduled_departure_ts - a.scheduled_arrival_ts)) / 60)  AS transfer_wait_minutes
FROM arrivals a
JOIN departures d
     ON  d.stop_id           = a.stop_id
     AND d.service_date      = a.service_date
     AND d.route_id         != a.route_id
     AND d.scheduled_departure_ts >= a.scheduled_arrival_ts + INTERVAL '2 minutes'
     AND d.scheduled_departure_ts <= a.scheduled_arrival_ts + INTERVAL '60 minutes'
"""

_MV_DEPARTURE_BOARD = """\
CREATE MATERIALIZED VIEW analysis.mv_live_departure_board AS
SELECT
    stop_id, stop_name, stop_lat, stop_lon,
    route_id, route_name, route_type,
    trip_id, trip_headsign, direction_id,
    service_date, scheduled_departure_ts, scheduled_arrival_ts,
    departure_hour, wheelchair_accessible
FROM analysis.fact_scheduled_stop_events
WITH DATA
"""

# ── agent serving views ───────────────────────────────────────────────────────

_VIEW_AGENT_DEPARTURES = """\
CREATE VIEW analysis.agent_station_departures AS
SELECT
    stop_id  AS station_id, stop_name AS station_name,
    route_id, route_name,
    trip_headsign AS destination,
    direction_id, service_date,
    scheduled_departure_ts AS departs_at,
    scheduled_arrival_ts   AS arrives_at,
    wheelchair_accessible, bikes_allowed, service_id
FROM analysis.fact_scheduled_stop_events
"""

_VIEW_AGENT_ROUTE_SUMMARY = """\
CREATE VIEW analysis.agent_route_summary AS
SELECT
    r.route_id,
    r.route_short_name  AS route_name,
    r.route_long_name   AS route_description,
    r.route_type, r.route_color,
    COUNT(DISTINCT t.trip_id)    AS total_trips,
    COUNT(DISTINCT t.service_id) AS service_patterns
FROM core.routes r
JOIN core.trips  t ON t.route_id = r.route_id
GROUP BY r.route_id, r.route_short_name, r.route_long_name, r.route_type, r.route_color
"""

_VIEW_AGENT_TRIP_SUMMARY = """\
CREATE VIEW analysis.agent_trip_summary AS
SELECT
    rt.trip_id, rt.route_id, rt.service_date, rt.direction_id,
    rt.stop_count AS stops,
    rt.runtime_minutes,
    rt.first_departure_ts AS departs_at,
    rt.last_arrival_ts    AS arrives_at,
    rt.first_stop_id      AS origin_stop_id,
    rt.last_stop_id       AS destination_stop_id,
    s1.stop_name          AS origin_name,
    s2.stop_name          AS destination_name
FROM analysis.fact_trip_runtime rt
LEFT JOIN core.stops s1 ON s1.stop_id = rt.first_stop_id
LEFT JOIN core.stops s2 ON s2.stop_id = rt.last_stop_id
"""

_VIEW_AGENT_STOP_FREQUENCY = """\
CREATE VIEW analysis.agent_stop_frequency AS
SELECT
    f.route_id, f.stop_id, s.stop_name,
    f.direction_id, f.hour_of_day, f.day_type,
    f.avg_headway_minutes    AS avg_headway_mins,
    f.median_headway_minutes AS median_headway_mins,
    f.services_per_hour, f.sample_count
FROM analysis.fact_route_frequency f
JOIN core.stops s ON s.stop_id = f.stop_id
"""

_VIEW_AGENT_TRANSFER_HUBS = """\
CREATE VIEW analysis.agent_transfer_hubs AS
SELECT
    stop_id, stop_name, stop_lat, stop_lon,
    route_count, trip_count, avg_daily_departures, service_days, transfer_score,
    CASE
        WHEN route_count >= 10 THEN 'major_hub'
        WHEN route_count >= 5  THEN 'interchange'
        WHEN route_count >= 2  THEN 'connecting_stop'
        ELSE                        'local_stop'
    END AS hub_classification
FROM analysis.fact_stop_connectivity
ORDER BY route_count DESC, avg_daily_departures DESC
"""

# ── Sydney Trains specific tables ─────────────────────────────────────────────
# Only built when core.occupancies / core.vehicle_categories are present.

# Occupancies carry their own calendar: start_date/end_date + weekday flags.
# exception=0 rows are regular schedule; expand them like service_dates.
# end_date NULL → cap at 90 days from start_date.
_FACT_VEHICLE_OCCUPANCY = """\
CREATE TABLE analysis.fact_vehicle_occupancy AS
WITH occ_dates AS (
    SELECT
        o.trip_id,
        o.stop_sequence,
        o.occupancy_status,
        gs.d::date AS service_date
    FROM core.occupancies o
    CROSS JOIN LATERAL generate_series(
        o.start_date::timestamp,
        COALESCE(o.end_date, o.start_date + 90)::timestamp,
        '1 day'
    ) AS gs(d)
    WHERE o.exception = 0
      AND (
          (EXTRACT(ISODOW FROM gs.d) = 1 AND o.monday    = 1) OR
          (EXTRACT(ISODOW FROM gs.d) = 2 AND o.tuesday   = 1) OR
          (EXTRACT(ISODOW FROM gs.d) = 3 AND o.wednesday = 1) OR
          (EXTRACT(ISODOW FROM gs.d) = 4 AND o.thursday  = 1) OR
          (EXTRACT(ISODOW FROM gs.d) = 5 AND o.friday    = 1) OR
          (EXTRACT(ISODOW FROM gs.d) = 6 AND o.saturday  = 1) OR
          (EXTRACT(ISODOW FROM gs.d) = 7 AND o.sunday    = 1)
      )
)
SELECT
    od.service_date,
    od.trip_id,
    od.stop_sequence,
    od.occupancy_status,
    CASE od.occupancy_status
        WHEN 0 THEN 'empty'
        WHEN 1 THEN 'many_seats'
        WHEN 2 THEN 'seats_available'
        WHEN 3 THEN 'standing_only'
        WHEN 4 THEN 'crushed_standing'
        WHEN 5 THEN 'full'
        WHEN 6 THEN 'not_accepting'
        ELSE        'unknown'
    END AS occupancy_label,
    e.stop_id,
    e.stop_name,
    e.route_id,
    e.route_name,
    e.scheduled_departure_ts,
    e.direction_id
FROM occ_dates od
JOIN analysis.fact_scheduled_stop_events e
     ON e.trip_id       = od.trip_id
    AND e.stop_sequence = od.stop_sequence
    AND e.service_date  = od.service_date
"""

# vehicle_categories + aggregate coupling/boarding info per train type
_DIM_VEHICLE_CATEGORIES = """\
CREATE TABLE analysis.dim_vehicle_categories AS
SELECT
    vc.vehicle_category_id,
    vc.vehicle_category_name,
    COUNT(DISTINCT cc.child_sequence)       AS car_count,
    COUNT(DISTINCT vb.boarding_area_id)     AS boarding_area_count
FROM core.vehicle_categories vc
LEFT JOIN core.vehicle_couplings cc ON cc.parent_id           = vc.vehicle_category_id
LEFT JOIN core.vehicle_boardings vb ON vb.vehicle_category_id = vc.vehicle_category_id
GROUP BY vc.vehicle_category_id, vc.vehicle_category_name
"""

# One row per (trip, service_date) → what train type is running
_FACT_TRIP_VEHICLE = """\
CREATE TABLE analysis.fact_trip_vehicle AS
SELECT DISTINCT
    e.trip_id,
    e.route_id,
    e.route_name,
    e.service_date,
    e.direction_id,
    t.vehicle_category_id,
    vc.vehicle_category_name
FROM analysis.fact_scheduled_stop_events e
JOIN core.trips t ON t.trip_id = e.trip_id
LEFT JOIN core.vehicle_categories vc ON vc.vehicle_category_id = t.vehicle_category_id
WHERE t.vehicle_category_id IS NOT NULL
"""

_VIEW_AGENT_OCCUPANCY = """\
CREATE VIEW analysis.agent_occupancy_advisory AS
SELECT
    service_date,
    stop_id, stop_name,
    route_id, route_name,
    trip_id,
    scheduled_departure_ts AS departs_at,
    occupancy_status,
    occupancy_label,
    direction_id
FROM analysis.fact_vehicle_occupancy
"""

_VIEW_AGENT_TRAIN_FORMATION = """\
CREATE VIEW analysis.agent_train_formation AS
SELECT
    tv.trip_id,
    tv.route_id,
    tv.route_name,
    tv.service_date,
    tv.direction_id,
    tv.vehicle_category_id,
    tv.vehicle_category_name,
    vc.car_count,
    vc.boarding_area_count
FROM analysis.fact_trip_vehicle tv
JOIN analysis.dim_vehicle_categories vc
     ON vc.vehicle_category_id = tv.vehicle_category_id
"""

# ── build plans ───────────────────────────────────────────────────────────────
# Indexes on fact_scheduled_stop_events must be created before the tables
# that join against it (transfer_opportunities, occupancy, etc.).

BASE_DDL_STEPS: list[tuple[str, str]] = [
    # fact_scheduled_stop_events is injected first in load_db() — not listed here
    ("idx: stop_id, scheduled_departure_ts",
     "CREATE INDEX ON analysis.fact_scheduled_stop_events (stop_id, scheduled_departure_ts)"),
    ("idx: stop_id, scheduled_arrival_ts",
     "CREATE INDEX ON analysis.fact_scheduled_stop_events (stop_id, scheduled_arrival_ts)"),
    ("idx: route_id, service_date",
     "CREATE INDEX ON analysis.fact_scheduled_stop_events (route_id, service_date)"),
    ("idx: trip_id, service_date",
     "CREATE INDEX ON analysis.fact_scheduled_stop_events (trip_id, service_date)"),
    ("idx: service_date",
     "CREATE INDEX ON analysis.fact_scheduled_stop_events (service_date)"),
    ("idx: stop_id, departure_hour",
     "CREATE INDEX ON analysis.fact_scheduled_stop_events (stop_id, departure_hour)"),
    ("fact_route_frequency",        _FACT_ROUTE_FREQUENCY),
    ("fact_trip_runtime",           _FACT_TRIP_RUNTIME),
    ("fact_stop_connectivity",      _FACT_STOP_CONNECTIVITY),
    ("dim_service_patterns",        _DIM_SERVICE_PATTERNS),
    ("fact_transfer_opportunities", _FACT_TRANSFER_OPPORTUNITIES),
    ("idx: transfer from_route",
     "CREATE INDEX ON analysis.fact_transfer_opportunities (from_route_id, service_date)"),
    ("idx: transfer to_route",
     "CREATE INDEX ON analysis.fact_transfer_opportunities (to_route_id, service_date)"),
    ("idx: transfer stop_date",
     "CREATE INDEX ON analysis.fact_transfer_opportunities (stop_id, service_date)"),
    ("mv_live_departure_board",     _MV_DEPARTURE_BOARD),
    ("idx: mv_live_departure_board",
     "CREATE INDEX ON analysis.mv_live_departure_board (stop_id, scheduled_departure_ts)"),
    ("view: agent_station_departures", _VIEW_AGENT_DEPARTURES),
    ("view: agent_route_summary",   _VIEW_AGENT_ROUTE_SUMMARY),
    ("view: agent_trip_summary",    _VIEW_AGENT_TRIP_SUMMARY),
    ("view: agent_stop_frequency",  _VIEW_AGENT_STOP_FREQUENCY),
    ("view: agent_transfer_hubs",   _VIEW_AGENT_TRANSFER_HUBS),
]

SYDNEYTRAINS_EXTRA_STEPS: list[tuple[str, str]] = [
    ("fact_vehicle_occupancy",         _FACT_VEHICLE_OCCUPANCY),
    ("idx: occupancy stop+date",
     "CREATE INDEX ON analysis.fact_vehicle_occupancy (stop_id, service_date)"),
    ("idx: occupancy trip+date",
     "CREATE INDEX ON analysis.fact_vehicle_occupancy (trip_id, service_date)"),
    ("dim_vehicle_categories",         _DIM_VEHICLE_CATEGORIES),
    ("fact_trip_vehicle",              _FACT_TRIP_VEHICLE),
    ("idx: trip_vehicle route+date",
     "CREATE INDEX ON analysis.fact_trip_vehicle (route_id, service_date)"),
    ("view: agent_occupancy_advisory", _VIEW_AGENT_OCCUPANCY),
    ("view: agent_train_formation",    _VIEW_AGENT_TRAIN_FORMATION),
]


# ── runner ────────────────────────────────────────────────────────────────────

def _run_steps(conn: psycopg.Connection, steps: list[tuple[str, str]]) -> None:
    for label, sql in steps:
        with conn.cursor() as cur:
            try:
                cur.execute(sql)
                conn.commit()
                print(f"  ✓ {label}")
            except Exception as exc:
                conn.rollback()
                print(f"  ✗ {label}: {exc}")


def load_db(db_name: str) -> None:
    print(f"\nBuilding analysis schema in '{db_name}'...")
    try:
        cfg = db_config(db_name)
        with psycopg.connect(**cfg) as conn:
            with conn.cursor() as cur:
                if not _table_exists(cur, "core", "stop_times"):
                    print(f"  Skipping — core.stop_times not found")
                    return

                has_calendar_dates = _table_exists(cur, "core", "calendar_dates")
                has_occupancies    = _table_exists(cur, "core", "occupancies")
                has_vehicle_cats   = _table_exists(cur, "core", "vehicle_categories")
                cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='core' AND table_name='trips' AND column_name='bikes_allowed'")
                has_bikes_allowed  = cur.fetchone() is not None

                if not has_calendar_dates:
                    print(f"  Note — core.calendar_dates absent; skipping exception handling")
                if not has_bikes_allowed:
                    print(f"  Note — core.trips.bikes_allowed absent; using NULL")

                cur.execute("DROP SCHEMA IF EXISTS analysis CASCADE")
                cur.execute("CREATE SCHEMA analysis")
                conn.commit()

            # Build fact_scheduled_stop_events first — everything depends on it
            sse_sql = _fact_scheduled_stop_events(has_calendar_dates, has_bikes_allowed)
            with conn.cursor() as cur:
                try:
                    cur.execute(sse_sql)
                    conn.commit()
                    print(f"  ✓ fact_scheduled_stop_events")
                except Exception as exc:
                    conn.rollback()
                    print(f"  ✗ fact_scheduled_stop_events: {exc}")
                    return

            _run_steps(conn, BASE_DDL_STEPS)

            if has_occupancies or has_vehicle_cats:
                print(f"  -- Sydney Trains extensions --")
                _run_steps(conn, SYDNEYTRAINS_EXTRA_STEPS)

    except psycopg.OperationalError as exc:
        print(f"  Connection failed for '{db_name}': {exc}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    db_names = [
        os.getenv("POSTGRES_DB_TRANSPORT",    "transport"),
        # os.getenv("POSTGRES_DB_METRO",        "metro"),  # already complete
        os.getenv("POSTGRES_DB_BUSES",        "buses"),
        os.getenv("POSTGRES_DB_SYDNEYTRAINS", "sydneytrains"),
    ]
    for db_name in db_names:
        load_db(db_name)
    print("\nDone — analysis layer complete")


if __name__ == "__main__":
    main()
