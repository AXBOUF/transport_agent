# Scripts

Run in order:

1. `python user/datawarehouse/scripts/bootstrap_schema.py`
2. `python user/datawarehouse/scripts/load_gtfs_metro.py`
3. `python user/datawarehouse/scripts/build_core.py`

Raw GTFS import (from `gtfs_data` into schema `raw`):

1. `python user/datawarehouse/scripts/load_gtfs_data_raw.py`
