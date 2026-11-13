# Progress log — steam-etl

Newest first. One entry per session: what was done, what was decided and why,
what is next, what is still open.

---

## 2026-09-07 -- A safety net before the refactor, and what it cost to prove it

The `main.py` refactor was planned as five steps: a CLI contract net, then
`src/matching.py`, `src/queries.py` + `load.py`, `src/pipelines/`, `src/cli.py`.
Four forks were settled before any code -- SQL split as reads in `queries.py`
and writes in `load.py` (matching the module map), `argparse` kept and moved
rather than rewritten on Typer, a pure move with no behaviour change, and
`src/main.py` retained as the entry point. That last one matters: the plan on
the table proposed a root `main.py` delegating to `src/cli.py`, which would have
broken all 12 `BashOperator`s, every one of which addresses `python -m src.main`.

**Task 001 is the net, and it took two review passes.** 14 subcommands, dispatch
coverage for 8. The card is `tasks/001-cli-contract-safety-net.md`; the trail is
worth reading, because both reviews found real things.

**The first review's two blockers were both "the test does not test what it
says".** The DAG contract asserted the subcommand token and threw the rest of
the line away, so renaming `--limit` to `--max-observed` while keeping
`dest="limit"` left 130 tests green with `dags/steam_etl_mapping.py:23`'s real
command line rejected by the CLI. And the extraction matched double quotes and
the first match only, guarded by `assert used` -- losing 10 of 11 commands
passed. Both fixed: the whole line is now `shlex.split` and fed to the live
`parse_args()`, and the count is pinned.

**The second review's two blockers were in the fix.** Resolving test names
through `session.items` broke every selective run -- one test from the editor
gutter reported all fourteen as missing. And the "does this test mention its
subcommand" check was a bare substring, while three subcommand names are
prefixes of another; repointing one at its longer sibling dropped its only
coverage silently at `46 passed`. The two-return limit was reached, so the
decision went to Ivan; both were closed in the main thread with the mutations
demonstrated.

**The rule this session paid for: an unverified claim reaches a general document
in one move.** The first review reported `_live_parser_subcommands` as
duplicated across two test files. It went into `ROADMAP.md` without a `grep`.
It exists once. This is the third time this project has been burned by exactly
that, and the previous two were also claims copied from a report rather than
measured. A reviewer's finding is evidence about where to look, not a fact.

**Mutation testing is not free of side effects.** The card's own mutation 4
swaps a dispatch branch's callable, and the test patches only the original --
so the real pipeline ran: five SteamSpy page-3 fetches landed in
`data/raw/steamspy/all/2026-09-07/` at 12:00-12:06 UTC, and a review copy
carrying `.env` wrote two rows into the working database (`games` 45 502 to
45 504, `Harry Potter: Quidditch Champions` and `Normality`, `created_at
12:53:08`). `game_snapshots` for today is 0. Nothing is corrupt, and bronze is
gitignored -- but bronze is the system of record, and those five files are
replayable artefacts of a test run. Open question below.

**The DB tests had never actually run.** They skipped for weeks because port
5433 belonged to another project. With the project's own PostgreSQL up:
**178 passed**, and the working database is intact (`games` 45 504,
`game_snapshots` 167 760, `twitch_game_snapshots` 1 464, `igdb_games` 24 542,
`igdb_game_store_links` 28 076). That also gave the first real run for the
uncommitted migration-016/017 work.

**And a defect the day produced on its own:** `tests/conftest.py:88` drops and
recreates a *fixed* database name with `WITH (FORCE)`, so two concurrent pytest
processes on one server destroy each other. Observed live -- the suite
alternated between `178 passed` and `13 failed, 33 errors` while a review agent
ran its own pytest. With `POSTGRES_TEST_DB=steam_analytics_test_lead` it is
`178 passed` three runs in a row. Two wrong diagnoses were published on the way
to that one (module ordering, then a `pytest-randomly` that is not installed),
both corrected by measurement.

**Next:** task 002 -- `src/matching.py`. `normalize_game_name`,
`calculate_name_score`, `NON_GAME_TWITCH_CATEGORIES` and their tests, moving
together, no shims.

**Both open questions settled by Ivan the same day.**

- **The rule is in `CLAUDE.md`:** a mutation runs against a copy with no
  network and no `.env`. Bronze is the system of record, so a test run must
  not be able to write to it.
- **The five bronze files and the two `games` rows stay.** They are real
  SteamSpy data, correctly shaped and correctly named -- deleting them would
  remove real observations to tidy up the provenance story, which is the worse
  trade. What they are is recorded here instead: `page_3` fetched five times
  between 12:00 and 12:06 UTC on 2026-09-07 by a mutation test, not by a
  scheduled run, and `games` 45 502 -> 45 504 at 12:53:08 from a review copy.
  Anyone reading a spike in that day's archive has the explanation.

## 2026-08-13 (later) — The bundle uids, and a number taken from a stale column

Migrations `016`–`017`. Phase 0's last substantive item. One reviewer pass came
back **blocked**, and both of its blocking findings were about evidence rather
than about behaviour — the code did the right thing for reasons that were not
actually established.

**The cast moved into the schema.** 16 of 16 366 steam links carry several
appids packed into one comma-separated uid, because IGDB models a bundle / GOTY
/ collection edition as a single `external_games` entry. Three marts were
casting `store_game_id` to integer inline; that works for 16 350 rows and throws
on the other 16, and it only ever survived because the query plan never reached
them. `igdb_game_store_links` now has `steam_appid INTEGER` and `is_bundle
BOOLEAN`, both `GENERATED ALWAYS ... STORED` — the same device `014` used for
`steam_store_success`, so the derived value cannot drift from its source. Every
mart and every file in `sql/analytics/` joins on the typed column. Bundles drop
out on their own because NULL never equals an appid; no `WHERE NOT is_bundle`
was added anywhere, since a filter would imply the join needed protecting.

**`is_bundle` is NULL for non-steam rows on purpose.** We have never asked IGDB
whether an Epic GUID or a Microsoft SKU packs several ids, so `FALSE` there would
be an unearned claim. Same reasoning as `is_free`: two thirds of a signal beats a
fabricated whole.

**The name is the interpretation; the test is the form.** A comma in the uid is
what the column is generated from — never `game_type`. That distinction is
written into the migration, because it is the thing a future reader will get
wrong.

**Which is exactly what we got wrong ourselves.** The first version justified it
with "IGDB's own `game_type_label` says 'bundle' for only 5 of these 16". Measured
from `raw_json->>'game_type'` instead, it is **10 of 16** — 9 bundle, 1 pack, 6
main_game. The 5 was an artefact of `game_type_label` being NULL for 5 916 of
24 542 `igdb_games` rows, because that column was never backfilled. The worked
example was backwards too: the test docstring said IGDB does not call `362774` a
bundle, and loaded fresh through the real loader it comes back `game_type = 3`,
which `transform.py` maps to exactly `'bundle'`. It read as true only against
the working database.

The conclusion survives — six of the 16 are `game_type = 0` with a comma uid, so
`game_type` genuinely cannot be the test — but the number was wrong by half. The
rule this earns: **write what a number was measured from, next to the number.**
Not "10 of 16" but "10 of 16, from `game_type` in `raw_json`, not from
`game_type_label`, which is unbackfilled for 5 916 of 24 542 rows." The error was
not arithmetic; it was reading a stale column and not saying which column.

**The guard nobody was testing.** The review mutation-tested the migration and
found that dropping the `store = 'steam'` guard from `steam_appid` *alone* left
all 169 tests green — the fixture's only non-steam uids were Epic GUIDs, which
are non-numeric and yield NULL with or without the guard. The property the
migration spends fifteen comment lines arguing for was covered by nothing.
Applied live, that mutation gives **5 575 non-steam rows a `steam_appid`** (all
2 995 GOG and 2 580 PlayStation uids are purely numeric), 20 of them colliding
with a real `games.appid`. Fixed by appending one real PlayStation record from
the archive — a *numeric* non-steam uid is the only shape that kills the mutant.
Re-verified by an independent mutant run: six mutants, all caught.

This is the second session running in which mutation testing found a claim the
suite did not support. It is becoming the thing that actually distinguishes a
test from a sentence.

**The index was dropped one migration after it was created.** `016` added an
index on `steam_appid` justified as "the marts join on it". Hard rule 9 says read
the plan first, and the comment asserted the rule without following it: all three
marts do a `Seq Scan` over 16 366 rows feeding a hash join and never touch the
index. Forcing the nested-loop shape proved the planner *can* use it and that it
is **slower** where it would — 15.0 ms against 9.2 ms. `017` drops it.

Worth keeping: the first `EXPLAIN` run said the opposite. A trimmed-down version
of the query, selecting two columns instead of the mart's real select list, did
pick the index under a nested loop. The plan is shape-dependent, so the query you
explain must be the compiled one under `steam_analytics/target/compiled/`, not a
paraphrase of it. That caution is recorded in `017`.

**Editing an applied migration's comment.** `016` was already applied live when
the wrong number was found. Ivan's ruling, which is worth keeping as a rule:
bronze is immutable because it is *evidence* — you cannot argue with Steam's
answer by rewriting the file that holds it. A migration is *code*, and "don't
touch an applied migration" protects one invariant: that running the chain on an
empty database reproduces the live schema. A comment carries no DDL, so the
invariant is untouched, and the runner tracks by filename with no checksum
(`schema_migrations` is filename + `applied_at`), so an edited file simply stays
skipped. The correction belongs where the number lives, because that is where the
next reader looks — demonstrably so, since this very session carried the wrong
number out of that comment and into a task brief.

The index, by contrast, *is* DDL, so it could not be removed by editing `016` —
that would strand it on the live database with no runner path, and hard rule 3
forbids the ad-hoc `DROP INDEX` that would fix it. Hence `017`. The invariant was
then checked rather than asserted: a from-scratch build of `create_tables.sql`
plus the full chain diffs to zero against the live database, columns, generation
expressions, indexes and `schema_migrations` alike.

**What this does not do.** It does not resolve the 16 bundles. It replaces a
crash with an honest NULL. Of the 91 packed appids, 19 exist in `games`, 18 of
those already have their own single-appid link, and exactly one — 1257290,
Atelier Ryza 2 — is in `games` with no other link. The bundle uid was a
correctness problem, not a coverage one, and the coverage numbers prove it: 162
categories resolve before and after, `mart_igdb_coverage` returns 9 648 / 8 652 /
996 / 89.68% under both the old and the new join predicate.

**A near-miss on how that was verified.** The first before/after comparison
showed movement — 7 314 → 8 652 linked — which is exactly the shape of the
regression we were watching for. It was the *materialised* mart tables being
stale, and the review confirmed it independently rather than taking the
explanation: reconstructing from `created_at`, the 7 314th matching link was
written at 2026-05-15 10:00:05.918 and the mart was last built at 10:00:06,
mid-ingest. The number was three months old. The lesson is the method, not the
outcome: compare both join forms against the *same* data in the same connection,
never a new query against an old table.

**Deferred, with the largest one first.** The links loader conflicts on the
global key `(store, store_game_id)` and overwrites `igdb_game_id`, so when two
IGDB games name the same appid the later load discards the earlier link: 137 of
7 814 triples in the archive are absent from the table, each present under a
different IGDB id. Pre-existing and unrelated to this diff, but it is hard rule
6's failure class sitting in the identity spine Phase 1 is about to build on.
Also open: `mart_top_twitch_games` can fan out (984 rows for 978 categories; six
auto-approved IGDB games hold two steam links each), and the warehouse half of
this change has no automated coverage at all — reverting the mart edit would be
caught by nothing, because `dbt build PASS=12` is twelve models and zero tests.

169 tests, ruff check clean. Reviewer **clean** on the second pass.

**Next.** Phase 0 housekeeping — the hardcoded `admin/admin`, the compose
webserver that dies on a second `up`, dbt reachable from the Airflow container,
and the `006` gap.

---

## 2026-08-13 — Tests that can fail

45 new tests against a real database, bringing the suite to 165. No production
code changed; this session only added the mechanism that would have caught the
last three sessions' defects without a human running queries by hand.

**Substrate.** A separate `steam_analytics_test` database on the same server,
built from `create_tables.sql` plus the whole migration chain and dropped at the
end — a different database, not merely a different schema, so an unqualified
statement in a test cannot reach real rows. `POSTGRES_DB` is repointed for the
session, so the code under test reaches it through the ordinary
`get_db_connection()` and needs no test-awareness. Rejected: testcontainers,
which adds a Docker dependency and seconds to every local run — and a slow suite
stops being run, which is the only way a test loses all its value.

**Three levels, chosen against the four defect classes that got through.**
Schema, proven by *violating* constraints rather than by reading `pg_constraint`
— the string form of a check is exactly the kind of assertion that passed while
`ON CONFLICT (snapshot_time, …)` was unreachable. Loaders, each run twice
against a frozen fixture with a content digest; the digest excludes bookkeeping
timestamps and deliberately **includes** the attempt counters, so the `is_replay`
guard is under test in both directions. Queries, executed for real against the
schema, which is the only thing that can reject invalid SQL.

**Fixtures are cut from `data/raw/`, never written by hand.** This is the part
worth keeping as a rule. A fixture an author invents tests the author's idea of
what an API returns; one cut from the archive tests what it actually returned.
`steamspy_all_page.json` holds four games reporting `price: "0"` that the Store
confirms are *not* free — GTA V Legacy, Rocket League, Realm Royale, Dawn of War
— which is the trap that produced 6 100 fabricated `is_free` values, in the
source's own words rather than in a paraphrase of it. `tests/fixtures/README.md`
records provenance per file and the rule.

**Where a fixture cannot exist, say so.** There is no `transport_error` fixture:
no request ever failed that way during collection, and hand-writing one would
mean authoring exactly the shape whose honesty is under test. That path is
covered by simulating a network failure — the mock is of the network, never of
the database.

**The retry policy is now encoded as behaviour**, one parametrised case per
outcome with the reason in the case itself: `redirected` must never return,
`transport_error` with 99 consecutive failures must still return after the
capped pause. Those two are the ones a future refactor is most likely to
"simplify" into a single cooldown.

**CI would otherwise have gone green for the wrong reason.** A database test
with no database skips, and a suite of skips reports success. CI now runs a
Postgres service with `REQUIRE_DB_TESTS=1`, which turns the skip into a failure;
locally the skip stays, with a message naming the command that fixes it.
`pytest.ini` pins `testpaths` — a bare `pytest` had been dying while collecting
an Airflow symlink Windows cannot stat.

**Not done, deliberately.** The 120 pre-existing mocked tests stay. They are
fast, they do catch call-flow regressions, and deleting them is a separate
decision. What should not happen is new ones of that shape —
`test_load_twitch_file_uses_on_conflict` still asserts that a SQL string
contains `ON CONFLICT` and still claims in its docstring that this proves no
duplicates, which was false when it was written. It is now contradicted by a
test that loads the file twice and counts.

**The review of these tests came back blocked, and it was right.** It
mutation-tested the suite — changed production code in a copy of the repository
and checked whether anything failed — and found that four claims made in
docstrings and the fixture README were not met by the tests underneath them.
That is the same defect the suite was written to remove, committed by the suite
itself.

What did not hold, each proven by a surviving mutation: the `is_replay` guard was
described as covered "in both directions" while the counters were only ever
compared to themselves (`0 == 0`), so an answer never counting as an attempt
passed; the error-counter test never reached the `ON CONFLICT DO UPDATE` branch
it exists to protect, because the row did not exist yet and the INSERT path ran
instead; the `is_free` trap — the headline purpose of the main fixture, quoted in
this log and in the commit message — was asserted nowhere at the database level,
so reintroducing `is_free = True` for a zero price passed; and idempotence was
only ever tested with byte-identical input, so `DO UPDATE` → `DO NOTHING` passed
while in production it would silently discard SteamSpy's afternoon revision.

All four are fixed, and each fix was verified by re-running the mutation and
watching the test fail. The revision case needed a second fixture, and the honest
version of it turned out to be better than a hand-edited one: the same five games
observed two days apart, caught as a sale ended, with `price` and `discount` both
moving. Building it surfaced a fact worth keeping — across those two days only
**69 of 2 000** common appids changed at all, and the seven games in the main
fixture were byte-identical.

One asymmetry the value assertions exposed rather than fixed: a legacy Steam
Store file carries no `fetched_at`, so the replay guard compares NULL to NULL,
matches, and never counts an attempt. That is defensible — a file that cannot
date itself gives no way to tell a first read from a replay — and it is now
pinned by a test so a future change to the guard is a decision rather than a side
effect.

Deferred with reasons in `ROADMAP.md`: migration *content* is still untested (the
chain only ever runs against an empty database, so a repair migration with a
wrong predicate ships green — which is how `008` shipped), the envelope writer is
never proven to agree with the reader, and `REQUIRE_DB_TESTS` guards only
"server unreachable", not "the database tests actually ran".

**Next.** Phase 0's remaining item is the comma-separated `store_game_id`, then
housekeeping.

---

## 2026-08-12 (later) — Steam Store: bronze for every outcome, and a retry policy

Migrations `013`–`015`. Two reviewer passes, both **blocked**, and the second
found defects the first had not created but the fix for the first had.

**Bronze for a refusal.** A failure used to return before the raw file was
written, so 8 864 games carried `success = FALSE` with nothing on disk. Every
call now writes an envelope with an explicit `"envelope": 1` version and an
`outcome` of `ok`, `refused`, `not_found`, `redirected` or `transport_error`.
The old 3 148 files are never rewritten — bronze is immutable, so compatibility
lives in the loader, which reads a file with no `envelope` key as legacy `ok`.
An *unknown* version now raises instead of falling through to that branch: the
first version silently degraded, which would have turned one forgotten constant
bump into a run of fabricated refusals.

**`transport_error` carries no `fetched_at` and no `body`.** No answer arrived,
so no moment of receiving one exists. Stamping the attempt clock there would
repeat exactly what migration 010 undid for Twitch `sample_time` and 013 for
`is_free`. The attempt is timestamped by `steam_store_updated_at`. There is a
test for the invariant rather than a sentence about it.

**`is_free`.** SteamSpy now writes `FALSE` when `price > 0` and `NULL` when
`price == 0` — two thirds of the signal kept, nothing asserted for the rest.
The asymmetry is the point: `price > 0` supports "not free", `price == 0`
supports nothing, because SteamSpy sends it for unreleased and delisted apps.
Migration `013` nulled the 6 100 unconfirmed `TRUE` values and deliberately left
`FALSE` alone; the affected appids are archived under `data/audit/`. Evidence
was never at risk — the raw price stays in `game_snapshots.price`. The measured
tell: 8.6% of Store-confirmed games are free against SteamSpy's 17% claim.

**27 appids answer with a different game.** Steam returns `success: true` but
with another `steam_appid` (100→80, 2130→2100, …). The loader wrote the metadata
to the *target*, so the *requested* appid was never marked — 26 of them sat at
the literal head of the backlog, re-fetched on every run and reported as
processed. They are now outcome `redirected`, terminal, with the target in a
typed `steam_store_redirect_to`. The raw file stays under the requested appid:
bronze answers "what happened when we asked for 100", not "whose data is this".
The pattern looks like merged catalogue entries, which is a Phase 1 concern and
is written into `ROADMAP.md` rather than fixed here.

**`steam_store_success` became a generated column.** `GENERATED ALWAYS AS
(steam_store_outcome = 'ok') STORED`, so one source of truth and no possible
drift, and the two marts filtering on it keep working untouched. The conversion
needed `DROP COLUMN ... CASCADE`, which **dropped the dbt view `stg_games`** —
found by a review pass after the fact, not before. That is the lesson worth
keeping: a raw-layer migration may not drop another layer's object, and if a
DROP needs CASCADE the `pg_depend` query belongs in the decision, not the
autopsy. The rule is written into `014` itself.

Recovering the view also corrected a diagnosis. dbt was never missing — `.venv`
has had dbt-core 1.12.0-b1 all along. `~/.dbt/profiles.yml` still said port
5432 after the database moved to 5433. The profile now lives in
`steam_analytics/profiles.yml`, version-controlled, reading `.env` through
`env_var`, with 5433 as the only default. dbt 1.12 picks it up from the project
directory with no `DBT_PROFILES_DIR`. The `ROADMAP` item is rewritten: it is
about reaching dbt from *orchestration*, not about the package being absent.

**The retry policy, after two corrections.** The first version gave
`transport_error` a lifetime ceiling of three, which meant three unrelated
network blips across years removed a game from the catalogue for good — a
harsher consequence for our own fault than for a refusal by Steam, which carries
no ceiling at all. It now escalates 1, 2, 4, 8, 16, 30 days and resets to zero on
any answer, with no terminal state. The second version had the opposite bug: the
exception path called the recorder with no `fetched_at`, the replay guard
compared NULL to NULL, matched, and counted nothing, so the ceiling could never
engage and the appid returned daily forever. The guard is now an explicit
`is_replay` flag defaulting to False — forgetting it over-counts, which is
visible and fixable, rather than swallowing a real failure, which is not.

Verified live, then cleaned up: the pause sequence, the reset on an answer, and
eligibility again after 400 days. `games` 45 502 throughout, outcome
distribution `ok` 9 648 / `failed_legacy` 8 864 / NULL 26 990, the generated
boolean reproducing the pre-migration 9 648 / 8 864 / 26 990 exactly. 120 tests,
ruff clean.

**`failed_legacy` exists for the same reason `load_clock` does.** The 8 864 old
failures cannot be resolved into `refused` / `not_found` / `transport_error` —
the bronze that would say which was never written. They get their own value
rather than borrowing a neighbour's meaning, and are treated as `refused` for
cooldown because 30 days is the more cautious guess.

**Still true, and still the largest gap:** no test executes SQL. Every one of
the 120 mocks the connection. Migrations `008`–`015` and every query written
across these sessions have zero automated coverage, and both blocking defects
this session were found by running things by hand.

**Next.** Phase 0's remaining item in this block is the comma-separated
`store_game_id`, then housekeeping. Collection stays stopped.

---

## 2026-08-12 (evening) — Coverage measured by attention, not by row count

Read-only session, no code changed. The open question from this morning is
settled and it moved Phase 1's shape.

**Why the figure would not reproduce.** 162 / 163 / 180 / 186 were all the same
query with and without `DISTINCT`. 188 IGDB games hold more than one Steam store
link, so the join fans out. Honest figures: **162** categories resolve to a row
in `games`, **180** have a Steam link.

**The number nobody had computed.** Coverage weighted by viewers rather than by
category: the resolvable set is 16.6% of categories but only **9.6% of observed
attention**. The chain survives the categories people do not watch. Every
statement of the form "162 of 978" was flattering by roughly seventy percent,
not because anyone was careless but because counting rows was the obvious thing
to do and nobody asked what a row was worth.

**The first rung of the ladder has a hole in it.** The drop from 100% to 55.2%
happens before IGDB is involved at all: Twitch supplies no `igdb_id` for its
oldest categories. Most of what falls out is correctly excluded — Just Chatting
(17.15% of all attention), IRL, Slots, ASMR, Music. But **Counter-Strike (7.64%)
and Dota 2 (6.10%) are Steam's two largest titles in this sample and both are
unmappable at rung one**. Together they carry more attention than the entire
currently resolvable universe.

The consequence for the plan: Phase 1 gains a **rung 0** — a version-controlled
seed of hand-written identifiers for high-attention categories Twitch cannot
identify. Five entries roughly double covered attention, which no amount of
crawling would achieve. It is deterministic and reviewable in a diff, so it does
not weaken the rule that fuzzy matches stay quarantined; it is the opposite of a
fuzzy match.

**Left open deliberately.** Phase 1's done-criterion had been "≥ 600 of 978
categories", which today's measurement shows is the least informative of the
three possible denominators. The alternatives — share of observed attention
(ceiling ~72%, because Just Chatting will never map) and share of *game*
attention (reaches 100%, at the cost of us deciding what counts as a game) — are
written into `ROADMAP.md` with a recommendation, for Ivan to settle before
Phase 1 starts.

---

## 2026-08-12 — Phase 0: the three corrupting defects are closed

Migrations `008`–`012`. Two reviewer passes, both returned **blocked** before
the third state was accepted. `twitch_game_snapshots` went 1 505 → 1 464 rows.

**The Twitch snapshot key.** `ON CONFLICT (snapshot_time, twitch_game_id)` keyed
on `CURRENT_TIMESTAMP`, which is the *transaction start* time — so it did dedupe
within one load and never across loads. Options weighed: exact `fetched_at`,
hour bucket, explicit run id, calendar day. Chose **`(sample_hour,
twitch_game_id)`** with `sample_hour = date_trunc('hour', fetched_at)`, because
it is idempotent both on replaying a raw file and on an Airflow retry minutes
later, and Phase 3's planned cadence (every 4 hours) is coarser than the bucket,
so no real observation collapses. Day-grain was rejected for exactly that
reason: it would have merged the 09:12 and 13:18 samples of 14 May.

`snapshot_time` was deliberately left in place — dbt models and `sql/analytics/`
read it. Its meaning is now "row load time", and renaming it plus repointing the
readers is a handoff to `warehouse`, in the backlog.

**`sample_time_source`, and why a comment was not enough.** Bronze survives for
only 2 of the 6 historical runs, so the other 4 have no recoverable observation
time. Migration `008` backfilled all six from the load clock and asserted in a
comment that nothing better existed. That was false: for the 2026-05-10 run the
raw file was on disk with `fetched_at = 13:17:24`, while the backfill filed those
rows under hour `14:00` — a 58-minute load delay written into the data as if it
were the observation. Replaying that surviving file then produced 1 465 → 1 503:
one observation in two hourly slots. Migration `010` moved the run to its true
hour and added **`sample_time_source`** (`bronze` / `load_clock`) so the
distinction lives in the data where a query can filter on it, rather than in a
migration comment nobody reads at query time.

**The 40 deleted rows were not duplicates.** This is the session's real mistake.
The dedupe before the new constraint was justified to Ivan with "both copies are
identical in `(viewer_count, stream_count)`, nothing is lost" — a claim
generalised from a `LIMIT 5` query over 40 pairs, never checked against the rest.
A dump taken before `008` settles it: hour `2026-05-14 09:00` held **two loads of
41 rows each, four milliseconds apart, with different contents** — `Chess` only
in A, `Total War: WARHAMMER III` only in B, and Overwatch (13 269/4 vs 14 788/5)
and Just Chatting (73 747/11 vs 69 549/10) differing between them. Since
`transform_twitch_streams` is deterministic over one file, differing game sets
prove two separate Twitch fetches loaded back to back, not one load run twice.
`008` deleted 40 rows of a real second observation, and one row of B survived
only because A lacked that game — leaving an hour that described no single
observation.

Migration `012` removes that orphan, making the hour exactly observation A:
41 rows, one load, 366 083 viewers. A known gap beats a plausible-looking
mixture, and restoring B would have required an observation time that no longer
exists. The deleted rows and the pre-migration dump are archived at
`data/audit/` (gitignored — note that only `data/raw/` was ignored before, so
the rule had to be added). 978 observed categories are unchanged: Total War
survives in two other hours.

**Mapping candidate status.** `status` removed from the `DO UPDATE`. It is set on
insert and never overwritten, so the weekly DAG can no longer erase a manual
approve/reject — the human decision the fuzzy quarantine depends on. No repair
was needed: there were no manual decisions yet (1 152 `pending`, 234
`auto_approved`, all machine-written).

**Draining the IGDB backlog.** Two separate faults. Nothing was recorded when a
search found nothing, and the backlog was ordered `BY twitch_game_name` with a
fixed limit — so the crawler spent its budget on names starting with digits and
punctuation while 131 categories with ≥1 000 peak viewers waited. Now every
attempt is recorded (`009`), ordering is never-searched → oldest → highest peak
viewers, with `--retry-after-days` (30) and `--max-attempts` (3).

Errors got their **own counter** (`011`) rather than sharing the attempt budget:
"IGDB answered, nothing found" and "we could not ask" are different facts, and a
network failure should not consume one of three chances. The accepted cost is
that a permanently failing category returns every 30 days forever.

The rewritten backlog query dropped `SELECT DISTINCT` in favour of aggregating
once — `DISTINCT` over the raw snapshot rows returned one row per distinct
`(id, name)` pair, so a renamed category consumed two slots of the limit and sent
the crawler after a stale name. Exactly one category in the table has two names.

**The test suite cannot catch SQL errors.** All 87 tests mock the connection and
assert on query strings. The first version of the rewritten backlog query used
`SELECT DISTINCT` with an `ORDER BY` expression absent from the select list —
illegal in Postgres — and it passed the entire suite, failing only on the live
database. Migrations `008`–`012` and every query written this session have zero
automated coverage. Logged as the highest-value item in the Phase 0 backlog.

**Next.** Phase 0 continues with the raw-layer gap (Steam Store failures leave no
bronze record) and `is_free`, then housekeeping. Collection stays stopped until
those land.

**Open questions.** The `Twitch → Steam resolvable = 163` figure in `ROADMAP.md`
could not be reproduced — several defensible formulations give 162, 179, 180 or
234. It needs one agreed definition, published by a mart rather than restated in
prose.

---

## 2026-08-11 (later) — Review of the existing code: blocked

An adversarial read of the whole codebase against the live database. Verdict
**blocked**; full findings folded into `ROADMAP.md` Phase 0 and the defect list
in `CLAUDE.md`. What changed in the plan, as opposed to what was merely confirmed:

**The identity loss is upstream of where the plan assumed it was.** The original
estimate said store links were the bottleneck. The measured chain is
978 observed → 915 with a Helix `igdb_id` → **234 whose id exists in our
`igdb_games`** → 186 with a Steam link → 162 resolved. The collapse is at an
INNER JOIN against a table that was only ever filled by name search from the
Steam side, so fetching `external_games` does not fix it on its own — Phase 1
now starts by fetching IGDB games *by id*, which the foreign key on
`mapping_candidates` requires anyway.

**Three defects actively corrupt data on every scheduled run**, which is why
collection is not restarted until they are fixed. The Twitch snapshot's
`ON CONFLICT` keys on its own insert timestamp, so it never matches a prior run —
worse than "no `ON CONFLICT`", because it reads as handled; duplicates are
already in the table. The mapping-candidate upsert overwrites `status`, so the
weekly DAG erases any manual approve/reject, which is exactly the human decision
the fuzzy-quarantine design depends on. And `igdb-enrich-twitch` records nothing
when a search fails, so it re-requests the same twenty categories indefinitely —
no progress, and not polite crawling either.

**SteamSpy contributes no genres at all** — the `all` endpoint has no `genre`
field in any of the 33 raw files on disk. Every genre in the warehouse came from
the Store API, and the enrichment backlog query re-selects games Steam has
already refused, with no failure counter. Divergence model B is conditioned on
genre, so Phase 5's real precondition is fixing that query, not spending crawl
budget.

**`is_free` is fabricated for 6 100 games** from `price == 0`, which SteamSpy
sends for unreleased and delisted apps. Four rows in the entire table are honest
nulls. This is the "zero that means unknown" failure the rules name explicitly,
sitting in a monetisation attribute that reads like a measurement.

**Two things in the defect list I wrote this morning were wrong.** They came from
the previous auto-generated CLAUDE.md and were repeated without checking:
`run_twitch_streams_extract` *is* wired to the CLI, and the IGDB token *is*
cached — it is the Twitch token that is not. Corrected in place.

Also corrected in `README.md`: every command in "Run the pipeline" was wrong
(`run-daily`, `twitch-daily` and `generate-mapping` do not exist; the module must
be run with `-m`), the DAG table misdescribed the weekly DAG, and the claim that
all writes use `ON CONFLICT DO UPDATE` is contradicted by the Twitch loader.

`.pytest_tmp/` and `.pytest_cache/` are now ignored. The directory itself could
not be deleted — it was created from WSL and Windows cannot read its ACL — but
git no longer descends into it.

**Next.** Phase 0, in order: the three corrupting defects, then the raw-layer gap
and `is_free`, then housekeeping. Fixes go through the layer agents from a
session rooted in this repository.

---

## 2026-08-11 — Direction set: attention-versus-players

**Context.** The project had been dormant since 15 May 2026. It was reopened to
become the batch half of a two-project portfolio (the other, a capstone, is the
streaming one, on exchange data — deliberately a different domain and a different
processing model).

**What was done.**

- Surveyed the live database and wrote the numbers down (see `ROADMAP.md`).
- Moved this project's Postgres to port `5433` — 5432 on this machine is taken by
  an unrelated project's database. `docker-compose.yml` now reads
  `${POSTGRES_PORT:-5433}`, and `.env` was updated to match.
- Removed `..env.swp` — a nano swap file holding the contents of `.env`,
  including `TWITCH_CLIENT_SECRET`. It was untracked and *not* covered by
  `.gitignore`, so any blanket "stage all" would have published the secret.
- Moved `cs50p_project/` and `cs50sql_project/` out of the repository into
  `../projects/`; they were untracked course work sitting inside this repo.
- Wrote `ARCHITECTURE.md` and `ROADMAP.md`; started this log.

**Decisions and why.**

- **The product is the gap between attention and players**, not another Steam
  stats dashboard. Steam gives players (CCU, review velocity); Twitch and later
  YouTube give attention. Where they diverge is the marketing question.
- **The thesis is written to be falsifiable** — rank stability day-over-day, and
  face validity by genre. If the ranking reshuffles daily we are measuring
  sampling noise, and the honest outcome is a written finding, not a dashboard.
- **Twitch first, YouTube second.** YouTube's free quota allows roughly 100
  search queries a day, so it can never cover the catalogue — it needs a
  watchlist and a rotation policy, which is a phase of its own rather than a
  detail of phase one.
- **Both divergence models ship**, in order: rank gap first (works today, needs
  no genres and no history), residual-from-expected second (the real metric, but
  it needs genre coverage, currently 21%). The rank version stays afterwards as
  the sanity check on the residual version.
- **Warehouse moves to `raw` / `staging` / `marts`.** `raw` is not a JSONB
  landing zone: the immutable copy already exists as the JSON files under
  `data/raw/`, so `raw` means "loader-owned and unreshaped" instead.
- **Agent roles are split by layer, with a mandatory reviewer.** `ingestion`,
  `warehouse`, `orchestration` on Sonnet; `analytics` and `reviewer` on Opus,
  because a metric error does not throw a traceback — it produces a plausible
  wrong number, and a reviewer weaker than the implementer rubber-stamps.
  Roles live in `.claude/agents/` (gitignored, local only).
- **Claude does not commit.** `git commit`, `push`, `rebase` and `cherry-pick`
  are denied in `.claude/settings.local.json`; Ivan commits by hand.

**The finding that shapes the plan.** Of 978 Twitch categories ever observed,
915 carry an `igdb_id`, but only 186 have a Steam link in our IGDB copy and only
163 resolve to a row in `games`. **83% of the observed Twitch universe cannot be
compared to Steam at all.** The cause is the ingestion path: IGDB was populated
by name search from Steam games, so store links exist only where a search
happened to hit. The fix is to resolve rather than search — IGDB
`external_games` by `uid = appid`, in both directions. Until that lands, every
divergence number would be computed over a sixth of the universe.

**Known live defects, carried into Phase 0.**

- `twitch_game_snapshots` inserts without `ON CONFLICT` — re-running a day
  duplicates rows.
- Migration `006` is missing from the sequence (005 → 007).
- `requirements.txt` has no dbt, though the README and the DAGs assume it.
- `.pytest_tmp/` is unreadable by git and clutters `git status`.

**Next.** Code review and refactor of the existing code, then Phase 0.

**Open questions.** Listed at the bottom of `ROADMAP.md`.
