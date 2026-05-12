from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

_DB_ENV = {
    "sydneytrains": "POSTGRES_DB_SYDNEYTRAINS",
    "buses":        "POSTGRES_DB_BUSES",
    "metro":        "POSTGRES_DB_METRO",
}

# Stale threshold: records older than this get pruned after each write cycle.
# 4× the 30-second fetch interval gives a safe buffer for slow fetches.
_STALE = "2 minutes"


# ── connection ────────────────────────────────────────────────────────────────

def _connect(transport_type: str) -> psycopg.Connection:
    load_dotenv(ROOT / ".env")
    db_name = os.getenv(_DB_ENV[transport_type], transport_type)
    return psycopg.connect(
        host=os.getenv("POSTGRES_CONN_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        user=os.getenv("POSTGRES_USERNAME"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=db_name,
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _ts(unix: int | str | None) -> datetime | None:
    if not unix:
        return None
    return datetime.fromtimestamp(int(unix), tz=timezone.utc)


def _int(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# ── alerts ────────────────────────────────────────────────────────────────────

_UPSERT_ALERTS = """
INSERT INTO realtime.rt_alerts (
    transport_type, entity_id, cause, effect,
    header_text, description_text, route_ids, agency_id,
    active_start, active_end, feed_ts, fetched_at
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
ON CONFLICT (transport_type, entity_id) DO UPDATE SET
    cause            = EXCLUDED.cause,
    effect           = EXCLUDED.effect,
    header_text      = EXCLUDED.header_text,
    description_text = EXCLUDED.description_text,
    route_ids        = EXCLUDED.route_ids,
    agency_id        = EXCLUDED.agency_id,
    active_start     = EXCLUDED.active_start,
    active_end       = EXCLUDED.active_end,
    feed_ts          = EXCLUDED.feed_ts,
    fetched_at       = now()
"""


def write_alerts(data: dict, transport_type: str) -> None:
    feed_ts = _ts(data.get("header", {}).get("timestamp"))
    rows: list[tuple] = []

    for entity in data.get("entity", []):
        alert = entity.get("alert", {})
        if not alert:
            continue

        entity_id = entity.get("id", "")
        route_ids, agency_id = [], None

        for ie in alert.get("informed_entity", []):
            if "route_id" in ie:
                route_ids.append(ie["route_id"])
            if "agency_id" in ie and agency_id is None:
                agency_id = ie["agency_id"]

        active_start = active_end = None
        for period in alert.get("active_period", []):
            active_start = _ts(period.get("start"))
            active_end   = _ts(period.get("end"))
            break

        header_text = description_text = None
        for t in alert.get("header_text", {}).get("translation", []):
            header_text = t.get("text")
            break
        for t in alert.get("description_text", {}).get("translation", []):
            description_text = t.get("text")
            break

        rows.append((
            transport_type, entity_id,
            alert.get("cause"), alert.get("effect"),
            header_text, description_text,
            route_ids or None, agency_id,
            active_start, active_end, feed_ts,
        ))

    if not rows:
        return

    with _connect(transport_type) as conn:
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_ALERTS, rows)
            # prune alerts whose window has passed
            cur.execute("""
                DELETE FROM realtime.rt_alerts
                WHERE transport_type = %s
                  AND active_end IS NOT NULL
                  AND active_end < now()
            """, (transport_type,))
        conn.commit()

    print(f"[{transport_type}] alerts: {len(rows)} upserted")


# ── vehicle positions ─────────────────────────────────────────────────────────

_UPSERT_VP = """
INSERT INTO realtime.rt_vehicle_positions (
    transport_type, vehicle_id, trip_id, route_id, direction_id,
    latitude, longitude, bearing, speed, stop_sequence,
    current_status, stop_id, occupancy_status, congestion_level,
    feed_ts, fetched_at
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
ON CONFLICT (transport_type, vehicle_id) DO UPDATE SET
    trip_id          = EXCLUDED.trip_id,
    route_id         = EXCLUDED.route_id,
    direction_id     = EXCLUDED.direction_id,
    latitude         = EXCLUDED.latitude,
    longitude        = EXCLUDED.longitude,
    bearing          = EXCLUDED.bearing,
    speed            = EXCLUDED.speed,
    stop_sequence    = EXCLUDED.stop_sequence,
    current_status   = EXCLUDED.current_status,
    stop_id          = EXCLUDED.stop_id,
    occupancy_status = EXCLUDED.occupancy_status,
    congestion_level = EXCLUDED.congestion_level,
    feed_ts          = EXCLUDED.feed_ts,
    fetched_at       = now()
"""


def write_vehicle_positions(data: dict, transport_type: str) -> None:
    feed_ts = _ts(data.get("header", {}).get("timestamp"))
    rows: list[tuple] = []

    for entity in data.get("entity", []):
        vp = entity.get("vehicle", {})
        if not vp:
            continue
        vehicle_id = vp.get("vehicle", {}).get("id")
        if not vehicle_id:
            continue

        trip     = vp.get("trip", {})
        position = vp.get("position", {})

        rows.append((
            transport_type, vehicle_id,
            trip.get("trip_id"),
            trip.get("route_id"),
            _int(trip.get("direction_id")),
            position.get("latitude"),
            position.get("longitude"),
            position.get("bearing"),
            position.get("speed"),
            _int(vp.get("current_stop_sequence")),
            vp.get("current_status"),
            vp.get("stop_id"),
            vp.get("occupancy_status"),
            vp.get("congestion_level"),
            feed_ts,
        ))

    if not rows:
        return

    with _connect(transport_type) as conn:
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_VP, rows)
            # prune vehicles not seen in the latest cycle
            cur.execute("""
                DELETE FROM realtime.rt_vehicle_positions
                WHERE transport_type = %s
                  AND fetched_at < now() - %s::interval
            """, (transport_type, _STALE))
        conn.commit()

    print(f"[{transport_type}] vehicle_positions: {len(rows)} upserted")


# ── trip updates + stop_time_updates ─────────────────────────────────────────

_UPSERT_TU = """
INSERT INTO realtime.rt_trip_updates (
    transport_type, trip_id, route_id, direction_id,
    vehicle_id, schedule_relationship, feed_ts, fetched_at
) VALUES (%s,%s,%s,%s,%s,%s,%s, now())
ON CONFLICT (transport_type, trip_id) DO UPDATE SET
    route_id              = EXCLUDED.route_id,
    direction_id          = EXCLUDED.direction_id,
    vehicle_id            = EXCLUDED.vehicle_id,
    schedule_relationship = EXCLUDED.schedule_relationship,
    feed_ts               = EXCLUDED.feed_ts,
    fetched_at            = now()
"""

_UPSERT_STU = """
INSERT INTO realtime.rt_stop_time_updates (
    transport_type, trip_id, stop_sequence, stop_id,
    arrival_delay, departure_delay, arrival_time, departure_time,
    schedule_relationship, feed_ts, fetched_at
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
ON CONFLICT (transport_type, trip_id, stop_sequence) DO UPDATE SET
    stop_id               = EXCLUDED.stop_id,
    arrival_delay         = EXCLUDED.arrival_delay,
    departure_delay       = EXCLUDED.departure_delay,
    arrival_time          = EXCLUDED.arrival_time,
    departure_time        = EXCLUDED.departure_time,
    schedule_relationship = EXCLUDED.schedule_relationship,
    feed_ts               = EXCLUDED.feed_ts,
    fetched_at            = now()
"""


def write_trip_updates(data: dict, transport_type: str) -> None:
    feed_ts = _ts(data.get("header", {}).get("timestamp"))
    tu_rows:  list[tuple] = []
    stu_rows: list[tuple] = []

    for entity in data.get("entity", []):
        tu = entity.get("trip_update", {})
        if not tu:
            continue

        trip    = tu.get("trip", {})
        trip_id = trip.get("trip_id")
        if not trip_id:
            continue

        tu_rows.append((
            transport_type, trip_id,
            trip.get("route_id"),
            _int(trip.get("direction_id")),
            tu.get("vehicle", {}).get("id"),
            trip.get("schedule_relationship"),
            feed_ts,
        ))

        for pos, stu in enumerate(tu.get("stop_time_update", [])):
            # Sydney Trains omits stop_sequence — use list position as fallback
            stop_seq = _int(stu.get("stop_sequence")) if stu.get("stop_sequence") is not None else pos
            arrival   = stu.get("arrival",   {})
            departure = stu.get("departure", {})
            stu_rows.append((
                transport_type, trip_id, stop_seq,
                stu.get("stop_id"),
                _int(arrival.get("delay")),
                _int(departure.get("delay")),
                _ts(arrival.get("time")),
                _ts(departure.get("time")),
                stu.get("schedule_relationship"),
                feed_ts,
            ))

    if not tu_rows:
        return

    with _connect(transport_type) as conn:
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_TU, tu_rows)
            if stu_rows:
                cur.executemany(_UPSERT_STU, stu_rows)
            # prune trips not seen in the latest cycle
            cur.execute("""
                DELETE FROM realtime.rt_trip_updates
                WHERE transport_type = %s
                  AND fetched_at < now() - %s::interval
            """, (transport_type, _STALE))
            cur.execute("""
                DELETE FROM realtime.rt_stop_time_updates
                WHERE transport_type = %s
                  AND fetched_at < now() - %s::interval
            """, (transport_type, _STALE))
        conn.commit()

    print(f"[{transport_type}] trip_updates: {len(tu_rows)}, stop_time_updates: {len(stu_rows)}")


# ── delay history snapshot ────────────────────────────────────────────────────

_HISTORY_WINDOW = "6 hours"

_INSERT_HISTORY = """
INSERT INTO realtime.rt_delay_history
    (transport_type, trip_id, route_id, delay_seconds, stop_id, stop_sequence)
SELECT
    tu.transport_type,
    tu.trip_id,
    tu.route_id,
    COALESCE(stu.departure_delay, stu.arrival_delay) AS delay_seconds,
    stu.stop_id,
    stu.stop_sequence
FROM realtime.rt_trip_updates tu
JOIN realtime.rt_stop_time_updates stu
  ON stu.trip_id        = tu.trip_id
 AND stu.transport_type = tu.transport_type
WHERE tu.transport_type = %s
  AND COALESCE(stu.departure_delay, stu.arrival_delay) IS NOT NULL
"""

_PRUNE_HISTORY = """
DELETE FROM realtime.rt_delay_history
WHERE transport_type = %s
  AND recorded_at < now() - %s::interval
"""


def snapshot_delay_history(transport_type: str) -> None:
    """
    Called every 5 minutes by the scheduler.
    Snapshots current delay state into rt_delay_history and prunes records
    older than 6 hours.
    """
    with _connect(transport_type) as conn:
        with conn.cursor() as cur:
            cur.execute(_INSERT_HISTORY, (transport_type,))
            inserted = cur.rowcount
            cur.execute(_PRUNE_HISTORY, (transport_type, _HISTORY_WINDOW))
            pruned = cur.rowcount
        conn.commit()

    print(f"[{transport_type}] delay_history: +{inserted} rows, -{pruned} pruned")
