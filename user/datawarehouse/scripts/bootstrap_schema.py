from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
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


def main() -> None:
    with psycopg.connect(**db_config()) as conn:
        with conn.cursor() as cur:
            cur.execute(STAGING_SCHEMA.read_text(encoding="utf-8"))
            cur.execute(CORE_SCHEMA.read_text(encoding="utf-8"))
        conn.commit()
        print("Created staging and core schemas")


if __name__ == "__main__":
    main()
