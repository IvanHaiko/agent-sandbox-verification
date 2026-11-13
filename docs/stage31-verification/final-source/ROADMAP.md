# Roadmap — steam-etl

Active plan as of 2026-08-11. `ARCHITECTURE.md` says what the thing is; this
says in what order it gets built and how each step is known to be finished.

Each phase has **done-criteria that are numbers or commands**, not adjectives.
"Coverage improved" is not a done-criterion; "resolved ≥ 600 of 978 observed
Twitch categories, reported by `mart_identity_coverage`" is.

---

## Where the project stands

Measured 2026-08-11 against the live database:

| | |
|---|---|
| `games` | 45 502, of which 9 648 (21%) have Steam Store metadata |
| `game_snapshots` | 167 760 rows over **6 days**, 8–15 May 2026 |
| `twitch_game_snapshots` | 1 464 rows, 978 categories, **6 samples on 4 days**, 10–15 May 2026 |
| `igdb_games` / external links | 24 542 / 28 076 (16 366 Steam) |
| Twitch → Steam resolvable | **162 of 978 categories — 9.6% of observed attention** |
| mapping candidates | 234 `auto_approved`, 1 152 `pending` |

Collection has been stopped since 15 May 2026.

---

## Phase 0 — Stop the damage

A code review on 2026-08-11 returned **blocked**. Three of these defects make the
data worse on every scheduled run, so nothing is restarted until they are fixed.

**Corrupting, fix first:**

- [x] `twitch_game_snapshots` re-keyed on `(sample_hour, twitch_game_id)`
      (2026-08-12, migrations 008/010/012). `sample_time` now comes from the
      raw file's `fetched_at`, and `sample_time_source` records whether it is
      real (`bronze`, 2 runs) or the load clock standing in for it
      (`load_clock`, 4 runs whose bronze is gone). Verified by loading both
      surviving raw files twice each: 1 464 rows throughout.
- [x] `upsert_twitch_igdb_mapping_candidate` no longer overwrites `status`
      (2026-08-12). Verified against live data: re-upserting an
      `auto_approved` candidate with `status='pending'` on the input left it
      `auto_approved`.
- [x] `igdb-enrich-twitch` records every search attempt (2026-08-12,
      migrations 009/011). Empty results bump `igdb_search_attempts`, errors
      bump a separate `igdb_search_errors` so a failure to *ask* never spends
      the budget for an actual *answer*. Backlog ordering is now never-searched
      first, then oldest, then by peak viewers — it was alphabetical, which
      spent the whole budget on names starting with digits. Verified: backlog
      740 → 739 after one recorded attempt, head moved off Dota 2.

**Blocking the metric path:**

- [x] Steam Store failures now write bronze (2026-08-12). Every call saves an
      envelope (`"envelope": 1`) whose `outcome` is one of `ok`, `refused`,
      `not_found`, `redirected`, `transport_error`, so "Steam said no",
      "no wrapper for this appid" and "we could not ask" stop collapsing into
      one string. The old 3 148 files are untouched and read as legacy.
      `transport_error` carries `fetched_at = NULL` and `body = NULL` — no
      answer arrived, so neither exists — and there is a test for that
      invariant.
- [x] `is_free` no longer fabricated (2026-08-12, migration 013). SteamSpy now
      writes `FALSE` when `price > 0` and `NULL` when `price == 0`, keeping the
      two thirds of the signal that holds and asserting nothing for the rest.
      The 6 100 unconfirmed `TRUE` values were nulled; `FALSE` was deliberately
      left alone. Live check returns `free = 834, free_unconfirmed = 0`.
      Affected appids archived in `data/audit/`.
- [x] Steam `store_game_id` is sometimes a comma-separated list of appids
      (16 rows) — killed the identity join, and `mart_top_twitch_games` only
      survived its `CAST(... AS INTEGER)` because the plan never reached those
      rows (2026-08-13, migrations 016/017). `igdb_game_store_links` gained two
      `GENERATED ALWAYS ... STORED` columns: `steam_appid INTEGER` (the cast,
      moved from the marts into the schema, NULL for a bundle and for every
      non-steam row) and `is_bundle BOOLEAN` (NULL for non-steam — we have never
      asked whether an Epic uid packs several ids). The verbatim uid stays in
      `store_game_id`; 16 366 steam links before and after, all 91 packed appids
      still recoverable. Every mart and `sql/analytics/` query now joins on the
      typed column, and bundles fall out on their own because NULL never equals
      an appid — no `WHERE NOT is_bundle` anywhere.
      **This is a correctness fix, not a coverage one.** The 16 bundles still
      do not resolve; a crash was replaced with an honest NULL. Of the 91 packed
      appids, 19 exist in `games`, 18 of those already have their own
      single-appid link, and exactly one (1257290, Atelier Ryza 2) is in `games`
      with no other link — Phase 1's problem.

**Housekeeping:**

- [ ] `admin/admin` is hardcoded in the tracked `docker-compose.yml` and is in
      git history; `.env.example` defines the variables nothing reads
- [ ] `docker compose up` a second time leaves the webserver dead: the
      `&&` chain breaks on "user already exists" while the scheduler keeps running
- [ ] Add `dbt-core` / `dbt-postgres` to `requirements.txt` and mount
      `steam_analytics/` into the Airflow container. **Corrected 2026-08-12:**
      this is about reaching dbt *from orchestration*. dbt was never missing
      locally — `.venv` has dbt-core 1.12.0-b1 and dbt-postgres 1.10.0. What
      made it look absent was `~/.dbt/profiles.yml` still pointing at port
      5432 after the database moved to 5433. The profile now lives in
      `steam_analytics/profiles.yml`, in the repository, reading `.env`
      through `env_var` with 5433 as the port default. The earlier wording
      ("dbt is unreachable") sent the diagnosis to the wrong place.
- [ ] Migration `006` is genuinely absent; note that the runner sorts by
      filename, so adding it later would apply it *after* `007`
- [x] `.pytest_tmp/` and `.pytest_cache/` ignored (2026-08-11)

**Raised by the review of the Phase 0 fixes (2026-08-12), deliberately deferred:**

- [x] **Tests that execute SQL** (2026-08-13). 45 of them, against a separate
      `steam_analytics_test` database built from `create_tables.sql` plus the
      full migration chain and dropped afterwards. Three levels: the schema
      proven by *violating* its constraints, every loader run twice against
      frozen bronze fixtures with a content digest, and every read query
      executed for real. Fixtures are cut from `data/raw/`, never written by
      hand, so they carry the anomalies nobody would invent — `price: "0"` on
      four delisted games, Twitch categories with no `igdb_id`, a Store response
      describing a different appid. CI now runs a Postgres service with
      `REQUIRE_DB_TESTS=1`, so a skip is a failure rather than a green tick.
      165 tests, ruff clean. Still open below: the 120 pre-existing tests that
      mock the connection remain, and new ones of that shape should not be
      written.
- [ ] Four DB functions in `main.py` now open a connection per row (was two).
      `record_igdb_search_attempt` and `record_igdb_search_error` differ by one
      column and belong in `load.py` as one function with an outcome parameter —
      the module map says `load.py` owns every upsert.
- [ ] One expired IGDB token benches up to `--limit` categories for
      `--retry-after-days` (30) with `igdb_search_attempts` still 0. An error
      should get its own, shorter cooldown.
- [ ] `record_igdb_search_error` runs inside `except` with nothing around it,
      and it needs the database that probably just failed. A DB restart mid-run
      now aborts the task instead of logging and continuing.
- [ ] A bookkeeping failure *after* a successful search is recorded as an
      error: IGDB answered, results are loaded, but the category reads as
      "could not ask" and returns every 30 days forever.
- [ ] A same-hour re-run overwrites only the games present in the newer sample
      and leaves the rest, producing an hour that matches no single observation.
      `DELETE` + `INSERT` per `sample_hour` would remove the class.
- [ ] `--max-attempts 0` does not disable the backlog: never-searched rows
      still qualify through the `IS NULL` branch.
- [x] `Twitch → Steam resolvable` settled (2026-08-12). The spread was
      `count(*)` versus `count(distinct twitch_game_id)`: 188 IGDB games hold
      more than one Steam link, so the join fans out. The honest figures are
      **162** resolved and **180** with a Steam link. Measurements moved into
      Phase 1 below.
- [ ] Handoff to `warehouse`: `snapshot_time` now means "row load time".
      Rename it `loaded_at` and point the dbt models and `sql/analytics/` at
      `sample_time`.

**Raised by the review of the test suite (2026-08-13):**

- [ ] **Migration *content* is untested.** The chain is only ever applied to an
      empty database, so a data-repair migration with a wrong predicate ships
      green: rewriting `014`'s backfill to `WHERE FALSE`, and neutering `010`'s
      targeted `sample_time` repair, both left 165 tests passing. Closing this
      needs a harness that seeds pre-migration state and then applies one
      migration — a different mechanism from the current build-from-scratch
      fixture, which is why it is a task rather than a patch. This is how `008`
      shipped.
- [ ] The envelope **writer** in `src/extract_*.py` is never proven to agree
      with the reader: outcome classification is exercised only through
      fixtures already on disk.
- [ ] `main.run_*` orchestration (backlog → fetch → load → tally) has no
      database-level coverage, and that is exactly where the 26-appid
      backlog-head defect lived.
- [ ] `REQUIRE_DB_TESTS=1` only turns *server unreachable* into a failure. It is
      not a floor on how many database tests ran, so deleting or renaming a test
      file out of `testpaths` restores a green-for-the-wrong-reason CI.
- [ ] `mark_twitch_category_as_excluded` is the one database-writing function
      with no real-SQL execution anywhere. Its SQL is valid today (checked by
      hand), so this is a gap rather than a defect.

**Raised by the review of the CLI contract safety net (2026-09-07, task 001):**

- [ ] **`tests/test_dag_cli_contract.py`'s count guard is guarded by
      construction, not by assertion.** Every tracked `bash_command` is
      double-quoted, holds exactly one invocation, and sits directly in
      `dags/`, so narrowing `BASH_COMMAND_RE` to double quotes, `finditer` to
      `search`, or `rglob` to `glob` each leaves the two contract tests green
      (measured 2026-09-07, one mutation at a time: `2 passed` in all three
      cases). The extraction is correct today; nothing proves it stays
      correct. Closing this needs a fixture DAG tree carrying a single-quoted
      `bash_command`, two chained invocations in one string, and a DAG in a
      subdirectory. The docstring has been corrected to claim only what it
      proves.

- [ ] **Two concurrent test runs against the same server destroy each other.**
      `tests/conftest.py:88` drops and recreates a fixed database name
      (`steam_analytics_test`, `DROP DATABASE IF EXISTS ... WITH (FORCE)`) in a
      session-scoped fixture, so a second `pytest` process on the same
      PostgreSQL — another agent, a second terminal, or two CI jobs sharing a
      service — kills the first one's database mid-run. Observed 2026-09-07:
      the suite alternated between `178 passed` and `13 failed, 132 passed,
      33 errors` (`database "steam_analytics_test" does not exist`, `relation
      "games" does not exist`, `deadlock detected`) while a review agent was
      running its own pytest. Reproduction: run the suite twice concurrently.
      With `POSTGRES_TEST_DB=steam_analytics_test_lead` it is `178 passed`
      three runs in a row. Fix is a per-process suffix (pid, or
      `PYTEST_XDIST_WORKER`) on the database name.

- [ ] **The dispatch chain in `main()` has no `else:`** (`src/main.py:1618-1746`).
      An `args.command` the chain does not recognise — reachable when a parser
      name and a branch string drift apart — makes `main()` exit 0 having done
      nothing, and an Airflow `BashOperator` reads that as success. This is why
      a deleted branch is a *silent* failure rather than a crash. Reproduction:
      delete `elif args.command == "twitch-games-lookup":` and run
      `python -m src.main twitch-games-lookup --ids 123` — exit code 0, no work.
- [ ] **`main()`-level argument validation is covered by nothing.** Dropping
      `if args.page < 0: raise ValueError(...)` or `if args.appid <= 0: raise
      ValueError(...)` each leaves the suite green — demonstrated at
      `130 passed, 48 skipped`, i.e. with PostgreSQL unreachable and a quarter
      of the suite skipping; the baseline with the database up is `178 passed`.
      Uniform across all 14 subcommands, so this is a gap rather than a
      regression. Task 001's coverage should not be read as covering it.
- [ ] **`dags/.ipynb_checkpoints/steam_etl_daily-checkpoint.py`** is a complete
      DAG file, dated 14 May 2026, carrying `dag_id="steam_etl_daily"` and four
      `bash_command`s. `.ipynb_checkpoints/` is now in `.gitignore` (task 001),
      so it can no longer be swept in by `git add .` — but the file is still on
      disk, and Airflow's DagBag scans the dags folder recursively, so if the
      folder is mounted as-is it publishes a duplicate `dag_id`. Deleting it is
      Ivan's call. `tests/test_dag_cli_contract.py` deliberately skips
      dot-directories: counting them made the expected invocation count
      machine-dependent (15 locally, 11 on a clean checkout).

**Raised by the review of the bundle-uid fix (2026-08-13):**

- [ ] **Silent row loss in `igdb_game_store_links`, and the largest thing the
      review found.** `src/load.py:431` conflicts on the *global* key
      `(store, store_game_id)` and does `DO UPDATE SET igdb_game_id =
      EXCLUDED.igdb_game_id`, so when two IGDB games name the same appid the
      later load overwrites the earlier link instead of keeping both. Replaying
      all 2 155 archive files through `extract_igdb_store_links` yields 7 814
      distinct `(igdb_game_id, store, uid)` triples, of which **137 are absent
      from the table** (135 steam, 2 microsoft) — and every one of them exists
      under a *different* `igdb_game_id`, e.g. raw says `(8998, steam, 226620)`
      while the table holds `51752`. Failure: a Twitch category auto-approved to
      IGDB 8998 publishes a NULL appid although the archive can resolve it.
      Pre-existing, unrelated to this diff, and hard rule 6's failure class.
- [ ] **Fan-out risk in `mart_top_twitch_games`.** It joins the links table on
      `igdb_game_id` with no uniqueness guarantee, and 6 auto-approved IGDB
      games carry two steam links each (igdb `1338` → `233450` and `1521270`),
      so the pre-`LIMIT` result is 984 rows for 978 categories. None reach the
      top 50 today, so nothing is duplicated in the published table — the day
      one of the six does, the category is published twice and evicts the 50th.
- [ ] No test pins that `steam_appid` / `is_bundle` refuse a direct write,
      although `test_success_flag_cannot_be_written_directly` establishes
      exactly that pattern for `steam_store_success`. Also
      `tests/test_loaders_idempotent_db.py:329` asserts `>= 5` where the exact
      stable count is 8 — weak enough to survive a fixture record being dropped.
- [ ] `src/main.py:744` (`has_igdb_steam_link`) still compares `store_game_id`
      as text. Results are identical today (checked), so this is the last
      inconsistency rather than a defect.
- [ ] `ruff format --check .` flags ~15 files repo-wide, none of them touched by
      recent work. Worth one cleanup pass so the check is green and a real
      regression is visible.

**Raised by the review of the Steam Store fixes (2026-08-12):**

- [ ] **27 appids whose response describes a different game.** Steam answers
      `success: true` but with another `steam_appid` — 100→80, 2130→2100,
      2525→2520, 8640→8780, 10190→10180, 12370→1620, 12380→1620, 17340→17330,
      25860→42890, 33229→33220, 33530→33520, 34440→3900, 34450→3990,
      34460→8800, 34470→16810, 35010→35140, 42710→42700, 47830→47790,
      56437→56400, 99830→108800, 115300→42680, 201270→34330, 202990→202970,
      209170→209160, 209660→209650, 223870→223810, 336390→238210. Recorded as
      outcome `redirected` so they stop being re-fetched, but the pattern
      looks like merged or superseded catalogue entries — i.e. **duplicates in
      the game reference**, which matters for Phase 1's identity spine.
- [ ] ~6 500 *successful* enrichments also have no bronze file (3 148 files on
      disk against 9 648 `ok` rows). Unrecoverable retroactively — noted so
      nobody plans a replay-from-bronze that silently covers a third of it.
- [ ] `run_steam_store_enrich` ordering, prioritisation and daily budget shape
      stay open — **note that the failure counters and cooldown are already
      done** (migrations 014/015), so this item is smaller than it looks. It is
      the Phase 5 entry below, not a fresh defect.

**Done when:** three consecutive days land unattended, and every loader has been
run twice against the same input with an unchanged row count — verified, not
assumed.

---

## Phase 0.5 — Make src/main.py readable

Not a data goal. `src/main.py` is 1 750 lines and is the first file anyone
opening this repository reads: 27% raw SQL, 27% argparse and dispatch, 46%
pipeline orchestration, 62 lines of pure functions. Five steps, each a task
card, each a pure move with its tests moving in the same step and no re-export
shims. The four forks were settled 2026-09-07 and are recorded in
`tasks/001-cli-contract-safety-net.md`.

- [x] 001 — CLI contract safety net (2026-09-07). 14 subcommands, dispatch
      coverage for 8 before and 14 after; the command lines in `dags/*.py` are
      now fed to the live `parse_args()`, not matched as a bare token. Two
      review passes, both returning **blocked**. `178 passed`.
- [ ] 002 — `src/matching.py`: `normalize_game_name`, `calculate_name_score`,
      `NON_GAME_TWITCH_CATEGORIES`, with their tests.
- [ ] 003 — `src/queries.py` for the 6 read queries; the 4 writers move to
      `src/load.py`, which the module map already says owns every upsert.
      Done when `cur.execute` no longer appears in `src/main.py`.
- [ ] 004 — `src/pipelines/` split by domain: `steamspy`, `steam_store`,
      `igdb`, `twitch`, `daily`. Done when no `run_*` remains in `src/main.py`.
- [ ] 005 — `src/cli.py` takes `parse_args` and `main`. `src/main.py` stays the
      entry point — all 12 DAG `bash_command`s address `python -m src.main` —
      and shrinks to a few lines.

Afterwards, and not before: the three related backlog defects (a connection
opened per row, the two `record_igdb_search_*` functions merged into one with an
outcome parameter, and `has_igdb_steam_link` still comparing `store_game_id` as
text) become a small diff on laid-out code. `src/load.py` at 1 145 lines is the
next candidate after that, as its own decision.

---

## Phase 1 — The identity spine

The highest-value fix in the project. The review located the loss more precisely
than the original estimate did:

Re-measured 2026-08-12, counting distinct categories and weighting by attention.
The second column is the one that matters: a category is worth what it is watched
for, not one row.

| stage | categories | % | viewers | % |
|---|---|---|---|---|
| observed in a Twitch sample | 978 | 100 | 5 774 229 | 100 |
| carry a Helix `igdb_id` | 915 | 93.6 | 3 186 589 | **55.2** |
| **that id exists in local `igdb_games`** | **234** | 23.9 | 2 153 283 | 37.3 |
| has a Steam store link | 180 | 18.4 | 732 024 | 12.7 |
| resolves to a row in `games` | 162 | 16.6 | 552 159 | **9.6** |

Divergence today could therefore be computed over **9.6% of observed attention** —
materially worse than "162 of 978" suggests, because the categories that survive
the chain are not the ones people watch.

The 915 → 234 collapse happens at an INNER JOIN against an `igdb_games` table
that was only ever filled by name search from the Steam side. It is upstream of
the store-link problem, so fetching `external_games` alone does not fix it.

**The first step down is a different problem entirely.** 100% → 55.2% is not all
junk categories. Twitch itself supplies no `igdb_id` for its oldest categories,
and two of them are among the largest Steam games in the sample:

| category (no Helix `igdb_id`) | viewers | % of all |
|---|---|---|
| Just Chatting | 990 039 | 17.15 |
| **Counter-Strike** (id 32399) | 440 909 | **7.64** |
| **Dota 2** (id 29595) | 352 001 | **6.10** |
| IRL | 268 823 | 4.66 |
| Special Events | 137 482 | 2.38 |

Of the 63 categories without an `igdb_id`, most are genuinely not games — Just
Chatting, IRL, Slots, ASMR, Music, Art — and excluding them is correct. But
Counter-Strike and Dota 2 alone carry **13.7% of all observed attention, more
than the entire currently resolvable set (9.6%)**. Hand-mapping five identifiers
covers more ground than any amount of crawling.

- [ ] **Rung 0: a version-controlled seed of manual identifiers** for
      high-attention categories where Twitch supplies no `igdb_id` —
      Counter-Strike, Dota 2, Chess, Warcraft III, Pokémon FireRed/LeafGreen.
      This is deterministic and auditable, not fuzzy matching: a human wrote the
      pair down and it is reviewable in a diff. Highest precision rung, so
      nothing may overwrite it.
- [ ] Mark non-game categories explicitly (Just Chatting, IRL, Special Events,
      Slots, Sports, ASMR, Art, Music, DJs, Talk Shows, Always On, Pools,
      Animals, Retro) so the coverage denominator can exclude what will never map
- [ ] Fetch IGDB games by id (`GET /v4/games?where=id=(...)`) for every Helix
      `igdb_id` we hold — the FK on `mapping_candidates.igdb_game_id` rejects
      rows for games absent from `igdb_games`, so this comes first
- [ ] Resolve identity via IGDB `external_games` by `uid = appid`, both directions
- [ ] Enforce the resolution ladder in SQL: `upsert_twitch_category` currently
      overwrites `igdb_game_id` and `mapping_method` unconditionally, so
      precedence depends on call order
- [ ] Build `marts.dim_game` with `match_method` and `match_confidence`
- [ ] Publish `marts.mart_identity_coverage` — resolved vs **observed**, not vs
      the enriched subset the way `mart_igdb_coverage` does it today
- [ ] dbt test that fails the build when coverage regresses
- [ ] Keep fuzzy candidates quarantined — `pending` never reaches a mart

**Done when:** open — the target needs a denominator, and picking one is a real
choice rather than a detail. Three defensible forms, to be settled before Phase 1
starts:

1. **Share of observed attention** — resolved viewers / all observed viewers.
   Honest, one number, but its ceiling is ~72%: Just Chatting and IRL will never
   map to a Steam appid, so the metric can never reach 100% and a reader has to
   be told why.
2. **Share of game attention** — same, with categories marked non-game excluded
   from the denominator. Reaches 100% in principle, at the cost of a judgement
   call about what counts as a game, made by us and visible in a seed file.
3. **Count of categories** (the original "≥ 600 of 978"). Simplest to state and
   the least informative: it weights Pokémon FireRed the same as Counter-Strike,
   which is how the 9.6%-of-attention problem stayed invisible until today.

Recommendation: publish 1 and 3 side by side and set the target on 2 — the first
two make the ceiling explicit, and the third is what a reader will ask for
anyway. Whatever is chosen, no fuzzy match appears in any mart.

---

## Phase 2 — Warehouse layers

The dbt project has **no schema files at all** — `find steam_analytics/models
-name "*.yml"` returns nothing. Zero tests, zero documented columns across six
staging models and six marts. `dbt test` passes today by testing nothing.


- [ ] Create `raw` / `staging` / `marts` schemas
- [ ] Move loader-owned tables into `raw` with `ALTER TABLE ... SET SCHEMA`, source-prefixed names
- [ ] Qualify table names in `src/load.py`; no other loader changes
- [ ] dbt `sources.yml` over `raw`; staging views; marts rebuilt as `dim_*` / `fct_*` / `mart_*`
- [ ] Key tests (`unique`, `not_null`) on every model's declared grain
- [ ] Drop the old `mart_*` tables from `public`

**Done when:** `dbt build` is green including tests, `public` holds no project
tables, and every model has a declared grain with tests on it.

---

## Phase 3 — Honest attention measurement

- [ ] Store streams per row: `(sample_time, twitch_game_id, user_id, viewer_count)`
- [ ] Sample every 4 hours instead of once a day
- [ ] Roll up to daily viewer-hours per game
- [ ] Compute top-3 channel concentration per game per day

**Done when:** seven consecutive days at six samples per day, and viewer-hours
per game per day exist for every mapped game that appeared in any sample.

---

## Phase 4 — Divergence v1 (rank gap)

- [ ] `marts.mart_attention_divergence` with `steam_rank`, `twitch_rank`, `rank_gap`
- [ ] Rank-stability check: day-over-day rank correlation of the top and bottom 50
- [ ] Face-validity check: where spectator-native and single-player genres land

**Done when:** both checks are run against real data and reported with numbers.
If rank stability is low, the metric is noise and the phase ends in a written
finding rather than a dashboard — that is a valid outcome, not a failure.

---

## Phase 5 — Genre coverage and divergence v2 (residual)

**SteamSpy contributes no genres at all.** The `request=all` endpoint returns no
`genre` field — checked across all 33 raw files, 33 000 records, zero present.
Every genre in the warehouse came from the Store API, and running the daily DAG
for another year moves genre coverage by exactly zero. Worse, the enrichment
backlog query keeps re-selecting games Steam has already refused: 8 840 of the
18 512 checked games still satisfy it, with no failure counter and no backoff.
Fixing the backlog query is a precondition for this phase, not a detail of it.

- [x] Give the enrichment backlog a failure counter and backoff so it drains
      (2026-08-12, migrations 014/015). Cooldown is per outcome, not one number
      for everything: `ok` 30 days, `refused` and `failed_legacy` 30, `not_found`
      90, `redirected` never again, `transport_error` an escalating 1-2-4-8-16-30
      days. Only `transport_error` counts against anything, on its own counter,
      and it resets on any answer — a fault of ours must not be a harsher
      consequence than a refusal by Steam. **What remains of this phase item is
      ordering and budget shape, below, not the counters.**
- [ ] Finish Steam Store enrichment in budgeted daily batches (21% → target 80% of *mapped* games)
- [ ] IGDB genres as fallback where Steam Store has none
- [ ] Log-log fit per genre via `regr_slope` / `regr_intercept`; `divergence_z` as residual
- [ ] Agreement check between v1 ranks and v2 residuals at the extremes

**Done when:** ≥ 80% of mapped games carry a genre, the residual metric is
published with its coverage stated next to it, and v1 and v2 agree at the
extremes or the disagreement is explained in writing.

---

## Phase 6 — YouTube as a second attention source

- [ ] Verify the quota arithmetic before building (10 000 units/day, `search.list` = 100)
- [ ] Watchlist of tracked games with a rotation policy; log what the rotation skipped
- [ ] Upload counts and view counts per tracked game per day
- [ ] Disambiguation strategy for noisy names, with its error rate measured

**Done when:** the watchlist runs inside quota for seven days without a quota
error, and the rotation policy publishes what it did not cover.

---

## Phase 7 — Bought-exposure candidates

Needs at least 30 days of history from Phase 3.

- [ ] Per-game 14-day attention baseline and z-scores
- [ ] Candidate rule: attention z > 2, review-velocity z < 0.5, concentration above genre norm
- [ ] Candidate list with all three components visible and the caveat attached

**Done when:** the list is produced, hand-checked against a handful of known
sponsored campaigns, and the hit rate is written down — including if it is bad.

---

## Phase 8 — Serving and the portfolio story

- [ ] Dashboard (Metabase, already in the compose stack) over the marts
- [ ] `README.md` rewritten around the question the project answers, with an architecture diagram
- [ ] Cloud deployment decision: what moves, what it costs, what stays local

---

## Non-goals

- **Claiming a game bought its exposure.** We publish candidates with their
  evidence. The word "verdict" does not belong anywhere in this project.
- **Streaming ingestion.** This is the batch project by design; the streaming
  work lives in the separate capstone with a different domain.
- **Scraping around a rate limit or a consent gate.** If an API does not serve
  it, we do not have it.

---

## Open questions

- How much of the Twitch tail is missing at 6 samples/day? Unknown until Phase 3
  runs; it bounds every conclusion about small games.
- Does `review_velocity` actually track sales closely enough to serve as the
  conversion axis, or does the review lag swamp the campaign window?
- Is IGDB genre comparable to Steam Store genre, or do the two taxonomies need a
  mapping of their own before they can be mixed?
