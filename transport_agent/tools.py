from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text

MAX_ROWS = 200

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "list_tables",
        "description": "List all tables in the transport PostgreSQL database grouped by schema.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "describe_table",
        "description": "Get column names, data types, and nullability for a specific table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "schema": {"type": "string", "description": "Schema name, e.g. 'raw'"},
                "table": {"type": "string", "description": "Table name, e.g. 'stops'"},
            },
            "required": ["schema", "table"],
        },
    },
    {
        "name": "execute_query",
        "description": (
            "Run a read-only SELECT query against the transport database. "
            f"Returns up to {MAX_ROWS} rows as JSON."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A SELECT SQL query to execute"},
            },
            "required": ["sql"],
        },
    },
]


def list_tables(engine: Engine) -> str:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)).fetchall()
    return json.dumps([{"schema": r[0], "table": r[1]} for r in rows])


def describe_table(engine: Engine, schema: str, table: str) -> str:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """), {"schema": schema, "table": table}).fetchall()
    if not rows:
        return json.dumps({"error": f"Table {schema}.{table} not found"})
    return json.dumps([{"column": r[0], "type": r[1], "nullable": r[2]} for r in rows])


def execute_query(engine: Engine, sql: str) -> str:
    if not sql.strip().lower().startswith("select"):
        return json.dumps({"error": "Only SELECT queries are allowed"})
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        cols = list(result.keys())
        rows = result.fetchmany(MAX_ROWS)
    data = [dict(zip(cols, row)) for row in rows]
    return json.dumps({"columns": cols, "rows": data, "count": len(data)}, default=str)


def dispatch(engine: Engine, name: str, inputs: dict[str, Any]) -> str:
    if name == "list_tables":
        return list_tables(engine)
    if name == "describe_table":
        return describe_table(engine, inputs["schema"], inputs["table"])
    if name == "execute_query":
        return execute_query(engine, inputs["sql"])
    return json.dumps({"error": f"Unknown tool: {name}"})
