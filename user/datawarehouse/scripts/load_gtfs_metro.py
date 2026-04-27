from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
GTFS_DIR = ROOT / "gtfs_METRO"
STAGING_SCHEMA = ROOT / "user" / "datawarehouse" / "staging" / "schema.sql"
CORE_SCHEMA = ROOT / "user" / "datawarehouse" / "core" / "schema.sql"


def db_config() -> dict[str, object]:
    load_dotenv(ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_DB"),
    }


def import_csv(conn: psycopg.Connection, table: str, file_name: str, columns: list[str]) -> None:
    path = GTFS_DIR / file_name
    if not path.exists():
        print(f"Skipping missing file: {file_name}")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [tuple(row.get(column, "") or None for column in columns) for row in reader]

    if not rows:
        print(f"No rows in {file_name}")
        return

    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    insert_sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"

    with conn.cursor() as cur:
        cur.executemany(insert_sql, rows)
    conn.commit()
    print(f"Loaded {len(rows)} rows into {table}")


def main() -> None:
    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            for schema_file in (STAGING_SCHEMA, CORE_SCHEMA):
                cur.execute(schema_file.read_text(encoding="utf-8"))
            cur.execute("TRUNCATE staging.gtfs_agency, staging.gtfs_stops, staging.gtfs_routes, staging.gtfs_trips, staging.gtfs_stop_times, staging.gtfs_calendar, staging.gtfs_calendar_dates, staging.gtfs_shapes, staging.gtfs_notes RESTART IDENTITY")
        conn.commit()

        import_csv(conn, "staging.gtfs_agency", "agency.txt", ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang", "agency_phone", "agency_fare_url", "agency_email"])
        import_csv(conn, "staging.gtfs_stops", "stops.txt", ["stop_id", "stop_code", "stop_name", "stop_desc", "stop_lat", "stop_lon", "zone_id", "stop_url", "location_type", "parent_station", "stop_timezone", "wheelchair_boarding", "platform_code"])
        import_csv(conn, "staging.gtfs_routes", "routes.txt", ["route_id", "agency_id", "route_short_name", "route_long_name", "route_desc", "route_type", "route_url", "route_color", "route_text_color"])
        import_csv(conn, "staging.gtfs_trips", "trips.txt", ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id", "block_id", "shape_id", "wheelchair_accessible", "bikes_allowed", "route_direction", "trip_note"])
        import_csv(conn, "staging.gtfs_stop_times", "stop_times.txt", ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "stop_headsign", "pickup_type", "drop_off_type", "shape_dist_traveled", "timepoint", "stop_note"])
        import_csv(conn, "staging.gtfs_calendar", "calendar.txt", ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"])
        import_csv(conn, "staging.gtfs_calendar_dates", "calendar_dates.txt", ["service_id", "date", "exception_type"])
        import_csv(conn, "staging.gtfs_shapes", "shapes.txt", ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"])
        import_csv(conn, "staging.gtfs_notes", "notes.txt", ["note_id", "note_text"])


if __name__ == "__main__":
    main()
