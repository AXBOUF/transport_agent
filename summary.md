# Transport NSW AI Platform — System Audit

**Date:** 2026-05-12  
**Auditor:** Claude Code (automated deep analysis)

---

## PROJECT OVERVIEW

An AI-powered transport intelligence platform integrating TfNSW GTFS static and realtime feeds with a Claude Haiku agent. Four PostgreSQL databases, a 4-layer ETL pipeline, a ReAct agent with 8 tools, and a FastAPI + Leaflet web dashboard.

---

## ARCHITECTURE SUMMARY

```
TfNSW GTFS ZIPs                    TfNSW GTFS-RT API
        ↓                                  ↓
load_staging_*.py              realtime/{network}/app.py (APScheduler)
        ↓                                  ↓
load_core_*.py                 pg_writer.py (upsert + 2-min prune)
        ↓                                  ↓
load_analysis.py          →   realtime.rt_* tables (30s refresh)
        ↓                                  ↓
analysis.fact_* + agent_*  ←──── joins ──────────────────┘
        ↓                                  ↓
transport_agent/tools.py          web/app.py endpoints
        ↓                                  ↓
Claude Haiku (ReAct loop)      Leaflet map + chat UI
        ↓
{answer, chart, tools_used}
```

---

## FOLDER STRUCTURE

```
transport/
├── .agents/skills/                  # Claude Code skills (project guidance, ref docs)
├── data/
│   ├── gtfs_METRO/                  # Metro M1 GTFS CSV files
│   ├── gtfs_sydneytrains/           # Sydney Trains T1–T9 GTFS CSV files
│   ├── gtfs_BUSES/                  # Bus network GTFS CSV files
│   ├── gtfs_TRANSPORT/              # Full TfNSW combined GTFS CSV files
│   └── sydneytrains.geojson         # Line geometry (downloaded)
├── docs/                            # GTFS schema reference
├── realtime/
│   ├── pg_schema.py                 # DDL: create realtime.rt_* tables
│   ├── pg_writer.py                 # Upsert vehicle positions, trips, alerts
│   ├── parser.py                    # [DEAD CODE] SQLite parser — not used
│   ├── schema.py                    # [DEAD CODE] SQLite schema — not used
│   ├── db_utils.py                  # DB connection helpers
│   ├── metro/app.py                 # APScheduler: metro fetchers (60s cycle)
│   ├── sydneytrains/app.py          # APScheduler: trains fetchers (60s cycle)
│   └── buses/app.py                 # APScheduler: buses fetchers (120s cycle)
├── transport_agent/
│   ├── agent.py                     # Full ReAct agent → {answer, chart, tools_used}
│   ├── minimal_agent.py             # Simple REPL agent → answer string
│   ├── tools.py                     # 8 tools + SQL + chart tool definitions
│   ├── config.py                    # db_url(source) builder from .env
│   ├── skill.md                     # System prompt: behaviour, schemas, output format
│   └── references/
│       ├── db_schema.md             # Full DB reference for agent context
│       └── gtfs_schema.md           # GTFS field definitions for agent context
├── user/datawarehouse/scripts/
│   ├── bootstrap_schema.py          # Create 4 databases and 4 schemas each
│   ├── load_staging_metro.py        # CSV → staging (metro)
│   ├── load_staging_sydneytrains.py # CSV → staging (sydneytrains, + extra tables)
│   ├── load_core_sydneytrains.py    # staging → core (sydneytrains)
│   ├── load_analysis.py             # core → analysis (all DBs, facts + views)
│   └── load_analysis_sydneytrains.py# Wrapper: sydneytrains only
├── web/
│   ├── app.py                       # FastAPI: 8 endpoints
│   └── static/
│       ├── index.html               # Single-page app shell
│       ├── app.js                   # Leaflet map, chat, markers, trip panel
│       └── style.css                # Dark theme + CSS tokens (6 themes)
├── desgin/                          # Design assets (fonts, logo images)
├── pyproject.toml                   # Python 3.11+, 27 dependencies (uv)
└── .env                             # DB credentials, API keys
```

---

## DATABASE ARCHITECTURE

### 4 Databases

| Database | Network | Source Feed | Analysis Built |
|---|---|---|---|
| `metro` | M1 Metro line | gtfs_METRO | ✓ complete |
| `sydneytrains` | T1–T9 + regional | gtfs_sydneytrains | building |
| `buses` | All NSW buses | gtfs_BUSES | ✗ skipped (redundant — transport covers it) |
| `transport` | All modes combined | gtfs_TRANSPORT | ✓ complete |

### 4 Schema Layers (identical across all databases)

| Schema | Purpose | Notes |
|---|---|---|
| `staging` | Raw CSV text, all columns TEXT | PKs enforced; FKs attempted |
| `core` | Typed + cleaned; NULLs from empty strings | Type inferred by column name |
| `analysis` | Pre-computed facts, agent views, materialized views | Spine: `fact_scheduled_stop_events` |
| `realtime` | Live GTFS-RT state; upsert + 2-min stale prune | 268 vehicles, 4702 stop updates (sydneytrains) |

### Key Analysis Tables

| Table | Purpose |
|---|---|
| `fact_scheduled_stop_events` | One row per (trip × stop × service_date). Spine for all queries. |
| `fact_route_frequency` | Headways + services/hour by stop/route/hour/day_type |
| `fact_trip_runtime` | Trip duration, stop count, origin/destination |
| `fact_stop_connectivity` | Route counts, transfer scores per stop |
| `fact_transfer_opportunities` | Cross-route transfers (2–60 min window) |
| `dim_service_patterns` | Unique stop sequences; express flag |
| `mv_live_departure_board` | Materialized view; fast departure lookups |

**Sydney Trains only:**

| Table | Purpose |
|---|---|
| `fact_vehicle_occupancy` | Crowd levels per (trip, stop, date) |
| `dim_vehicle_categories` | Train types: Waratah A/B, Oscar, Hunter |
| `fact_trip_vehicle` | Train type assignment per trip/date |

### Agent Views

| View | Description |
|---|---|
| `agent_station_departures` | All stop events with times, wheelchair, bikes |
| `agent_route_summary` | Route stats: trip count, patterns, colors |
| `agent_trip_summary` | Trip runtime, origin, destination |
| `agent_stop_frequency` | Headways per hour, day type |
| `agent_transfer_hubs` | Connectivity ranking: major_hub/interchange/local |
| `agent_occupancy_advisory` | Crowd predictions (Sydney Trains) |
| `agent_train_formation` | Car count, boarding areas (Sydney Trains) |

### Realtime Tables

| Table | PK | Prune |
|---|---|---|
| `rt_vehicle_positions` | (transport_type, vehicle_id) | After 2 min stale |
| `rt_trip_updates` | (transport_type, trip_id) | After 2 min stale |
| `rt_stop_time_updates` | (transport_type, trip_id, stop_sequence) | After 2 min stale |
| `rt_alerts` | (transport_type, entity_id) | When active_end passes |
| `rt_delay_history` | append-only | After 6 hours |

---

## ETL PIPELINE

```
data/gtfs_*/           CSV files (agency, stops, routes, trips, stop_times,
                        calendar, calendar_dates, shapes + sydneytrains extras)
        ↓
load_staging_*.py      Drop + recreate staging tables; all TEXT columns
                        PKs enforced; FKs skipped if table missing
        ↓
load_core_*.py         Introspect staging; infer types by column name
                        numeric (coords), integer (seqs), smallint (flags),
                        date (YYYYMMDD); empty → NULL; shapes split into
                        core.shapes + core.shape_points; FKs re-applied
        ↓
load_analysis.py       Build facts in dependency order:
                        1. fact_scheduled_stop_events  (calendar expansion;
                           handles 36-hour times; calendar_dates optional)
                        2. Indexes on fact_scheduled_stop_events
                        3. fact_route_frequency, fact_trip_runtime,
                           fact_stop_connectivity, dim_service_patterns,
                           fact_transfer_opportunities
                        4. mv_live_departure_board (materialized)
                        5. All agent_* views
                        6. Sydney Trains extensions (occupancy, vehicles)
```

**Schedule:** Full reload required (no incremental). Metro: ~minutes. Sydney Trains: ~hours (millions of stop_times × calendar dates = 100M+ events).

---

## REALTIME PIPELINE

```
TfNSW GTFS-RT API (protobuf binary)
        ↓
{metro,sydneytrains,buses}/get_vehicle_pos.py    (60–120s)
{metro,sydneytrains,buses}/get_trip_update.py    (60–120s)
{metro,sydneytrains,buses}/get_trip_alert.py     (10 min)
        ↓
pg_writer.py
  write_vehicle_positions()   → rt_vehicle_positions (upsert on vehicle_id)
  write_trip_updates()        → rt_trip_updates + rt_stop_time_updates
  write_alerts()              → rt_alerts
  snapshot_delay_history()    → rt_delay_history (every 5 min, 6-hour retention)
        ↓
PostgreSQL realtime schema
        ↓
web/app.py → /api/vehicles, /api/trip/{id}, /api/alerts
        ↓
Leaflet map markers (10s poll)
```

**Sydney Trains quirk:** Feed omits `stop_sequence` — pg_writer falls back to list position index. Can mis-order if feed changes structure.

---

## AI AGENT

### Architecture: ReAct Loop

```
User question
    ↓
Build prompt: skill.md + ANTHROPIC_TOOLS + conversation history
    ↓
Claude Haiku (claude-haiku-4-5-20251001, 4096 tokens)
    ↓
Loop (max 10–15 iterations):
    if stop_reason == "end_turn"   → return {answer, chart, tools_used}
    if stop_reason == "tool_use"   → run_tool(name, inputs) → append result → loop
    else                           → break
```

### Tools

| Tool | Data Source | Live? |
|---|---|---|
| `get_next_services` | `analysis.fact_scheduled_stop_events` | No (static) |
| `get_live_departures` | `analysis.live_departures` (**MISSING VIEW**) | Yes |
| `get_active_alerts` | `analysis.live_alerts` (**MISSING VIEW**) | Yes |
| `get_vehicle_position` | `analysis.agent_live_vehicle_state` (**MISSING VIEW**) | Yes |
| `get_delay_trend` | `realtime.rt_delay_history` | Yes |
| `get_worst_delays` | `realtime.rt_delay_history` | Yes |
| `list_tables` | `information_schema.tables` | No |
| `describe_table` | `information_schema.columns` | No |
| `run_sql` | Any DB (SELECT only, 100-row cap) | No |
| `render_chart` | UI-side only (Chart.js) | No |

### LLM Config

- **Model:** claude-haiku-4-5-20251001
- **Max tokens:** 4096
- **Prompt caching:** Not enabled (skill.md re-sent every request)
- **Entry points:** `agent.py` (web, returns dict), `minimal_agent.py` (CLI, returns string)

---

## WEB APP

### Backend Endpoints (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Serve index.html |
| POST | `/api/chat` | Agent chat → {answer, chart, tools_used} |
| GET | `/api/vehicles` | Live vehicle GeoJSON (rt_vehicle_positions + core joins) |
| GET | `/api/trip/shape` | Trip stop coordinates for route polyline |
| GET | `/api/trip/{trip_id}` | Stop sequence + realtime delays for panel |
| GET | `/api/stops` | Station list for stop layer |
| GET | `/api/routes/shapes` | Line polylines from staging.shapes |
| GET | `/api/alerts` | Service alerts from realtime.rt_alerts |

### Frontend Features

| Feature | Status |
|---|---|
| Leaflet dark map (6 themes: dark/midnight/cyberpunk/noir/blueprint/emerald) | ✓ |
| Live vehicle markers (color by network, bearing, delay dot) | ✓ |
| Hover popup: line, destination, occupancy, delay, last updated | ✓ |
| Click: route polyline + stop dots drawn | ✓ |
| Click: trip detail panel (stop sequence + realtime delays) | ✓ |
| Route lines panel (T1–T9, M1 toggles) | ✓ |
| Agent chat with service cards and chart rendering | ✓ |
| Alerts bar with expandable detail | ✓ |
| Stop layer (stations + platforms) | ✓ |
| Auto-refresh vehicles every 10s | ✓ |
| Theme picker (6 presets) | ✓ |
| Error UI on fetch failure | ✗ missing |
| Offline fallback | ✗ missing |
| Marker clustering (50+ vehicles) | ✗ not implemented |

---

## ISSUES

### Critical (blockers)

| # | Issue | Fix |
|---|---|---|
| 1 | `get_live_departures` tool queries `analysis.live_departures` — view does not exist | Create view: fact_scheduled_stop_events LEFT JOIN rt_stop_time_updates |
| 2 | `get_active_alerts` tool queries `analysis.live_alerts` — view does not exist | Create view: wrap realtime.rt_alerts |
| 3 | `get_vehicle_position` tool queries `analysis.agent_live_vehicle_state` — view does not exist | Create view: rt_vehicle_positions JOIN core tables |
| 4 | `test_shapes.py` has hardcoded password `"301415"` | Use os.getenv("POSTGRES_PASSWORD") |

### High

| # | Issue | Fix |
|---|---|---|
| 5 | No Anthropic prompt caching — skill.md re-sent every request | Add cache_control={"type":"ephemeral"} to system message |
| 6 | No rate limiting on /api/chat | Add 1 req/s per IP limiter |
| 7 | Route shapes hardcoded to T1–T9, M1 only | Load all routes from DB dynamically |
| 8 | Sydney Trains stop_sequence fallback by list position — lossy | Log warning; validate against core.stop_times |
| 9 | No retry in realtime fetchers — failed call = missed snapshot | Exponential backoff + retry (max 3) |

### Medium (tech debt)

| # | Issue | Fix |
|---|---|---|
| 10 | `realtime/parser.py` and `realtime/schema.py` are dead code (SQLite) | Delete |
| 11 | Type inference fragile: based on column name matching | Config-driven type map |
| 12 | No CSV validation before staging load | Schema validation pre-load; fail loudly |
| 13 | Agent loop count arbitrary (10–15); no wall-clock timeout | 30-second timeout |
| 14 | No input validation on /api/trip/{trip_id} | Whitelist alphanum + underscore |
| 15 | Bus realtime pipeline untested end-to-end | Verify pg_writer called by buses/app.py |

### Low (polish)

| # | Issue | Fix |
|---|---|---|
| 16 | No error UI on frontend (silent failures) | Toast/snackbar on fetch failure |
| 17 | Chart.js + Leaflet loaded from CDN | Bundle locally for offline use |
| 18 | No pagination on vehicle markers | Leaflet.markercluster when >50 |
| 19 | `desgin/` folder is a typo | Rename to `design/` |

---

## STRENGTHS

1. **4-layer schema** is clean and well-reasoned — staging/core/analysis/realtime separation keeps concerns isolated
2. **Pre-computed facts** eliminate ad-hoc SQL complexity; agent tools are fast
3. **Sydney Trains extensions** (occupancy, vehicle formation) are uniquely valuable data not available elsewhere
4. **ReAct loop** with `render_chart` tool that flows directly to frontend Chart.js integration
5. **Realtime pipeline** handles 268+ vehicles at 30s refresh with upsert + prune efficiently
6. **skill.md** is well-written: clear schema awareness, tool usage rules, output format contract
7. **6-theme UI** with CSS tokens for all colors — trivially extensible
8. **Multi-mode coverage**: Metro, Trains, Buses, full TfNSW all loaded; agent switches with `transport_type`
9. **GTFS-RT protobuf parsing**: Efficient binary format; avoids JSON overhead
10. **`fact_transfer_opportunities`** pre-computed — enables cross-route interchange queries without expensive joins at query time

---

## RECOMMENDED NEXT STEPS

### This week (blockers)

1. Create 3 missing analysis views (`live_departures`, `live_alerts`, `agent_live_vehicle_state`) in `load_analysis.py`
2. Fix hardcoded password in `test_shapes.py`
3. Delete `realtime/parser.py` and `realtime/schema.py`

### Next 2 weeks

4. Enable Anthropic prompt caching in `agent.py` (add `cache_control` to system message)
5. Add error UI to frontend — toast on fetch failure
6. Rate limit `/api/chat` (e.g. slowapi, 1 req/s per IP)
7. Verify buses realtime pipeline end-to-end

### Next month

8. Config-driven type inference in `load_core_*.py`
9. CSV validation pre-load with loud failure
10. Leaflet.markercluster for 50+ vehicles
11. Rename `desgin/` → `design/`

### Quarterly

12. Incremental ETL (reload only changed GTFS data)
13. Time-travel mode: "What was service like on Jan 15?"
14. Stop accessibility queries (wheelchair, mobility aid)
15. Real-time occupancy heatmap view

---

## PRODUCTION READINESS

| Component | Score | Bottleneck |
|---|---|---|
| Static ETL | 8/10 | No validation layer; no incremental |
| Realtime pipeline | 6/10 | No retry; buses untested; dead code |
| Database schema | 8/10 | 3 missing views block agent live tools |
| AI agent | 7/10 | 3 broken tools; no prompt caching; no quota |
| Web backend | 7/10 | No input validation; no rate limiting |
| Web frontend | 7/10 | No error UI; CDN dependencies |
| **Overall** | **7/10** | **2–3 weeks to production-ready (metro + trains)** |

### Go/No-Go Checklist

- [ ] Create `live_departures`, `live_alerts`, `agent_live_vehicle_state` views
- [ ] Fix hardcoded password in test_shapes.py
- [ ] Verify buses realtime data flowing
- [ ] Test all 8 agent tools end-to-end
- [ ] Add error UI to frontend
- [ ] Enable prompt caching
- [ ] Rate limit /api/chat
- [ ] Load test with 300+ markers
