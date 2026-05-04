from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]


def db_config() -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_DB", "transport"),
    }


def main() -> None:
    cfg = db_config()
    with psycopg.connect(**cfg) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS staging;")
            cur.execute("CREATE SCHEMA IF NOT EXISTS core;")
            cur.execute("CREATE SCHEMA IF NOT EXISTS analysis;")
        conn.commit()
    print(f"Bootstrapped schemas (staging, core, analysis) in '{cfg['dbname']}'")


if __name__ == "__main__":
    main()
