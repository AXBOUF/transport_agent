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


# ── Dispatch ──────────────────────────────────────────────────────────────────

def run_tool(name: str, inputs: dict) -> str:  # noqa: ARG001 — inputs used by future tools
    if name == "list_tables":
        return list_tables()
    return json.dumps({"error": f"unknown tool: {name}"})
