from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[3]
GTFS_SOURCE = "gtfs_data"

load_dotenv(ROOT / ".env")
POSTGRES_DB = os.getenv("POSTGRES_DB_TRANSPORT", "transport")

TABLES = {
    "agency":         "agency.txt",
    "stops":          "stops.txt",
    "routes":         "routes.txt",
    "trips":          "trips.txt",
    "stop_times":     "stop_times.txt",
    "calendar":       "calendar.txt",
    "calendar_dates": "calendar_dates.txt",
    "levels":         "levels.txt",
    "shapes":         "shapes.txt",
    "notes":          "notes.txt",
    "pathways":       "pathways.txt",
}

PRIMARY_KEYS = {
    "agency":         ["agency_id"],
    "stops":          ["stop_id"],
    "routes":         ["route_id"],
    "trips":          ["trip_id"],
    "calendar":       ["service_id"],
    "stop_times":     ["trip_id", "stop_sequence"],
    "shapes":         ["shape_id", "shape_pt_sequence"],
    "calendar_dates": ["service_id", "date"],
    "levels":         ["level_id"],
    "notes":          ["note_id"],
    "pathways":       ["pathway_id"],
}

RELATIONS = [
    "ALTER TABLE staging.routes        ADD CONSTRAINT fk_routes_agency          FOREIGN KEY (agency_id)      REFERENCES staging.agency(agency_id);",
    "ALTER TABLE staging.stops         ADD CONSTRAINT fk_stops_parent_station   FOREIGN KEY (parent_station) REFERENCES staging.stops(stop_id);",
    "ALTER TABLE staging.stops         ADD CONSTRAINT fk_stops_level            FOREIGN KEY (level_id)       REFERENCES staging.levels(level_id);",
    "ALTER TABLE staging.trips         ADD CONSTRAINT fk_trips_routes           FOREIGN KEY (route_id)       REFERENCES staging.routes(route_id);",
    "ALTER TABLE staging.trips         ADD CONSTRAINT fk_trips_calendar         FOREIGN KEY (service_id)     REFERENCES staging.calendar(service_id);",
    "ALTER TABLE staging.trips         ADD CONSTRAINT fk_trips_note             FOREIGN KEY (trip_note)      REFERENCES staging.notes(note_id);",
    "ALTER TABLE staging.stop_times    ADD CONSTRAINT fk_stop_times_trips       FOREIGN KEY (trip_id)        REFERENCES staging.trips(trip_id);",
    "ALTER TABLE staging.stop_times    ADD CONSTRAINT fk_stop_times_stops       FOREIGN KEY (stop_id)        REFERENCES staging.stops(stop_id);",
    "ALTER TABLE staging.stop_times    ADD CONSTRAINT fk_stop_times_note        FOREIGN KEY (stop_note)      REFERENCES staging.notes(note_id);",
    "ALTER TABLE staging.calendar_dates ADD CONSTRAINT fk_calendar_dates_cal   FOREIGN KEY (service_id)     REFERENCES staging.calendar(service_id);",
    "ALTER TABLE staging.pathways      ADD CONSTRAINT fk_pathways_from_stop     FOREIGN KEY (from_stop_id)   REFERENCES staging.stops(stop_id);",
    "ALTER TABLE staging.pathways      ADD CONSTRAINT fk_pathways_to_stop       FOREIGN KEY (to_stop_id)     REFERENCES staging.stops(stop_id);",
]


def build_db_url() -> str:
    load_dotenv(ROOT / ".env")
    host = os.getenv("POSTGRES_CONN_HOST", "localhost")
    port = os.getenv("POSTGRES_CONN_PORT", "5432")
    user = os.getenv("POSTGRES_USERNAME", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{POSTGRES_DB}"


def create_and_load_table(conn, table_name: str, file_path: Path) -> None:
    df = pd.read_csv(file_path, dtype="string")
    definitions = [f'"{col}" TEXT' for col in df.columns]
    pk_cols = PRIMARY_KEYS.get(table_name)
    if pk_cols:
        definitions.append(f"PRIMARY KEY ({', '.join(f'\"{c}\"' for c in pk_cols)})")
    conn.execute(text(f"""
        DROP TABLE IF EXISTS staging.{table_name} CASCADE;
        CREATE TABLE staging.{table_name} (
            {",\n            ".join(definitions)}
        );
    """))
    df = df.astype("string").where(pd.notna(df), None)
    df.to_sql(table_name, con=conn, schema="staging", if_exists="append", index=False)
    print(f"  Loaded {len(df):>10,} rows → staging.{table_name}")


def add_relations(conn) -> None:
    for sql in RELATIONS:
        constraint = sql.split("CONSTRAINT")[1].split("FOREIGN")[0].strip()
        try:
            with conn.begin_nested():
                conn.execute(text(sql))
        except Exception:
            print(f"  FK skipped (table missing): {constraint}")


def main() -> None:
    gtfs_dir = ROOT / "data" / GTFS_SOURCE
    print(f"Loading {GTFS_SOURCE} → {POSTGRES_DB}.staging")

    engine = create_engine(build_db_url())
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))
        for table, file_name in TABLES.items():
            source = gtfs_dir / file_name
            if not source.exists():
                print(f"  Skipping {table:<16} ({file_name} not in {GTFS_SOURCE})")
                continue
            create_and_load_table(conn, table, source)

    with engine.begin() as conn:
        add_relations(conn)

    print(f"Done — staging load complete for {POSTGRES_DB}")


if __name__ == "__main__":
    main()
