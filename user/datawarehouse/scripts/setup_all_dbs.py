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
    }


def create_database(db_name: str) -> None:
    """Create a fresh PostgreSQL database."""
    cfg = db_config()
    admin_db = "postgres"
    
    try:
        with psycopg.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            dbname=admin_db,
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}";')
                cur.execute(f'CREATE DATABASE "{db_name}";')
                print(f"  ✓ Created database '{db_name}'")
    except Exception as e:
        print(f"  ✗ Failed to create '{db_name}': {e}")


def main() -> None:
    print("Setting up all databases (transport, metro, buses)...\n")
    
    databases = ["transport", "metro", "buses", "sydneytrains"]
    for db_name in databases:
        create_database(db_name)
    
    print(f"\nDone — all {len(databases)} databases created")


if __name__ == "__main__":
    main()
