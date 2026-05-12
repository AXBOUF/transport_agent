"""
Transport NSW Dashboard — FastAPI backend
Serves the frontend and exposes API endpoints for chat and live data.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / "static"

sys.path.insert(0, str(ROOT / "transport_agent"))
load_dotenv(ROOT / ".env")

from config import db_url       # noqa: E402
import minimal_agent            # noqa: E402

app = FastAPI(title="Transport NSW Live")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat")
async def chat(body: ChatRequest):
    try:
        answer = await asyncio.to_thread(minimal_agent.run, body.question)
        return {"answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Vehicles ──────────────────────────────────────────────────────────────────

@app.get("/api/vehicles")
def vehicles(transport_type: str = "metro"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT
                    vehicle_id, trip_id, route_id,
                    route_short_name, route_long_name,
                    latitude, longitude, bearing, speed,
                    current_status, stop_name, stop_sequence,
                    occupancy_status, fetched_at
                FROM analysis.live_vehicle_positions
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """).fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    features = []
    for r in rows:
        lat, lon = r[5], r[6]
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "vehicle_id":     r[0],
                "trip_id":        r[1],
                "route_id":       r[2],
                "route":          r[3] or r[4] or r[2] or "—",
                "bearing":        float(r[7]) if r[7] is not None else None,
                "speed_kmh":      round(float(r[8]) * 3.6, 1) if r[8] is not None else None,
                "status":         r[9],
                "at_stop":        r[10],
                "stop_sequence":  r[11],
                "occupancy":      r[12],
                "as_of":          r[13].strftime("%H:%M:%S") if r[13] else None,
                "transport_type": transport_type,
            },
        })

    return {"type": "FeatureCollection", "features": features, "count": len(features)}


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get("/api/alerts")
def alerts(transport_type: str = "metro"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT entity_id, cause, effect, header_text,
                       description_text, route_ids, active_start, active_end
                FROM analysis.live_alerts
                ORDER BY active_start NULLS FIRST
            """).fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return [
        {
            "id":          r[0],
            "cause":       r[1],
            "effect":      r[2],
            "header":      r[3],
            "description": r[4],
            "routes":      r[5],
            "active_from": r[6].isoformat() if r[6] else None,
            "active_to":   r[7].isoformat() if r[7] else None,
        }
        for r in rows
    ]
