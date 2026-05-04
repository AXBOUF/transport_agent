# Datawarehouse Scripts

## Current state

One schema is live: **`raw`**

All 11 GTFS tables from `gtfs_data/` are loaded into `raw` with every column stored as `TEXT`. Primary keys and foreign key relationships are enforced at the database level — the data is fully relational, just untyped.

---

## Scripts

### `bootstrap_schema.py`
Creates the `staging` and `core` schemas by executing their `schema.sql` files. Not needed for the `raw` load — `load_gtfs_data_raw.py` creates the `raw` schema itself.

```
python user/datawarehouse/scripts/bootstrap_schema.py
```

---

### `load_gtfs_data_raw.py`
The active load script. Reads all 11 `.txt` files from `gtfs_data/`, creates the `raw` schema, and loads every table with:
- All columns as `TEXT`
- A `PRIMARY KEY` on each table's natural GTFS key
- 12 foreign key relationships between tables after load

Safe to rerun — each table is dropped and recreated.

```
python user/datawarehouse/scripts/load_gtfs_data_raw.py
```

PKs and FKs loaded:

| Table | Primary Key | Foreign Keys |
|---|---|---|
| `agency` | `agency_id` | — |
| `levels` | `level_id` | — |
| `notes` | `note_id` | — |
| `stops` | `stop_id` | → `stops` (parent_station), → `levels` |
| `routes` | `route_id` | → `agency` |
| `calendar` | `service_id` | — |
| `calendar_dates` | `(service_id, date)` | → `calendar` |
| `shapes` | `(shape_id, shape_pt_sequence)` | — |
| `trips` | `trip_id` | → `routes`, → `calendar`, → `notes` (trip_note) |
| `stop_times` | `(trip_id, stop_sequence)` | → `trips`, → `stops`, → `notes` (stop_note) |
| `pathways` | `pathway_id` | → `stops` (from/to) |

---

### `build_core.py` — not yet in use
Transforms `staging.gtfs_stops` into simplified `core.stations` and `core.platforms` tables. Depends on data being in the `staging` schema first.

---

### `build_relationship_schema.py` — not yet in use
Future step. Takes the `raw` data and produces a second typed schema (`relationship`) where columns are cast to their correct SQL types (`integer`, `numeric`, `date`), and `shapes` is split into a header table + a points table. Adds full FK constraints on the typed data.

To run when ready:

```
python user/datawarehouse/scripts/build_relationship_schema.py
# or force source schema explicitly:
SOURCE_SCHEMA=raw python user/datawarehouse/scripts/build_relationship_schema.py
```
