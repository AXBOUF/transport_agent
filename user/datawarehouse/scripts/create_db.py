from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]


def db_config(args: argparse.Namespace, admin_db: str = "postgres") -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host": args.host or os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(args.port or os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": args.user or os.getenv("POSTGRES_USERNAME"),
        "password": args.password or os.getenv("POSTGRES_PASSWORD"),
        "dbname": admin_db,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Create (drop+create) a Postgres database")
    p.add_argument("dbname", help="Database name to create")
    p.add_argument("--host", help="Postgres host")
    p.add_argument("--port", help="Postgres port")
    p.add_argument("--user", help="Postgres user")
    p.add_argument("--password", help="Postgres password")
    p.add_argument("--admin-db", default="postgres", help="DB to connect to for admin commands (default: postgres)")
    args = p.parse_args()

    target_db = args.dbname
    cfg = db_config(args, admin_db=args.admin_db)

    print(f"Connecting to {cfg['host']}:{cfg['port']} as {cfg['user']} to recreate '{target_db}' (admin DB: {cfg['dbname']})")

    try:
        # connect to an admin DB (usually 'postgres') so we can drop/create the target DB
        with psycopg.connect(**cfg) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{target_db}";')
                cur.execute(f'CREATE DATABASE "{target_db}";')

        print(f"Done: database '{target_db}' recreated on {cfg['host']}:{cfg['port']}")
    except Exception as exc:
        print(f"Failed to recreate database '{target_db}': {exc}")
        raise


if __name__ == "__main__":
    main()
