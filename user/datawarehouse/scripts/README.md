# Datawarehouse Scripts

## Pipeline

```
data/gtfs_*/          staging schema        core schema        analysis schema
(raw .txt files)  →   (TEXT, PKs, FKs)  →  (typed columns)  →  (empty for now)
```

Steps 1 and 2 are rare (only when TfNSW publishes new data or DB is reset).  
Steps 3 and 4 are the regular refresh cycle.

---

## Databases

| DB name     | Source folder        | Notes                         |
|-------------|----------------------|-------------------------------|
| `transport` | `data/gtfs_data/`    | Full dataset — 11 tables      |
| `metro`     | `data/gtfs_METRO/`   | 9 tables — no levels/pathways |
| `bus`       | `data/gtfs_BUSES/`   | Future                        |

---

## Scripts

### `bootstrap_schema.py`
Creates `staging`, `core`, and `analysis` schemas in the target database.  
Run once per DB after creation, or after a full DB reset.

```bash
POSTGRES_DB=transport python user/datawarehouse/scripts/bootstrap_schema.py
POSTGRES_DB=metro     python user/datawarehouse/scripts/bootstrap_schema.py
```

---

### `load_staging.py`
Loads GTFS `.txt` files into the `staging` schema — all columns as `TEXT`, with PKs and FKs.  
Auto-skips tables whose `.txt` file is absent (e.g. metro has no `levels.txt` or `pathways.txt`).

```bash
POSTGRES_DB=transport GTFS_SOURCE=gtfs_data  python user/datawarehouse/scripts/load_staging.py
POSTGRES_DB=metro     GTFS_SOURCE=gtfs_METRO python user/datawarehouse/scripts/load_staging.py
```

Tables loaded per source:

| Table           | transport (gtfs_data) | metro (gtfs_METRO) |
|-----------------|-----------------------|--------------------|
| agency          | ✓                     | ✓                  |
| stops           | ✓                     | ✓                  |
| routes          | ✓                     | ✓                  |
| trips           | ✓                     | ✓                  |
| stop_times      | ✓                     | ✓                  |
| calendar        | ✓                     | ✓                  |
| calendar_dates  | ✓                     | ✓                  |
| shapes          | ✓                     | ✓                  |
| notes           | ✓                     | ✓                  |
| levels          | ✓                     | —                  |
| pathways        | ✓                     | —                  |

---

### `load_core.py`
Transforms `staging` → `core` with proper SQL types (TEXT → numeric, smallint, date, etc.).  
Auto-detects which optional tables/columns exist in staging — safe for both transport and metro.

```bash
POSTGRES_DB=transport python user/datawarehouse/scripts/load_core.py
POSTGRES_DB=metro     python user/datawarehouse/scripts/load_core.py
```

Key type changes from staging:
- `stop_lat`, `stop_lon` → `numeric`
- `monday`–`sunday` → `smallint`
- `start_date`, `end_date`, `date` → `date`
- `route_type` → `integer`
- `stop_sequence`, `shape_pt_sequence` → `integer`
- `shapes` is split into `shapes` (header) + `shape_points` (points)

---

### `load_analysis.py`
Placeholder — analysis layer not yet designed.

```bash
python user/datawarehouse/scripts/load_analysis.py
```
