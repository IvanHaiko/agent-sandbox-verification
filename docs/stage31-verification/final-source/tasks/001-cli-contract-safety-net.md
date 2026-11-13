# 001 — CLI contract safety net before the main.py refactor

status: accepted
opened: 2026-09-07
zone: ingestion

## Brief

`src/main.py` is 1750 lines and is about to be split across four steps
(`src/matching.py`, `src/queries.py` + `src/load.py`, `src/pipelines/`,
`src/cli.py`). Every one of those steps moves code that the Airflow DAGs reach
only through the command line: all 12 tasks in `dags/*.py` are `BashOperator`s
running `python -m src.main <subcommand> …`. The subcommand surface is therefore
a public contract, and nothing in the repository currently asserts that it
holds. This task builds the net **before** anything moves; it changes no
production behaviour.

Two gaps are measured, not assumed:

- `main()` has 14 `elif` branches (14 `subparsers.add_parser(` calls at
  `src/main.py:1286`–`1603`). `tests/test_main.py` has dispatch tests for 8 of
  them (`daily`, `igdb-search`, `igdb-enrich-twitch`, `igdb-enrich-steam`,
  `generate-twitch-igdb-candidates`, `twitch-streams`, `steam-store-enrich`,
  `migrate`). Six have no dispatch coverage at all: `steamspy-all-page`,
  `steamspy-daily`, `steam-store-appdetails`, `twitch-games-lookup`,
  `twitch-games-lookup-observed`,
  `generate-twitch-igdb-candidates-from-catalog`.
- Nothing connects `dags/*.py` to the parser. A subcommand could be renamed and
  the whole test suite stays green while three DAGs fail at runtime.

**Boundaries.** In scope: `tests/` only, plus `tasks/001-*.md`. Explicitly out
of scope: any edit to `src/`, `dags/`, `docker-compose.yml`, or the argument
surface itself. If a command turns out to be broken, that is an out-of-scope
finding, not a fix. Do not move any code — that is task 002 onwards.

**Done when.**

- Every one of the 14 subcommands has coverage asserting it reaches its intended
  callable with the arguments the CLI parsed. Enumerated from the parser or from
  an explicit table in the test — a table is acceptable only if a test also
  fails when the table and the parser disagree.
- Named mutations that must turn the suite red, each demonstrated by actually
  applying it and pasting the failing test name and pytest's summary line:
  1. delete the `elif args.command == "twitch-games-lookup":` branch from
     `main()`;
  2. delete the `elif args.command == "steamspy-all-page":` branch;
  3. rename the parser name `"twitch-games-lookup-observed"` to
     `"twitch-games-lookup-obs"` while leaving `dags/steam_etl_mapping.py`
     untouched;
  4. swap the callables of two branches (`steamspy-all-page` →
     `run_steamspy_daily`).
  Each mutation is reverted after it is demonstrated. `git diff` at the end must
  show no change under `src/`.
- For each new test, the check that **no existing test already catches its
  mutation** is run and its result recorded (mutation applied with the new test
  file deleted or deselected; suite still green ⇒ the gap was real).
- `python -m pytest tests/` green, count reported before and after.
- `ruff check .` clean on the files touched.

**Known risk.**

- A test that enumerates subcommands can be written so it enumerates *itself* —
  building the expected list from `parse_args()` and then asserting against the
  same object proves nothing. The DAG check has the same trap: parsing DAG
  files for command names and then feeding them to the parser is only meaningful
  if a name absent from the parser fails.
- `tests/test_main.py` monkeypatches attributes on the `src.main` module. A new
  dispatch test written the same way will keep passing after task 003 moves the
  callable elsewhere, while asserting on a stub the production path no longer
  calls. Prefer an assertion shape that would break loudly rather than silently
  once the callables live in other modules.
- The DAG files import `airflow`, which is not in `requirements.txt` for the
  local test environment. A check over `dags/*.py` must therefore read them as
  text, not import them, or it will skip in CI and prove nothing.

## Forks and decisions

**Boundary amendment (2026-09-07, lead, after the first review).** The card was
scoped `tests/` only. Two deliberate crossings, announced rather than made
quietly:

- `.gitignore` gains `.ipynb_checkpoints/`. The reviewer found an untracked
  complete DAG file at `dags/.ipynb_checkpoints/steam_etl_daily-checkpoint.py`
  carrying `dag_id="steam_etl_daily"`; Airflow's DagBag scans recursively, so a
  `git add .` publishes a duplicate DAG id. One line, and leaving it uncrossed
  risks a commit that is worse than the crossing.
- Non-blocking findings 3 and 4 are fixed in this return rather than deferred.
  Finding 4 makes the meta-test go red in task 003 for a *correct* change, and
  the obvious way out of a false red is to delete the assertion — which is
  finding 3. Deferring them means the next task starts by weakening the net this
  task exists to build.


Put to Ivan on 2026-09-07, before any code, as four forks in the refactor plan:

- **Where the SQL goes.** Options: (a) `src/queries.py` for reads + existing
  `src/load.py` for writes; (b) a single new `src/repository.py`; (c) a
  `src/queries/` package split by domain. **Chosen: (a)** — it matches the
  module map in `CLAUDE.md` ("`load.py` owns all upserts") and the open ROADMAP
  item that already says `record_igdb_search_attempt` / `_error` belong in
  `load.py`. Cost: `load.py` grows past 1300 lines and is itself a later
  refactor.
- **CLI library.** Options: (a) keep `argparse`, move it to `src/cli.py`;
  (b) rewrite on Typer/Click. **Chosen: (a)** — the 340 lines of `parse_args`
  are the interface description, not boilerplate, and a rewrite puts the DAG
  contract at risk for cosmetics. Cost: the ~40 lines of inline validation in
  `main()` stay imperative for now.
- **Scope.** Options: (a) pure move, no behaviour change; (b) move and fix the
  three related ROADMAP defects (connection-per-row, merging the two
  `record_igdb_search_*` functions, `has_igdb_steam_link` text comparison) on
  the way. **Chosen: (a)** — a diff that is entirely moves can be checked
  mechanically; a behaviour change hidden among 1700 moved lines cannot. The
  fixes become their own card afterwards, where they are a 30-line diff.
- **Entry point.** The plan Ivan brought proposed a root `main.py` delegating to
  `src/cli.py`. Rejected: `python -m src.main` is what all 12 DAG
  `bash_command`s and both DB test modules address. `src/main.py` stays the
  entry point and shrinks to a few lines in task 004.
- **Re-export shims.** Deliberately not used. Keeping
  `from src.pipelines.steamspy import run_steamspy_daily` in `src/main.py` for
  compatibility is exactly what produces tests that patch one object while
  another executes. Tests move with the code they cover, in the same step.

## Implementation

**Files changed** (all under `tests/`, plus this card):
- `tests/test_main.py` — added `import re`, `import sys`; six new
  `test_main_dispatches_*` tests for the previously-uncovered subcommands
  (`steamspy-all-page`, `steamspy-daily`, `steam-store-appdetails`,
  `twitch-games-lookup`, `twitch-games-lookup-observed`,
  `generate-twitch-igdb-candidates-from-catalog`); a
  `DISPATCH_TEST_BY_SUBCOMMAND` table plus
  `test_all_parser_subcommands_have_a_recorded_dispatch_test`, which
  enumerates the live argparse parser (not a hand list — see below) and
  fails if the table and the parser disagree, or if a table entry names a
  test function that does not exist.
- `tests/test_dag_cli_contract.py` (new) — reads `dags/*.py` as text (no
  `import airflow`), extracts every `bash_command="... python -m src.main
  <subcommand> ..."`, and asserts each subcommand is a live choice in the
  argparse parser, using the same live-enumeration technique.

**How subcommands are enumerated without self-enumeration.** Both new
"coverage" tests avoid the trap the brief names (building the expected list
from `parse_args()` and asserting against the same object). Instead they
feed the real parser an invalid command (`sys.argv = ["prog",
"__not_a_real_subcommand__"]`) and read the choice set argparse itself
prints in the usage line (`{choice1,choice2,...}`) via regex. That set is
then compared against something built independently: a hand-written table
in `test_main.py`, or the regex-extracted subcommands actually referenced
in `dags/*.py`. Verified live in this session:
```
$ .venv/Scripts/python -c "...sys.argv=['prog','__bogus_command__']; main.parse_args()..."
prog: error: argument command: invalid choice: '__bogus_command__' (choose from steamspy-all-page, steamspy-daily, steam-store-appdetails, steam-store-enrich, daily, igdb-search, igdb-enrich-twitch, igdb-enrich-steam, generate-twitch-igdb-candidates, twitch-streams, twitch-games-lookup, twitch-games-lookup-observed, generate-twitch-igdb-candidates-from-catalog, migrate)
```

**On the "known risk" about `monkeypatch.setattr(main, ...)` becoming a
silent no-op post-refactor:** not addressed with a new technique, because it
does not need one. `monkeypatch.setattr(obj, name, value)` defaults to
`raising=True` — it raises `AttributeError` immediately if `name` is not
currently an attribute of `obj`. Since the refactor plan explicitly rules
out re-export shims (a fork already decided in this card), once a callable
moves out of `src.main` in task 003+, `monkeypatch.setattr(main,
"run_steamspy_all_page", ...)` will error at the setattr call, not pass
silently on a stub nothing calls. All six new dispatch tests and the
existing eight follow this same idiom deliberately, for that reason.

**Commands run and real output.**

Baseline, before this task's changes (`test_main.py` only):
```
$ .venv/Scripts/python -m pytest tests/test_main.py -q
......................................
38 passed in 0.67s
```
Full suite before, DB unreachable at `localhost:5433` in this environment
(`Test-NetConnection -Port 5433` → `TcpTestSucceeded: False`), so the DB
fixtures self-skip via `conftest.py`'s `_server_reachable()` check
(`REQUIRE_DB_TESTS` was not set):
```
$ .venv/Scripts/python -m pytest tests/ -q
121 passed, 48 skipped in 260.86s (0:04:20)
```

After this task's changes:
```
$ .venv/Scripts/python -m pytest tests/test_main.py -q --collect-only
45 tests collected
$ .venv/Scripts/python -m pytest tests/test_dag_cli_contract.py -q --collect-only
2 tests collected
$ .venv/Scripts/python -m pytest tests/test_main.py tests/test_dag_cli_contract.py -q
...............................................
47 passed in 0.40s
$ .venv/Scripts/python -m pytest tests/ -q
130 passed, 48 skipped in 130.76s (0:02:10)
```
+9 tests total (7 in `test_main.py`, 2 in `test_dag_cli_contract.py`); same
48 DB-dependent tests skip for the same reason as before (Postgres
unreachable on 5433 — did not work around it, per instructions).

**Ruff.**
```
$ .venv/Scripts/python -m ruff check .
All checks passed!
$ .venv/Scripts/python -m ruff format --check tests/test_dag_cli_contract.py
1 file already formatted
```
`ruff format --check tests/test_main.py` reports 2 blocks it would
reformat — both pre-existing, in tests I did not touch
(`test_run_steam_store_appdetails`'s `monkeypatch.setattr(...
save_steam_store_raw_json ...)` line, and
`test_run_igdb_enrich_twitch_does_not_record_attempt_on_exception`'s
signature line). Confirmed pre-existing by `git stash` + re-running
`ruff format --check` against the untouched file — same two blocks, before
any of my edits existed. Left alone: editing them is a change to a test I
did not write, out of this task's boundary either way.

**Mutation evidence.** Each mutation was applied to `src/main.py`, the named
test run, its failure captured, then the mutation reverted (`git diff --
src/main.py` shown clean before/after each, and confirmed unchanged
overall at the end — see below). For each, the same mutation was then
re-verified with the new test(s) deselected, to show the gap was real (no
existing test already caught it).

1. **Delete the `elif args.command == "twitch-games-lookup":` branch.**
   ```
   FAILED tests/test_main.py::test_main_dispatches_twitch_games_lookup - AssertionError...
   1 failed, 44 passed in 0.53s
   ```
   With `test_main_dispatches_twitch_games_lookup` and the meta-coverage
   test deselected:
   ```
   42 passed, 3 deselected in 0.24s
   ```
   (3 deselected, not 2, because pytest's `--deselect` matches by nodeid
   prefix and `test_main_dispatches_twitch_games_lookup` is a prefix of
   `test_main_dispatches_twitch_games_lookup_observed`; re-ran with a `-k`
   expression that excludes only the exact test to confirm — still green:)
   ```
   $ pytest tests/test_main.py -q -k "(not test_main_dispatches_twitch_games_lookup or test_main_dispatches_twitch_games_lookup_observed) and not test_all_parser_subcommands_have_a_recorded_dispatch_test"
   43 passed, 2 deselected in 0.27s
   ```
   Gap confirmed real.

2. **Delete the `steamspy-all-page` branch.** (It is the leading `if`, not
   an `elif`, in the source; deleting it required promoting the following
   `elif "steamspy-daily"` to `if` to stay syntactically valid — same
   effect the brief describes.)
   ```
   FAILED tests/test_main.py::test_main_dispatches_steamspy_all_page - AssertionError...
   1 failed, 44 passed in 0.39s
   ```
   With that test (and the meta-coverage test) excluded via `-k`:
   ```
   43 passed, 2 deselected in 0.30s
   ```
   Gap confirmed real.

3. **Rename the parser choice `"twitch-games-lookup-observed"` →
   `"twitch-games-lookup-obs"`** (only the `subparsers.add_parser(...)`
   call; `dags/steam_etl_mapping.py` and the `elif` string in `main()` left
   untouched, as specified):
   ```
   FAILED tests/test_main.py::test_all_parser_subcommands_have_a_recorded_dispatch_test
   FAILED tests/test_dag_cli_contract.py::test_every_dag_subcommand_is_registered_in_the_cli_parser
   2 failed, 45 passed in 0.37s
   ```
   The DAG test's failure message names the exact break: `dags/*.py
   reference subcommands that are not registered in src/main.py's argparse
   parser: {'twitch-games-lookup-observed':
   ['...dags\\steam_etl_mapping.py']}`. With both new meta-tests deselected:
   ```
   45 passed, 2 deselected in 0.24s
   ```
   Gap confirmed real for both.

4. **Swap the callables**: the `steamspy-all-page` branch calls
   `run_steamspy_daily(start_page=args.page, max_pages=None,
   delay_seconds=65, snapshot_date=args.snapshot_date)` instead of
   `run_steamspy_all_page(...)`.
   ```
   FAILED tests/test_main.py::test_main_dispatches_steamspy_all_page - AssertionError: assert [('wrong_function_called', {'start_page': 3, 'max_pages': None, 'delay_seconds': 65, 'snapshot_date': '2026-05-09'})] == [(3, '2026-05-09')]
   1 failed, 44 passed in 0.47s
   ```
   Deviation from a literal run: the committed test only patches
   `main.run_steamspy_all_page`, so under this mutation the real
   (unpatched) `run_steamspy_daily` executes — which calls
   `fetch_steamspy_data`, a live HTTP request. This sandbox has no route to
   the internet, and the request hangs (no bounded DNS-resolution timeout
   observed; killed a run after 60s+ with no result). To get the pytest
   summary line without an indefinite hang, I temporarily added a second
   stub (`monkeypatch.setattr(main, "run_steamspy_daily",
   fake_run_steamspy_daily_TEMP_NETWORK_GUARD)`) to this one test *for the
   duration of this demonstration only*, ran it, captured the failure
   above (which shows the wrong function was called, with the wrong
   arguments), then removed the stub and restored the test to exactly its
   committed form (diffed clean afterward). With the test (and the
   meta-coverage test) excluded via `-k`:
   ```
   43 passed, 2 deselected in 0.28s
   ```
   Gap confirmed real. The committed test itself was never changed — only
   this one throwaway run used the extra guard, to keep the demonstration
   inside this environment's constraints rather than skip it.

**End state:** `git diff -- src/` shows only the one pre-existing,
unrelated change already present before this task started (`get_steam_games_for_igdb_enrichment`'s
`s.steam_appid = g.appid` join, from an earlier session) — confirmed
identical before and after every mutation cycle above. `git diff -- dags/`
is empty throughout.

**Deliberately not done:**
- Did not touch `src/` or `dags/` beyond the four temporary,
  fully-reverted mutations above.
- Did not edit any pre-existing test, including the two lines
  `ruff format` would still reformat in `test_main.py` (not mine, out of
  boundary either way).
- Did not attempt to make the DB-dependent test files (48 tests) run —
  Postgres is unreachable at `localhost:5433` in this environment; they
  skip via the existing `conftest.py` mechanism, as instructed, rather than
  being worked around.
- Did not investigate why a plain outbound HTTP request seems to hang
  indefinitely rather than fail fast in this sandbox (see Out-of-scope
  findings) — out of this task's zone.

### Second pass (2026-09-07, after the first review returned this task
`blocked`)

**Files changed this pass** (all under `tests/`, plus `.gitignore` and this
card — the announced boundary crossing):
- `tests/test_dag_cli_contract.py` — rewritten. Discovery is now
  `DAGS_DIR.rglob("*.py")` (was `glob`), so the untracked checkpoint copy at
  `dags/.ipynb_checkpoints/steam_etl_daily-checkpoint.py` is inside the
  contract. Extraction now matches both quote styles
  (`bash_command\s*=\s*(?:"([^"]*)"|'([^']*)')`) and uses `finditer` over
  `INVOCATION_RE = python -m src\.main\s+([^&\n]+)` so a second, `&&`-chained
  invocation in one `bash_command` string is not lost. A new test,
  `test_dags_reference_the_expected_number_of_subcommand_invocations`,
  asserts the extracted count equals a hardcoded `EXPECTED_INVOCATION_COUNT
  = 15` (measured directly against the current tree: 11 across the three
  tracked DAG files, the same 11 the reviewer counted before this pass's
  `rglob` switch put the checkpoint file in scope, plus 4 more — the
  checkpoint file duplicates 4 of `steam_etl_daily.py`'s 5 tasks). The old
  `test_every_dag_subcommand_is_registered_in_the_cli_parser` (subcommand
  token only) is replaced by
  `test_every_dag_command_line_parses_with_the_live_cli`, which
  `shlex.split`s each extracted invocation string and feeds it straight to
  `main.parse_args()` — the actual argparse parser runs the actual argument
  string, not a regex proxy for it.
- `tests/test_main.py` — `test_all_parser_subcommands_have_a_recorded_dispatch_test`
  gained two changes: (1) it now also asserts, per table entry, that the
  named dispatch test's source (`inspect.getsource`) contains the literal
  subcommand string, so repointing a table entry at an unrelated test no
  longer passes; (2) test-function resolution moved from `globals()` of this
  one module to a new helper, `_collect_test_functions(session)`, which walks
  `request.session.items` (added `request` as a fixture parameter) and reads
  `item.originalname`/`item.function` — this resolves a dispatch test
  wherever pytest actually collected it from, not only from this file.
  Added `import inspect`.
- `.gitignore` — added `.ipynb_checkpoints/`, per the boundary amendment
  already recorded above in "Forks and decisions". Did not delete the
  existing checkpoint file itself — that stays Ivan's call.

**Why `EXPECTED_INVOCATION_COUNT` is 15, not 11.** The brief's own text
("assert an exact expected count of extracted command lines (11 today)")
and the review's reproduction both predate the `rglob` switch this same
finding also asks for. Doing the `rglob` switch first and then counting
what it actually finds gives 15, not 11 — verified directly:
```
$ .venv/Scripts/python -c "... DAGS_DIR.rglob('*.py') ..."
[.ipynb_checkpoints/steam_etl_daily-checkpoint.py, steam_etl_daily.py, steam_etl_mapping.py, steam_etl_weekly.py]
... 15 `python -m src.main ...` invocations found (4 duplicated from the checkpoint file)
```
Hardcoding 11 while also switching to `rglob` would have made the new count
test fail immediately on a correct, no-mutation run — not a real
regression, just wrong arithmetic. If the checkpoint file is ever removed
from the tree (data-engineering judgment call, not this task's), this
constant drops back to 11 and needs updating in the same change.

**Mutation evidence, second pass** (each applied to a file outside `tests/`,
demonstrated, then reverted; `git diff -- src/ dags/` confirmed to return to
only the one pre-existing line, `src/main.py:523`'s
`s.steam_appid = g.appid`, after every cycle below):

1. **Blocking 1 reproduction — `--limit` renamed to `--max-observed` with
   `dest="limit"` preserved**, at `src/main.py:1576`-ish
   (`twitch_games_lookup_observed_parser.add_argument("--max-observed",
   dest="limit", ...)`), `dags/steam_etl_mapping.py` and `main()`'s `elif`
   left untouched:
   ```
   FAILED tests/test_dag_cli_contract.py::test_every_dag_command_line_parses_with_the_live_cli
   AssertionError: dags/*.py command lines that src/main.py's live argparse parser rejects: {'...steam_etl_mapping.py': 'twitch-games-lookup-observed --limit 500'}
   1 failed, 46 passed
   ```
   With that test deselected (`-k "not test_every_dag_command_line_parses_with_the_live_cli"`),
   run against the **full** suite (this is the mutation that motivated the
   whole return, so it was checked against everything, not just the two new
   test files):
   ```
   129 passed, 48 skipped, 1 deselected in 260.76s
   ```
   Gap confirmed real: none of the 130 previously-green tests, including all
   14 dispatch tests (which hand-build an `argparse.Namespace` and never run
   real argparse), notice this.

2. **Blocking 2 reproduction A — single-quoted `bash_command` naming an
   unregistered subcommand.** `dags/steam_etl_mapping.py:23` rewritten to
   `bash_command='cd /opt/airflow && python -m src.main
   twitch-games-lookup-obsolete --limit 500'` (single quotes; the
   double-quoted sibling line elsewhere is untouched):
   ```
   FAILED tests/test_dag_cli_contract.py::test_every_dag_command_line_parses_with_the_live_cli
   AssertionError: ...: {'...steam_etl_mapping.py': 'twitch-games-lookup-obsolete --limit 500'}
   1 failed, 1 passed
   ```
   (The count test stayed green here — same number of invocations, just a
   different subcommand string in one of them — which is correct: this
   mutation doesn't drop an invocation, it corrupts one, and the parse test
   is what catches corruption.)

3. **Blocking 2 reproduction B — a chained second, invalid invocation in one
   `bash_command`.** `dags/steam_etl_weekly.py:33` rewritten to
   `bash_command="cd /opt/airflow && python -m src.main twitch-streams &&
   python -m src.main not-a-real-subcommand"`:
   ```
   FAILED tests/test_dag_cli_contract.py::test_dags_reference_the_expected_number_of_subcommand_invocations
   FAILED tests/test_dag_cli_contract.py::test_every_dag_command_line_parses_with_the_live_cli
   2 failed
   ```
   Both the count test (16 found, not 15 — the chained invocation is now
   seen) and the parse test (the second invocation doesn't parse) catch it.

4. **Non-blocking 3 reproduction — table repointed at an unrelated,
   passing test.** `DISPATCH_TEST_BY_SUBCOMMAND["migrate"]` changed from
   `"test_main_dispatches_migrate"` to `"test_main_dispatches_daily"`
   (`test_main_dispatches_migrate` left in place, not deleted, to isolate
   this one change):
   ```
   FAILED tests/test_main.py::test_all_parser_subcommands_have_a_recorded_dispatch_test
   AssertionError: dispatch tests recorded in DISPATCH_TEST_BY_SUBCOMMAND do not mention the subcommand string they are claimed to cover: {'migrate': 'test_main_dispatches_daily'}
   1 failed, 44 passed
   ```
   Before this pass's fix, the same edit produced `129 passed` (per the
   review) with `migrate` silently uncovered; now it fails on the source
   check specifically, naming the exact mismatch.

5. **Non-blocking 4 demonstration (not a red/green mutation — a
   false-red check).** Moved `test_main_dispatches_steamspy_daily` verbatim
   out of `tests/test_main.py` into a scratch file,
   `tests/test_pipelines_steamspy_SCRATCH.py`, with its own `import
   argparse` / `from src import main`, coverage fully intact:
   ```
   $ .venv/Scripts/python -m pytest tests/test_main.py tests/test_pipelines_steamspy_SCRATCH.py -q
   45 passed in 0.28s
   ```
   `test_all_parser_subcommands_have_a_recorded_dispatch_test` passes — the
   `request.session.items` lookup found the moved test in the other file.
   Before this pass's fix, per the review, the identical move gave
   `AssertionError: dispatch test functions not found`. The scratch file was
   deleted and the block restored verbatim to `test_main.py` afterward
   (diffed clean against git HEAD's baseline for the surrounding lines).

**End state, second pass:** `git diff -- src/` and `git diff -- dags/` both
confirmed to show nothing beyond the one pre-existing `src/main.py:523`
line, after every mutation cycle above, including the full-suite run under
mutation 1.

**Commands run and real output, second pass.**
```
$ .venv/Scripts/python -m pytest tests/test_main.py tests/test_dag_cli_contract.py -q
...............................................
47 passed in 0.34s
$ .venv/Scripts/python -m ruff check src/ tests/
All checks passed!
$ .venv/Scripts/python -m ruff format --check tests/test_dag_cli_contract.py
1 file already formatted
$ .venv/Scripts/python -m ruff format --check tests/test_main.py
Would reformat: tests\test_main.py  (same two pre-existing blocks the first
pass identified and left alone — test_run_steam_store_appdetails's
save_steam_store_raw_json line and
test_run_igdb_enrich_twitch_does_not_record_attempt_on_exception's
signature line; confirmed via `ruff format --diff`, neither touched this
pass)
```
Full suite (`pytest tests/ -q`), same environment constraint as the first
pass (Postgres unreachable at `localhost:5433`, DB fixtures self-skip via
`conftest.py`):
```
$ .venv/Scripts/python -m pytest tests/ -q
130 passed, 48 skipped in 260.82s (0:04:20)
```
Identical to the counts the reviewer measured after the first pass — no
regression, no new failures, same 48 DB-dependent skips for the same reason
(`FATAL: password authentication failed for user "steam_user"` — port 5433
on this machine is `pg-week3`, another project's container, not this
project's compose service; not worked around, per instructions).

**Deliberately not done, second pass:**
- Did not fix the `else:`-branch gap on the dispatch chain or add
  `main()`-level argument validation coverage — both explicitly deferred to
  the backlog by the review, not this return.
- Did not delete `dags/.ipynb_checkpoints/steam_etl_daily-checkpoint.py` —
  only added it to `.gitignore`, per the boundary amendment. Deleting it is
  a decision about the working tree's history, not this task's to make.
- Did not re-run the first pass's mutations 2 and 4 (delete
  `steamspy-all-page`, swap `steamspy-all-page`'s callable for
  `run_steamspy_daily`) — unchanged by this pass (neither the branches nor
  the dispatch tests covering them were touched), and the review already
  confirmed both sound. Did re-run mutations 1 and 3 as a spot check after
  editing the meta-test they interact with; both still caught correctly.

## Out-of-scope findings

**Lead correction before the second review (2026-09-07).** The second pass set
`EXPECTED_INVOCATION_COUNT = 15` in `tests/test_dag_cli_contract.py`, counting
the four invocations inside `dags/.ipynb_checkpoints/steam_etl_daily-checkpoint.py`
— a file that is untracked and, as of this same task, gitignored. Measured:

```
previous version (bare rglob), this machine:     15
previous version (bare rglob), clean checkout:   11
current version, this machine:                   11
```

So the test would have failed on every clean CI checkout, and on Ivan's machine
the moment he deleted the checkpoint directory. `_dag_files()` now keeps `rglob`
— a DAG in a real subpackage must stay inside the contract, because DagBag scans
recursively — but skips dot-directories, which are tooling artefacts rather than
deployable code. The constant is 11. The checkpoint file itself moved to
`ROADMAP.md` as a defect, which is where a thing this task is not fixing belongs.
Changed in the main thread: one file, ~15 lines, no production change.


- **Steam Store/SteamSpy HTTP requests appear to hang, not fail fast, when
  the sandbox has no route to the internet.** `src/extract_steamspy.py`
  passes `timeout=30` to its `requests` call (line 66), which should bound
  a call to at most ~30s once a connection attempt starts, but a live run of
  the real (unmocked) `run_steamspy_daily` in this environment did not
  return within 60s and was killed. This looks like it is stuck earlier —
  in DNS resolution / connection establishment, which `requests`' `timeout`
  parameter does not always bound tightly on Windows — rather than in the
  read phase the 30s timeout covers. Reproduction: with network
  connectivity disabled/unreachable, run
  `python -c "from src.extract_steamspy import fetch_steamspy_data; fetch_steamspy_data(request_type='all', page=0)"`
  and observe it does not return or raise within 60s. Not investigated
  further — this is an extraction-layer concern (`src/extract_steamspy.py`,
  possibly `src/extract_steam_store.py` too, both outside what this
  test-only task touches) and needs to be checked against a real network
  outage, not just an unreachable sandbox, before concluding anything about
  production behavior.
- `dags/.ipynb_checkpoints/` is untracked and present in the working tree
  (unrelated to this task; noticed via `git status` while confirming the
  `dags/` boundary was not crossed).

## Review

**Verdict: blocked** (2026-09-07, first return of at most two).

Mutations were applied in a scratch copy of the repository, never in the working
tree; `git status` was byte-identical before and after the review.

**Confirmed sound.** All four named mutations turn the suite red, and each was
shown green with the new tests deselected, so all six gaps were real. The
meta-test genuinely reads the live parser: a 15th subcommand added to
`parse_args` with the table left alone fails it. The
`monkeypatch.setattr(main, ...)` idiom does **not** become a silent no-op after
the later refactor steps — simulating task 003 (callable moved to
`src/pipelines_steamspy.py`) raises `AttributeError: module 'src.main' has no
attribute 'run_steamspy_all_page'`, i.e. it fails loudly; with a re-export shim
it passes for the right reason. Argument fidelity in the six dispatch tests is
real: `appid=args.appid + 1`, swapping `limit`/`batch_size`, and changing
`load_data("twitch_games_lookup", ...)` to `load_data("twitch_games", ...)` each
fail their test. Parser enumeration is stable at `COLUMNS=200/100/60/40`.

Counts observed by the reviewer: 121 passed / 48 skipped before, 130 / 48 after.
`ruff check src/ tests/` clean. **The 48 skips are `FATAL: password
authentication failed for user "steam_user"` — the container on 5433 is
`pg-week3`, not this project's compose service. No DB-backed test on this
machine has run.**

### Blocking 1 — the DAG contract asserts the subcommand token and nothing else

`tests/test_dag_cli_contract.py:24` captures only `([A-Za-z0-9_-]+)` after
`python -m src.main` and discards the rest of the line. The 11 DAG commands
carry 9 flags between them; none is asserted. Reproduction — a dest-preserving
flag rename at `src/main.py:1575`, the ordinary way an argument surface drifts:

```python
twitch_games_lookup_observed_parser.add_argument(
    "--max-observed",
    dest="limit",          # main() unchanged, args.limit still exists
    type=int,
```

Suite: `130 passed, 48 skipped`. The DAG's actual command line:
`main.py: error: unrecognized arguments: --limit 500`. That is the 6am failure
this file exists to prevent, and the Brief's done-criterion says "with the
arguments the CLI parsed" — no test parses them. All six dispatch tests
hand-build an `argparse.Namespace` and monkeypatch `parse_args` away, so
argparse never runs.

The reviewer verified the stronger check is achievable today with no production
change: `shlex.split` the `bash_command`, take everything after `src.main`, feed
it to `main.parse_args()`. All 11 current DAG command lines parse; 0 fail.

### Blocking 2 — the guard cannot detect partial coverage loss, and extraction is double-quote-and-first-match-only

`tests/test_dag_cli_contract.py:23` matches `bash_command\s*=\s*"([^"]*)"`, and
`test_dags_reference_at_least_one_subcommand` only asserts `used` is non-empty.
Losing 10 of 11 commands still passes. Two reproductions:

- `dags/steam_etl_mapping.py:23` rewritten with single quotes and a subcommand
  the parser does not have (`twitch-games-lookup-obsolete`): `2 passed`. The
  identical bad name in double quotes fails. Control established.
- `SUBCOMMAND_RE.search` returns only the first match per `bash_command`;
  chaining a second, invalid `python -m src.main …` in
  `dags/steam_etl_weekly.py:33`: `2 passed`.

Hard rule 6 asks for a coverage figure with a test that fails when it regresses;
`assert used` is the vacuous form of that.

### Non-blocking 3 — the meta-test checks that a *name* resolves, not what it does

`DISPATCH_TEST_BY_SUBCOMMAND` is documented as mapping each subcommand to the
test that dispatches it, but the assertion is only `test_name in module_globals
and callable(...)`. Reproduction: delete `test_main_dispatches_migrate` and
repoint the entry at `test_main_dispatches_daily` — `129 passed`, with `migrate`
now uncovered.

### Non-blocking 4 — the meta-test will go red in task 003 for a *correct* change

Moving `test_main_dispatches_steamspy_daily` verbatim into
`tests/test_pipelines_steamspy.py`, coverage fully intact, gives
`AssertionError: dispatch test functions not found`. A false red whose obvious
"fix" is to delete the assertion — i.e. finding 3's weakness becomes the path of
least resistance. Resolution must be across the collected suite, not
`globals()` of one module.

### Beyond the brief

- `dags/.ipynb_checkpoints/steam_etl_daily-checkpoint.py` is untracked, not in
  `.gitignore`, and would be swept in by `git add .`. It is a complete DAG file
  with `dag_id="steam_etl_daily"` and five `bash_command`s, dated May 14 —
  pre-existing, not from this task. Airflow's DagBag scans recursively, so in
  the container it is a duplicate `dag_id`; and `_dag_files()` uses
  non-recursive `glob("*.py")`, so it is outside the new contract test by
  construction.
- **No `else:` on the dispatch chain** (`src/main.py:1618-1746`). An
  unrecognised `args.command` exits 0 having done nothing, which a BashOperator
  reads as success. This is why a deleted branch is a *silent* failure.
- `main()`-level argument validation has **no** coverage, before or after this
  card. Dropping `if args.page < 0: raise` or `if args.appid <= 0: raise` each
  leaves `130 passed`. Pre-existing and uniform across all 14 subcommands.
- `_live_parser_subcommands` is duplicated verbatim in the two test files. Both
  copies fail loudly rather than silently; hygiene, not a defect.
- CI runs Python 3.10; the review ran 3.13.1. The usage-line metavar format is
  stable across those versions but was not executed on 3.10. Unverified, not a
  finding.

## Acceptance

Accepted 2026-09-07 after two review passes, the second of which returned
**blocked** on two findings. The two-return limit was reached, so the decision
went to Ivan, who chose to have the lead close them in the main thread rather
than open a third round.

**Fixed by the lead** (`tests/test_main.py`, ~15 lines, no production change):

- *Review finding 1.* `_collect_test_functions(request.session)` read
  `session.items`, which holds only the **selected** items, so any selective
  run -- a single test from the VS Code gutter, `-k`, `--lf` after an unrelated
  failure -- reported all fourteen dispatch tests as missing. Replaced with
  `_test_function_sources()`, which parses every `tests/test_*.py` with `ast`.
  Independent of what was selected and of which file a test lives in. Verified:
  running the meta-test alone by nodeid gives `1 passed`; `pytest tests/ -k
  recorded_dispatch` gives `1 passed, 177 deselected`.
- *Review finding 2.* The "this test mentions its subcommand" check was a bare
  substring, and three subcommand names are prefixes of another. It now matches
  `command="<subcommand>"` with the closing quote. All three sibling repoints
  are caught, each demonstrated and reverted: `generate-twitch-igdb-candidates`
  repointed at `...-from-catalog` gives `1 failed, 46 passed` where it was
  `46 passed` green; `daily` at `test_main_dispatches_steamspy_daily` gives
  `1 failed, 44 passed`; `twitch-games-lookup` at `..._observed` gives
  `1 failed, 44 passed`.
- *The task 003 scenario, re-verified after both fixes.*
  `test_main_dispatches_migrate` was moved verbatim into a second test file and
  removed from `test_main.py`: the meta-test stays green both in a full run and
  in `pytest tests/test_main.py`, which no longer contains it. Reverted.
- *Review finding 6.* `failures` was keyed by DAG path alone, so two broken
  command lines in one DAG collapsed to the last. Now keyed by path and
  argument string.
- *Review finding 3* was downgraded to a documentation correction, as the
  reviewer suggested. The count guard's docstring claimed to catch three
  extraction narrowings it does not catch -- all three measured green, one
  mutation at a time. The docstring now claims only what it proves, and the gap
  is in `ROADMAP.md` with the fixture tree it would take to close.
- *Review finding 5* was the lead's own error: a claim that
  `_live_parser_subcommands` is duplicated across two test files reached
  `ROADMAP.md` from the first review without being checked. `grep` returns two
  lines, both in `tests/test_main.py`. Entry removed. The same section quoted
  `130 passed, 48 skipped` as a baseline without saying that is the
  database-unreachable baseline; corrected to `178 passed` with the caveat.

**Final state.** `178 passed` with `REQUIRE_DB_TESTS=1` against the project's
own PostgreSQL, `ruff check src/ tests/` clean, `git diff -- src/ dags/` showing
only the pre-existing `s.steam_appid = g.appid` line from the migration-016
work. No re-export shims anywhere.

**Moved to the backlog instead of being fixed here:** the `else`-less dispatch
chain, the absent `main()`-level validation coverage, the checkpoint DAG file,
the count guard's construction-only protection, and the fixed test-database name
that lets two concurrent pytest runs destroy each other.

**A lead mistake worth recording.** Undoing a temporary file move, the lead ran
`git checkout -- tests/test_main.py`, which reverted the whole file to HEAD and
destroyed both the implementer's tests and the lead's own fix. Recovered from a
copy made minutes earlier; 1 900 lines restored and re-verified green. Nothing
was lost, but only by luck. `git checkout --` is not an undo for a scoped edit.
