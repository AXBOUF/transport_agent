"""
Sydney Trains Real-Time Data Schema
Separate database for Sydney Trains real-time feeds
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "realtime_data_sydneytrains.db"

def init_db():
    """Initialize database schema for Sydney Trains"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Alerts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            transport_type TEXT NOT NULL,
            entity_id TEXT,
            cause TEXT,
            effect TEXT,
            header_text TEXT,
            description_text TEXT,
            active_start INTEGER,
            active_end INTEGER,
            route_ids TEXT,
            agency_id TEXT,
            timestamp INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Vehicle positions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vehicle_positions (
            id TEXT PRIMARY KEY,
            transport_type TEXT NOT NULL,
            vehicle_id TEXT,
            trip_id TEXT,
            route_id TEXT,
            direction_id INTEGER,
            latitude REAL,
            longitude REAL,
            bearing REAL,
            speed REAL,
            current_stop_sequence INTEGER,
            current_status TEXT,
            stop_id TEXT,
            occupancy_status TEXT,
            congestion_level TEXT,
            timestamp INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Trip updates table
    c.execute('''
        CREATE TABLE IF NOT EXISTS trip_updates (
            id TEXT PRIMARY KEY,
            transport_type TEXT NOT NULL,
            trip_id TEXT,
            route_id TEXT,
            direction_id INTEGER,
            vehicle_id TEXT,
            schedule_relationship TEXT,
            current_stop_sequence INTEGER,
            current_status TEXT,
            timestamp INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Indexes for better query performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_alerts_transport ON alerts(transport_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_positions_transport ON vehicle_positions(transport_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_positions_vehicle ON vehicle_positions(vehicle_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_updates_transport ON trip_updates(transport_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_updates_trip ON trip_updates(trip_id)')
    
    conn.commit()
    conn.close()
    print(f"✅ Sydney Trains database initialized at {DB_PATH}")

def get_connection():
    """Get database connection for Sydney Trains"""
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    init_db()
