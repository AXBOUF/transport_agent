from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def db_url(source: str = "metro") -> str:
    host     = os.getenv("POSTGRES_CONN_HOST", "localhost")
    port     = os.getenv("POSTGRES_CONN_PORT", "5432")
    user     = os.getenv("POSTGRES_USERNAME", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    db = {
        "metro":     os.getenv("POSTGRES_DB_METRO", "metro"),
        "transport": os.getenv("POSTGRES_DB_TRANSPORT", "transport"),
        "buses":     os.getenv("POSTGRES_DB_BUSES", "buses"),
    }.get(source, os.getenv("POSTGRES_DATABASE", "metro"))

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"
