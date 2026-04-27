from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency in local environments
    psycopg = None


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STOPS_CANDIDATES = [
    ROOT / "gtfs_METRO" / "stops.txt",
    ROOT / "gtfs_data" / "stops.txt",
    ROOT / "user" / "gtfs_data" / "stops.txt",
]


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def resolve_stops_file() -> Path | None:
    explicit_path = os.getenv("GTFS_STOPS_FILE")
    if explicit_path:
        candidate = Path(explicit_path)
        if candidate.exists():
            return candidate

    for candidate in DEFAULT_STOPS_CANDIDATES:
        if candidate.exists():
            return candidate

    return None


def load_db_config() -> dict[str, Any]:
    load_dotenv_file(ROOT / ".env")

    host = os.getenv("POSTGRES_CONN_HOST", "localhost")
    port = int(os.getenv("POSTGRES_CONN_PORT", "5432"))
    user = os.getenv("POSTGRES_USERNAME")
    password = os.getenv("POSTGRES_PASSWORD")
    dbname = os.getenv("POSTGRES_DB")

    if not all([user, password, dbname]):
        raise RuntimeError("Missing Postgres credentials in .env")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": dbname,
    }


def check_postgres_connection() -> None:
    if psycopg is None:
        print("Postgres check skipped: psycopg is not installed")
        return

    config = load_db_config()
    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute("select current_database(), current_user")
            database, user = cur.fetchone()
            print(f"DB connection: ok ({database} / {user})")


def summarize_stops_file() -> None:
    stops_file = resolve_stops_file()
    if stops_file is None:
        print("GTFS stops summary skipped: no stops.txt file found")
        return

    stations: dict[str, dict[str, object]] = {}
    platforms_by_station: dict[str, list[dict[str, str]]] = defaultdict(list)

    with stops_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stop_id = row.get("stop_id", "").strip()
            stop_name = row.get("stop_name", "").strip()
            location_type = row.get("location_type", "").strip()
            parent_station = row.get("parent_station", "").strip()
            platform_code = row.get("platform_code", "").strip()
            stop_lat = row.get("stop_lat", "").strip()
            stop_lon = row.get("stop_lon", "").strip()

            if location_type == "1" or not parent_station:
                stations[stop_id] = {
                    "stop_name": stop_name,
                    "stop_lat": stop_lat,
                    "stop_lon": stop_lon,
                }
                platforms_by_station.setdefault(stop_id, [])
            else:
                platforms_by_station[parent_station].append(
                    {
                        "stop_id": stop_id,
                        "stop_name": stop_name,
                        "platform_code": platform_code,
                        "stop_lat": stop_lat,
                        "stop_lon": stop_lon,
                    }
                )

    print(f"Stations found: {len(stations)}")
    print("Sample station hierarchy:")

    for station_id, station in list(stations.items())[:5]:
        platforms = platforms_by_station.get(station_id, [])
        print(f"- {station['stop_name']} ({station_id})")
        print(f"  location: {station['stop_lat']}, {station['stop_lon']}")
        print(f"  platforms: {len(platforms)}")
        for platform in platforms[:5]:
            label = platform["platform_code"] or platform["stop_name"]
            print(f"    - {label} ({platform['stop_id']})")


def main() -> None:
    print("Running GTFS Metro sanity check")
    check_postgres_connection()
    summarize_stops_file()


if __name__ == "__main__":
    main()
