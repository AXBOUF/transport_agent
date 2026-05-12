"""Run analysis layer build for sydneytrains only.

load_db() connects only to the target database — transport/metro/buses are untouched.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

from load_analysis import load_db

if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    db_name = os.getenv("POSTGRES_DB_SYDNEYTRAINS", "sydneytrains")
    load_db(db_name)
    print("\nDone")
