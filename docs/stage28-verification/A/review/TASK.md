# Stage 28 frozen task: reliable IGDB bronze replay

Baseline: Steam ETL commit `0653617666399590c853c39f08e8cf97c9eca45c`.
The committed transformer silently accepts an envelope without data as an empty result,
and IGDB upserts unconditionally rewrite updated_at on replay. Fix those observable
reliability defects while preserving file-atomic recovery and current mapping semantics.

Allowed changes: src/transform.py, src/load.py, new tests/test_igdb_reliability.py only.
Existing tests, SQL/schema/migrations, dependencies and all unrelated behavior are immutable.
Preserve every existing public signature, including transform_igdb_search_results(raw_data),
load_igdb_file(file_path), load_data and the three IGDB persistence helpers.

1. Envelope validation: transform_igdb_search_results accepts a dict with an explicit
data list; [] is a valid empty answer. Missing data, null data, nonlist data and nondict
envelopes raise ValueError. Additional envelope metadata is ignored.
2. Validate the entire batch before opening a database connection. Every game is a dict
with id a positive non-bool int in PostgreSQL INTEGER range (1..2147483647), and name
a nonblank string. Duplicate game ids within a batch raise ValueError (even identical).
Do not mutate the caller's input. Keep valid names and fields verbatim.
3. external_games and websites may be absent or null (meaning empty), otherwise each
must be a list of dicts. A nested url may be absent/null or a string, otherwise reject.
external_games uid may be absent/null, string, or non-bool integer; reject other types.
Absent/empty identifiers and unrecognized URLs continue to be ignored as before.
Other optional game field transformation and link precedence retain committed semantics;
new validation of unrelated optional scalar fields is outside this task.
4. All malformed cases described above raise ValueError from the public transformer
and file loader, before acquiring a connection or writing any rows. Error wording is free.
Malformed JSON continues to raise its JSON decoding error. An explicit empty batch returns
0 from the loader without acquiring a connection.
5. One nonempty file's game, store link and Twitch mapping changes commit atomically.
A failure during any write propagates and rolls back ALL changes from that file, including
updates to prior rows. Previously committed files remain durable. Retrying the saved file
after the cause is removed succeeds without duplicate rows. Do not refetch the API.
6. Replaying identical valid records preserves all persisted values, including updated_at
on igdb_games and twitch_categories and created_at on store links. Row counts stay stable.
Compare values with NULL-safe semantics; JSON object key order is immaterial. Changed
game metadata or Twitch mapping must update normally and advance that row's updated_at.
Store link remapping/update retains the existing unique (store, store_game_id) behavior.
This is upsert-only: absent links/categories in a later file are NOT deleted.
7. Preserve transformed record shape, raw_json content, enum decoding, UTC release dates,
Steam URL-over-uid and websites-over-external precedence, successful loader return count
(number of distinct games), dispatch behavior and existing helper fake-connection compatibility.
No new runtime dependency, schema change, new orchestration component or broad rewrite.

Add focused unit and real PostgreSQL tests. The supplied test_database fixture creates
the full existing schema; get_db_connection uses that fixture database. For real tests,
request test_database or db. Test timestamp preservation across separate transactions.
The public test seam is src.load.get_db_connection; persistence helper seams are
upsert_igdb_game, upsert_igdb_game_store_link and upsert_twitch_category.

Both configurations use gpt-6.1-sol / medium and installed Linux Codex 0.160.1.
Order A then B. At most two candidate repair cycles per configuration, triggered by
frozen independent tests or concrete review findings, retaining original results. External
acceptance and mutations are final held-out evaluation; no post-evaluation test tuning.
Independent designs freeze before candidate exposure; existing regression tests are immutable.
