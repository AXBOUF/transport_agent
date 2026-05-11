from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_NAME = "core"
SOURCE_SCHEMA = "staging"

load_dotenv(ROOT / ".env")
POSTGRES_DB = os.getenv("POSTGRES_DB_TRANSPORT", "transport")


def db_config() -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": POSTGRES_DB,
    }


def qname(table: str) -> str:
    return f'"{SCHEMA_NAME}"."{table}"'


def src(table: str) -> str:
    return f'"{SOURCE_SCHEMA}"."{table}"'


def table_exists(cur: psycopg.Cursor, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"{SOURCE_SCHEMA}.{table}",))
    return cur.fetchone()[0] is not None


def get_table_columns(cur: psycopg.Cursor, table: str) -> list[str]:
    """Get all column names for a table in SOURCE_SCHEMA."""
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
        (SOURCE_SCHEMA, table),
    )
    return [row[0] for row in cur.fetchall()]


def _text(col: str) -> str:
    return f"NULLIF(({col})::text, '')"


def _smallint(col: str) -> str:
    return f"NULLIF(({col})::text, '')::smallint"


def _integer(col: str) -> str:
    return f"NULLIF(({col})::text, '')::integer"


def _numeric(col: str) -> str:
    return f"NULLIF(({col})::text, '')::numeric"


def _date(col: str) -> str:
    return f"CASE WHEN NULLIF(({col})::text, '') IS NULL THEN NULL ELSE to_date(({col})::text, 'YYYYMMDD') END"


def infer_core_type(table: str, col: str) -> str:
    """Infer appropriate SQL type for a column in core schema."""
    # Numeric coordinates
    if col in {"stop_lat", "stop_lon", "shape_pt_lat", "shape_pt_lon", "level_index", "shape_dist_traveled"}:
        return "numeric"
    # Integers (IDs, sequences, counts)
    if col in {"route_type", "stop_sequence", "shape_pt_sequence", "traversal_time"}:
        return "integer"
    # Flags (0/1 values)
    if col in {
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "location_type", "wheelchair_boarding", "direction_id", "exception_type",
        "pickup_type", "drop_off_type", "timepoint", "wheelchair_accessible", "bikes_allowed",
        "pathway_mode", "is_bidirectional"
    }:
        return "smallint"
    # Dates (YYYYMMDD format)
    if col in {"start_date", "end_date", "date"}:
        return "date"
    # Everything else is text
    return "text"


def infer_cast(table: str, col: str) -> str:
    """Infer SQL cast function for a column."""
    col_type = infer_core_type(table, col)
    if col_type == "numeric":
        return _numeric(col)
    elif col_type == "smallint":
        return _smallint(col)
    elif col_type == "integer":
        return _integer(col)
    elif col_type == "date":
        return _date(col)
    else:
        return _text(col)


def build_ddl(source_tables: dict[str, bool], col_map: dict[str, list[str]]) -> list[str]:
    """Build DDL for core tables using actual staging columns."""
    ddl: list[str] = []

    for table_name, exists in source_tables.items():
        if not exists:
            continue

        cols = col_map.get(table_name, [])
        if not cols:
            continue

        # Special case: shapes gets split into shapes + shape_points
        if table_name == "shapes":
            ddl.append(f"CREATE TABLE {qname('shapes')} (shape_id text PRIMARY KEY);")
            ddl.append(
                f"""CREATE TABLE {qname('shape_points')} (
                shape_id text NOT NULL,
                shape_pt_lat numeric,
                shape_pt_lon numeric,
                shape_pt_sequence integer NOT NULL,
                shape_dist_traveled numeric,
                PRIMARY KEY (shape_id, shape_pt_sequence)
            );"""
            )
            continue

        # Build column definitions with appropriate types
        col_defs = []
        for col in cols:
            col_type = infer_core_type(table_name, col)
            col_defs.append(f'"{col}" {col_type}')

        # Add primary key constraint
        pk_col = None
        if table_name == "agency":
            pk_col = "agency_id"
        elif table_name == "notes":
            pk_col = "note_id"
        elif table_name == "calendar":
            pk_col = "service_id"
        elif table_name == "levels":
            pk_col = "level_id"
        elif table_name == "stops":
            pk_col = "stop_id"
        elif table_name == "routes":
            pk_col = "route_id"
        elif table_name == "trips":
            pk_col = "trip_id"
        elif table_name == "pathways":
            pk_col = "pathway_id"
        elif table_name == "calendar_dates":
            col_defs.append('PRIMARY KEY ("service_id", "date")')
            col_defs_str = ", ".join(col_defs)
            ddl.append(f"CREATE TABLE {qname(table_name)} ({col_defs_str});")
            continue
        elif table_name == "stop_times":
            col_defs.append('PRIMARY KEY ("trip_id", "stop_sequence")')
            col_defs_str = ", ".join(col_defs)
            ddl.append(f"CREATE TABLE {qname(table_name)} ({col_defs_str});")
            continue

        if pk_col and pk_col in cols:
            col_defs.append(f'PRIMARY KEY ("{pk_col}")')

        col_defs_str = ", ".join(col_defs)
        ddl.append(f"CREATE TABLE {qname(table_name)} ({col_defs_str});")

    return ddl


def build_inserts(source_tables: dict[str, bool], col_map: dict[str, list[str]]) -> list[str]:
    """Build INSERT statements, casting columns appropriately."""
    inserts: list[str] = []

    for table_name, exists in source_tables.items():
        if not exists:
            continue

        cols = col_map.get(table_name, [])
        if not cols:
            continue

        # Special case: shapes gets split
        if table_name == "shapes":
            inserts.append(
                f"INSERT INTO {qname('shapes')} SELECT DISTINCT shape_id FROM {src('shapes')} WHERE NULLIF(shape_id::text,'') IS NOT NULL;"
            )
            if "shape_pt_lat" in cols:
                inserts.append(
                    f"""INSERT INTO {qname('shape_points')} 
                    SELECT shape_id, {_numeric('shape_pt_lat')}, {_numeric('shape_pt_lon')},
                    {_integer('shape_pt_sequence')}, {_numeric('shape_dist_traveled')} 
                    FROM {src('shapes')};"""
                )
            continue

        # Build select clause with appropriate casts
        col_alias = "x"
        selects = []
        for col in cols:
            cast_expr = infer_cast(table_name, col)
            selects.append(cast_expr.replace(f"({col})", f"({col_alias}.{col})"))
        select_clause = ", ".join(selects)

        col_list = ", ".join(f'"{col}"' for col in cols)
        inserts.append(
            f"INSERT INTO {qname(table_name)} ({col_list}) SELECT {select_clause} FROM {src(table_name)} {col_alias};"
        )

    return inserts


def build_constraints(source_tables: dict[str, bool]) -> list[str]:
    """Build foreign key constraints."""
    fks: list[str] = []

    if source_tables.get("routes") and source_tables.get("agency"):
        fks.append(
            f"ALTER TABLE {qname('routes')} ADD CONSTRAINT fk_routes_agency FOREIGN KEY (agency_id) REFERENCES {qname('agency')}(agency_id);"
        )

    if source_tables.get("stops"):
        fks.append(
            f"ALTER TABLE {qname('stops')} ADD CONSTRAINT fk_stops_parent FOREIGN KEY (parent_station) REFERENCES {qname('stops')}(stop_id);"
        )
        if source_tables.get("levels"):
            fks.append(
                f"ALTER TABLE {qname('stops')} ADD CONSTRAINT fk_stops_level FOREIGN KEY (level_id) REFERENCES {qname('levels')}(level_id);"
            )

    if source_tables.get("trips"):
        if source_tables.get("routes"):
            fks.append(
                f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_routes FOREIGN KEY (route_id) REFERENCES {qname('routes')}(route_id);"
            )
        if source_tables.get("calendar"):
            fks.append(
                f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_calendar FOREIGN KEY (service_id) REFERENCES {qname('calendar')}(service_id);"
            )
        if source_tables.get("shapes"):
            fks.append(
                f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_shapes FOREIGN KEY (shape_id) REFERENCES {qname('shapes')}(shape_id);"
            )
        if source_tables.get("notes"):
            fks.append(
                f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_notes FOREIGN KEY (trip_note_id) REFERENCES {qname('notes')}(note_id);"
            )

    if source_tables.get("shapes"):
        fks.append(
            f"ALTER TABLE {qname('shape_points')} ADD CONSTRAINT fk_shape_points_shapes FOREIGN KEY (shape_id) REFERENCES {qname('shapes')}(shape_id);"
        )

    if source_tables.get("stop_times"):
        if source_tables.get("trips"):
            fks.append(
                f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_trips FOREIGN KEY (trip_id) REFERENCES {qname('trips')}(trip_id);"
            )
        if source_tables.get("stops"):
            fks.append(
                f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_stops FOREIGN KEY (stop_id) REFERENCES {qname('stops')}(stop_id);"
            )
        if source_tables.get("notes"):
            fks.append(
                f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_notes FOREIGN KEY (stop_note_id) REFERENCES {qname('notes')}(note_id);"
            )

    if source_tables.get("calendar_dates") and source_tables.get("calendar"):
        fks.append(
            f"ALTER TABLE {qname('calendar_dates')} ADD CONSTRAINT fk_cal_dates_calendar FOREIGN KEY (service_id) REFERENCES {qname('calendar')}(service_id);"
        )

    if source_tables.get("pathways") and source_tables.get("stops"):
        fks.append(
            f"ALTER TABLE {qname('pathways')} ADD CONSTRAINT fk_pathways_from FOREIGN KEY (from_stop_id) REFERENCES {qname('stops')}(stop_id);"
        )
        fks.append(
            f"ALTER TABLE {qname('pathways')} ADD CONSTRAINT fk_pathways_to FOREIGN KEY (to_stop_id) REFERENCES {qname('stops')}(stop_id);"
        )

    return fks


def main() -> None:
    cfg = db_config()
    print(f"Loading staging → core in '{cfg['dbname']}'")

    with psycopg.connect(**cfg) as conn:
        with conn.cursor() as cur:
            source_tables = {
                "agency": table_exists(cur, "agency"),
                "notes": table_exists(cur, "notes"),
                "calendar": table_exists(cur, "calendar"),
                "levels": table_exists(cur, "levels"),
                "stops": table_exists(cur, "stops"),
                "routes": table_exists(cur, "routes"),
                "shapes": table_exists(cur, "shapes"),
                "trips": table_exists(cur, "trips"),
                "stop_times": table_exists(cur, "stop_times"),
                "calendar_dates": table_exists(cur, "calendar_dates"),
                "pathways": table_exists(cur, "pathways"),
            }

            col_map = {}
            for table_name in source_tables:
                if source_tables[table_name]:
                    col_map[table_name] = get_table_columns(cur, table_name)

            cur.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA_NAME}" CASCADE;')
            cur.execute(f'CREATE SCHEMA "{SCHEMA_NAME}";')

            for table_name, exists in source_tables.items():
                if not exists:
                    print(f"  Skipping {table_name:<16} (missing in staging)")

            for stmt in build_ddl(source_tables, col_map):
                cur.execute(stmt)

            for stmt in build_inserts(source_tables, col_map):
                cur.execute(stmt)
                print(f"  inserted → {stmt.split('INTO')[1].split()[0]}")

        conn.commit()

        for stmt in build_constraints(source_tables):
            constraint = stmt.split("CONSTRAINT")[1].split("FOREIGN")[0].strip()
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(stmt)
            except Exception as exc:
                print(f"  FK warning ({constraint}): {exc}")

    print(f"Done — core load complete for '{cfg['dbname']}'")


if __name__ == "__main__":
    main()
