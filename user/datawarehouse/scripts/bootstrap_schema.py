from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
# we need to do this for all three db from the env
'''
POSTGRES_DB_TRANSPORT = "transport"
POSTGRES_DB_METRO = "metro"
POSTGRES_DB_BUSES = "buses"

'''
def db_config() -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_DB", "metro"),
    }

db_list = [
    os.getenv("POSTGRES_DB_TRANSPORT",    "transport"),
    os.getenv("POSTGRES_DB_METRO",        "metro"),
    os.getenv("POSTGRES_DB_BUSES",        "buses"),
    os.getenv("POSTGRES_DB_SYDNEYTRAINS", "sydneytrains"),
]


def main() -> None:
    load_dotenv(ROOT / ".env")

    # admin connection config (connect to postgres database to manage DBs)
    admin_cfg = {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_ADMIN_DB", "postgres"),
        "autocommit": True,
    }

    def ensure_db_exists(db_name: str) -> None:
        try:
            with psycopg.connect(host=admin_cfg["host"], port=admin_cfg["port"], user=admin_cfg["user"], password=admin_cfg["password"], dbname=admin_cfg["dbname"], autocommit=True) as aconn:
                with aconn.cursor() as acur:
                    acur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db_name,))
                    if acur.fetchone() is None:
                        acur.execute(f'CREATE DATABASE "{db_name}"')
                        print(f"  Created database '{db_name}'")
                    else:
                        print(f"  Database '{db_name}' already exists")
        except Exception as exc:
            print(f"  Warning: could not ensure database '{db_name}': {exc}")

    def cfg_for(db_name: str) -> dict:
        return {
            "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
            "user": os.getenv("POSTGRES_USERNAME"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "dbname": db_name,
        }

    for db_name in db_list:
        print(f"Bootstrapping schemas in database: {db_name}")
        ensure_db_exists(db_name)
        cfg = cfg_for(db_name)
        try:
            with psycopg.connect(**cfg) as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE SCHEMA IF NOT EXISTS staging;")
                    cur.execute("CREATE SCHEMA IF NOT EXISTS core;")
                    cur.execute("CREATE SCHEMA IF NOT EXISTS analysis;")
                    cur.execute("CREATE SCHEMA IF NOT EXISTS realtime;")
                conn.commit()
            print(f"  Bootstrapped schemas (staging, core, analysis, realtime) in '{db_name}'\n")
        except Exception as exc:
            print(f"  Error bootstrapping schemas in '{db_name}': {exc}\n")


if __name__ == "__main__":
    main()
