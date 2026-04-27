# Data Warehouse

GTFS Metro warehouse work lives here.

## Layout

```text
user/datawarehouse/
  staging/
  core/
  scripts/
  docs/
```

## Flow

1. Load raw GTFS `.txt` files into `staging` tables.
2. Transform into `core` tables for station and platform views.
3. Use the `core` schema for map and API queries.
