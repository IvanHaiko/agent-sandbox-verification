# Architecture — steam-etl

Read this before touching the schema, the loaders or the metric definitions.
Written 2026-08-11, when the project changed from "collect Steam data" to
"measure the gap between attention and players".

---

## 1. What this platform answers

A game has two audiences that are usually assumed to move together: the people
who **play** it (Steam concurrent users, review growth) and the people who
**watch** it (Twitch viewers, later YouTube uploads). They do not always move
together, and the gap is the product.

**The thesis, stated so it can be falsified:** for a given game, the share of
attention that is *not* explained by its player base and its genre is a stable,
interpretable property of that game — not noise. Two consequences we can test:

- **Rank stability.** If the divergence is real, the same titles sit at the top
  and bottom of the list on consecutive days. If the ranking reshuffles daily,
  we are measuring sampling noise and the metric is dead.
- **Face validity by genre.** Spectator-native games (fighting games, MOBAs,
  extraction shooters) must land on the attention-heavy side; long single-player
  and simulation titles on the player-heavy side. If they do not, the mapping or
  the aggregation is wrong, not the world.

Only after both hold does the interesting reading become defensible: a game with
an **attention spike and no matching growth in players or reviews** is a
candidate for bought exposure — a sponsored-stream wave or an influencer push.
That is a **candidate signal, never a verdict**; see §8.

Useful in the other direction too: a game with many players and almost no stream
attention is either genuinely unspectatable or genuinely undermarketed, and
telling those apart is a marketing question worth putting on a dashboard.

---

## 2. Layers

Three schemas in one PostgreSQL database. The same bronze/silver/gold idea under
names that read the way a warehouse is expected to read.

| Schema | Owner | Contains | Rule |
|---|---|---|---|
| `raw` | loaders (`src/load.py`) | one table per source endpoint, typed but never reshaped | written only by ingestion; no business logic ever |
| `staging` | dbt (views) | typing, renaming, dedup, one row per business key | no cross-source joins except the identity spine |
| `marts` | dbt (tables) | `dim_*`, `fct_*`, `mart_*` — what the dashboard and the API read | every model has tests on its keys |

**Why `raw` is not a JSONB landing zone.** The immutable copy of the source
already exists: every extract writes the API response to
`data/raw/{source}/{request_type}/{date}/{descriptor}_{ts}.json` *before*
anything is loaded. Those files are the bronze layer. Duplicating them as JSONB
in Postgres would double the storage to re-answer a question the files already
answer. What `raw` guarantees instead is narrower and still worth having: a
loader may cast and rename, but it may not filter, aggregate, join, or interpret.
If a value is wrong in `raw`, the source said it.

**Migration path.** The existing tables in `public` are already loader-owned and
unreshaped, so they move with `ALTER TABLE ... SET SCHEMA raw` — no copy, no
downtime, no rewrite of `load.py` beyond qualifying table names. The current
`mart_*` tables in `public` were built by dbt and are dropped and rebuilt in
`marts`.

Names inside `raw` get a source prefix, because `games` stops being unambiguous
the moment a second catalogue exists:

```
public.games                          → raw.steam_games
public.game_snapshots                 → raw.steam_game_snapshots
public.genres, public.game_genres     → raw.steam_genres, raw.steam_game_genres
public.twitch_game_snapshots          → raw.twitch_game_snapshots
public.twitch_categories_catalog      → raw.twitch_categories
public.igdb_games                     → raw.igdb_games
public.igdb_game_store_links          → raw.igdb_external_games
public.twitch_igdb_mapping_candidates → raw.mapping_candidates
public.twitch_categories              → dropped (superseded by raw.twitch_categories)
```

### 2.1 What a bronze file contains

Decided 2026-08-12, while fixing the Steam Store path. Twitch and SteamSpy
already wrote an envelope around the response; Steam Store wrote the bare body,
and the formats had quietly diverged. They converge on the envelope.

```
{ "envelope": 1, "source": …, "fetched_at": …, "url": …,
  "http_status": …, "outcome": …, "body": <verbatim source response> }
```

`body` is exactly what the source said, unaltered. The envelope is **metadata
about the fetch**, not an edit of the payload, so the rule that a wrong value in
`raw` means the source said it is untouched.

**Why an envelope at all.** Because the fetch has properties the payload does not
record — above all *when we asked*. Losing that is not hypothetical: for four of
the six historical Twitch runs the bronze was gone and the observation time was
unrecoverable, which is why `sample_time_source` exists. Where the envelope
survived, migration `010` could repair the data exactly.

**`outcome` — five values.** The envelope may describe *whether the response
corresponds to the request*. It may not describe the game data inside it; that is
the body's job and the transform's.

| outcome | meaning |
|---|---|
| `ok` | the response carries what was asked for |
| `refused` | source answered, and said no (`success: false`) — often unreleased, region-locked or temporarily hidden, and it can become available later |
| `not_found` | source answered, but the response has no wrapper for the requested id — usually removed |
| `redirected` | the response carries a *different* id than the one requested; the target goes in a typed field, never into prose |
| `transport_error` | no answer arrived; `body` is null |

`refused` and `not_found` were separated deliberately: collapsing them loses the
difference between "not yet" and "never again", which is exactly what the retry
policy needs to know. `redirected` was added the same day for the same reason and
by the same argument — the enum grows when a genuinely new fact appears, rather
than folding it into `ok`.

**Retry depth follows the outcome**, because the outcomes mean different things
about the future:

| outcome | cooldown | attempt ceiling |
|---|---|---|
| `ok` | 30 days (refresh) | — |
| `refused` | 30 days | none — a game announced today may release in a year, and a ceiling would bench it permanently |
| `not_found` | 90 days | none |
| `transport_error` | 1 day | 3, on a **separate counter** — a failure to *ask* must never spend a chance meant for an *answer* |
| `redirected` | terminal, never re-asked | — |

Budget is not what sets these numbers. At a 30-day cooldown the whole 45 502-game
catalogue costs ~1 500 requests a day, about 25 minutes at 1 req/s. The numbers
follow from what each outcome says about whether asking again could change the
answer.

**Two rules that fall out of this.**

*Old bronze is never rewritten.* The 3 148 files predating the envelope stay as
they are — repacking them would be exactly the mutation the immutability rule
exists to prevent. The reader accepts both shapes and treats a bare body as
legacy with an unknown fetch time. The `envelope` field is an explicit version,
not something to infer from which keys are present, and an unknown version must
fail loudly rather than degrade into "legacy".

*A coarse record must look coarse.* The 8 864 rows that failed before outcomes
existed cannot be resolved into one of the five — the bronze for failures was
never written, which was the defect. They carry `failed_legacy`, in the same
spirit as `load_clock` in `sample_time_source`: where the record is coarser than
the schema, the value says so instead of inventing precision.

The boolean `steam_store_success` survives as a generated column
(`GENERATED ALWAYS AS (steam_store_outcome = 'ok')`), so the existing marts keep
reading it while the enum stays the single source of truth and the two cannot
drift apart.

**The general rule these decisions share: a source that cannot know something
writes null.** `is_free` was the counter-example — derived from `price == 0`,
which SteamSpy also sends for unreleased and delisted apps, so 6 100 games were
recorded as free-to-play on no evidence and four rows in the whole table were
honestly unknown. `price == 0` is not a degraded measurement of "free", the way
a load clock is a degraded measurement of an observation time; it is a different
proposition, so a provenance flag would have dressed an inference as a
measurement. SteamSpy now writes `false` when `price > 0` — an inference that
does hold — and null when it does not, and only the Store API may assert `true`.

**A safeguard relies on a declared fact, not on a coincidence of clocks.** The
loader has a guard that distinguishes replaying a stored file from a new event.
It must be told which one it is — the caller knows for certain — rather than
inferring it by comparing timestamps. The first attempt inferred it, and broke in
both directions at once: the load path could not forget an error, and the error
path could not record one. Guards written this way fail silently, because a guard
that guesses wrong still looks like a guard. Where a flag is boolean, name it so
the *unsafe* case is the one you have to ask for: `is_replay=False` by default
means a forgotten argument double-counts a replay, which shows up in a counter,
instead of swallowing a real failure, which shows up nowhere.

### 2.2 Migrations may not reach across layers

A migration belongs to one layer and may only drop what that layer owns. A
`DROP ... CASCADE` in a `raw` migration silently removed `stg_games`, a dbt view
owned by `warehouse`; the damage was found afterwards by reading `pg_depend`,
which is the right query at the wrong time.

If a drop needs `CASCADE`, stop and show what would go — `pg_depend` answers this
before the fact as readily as after — and hand it to the owning layer. The
inverse holds too: `warehouse` does not alter `raw` tables to make a model
simpler.

This is the same boundary the agent zones describe, enforced where it actually
gets crossed. Zones stop two authors from overwriting each other's design;
`CASCADE` crosses the boundary without either author noticing, which is worse,
because nothing in the diff looks wrong.

---

## 3. Sources — what each gives, and what it costs

| Source | Endpoint | Grain | Rate limit | Known bias |
|---|---|---|---|---|
| SteamSpy | `/api.php?request=all&page=N` | game × day | 1 page (1000 games) / 65 s → ~46 pages ≈ 50 min | `owners` is a wide bucket estimate, not a number; `ccu` is yesterday's peak, not a live sample |
| Steam Store | `/api/appdetails?appids=N` | game (static metadata) | 1 req/s, unofficial, throttles hard on bursts | one game per request — the full catalogue is a multi-day budget, not a task |
| Twitch Helix | `/helix/streams`, `/helix/games` | stream, sampled | generous; OAuth2 client_credentials | **only the top slice of streams is paginated** — the tail is invisible, and a game with no rows means "not in the top slice", not "nobody streams it" |
| IGDB | `/v4/games`, `/v4/external_games` | game, cross-platform identity | same OAuth as Twitch, 4 req/s | store-link coverage is uneven; a missing Steam link is not proof the game is not on Steam |
| YouTube (phase 6) | `search.list` | query × day | 10 000 units/day, `search.list` = 100 units → **~100 queries/day** (verify before building) | name search is noisy — "Rust" the game vs the language |

The Twitch tail bias is the one that can silently invalidate the metric. It is
handled by scope, not by cleverness: divergence is computed only over the mapped
universe, and a game absent from the sample is reported as
`attention_observed = false`, never as `viewers = 0`.

---

## 4. The identity spine

Everything here depends on one join: *this Steam game and this Twitch category
are the same game*. That join is the backbone, and today it is the weakest thing
in the repo.

**Measured 2026-08-11:** of 978 Twitch categories ever seen, 915 carry an
`igdb_id` from Helix, but only 186 have a Steam link in our IGDB copy, and only
163 resolve to a row in `games`. **83% of the observed Twitch universe cannot
currently be compared to Steam at all.**

The cause is the ingestion path, not the data. IGDB was populated by *searching
by name* starting from Steam games, so external store links exist only where a
name search happened to succeed. The fix is to stop searching and start
resolving.

**Resolution ladder — highest precision first. A lower rung may never overwrite a
higher one.**

1. **IGDB `external_games`, Steam category, by `uid = appid`.** Deterministic in
   both directions: appid → IGDB id, and for the 915 known `igdb_id`s → appid.
   About 915 cheap requests closes most of the gap.
2. **Twitch Helix `igdb_id`.** First-party — Twitch itself declares which IGDB
   entry a category is. Already ingested, already `auto_approved` (234 rows).
3. **Fuzzy name match** (RapidFuzz, 1 152 rows `pending`). Produces *candidates
   only*. A fuzzy candidate never enters a mart until its status is `approved`.
   Deliberate: one wrong high-profile match — "Rust", "Among Us", franchise
   entries sharing a name — discredits the whole dashboard.

The spine materialises as `marts.dim_game`: one row per resolved game, a
surrogate `game_key`, the identifiers hanging off it (`steam_appid`,
`igdb_game_id`, `twitch_game_id`, later `youtube_query`), and `match_method` /
`match_confidence` carried downstream so any number can be filtered by how it was
matched.

**Coverage is a published metric, not an implementation detail.**
`marts.mart_identity_coverage` reports resolved vs observed per source per day,
and a dbt test fails the build when coverage regresses. A join that silently
drops rows is the failure mode this project is most exposed to.

---

## 5. Metrics

### 5.1 Players (Steam)

- `ccu` — from SteamSpy, one value per game per day.
- `review_velocity` — Δ`total_reviews` between consecutive snapshots, per day.
  The closest free proxy for *new buyers*: CCU says how many are playing, review
  growth says how many arrived. A campaign that moves attention but not review
  velocity moved nobody into the store.
- `owners_bucket` — kept for tiering only, never used as a number.

### 5.2 Attention (Twitch)

Stored per stream, not pre-aggregated. `raw.twitch_streams` keeps
`(sample_time, twitch_game_id, user_id, viewer_count)`, because two things we
need cannot be recovered from a per-game total:

- **viewer-hours** — `Σ viewers × sample_interval`, the honest daily attention
  measure. A single daily sample at 06:00 UTC measures one time zone waking up,
  not a day. Sampling moves to **every 4 hours** (6 samples/day).
- **concentration** — the share of viewer-hours held by the top 3 channels.
  Organic interest is spread across many small streams; a paid wave is a handful
  of large ones. This is the discriminating feature for §5.4, and it is lost
  forever if only the sum is stored.

The existing per-game aggregate stays as a rollup fed from the stream rows.

### 5.3 Divergence — two models, both shipped

**A. Rank gap** — ships first, needs neither genres nor history.

```
steam_rank  = rank by ccu          among mapped games on date d
twitch_rank = rank by viewer_hours among mapped games on date d
rank_gap    = steam_rank - twitch_rank     -- positive = louder than it is played
```

Robust to outliers and to the fact that both distributions are heavy-tailed. Its
weakness is exactly the one to be honest about: it confuses a game's *nature*
with its *marketing*. A fighting game will always out-rank its player count.

**B. Residual from expected** — the real metric, gated on genre coverage.

Fit, per genre with `n >= 30` mapped games (global fit as fallback):

```
y            = log10(viewer_hours + 1)
x            = log10(ccu + 1)
y_hat        = regr_intercept(y, x) + regr_slope(y, x) * x
divergence_z = (y - y_hat) / stddev_samp(y - y_hat)
```

Postgres computes this natively with `regr_*` aggregates — no Python, no
extract-fit-load loop; the model lives in a dbt model and is recomputed daily.
Conditioning on genre removes the nature-versus-marketing confusion, which is why
**finishing Steam Store enrichment is a prerequisite for B, not a chore**
(genres exist for 21% of games today; IGDB genres are the fallback for the rest).

A is kept after B ships, as the sanity check: the two must broadly agree at the
extremes. Where they disagree, one of them is wrong, and that is worth a look.

### 5.4 Bought-exposure candidate (phase 7, needs history)

A game is flagged when, in the same window:

- attention z-score rises above 2 against its own 14-day baseline, **and**
- `review_velocity` z-score stays below 0.5 — the attention did not convert, **and**
- top-3 channel concentration exceeds the genre norm — the attention is not spread.

Reported as a ranked candidate list with all three components visible. Never as
"this game bought its streams" — see §8.

---

## 6. Orchestration

| DAG | Schedule | Job |
|---|---|---|
| `steam_daily` | 05:00 UTC | SteamSpy full catalogue → `raw.steam_game_snapshots` |
| `steam_store_enrich` | 05:30 UTC | one polite batch of the enrichment backlog (budgeted, resumable) |
| `twitch_sample` | every 4 h | top streams → `raw.twitch_streams` + rollup |
| `identity_resolve` | daily 07:00 UTC | IGDB `external_games` for unresolved appids and igdb_ids |
| `dbt_build` | 08:00 UTC | `dbt build` — models and tests in one command |
| `youtube_watchlist` | phase 6 | quota-bounded rotation over the tracked list |

Every task is idempotent by key. `twitch_game_snapshots` currently inserts
without `ON CONFLICT` — a live bug, and the first thing ingestion fixes.

Postgres for this project publishes on `${POSTGRES_PORT:-5433}`; 5432 on this
machine belongs to another project.

---

## 7. Conventions inherited from the existing code

Kept because they are already consistent across the repo: psycopg3 with `%s`
placeholders and explicit `commit()`; stateless transforms with no I/O;
extract-then-load as separate steps against a saved raw file; `to_int()` instead
of bare casts; type hints in 3.10+ union syntax; kebab-case CLI subcommands.

---

## 8. Measurement caveats — say these out loud, on the dashboard

- **We observe public counters, never intent.** Sponsored streams and a genuine
  viral moment look alike from outside. The output is a candidate list for a
  human to investigate, and the UI must say so.
- **Twitch shows only the top slice.** Absence is not zero.
- **CCU is a daily peak from a third party**, not a measurement we control.
- **Reviews lag purchases** by days to weeks, and lag differently by price and
  genre.
- **A name is not an identity.** Franchise entries, remasters and regional
  editions share names across platforms — which is why fuzzy matches are
  quarantined.
- **The May–August 2026 gap is permanent.** Collection ran 8–15 May and stopped.
  Everything before the August restart is a six-day island; trend models treat it
  as a hole and never interpolate across it.
