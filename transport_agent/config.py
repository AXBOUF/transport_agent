from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def db_url() -> str:
    # Allow a full DB URL to be provided directly via environment
    for env_var in ("TRANSPORT_DB_URL", "TRANSPORT_DATABASE_URL", "DATABASE_URL"):
        val = os.getenv(env_var)
        if val:
            return val

    # Support a few common environment variable names for individual parts
    host = os.getenv("POSTGRES_HOST") or os.getenv("POSTGRES_CONN_HOST") or "localhost"
    port = os.getenv("POSTGRES_PORT") or os.getenv("POSTGRES_CONN_PORT") or "5432"
    user = (
        os.getenv("POSTGRES_USER")
        or os.getenv("POSTGRES_USERNAME")
        or os.getenv("POSTGRES_CONN_USER")
        or os.getenv("POSTGRES_CONN_USERNAME")
        or "postgres"
    )
    password = (
        os.getenv("POSTGRES_PASSWORD")
        or os.getenv("POSTGRES_CONN_PASSWORD")
        or ""
    )
    db = (
        os.getenv("POSTGRES_DB")
        or os.getenv("POSTGRES_DATABASE")
        or os.getenv("POSTGRES_CONN_DB")
        or os.getenv("POSTGRES_CONN_DATABASE")
        or "METRO"
    )

    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql://{user}@{host}:{port}/{db}"
