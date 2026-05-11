-- Real-Time Transport Database Reference
-- SQLite schema for storing fresh GTFS real-time data

-- ============================================
-- ALERTS TABLE
-- ============================================
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,              -- metro_<alert_id>
    transport_type TEXT NOT NULL,     -- metro, buses, sydneytrains
    entity_id TEXT,                   -- UUID from feed
    cause TEXT,                       -- MAINTENANCE, INCIDENT, etc.
    effect TEXT,                      -- MODIFIED_SERVICE, SERVICE_CHANGE, etc.
    header_text TEXT,                 -- Short alert message
    description_text TEXT,            -- Full alert description
    active_start INTEGER,             -- Unix timestamp when alert starts
    active_end INTEGER,               -- Unix timestamp when alert ends
    route_ids TEXT,                   -- Pipe-separated (SMNW_M1|SMNW_M2)
    agency_id TEXT,                   -- SMNW, etc.
    timestamp INTEGER NOT NULL,       -- When feed was generated
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Example Query:
-- SELECT header_text, route_ids, active_start, active_end
-- FROM alerts WHERE transport_type = 'metro' ORDER BY timestamp DESC;

-- ============================================
-- VEHICLE_POSITIONS TABLE
-- ============================================
CREATE TABLE vehicle_positions (
    id TEXT PRIMARY KEY,              -- metro_<entity_id>/<vehicle_id>
    transport_type TEXT NOT NULL,     -- metro, buses, sydneytrains
    vehicle_id TEXT,                  -- RS037, etc.
    trip_id TEXT,                     -- 0215-003-115-017:1000
    route_id TEXT,                    -- SMNW_M1
    direction_id INTEGER,             -- 0 or 1
    latitude REAL,                    -- -33.71057
    longitude REAL,                   -- 150.93367
    bearing REAL,                     -- 333.21 degrees
    speed REAL,                       -- km/h
    current_stop_sequence INTEGER,    -- Stop sequence in trip
    current_status TEXT,              -- IN_TRANSIT_TO, STOPPED_AT
    occupancy_status TEXT,            -- MANY_SEATS_AVAILABLE, FEW_SEATS_AVAILABLE
    congestion_level TEXT,            -- RUNNING_SMOOTHLY, SEVERE_CONGESTION
    timestamp INTEGER NOT NULL,       -- When feed was generated
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries:
CREATE INDEX idx_positions_transport ON vehicle_positions(transport_type);
CREATE INDEX idx_positions_vehicle ON vehicle_positions(vehicle_id);
CREATE INDEX idx_positions_route ON vehicle_positions(route_id);

-- Example Queries:
-- Get all vehicles currently in transit
-- SELECT vehicle_id, speed, latitude, longitude 
-- FROM vehicle_positions WHERE current_status = 'IN_TRANSIT_TO';

-- Get vehicles on a specific route
-- SELECT vehicle_id, occupancy_status, speed
-- FROM vehicle_positions WHERE route_id = 'SMNW_M1' ORDER BY vehicle_id;

-- Get latest positions (always fresh)
-- SELECT * FROM vehicle_positions WHERE transport_type = 'metro' 
-- ORDER BY updated_at DESC LIMIT 10;

-- ============================================
-- TRIP_UPDATES TABLE
-- ============================================
CREATE TABLE trip_updates (
    id TEXT PRIMARY KEY,              -- metro_<entity_id>
    transport_type TEXT NOT NULL,     -- metro, buses, sydneytrains
    trip_id TEXT,                     -- 0215-003-115-017:1000
    route_id TEXT,                    -- SMNW_M1
    direction_id INTEGER,             -- 0 or 1
    vehicle_id TEXT,                  -- Which vehicle serving this trip
    schedule_relationship TEXT,       -- SCHEDULED, ADDED, CANCELED
    current_stop_sequence INTEGER,    -- Next stop to serve
    current_status TEXT,              -- IN_TRANSIT, STOPPED, etc.
    timestamp INTEGER NOT NULL,       -- When feed was generated
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes:
CREATE INDEX idx_updates_transport ON trip_updates(transport_type);
CREATE INDEX idx_updates_trip ON trip_updates(trip_id);
CREATE INDEX idx_updates_vehicle ON trip_updates(vehicle_id);

-- Example Queries:
-- Get canceled trips
-- SELECT trip_id, route_id FROM trip_updates 
-- WHERE schedule_relationship = 'CANCELED';

-- Get which vehicle is assigned to a trip
-- SELECT vehicle_id, current_stop_sequence FROM trip_updates 
-- WHERE trip_id = '0215-003-115-017:1000';

-- ============================================
-- USEFUL ANALYTICS QUERIES
-- ============================================

-- 1. How many vehicles are currently running?
SELECT COUNT(DISTINCT vehicle_id) as active_vehicles
FROM vehicle_positions WHERE transport_type = 'metro';

-- 2. Average occupancy by route
SELECT route_id, occupancy_status, COUNT(*) as vehicles
FROM vehicle_positions WHERE transport_type = 'metro'
GROUP BY route_id, occupancy_status;

-- 3. Routes with congestion
SELECT route_id, COUNT(*) as congested_vehicles
FROM vehicle_positions 
WHERE transport_type = 'metro' AND congestion_level = 'SEVERE_CONGESTION'
GROUP BY route_id ORDER BY congested_vehicles DESC;

-- 4. Average speed by route
SELECT route_id, AVG(speed) as avg_speed, MAX(speed) as max_speed
FROM vehicle_positions WHERE transport_type = 'metro'
GROUP BY route_id ORDER BY avg_speed DESC;

-- 5. Data freshness (how recent is position data?)
SELECT transport_type, 
       COUNT(*) as total_vehicles,
       MAX(timestamp) as latest_timestamp,
       DATETIME('now', '-' || (CAST((strftime('%s', 'now') - MAX(timestamp)) AS INTEGER)) || ' seconds') as age
FROM vehicle_positions
GROUP BY transport_type;

-- 6. Alert timeline
SELECT timestamp, header_text, route_ids, cause, effect
FROM alerts WHERE transport_type = 'metro'
ORDER BY timestamp DESC LIMIT 20;

-- 7. Vehicle movement (position history for one vehicle)
SELECT * FROM vehicle_positions 
WHERE vehicle_id = 'RS037' AND transport_type = 'metro'
ORDER BY timestamp DESC LIMIT 10;

-- ============================================
-- DATA CLEANUP & MAINTENANCE
-- ============================================

-- Remove alerts older than 30 days
-- DELETE FROM alerts WHERE timestamp < (strftime('%s', 'now') - 2592000);

-- Remove old vehicle positions (keep only last 7 days)
-- DELETE FROM vehicle_positions WHERE timestamp < (strftime('%s', 'now') - 604800);

-- Check database size
-- PRAGMA database_list;
-- SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();

-- Get table sizes
-- SELECT name, count(*) FROM sqlite_master WHERE type='table' GROUP BY name;

-- Optimize database (run periodically)
-- VACUUM;
-- ANALYZE;
