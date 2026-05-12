# Transport NSW Agent — Showcase Prompts

All prompts below are verified against live data. Each section lists what tool(s) fire and what the UI renders.

---

## 🚆 Commuter Queries

**Next trains — SVCROW cards**
```
What are the next 4 trains from Strathfield to Central right now?
```
_Fires `get_next_services` (auto). Renders visual departure cards with times and platform._

---

**Live departures board**
```
What's leaving Central Station in the next 20 minutes?
```
_Fires `get_live_departures` (auto). Returns live departure list across all platforms._

---

**One specific line**
```
Show me upcoming Metro trains from Chatswood heading into the city.
```
_Fires `get_next_services` (metro). Filters to Chatswood → city direction SVCROW cards._

---

## 🔍 Enthusiast Queries

**Fleet breakdown — what's actually running**
```
What train types are running on Sydney Trains today? Break it down by fleet type and how many trips each model runs.
```
_Fires `run_sql` on `analysis.agent_train_formation` grouped by `vehicle_category_name`. Expect Waratah (8-car), Tangara, Oscar, Millennium. Should render a bar chart._

---

**Peak frequency deep-dive**
```
How often does the M1 Metro run at Chatswood through the day? When are trains most frequent and when does service thin out?
```
_Fires `run_sql` on `analysis.agent_stop_frequency` (metro, Chatswood). Headways drop to 4 min at peak (7–9am), 9–10 min off-peak. Renders a line chart._

---

**Which line dominates the timetable**
```
Which Sydney Trains T-lines run the most scheduled trips in the whole timetable? Is T1 really king of the network?
```
_Fires `run_sql` on `analysis.agent_route_summary` grouped by route_name. T1 = 11,868 trips total, ahead of T8, T2. Bar chart expected._

---

## 📊 Multi-Dimensional Queries

**Cross-network live comparison**
```
How many trains and metros are live on the network right now? Compare Sydney Trains vs Metro — which has more vehicles out?
```
_Fires `get_vehicle_position` (auto, limit=300). Returns 268 Sydney Trains vs 32 Metro live. Agent summarises both networks side by side._

---

**Hourly service volume at a major station**
```
Show me a bar chart of how many train services pass through Central Station each hour on a weekday. When is it peak and when is it dead?
```
_Fires `run_sql` on `analysis.agent_stop_frequency` (sydneytrains, Central, weekday) grouped by hour. Peak around 7–9am and 5–6pm. Renders a bar chart._

---

**Crush vs comfort across T-lines**
```
Compare T1, T2, T4, T8 and T9 — which line has the most crush-loaded departures in the schedule? Show me a bar chart of comfortable vs overcrowded trips per line.
```
_Fires `run_sql` on `analysis.agent_occupancy_advisory`. T1 has 261 crush-load departures vs near-zero for T4. Multi-series bar chart._

---

## ⚙️ Operational Queries

**Network interchange hubs**
```
Which stations on the Sydney Trains network are the biggest transfer hubs? Show me the top 8 ranked by connectivity score.
```
_Fires `run_sql` on `analysis.agent_transfer_hubs` (deduplicated by station). Redfern (30 routes, score 65.3), Central (34 routes), Lidcombe, Glenfield. Bar chart by score._

---

**Live service alerts**
```
Are there any active service disruptions or alerts on Sydney Trains right now?
```
_Fires `get_active_alerts` (sydneytrains). Live alert exists: Macquarie Fields station access changes. Returns cause, effect, and description text._

---

**Delay snapshot — who is running late**
```
Which Metro trips are running with the most delay right now? Give me the worst offenders.
```
_Fires `get_worst_delays` (metro, 2hr). Returns peak delay in minutes per trip, first/last seen time, and snapshot count._

---

**Network delay trend**
```
Plot the average delay trend across Metro and Sydney Trains over the last 2 hours as a line chart. Is the network recovering or getting worse?
```
_Fires `get_delay_trend` (auto, 2hr). Returns 5-min buckets with avg/max delay. Renders a line chart with time on X-axis._

---

## 🃏 Silly Queries

**The marathon train**
```
What's the longest train journey in the entire Sydney Trains timetable? How long does it take?
```
_Fires `run_sql` on `analysis.agent_trip_summary` ORDER BY runtime_minutes DESC. Top result: Central → Brisbane Roma St, 850 minutes (14h 10m), 83 stops. Unexpected result that lands well._

---

**Rush hour dodge**
```
If I'm trying to avoid being sardined on a train, which lines and times should I absolutely avoid in the morning peak?
```
_Fires `run_sql` on `analysis.agent_occupancy_advisory` filtering for `crushed_standing` between 7–9am. Returns BMT and T1 routes at specific stations._

---

**Do trains actually run at 3am?**
```
Are there any trains running at 3am between Parramatta and the city, or am I stuck getting a cab?
```
_Fires `get_next_services` (from=Parramatta, to=Central, after_time=03:00). Will find night owl services or correctly report no services._

---

## 📈 Chart Queries

### Bar Chart
```
Show me a bar chart of the total number of scheduled trips per Sydney Trains T-line in the timetable.
```
_`run_sql` → `agent_route_summary` GROUP BY route_name WHERE T-lines only → `render_chart` bar. Verified: T1 top, T3/T5/T6 at bottom._

---

### Doughnut / Pie
```
Give me a doughnut chart of Metro occupancy levels across all live trains right now — how many are empty, few seats, or standing room only?
```
_`run_sql` → `agent_live_vehicle_state` GROUP BY occupancy_status (metro) → `render_chart` doughnut. Verified: STANDING_ROOM_ONLY=15, FEW_SEATS=9, MANY_SEATS=9._

---

### Line Chart — Headway over the day
```
Plot Metro service frequency at Chatswood through the day as a line chart — show me how headway in minutes changes from midnight to midnight on a weekday.
```
_`run_sql` → `agent_stop_frequency` (metro, Chatswood, weekday) GROUP BY hour → `render_chart` line. Peak drops to 4 min, late night stretches to 10 min._

---

### Line Chart — Delay Trend
```
Show me a line chart of average train delays over the last hour across the whole network. Is the afternoon peak getting worse?
```
_`get_delay_trend` (auto, 1hr) → `render_chart` line. X = time buckets, Y = avg delay seconds. Metro delay visible from recorded history._

---

## Quick-fire Sequence (for live demo flow)

Run these in order for a smooth 5-minute demo:

1. `What's leaving Central Station in the next 15 minutes?` — live departures card
2. `Show me a bar chart of scheduled trips per T-line.` — bar chart
3. `How many trains are live on the network right now vs Metro?` — cross-network
4. `Plot the delay trend over the last 2 hours as a line chart.` — live trend
5. `Give me a doughnut of Metro occupancy levels right now.` — live pie
6. `What's the longest train journey in the timetable?` — silly reveal
7. `Are there any service alerts on Sydney Trains today?` — live alerts

---

## Notes for Demo

- **SVCROW cards** only render for `get_next_services` and `get_live_departures` — those always produce the visual card UI
- **Charts** render in the map overlay; clicking ✕ closes and returns to map view
- **Live data** (vehicles, delays, alerts) requires `test_realtime.py` running — confirm it is up before demoing queries 4–5
- `run_sql` queries default to `metro` DB unless `transport_type` is specified in the prompt or inferred — for T-line queries say "Sydney Trains" explicitly to be safe
