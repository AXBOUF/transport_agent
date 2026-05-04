from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

from config import make_engine
from tools import describe_table, execute_query, list_tables

mcp = FastMCP("transport-db")
_engine = make_engine()


@mcp.tool()
def list_db_tables() -> str:
    """List all tables in the transport PostgreSQL database, grouped by schema."""
    return list_tables(_engine)


@mcp.tool()
def describe_db_table(schema: str, table: str) -> str:
    """Get column names, data types, and nullability for a specific table.

    Args:
        schema: Schema name, e.g. 'raw'
        table: Table name, e.g. 'stops'
    """
    return describe_table(_engine, schema, table)


@mcp.tool()
def query_db(sql: str) -> str:
    """Run a read-only SELECT query against the transport database. Returns up to 200 rows.

    Args:
        sql: A SELECT SQL query to execute
    """
    return execute_query(_engine, sql)


if __name__ == "__main__":
    mcp.run()
