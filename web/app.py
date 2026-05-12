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

ROOT   = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / "static"
DESIGN = ROOT / "desgin"

sys.path.insert(0, str(ROOT / "transport_agent"))
load_dotenv(ROOT / ".env")

from config import db_url       # noqa: E402
import agent                    # noqa: E402

app = FastAPI(title="Transport NSW Live")
app.mount("/static",       StaticFiles(directory=STATIC),           name="static")
app.mount("/static/fonts", StaticFiles(directory=DESIGN / "fonts"), name="fonts")
app.mount("/design",       StaticFiles(directory=DESIGN),           name="design")


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
        result = await asyncio.to_thread(agent.run, body.question)
        return result          # {answer, chart, tools_used}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Vehicles ──────────────────────────────────────────────────────────────────

@app.get("/api/vehicles")
def vehicles(transport_type: str = "metro"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT
                    vp.vehicle_id, vp.trip_id, vp.route_id,
                    COALESCE(r.route_short_name, r.route_long_name, vp.route_id) AS route_name,
                    r.route_color,
                    vp.latitude, vp.longitude, vp.bearing, vp.speed,
                    vp.current_status,
                    stu.departure_delay  AS delay_seconds,
                    s.stop_name          AS next_stop_name,
                    vp.stop_sequence     AS next_stop_sequence,
                    t.trip_headsign      AS destination,
                    vp.occupancy_status, vp.congestion_level,
                    vp.transport_type,   vp.fetched_at
                FROM realtime.rt_vehicle_positions vp
                LEFT JOIN core.routes r ON r.route_id = vp.route_id
                LEFT JOIN core.stops  s ON s.stop_id  = vp.stop_id
                LEFT JOIN core.trips  t ON t.trip_id  = vp.trip_id
                LEFT JOIN realtime.rt_stop_time_updates stu
                       ON stu.trip_id        = vp.trip_id
                      AND stu.stop_id        = vp.stop_id
                      AND stu.transport_type = vp.transport_type
                WHERE vp.latitude IS NOT NULL AND vp.longitude IS NOT NULL
            """).fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    def _color(raw):
        if not raw:
            return None
        return raw if raw.startswith('#') else f'#{raw}'

    features = []
    for r in rows:
        lat, lon = r[5], r[6]
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "vehicle_id":    r[0],
                "trip_id":       r[1],
                "route_id":      r[2],
                "route_name":    r[3] or r[2] or "—",
                "route_color":   _color(r[4]),
                "bearing":       float(r[7]) if r[7] is not None else None,
                "speed_kmh":     round(float(r[8]) * 3.6, 1) if r[8] is not None else None,
                "status":        r[9],
                "delay_seconds": int(r[10]) if r[10] is not None else None,
                "next_stop":     r[11],
                "next_stop_seq": r[12],
                "destination":   r[13],
                "occupancy":     r[14],
                "congestion":    r[15],
                "transport_type":r[16],
                "as_of":         r[17].strftime("%H:%M:%S") if r[17] else None,
            },
        })

    return {"type": "FeatureCollection", "features": features, "count": len(features)}


@app.get("/api/trip/shape")
def trip_shape(trip_id: str, transport_type: str = "metro"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT
                    e.stop_name,
                    COALESCE(e.stop_lat, s.stop_lat)  AS lat,
                    COALESCE(e.stop_lon, s.stop_lon)  AS lon,
                    e.stop_sequence,
                    e.scheduled_departure_ts,
                    e.trip_headsign
                FROM analysis.fact_scheduled_stop_events e
                LEFT JOIN core.stops s ON s.stop_id = e.stop_id
                WHERE e.trip_id = %s
                  AND e.service_date = (
                      SELECT MAX(service_date)
                      FROM analysis.fact_scheduled_stop_events
                      WHERE trip_id = %s
                  )
                ORDER BY e.stop_sequence
            """, (trip_id, trip_id)).fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    stops = [
        {
            "name":      r[0],
            "lat":       float(r[1]) if r[1] else None,
            "lon":       float(r[2]) if r[2] else None,
            "sequence":  r[3],
            "departure": r[4].strftime("%H:%M") if r[4] else None,
        }
        for r in rows if r[1] and r[2]
    ]
    return {
        "trip_id":  trip_id,
        "headsign": rows[0][5] if rows else None,
        "stops":    stops,
    }


@app.get("/api/stops")
def stops(transport_type: str = "metro", platforms: bool = False):
    loc_filter = "AND location_type IN (0, 1)" if platforms else "AND location_type = 1"
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute(f"""
                SELECT stop_id, stop_name, stop_lat, stop_lon,
                       location_type, parent_station, platform_code
                FROM core.stops
                WHERE stop_lat IS NOT NULL AND stop_lon IS NOT NULL
                {loc_filter}
                ORDER BY stop_name
            """).fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "transport_type": transport_type,
        "stops": [
            {
                "id":            r[0],
                "name":          r[1],
                "lat":           float(r[2]),
                "lon":           float(r[3]),
                "type":          r[4],   # 1=station, 0=platform
                "parent":        r[5],
                "platform_code": r[6],
            }
            for r in rows
        ],
    }


# ── Route shapes ─────────────────────────────────────────────────────────────

# Only these lines are in scope — everything else is filtered out
_LINE_META = {
    "T1": {"color": "#F99D1C", "long_name": "North Shore, Northern & Western"},
    "T2": {"color": "#0098CD", "long_name": "Inner West & Leppington"},
    "T3": {"color": "#F37021", "long_name": "Bankstown"},
    "T4": {"color": "#005AA3", "long_name": "Eastern Suburbs & Illawarra"},
    "T5": {"color": "#C4258F", "long_name": "Cumberland"},
    "T6": {"color": "#7C3E21", "long_name": "Carlingford"},
    "T7": {"color": "#6F818E", "long_name": "Olympic Park"},
    "T8": {"color": "#00954C", "long_name": "Airport & South"},
    "T9": {"color": "#D11F2F", "long_name": "Northern"},
    "M1": {"color": "#009FDB", "long_name": "Metro North West & City & Southwest"},
}
_ALLOWED_LINES = set(_LINE_META.keys())


@app.get("/api/routes/shapes")
def route_shapes(transport_type: str = "sydneytrains"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            # Get distinct route short names + their route_ids
            routes = conn.execute("""
                SELECT DISTINCT route_short_name, route_id, route_color
                FROM core.routes
                WHERE route_short_name IS NOT NULL
                ORDER BY route_short_name, route_id
            """).fetchall()

            grouped: dict = {}
            for short_name, route_id, db_color in routes:
                if short_name not in _ALLOWED_LINES:
                    continue
                if short_name not in grouped:
                    meta = _LINE_META.get(short_name, {})
                    color = meta.get("color") or (f"#{db_color}" if db_color else "#6366f1")
                    grouped[short_name] = {
                        "name":      short_name,
                        "long_name": meta.get("long_name", ""),
                        "color":     color,
                        "shapes":    [],
                    }

                # Get all distinct shapes for this route_id, pick longest per shape_id
                shape_rows = conn.execute("""
                    SELECT s.shape_id,
                           s.shape_pt_lat::float,
                           s.shape_pt_lon::float,
                           s.shape_pt_sequence::int
                    FROM staging.shapes s
                    WHERE s.shape_id IN (
                        SELECT DISTINCT shape_id FROM core.trips
                        WHERE route_id = %s AND shape_id IS NOT NULL
                    )
                    ORDER BY s.shape_id, s.shape_pt_sequence::int
                """, (route_id,)).fetchall()

                # Group by shape_id, sample every Nth point for Metro (large shapes)
                shape_groups: dict = {}
                for sid, lat, lon, seq in shape_rows:
                    shape_groups.setdefault(sid, []).append((lat, lon, seq))

                for sid, pts in shape_groups.items():
                    pts.sort(key=lambda x: x[2])
                    # Sample: Metro shapes have ~5000 pts → every 8th; trains <500 → all
                    step = 8 if len(pts) > 1000 else 1
                    coords = [[p[1], p[0]] for i, p in enumerate(pts) if i % step == 0]
                    if len(coords) >= 2:
                        grouped[short_name]["shapes"].append(coords)

            # Deduplicate shapes within each route group
            result = []
            for short_name, group in grouped.items():
                if group["shapes"]:
                    result.append(group)

            return {"routes": result}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Alerts ────────────────────────────────────────────────────────────────────

@app.get("/api/trip/{trip_id}")
def trip_detail(trip_id: str, transport_type: str = "sydneytrains"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT
                    e.stop_sequence,
                    e.stop_name,
                    e.scheduled_departure_ts::time AS scheduled,
                    stu.departure_delay             AS delay_secs,
                    (e.scheduled_departure_ts
                     + make_interval(secs := COALESCE(stu.departure_delay, 0)))::time AS predicted,
                    COALESCE(stu.schedule_relationship, 'NO_DATA') AS status
                FROM analysis.fact_scheduled_stop_events e
                LEFT JOIN realtime.rt_stop_time_updates stu
                       ON stu.trip_id        = e.trip_id
                      AND stu.stop_id        = e.stop_id
                      AND stu.transport_type = %s
                WHERE e.trip_id      = %s
                  AND e.service_date = (
                      SELECT MAX(service_date)
                      FROM analysis.fact_scheduled_stop_events
                      WHERE trip_id = %s AND service_date <= CURRENT_DATE
                  )
                ORDER BY e.stop_sequence
            """, (transport_type, trip_id, trip_id)).fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not rows:
        raise HTTPException(status_code=404, detail="Trip not found")

    headsign = None
    stops = []
    for r in rows:
        stops.append({
            "seq":       r[0],
            "name":      r[1],
            "scheduled": str(r[2])[:5] if r[2] else None,
            "delay_secs": int(r[3]) if r[3] is not None else None,
            "predicted": str(r[4])[:5] if r[4] else None,
            "status":    r[5],
        })
    return {"trip_id": trip_id, "stops": stops}


@app.get("/api/alerts")
def alerts(transport_type: str = "metro"):
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT entity_id, cause, effect, header_text,
                       description_text, route_ids, active_start, active_end
                FROM realtime.rt_alerts
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
