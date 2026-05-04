# Scripts

Run in order:

1. `python user/datawarehouse/scripts/bootstrap_schema.py`
2. `python user/datawarehouse/scripts/load_gtfs_metro.py`
3. `python user/datawarehouse/scripts/build_core.py`

Raw GTFS import (from `gtfs_data` into schema `raw`):

1. `python user/datawarehouse/scripts/load_gtfs_data_raw.py`

Relational transform (from `staging` into schema `relationship`):

1. `python user/datawarehouse/scripts/build_relationship_schema.py`

If your GTFS files were loaded into `raw` instead of `staging`, run the transformer with `SOURCE_SCHEMA=raw`.
