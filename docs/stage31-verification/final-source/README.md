# steam-etl

A batch data platform that measures **the gap between attention and players**.

Steam says how many people *play* a game — concurrent users, review growth.
Twitch says how many *watch* it. The two are usually assumed to move together,
and they do not. A game that is loud on stream but empty in the store looks
different from a game that is quiet on stream but full of players, and the
difference is a marketing question: bought exposure that did not convert, or a
title nobody has heard of that people keep playing.

The pipeline collects both sides daily into a PostgreSQL warehouse, resolves the
same game across Steam, Twitch and IGDB, and publishes the divergence.

**Design documents:** [`ARCHITECTURE.md`](ARCHITECTURE.md) — what it is and why,
including how the central claim can be falsified. [`ROADMAP.md`](ROADMAP.md) —
build order, with numeric done-criteria per phase.

---

## What it does

Every day the pipeline:

1. Pulls the full Steam catalog from SteamSpy with CCU, review counts, and price
2. Enriches each game with metadata from the Steam Store API (developer, publisher, genres, release date)
3. Samples top Twitch streams and aggregates attention per game
4. Resolves cross-platform identity through IGDB, so a Twitch category and a Steam appid can be recognised as one game
5. Stores everything as daily snapshots for trend analysis

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Database | PostgreSQL 18 |
| HTTP | requests 2.33.1 |
| DB driver | psycopg 3.3.4 (psycopg3) |
| Fuzzy matching | RapidFuzz 3.14.5 |
| Orchestration | Airflow 2.9.1 |
| Transformations | dbt |
| Visualisation | Metabase |
| Infrastructure | Docker / docker-compose |
| CI/CD | GitHub Actions (pytest + ruff) |

---

## Project structure

```
steam-etl/
├── src/
│   ├── main.py                 # CLI entry point — 13 subcommands
│   ├── db.py                   # DB connection (psycopg3)
│   ├── extract_steamspy.py     # SteamSpy API client
│   ├── extract_steam_store.py  # Steam Store API client
│   ├── extract_twitch.py       # Twitch Helix API client
│   ├── extract_igdb.py         # IGDB API client
│   ├── transform.py            # Stateless transform functions
│   └── load.py                 # Upsert functions for all tables
├── sql/
│   ├── create_tables.sql       # Initial schema (destructive — dev only)
│   ├── migrations/             # 001–005, apply in order manually
│   └── analytics/              # 6 read-only analytical queries
├── tests/
│   ├── test_transform.py
│   ├── test_load.py
│   ├── test_extract.py
│   └── test_main.py
├── data/raw/                   # Raw JSON snapshots (gitignored)
├── dags/                       # Airflow DAGs
├── steam_analytics/            # dbt project
├── docker-compose.yml
└── .env                        # Local secrets (never committed)
```

---

## Data sources

**SteamSpy** — paginated catalog of all Steam games. 1000 games per page, rate-limited to one page per 65 seconds. Provides CCU, positive/negative review counts, price, and estimated owners range.

**Steam Store API** — per-game metadata fetched one game at a time (1 request/sec). Provides developer, publisher, genres, release date, header image, and `is_free` flag. Steam Store data takes priority over SteamSpy for stable fields.

**Twitch Helix** — top live streams aggregated by game category. Uses OAuth2 client credentials flow. Provides viewer counts, stream counts, and an `igdb_id` field used for high-confidence cross-platform linking.

**IGDB** — game catalog with ratings, platform list, and external store links (Steam, Epic, GOG, etc.). Queried via POST with a text body. Uses the same Twitch OAuth credentials.

---

## Database schema

```
games                    — one row per Steam appid
game_snapshots           — daily CCU/review/price snapshots
genres                   — genre lookup table
game_genres              — many-to-many: games ↔ genres

twitch_game_snapshots    — daily viewer/stream count per Twitch category
twitch_categories_catalog — Twitch Helix category metadata + igdb_id

igdb_games               — IGDB game records
igdb_game_store_links    — store links per IGDB game (Steam, Epic, GOG…)
twitch_categories        — Twitch category records from IGDB

twitch_igdb_mapping_candidates — fuzzy match results linking
                                  Twitch categories to IGDB games
                                  (status: pending / auto_approved /
                                           approved / rejected)
```

---

## Setup

**Prerequisites:** Docker, Python 3.10+, a Twitch Developer application (for IGDB access)

### 1. Clone and configure

```bash
git clone https://github.com/yourname/steam-etl.git
cd steam-etl
cp .env.example .env
# Fill in your credentials — see .env.example for required variables
```

Required environment variables:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=steam_analytics
POSTGRES_USER=steam_user
POSTGRES_PASSWORD=yourpassword

TWITCH_CLIENT_ID=...
TWITCH_CLIENT_SECRET=...
```

`POSTGRES_PORT` is also the port Compose publishes on. It defaults to 5433 so the
stack can coexist with another local PostgreSQL on 5432.

### 2. Start the database

```bash
docker compose up -d
```

### 3. Apply the schema

```bash
psql -h localhost -p 5433 -U steam_user -d steam_analytics -f sql/create_tables.sql
```

`create_tables.sql` begins with `DROP TABLE IF EXISTS` — it is an initial-setup
script and it destroys a populated database. Run it once, on an empty one.

Then apply migrations with the runner, which tracks what has already been applied
in `schema_migrations` and is safe to re-run:

```bash
python -m src.main migrate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the pipeline

Run as a module — `python src/main.py` fails on the `from src.db import ...`
imports.

```bash
# Full daily pipeline (SteamSpy → Steam Store → Twitch → IGDB)
python -m src.main daily

# Or run individual steps
python -m src.main steamspy-daily                     # SteamSpy catalogue snapshot
python -m src.main steam-store-enrich                 # enrich games with Steam Store metadata
python -m src.main twitch-streams                     # Twitch stream snapshot
python -m src.main igdb-enrich-steam                  # link Steam games to IGDB
python -m src.main generate-twitch-igdb-candidates    # Twitch→IGDB fuzzy match candidates
```

`python -m src.main --help` lists all 14 subcommands.

---

## Running tests

```bash
pytest
```

CI runs pytest and ruff on every push via GitHub Actions.

---

## How the pipeline works

Raw JSON is always saved to `data/raw/` before loading into the database. Extract and load are separate steps — if a load fails, you can re-run it against the saved raw file without hitting the API again.

Raw file layout:
```
data/raw/{source}/{request_type}/{YYYY-MM-DD}/{descriptor}_{YYYYMMDD_HHMMSS}.json
```

Transform functions in `transform.py` are stateless — they take a raw dict and return a typed dict. No I/O happens inside them, making them easy to test in isolation.

Upsert strategy: Steam Store metadata wins over SteamSpy for stable fields (name,
developer, publisher); SteamSpy wins for metrics (CCU, review counts, price),
which it updates daily. `game_snapshots` upserts on `(appid, snapshot_date)` and
re-running a day is safe.

Not every write is like that yet. The Twitch snapshot loader conflicts on a key
that includes its own insert timestamp, so it never matches a previous run and
duplicates already exist in the database; the mapping-candidate upsert overwrites
`status`, which discards manual review. Both are Phase 0 in
[`ROADMAP.md`](ROADMAP.md) and are listed here rather than glossed over, because
"all writes are idempotent" is exactly the kind of claim a reader should be able
to check.

---

## Twitch → IGDB mapping

Twitch categories and IGDB games are different databases with different names and IDs. The pipeline builds a mapping between them in two ways:

- **High-confidence**: Twitch Helix returns an `igdb_id` field directly — these are inserted as `auto_approved`
- **Fuzzy match**: RapidFuzz compares normalized game names — results go in as `pending` for manual review

The `twitch_igdb_mapping_candidates` table holds all candidates with their match score and status.

---

## Airflow DAGs

Three DAGs run on schedule:

| DAG | Schedule | What it does |
|---|---|---|
| `steam_etl_daily` | 06:00 UTC daily | SteamSpy snapshot, Steam Store enrichment, Twitch snapshot, IGDB enrichment |
| `steam_etl_weekly` | Sunday 03:00 UTC | the same four steps, strictly chained, with smaller enrichment budgets |
| `steam_etl_mapping` | Sunday 12:00 UTC | regenerate Twitch→IGDB mapping candidates |

Caveats worth knowing before trusting the table: in the daily DAG only
`steam_store → sleep 1800 → igdb_enrich` is chained, so SteamSpy and Twitch start
at the same moment as the enrichment that reads their output — new appids wait a
day to be enriched. No DAG runs dbt, and `dbt-core` is not in
`requirements.txt`, so the transformation layer is currently unreachable from the
scheduler. Both are Phase 0/2 work.

---

## Roadmap

Phases, done-criteria and the current measured state of the database are in
[`ROADMAP.md`](ROADMAP.md). The short version:

1. Restart collection and fix the known idempotency defect
2. **Fix cross-platform identity** — today only 163 of 978 observed Twitch categories resolve to a Steam game, which bounds every number downstream
3. Restructure the warehouse into `raw` / `staging` / `marts`
4. Sample Twitch honestly — per stream, every four hours, aggregated to viewer-hours
5. Publish divergence: rank gap first, residual-from-expected once genre coverage allows
6. YouTube as a second attention source, inside its quota
7. Bought-exposure candidates, once there is enough history