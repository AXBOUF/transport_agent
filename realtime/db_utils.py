"""
Database Query and Management Utilities
Query realtime data from database and manage storage
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import get_connection
from pathlib import Path
from datetime import datetime, timedelta
import json

def get_latest_alerts(transport_type=None, limit=10):
    """Get latest alerts from database"""
    conn = get_connection()
    c = conn.cursor()
    
    if transport_type:
        c.execute('''
            SELECT * FROM alerts 
            WHERE transport_type = ? 
            ORDER BY timestamp DESC LIMIT ?
        ''', (transport_type, limit))
    else:
        c.execute('''
            SELECT * FROM alerts 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
    
    columns = [description[0] for description in c.description]
    results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return results

def get_active_vehicles(transport_type=None):
    """Get currently active vehicle positions"""
    conn = get_connection()
    c = conn.cursor()
    
    if transport_type:
        c.execute('''
            SELECT vehicle_id, trip_id, route_id, latitude, longitude, 
                   current_status, occupancy_status, speed, timestamp
            FROM vehicle_positions
            WHERE transport_type = ?
            ORDER BY updated_at DESC
        ''', (transport_type,))
    else:
        c.execute('''
            SELECT * FROM vehicle_positions
            ORDER BY updated_at DESC
        ''')
    
    columns = [description[0] for description in c.description]
    results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return results

def get_vehicle_history(vehicle_id, limit=20):
    """Get position history for a specific vehicle"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM vehicle_positions
        WHERE vehicle_id = ?
        ORDER BY timestamp DESC LIMIT ?
    ''', (vehicle_id, limit))
    
    columns = [description[0] for description in c.description]
    results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return results

def get_route_stats(route_id, transport_type=None):
    """Get stats for vehicles on a route"""
    conn = get_connection()
    c = conn.cursor()
    
    if transport_type:
        c.execute('''
            SELECT COUNT(*) as vehicle_count, 
                   SUM(CASE WHEN current_status = 'IN_TRANSIT_TO' THEN 1 ELSE 0 END) as in_transit,
                   SUM(CASE WHEN current_status = 'STOPPED_AT' THEN 1 ELSE 0 END) as stopped,
                   AVG(speed) as avg_speed,
                   MAX(speed) as max_speed
            FROM vehicle_positions
            WHERE route_id = ? AND transport_type = ?
        ''', (route_id, transport_type))
    else:
        c.execute('''
            SELECT COUNT(*) as vehicle_count, 
                   SUM(CASE WHEN current_status = 'IN_TRANSIT_TO' THEN 1 ELSE 0 END) as in_transit,
                   SUM(CASE WHEN current_status = 'STOPPED_AT' THEN 1 ELSE 0 END) as stopped,
                   AVG(speed) as avg_speed,
                   MAX(speed) as max_speed
            FROM vehicle_positions
            WHERE route_id = ?
        ''', (route_id,))
    
    columns = [description[0] for description in c.description]
    result = dict(zip(columns, c.fetchone() or []))
    conn.close()
    return result

def cleanup_old_json_files(days=1, dry_run=True):
    """Delete JSON files older than specified days"""
    realtime_path = Path(__file__).parent
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    saved_space = 0
    
    for json_file in realtime_path.glob("**/*.json"):
        file_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
        if file_mtime < cutoff_date:
            file_size = json_file.stat().st_size
            deleted_count += 1
            saved_space += file_size
            
            if not dry_run:
                json_file.unlink()
                print(f"🗑️  Deleted: {json_file.name} ({file_size / 1024:.2f} KB)")
            else:
                print(f"📋 Would delete: {json_file.name} ({file_size / 1024:.2f} KB)")
    
    if dry_run:
        print(f"\n📊 Dry run: Would delete {deleted_count} files, freeing {saved_space / (1024*1024):.2f} MB")
    else:
        print(f"\n✅ Deleted {deleted_count} files, freed {saved_space / (1024*1024):.2f} MB")

def export_snapshot_to_json(transport_type):
    """Export current state as JSON snapshot"""
    alerts = get_latest_alerts(transport_type, limit=100)
    vehicles = get_active_vehicles(transport_type)
    
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "transport_type": transport_type,
        "alerts": alerts,
        "vehicles": vehicles
    }
    
    snapshot_file = Path(__file__).parent / f"{transport_type}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)
    
    print(f"✅ Snapshot saved to {snapshot_file.name}")
    return snapshot_file

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "alerts":
            transport = sys.argv[2] if len(sys.argv) > 2 else None
            alerts = get_latest_alerts(transport)
            print(f"\n📢 Latest Alerts ({len(alerts)}):\n")
            for alert in alerts[:5]:
                print(f"  {alert['transport_type'].upper()}: {alert['header_text']}")
        
        elif cmd == "vehicles":
            transport = sys.argv[2] if len(sys.argv) > 2 else None
            vehicles = get_active_vehicles(transport)
            print(f"\n🚗 Active Vehicles ({len(vehicles)}):\n")
            for v in vehicles[:10]:
                print(f"  {v['vehicle_id']}: {v['current_status']} - Speed: {v['speed']}km/h")
        
        elif cmd == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            dry_run = sys.argv[3] != "execute" if len(sys.argv) > 3 else True
            cleanup_old_json_files(days, dry_run)
        
        elif cmd == "snapshot":
            transport = sys.argv[2] if len(sys.argv) > 2 else "metro"
            export_snapshot_to_json(transport)
    else:
        print("Usage: python db_utils.py <command> [args]")
        print("  alerts [transport_type]     - Show latest alerts")
        print("  vehicles [transport_type]   - Show active vehicles")
        print("  cleanup [days] [execute]    - Cleanup old JSON files (default: dry-run)")
        print("  snapshot [transport_type]   - Export current state as JSON")
