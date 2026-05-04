CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.gtfs_agency (
    agency_id text,
    agency_name text,
    agency_url text,
    agency_timezone text,
    agency_lang text,
    agency_phone text,
    agency_fare_url text,
    agency_email text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_stops (
    stop_id text,
    stop_code text,
    stop_name text,
    stop_desc text,
    stop_lat numeric,
    stop_lon numeric,
    zone_id text,
    stop_url text,
    location_type text,
    parent_station text,
    stop_timezone text,
    wheelchair_boarding text,
    platform_code text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_routes (
    route_id text,
    agency_id text,
    route_short_name text,
    route_long_name text,
    route_desc text,
    route_type text,
    route_url text,
    route_color text,
    route_text_color text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_trips (
    route_id text,
    service_id text,
    trip_id text,
    trip_headsign text,
    trip_short_name text,
    direction_id text,
    block_id text,
    shape_id text,
    wheelchair_accessible text,
    bikes_allowed text,
    route_direction text,
    trip_note text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_stop_times (
    trip_id text,
    arrival_time text,
    departure_time text,
    stop_id text,
    stop_sequence text,
    stop_headsign text,
    pickup_type text,
    drop_off_type text,
    shape_dist_traveled text,
    timepoint text,
    stop_note text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_calendar (
    service_id text,
    monday text,
    tuesday text,
    wednesday text,
    thursday text,
    friday text,
    saturday text,
    sunday text,
    start_date text,
    end_date text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_calendar_dates (
    service_id text,
    date text,
    exception_type text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_levels (
    level_id text,
    level_index text,
    level_name text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_shapes (
    shape_id text,
    shape_pt_lat text,
    shape_pt_lon text,
    shape_pt_sequence text,
    shape_dist_traveled text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_notes (
    note_id text,
    note_text text
);

CREATE TABLE IF NOT EXISTS staging.gtfs_pathways (
    pathway_id text,
    from_stop_id text,
    to_stop_id text,
    pathway_mode text,
    is_bidirectional text,
    traversal_time text
);
