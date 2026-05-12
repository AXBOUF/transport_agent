# Transport Agent — Database Schema Reference

## Databases

| Source | DB Name | env var |
|---|---|---|
| Metro (M1 line) | `metro` | `POSTGRES_DB_METRO` |
| Sydney Trains | `sydneytrains` | `POSTGRES_DB_SYDNEYTRAINS` |
| Buses | `buses` | `POSTGRES_DB_BUSES` |
| Full TfNSW feed | `transport` | `POSTGRES_DB_TRANSPORT` |

Default DB is `metro`. Use `db_url("sydneytrains")` etc. to switch.

---

## Schema Layers (all databases)

```
staging   — raw GTFS text loaded from CSV files (all columns TEXT)
core      — cleaned, typed version of staging
analysis  — pre-computed facts and agent-facing views
```

---

## Analysis Layer — Agent Views

These are the primary query targets for the agent. Pre-joined, no complex SQL needed.

### agent_station_departures
One row per stop event. Primary query surface for timetable questions.
```
station_id          stop_id from core.stops
station_name        e.g. "Central Station, Platform 26"
route_id            e.g. "SMNW_M1"
route_name          e.g. "M1"
destination         trip_headsign e.g. "Tallawong"
direction_id        0=outbound 1=inbound
service_date        date
departs_at          timestamp
arrives_at          timestamp
wheelchair_accessible
bikes_allowed       NULL if not published by this feed
service_id
```

### agent_route_summary
One row per route.
```
route_id, route_name, route_description, route_type, route_color
total_trips, service_patterns
```

### agent_trip_summary
One row per (trip, service_date). Runtime and origin/destination.
```
trip_id, route_id, service_date, direction_id
stops (count), runtime_minutes
departs_at, arrives_at
origin_stop_id, destination_stop_id
origin_name, destination_name
```

### agent_stop_frequency
Headway and services-per-hour per stop/route/hour.
```
route_id, stop_id, stop_name, direction_id
hour_of_day (0–23), day_type (weekday/weekend)
avg_headway_mins, median_headway_mins
services_per_hour, sample_count
```

### agent_transfer_hubs
Stops ranked by connectivity.
```
stop_id, stop_name, stop_lat, stop_lon
route_count, trip_count, avg_daily_departures, service_days
transfer_score, hub_classification (major_hub/interchange/connecting_stop/local_stop)
```

---

## Analysis Layer — Sydney Trains Only

### agent_occupancy_advisory
Predicted occupancy per departure (from occupancies.txt).
```
service_date, stop_id, stop_name, route_id, route_name
trip_id, departs_at, occupancy_status (0–6), occupancy_label, direction_id
```

### agent_train_formation
Train type per trip — car count, boarding areas.
```
trip_id, route_id, route_name, service_date, direction_id
vehicle_category_id, vehicle_category_name
car_count, boarding_area_count
```

---

## Analysis Layer — Fact Tables

Use these when agent views don't have enough detail.

### fact_scheduled_stop_events
The core fact table. One row per (trip × stop × service_date).
Key columns: `trip_id, stop_id, stop_name, route_id, service_date,
scheduled_arrival_ts, scheduled_departure_ts, departure_hour,
stop_sequence, trip_headsign, direction_id`

**Use this for**: journey queries between two stations (join on trip_id + stop_sequence).

### fact_route_frequency
Pre-computed headways. Joined from fact_scheduled_stop_events.

### fact_trip_runtime
Start/end times and total runtime per trip per date.

### fact_stop_connectivity
Route count, daily departures, transfer score per stop.

### fact_transfer_opportunities
Valid cross-route transfers (2–60 min window) at shared stops.

---

## Core Layer — Key Tables

```
core.stops       stop_id, stop_name, stop_lat, stop_lon, parent_station, platform_code
core.routes      route_id, agency_id, route_short_name, route_long_name, route_type
core.trips       trip_id, route_id, service_id, direction_id, trip_headsign, shape_id
core.stop_times  trip_id, stop_id, stop_sequence, arrival_time, departure_time
core.calendar    service_id, monday–sunday (smallint), start_date, end_date
core.calendar_dates  service_id, date, exception_type (1=added 2=removed)
```

---

## Key Join Paths

```
trips → routes          via route_id
trips → calendar        via service_id
stop_times → trips      via trip_id
stop_times → stops      via stop_id
fact_scheduled_stop_events → core.stops   via stop_id (for extra stop fields)
```

---

## Station Name Pattern

Stations have platform-level stop_ids e.g.:
- `"Central Station, Platform 26"`
- `"Central Station, Platform 27"`

Always use `ILIKE '%Central%'` not exact match.
Use `stop_sequence` ordering to confirm direction of travel.

---

## Date Range (metro)
Schedule covers **2026-04-21 to 2026-09-30**.
No calendar_dates exceptions — pure weekly pattern.
