# transport_agent

Working repo for transport data, scripts, and documentation.

## What stays here

- `user/` for experiments and scripts
- `docs/` for transport documentation and versioned references
- `gtfs_*` folders for local data sets and generated GTFS outputs

## Notes

- The production `apps/`, `infra/`, `packages/`, and other future scaffold folders are removed for now.
- Keep `.env` local; use `.env.example` as the template.
Clean. Every table has exactly what it needs — no redundant UNIQUEs, no leftover junk. Here's the full picture:

Table	PK	Foreign Keys
agency	agency_id	—
levels	level_id	—
notes	note_id	—
stops	stop_id	→ stops(stop_id) (parent), → levels(level_id)
routes	route_id	→ agency(agency_id)
calendar	service_id	—
calendar_dates	(service_id, date)	→ calendar(service_id)
shapes	(shape_id, shape_pt_sequence)	—
trips	trip_id	→ routes, → calendar, → notes(trip_note)
stop_times	(trip_id, stop_sequence)	→ trips, → stops, → notes(stop_note)
pathways	pathway_id	→ stops(from_stop_id), → stops(to_stop_id)


All 12 FK relationships enforced, all 11 tables with proper primary keys, all columns still raw TEXT.