from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]


def db_config() -> dict[str, object]:
    load_dotenv(ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_DB"),
    }


def main() -> None:
    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO core.stations (station_id, station_name, station_lat, station_lon, parent_station, platform_count)
                SELECT
                    s.stop_id,
                    s.stop_name,
                    s.stop_lat,
                    s.stop_lon,
                    s.parent_station,
                    COUNT(p.stop_id)::int
                FROM staging.gtfs_stops s
                LEFT JOIN staging.gtfs_stops p
                    ON p.parent_station = s.stop_id
                WHERE s.location_type = '1' OR s.parent_station = '' OR s.parent_station IS NULL
                GROUP BY s.stop_id, s.stop_name, s.stop_lat, s.stop_lon, s.parent_station
                ON CONFLICT (station_id) DO UPDATE
                SET station_name = EXCLUDED.station_name,
                    station_lat = EXCLUDED.station_lat,
                    station_lon = EXCLUDED.station_lon,
                    parent_station = EXCLUDED.parent_station,
                    platform_count = EXCLUDED.platform_count;
                """
            )

            cur.execute(
                """
                INSERT INTO core.platforms (platform_id, station_id, platform_name, platform_code, platform_lat, platform_lon, location_type)
                SELECT
                    s.stop_id,
                    s.parent_station,
                    s.stop_name,
                    s.platform_code,
                    s.stop_lat,
                    s.stop_lon,
                    s.location_type
                FROM staging.gtfs_stops s
                WHERE s.parent_station IS NOT NULL AND s.parent_station <> ''
                ON CONFLICT (platform_id) DO UPDATE
                SET station_id = EXCLUDED.station_id,
                    platform_name = EXCLUDED.platform_name,
                    platform_code = EXCLUDED.platform_code,
                    platform_lat = EXCLUDED.platform_lat,
                    platform_lon = EXCLUDED.platform_lon,
                    location_type = EXCLUDED.location_type;
                """
            )

        conn.commit()
        print("Built core station and platform tables")


if __name__ == "__main__":
    main()
