"""
Parser for Sydney Trains GTFS Real-time JSON feeds
Extracts entities and stores in Sydney Trains database
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import get_connection

def parse_alerts(json_file, transport_type):
    """Parse alerts JSON and store in database"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        conn = get_connection()
        c = conn.cursor()
        
        for entity in data.get('entity', []):
            alert = entity.get('alert', {})
            if not alert:
                continue
            
            entity_id = entity.get('id')
            timestamp = int(data.get('header', {}).get('timestamp', 0))
            
            # Get route info from first informed entity
            route_ids = []
            agency_id = None
            for informed_entity in alert.get('informed_entity', []):
                if 'route_id' in informed_entity:
                    route_ids.append(informed_entity['route_id'])
                if 'agency_id' in informed_entity and not agency_id:
                    agency_id = informed_entity['agency_id']
            
            # Get active period
            active_start = None
            active_end = None
            for period in alert.get('active_period', []):
                active_start = int(period.get('start', 0))
                active_end = int(period.get('end', 0))
                break
            
            # Get text translations (first one)
            header_text = None
            description_text = None
            
            if alert.get('header_text'):
                for trans in alert['header_text'].get('translation', []):
                    header_text = trans.get('text')
                    break
            
            if alert.get('description_text'):
                for trans in alert['description_text'].get('translation', []):
                    description_text = trans.get('text')
                    break
            
            cause = alert.get('cause')
            effect = alert.get('effect')
            
            # Insert or update in database
            c.execute('''
                INSERT OR REPLACE INTO alerts 
                (id, transport_type, entity_id, cause, effect, header_text, 
                 description_text, active_start, active_end, route_ids, agency_id, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                f"{transport_type}_{entity_id}",
                transport_type,
                entity_id,
                cause,
                effect,
                header_text,
                description_text,
                active_start,
                active_end,
                '|'.join(route_ids) if route_ids else None,
                agency_id,
                timestamp
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Stored {len(data.get('entity', []))} alerts from {Path(json_file).name}")
        return True
    
    except Exception as e:
        print(f"❌ Error parsing alerts: {e}")
        return False

def parse_vehicle_positions(json_file, transport_type):
    """Parse vehicle positions JSON and store in database"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        conn = get_connection()
        c = conn.cursor()
        
        for entity in data.get('entity', []):
            vehicle_data = entity.get('vehicle', {})
            if not vehicle_data:
                continue
            
            trip = vehicle_data.get('trip', {})
            position = vehicle_data.get('position', {})
            vehicle = vehicle_data.get('vehicle', {})
            
            # Use vehicle_id as stable key, not timestamp-based entity_id
            vehicle_id = vehicle.get('id')
            if not vehicle_id:
                continue
            
            timestamp = int(data.get('header', {}).get('timestamp', 0))
            
            c.execute('''
                INSERT OR REPLACE INTO vehicle_positions
                (id, transport_type, vehicle_id, trip_id, route_id, direction_id,
                 latitude, longitude, bearing, speed, current_stop_sequence,
                 current_status, stop_id, occupancy_status, congestion_level, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                f"{transport_type}_{vehicle_id}",
                transport_type,
                vehicle_id,
                trip.get('trip_id'),
                trip.get('route_id'),
                trip.get('direction_id'),
                position.get('latitude'),
                position.get('longitude'),
                position.get('bearing'),
                position.get('speed'),
                vehicle_data.get('current_stop_sequence'),
                vehicle_data.get('current_status'),
                vehicle_data.get('stop_id'),
                vehicle_data.get('occupancy_status'),
                vehicle_data.get('congestion_level'),
                timestamp
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Stored {len(data.get('entity', []))} vehicle positions from {Path(json_file).name}")
        return True
    
    except Exception as e:
        print(f"❌ Error parsing vehicle positions: {e}")
        return False

def parse_trip_updates(json_file, transport_type):
    """Parse trip updates JSON and store in database"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        conn = get_connection()
        c = conn.cursor()
        
        for entity in data.get('entity', []):
            trip_update = entity.get('trip_update', {})
            if not trip_update:
                continue
            
            trip = trip_update.get('trip', {})
            trip_id = trip.get('trip_id')
            if not trip_id:
                continue
            
            timestamp = int(data.get('header', {}).get('timestamp', 0))
            vehicle = trip_update.get('vehicle', {})
            
            c.execute('''
                INSERT OR REPLACE INTO trip_updates
                (id, transport_type, trip_id, route_id, direction_id, vehicle_id, 
                 schedule_relationship, current_stop_sequence, current_status, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                f"{transport_type}_{trip_id}",
                transport_type,
                trip_id,
                trip.get('route_id'),
                trip.get('direction_id'),
                vehicle.get('id'),
                trip.get('schedule_relationship'),
                trip_update.get('current_stop_sequence'),
                trip_update.get('current_status'),
                timestamp
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Stored {len(data.get('entity', []))} trip updates from {Path(json_file).name}")
        return True
    
    except Exception as e:
        print(f"❌ Error parsing trip updates: {e}")
        return False
