# GTFS Static Data Reference

TfNSW publishes a rolling **~3-month schedule window** (current: Apr 27 – Jul 26 2026).  
All 11 tables live in the `raw` schema in PostgreSQL. Every column is stored as `TEXT`.

---

## Tables

### `agency`
The transit operators that run routes. Each route belongs to one agency.

| Column | Description |
|---|---|
| `agency_id` | Unique identifier for the agency |
| `agency_name` | Full name of the agency (e.g. "Sydney Trains") |
| `agency_url` | Agency website URL |
| `agency_timezone` | Timezone for all times in this feed (e.g. "Australia/Sydney") |
| `agency_lang` | Default language (e.g. "EN") |
| `agency_phone` | Public contact phone number |

---

### `stops`
Every physical location where passengers board or alight — platforms, bus stops, ferry wharves, entrances. Also includes parent stations that group platforms.

| Column | Description |
|---|---|
| `stop_id` | Unique identifier for the stop |
| `stop_code` | Short public-facing code shown on signage |
| `stop_name` | Human-readable name (e.g. "Central Station") |
| `stop_lat` | Latitude (WGS84) |
| `stop_lon` | Longitude (WGS84) |
| `location_type` | `0`=stop/platform, `1`=station (parent), `2`=entrance, `3`=generic node, `4`=boarding area |
| `parent_station` | `stop_id` of the parent station this stop belongs to |
| `wheelchair_boarding` | `0`=no info, `1`=accessible, `2`=not accessible |
| `level_id` | Which level of a multi-level station this stop is on |
| `platform_code` | Platform label shown to passengers (e.g. "1", "2A") |

---

### `routes`
A named transit service that runs between defined endpoints. Groups trips by line (e.g. T1 North Shore Line).

| Column | Description |
|---|---|
| `route_id` | Unique identifier for the route |
| `agency_id` | The agency operating this route |
| `route_short_name` | Short public label (e.g. "T1", "700") |
| `route_long_name` | Full descriptive name (e.g. "T1 North Shore and Western Line") |
| `route_desc` | Additional description |
| `route_type` | Mode of transport — see route type codes below |
| `route_color` | Hex colour for the route (e.g. "F99D1C") |
| `route_text_color` | Hex colour for text overlaid on route colour |
| `exact_times` | TfNSW extension: `1` if headway-based trips run at exact intervals |

**Route type codes used by TfNSW:**

| Code | Mode |
|---|---|
| `2` | Rail (Sydney Trains / NSW Trains) |
| `4` | Ferry |
| `106` | Rail replacement bus |
| `204` / `205` | School / special bus |
| `401` | Metro |
| `700` | Bus |
| `712` | Coach (intercity bus) |
| `714` | Bus (on-demand / flexible) |
| `900` | Light Rail / Tram |

---

### `trips`
A single scheduled run of a route — one vehicle travelling its full path at a specific time on specific days.

| Column | Description |
|---|---|
| `trip_id` | Unique identifier for this trip |
| `route_id` | Which route this trip belongs to |
| `service_id` | Links to `calendar`/`calendar_dates` to define which days it runs |
| `shape_id` | The geographic path this trip follows (links to `shapes`) |
| `trip_headsign` | Destination text shown on the vehicle (e.g. "City Circle") |
| `direction_id` | `0`=outbound, `1`=inbound |
| `block_id` | Trips sharing a block_id use the same vehicle consecutively |
| `wheelchair_accessible` | `0`=no info, `1`=accessible, `2`=not accessible |
| `route_direction` | TfNSW extension: descriptive direction label |
| `trip_note` | TfNSW extension: links to `notes.note_id` for supplementary info |
| `bikes_allowed` | `0`=no info, `1`=allowed, `2`=not allowed |

---

### `stop_times`
The timetable — every stop a trip makes, in order, with scheduled arrival and departure times. This is the largest table (5.1M rows).

| Column | Description |
|---|---|
| `trip_id` | Which trip this stop belongs to |
| `arrival_time` | Scheduled arrival time (HH:MM:SS — can exceed 24:00:00 for overnight) |
| `departure_time` | Scheduled departure time |
| `stop_id` | Which stop is being visited |
| `stop_sequence` | Order of this stop within the trip (1, 2, 3…) |
| `stop_headsign` | Overrides the trip headsign from this stop onward |
| `pickup_type` | `0`=regular, `1`=no pickup, `2`=phone agency, `3`=coordinate with driver |
| `drop_off_type` | Same codes as pickup_type but for alighting |
| `shape_dist_traveled` | Distance along the shape from the first stop (metres) |
| `timepoint` | `0`=approximate time, `1`=exact timepoint |
| `stop_note` | TfNSW extension: links to `notes.note_id` for this stop |

> **Note:** `arrival_time` and `departure_time` are **scheduled only**. There are no actual times here. For real-time delays see the GTFS-Realtime TripUpdates feed.

---

### `calendar`
Defines recurring weekly service patterns — which days of the week a service_id operates and over what date range.

| Column | Description |
|---|---|
| `service_id` | Unique identifier for this service pattern |
| `monday` | `1`=runs on Mondays, `0`=does not |
| `tuesday` | Same for Tuesday |
| `wednesday` | Same for Wednesday |
| `thursday` | Same for Thursday |
| `friday` | Same for Friday |
| `saturday` | Same for Saturday |
| `sunday` | Same for Sunday |
| `start_date` | First date this pattern is valid (YYYYMMDD) |
| `end_date` | Last date this pattern is valid (YYYYMMDD) |

---

### `calendar_dates`
Exceptions to the regular weekly calendar — adds or removes service on specific dates (public holidays, special events).

| Column | Description |
|---|---|
| `service_id` | Which service pattern this exception applies to |
| `date` | The specific date of the exception (YYYYMMDD) |
| `exception_type` | `1`=service added on this date, `2`=service removed on this date |

---

### `shapes`
Geographic polylines that define the path a trip travels — sequence of lat/lon points. Used to draw routes on a map. Largest table (15.1M rows).

| Column | Description |
|---|---|
| `shape_id` | Identifier for this shape (shared by trips with the same path) |
| `shape_pt_lat` | Latitude of this point |
| `shape_pt_lon` | Longitude of this point |
| `shape_pt_sequence` | Order of this point within the shape |
| `shape_dist_traveled` | Cumulative distance from the first point (metres) |

---

### `levels`
Defines the floors/levels within a multi-level station. Used to describe vertical location of platforms.

| Column | Description |
|---|---|
| `level_id` | Unique identifier for this level |
| `level_index` | Numeric floor index (`0`=ground, positive=above, negative=below) |
| `level_name` | Human-readable label (e.g. "Ground Level", "Concourse") |

---

### `pathways`
Walking connections between stops within a station — stairs, escalators, lifts, walkways. Used for in-station navigation and accessibility routing.

| Column | Description |
|---|---|
| `pathway_id` | Unique identifier for this pathway |
| `from_stop_id` | The stop/node this pathway starts from |
| `to_stop_id` | The stop/node this pathway leads to |
| `pathway_mode` | `1`=walkway, `2`=stairs, `3`=moving sidewalk, `4`=escalator, `5`=elevator, `6`=fare gate, `7`=exit gate |
| `is_bidirectional` | `0`=one direction only, `1`=traversable both ways |
| `traversal_time` | Estimated seconds to traverse this pathway |

---

### `notes`
TfNSW extension table. Stores supplementary text notes that are referenced by trips or individual stop_times.

| Column | Description |
|---|---|
| `note_id` | Unique identifier for this note |
| `note_text` | The note content (e.g. "Does not run on public holidays") |

---

## Primary Keys & Foreign Keys

| Table | Primary Key | Foreign Keys |
|---|---|---|
| `agency` | `agency_id` | — |
| `levels` | `level_id` | — |
| `notes` | `note_id` | — |
| `calendar` | `service_id` | — |
| `shapes` | `(shape_id, shape_pt_sequence)` | — |
| `stops` | `stop_id` | `parent_station` → `stops.stop_id` (self-ref) |
| | | `level_id` → `levels.level_id` |
| `routes` | `route_id` | `agency_id` → `agency.agency_id` |
| `trips` | `trip_id` | `route_id` → `routes.route_id` |
| | | `service_id` → `calendar.service_id` |
| | | `trip_note` → `notes.note_id` |
| `calendar_dates` | `(service_id, date)` | `service_id` → `calendar.service_id` |
| `stop_times` | `(trip_id, stop_sequence)` | `trip_id` → `trips.trip_id` |
| | | `stop_id` → `stops.stop_id` |
| | | `stop_note` → `notes.note_id` |
| `pathways` | `pathway_id` | `from_stop_id` → `stops.stop_id` |
| | | `to_stop_id` → `stops.stop_id` |

---

## Row Counts (as loaded)

| Table | Rows |
|---|---|
| agency | 689 |
| stops | 170,265 |
| routes | 10,234 |
| trips | 191,500 |
| stop_times | 5,100,341 |
| calendar | 2,103 |
| calendar_dates | 27,204 |
| levels | 7 |
| shapes | 15,180,873 |
| notes | 958 |
| pathways | 6,097 |
```sh

 PRIMARY_KEYS = {
         "agency":         ["agency_id"],
         "stops":          ["stop_id"],
         "routes":         ["route_id"],
         "trips":          ["trip_id"],
         "calendar":       ["service_id"],
         "stop_times":     ["trip_id", "stop_sequence"],
         "shapes":         ["shape_id", "shape_pt_sequence"],
         "calendar_dates": ["service_id", "date"],
         "levels":         ["level_id"],
         "notes":          ["note_id"],
         "pathways":       ["pathway_id"],
     }
     RELATIONS = [
         "ALTER TABLE raw.routes     ADD CONSTRAINT fk_routes_agency ...",
         "ALTER TABLE raw.stops      ADD CONSTRAINT fk_stops_parent_station ...",
         "ALTER TABLE raw.stops      ADD CONSTRAINT fk_stops_level ...",
         "ALTER TABLE raw.trips      ADD CONSTRAINT fk_trips_routes ...",
         "ALTER TABLE raw.trips      ADD CONSTRAINT fk_trips_calendar ...",
         "ALTER TABLE raw.trips      ADD CONSTRAINT fk_trips_note ...",
         "ALTER TABLE raw.stop_times ADD CONSTRAINT fk_stop_times_trips ...",
         "ALTER TABLE raw.stop_times ADD CONSTRAINT fk_stop_times_stops ...",
         "ALTER TABLE raw.stop_times ADD CONSTRAINT fk_stop_times_note ...",
         "ALTER TABLE raw.calendar_dates ADD CONSTRAINT fk_calendar_dates_calendar ...",
         "ALTER TABLE raw.pathways   ADD CONSTRAINT fk_pathways_from_stop ...",
         "ALTER TABLE raw.pathways   ADD CONSTRAINT fk_pathways_to_stop ...",
     ]
     ```