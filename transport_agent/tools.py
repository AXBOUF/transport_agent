from __future__ import annotations

import json

import psycopg

from config import db_url

SCHEMAS = [
    {
        "name": "list_tables",
        "description": "Returns all table names in the database grouped by schema.",
        "input": {},
    },
    {
        "name": "describe_table",
        "description": "Returns columns and datatypes for a table.",
        "input": {"table_name": "string", "schema": "optional schema name (defaults to staging)"},
    },
]


def _tool_block(schema: dict) -> str:
    return f"- {schema['name']}: {schema['description']} Input: {json.dumps(schema['input'])}"


def tools_prompt() -> str:
    return "\n".join(_tool_block(s) for s in SCHEMAS)


# ── Implementations ───────────────────────────────────────────────────────────

def list_tables() -> str:
    with psycopg.connect(db_url()) as conn:
        rows = conn.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """).fetchall()
    return json.dumps([{"schema": r[0], "table": r[1]} for r in rows])


def describe_table(table_name: str, schema: str | None = None) -> str:
    """Return list of columns and data types for a table as JSON.

    If schema is not provided, default to 'staging'.
    """
    schema = schema or "staging"
    with psycopg.connect(db_url()) as conn:
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


# ── Dispatch ──────────────────────────────────────────────────────────────────

def run_tool(name: str, inputs: dict) -> str:  # noqa: ARG001 — inputs used by future tools
    if name == "list_tables":
        return list_tables()
    if name == "describe_table":
        table = inputs.get("table_name") or inputs.get("table")
        schema = inputs.get("schema")
        if not table:
            return json.dumps({"error": "missing 'table_name' in input"})
        return describe_table(table, schema)
    return json.dumps({"error": f"unknown tool: {name}"})
