-- CREATE SCHEMA IF NOT EXISTS realationship;
-- SET search_path TO realationship;

-- CREATE TABLE agency (
--     agency_id TEXT PRIMARY KEY,
--     agency_name TEXT,
--     agency_url TEXT,
--     agency_timezone TEXT,
--     agency_lang TEXT,
--     agency_phone TEXT
-- );

-- CREATE TABLE routes (
--     route_id TEXT PRIMARY KEY,
--     agency_id TEXT REFERENCES agency(agency_id),
--     route_short_name TEXT,
--     route_long_name TEXT,
--     route_desc TEXT,
--     route_type INT,
--     route_colour TEXT,
--     route_text_colour TEXT
-- );

-- CREATE TABLE calendar (
--     service_id TEXT PRIMARY KEY,
--     monday INT,CREATE TABLE stops (
--     stop_id TEXT PRIMARY KEY,
--     stop_name TEXT,
--     stop_lat NUMERIC(10,6),
--     stop_lon NUMERIC(10,6),
--     location_type INT,
--     parent_station TEXT,
--     wheelchair_boarding INT
-- );CREATE TABLE calendar (
--     service_id TEXT PRIMARY KEY,
--     monday INT,
--     tuesday INT,
--     wednesday INT,
--     thursday INT,
--     friday INT,
--     saturday INT,
--     sunday INT,
--     start_date DATE,
--     end_date DATE
-- );
--     tuesday INT,
--     wednesday INT,
--     thursday INT,
--     friday INT,
--     saturday INT,
--     sunday INT,
--     start_date DATE,
--     end_date DATE
-- );

-- CREATE TABLE calendar_dates (
--     service_id TEXT REFERENCES calendar(service_id),
--     date DATE,
--     exception_type SMALLINT,
--     PRIMARY KEY (service_id, date)
-- );

-- CREATE TABLE stops (
--     stop_id TEXT PRIMARY KEY,
--     stop_name TEXT,
--     stop_lat NUMERIC(10,6),
--     stop_lon NUMERIC(10,6),
--     location_type INT,
--     parent_station TEXT,
--     wheelchair_boarding INT
-- );

-- CREATE TABLE notes (
--     note_id TEXT PRIMARY KEY,
--     note_text TEXT
-- );

-- CREATE TABLE trips (
--     trip_id TEXT PRIMARY KEY,
--     route_id TEXT REFERENCES routes(route_id),
--     service_id TEXT REFERENCES calendar(service_id),
--     trip_headsign TEXT,
--     direction_id SMALLINT,
--     shape_id TEXT,
--     wheelchair_accessible SMALLINT,
--     trip_note_id TEXT REFERENCES notes(note_id),
--     route_direction TEXT
-- );

-- CREATE TABLE shapes (
--     shape_id TEXT,
--     shape_pt_lat NUMERIC(10,6),
--     shape_pt_lon NUMERIC(10,6),
--     shape_pt_sequence INT,
--     shape_dist_traveled NUMERIC,
--     PRIMARY KEY (shape_id, shape_pt_sequence)
-- );

-- CREATE TABLE stop_times (
--     trip_id TEXT REFERENCES trips(trip_id),
--     arrival_time TEXT,
--     departure_time TEXT,
--     stop_id TEXT REFERENCES stops(stop_id),
--     stop_sequence INT,
--     stop_headsign TEXT,
--     pickup_type SMALLINT,
--     drop_off_type SMALLINT,
--     shape_distance_traveled NUMERIC,
--     timepoint SMALLINT,
--     stop_note_id TEXT REFERENCES notes(note_id),
--     PRIMARY KEY (trip_id, stop_sequence)
-- );


-- COPY agency
-- FROM 'C:\Users\Public\transport\gtfs_data\agency.txt'
-- DELIMITER ','
-- CSV HEADER;

-- COPY calendar
-- FROM 'C:\Users\Public\transport\gtfs_data\calendar.txt'
-- DELIMITER ','
-- CSV HEADER;

-- COPY calendar_dates
-- FROM 'C:\Users\Public\transport\gtfs_data\calendar_dates.txt'
-- DELIMITER ','
-- CSV HEADER;

-- COPY notes
-- FROM 'C:\Users\Public\transport\gtfs_data\notes.txt'
-- DELIMITER ','
-- CSV HEADER;


-- DROP TABLE IF EXISTS routes CASCADE;

-- CREATE TABLE routes (
--     route_id TEXT PRIMARY KEY,
--     agency_id TEXT REFERENCES agency(agency_id),
--     route_short_name TEXT,
--     route_long_name TEXT,
--     route_desc TEXT,
--     route_type INT,
--     route_color TEXT,
--     route_text_color TEXT,
--     exact_times SMALLINT
-- );

-- COPY routes
-- FROM 'C:\Users\Public\transport\gtfs_data\routes.txt'
-- DELIMITER ','
-- CSV HEADER;
-- DROP TABLE IF EXISTS stops CASCADE;

-- CREATE TABLE stops (
--     stop_id TEXT PRIMARY KEY,
--     stop_code TEXT,
--     stop_name TEXT NOT NULL,
--     stop_lat NUMERIC(10,6),
--     stop_lon NUMERIC(10,6),
--     location_type SMALLINT,
--     parent_station TEXT REFERENCES stops(stop_id),
--     wheelchair_boarding SMALLINT,
--     level_id TEXT,
--     platform_code TEXT
-- );


-- copy stops
-- FROM 'C:\Users\Public\transport\gtfs_data\stops.txt'
-- DELIMITER ','
-- CSV HEADER
-- NULL '';

-- ALTER TABLE stops
-- ADD CONSTRAINT fk_parent_station
-- FOREIGN KEY (parent_station)
-- REFERENCES stops(stop_id);

-- COPY trips
-- FROM 'C:\Users\Public\transport\gtfs_data\trips.txt'
-- DELIMITER ','
-- CSV HEADER;

-- COPY shapes
-- FROM 'C:\Users\Public\transport\gtfs_data\shapes.txt'
-- DELIMITER ','
-- CSV HEADER;

-- COPY stop_times
-- FROM 'C:\Users\Public\transport\gtfs_data\stop_times.txt'
-- DELIMITER ','
-- CSV HEADER;

-- verify counts
SELECT 'agency', count(*) FROM raw.agency;
SELECT 'routes', count(*) FROM raw.routes;
-- check duplicates on referenced columns
SELECT agency_id, count(*) FROM raw.agency GROUP BY agency_id HAVING count(*)>1 LIMIT 20;
SELECT route_id, count(*) FROM raw.routes GROUP BY route_id HAVING count(*)>1 LIMIT 20;
SELECT trip_id, count(*) FROM raw.trips GROUP BY trip_id HAVING count(*)>1 LIMIT 20;
SELECT stop_id, count(*) FROM raw.stops GROUP BY stop_id HAVING count(*)>1 LIMIT 20;
SELECT service_id, count(*) FROM raw.calendar GROUP BY service_id HAVING count(*)>1 LIMIT 20;