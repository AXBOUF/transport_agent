from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

_DB_ENV = {
    "sydneytrains": "POSTGRES_DB_SYDNEYTRAINS",
    "buses":        "POSTGRES_DB_BUSES",
    "metro":        "POSTGRES_DB_METRO",
}

DDL = """
CREATE SCHEMA IF NOT EXISTS realtime;

-- Active service alerts.
-- Pruned when active_end passes; upserted by (transport_type, entity_id).
CREATE TABLE IF NOT EXISTS realtime.rt_alerts (
    transport_type   text        NOT NULL,
    entity_id        text        NOT NULL,
    cause            text,
    effect           text,
    header_text      text,
    description_text text,
    route_ids        text[],
    agency_id        text,
    active_start     timestamptz,
    active_end       timestamptz,
    feed_ts          timestamptz NOT NULL,
    fetched_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (transport_type, entity_id)
);

-- Current vehicle positions — one row per vehicle, overwritten every 30s.
-- Pruned when a vehicle stops appearing in the feed.
CREATE TABLE IF NOT EXISTS realtime.rt_vehicle_positions (
    transport_type   text        NOT NULL,
    vehicle_id       text        NOT NULL,
    trip_id          text,
    route_id         text,
    direction_id     smallint,
    latitude         numeric,
    longitude        numeric,
    bearing          numeric,
    speed            numeric,
    stop_sequence    integer,
    current_status   text,
    stop_id          text,
    occupancy_status text,
    congestion_level text,
    feed_ts          timestamptz NOT NULL,
    fetched_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (transport_type, vehicle_id)
);

-- Current trip-level delay status — one row per trip, overwritten every 30s.
CREATE TABLE IF NOT EXISTS realtime.rt_trip_updates (
    transport_type        text        NOT NULL,
    trip_id               text        NOT NULL,
    route_id              text,
    direction_id          smallint,
    vehicle_id            text,
    schedule_relationship text,
    feed_ts               timestamptz NOT NULL,
    fetched_at            timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (transport_type, trip_id)
);

-- Per-stop arrival/departure predictions — upserted every 30s.
-- This is the data the existing SQLite parser was throwing away.
-- Joins to analysis.fact_scheduled_stop_events on (trip_id, stop_sequence).
CREATE TABLE IF NOT EXISTS realtime.rt_stop_time_updates (
    transport_type        text        NOT NULL,
    trip_id               text        NOT NULL,
    stop_sequence         integer     NOT NULL,
    stop_id               text,
    arrival_delay         integer,
    departure_delay       integer,
    arrival_time          timestamptz,
    departure_time        timestamptz,
    schedule_relationship text,
    feed_ts               timestamptz NOT NULL,
    fetched_at            timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (transport_type, trip_id, stop_sequence)
);

CREATE INDEX IF NOT EXISTS idx_rt_vp_trip
    ON realtime.rt_vehicle_positions (trip_id);

CREATE INDEX IF NOT EXISTS idx_rt_tu_route
    ON realtime.rt_trip_updates (route_id);

CREATE INDEX IF NOT EXISTS idx_rt_stu_trip
    ON realtime.rt_stop_time_updates (trip_id, stop_sequence);

CREATE INDEX IF NOT EXISTS idx_rt_alerts_end
    ON realtime.rt_alerts (active_end);

-- Rolling delay history — one row per trip per snapshot, kept for 6 hours.
-- Inserted every 5 minutes by the history snapshot job (not upserted).
CREATE TABLE IF NOT EXISTS realtime.rt_delay_history (
    recorded_at      timestamptz NOT NULL DEFAULT now(),
    transport_type   text        NOT NULL,
    trip_id          text        NOT NULL,
    route_id         text,
    delay_seconds    integer     NOT NULL,
    stop_id          text,
    stop_sequence    integer
);

CREATE INDEX IF NOT EXISTS idx_rt_dh_time
    ON realtime.rt_delay_history (recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_rt_dh_trip
    ON realtime.rt_delay_history (transport_type, trip_id, recorded_at DESC);
"""


def _connect(db_name: str) -> psycopg.Connection:
    load_dotenv(ROOT / ".env")
    return psycopg.connect(
        host=os.getenv("POSTGRES_CONN_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        user=os.getenv("POSTGRES_USERNAME"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=db_name,
    )


def init_realtime_schema(transport_type: str) -> None:
    db_name = os.getenv(_DB_ENV[transport_type], transport_type)
    print(f"Initialising realtime schema in '{db_name}'...")
    with _connect(db_name) as conn:
        conn.execute(DDL)
        conn.commit()
    print(f"  ✓ realtime schema ready in '{db_name}'")


def main() -> None:
    load_dotenv(ROOT / ".env")
    for transport_type in _DB_ENV:
        try:
            init_realtime_schema(transport_type)
        except Exception as exc:
            print(f"  ✗ {transport_type}: {exc}")


if __name__ == "__main__":
    main()
