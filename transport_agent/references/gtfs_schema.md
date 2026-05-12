# Transport Agent — GTFS Static Schema Reference

## What is GTFS?

GTFS (General Transit Feed Specification) is a standard format for public transit schedules.
Each feed is a ZIP of CSV files. They are loaded into `staging` as TEXT, then typed into `core`.

---

## Core GTFS Files (all feeds)

### agency.txt → staging.agency / core.agency
```
agency_id       text PRIMARY KEY
agency_name     text
agency_url      text
agency_timezone text
agency_lang     text
```

### stops.txt → staging.stops / core.stops
```
stop_id             text PRIMARY KEY
stop_name           text
stop_lat            numeric
stop_lon            numeric
location_type       smallint   (0=stop, 1=station, 2=entrance, 3=node, 4=boarding_area)
parent_station      text       FK → stops.stop_id (for platform → station grouping)
platform_code       text
wheelchair_boarding smallint   (0=unknown, 1=yes, 2=no)
```

**Important**: Platform-level stops have names like `"Central Station, Platform 26"`.
Parent stops (location_type=1) group platforms. Always use `ILIKE '%name%'` not exact match.

### routes.txt → staging.routes / core.routes
```
route_id            text PRIMARY KEY
agency_id           text FK → agency
route_short_name    text   (e.g. "M1", "T1", "600")
route_long_name     text
route_type          integer  (0=tram, 1=subway/metro, 2=rail, 3=bus, 4=ferry)
route_color         text
route_text_color    text
```

### trips.txt → staging.trips / core.trips
```
trip_id             text PRIMARY KEY
route_id            text FK → routes
service_id          text FK → calendar
direction_id        smallint  (0=outbound, 1=inbound)
trip_headsign       text  (destination shown on vehicle, e.g. "Tallawong", "Berowra")
shape_id            text FK → shapes (optional)
vehicle_category_id text FK → vehicle_categories (Sydney Trains only)
```

### stop_times.txt → staging.stop_times / core.stop_times
```
trip_id             text FK → trips     }
stop_sequence       integer              } PRIMARY KEY
stop_id             text FK → stops
arrival_time        text   (HH:MM:SS, can be >24:00 for post-midnight)
departure_time      text
pickup_type         smallint  (0=regular, 1=no pickup, 2=must phone, 3=must coordinate)
drop_off_type       smallint
timepoint           smallint  (0=approximate, 1=exact)
shape_dist_traveled numeric
```

**Note**: `stop_times` is the largest table. Metro has ~4M rows. Sydney Trains ~10M+.

### calendar.txt → staging.calendar / core.calendar
```
service_id  text PRIMARY KEY
monday      smallint  (0 or 1)
tuesday     smallint
wednesday   smallint
thursday    smallint
friday      smallint
saturday    smallint
sunday      smallint
start_date  date  (YYYYMMDD in staging, date in core)
end_date    date
```

### calendar_dates.txt → staging.calendar_dates / core.calendar_dates
```
service_id    text    } PRIMARY KEY
date          date    }
exception_type smallint  (1=service added, 2=service removed)
```

**Metro note**: Metro feed has no calendar_dates. Pure weekly pattern only.

### shapes.txt → staging.shapes / core.shapes + core.shape_points
Shapes are split in core:
```
core.shapes:        shape_id PRIMARY KEY
core.shape_points:  shape_id, shape_pt_sequence, shape_pt_lat, shape_pt_lon, shape_dist_traveled
```

---

## Sydney Trains Extra Files

### vehicle_categories.txt → core.vehicle_categories
```
vehicle_category_id   text PRIMARY KEY
vehicle_category_name text  (e.g. "Waratah A", "Waratah B", "Oscar", "Hunter")
```

### vehicle_boardings.txt → core.vehicle_boardings
```
vehicle_category_id  text   }
child_sequence       integer } PRIMARY KEY
boarding_area_id     text   }
boarding_area_name   text
car_count            integer  (number of cars/carriages in this formation)
boarding_area_count  integer
```

### vehicle_couplings.txt → core.vehicle_couplings
```
parent_id      text FK → vehicle_categories
child_id       text
child_sequence integer
PRIMARY KEY (parent_id, child_id, child_sequence)
```

### occupancies.txt → core.occupancies
```
trip_id        text FK → trips
stop_sequence  integer
start_date     date
occupancy_status smallint  (0=empty, 1=many_seats, 2=few_seats, 3=standing, 4=crushed, 5=full, 6=not_accepting)
PRIMARY KEY (trip_id, stop_sequence, start_date)
```

Mapped to labels in `analysis.agent_occupancy_advisory`.

---

## How Stop Times Expand to Dates

`stop_times` has no date — it links to `trips → calendar` for service days.
`fact_scheduled_stop_events` in analysis expands this:

```
for each (trip, stop_time):
  for each date in calendar where day-of-week matches:
    emit one row with scheduled_departure_ts = date + departure_time
```

This is why `load_analysis.py` takes hours — Sydney Trains has millions of stop_times
times hundreds of service dates = hundreds of millions of events.

---

## Key Relationships

```
agency ← routes ← trips ← stop_times → stops
                    ↓
                 calendar / calendar_dates   (which days does this trip run?)
                    ↓
              vehicle_categories             (Sydney Trains only — train type)
                    ↓
              occupancies                    (Sydney Trains only — predicted crowd)
```

---

## Feed → Database Mapping

| Feed directory         | Database       | Extra tables vs standard GTFS         |
|------------------------|----------------|---------------------------------------|
| gtfs_metro/            | metro          | none                                  |
| gtfs_sydneytrains/     | sydneytrains   | vehicle_categories, vehicle_boardings, vehicle_couplings, occupancies |
| gtfs_buses/            | buses          | none                                  |
| gtfs_transport/        | transport      | none                                  |

---

## Time Format Notes

- Raw `stop_times.arrival_time` / `departure_time` are HH:MM:SS strings (staging.stop_times).
- Times can exceed 24:00 (e.g. `25:30:00` = 1:30 AM next day).
- In `fact_scheduled_stop_events`, these are expanded to full `timestamp` values
  using the service_date, handling the >24h rollover.
- Agent views use `departs_at` / `arrives_at` as proper timestamps.

---

## direction_id Convention

```
0 = outbound (away from city / CBD)
1 = inbound  (toward city / CBD)
```

For metro M1: 0 = toward Tallawong, 1 = toward Sydenham.
Use `trip_headsign` (e.g. "Tallawong", "Sydenham") for human-readable direction.
