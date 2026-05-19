# Transport

A workspace for collecting, processing and serving public-transport data (GTFS + realtime), plus a frontend, agent tooling and developer utilities.

This repo contains data ingestion scripts, realtime parsers and writers, a lightweight web backend, a Vite/React frontend, and an experimental transport agent used for queries and automation.

**Highlights / Features**
- GTFS ingestion and processing: fetch, parse and normalise GTFS feeds for BUSES, METRO and Sydney Trains ([data/](data)).
- Static GTFS utilities: scripts to download and extract GTFS, and to build local test datasets ([data/get_gtfs_*.py](data)).
- Realtime feed parsing and writing: parsers, writers, schema and convenience tools to ingest vehicle positions, trip updates and alerts into Postgres ([realtime/](realtime)).
- Postgres schema & writers: schema definition, helpers and batched writers for efficient realtime ingestion ([realtime/pg_schema.py](realtime/pg_schema.py), [realtime/pg_writer.py](realtime/pg_writer.py)).
- App backends: lightweight web services and API endpoints for buses, metro and trains ([web/](web), [realtime/buses/app.py](realtime/buses/app.py)).
- Frontend: Vite + React app and components for visualising routes and realtime state ([frontend/](frontend)).
- Transport agent: experimental agent, skills and tools to query the dataset and interact with the system programmatically ([transport_agent/](transport_agent)).
- Tests & validation: unit/integration tests and audit utilities to verify GTFS and DB schema ([test_*.py](test_describe.py), [audit_schema.py](audit_schema.py)).
- Design assets & themes: UI themes and fonts used by the frontend ([design/themes](design/themes)).

Project structure (top-level)
- data/: GTFS fetchers, loaders and local dataset management (e.g., `load_data.py`, `get_gtfs_*`).
- realtime/: parsers, writers, schema and service code for realtime ingestion and transformation.
- web/: small web backend(s) and API entry points.
- frontend/: Vite + React single-page app, components and build config.
- transport_agent/: agent code, skills and tools for automations and experiments.
- docs/: documentation and notes (including GTFS.md and other references).
- user/: experiments, datawarehouse sketches and ad-hoc scripts.

Quickstart
1. Create a Python virtual environment and activate it (Windows example):

	python -m venv .venv
	.venv\Scripts\Activate.ps1

2. Install Python dependencies. This repo uses a `pyproject.toml`; if you use pip:

	pip install -e .

	Or, if you rely on npm for the frontend, install node deps in `frontend/`:

	cd frontend
	npm install
	npm run dev

3. Load static GTFS data (local scripts):

	python data/load_data.py

4. Realtime ingestion (developer mode): see [realtime/QUICKSTART.md](realtime/QUICKSTART.md) for environment, Postgres and run instructions. Typical steps:

	- Configure Postgres connection in environment variables or config files used by `realtime/pg_writer.py`.
	- Run parsers/writers from `realtime/` to start ingesting feeds.

Development & testing
- Run tests with pytest:

	pytest -q

- Linting and formatting: follow local Python and frontend tooling conventions (e.g. `black`, `eslint`).

Where to find things (examples)
- GTFS scripts: [data/get_gtfs_buses.py](data/get_gtfs_buses.py), [data/get_gtfs_metro.py](data/get_gtfs_metro.py), [data/get_gtfs_sydneytrains.py](data/get_gtfs_sydneytrains.py).
- Realtime examples: [realtime/parser.py](realtime/parser.py), [realtime/pg_writer.py](realtime/pg_writer.py), [realtime/QUICKSTART.md](realtime/QUICKSTART.md).
- Frontend entry: [frontend/src/](frontend/src) and [frontend/package.json](frontend/package.json).
- Agent entry: [transport_agent/agent.py](transport_agent/agent.py) and [transport_agent/tools.py](transport_agent/tools.py).

Contributing
- Fork or branch, follow the existing code style, and open a PR with a clear description of changes.
- Add tests for new features and run `pytest` locally.

Further notes
- See `docs/` for in-repo documentation about GTFS conventions and platform design.
- Keep environment secrets out of the repository; use `.env` or a secrets manager for production credentials.

License
- This repository does not include a license file by default; add one if you plan to publish or share the code.

Contact / help
- For questions about running or developing the project, open an issue or contact the repository maintainers.

Updated README to summarise features, structure and quickstart.

Resume / CV project summary
---------------------------
Below are short, resume-ready descriptions and a slightly expanded summary you can copy into a CV or LinkedIn profile.

- One-line (concise): Built a full-stack transport data platform that ingests GTFS and realtime feeds, stores them in Postgres, and exposes APIs with a React frontend and automation agent.

- Short (1–2 lines): Developed a data pipeline and web platform to collect, normalise and serve GTFS and realtime public-transport data. Implemented Postgres schema and batched writers for realtime ingestion, a Vite/React frontend for visualization, and an experimental agent for automated queries and tooling.

- Expanded (achievements): Designed and implemented end-to-end GTFS ingestion and realtime processing for multiple transport modes; built robust ingestion writers and parsers, added automated validation and tests, and delivered a developer-friendly frontend and agent tools. Useful CV metrics to add: dataset size (rows), ingestion throughput (messages/sec) or test coverage if available.

Feel free to tell me which variant you prefer or supply metrics (rows, throughput, coverage) and I'll tailor the bullets further for your CV.