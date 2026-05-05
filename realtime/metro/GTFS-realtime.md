# GTFS-Realtime Reference

TfNSW publishes three live GTFS-Realtime feeds accessible via your API key (`TRANSPORT_NSW_API_KEY`).  
All feeds use **Protocol Buffers** encoding over HTTP. Refresh every 30–60 seconds.

---

## Feed Structure

Every feed is a `FeedMessage` containing a header and a list of entities:

```
FeedMessage
├── header (FeedHeader)
│   ├── gtfs_realtime_version   — always "2.0"
│   ├── incrementality          — FULL_DATASET or DIFFERENTIAL
│   └── timestamp               — Unix epoch when feed was generated
└── entity[] (FeedEntity)
    ├── id                      — unique string ID for this entity
    ├── is_deleted              — true if this entity is being removed
    └── one of:
        ├── trip_update         — TripUpdate
        ├── vehicle             — VehiclePosition
        └── alert               — Alert
```

---

## TripUpdate

Provides real-time arrival and departure predictions for an active trip. Compare against `raw.stop_times` (scheduled) to calculate delay.

### TripDescriptor (identifies which trip)

| Field | Type | Description |
|---|---|---|
| `trip_id` | string | Matches `trips.trip_id` in the static feed |
| `route_id` | string | Matches `routes.route_id` |
| `direction_id` | int | `0`=outbound, `1`=inbound |
| `start_time` | string | Scheduled start time (HH:MM:SS) |
| `start_date` | string | Service date (YYYYMMDD) |
| `schedule_relationship` | enum | `SCHEDULED`, `ADDED`, `UNSCHEDULED`, `CANCELED` |

### StopTimeUpdate (one per stop, in sequence order)

| Field | Type | Description |
|---|---|---|
| `stop_sequence` | int | Matches `stop_times.stop_sequence` |
| `stop_id` | string | Matches `stops.stop_id` |
| `arrival.delay` | int | Seconds late (negative = early). Propagates forward if stop omitted |
| `arrival.time` | int | Predicted arrival as Unix timestamp |
| `arrival.uncertainty` | int | Confidence in seconds (0 = certain) |
| `departure.delay` | int | Seconds late for departure |
| `departure.time` | int | Predicted departure as Unix timestamp |
| `departure.uncertainty` | int | Confidence in seconds |
| `schedule_relationship` | enum | `SCHEDULED`, `SKIPPED`, `NO_DATA` |

### How to calculate delay

```
delay_seconds = actual_arrival_unix - scheduled_arrival_unix
```

Where `scheduled_arrival_unix` is derived from `raw.stop_times.arrival_time` + the trip's `start_date`.

> **To build a delay history:** poll this feed every 30–60s and write each `StopTimeUpdate` to a `realtime.trip_actuals` table. The feed is ephemeral — once a trip completes the data is gone.

---

## VehiclePosition

Provides the live location and status of every active vehicle on the network.

### TripDescriptor

Same fields as in TripUpdate — identifies which scheduled trip this vehicle is running.

### VehicleDescriptor

| Field | Type | Description |
|---|---|---|
| `id` | string | Internal vehicle identifier |
| `label` | string | Visible label on the vehicle (e.g. carriage set number) |
| `license_plate` | string | Vehicle registration (where applicable) |

### Position

| Field | Type | Description |
|---|---|---|
| `latitude` | float | Current latitude (WGS84) |
| `longitude` | float | Current longitude (WGS84) |
| `bearing` | float | Direction of travel in degrees (0=North, 90=East) |
| `odometer` | double | Distance travelled in metres (if published) |
| `speed` | float | Current speed in metres/second |

### Vehicle Status Fields

| Field | Type | Description |
|---|---|---|
| `current_stop_sequence` | int | Stop sequence of the stop the vehicle is at or approaching |
| `stop_id` | string | ID of the current/next stop |
| `current_status` | enum | `INCOMING_AT`, `STOPPED_AT`, `IN_TRANSIT_TO` |
| `timestamp` | int | Unix timestamp of when this position was recorded |
| `congestion_level` | enum | `UNKNOWN`, `RUNNING_SMOOTHLY`, `STOP_AND_GO`, `CONGESTION`, `SEVERE_CONGESTION` |
| `occupancy_status` | enum | `EMPTY`, `MANY_SEATS_AVAILABLE`, `FEW_SEATS_AVAILABLE`, `STANDING_ROOM_ONLY`, `CRUSHED_STANDING_ROOM_ONLY`, `FULL`, `NOT_ACCEPTING_PASSENGERS` |

### TfNSW Train-Specific Status Codes

From the Real-Time Train Technical Document, trains also report operational state:

| State | Meaning |
|---|---|
| On time | Running within tolerance |
| Delayed | Behind schedule |
| Cancelled | Trip will not run |
| Diverted | Running a different path |
| Limited stops | Skipping some scheduled stops |
| Rail replacement | Bus running instead of train |

---

## Alert

Service disruptions, cancellations, platform changes, and general advisories.

### Active Period

| Field | Type | Description |
|---|---|---|
| `active_period[].start` | int | Unix timestamp when the alert begins |
| `active_period[].end` | int | Unix timestamp when the alert ends (omitted = ongoing) |

### Informed Entity (what the alert applies to)

| Field | Type | Description |
|---|---|---|
| `informed_entity[].agency_id` | string | Applies to an entire agency |
| `informed_entity[].route_id` | string | Applies to a specific route |
| `informed_entity[].route_type` | int | Applies to all routes of a mode (e.g. all trains) |
| `informed_entity[].trip.trip_id` | string | Applies to one specific trip |
| `informed_entity[].stop_id` | string | Applies to a specific stop |

### Cause

| Value | Meaning |
|---|---|
| `UNKNOWN_CAUSE` | Cause not specified |
| `OTHER_CAUSE` | Cause specified in description |
| `TECHNICAL_PROBLEM` | Vehicle or infrastructure fault |
| `STRIKE` | Industrial action |
| `DEMONSTRATION` | Public event causing disruption |
| `ACCIDENT` | Collision or incident |
| `HOLIDAY` | Public holiday service change |
| `WEATHER` | Weather-related disruption |
| `MAINTENANCE` | Planned maintenance works |
| `CONSTRUCTION` | Construction affecting service |
| `POLICE_ACTIVITY` | Police or emergency services |
| `MEDICAL_EMERGENCY` | Medical incident on network |

### Effect

| Value | Meaning |
|---|---|
| `NO_SERVICE` | Route/stop has no service |
| `REDUCED_SERVICE` | Fewer trips than normal |
| `SIGNIFICANT_DELAYS` | Major delays expected |
| `DETOUR` | Route is diverted |
| `ADDITIONAL_SERVICE` | Extra trips added |
| `MODIFIED_SERVICE` | Service running differently |
| `OTHER_EFFECT` | See description |
| `UNKNOWN_EFFECT` | Effect not specified |
| `STOP_MOVED` | Stop location has changed |
| `NO_EFFECT` | Informational only |
| `ACCESSIBILITY_ISSUE` | Accessibility equipment out of service |

### Alert Text Fields

| Field | Type | Description |
|---|---|---|
| `url` | TranslatedString | Link to more information |
| `header_text` | TranslatedString | Short summary (shown in alert list) |
| `description_text` | TranslatedString | Full alert body |
| `tts_header_text` | TranslatedString | Text-to-speech version of header |
| `tts_description_text` | TranslatedString | Text-to-speech version of description |
| `severity_level` | enum | `UNKNOWN_SEVERITY`, `INFO`, `WARNING`, `SEVERE` |

> `TranslatedString` is a list of `{text, language}` pairs. TfNSW publishes in English (`"en"`).

---

## Feed Endpoints (TfNSW)

Authenticate with header: `Authorization: apikey <TRANSPORT_NSW_API_KEY>`

| Feed | Endpoint |
|---|---|
| TripUpdates | `https://api.transport.nsw.gov.au/v2/gtfs/realtime/sydneytrains` |
| VehiclePositions | `https://api.transport.nsw.gov.au/v2/gtfs/vehiclepos/sydneytrains` |
| Alerts | `https://api.transport.nsw.gov.au/v2/gtfs/alerts/sydneytrains` |

> Replace `sydneytrains` with `buses`, `ferries`, `lightrail`, `nswtrains`, `metro` for other modes.

---

## Relationship to Static GTFS

| Real-time field | Joins to static |
|---|---|
| `trip_update.trip.trip_id` | `raw.trips.trip_id` |
| `trip_update.trip.route_id` | `raw.routes.route_id` |
| `stop_time_update.stop_id` | `raw.stops.stop_id` |
| `stop_time_update.stop_sequence` | `raw.stop_times.stop_sequence` |
| `vehicle.trip.trip_id` | `raw.trips.trip_id` |
| `alert.informed_entity.route_id` | `raw.routes.route_id` |
| `alert.informed_entity.stop_id` | `raw.stops.stop_id` |
