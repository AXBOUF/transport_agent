# Real-Time Transport Data Management

## Overview
Instead of storing every JSON file from API pulls, this system uses SQLite to store only the fresh/latest entity data. This dramatically reduces storage requirements while maintaining all necessary information.

## Architecture

### Database Schema (schema.py)
Three main tables store real-time data:

#### 1. **alerts** table
- Stores trip alerts (maintenance, service changes, etc.)
- Key fields: cause, effect, header_text, description_text, route_ids, active periods
- One alert per unique alert ID per transport type
- **Storage**: ~5-10 KB per alert

#### 2. **vehicle_positions** table  
- Stores current vehicle positions and status
- Key fields: vehicle_id, position (lat/lon), speed, occupancy, trip_id, route_id
- Latest entry replaces previous entry for each vehicle
- **Storage**: ~0.5-1 KB per vehicle

#### 3. **trip_updates** table
- Stores trip update information
- Key fields: trip_id, vehicle_id, schedule_relationship, current_status
- Latest entry replaces previous for each trip
- **Storage**: ~0.3-0.5 KB per trip

### Processing Flow

```
API Pull (30-60 sec)
    ↓
Save JSON (get_trip_*.py)
    ↓
Parse & Extract Entities (parser.py)
    ↓
Store/Update in Database (schema.py)
    ↓
Query via db_utils.py
```

## Data Accumulation vs Storage

### Old Approach (JSON Files)
- **100 vehicles** × **30 sec pull rate** = **3,600 files/day**
- **~500 KB per file** × **3,600** = **~1.8 GB/day**
- **Monthly**: ~54 GB storage

### New Approach (Database)
- **Single entry per vehicle** (updated each pull)
- **100 vehicles** × **1 KB** = **~100 KB total**
- **Alerts**: ~20-100 KB total
- **Trip updates**: ~50-200 KB total
- **Total daily growth**: ~1-5 MB (only new metadata)
- **Monthly**: ~50-100 MB growth

**Storage Savings: 99.9%**

## Usage

### Initialize Database
```bash
python schema.py
# Creates realtime_data.db with all tables and indexes
```

### Scheduler (app.py)
Automatically runs in all three folders:
- Metro: `python realtime/metro/app.py`
- Buses: `python realtime/buses/app.py`
- Sydney Trains: `python realtime/sydneytrains/app.py`

Each scheduler calls the update functions every 30 seconds (alerts) or 10 minutes (positions/updates).

### Query Database

```bash
# View latest alerts
python db_utils.py alerts metro

# View active vehicles
python db_utils.py vehicles buses

# Get vehicle history
python -c "from db_utils import get_vehicle_history; print(get_vehicle_history('RS037'))"

# Get route statistics
python -c "from db_utils import get_route_stats; print(get_route_stats('SMNW_M1', 'metro'))"

# Export current snapshot
python db_utils.py snapshot metro

# Cleanup old JSON files (dry-run)
python db_utils.py cleanup 1

# Actually delete files older than 1 day
python db_utils.py cleanup 1 execute
```

## Database Files
- **Location**: `realtime/realtime_data.db`
- **Size**: ~10-50 MB after months of operation
- **Backup**: Portable single file

## Entity ID Examples

### Alerts
```
ID: 8602c0be-3f1e-592d-a864-ee342d55e758
Key: metro_8602c0be-3f1e-592d-a864-ee342d55e758
```

### Vehicle Positions
```
ID: 0/2026-05-11T12:37:41Z/RS037
Key: metro_0/2026-05-11T12:37:41Z/RS037
Vehicle: RS037, Route: SMNW_M1
```

### Trip Updates
```
ID: trip-1788-123
Trip: 0215-003-115-017:1000
```

## Retention Policies

### Recommended Settings

1. **Keep in database**: All time (indexed queries are fast)
2. **Delete JSON files**: After 1-7 days
3. **Archive snapshots**: Compress monthly snapshots

```bash
# Weekly cleanup of JSON files
python db_utils.py cleanup 7 execute
```

## Benefits

✅ **99% storage reduction** compared to storing all JSON files
✅ **Fast queries** - indexed SQLite lookups in milliseconds  
✅ **Real-time data** - always latest state available
✅ **Portability** - single database file to backup/transfer
✅ **Historical tracking** - `updated_at` timestamp on every entry
✅ **No JSON parsing overhead** - direct database access

## Next Steps

Consider adding:
- [ ] Compression for older snapshots
- [ ] Full-text search on alerts
- [ ] API endpoints to query database
- [ ] Charts/dashboards from historical data
- [ ] Alerts on anomalies
