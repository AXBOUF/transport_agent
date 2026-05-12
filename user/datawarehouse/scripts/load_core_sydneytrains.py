from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_NAME = "core"
SOURCE_SCHEMA = "staging"

load_dotenv(ROOT / ".env")
POSTGRES_DB = os.getenv("POSTGRES_DB_SYDNEYTRAINS", "sydneytrains")


def db_config() -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host":     os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port":     int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user":     os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname":   POSTGRES_DB,
    }


def qname(table: str) -> str:
    return f'"{SCHEMA_NAME}"."{table}"'


def src(table: str) -> str:
    return f'"{SOURCE_SCHEMA}"."{table}"'


def table_exists(cur: psycopg.Cursor, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"{SOURCE_SCHEMA}.{table}",))
    return cur.fetchone()[0] is not None


def get_table_columns(cur: psycopg.Cursor, table: str) -> list[str]:
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
    if col in {"stop_lat", "stop_lon", "shape_pt_lat", "shape_pt_lon", "shape_dist_traveled"}:
        return "numeric"
    if col in {"route_type", "stop_sequence", "shape_pt_sequence", "child_sequence", "grandchild_sequence"}:
        return "integer"
    if col in {
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "location_type", "wheelchair_boarding", "direction_id", "exception_type",
        "pickup_type", "drop_off_type", "timepoint", "wheelchair_accessible", "bikes_allowed",
        "occupancy_status", "exception",
    }:
        return "smallint"
    if col in {"start_date", "end_date", "date"}:
        return "date"
    return "text"


def infer_cast(table: str, col: str) -> str:
    t = infer_core_type(table, col)
    if t == "numeric":   return _numeric(col)
    if t == "smallint":  return _smallint(col)
    if t == "integer":   return _integer(col)
    if t == "date":      return _date(col)
    return _text(col)


def build_ddl(source_tables: dict[str, bool], col_map: dict[str, list[str]]) -> list[str]:
    ddl: list[str] = []

    for table_name, exists in source_tables.items():
        if not exists:
            continue
        cols = col_map.get(table_name, [])
        if not cols:
            continue

        if table_name == "shapes":
            ddl.append(f"CREATE TABLE {qname('shapes')} (shape_id text PRIMARY KEY);")
            ddl.append(f"""CREATE TABLE {qname('shape_points')} (
                shape_id text NOT NULL,
                shape_pt_lat numeric,
                shape_pt_lon numeric,
                shape_pt_sequence integer NOT NULL,
                shape_dist_traveled numeric,
                PRIMARY KEY (shape_id, shape_pt_sequence)
            );""")
            continue

        col_defs = [f'"{col}" {infer_core_type(table_name, col)}' for col in cols]

        # composite PKs
        if table_name == "stop_times":
            col_defs.append('PRIMARY KEY ("trip_id", "stop_sequence")')
        elif table_name == "calendar_dates":
            col_defs.append('PRIMARY KEY ("service_id", "date")')
        elif table_name == "vehicle_boardings":
            col_defs.append('PRIMARY KEY ("vehicle_category_id", "child_sequence", "boarding_area_id")')
        elif table_name == "vehicle_couplings":
            col_defs.append('PRIMARY KEY ("parent_id", "child_id", "child_sequence")')
        elif table_name == "occupancies":
            col_defs.append('PRIMARY KEY ("trip_id", "stop_sequence", "start_date")')
        else:
            pk = {
                "agency": "agency_id", "stops": "stop_id", "routes": "route_id",
                "trips": "trip_id", "calendar": "service_id", "notes": "note_id",
                "vehicle_categories": "vehicle_category_id",
            }.get(table_name)
            if pk and pk in cols:
                col_defs.append(f'PRIMARY KEY ("{pk}")')

        ddl.append(f"CREATE TABLE {qname(table_name)} ({', '.join(col_defs)});")

    return ddl


def build_inserts(source_tables: dict[str, bool], col_map: dict[str, list[str]]) -> list[str]:
    inserts: list[str] = []

    for table_name, exists in source_tables.items():
        if not exists:
            continue
        cols = col_map.get(table_name, [])
        if not cols:
            continue

        if table_name == "shapes":
            inserts.append(
                f"INSERT INTO {qname('shapes')} SELECT DISTINCT shape_id FROM {src('shapes')} WHERE NULLIF(shape_id::text,'') IS NOT NULL;"
            )
            if "shape_pt_lat" in cols:
                inserts.append(
                    f"INSERT INTO {qname('shape_points')} SELECT shape_id, {_numeric('shape_pt_lat')}, {_numeric('shape_pt_lon')}, {_integer('shape_pt_sequence')}, {_numeric('shape_dist_traveled')} FROM {src('shapes')};"
                )
            continue

        selects = []
        for col in cols:
            expr = infer_cast(table_name, col).replace(f"({col})", f"(x.{col})")
            selects.append(expr)

        col_list = ", ".join(f'"{col}"' for col in cols)
        inserts.append(
            f"INSERT INTO {qname(table_name)} ({col_list}) SELECT {', '.join(selects)} FROM {src(table_name)} x;"
        )

    return inserts


def build_constraints(source_tables: dict[str, bool]) -> list[str]:
    fks: list[str] = []

    if source_tables.get("routes") and source_tables.get("agency"):
        fks.append(f"ALTER TABLE {qname('routes')} ADD CONSTRAINT fk_routes_agency FOREIGN KEY (agency_id) REFERENCES {qname('agency')}(agency_id);")

    if source_tables.get("stops"):
        fks.append(f"ALTER TABLE {qname('stops')} ADD CONSTRAINT fk_stops_parent FOREIGN KEY (parent_station) REFERENCES {qname('stops')}(stop_id);")

    if source_tables.get("trips"):
        if source_tables.get("routes"):
            fks.append(f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_routes FOREIGN KEY (route_id) REFERENCES {qname('routes')}(route_id);")
        if source_tables.get("calendar"):
            fks.append(f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_calendar FOREIGN KEY (service_id) REFERENCES {qname('calendar')}(service_id);")
        if source_tables.get("shapes"):
            fks.append(f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_shapes FOREIGN KEY (shape_id) REFERENCES {qname('shapes')}(shape_id);")
        if source_tables.get("vehicle_categories"):
            fks.append(f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_vehicle_category FOREIGN KEY (vehicle_category_id) REFERENCES {qname('vehicle_categories')}(vehicle_category_id);")

    if source_tables.get("shapes"):
        fks.append(f"ALTER TABLE {qname('shape_points')} ADD CONSTRAINT fk_shape_points_shapes FOREIGN KEY (shape_id) REFERENCES {qname('shapes')}(shape_id);")

    if source_tables.get("stop_times"):
        if source_tables.get("trips"):
            fks.append(f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_trips FOREIGN KEY (trip_id) REFERENCES {qname('trips')}(trip_id);")
        if source_tables.get("stops"):
            fks.append(f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_stops FOREIGN KEY (stop_id) REFERENCES {qname('stops')}(stop_id);")

    if source_tables.get("calendar_dates") and source_tables.get("calendar"):
        fks.append(f"ALTER TABLE {qname('calendar_dates')} ADD CONSTRAINT fk_cal_dates_calendar FOREIGN KEY (service_id) REFERENCES {qname('calendar')}(service_id);")

    if source_tables.get("vehicle_boardings") and source_tables.get("vehicle_categories"):
        fks.append(f"ALTER TABLE {qname('vehicle_boardings')} ADD CONSTRAINT fk_boardings_category FOREIGN KEY (vehicle_category_id) REFERENCES {qname('vehicle_categories')}(vehicle_category_id);")

    if source_tables.get("vehicle_couplings") and source_tables.get("vehicle_categories"):
        fks.append(f"ALTER TABLE {qname('vehicle_couplings')} ADD CONSTRAINT fk_couplings_category FOREIGN KEY (parent_id) REFERENCES {qname('vehicle_categories')}(vehicle_category_id);")

    if source_tables.get("occupancies") and source_tables.get("trips"):
        fks.append(f"ALTER TABLE {qname('occupancies')} ADD CONSTRAINT fk_occupancies_trips FOREIGN KEY (trip_id) REFERENCES {qname('trips')}(trip_id);")

    return fks


def main() -> None:
    cfg = db_config()
    print(f"Loading staging → core in '{cfg['dbname']}'")

    with psycopg.connect(**cfg) as conn:
        with conn.cursor() as cur:
            source_tables = {t: table_exists(cur, t) for t in [
                "agency", "notes", "calendar", "stops", "routes", "shapes",
                "trips", "stop_times", "calendar_dates",
                "vehicle_categories", "vehicle_boardings", "vehicle_couplings", "occupancies",
            ]}
            col_map = {t: get_table_columns(cur, t) for t, exists in source_tables.items() if exists}

            cur.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA_NAME}" CASCADE;')
            cur.execute(f'CREATE SCHEMA "{SCHEMA_NAME}";')

            for t, exists in source_tables.items():
                if not exists:
                    print(f"  Skipping {t:<20} (missing in staging)")

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
