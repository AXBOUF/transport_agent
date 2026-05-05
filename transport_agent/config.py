from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def db_url() -> str:
    explicit = os.getenv("TRANSPORT_DB_URL")
    if explicit:
        return explicit
    host = os.getenv("POSTGRES_CONN_HOST", "localhost")
    port = os.getenv("POSTGRES_CONN_PORT", "5432")
    user = os.getenv("POSTGRES_USERNAME", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    db = os.getenv("POSTGRES_DB", "transport")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"
