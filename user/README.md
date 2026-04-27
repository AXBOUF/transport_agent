# Progress so far

experiments/get_static_gfts_data.py gives gtfs_data/* called on 20260427

## Current workspace focus

- Keep `user/` scripts and experiments
- Keep `docs/` and local `gtfs_*` datasets
- Do not restore the removed production scaffold (`apps/`, `infra/`, `packages/`, `src/`) unless the project moves back to that layout

# realtime endpoint url 

## timetable
Public Transport – Timetables – For Realtime v2 - static GTFS data for operators and services that support realtime data

url = "https://api.transport.nsw.gov.au/v1/gtfs/schedule/" 

Note - this feed has been superseded by version 2
url = "https://api.transport.nsw.gov.au/v2/gtfs/schedule/metro"


----

## trip update

Public URI: https://api.transport.nsw.gov.au/v1/gtfs/realtime/  

Public URI version 2 : https://api.transport.nsw.gov.au/v2/gtfs/realtime/ 

Operations:

GET /sydneytrains - Note - this feed has been superseded by version 2

GET /buses

GET /ferries/

GET /lightrail/

GET /lightrail/innerwest - Note - this feed has been superseded by version 2

GET /nswtrains

GET /regionbuses/

GET /metro - Note - this feed has been superseded by version 2
---

## vehicle position 

Current GTFS-realtime vehicle positions for Sydney Trains, Metro, and Inner West Light Rail.

Public URI: https://api.transport.nsw.gov.au/v2/gtfs/vehiclepos/

Operations:

GET /sydneytrains

GET /metro

GET /lightrail/innerwest

---

## alert 

Public URI: https://api.transport.nsw.gov.au/v2/gtfs/alerts

Operations:

GET /all

GET /buses

GET /ferries

GET /lightrail

GET /nswtrains

GET /sydneytrains

GET /metro

GET /regionbuses

----