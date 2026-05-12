from __future__ import annotations

import json
from datetime import datetime

import psycopg

from config import db_url

def _f(v) -> float | None:
    """Convert Decimal/numeric DB value to float for JSON serialisation."""
    return float(v) if v is not None else None


SCHEMAS = [
    {
        "name": "get_next_services",
        "description": (
            "Find the next scheduled services between two stations from a given time. "
            "If no time is given the current time is used. "
            "Returns departure time, arrival time, and destination headsign. "
            "Use transport_type to pick the right database: metro, sydneytrains, transport."
        ),
        "input": {
            "from_station":    "string — partial station name e.g. 'Central'",
            "to_station":      "string — partial station name e.g. 'Chatswood'",
            "after_time":      "optional — HH:MM on today's date, defaults to now",
            "date":            "optional — YYYY-MM-DD, defaults to today",
            "limit":           "optional — number of services to return, defaults to 3",
            "transport_type":  "optional — auto (default, searches all networks), metro, sydneytrains, or transport",
        },
    },
    {
        "name": "get_live_departures",
        "description": (
            "Get upcoming real-time departures from a stop, with live delay information. "
            "Shows estimated departure time, delay in seconds, vehicle position, and "
            "whether real-time data is available. Covers the next 2.5 hours from now. "
            "Only available for metro and sydneytrains."
        ),
        "input": {
            "stop_name":      "string — partial stop name e.g. 'Central'",
            "transport_type": "optional — auto (default, searches metro + sydneytrains), metro, or sydneytrains",
            "limit":          "optional — number of departures, defaults to 5",
        },
    },
    {
        "name": "get_active_alerts",
        "description": (
            "Get current service alerts — disruptions, delays, planned works. "
            "Returns alert text, affected routes, cause, and effect. "
            "Only available for metro and sydneytrains."
        ),
        "input": {
            "transport_type": "optional — metro (default) or sydneytrains",
        },
    },
    {
        "name": "get_vehicle_position",
        "description": (
            "Get the current real-time position and status of vehicles on a route or trip. "
            "Returns latitude, longitude, bearing, speed, current stop, and occupancy. "
            "Only available for metro and sydneytrains."
        ),
        "input": {
            "route_id":       "optional — exact route_id to filter by",
            "trip_id":        "optional — exact trip_id to filter by",
            "transport_type": "optional — metro (default) or sydneytrains",
            "limit":          "optional — number of vehicles, defaults to 10",
        },
    },
    {
        "name": "get_delay_trend",
        "description": (
            "Show how delays have changed over the past N hours for a network or specific route. "
            "Returns average delay per 5-minute snapshot so you can see if delays are improving or worsening. "
            "Only available for metro and sydneytrains."
        ),
        "input": {
            "transport_type": "optional — auto (default), metro, or sydneytrains",
            "route_id":       "optional — filter to a specific route",
            "hours":          "optional — how many hours of history to show, defaults to 2",
        },
    },
    {
        "name": "get_worst_delays",
        "description": (
            "Find the most delayed trips in the past N hours. "
            "Useful for answering 'which services have been delayed today?' or 'what was running late this morning?'. "
            "Only available for metro and sydneytrains."
        ),
        "input": {
            "transport_type": "optional — auto (default), metro, or sydneytrains",
            "hours":          "optional — how far back to look, defaults to 2",
            "limit":          "optional — number of trips to return, defaults to 10",
        },
    },
    {
        "name": "list_tables",
        "description": "Returns all table names in the database grouped by schema.",
        "input": {
            "transport_type": "optional — metro (default), sydneytrains, transport, or buses",
        },
    },
    {
        "name": "describe_table",
        "description": "Returns columns and datatypes for a table.",
        "input": {
            "table_name":     "string",
            "schema":         "optional schema name (defaults to staging)",
            "transport_type": "optional — metro (default), sydneytrains, transport, or buses",
        },
    },
]


def _tool_block(schema: dict) -> str:
    return f"- {schema['name']}: {schema['description']} Input: {json.dumps(schema['input'])}"


def tools_prompt() -> str:
    return "\n".join(_tool_block(s) for s in SCHEMAS)


ANTHROPIC_TOOLS = [
    {
        "name": "get_next_services",
        "description": (
            "Find the next scheduled services between two stations from a given time. "
            "If no time is given the current time is used. "
            "Returns departure time, arrival time, and destination headsign. "
            "transport_type auto searches all networks (metro, sydneytrains, transport)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_station":   {"type": "string",  "description": "Partial station name e.g. 'Central'"},
                "to_station":     {"type": "string",  "description": "Partial station name e.g. 'Chatswood'"},
                "after_time":     {"type": "string",  "description": "HH:MM on today's date, defaults to now"},
                "date":           {"type": "string",  "description": "YYYY-MM-DD, defaults to today"},
                "limit":          {"type": "integer", "description": "Number of services to return, defaults to 3"},
                "transport_type": {"type": "string",  "description": "auto (default), metro, sydneytrains, or transport"},
            },
            "required": ["from_station", "to_station"],
        },
    },
    {
        "name": "get_live_departures",
        "description": (
            "Get upcoming real-time departures from a stop, with live delay information. "
            "Shows estimated departure time, delay in seconds, vehicle position, and "
            "whether real-time data is available. Covers the next 2.5 hours from now. "
            "Only available for metro and sydneytrains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "stop_name":      {"type": "string",  "description": "Partial stop name e.g. 'Central'"},
                "transport_type": {"type": "string",  "description": "auto (default, searches metro + sydneytrains), metro, or sydneytrains"},
                "limit":          {"type": "integer", "description": "Number of departures, defaults to 5"},
            },
            "required": ["stop_name"],
        },
    },
    {
        "name": "get_active_alerts",
        "description": (
            "Get current service alerts — disruptions, delays, planned works. "
            "Returns alert text, affected routes, cause, and effect. "
            "Only available for metro and sydneytrains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transport_type": {"type": "string", "description": "metro (default) or sydneytrains"},
            },
        },
    },
    {
        "name": "get_vehicle_position",
        "description": (
            "Get the current real-time position and status of vehicles on a route or trip. "
            "Returns latitude, longitude, bearing, speed, current stop, delay, and destination. "
            "transport_type auto searches both metro and sydneytrains. "
            "Use route_name to filter by a line name like 'T1' or 'M1'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "route_id":       {"type": "string",  "description": "Exact route_id to filter by"},
                "trip_id":        {"type": "string",  "description": "Exact trip_id to filter by"},
                "route_name":     {"type": "string",  "description": "Partial route name to filter by, e.g. 'T1', 'M1'"},
                "transport_type": {"type": "string",  "description": "auto (default, searches metro + sydneytrains), metro, or sydneytrains"},
                "limit":          {"type": "integer", "description": "Number of vehicles, defaults to 10"},
            },
        },
    },
    {
        "name": "get_delay_trend",
        "description": (
            "Show how delays have changed over the past N hours for a network or specific route. "
            "Returns average delay per 5-minute snapshot so you can see if delays are improving or worsening. "
            "Only available for metro and sydneytrains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transport_type": {"type": "string",  "description": "auto (default), metro, or sydneytrains"},
                "route_id":       {"type": "string",  "description": "Filter to a specific route"},
                "hours":          {"type": "integer", "description": "How many hours of history to show, defaults to 2"},
            },
        },
    },
    {
        "name": "get_worst_delays",
        "description": (
            "Find the most delayed trips in the past N hours. "
            "Useful for answering 'which services have been delayed today?' or 'what was running late this morning?'. "
            "Only available for metro and sydneytrains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transport_type": {"type": "string",  "description": "auto (default), metro, or sydneytrains"},
                "hours":          {"type": "integer", "description": "How far back to look, defaults to 2"},
                "limit":          {"type": "integer", "description": "Number of trips to return, defaults to 10"},
            },
        },
    },
    {
        "name": "list_tables",
        "description": "Returns all table names in the database grouped by schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transport_type": {"type": "string", "description": "metro (default), sydneytrains, transport, or buses"},
            },
        },
    },
    {
        "name": "describe_table",
        "description": "Returns columns and datatypes for a table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name":     {"type": "string", "description": "Table name"},
                "schema":         {"type": "string", "description": "Schema name, defaults to staging"},
                "transport_type": {"type": "string", "description": "metro (default), sydneytrains, transport, or buses"},
            },
            "required": ["table_name"],
        },
    },
    {
        "name": "render_chart",
        "description": (
            "Render a chart in the UI canvas. Call this after gathering data whenever a visual "
            "would be clearer than text. Pick the best chart type for the data: "
            "'line' for trends over time, 'bar' for comparisons, 'pie'/'doughnut' for proportions. "
            "You can call this AND return a text answer — the chart appears alongside your reply."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type":   {"type": "string", "enum": ["bar", "line", "pie", "doughnut"],
                           "description": "Chart type"},
                "title":  {"type": "string", "description": "Chart title shown above the chart"},
                "x_label":{"type": "string", "description": "X-axis label (bar/line only)"},
                "y_label":{"type": "string", "description": "Y-axis label (bar/line only)"},
                "labels": {"type": "array",  "items": {"type": "string"},
                           "description": "Category labels (x-axis for bar/line, slice names for pie)"},
                "datasets": {
                    "type": "array",
                    "description": "One entry per data series",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string",  "description": "Series name shown in legend"},
                            "data":  {"type": "array",   "items": {"type": "number"}},
                            "color": {"type": "string",  "description": "Hex color e.g. #F5A623 (optional)"},
                        },
                        "required": ["label", "data"],
                    },
                },
            },
            "required": ["type", "title", "labels", "datasets"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Run a read-only SELECT query directly against a transport database. "
            "Use this for any question that the pre-built tools cannot answer — "
            "platform counts, stop lookups, route listings, custom aggregations, etc. "
            "Only SELECT is allowed. Results capped at 100 rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":          {"type": "string",  "description": "A valid PostgreSQL SELECT statement"},
                "transport_type": {"type": "string",  "description": "metro (default), sydneytrains, transport, or buses"},
            },
            "required": ["query"],
        },
    },
]


# ── Implementations ───────────────────────────────────────────────────────────

_STATIC_DBS = ["sydneytrains", "metro", "transport"]
_LIVE_DBS   = ["sydneytrains", "metro"]


def _query_next_services(
    transport_type: str,
    from_station: str,
    to_station: str,
    service_date: str,
    from_dt: str,
    limit: int,
) -> list[dict]:
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT
                    dep.scheduled_departure_ts,
                    arr.scheduled_arrival_ts,
                    dep.trip_headsign,
                    dep.stop_name,
                    arr.stop_name
                FROM analysis.fact_scheduled_stop_events dep
                JOIN analysis.fact_scheduled_stop_events arr
                  ON  arr.trip_id       = dep.trip_id
                  AND arr.service_date  = dep.service_date
                  AND arr.stop_name     ILIKE %s
                  AND arr.stop_sequence > dep.stop_sequence
                WHERE dep.stop_name    ILIKE %s
                  AND dep.service_date = %s
                  AND dep.scheduled_departure_ts >= %s
                ORDER BY dep.scheduled_departure_ts
                LIMIT %s
            """, (
                f"%{to_station}%",
                f"%{from_station}%",
                service_date,
                from_dt,
                limit,
            )).fetchall()
    except Exception:
        return []

    return [{
        "departs":        r[0].strftime("%H:%M"),
        "arrives":        r[1].strftime("%H:%M"),
        "destination":    r[2],
        "from_stop":      r[3],
        "to_stop":        r[4],
        "transport_type": transport_type,
    } for r in rows]


def get_next_services(
    from_station: str,
    to_station: str,
    after_time: str | None = None,
    date: str | None = None,
    limit: int = 3,
    transport_type: str = "auto",
) -> str:
    now = datetime.now()
    service_date = date or now.strftime("%Y-%m-%d")
    from_dt = f"{service_date} {after_time}:00" if after_time else now.strftime("%Y-%m-%d %H:%M:%S")

    targets = _STATIC_DBS if transport_type == "auto" else [transport_type]

    results = []
    for tt in targets:
        results.extend(_query_next_services(tt, from_station, to_station, service_date, from_dt, limit))

    results.sort(key=lambda r: r["departs"])
    results = results[:limit]

    if not results:
        return json.dumps({"message": f"No services found from {from_station} to {to_station} after {from_dt}"})

    return json.dumps(results)


def _query_live_departures(transport_type: str, stop_name: str, limit: int) -> list[dict]:
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute("""
                SELECT
                    stop_name, route_name, trip_headsign,
                    scheduled_departure_ts, estimated_departure_ts,
                    departure_delay, schedule_relationship,
                    current_status, vehicle_lat, vehicle_lon,
                    occupancy_status, has_realtime, rt_fetched_at
                FROM analysis.live_departures
                WHERE stop_name ILIKE %s
                ORDER BY estimated_departure_ts
                LIMIT %s
            """, (f"%{stop_name}%", limit)).fetchall()
    except Exception:
        return []

    return [{
        "stop":                  r[0],
        "route":                 r[1],
        "destination":           r[2],
        "scheduled_departure":   r[3].strftime("%H:%M") if r[3] else None,
        "estimated_departure":   r[4].strftime("%H:%M") if r[4] else None,
        "delay_seconds":         r[5],
        "schedule_relationship": r[6],
        "vehicle_status":        r[7],
        "vehicle_lat":           _f(r[8]),
        "vehicle_lon":           _f(r[9]),
        "occupancy":             r[10],
        "has_realtime":          r[11],
        "rt_as_of":              r[12].strftime("%H:%M:%S") if r[12] else None,
        "transport_type":        transport_type,
    } for r in rows]


def get_live_departures(
    stop_name: str,
    transport_type: str = "auto",
    limit: int = 5,
) -> str:
    targets = _LIVE_DBS if transport_type == "auto" else [transport_type]

    results = []
    for tt in targets:
        results.extend(_query_live_departures(tt, stop_name, limit))

    results.sort(key=lambda r: r["estimated_departure"] or "")
    results = results[:limit]

    if not results:
        return json.dumps({"message": f"No upcoming departures found at '{stop_name}' in the next 2.5 hours"})

    return json.dumps(results)


def get_active_alerts(transport_type: str = "metro") -> str:
    with psycopg.connect(db_url(transport_type)) as conn:
        rows = conn.execute("""
            SELECT
                entity_id,
                cause,
                effect,
                header_text,
                description_text,
                route_ids,
                active_start,
                active_end,
                fetched_at
            FROM analysis.live_alerts
            ORDER BY active_start NULLS FIRST
        """).fetchall()

    if not rows:
        return json.dumps({"message": f"No active alerts for {transport_type}"})

    return json.dumps([{
        "id":          r[0],
        "cause":       r[1],
        "effect":      r[2],
        "header":      r[3],
        "description": r[4],
        "routes":      r[5],
        "active_from": r[6].strftime("%Y-%m-%d %H:%M") if r[6] else None,
        "active_to":   r[7].strftime("%Y-%m-%d %H:%M") if r[7] else None,
        "fetched_at":  r[8].strftime("%H:%M:%S") if r[8] else None,
    } for r in rows])


def _query_vehicle_position(
    transport_type: str,
    route_id: str | None,
    trip_id: str | None,
    route_name: str | None,
    limit: int,
) -> list[dict]:
    filters: list[str] = []
    params:  list      = []

    if route_id:
        filters.append("route_id = %s");    params.append(route_id)
    if trip_id:
        filters.append("trip_id = %s");     params.append(trip_id)
    if route_name:
        filters.append("route_name ILIKE %s"); params.append(f"%{route_name}%")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params.append(limit)

    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            rows = conn.execute(f"""
                SELECT
                    vehicle_id, trip_id, route_id, route_name,
                    latitude, longitude, bearing, speed,
                    current_status, delay_seconds,
                    next_stop_name, destination,
                    occupancy_status, transport_type, updated_at
                FROM analysis.agent_live_vehicle_state
                {where}
                ORDER BY updated_at DESC
                LIMIT %s
            """, params).fetchall()
    except Exception:
        return []

    return [{
        "vehicle_id":    r[0],
        "trip_id":       r[1],
        "route_id":      r[2],
        "route":         r[3],
        "latitude":      _f(r[4]),
        "longitude":     _f(r[5]),
        "bearing":       _f(r[6]),
        "speed_kmh":     round(_f(r[7]) * 3.6, 1) if r[7] else None,
        "status":        r[8],
        "delay_seconds": r[9],
        "next_stop":     r[10],
        "destination":   r[11],
        "occupancy":     r[12],
        "network":       r[13],
        "as_of":         r[14].strftime("%H:%M:%S") if r[14] else None,
    } for r in rows]


def get_vehicle_position(
    route_id: str | None = None,
    trip_id: str | None = None,
    route_name: str | None = None,
    transport_type: str = "auto",
    limit: int = 10,
) -> str:
    targets = _LIVE_DBS if transport_type == "auto" else [transport_type]
    results = []

    for tt in targets:
        results.extend(_query_vehicle_position(tt, route_id, trip_id, route_name, limit))

    results.sort(key=lambda r: r["as_of"] or "", reverse=True)
    results = results[:limit]

    if not results:
        return json.dumps({"message": "No live vehicle positions found. Check that test_realtime.py is running."})

    return json.dumps(results)


def get_delay_trend(
    transport_type: str = "auto",
    route_id: str | None = None,
    hours: int = 2,
) -> str:
    targets = _LIVE_DBS if transport_type == "auto" else [transport_type]
    results = []

    for tt in targets:
        try:
            route_filter = "AND route_id = %s" if route_id else ""
            params = [hours, route_id] if route_id else [hours]
            with psycopg.connect(db_url(tt)) as conn:
                rows = conn.execute(f"""
                    SELECT
                        date_trunc('minute', recorded_at) -
                            (EXTRACT(minute FROM recorded_at)::int %% 5) * interval '1 minute'
                                                        AS bucket,
                        COUNT(DISTINCT trip_id)          AS trips_sampled,
                        ROUND(AVG(delay_seconds))        AS avg_delay_seconds,
                        ROUND(MAX(delay_seconds))        AS max_delay_seconds,
                        COUNT(*) FILTER (WHERE delay_seconds > 60)  AS delayed_count,
                        COUNT(*) FILTER (WHERE delay_seconds > 300) AS severely_delayed
                    FROM realtime.rt_delay_history
                    WHERE transport_type = %s
                      AND recorded_at >= now() - %s * interval '1 hour'
                      {route_filter}
                    GROUP BY bucket
                    ORDER BY bucket
                """, (tt, *params)).fetchall()
        except Exception:
            continue

        for r in rows:
            results.append({
                "time":              r[0].strftime("%H:%M") if r[0] else None,
                "transport_type":    tt,
                "trips_sampled":     r[1],
                "avg_delay_seconds": int(r[2]) if r[2] else 0,
                "max_delay_seconds": int(r[3]) if r[3] else 0,
                "delayed_count":     r[4],
                "severely_delayed":  r[5],
            })

    if not results:
        return json.dumps({"message": "No delay history yet — history builds up after test_realtime.py has been running for at least 5 minutes."})

    return json.dumps(results)


def get_worst_delays(
    transport_type: str = "auto",
    hours: int = 2,
    limit: int = 10,
) -> str:
    targets = _LIVE_DBS if transport_type == "auto" else [transport_type]
    results = []

    for tt in targets:
        try:
            with psycopg.connect(db_url(tt)) as conn:
                rows = conn.execute("""
                    SELECT
                        trip_id,
                        route_id,
                        transport_type,
                        ROUND(MAX(delay_seconds))   AS peak_delay_seconds,
                        ROUND(AVG(delay_seconds))   AS avg_delay_seconds,
                        MIN(recorded_at)            AS first_seen,
                        MAX(recorded_at)            AS last_seen,
                        COUNT(*)                    AS snapshots
                    FROM realtime.rt_delay_history
                    WHERE transport_type = %s
                      AND recorded_at >= now() - %s * interval '1 hour'
                      AND delay_seconds > 60
                    GROUP BY trip_id, route_id, transport_type
                    ORDER BY peak_delay_seconds DESC
                    LIMIT %s
                """, (tt, hours, limit)).fetchall()
        except Exception:
            continue

        for r in rows:
            results.append({
                "trip_id":           r[0],
                "route_id":          r[1],
                "transport_type":    r[2],
                "peak_delay_min":    round(int(r[3] or 0) / 60, 1),
                "avg_delay_min":     round(int(r[4] or 0) / 60, 1),
                "first_seen":        r[5].strftime("%H:%M") if r[5] else None,
                "last_seen":         r[6].strftime("%H:%M") if r[6] else None,
                "snapshots":         r[7],
            })

    results.sort(key=lambda x: x["peak_delay_min"], reverse=True)
    results = results[:limit]

    if not results:
        return json.dumps({"message": f"No delayed trips found in the last {hours} hour(s)."})

    return json.dumps(results)


def list_tables(transport_type: str = "metro") -> str:
    with psycopg.connect(db_url(transport_type)) as conn:
        rows = conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """).fetchall()
    return json.dumps([{"schema": r[0], "table": r[1]} for r in rows])


def describe_table(table_name: str, schema: str | None = None, transport_type: str = "metro") -> str:
    schema = schema or "staging"
    with psycopg.connect(db_url(transport_type)) as conn:
        rows = conn.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table_name),
        ).fetchall()
    return json.dumps([{"column": r[0], "type": r[1]} for r in rows])


def run_sql(query: str, transport_type: str = "metro") -> str:
    q = query.strip()
    if not q.lower().startswith("select"):
        return json.dumps({"error": "Only SELECT queries are allowed."})
    try:
        with psycopg.connect(db_url(transport_type)) as conn:
            cur = conn.execute(q)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchmany(100)
        results = []
        for row in rows:
            record = {}
            for col, val in zip(cols, row):
                if hasattr(val, "strftime"):
                    record[col] = val.strftime("%Y-%m-%d %H:%M:%S")
                elif hasattr(val, "__float__"):
                    record[col] = _f(val)
                else:
                    record[col] = val
            results.append(record)
        return json.dumps({"columns": cols, "rows": results, "count": len(results)})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Dispatch ──────────────────────────────────────────────────────────────────

def run_tool(name: str, inputs: dict) -> str:
    transport = inputs.get("transport_type", "auto")

    if name == "get_next_services":
        return get_next_services(
            from_station=inputs["from_station"],
            to_station=inputs["to_station"],
            after_time=inputs.get("after_time"),
            date=inputs.get("date"),
            limit=int(inputs.get("limit", 3)),
            transport_type=transport,
        )
    if name == "get_live_departures":
        stop = inputs.get("stop_name")
        if not stop:
            return json.dumps({"error": "missing 'stop_name'"})
        return get_live_departures(
            stop_name=stop,
            transport_type=transport,
            limit=int(inputs.get("limit", 5)),
        )
    if name == "get_active_alerts":
        return get_active_alerts(transport_type=transport)
    if name == "get_vehicle_position":
        return get_vehicle_position(
            route_id=inputs.get("route_id"),
            trip_id=inputs.get("trip_id"),
            route_name=inputs.get("route_name"),
            transport_type=transport,
            limit=int(inputs.get("limit", 10)),
        )
    if name == "get_delay_trend":
        return get_delay_trend(
            transport_type=transport,
            route_id=inputs.get("route_id"),
            hours=int(inputs.get("hours", 2)),
        )
    if name == "get_worst_delays":
        return get_worst_delays(
            transport_type=transport,
            hours=int(inputs.get("hours", 2)),
            limit=int(inputs.get("limit", 10)),
        )
    if name == "list_tables":
        return list_tables(transport_type=transport)
    if name == "describe_table":
        table = inputs.get("table_name") or inputs.get("table")
        if not table:
            return json.dumps({"error": "missing 'table_name' in input"})
        return describe_table(table, inputs.get("schema"), transport_type=transport)
    if name == "run_sql":
        query = inputs.get("query") or inputs.get("sql")
        if not query:
            return json.dumps({"error": "missing 'query'"})
        return run_sql(query, transport_type=transport)
    if name == "render_chart":
        return json.dumps({"status": "chart rendered in UI"})

    return json.dumps({"error": f"unknown tool: {name}"})
