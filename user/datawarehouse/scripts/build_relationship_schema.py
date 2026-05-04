from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_NAME = "relationship"
SOURCE_SCHEMA = os.getenv("SOURCE_SCHEMA")

load_dotenv(ROOT / ".env")

CORE_TABLES = ["agency", "stops", "routes", "trips", "stop_times", "calendar", "calendar_dates", "shapes", "notes"]


def db_config() -> dict[str, object]:
    return {
        "host": os.getenv("POSTGRES_CONN_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "dbname": os.getenv("POSTGRES_DB"),
    }


def qname(table: str) -> str:
    return f'"{SCHEMA_NAME}"."{table}"'


def source_table_name(schema_name: str, base_name: str) -> str:
    return f"gtfs_{base_name}" if schema_name == "staging" else base_name


def source_qname(schema_name: str, base_name: str) -> str:
    return f'"{schema_name}"."{source_table_name(schema_name, base_name)}"'


def table_exists(conn: psycopg.Connection, schema_name: str, base_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (source_qname(schema_name, base_name),))
        return cur.fetchone()[0] is not None


def column_exists(conn: psycopg.Connection, schema_name: str, base_name: str, column_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND column_name = %s
            LIMIT 1
            """,
            (schema_name, source_table_name(schema_name, base_name), column_name),
        )
        return cur.fetchone() is not None


def detect_source_schema(conn: psycopg.Connection) -> str:
    schema_candidates = [SOURCE_SCHEMA] if SOURCE_SCHEMA else ["raw", "staging"]
    for schema_name in schema_candidates:
        if schema_name and all(table_exists(conn, schema_name, table_name) for table_name in CORE_TABLES):
            return schema_name
    raise RuntimeError("Could not find a GTFS source schema with the required core tables in raw or staging.")


def text_expr(column: str) -> str:
    return f"NULLIF(BTRIM({column}), '')"


def text_expr_source(column: str) -> str:
    return f"NULLIF(({column})::text, '')"


def smallint_expr(column: str) -> str:
    return f"NULLIF(BTRIM({column}), '')::smallint"


def smallint_expr_source(column: str) -> str:
    return f"NULLIF(({column})::text, '')::smallint"


def integer_expr_source(column: str) -> str:
    return f"NULLIF(({column})::text, '')::integer"


def numeric_expr_source(column: str) -> str:
    return f"NULLIF(({column})::text, '')::numeric"


def date_expr(column: str) -> str:
    return f"CASE WHEN NULLIF(BTRIM({column}), '') IS NULL THEN NULL ELSE to_date(BTRIM({column}), 'YYYYMMDD') END"


def date_expr_source(column: str) -> str:
    return f"CASE WHEN NULLIF(({column})::text, '') IS NULL THEN NULL ELSE to_date(({column})::text, 'YYYYMMDD') END"


def build_table_ddl(include_levels: bool, include_pathways: bool, include_route_exact_times: bool, include_stop_level_id: bool) -> list[str]:
    routes_columns = """
        route_id text PRIMARY KEY,
        agency_id text,
        route_short_name text,
        route_long_name text,
        route_desc text,
        route_type integer,
        route_color text,
        route_text_color text
    """
    if include_route_exact_times:
        routes_columns = routes_columns + ",\n        exact_times smallint"

    stops_columns = """
        stop_id text PRIMARY KEY,
        stop_code text,
        stop_name text,
        stop_lat numeric,
        stop_lon numeric,
        location_type smallint,
        parent_station text,
        wheelchair_boarding smallint,
        platform_code text
    """
    if include_stop_level_id:
        stops_columns = stops_columns.replace("platform_code text", "level_id text,\n        platform_code text")

    ddl = [
        f"""
        CREATE TABLE {qname('agency')} (
            agency_id text PRIMARY KEY,
            agency_name text,
            agency_url text,
            agency_timezone text,
            agency_lang text,
            agency_phone text
        );
        """,
        f"""
        CREATE TABLE {qname('notes')} (
            note_id text PRIMARY KEY,
            note_text text
        );
        """,
        f"""
        CREATE TABLE {qname('calendar')} (
            service_id text PRIMARY KEY,
            monday smallint,
            tuesday smallint,
            wednesday smallint,
            thursday smallint,
            friday smallint,
            saturday smallint,
            sunday smallint,
            start_date date,
            end_date date
        );
        """,
        f"""
        CREATE TABLE {qname('stops')} (
            {stops_columns}
        );
        """,
        f"""
        CREATE TABLE {qname('routes')} (
            {routes_columns}
        );
        """,
        f"""
        CREATE TABLE {qname('shapes')} (
            shape_id text PRIMARY KEY
        );
        """,
        f"""
        CREATE TABLE {qname('shape_points')} (
            shape_id text NOT NULL,
            shape_pt_lat numeric,
            shape_pt_lon numeric,
            shape_pt_sequence integer NOT NULL,
            shape_dist_traveled numeric,
            PRIMARY KEY (shape_id, shape_pt_sequence)
        );
        """,
        f"""
        CREATE TABLE {qname('trips')} (
            trip_id text PRIMARY KEY,
            route_id text,
            service_id text,
            shape_id text,
            trip_headsign text,
            direction_id smallint,
            block_id text,
            wheelchair_accessible smallint,
            route_direction text,
            trip_note_id text,
            bikes_allowed smallint
        );
        """,
        f"""
        CREATE TABLE {qname('stop_times')} (
            trip_id text NOT NULL,
            arrival_time text,
            departure_time text,
            stop_id text,
            stop_sequence integer NOT NULL,
            stop_headsign text,
            pickup_type smallint,
            drop_off_type smallint,
            shape_dist_traveled numeric,
            timepoint smallint,
            stop_note_id text,
            PRIMARY KEY (trip_id, stop_sequence)
        );
        """,
        f"""
        CREATE TABLE {qname('calendar_dates')} (
            service_id text NOT NULL,
            date date NOT NULL,
            exception_type smallint,
            PRIMARY KEY (service_id, date)
        );
        """,
    ]

    if include_levels:
        ddl.insert(
            2,
            f"""
            CREATE TABLE {qname('levels')} (
                level_id text PRIMARY KEY,
                level_index numeric,
                level_name text
            );
            """,
        )

    if include_pathways:
        ddl.append(
            f"""
            CREATE TABLE {qname('pathways')} (
                pathway_id text PRIMARY KEY,
                from_stop_id text,
                to_stop_id text,
                pathway_mode smallint,
                is_bidirectional smallint,
                traversal_time integer
            );
            """
        )

    return ddl


def build_inserts(
    schema_name: str,
    include_levels: bool,
    include_pathways: bool,
    include_stop_level_id: bool,
    include_route_exact_times: bool,
) -> list[str]:
    agency = source_qname(schema_name, "agency")
    notes = source_qname(schema_name, "notes")
    calendar = source_qname(schema_name, "calendar")
    stops = source_qname(schema_name, "stops")
    routes = source_qname(schema_name, "routes")
    shapes = source_qname(schema_name, "shapes")
    trips = source_qname(schema_name, "trips")
    stop_times = source_qname(schema_name, "stop_times")
    calendar_dates = source_qname(schema_name, "calendar_dates")
    levels = source_qname(schema_name, "levels")
    pathways = source_qname(schema_name, "pathways")

    inserts = [
        f"""
        INSERT INTO {qname('agency')} (agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone)
        SELECT
            a.agency_id,
            a.agency_name,
            a.agency_url,
            a.agency_timezone,
            a.agency_lang,
            a.agency_phone
        FROM {agency} AS a;
        """,
        f"""
        INSERT INTO {qname('notes')} (note_id, note_text)
        SELECT n.note_id, n.note_text
        FROM {notes} AS n;
        """,
        f"""
        INSERT INTO {qname('calendar')} (
            service_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date
        )
        SELECT
            c.service_id,
            {smallint_expr('c.monday')},
            {smallint_expr('c.tuesday')},
            {smallint_expr('c.wednesday')},
            {smallint_expr('c.thursday')},
            {smallint_expr('c.friday')},
            {smallint_expr('c.saturday')},
            {smallint_expr('c.sunday')},
            {date_expr('c.start_date')},
            {date_expr('c.end_date')}
        FROM {calendar} AS c;
        """,
    ]

    if include_levels:
        inserts.append(
            f"""
            INSERT INTO {qname('levels')} (level_id, level_index, level_name)
            SELECT
                l.level_id,
                {numeric_expr_source('l.level_index')},
                {text_expr_source('l.level_name')}
            FROM {levels} AS l;
            """
        )

    if include_stop_level_id:
        stops_insert = f"""
        INSERT INTO {qname('stops')} (
            stop_id, stop_code, stop_name, stop_lat, stop_lon, location_type, parent_station, wheelchair_boarding, level_id, platform_code
        )
        SELECT
            s.stop_id,
            {text_expr_source('s.stop_code')},
            {text_expr_source('s.stop_name')},
            {numeric_expr_source('s.stop_lat')},
            {numeric_expr_source('s.stop_lon')},
            {smallint_expr_source('s.location_type')},
            {text_expr_source('s.parent_station')},
            {smallint_expr_source('s.wheelchair_boarding')},
            {text_expr_source('s.level_id')},
            {text_expr_source('s.platform_code')}
        FROM {stops} AS s;
        """
    else:
        stops_insert = f"""
        INSERT INTO {qname('stops')} (
            stop_id, stop_code, stop_name, stop_lat, stop_lon, location_type, parent_station, wheelchair_boarding, platform_code
        )
        SELECT
            s.stop_id,
            {text_expr_source('s.stop_code')},
            {text_expr_source('s.stop_name')},
            {numeric_expr_source('s.stop_lat')},
            {numeric_expr_source('s.stop_lon')},
            {smallint_expr_source('s.location_type')},
            {text_expr_source('s.parent_station')},
            {smallint_expr_source('s.wheelchair_boarding')},
            {text_expr_source('s.platform_code')}
        FROM {stops} AS s;
        """
    inserts.append(stops_insert)

    if include_route_exact_times:
        routes_insert = f"""
        INSERT INTO {qname('routes')} (
            route_id, agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color, exact_times
        )
        SELECT
            r.route_id,
            {text_expr_source('r.agency_id')},
            {text_expr_source('r.route_short_name')},
            {text_expr_source('r.route_long_name')},
            {text_expr_source('r.route_desc')},
            {integer_expr_source('r.route_type')},
            {text_expr_source('r.route_color')},
            {text_expr_source('r.route_text_color')},
            {smallint_expr_source('r.exact_times')}
        FROM {routes} AS r;
        """
    else:
        routes_insert = f"""
        INSERT INTO {qname('routes')} (
            route_id, agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color
        )
        SELECT
            r.route_id,
            {text_expr_source('r.agency_id')},
            {text_expr_source('r.route_short_name')},
            {text_expr_source('r.route_long_name')},
            {text_expr_source('r.route_desc')},
            {integer_expr_source('r.route_type')},
            {text_expr_source('r.route_color')},
            {text_expr_source('r.route_text_color')}
        FROM {routes} AS r;
        """
    inserts.append(routes_insert)

    inserts.extend(
        [
            f"""
            INSERT INTO {qname('shapes')} (shape_id)
            SELECT DISTINCT sh.shape_id
            FROM {shapes} AS sh
            WHERE NULLIF((sh.shape_id)::text, '') IS NOT NULL;
            """,
            f"""
            INSERT INTO {qname('shape_points')} (shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence, shape_dist_traveled)
            SELECT
                sh.shape_id,
                {numeric_expr_source('sh.shape_pt_lat')},
                {numeric_expr_source('sh.shape_pt_lon')},
                {integer_expr_source('sh.shape_pt_sequence')},
                {numeric_expr_source('sh.shape_dist_traveled')}
            FROM {shapes} AS sh;
            """,
            f"""
            INSERT INTO {qname('trips')} (
                trip_id, route_id, service_id, shape_id, trip_headsign, direction_id, block_id, wheelchair_accessible,
                route_direction, trip_note_id, bikes_allowed
            )
            SELECT
                t.trip_id,
                {text_expr_source('t.route_id')},
                {text_expr_source('t.service_id')},
                {text_expr_source('t.shape_id')},
                {text_expr_source('t.trip_headsign')},
                {smallint_expr_source('t.direction_id')},
                {text_expr_source('t.block_id')},
                {smallint_expr_source('t.wheelchair_accessible')},
                {text_expr_source('t.route_direction')},
                {text_expr_source('t.trip_note')},
                {smallint_expr_source('t.bikes_allowed')}
            FROM {trips} AS t;
            """,
            f"""
            INSERT INTO {qname('stop_times')} (
                trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_headsign,
                pickup_type, drop_off_type, shape_dist_traveled, timepoint, stop_note_id
            )
            SELECT
                st.trip_id,
                {text_expr_source('st.arrival_time')},
                {text_expr_source('st.departure_time')},
                {text_expr_source('st.stop_id')},
                {integer_expr_source('st.stop_sequence')},
                {text_expr_source('st.stop_headsign')},
                {smallint_expr_source('st.pickup_type')},
                {smallint_expr_source('st.drop_off_type')},
                {numeric_expr_source('st.shape_dist_traveled')},
                {smallint_expr_source('st.timepoint')},
                {text_expr_source('st.stop_note')}
            FROM {stop_times} AS st;
            """,
            f"""
            INSERT INTO {qname('calendar_dates')} (service_id, date, exception_type)
            SELECT
                cd.service_id,
                {date_expr_source('cd.date')},
                {smallint_expr_source('cd.exception_type')}
            FROM {calendar_dates} AS cd;
            """,
        ]
    )

    if include_pathways:
        inserts.append(
            f"""
            INSERT INTO {qname('pathways')} (
                pathway_id, from_stop_id, to_stop_id, pathway_mode, is_bidirectional, traversal_time
            )
            SELECT
                p.pathway_id,
                {text_expr_source('p.from_stop_id')},
                {text_expr_source('p.to_stop_id')},
                {smallint_expr_source('p.pathway_mode')},
                {smallint_expr_source('p.is_bidirectional')},
                {integer_expr_source('p.traversal_time')}
            FROM {pathways} AS p;
            """
        )

    return inserts


def build_constraints(include_levels: bool, include_pathways: bool, include_stop_level_id: bool) -> list[str]:
    constraints = [
        f"ALTER TABLE {qname('routes')} ADD CONSTRAINT fk_routes_agency FOREIGN KEY (agency_id) REFERENCES {qname('agency')}(agency_id);",
        f"ALTER TABLE {qname('stops')} ADD CONSTRAINT fk_stops_parent_station FOREIGN KEY (parent_station) REFERENCES {qname('stops')}(stop_id);",
        f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_routes FOREIGN KEY (route_id) REFERENCES {qname('routes')}(route_id);",
        f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_calendar FOREIGN KEY (service_id) REFERENCES {qname('calendar')}(service_id);",
        f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_shapes FOREIGN KEY (shape_id) REFERENCES {qname('shapes')}(shape_id);",
        f"ALTER TABLE {qname('trips')} ADD CONSTRAINT fk_trips_notes FOREIGN KEY (trip_note_id) REFERENCES {qname('notes')}(note_id);",
        f"ALTER TABLE {qname('shape_points')} ADD CONSTRAINT fk_shape_points_shapes FOREIGN KEY (shape_id) REFERENCES {qname('shapes')}(shape_id);",
        f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_trips FOREIGN KEY (trip_id) REFERENCES {qname('trips')}(trip_id);",
        f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_stops FOREIGN KEY (stop_id) REFERENCES {qname('stops')}(stop_id);",
        f"ALTER TABLE {qname('stop_times')} ADD CONSTRAINT fk_stop_times_notes FOREIGN KEY (stop_note_id) REFERENCES {qname('notes')}(note_id);",
        f"ALTER TABLE {qname('calendar_dates')} ADD CONSTRAINT fk_calendar_dates_calendar FOREIGN KEY (service_id) REFERENCES {qname('calendar')}(service_id);",
    ]

    if include_levels and include_stop_level_id:
        constraints.append(f"ALTER TABLE {qname('stops')} ADD CONSTRAINT fk_stops_level FOREIGN KEY (level_id) REFERENCES {qname('levels')}(level_id);")

    if include_pathways:
        constraints.extend(
            [
                f"ALTER TABLE {qname('pathways')} ADD CONSTRAINT fk_pathways_from_stop FOREIGN KEY (from_stop_id) REFERENCES {qname('stops')}(stop_id);",
                f"ALTER TABLE {qname('pathways')} ADD CONSTRAINT fk_pathways_to_stop FOREIGN KEY (to_stop_id) REFERENCES {qname('stops')}(stop_id);",
            ]
        )

    return constraints


def main() -> None:
    with psycopg.connect(**db_config()) as conn:
        source_schema = detect_source_schema(conn)
        include_levels = table_exists(conn, source_schema, "levels")
        include_pathways = table_exists(conn, source_schema, "pathways")
        include_stop_level_id = column_exists(conn, source_schema, "stops", "level_id")
        include_route_exact_times = column_exists(conn, source_schema, "routes", "exact_times")

        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA_NAME}" CASCADE;')
            cur.execute(f'CREATE SCHEMA "{SCHEMA_NAME}";')
            for statement in build_table_ddl(include_levels, include_pathways, include_route_exact_times, include_stop_level_id):
                cur.execute(statement)
            for statement in build_inserts(source_schema, include_levels, include_pathways, include_stop_level_id, include_route_exact_times):
                cur.execute(statement)
        conn.commit()

        for statement in build_constraints(include_levels, include_pathways, include_stop_level_id):
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(statement)
            except Exception as exc:
                print("FK warning:", exc)

    print(f"Built {SCHEMA_NAME} schema from {source_schema} data")


if __name__ == "__main__":
    main()
