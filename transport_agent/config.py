from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _build_db_url() -> str:
    explicit = os.getenv("TRANSPORT_DB_URL")
    if explicit:
        if explicit.startswith("postgresql://") and "+" not in explicit.split("://", 1)[0]:
            return explicit.replace("postgresql://", "postgresql+psycopg://", 1)
        return explicit
    host = os.getenv("POSTGRES_CONN_HOST", "localhost")
    port = os.getenv("POSTGRES_CONN_PORT", "5432")
    user = os.getenv("POSTGRES_USERNAME", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    db = os.getenv("POSTGRES_DB", "transport")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def make_engine() -> Engine:
    return create_engine(_build_db_url())


def make_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()
