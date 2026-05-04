CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.stations (
    station_id text PRIMARY KEY,
    station_name text NOT NULL,
    station_lat numeric,
    station_lon numeric,
    parent_station text,
    platform_count integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS core.platforms (
    platform_id text PRIMARY KEY,
    station_id text NOT NULL,
    platform_name text,
    platform_code text,
    platform_lat numeric,
    platform_lon numeric,
    location_type text,
    FOREIGN KEY (station_id) REFERENCES core.stations(station_id)
);

CREATE TABLE IF NOT EXISTS core.routes (
    route_id text PRIMARY KEY,
    route_short_name text,
    route_long_name text,
    route_type text,
    route_color text,
    route_text_color text
);

CREATE TABLE IF NOT EXISTS core.trip_stop_map (
    trip_id text NOT NULL,
    route_id text,
    stop_id text NOT NULL,
    stop_sequence integer NOT NULL,
    arrival_time text,
    departure_time text,
    shape_id text,
    PRIMARY KEY (trip_id, stop_sequence),
    FOREIGN KEY (route_id) REFERENCES core.routes(route_id),
    FOREIGN KEY (stop_id) REFERENCES core.platforms(platform_id)
);

CREATE INDEX IF NOT EXISTS idx_trip_stop_map_stop_id ON core.trip_stop_map(stop_id);
CREATE INDEX IF NOT EXISTS idx_trip_stop_map_route_id ON core.trip_stop_map(route_id);
CREATE INDEX IF NOT EXISTS idx_platforms_station_id ON core.platforms(station_id);
