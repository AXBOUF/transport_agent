"""
Add live bridge views to each transport database.

Creates three views in the analysis schema that JOIN static timetable data
(analysis.fact_scheduled_stop_events) with live GTFS-RT tables
(realtime.rt_*). Safe to re-run — uses CREATE OR REPLACE VIEW.

Run AFTER load_analysis.py has finished for a given database.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]

_DB_ENV = {
    "sydneytrains": "POSTGRES_DB_SYDNEYTRAINS",
    "metro":        "POSTGRES_DB_METRO",
}


# ── connection ────────────────────────────────────────────────────────────────

def _connect(db_name: str) -> psycopg.Connection:
    load_dotenv(ROOT / ".env")
    return psycopg.connect(
        host=os.getenv("POSTGRES_CONN_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        user=os.getenv("POSTGRES_USERNAME"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=db_name,
    )


def _table_exists(cur: psycopg.Cursor, schema: str, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"{schema}.{table}",))
    return cur.fetchone()[0] is not None


# ── view DDL ──────────────────────────────────────────────────────────────────

# Upcoming/recent departures at each stop, enriched with realtime delay and
# vehicle position. Covers a 30-min-past to 150-min-ahead window.
_LIVE_DEPARTURES = """\
CREATE OR REPLACE VIEW analysis.live_departures AS
SELECT
    e.service_date,
    e.route_id,
    e.route_name,
    e.route_type,
    e.route_color,
    e.trip_id,
    e.trip_headsign,
    e.direction_id,
    e.stop_id,
    e.stop_name,
    e.stop_lat,
    e.stop_lon,
    e.stop_sequence,
    e.scheduled_arrival_ts,
    e.scheduled_departure_ts,
    stu.arrival_delay,
    stu.departure_delay,
    CASE
        WHEN stu.arrival_time   IS NOT NULL THEN stu.arrival_time
        WHEN stu.arrival_delay  IS NOT NULL THEN e.scheduled_arrival_ts   + make_interval(secs := stu.arrival_delay)
        ELSE e.scheduled_arrival_ts
    END AS estimated_arrival_ts,
    CASE
        WHEN stu.departure_time  IS NOT NULL THEN stu.departure_time
        WHEN stu.departure_delay IS NOT NULL THEN e.scheduled_departure_ts + make_interval(secs := stu.departure_delay)
        ELSE e.scheduled_departure_ts
    END AS estimated_departure_ts,
    stu.schedule_relationship,
    vp.vehicle_id,
    vp.current_status,
    vp.latitude   AS vehicle_lat,
    vp.longitude  AS vehicle_lon,
    vp.bearing,
    vp.speed,
    vp.occupancy_status,
    (stu.trip_id IS NOT NULL) AS has_realtime,
    stu.fetched_at            AS rt_fetched_at
FROM analysis.fact_scheduled_stop_events e
LEFT JOIN realtime.rt_stop_time_updates stu
       ON stu.trip_id       = e.trip_id
      AND stu.stop_sequence = e.stop_sequence
LEFT JOIN realtime.rt_vehicle_positions vp
       ON vp.trip_id = e.trip_id
WHERE e.scheduled_departure_ts BETWEEN now() - INTERVAL '30 minutes'
                                   AND now() + INTERVAL '150 minutes'
"""

# Active service alerts, filtered to those currently in effect (or starting
# within the next hour). No JOIN needed — alerts carry their own text.
_LIVE_ALERTS = """\
CREATE OR REPLACE VIEW analysis.live_alerts AS
SELECT
    a.entity_id,
    a.transport_type,
    a.cause,
    a.effect,
    a.header_text,
    a.description_text,
    a.route_ids,
    a.agency_id,
    a.active_start,
    a.active_end,
    a.feed_ts,
    a.fetched_at
FROM realtime.rt_alerts a
WHERE (a.active_end   IS NULL OR a.active_end   > now())
  AND (a.active_start IS NULL OR a.active_start <= now() + INTERVAL '1 hour')
"""

# All currently tracked vehicles, enriched with route and stop names.
_LIVE_VEHICLE_POSITIONS = """\
CREATE OR REPLACE VIEW analysis.live_vehicle_positions AS
SELECT
    vp.vehicle_id,
    vp.trip_id,
    vp.route_id,
    r.route_short_name,
    r.route_long_name,
    r.route_type,
    r.route_color,
    vp.direction_id,
    vp.latitude,
    vp.longitude,
    vp.bearing,
    vp.speed,
    vp.current_status,
    vp.stop_id,
    s.stop_name,
    vp.stop_sequence,
    vp.occupancy_status,
    vp.congestion_level,
    vp.feed_ts,
    vp.fetched_at
FROM realtime.rt_vehicle_positions vp
LEFT JOIN core.routes r ON r.route_id = vp.route_id
LEFT JOIN core.stops  s ON s.stop_id  = vp.stop_id
"""

# Canonical single-row-per-vehicle state — powers the map, dashboards, and AI.
_AGENT_LIVE_VEHICLE_STATE = """\
CREATE OR REPLACE VIEW analysis.agent_live_vehicle_state AS
SELECT
    vp.vehicle_id,
    vp.trip_id,
    vp.route_id,
    COALESCE(r.route_short_name, r.route_long_name, vp.route_id) AS route_name,
    r.route_color,
    r.route_type,
    vp.direction_id,
    vp.latitude,
    vp.longitude,
    vp.bearing,
    vp.speed,
    vp.current_status,
    COALESCE(stu.departure_delay, stu.arrival_delay)              AS delay_seconds,
    vp.stop_id                                                    AS next_stop_id,
    s.stop_name                                                   AS next_stop_name,
    vp.stop_sequence                                              AS next_stop_sequence,
    dest.stop_name                                                AS destination,
    vp.occupancy_status,
    vp.congestion_level,
    vp.transport_type,
    vp.feed_ts,
    vp.fetched_at                                                 AS updated_at
FROM realtime.rt_vehicle_positions vp
LEFT JOIN core.routes r
       ON r.route_id = vp.route_id
LEFT JOIN core.stops s
       ON s.stop_id = vp.stop_id
LEFT JOIN realtime.rt_stop_time_updates stu
       ON stu.trip_id       = vp.trip_id
      AND stu.stop_sequence = vp.stop_sequence
LEFT JOIN LATERAL (
    SELECT stop_name
    FROM   analysis.fact_scheduled_stop_events
    WHERE  trip_id      = vp.trip_id
      AND  service_date = CURRENT_DATE
    ORDER  BY stop_sequence DESC
    LIMIT  1
) dest ON true
WHERE vp.latitude  IS NOT NULL
  AND vp.longitude IS NOT NULL
"""

VIEWS = [
    ("live_departures",          _LIVE_DEPARTURES),
    ("live_alerts",              _LIVE_ALERTS),
    ("live_vehicle_positions",   _LIVE_VEHICLE_POSITIONS),
    ("agent_live_vehicle_state", _AGENT_LIVE_VEHICLE_STATE),
]


# ── per-database logic ────────────────────────────────────────────────────────

def add_views(transport: str, db_name: str) -> bool:
    print(f"\n── {transport} ({db_name}) ──────────────────────────")

    try:
        conn = _connect(db_name)
    except Exception as exc:
        print(f"  ✗ cannot connect: {exc}")
        return False

    with conn:
        with conn.cursor() as cur:
            if not _table_exists(cur, "analysis", "fact_scheduled_stop_events"):
                print("  ⚠  analysis.fact_scheduled_stop_events not found — skipping")
                print("     (run load_analysis.py first for this database)")
                return False

            if not _table_exists(cur, "realtime", "rt_alerts"):
                print("  ⚠  realtime.rt_alerts not found — skipping")
                print("     (run realtime/pg_schema.py first)")
                return False

            for view_name, ddl in VIEWS:
                cur.execute(ddl)
                print(f"  ✓ analysis.{view_name}")

    conn.close()
    return True


# ── main ──────────────────────────────────────────────────────────────────────

def main(targets: list[str] | None = None) -> None:
    load_dotenv(ROOT / ".env")

    dbs = {
        transport: os.getenv(env_key, transport)
        for transport, env_key in _DB_ENV.items()
    }

    if targets:
        dbs = {k: v for k, v in dbs.items() if k in targets}

    ok, skipped, failed = 0, 0, 0
    for transport, db_name in dbs.items():
        result = add_views(transport, db_name)
        if result:
            ok += 1
        else:
            skipped += 1

    print(f"\n{'─' * 52}")
    print(f"Done — {ok} updated, {skipped} skipped")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    # Optionally pass transport names as arguments: python add_live_views.py sydneytrains
    targets = sys.argv[1:] or None
    main(targets)
