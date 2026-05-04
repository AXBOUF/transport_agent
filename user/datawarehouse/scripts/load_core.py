from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_NAME = "core"
SOURCE_SCHEMA = "staging"


def db_config() -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_DB", "transport"),
    }


def qname(table: str) -> str:
    return f'"{SCHEMA_NAME}"."{table}"'


def src(table: str) -> str:
    return f'"{SOURCE_SCHEMA}"."{table}"'


def table_exists(cur: psycopg.Cursor, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"{SOURCE_SCHEMA}.{table}",))
    return cur.fetchone()[0] is not None


def column_exists(cur: psycopg.Cursor, table: str, column: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema=%s AND table_name=%s AND column_name=%s",
        (SOURCE_SCHEMA, table, column),
    )
    return cur.fetchone() is not None


# ── Type cast helpers ──────────────────────────────────────────────────────────

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


# ── DDL ───────────────────────────────────────────────────────────────────────

def build_ddl(has_levels: bool, has_pathways: bool, has_level_id: bool, has_exact_times: bool) -> list[str]:
    stops_extra = ",\n        level_id text" if has_level_id else ""
    routes_extra = ",\n        exact_times smallint" if has_exact_times else ""

    ddl = [
        f"""CREATE TABLE {qname('agency')} (
            agency_id text PRIMARY KEY, agency_name text, agency_url text,
            agency_timezone text, agency_lang text, agency_phone text);""",
        f"""CREATE TABLE {qname('notes')} (
            note_id text PRIMARY KEY, note_text text);""",
        f"""CREATE TABLE {qname('calendar')} (
            service_id text PRIMARY KEY,
            monday smallint, tuesday smallint, wednesday smallint, thursday smallint,
            friday smallint, saturday smallint, sunday smallint,
            start_date date, end_date date);""",
        f"""CREATE TABLE {qname('stops')} (
            stop_id text PRIMARY KEY, stop_code text, stop_name text,
            stop_lat numeric, stop_lon numeric, location_type smallint,
            parent_station text, wheelchair_boarding smallint{stops_extra},
            platform_code text);""",
        f"""CREATE TABLE {qname('routes')} (
            route_id text PRIMARY KEY, agency_id text,
            route_short_name text, route_long_name text, route_desc text,
            route_type integer, route_color text, route_text_color text{routes_extra});""",
        f"""CREATE TABLE {qname('shapes')} (
            shape_id text PRIMARY KEY);""",
        f"""CREATE TABLE {qname('shape_points')} (
            shape_id text NOT NULL, shape_pt_lat numeric, shape_pt_lon numeric,
            shape_pt_sequence integer NOT NULL, shape_dist_traveled numeric,
            PRIMARY KEY (shape_id, shape_pt_sequence));""",
        f"""CREATE TABLE {qname('trips')} (
            trip_id text PRIMARY KEY, route_id text, service_id text, shape_id text,
            trip_headsign text, direction_id smallint, block_id text,
            wheelchair_accessible smallint, route_direction text,
            trip_note_id text, bikes_allowed smallint);""",
        f"""CREATE TABLE {qname('stop_times')} (
            trip_id text NOT NULL, arrival_time text, departure_time text,
            stop_id text, stop_sequence integer NOT NULL, stop_headsign text,
            pickup_type smallint, drop_off_type smallint,
            shape_dist_traveled numeric, timepoint smallint, stop_note_id text,
            PRIMARY KEY (trip_id, stop_sequence));""",
        f"""CREATE TABLE {qname('calendar_dates')} (
            service_id text NOT NULL, date date NOT NULL, exception_type smallint,
            PRIMARY KEY (service_id, date));""",
    ]

    if has_levels:
        ddl.insert(2, f"""CREATE TABLE {qname('levels')} (
            level_id text PRIMARY KEY, level_index numeric, level_name text);""")

    if has_pathways:
        ddl.append(f"""CREATE TABLE {qname('pathways')} (
            pathway_id text PRIMARY KEY, from_stop_id text, to_stop_id text,
            pathway_mode smallint, is_bidirectional smallint, traversal_time integer);""")

    return ddl


# ── Inserts ───────────────────────────────────────────────────────────────────

def build_inserts(has_levels: bool, has_pathways: bool, has_level_id: bool, has_exact_times: bool) -> list[str]:
    stops_cols = "stop_id, stop_code, stop_name, stop_lat, stop_lon, location_type, parent_station, wheelchair_boarding, platform_code"
    stops_sel  = f"s.stop_id, {_text('s.stop_code')}, {_text('s.stop_name')}, {_numeric('s.stop_lat')}, {_numeric('s.stop_lon')}, {_smallint('s.location_type')}, {_text('s.parent_station')}, {_smallint('s.wheelchair_boarding')}, {_text('s.platform_code')}"
    if has_level_id:
        stops_cols = stops_cols.replace("platform_code", "level_id, platform_code")
        stops_sel  = stops_sel.replace(f"{_text('s.platform_code')}", f"{_text('s.level_id')}, {_text('s.platform_code')}")

    routes_cols = "route_id, agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color"
    routes_sel  = f"r.route_id, {_text('r.agency_id')}, {_text('r.route_short_name')}, {_text('r.route_long_name')}, {_text('r.route_desc')}, {_integer('r.route_type')}, {_text('r.route_color')}, {_text('r.route_text_color')}"
    if has_exact_times:
        routes_cols += ", exact_times"
        routes_sel  += f", {_smallint('r.exact_times')}"

    inserts = [
        f"INSERT INTO {qname('agency')} SELECT agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone FROM {src('agency')};",
        f"INSERT INTO {qname('notes')} SELECT note_id, note_text FROM {src('notes')};",
        f"""INSERT INTO {qname('calendar')} SELECT service_id,
            {_smallint('monday')}, {_smallint('tuesday')}, {_smallint('wednesday')}, {_smallint('thursday')},
            {_smallint('friday')}, {_smallint('saturday')}, {_smallint('sunday')},
            {_date('start_date')}, {_date('end_date')} FROM {src('calendar')};""",
        f"INSERT INTO {qname('stops')} ({stops_cols}) SELECT {stops_sel} FROM {src('stops')} s;",
        f"INSERT INTO {qname('routes')} ({routes_cols}) SELECT {routes_sel} FROM {src('routes')} r;",
        f"INSERT INTO {qname('shapes')} SELECT DISTINCT shape_id FROM {src('shapes')} WHERE NULLIF(shape_id::text,'') IS NOT NULL;",
        f"""INSERT INTO {qname('shape_points')} SELECT shape_id, {_numeric('shape_pt_lat')}, {_numeric('shape_pt_lon')},
            {_integer('shape_pt_sequence')}, {_numeric('shape_dist_traveled')} FROM {src('shapes')};""",
        f"""INSERT INTO {qname('trips')} SELECT trip_id, {_text('route_id')}, {_text('service_id')}, {_text('shape_id')},
            {_text('trip_headsign')}, {_smallint('direction_id')}, {_text('block_id')},
            {_smallint('wheelchair_accessible')}, {_text('route_direction')}, {_text('trip_note')},
            {_smallint('bikes_allowed')} FROM {src('trips')};""",
        f"""INSERT INTO {qname('stop_times')} SELECT trip_id, {_text('arrival_time')}, {_text('departure_time')},
            {_text('stop_id')}, {_integer('stop_sequence')}, {_text('stop_headsign')},
            {_smallint('pickup_type')}, {_smallint('drop_off_type')}, {_numeric('shape_dist_traveled')},
            {_smallint('timepoint')}, {_text('stop_note')} FROM {src('stop_times')};""",
        f"""INSERT INTO {qname('calendar_dates')} SELECT service_id, {_date('date')}, {_smallint('exception_type')}
            FROM {src('calendar_dates')};""",
    ]

    if has_levels:
        inserts.insert(2, f"""INSERT INTO {qname('levels')} SELECT level_id,
            {_numeric('level_index')}, {_text('level_name')} FROM {src('levels')};""")

    if has_pathways:
        inserts.append(f"""INSERT INTO {qname('pathways')} SELECT pathway_id,
            {_text('from_stop_id')}, {_text('to_stop_id')}, {_smallint('pathway_mode')},
            {_smallint('is_bidirectional')}, {_integer('traversal_time')} FROM {src('pathways')};""")

    return inserts


# ── Constraints ───────────────────────────────────────────────────────────────

def build_constraints(has_levels: bool, has_pathways: bool, has_level_id: bool) -> list[str]:
    fks = [
        f"ALTER TABLE {qname('routes')}         ADD CONSTRAINT fk_routes_agency        FOREIGN KEY (agency_id)       REFERENCES {qname('agency')}(agency_id);",
        f"ALTER TABLE {qname('stops')}          ADD CONSTRAINT fk_stops_parent         FOREIGN KEY (parent_station)  REFERENCES {qname('stops')}(stop_id);",
        f"ALTER TABLE {qname('trips')}          ADD CONSTRAINT fk_trips_routes         FOREIGN KEY (route_id)        REFERENCES {qname('routes')}(route_id);",
        f"ALTER TABLE {qname('trips')}          ADD CONSTRAINT fk_trips_calendar       FOREIGN KEY (service_id)      REFERENCES {qname('calendar')}(service_id);",
        f"ALTER TABLE {qname('trips')}          ADD CONSTRAINT fk_trips_shapes         FOREIGN KEY (shape_id)        REFERENCES {qname('shapes')}(shape_id);",
        f"ALTER TABLE {qname('trips')}          ADD CONSTRAINT fk_trips_notes          FOREIGN KEY (trip_note_id)    REFERENCES {qname('notes')}(note_id);",
        f"ALTER TABLE {qname('shape_points')}   ADD CONSTRAINT fk_shape_points_shapes  FOREIGN KEY (shape_id)        REFERENCES {qname('shapes')}(shape_id);",
        f"ALTER TABLE {qname('stop_times')}     ADD CONSTRAINT fk_stop_times_trips     FOREIGN KEY (trip_id)         REFERENCES {qname('trips')}(trip_id);",
        f"ALTER TABLE {qname('stop_times')}     ADD CONSTRAINT fk_stop_times_stops     FOREIGN KEY (stop_id)         REFERENCES {qname('stops')}(stop_id);",
        f"ALTER TABLE {qname('stop_times')}     ADD CONSTRAINT fk_stop_times_notes     FOREIGN KEY (stop_note_id)    REFERENCES {qname('notes')}(note_id);",
        f"ALTER TABLE {qname('calendar_dates')} ADD CONSTRAINT fk_cal_dates_calendar   FOREIGN KEY (service_id)      REFERENCES {qname('calendar')}(service_id);",
    ]
    if has_levels and has_level_id:
        fks.append(f"ALTER TABLE {qname('stops')} ADD CONSTRAINT fk_stops_level FOREIGN KEY (level_id) REFERENCES {qname('levels')}(level_id);")
    if has_pathways:
        fks += [
            f"ALTER TABLE {qname('pathways')} ADD CONSTRAINT fk_pathways_from FOREIGN KEY (from_stop_id) REFERENCES {qname('stops')}(stop_id);",
            f"ALTER TABLE {qname('pathways')} ADD CONSTRAINT fk_pathways_to   FOREIGN KEY (to_stop_id)   REFERENCES {qname('stops')}(stop_id);",
        ]
    return fks


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    cfg = db_config()
    print(f"Loading staging → core in '{cfg['dbname']}'")

    with psycopg.connect(**cfg) as conn:
        with conn.cursor() as cur:
            has_levels     = table_exists(cur, "levels")
            has_pathways   = table_exists(cur, "pathways")
            has_level_id   = column_exists(cur, "stops", "level_id")
            has_exact_times = column_exists(cur, "routes", "exact_times")

            cur.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA_NAME}" CASCADE;')
            cur.execute(f'CREATE SCHEMA "{SCHEMA_NAME}";')

            for stmt in build_ddl(has_levels, has_pathways, has_level_id, has_exact_times):
                cur.execute(stmt)
            for stmt in build_inserts(has_levels, has_pathways, has_level_id, has_exact_times):
                cur.execute(stmt)
                print(f"  inserted → {stmt.split('INTO')[1].split()[0]}")

        conn.commit()

        for stmt in build_constraints(has_levels, has_pathways, has_level_id):
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
