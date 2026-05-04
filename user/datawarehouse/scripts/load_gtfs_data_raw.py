from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[3]
GTFS_DIR = ROOT / "gtfs_data"

load_dotenv(ROOT / ".env")


def build_db_url() -> str:
    explicit_url = os.getenv("TRANSPORT_DB_URL")
    if explicit_url:
        if explicit_url.startswith("postgresql://") and "+" not in explicit_url.split("://", 1)[0]:
            return explicit_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return explicit_url

    host = os.getenv("POSTGRES_CONN_HOST", "localhost")
    port = os.getenv("POSTGRES_CONN_PORT", "5432")
    user = os.getenv("POSTGRES_USERNAME", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    db_name = os.getenv("POSTGRES_DB", "transport")

    # Use psycopg3 driver explicitly so SQLAlchemy does not depend on psycopg2.
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"

TABLES = {
    "agency": "agency.txt",
    "stops": "stops.txt",
    "routes": "routes.txt",
    "trips": "trips.txt",
    "stop_times": "stop_times.txt",
    "calendar": "calendar.txt",
    "calendar_dates": "calendar_dates.txt",
    "levels": "levels.txt",
    "shapes": "shapes.txt",
    "notes": "notes.txt",
    "pathways": "pathways.txt",
}

UNIQUE_KEYS = {
    "agency": ["agency_id"],
    "stops": ["stop_id"],
    "routes": ["route_id"],
    "trips": ["trip_id"],
    "calendar": ["service_id"],
}

# Foreign keys are added after load, mirroring the requested relationships.
RELATIONS = [
    """
    ALTER TABLE raw.routes
    ADD CONSTRAINT fk_routes_agency
    FOREIGN KEY (agency_id) REFERENCES raw.agency(agency_id);
    """,
    """
    ALTER TABLE raw.trips
    ADD CONSTRAINT fk_trips_routes
    FOREIGN KEY (route_id) REFERENCES raw.routes(route_id);
    """,
    """
    ALTER TABLE raw.stop_times
    ADD CONSTRAINT fk_stop_times_trips
    FOREIGN KEY (trip_id) REFERENCES raw.trips(trip_id);
    """,
    """
    ALTER TABLE raw.stop_times
    ADD CONSTRAINT fk_stop_times_stops
    FOREIGN KEY (stop_id) REFERENCES raw.stops(stop_id);
    """,
    """
    ALTER TABLE raw.calendar_dates
    ADD CONSTRAINT fk_calendar_dates_calendar
    FOREIGN KEY (service_id) REFERENCES raw.calendar(service_id);
    """,
]


engine = create_engine(build_db_url())


def create_table(conn, table_name: str, file_path: Path) -> None:
    df = pd.read_csv(file_path, dtype="string")

    definitions = [f'"{col}" TEXT' for col in df.columns]
    unique_columns = UNIQUE_KEYS.get(table_name)
    if unique_columns:
        constraint_columns = ", ".join(f'"{col}"' for col in unique_columns)
        definitions.append(f"UNIQUE ({constraint_columns})")

    create_sql = f"""
    DROP TABLE IF EXISTS raw.{table_name} CASCADE;
    CREATE TABLE raw.{table_name} (
        {",\n        ".join(definitions)}
    );
    """

    conn.execute(text(create_sql))

    print(f"Created table: raw.{table_name}")


def load_data(conn, table_name: str, file_path: Path) -> None:
    df = pd.read_csv(file_path, dtype="string")
    df = df.astype("string").where(pd.notna(df), None)
    df.to_sql(table_name, con=conn, schema="raw", if_exists="append", index=False)
    print(f"Loaded data: raw.{table_name} ({len(df)} rows)")


def add_relations(conn) -> None:
    for relation_sql in RELATIONS:
        try:
            with conn.begin_nested():
                conn.execute(text(relation_sql))
        except Exception as exc:
            print("FK warning:", exc)


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))

        for table, file_name in TABLES.items():
            source = GTFS_DIR / file_name
            if not source.exists():
                raise FileNotFoundError(f"Missing GTFS file: {source}")

            create_table(conn, table, source)
            load_data(conn, table, source)

    with engine.begin() as conn:
        add_relations(conn)

    print("Raw schema load complete")


if __name__ == "__main__":
    main()
