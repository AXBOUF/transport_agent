from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
GTFS_DIR = ROOT / "gtfs_METRO"


def main() -> None:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("TRANSPORT_NSW_API_KEY")
    if not api_key:
        raise RuntimeError("TRANSPORT_NSW_API_KEY is not set")

    url = "https://api.transport.nsw.gov.au/v2/gtfs/schedule/metro"
    response = requests.get(url, headers={"Authorization": f"apikey {api_key}"}, timeout=60)
    response.raise_for_status()

    GTFS_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(GTFS_DIR)

    print(f"Extracted GTFS Metro data to {GTFS_DIR}")


if __name__ == "__main__":
    main()
