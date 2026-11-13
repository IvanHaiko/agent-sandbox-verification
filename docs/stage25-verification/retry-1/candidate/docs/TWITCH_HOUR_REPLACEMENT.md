# Twitch hour replacement

`load_twitch_file(str | Path) -> int` treats each nonempty bronze streams file as
one complete configured top-stream sample. It validates and aggregates the whole
file before opening a database connection. The existing CLI and dispatch remain
compatible. Accepted loads and identical replays return the aggregate count;
stale observations return 0. Invalid input and equal-time conflicting observations
raise `ValueError`.

`fetched_at` is the observation instant recorded after the extractor's pagination
loop. Aware offsets are normalized to naive UTC; legacy naive datetimes mean UTC.
`sample_time` carries that instant and `sample_hour` is its UTC hour floor.
Incoming rows retain `sample_time_source = 'bronze'`. `snapshot_time` still means
row insertion time. Retained game IDs and insertion times are preserved by upsert.

A single READ COMMITTED transaction acquires a SHARE ROW EXCLUSIVE table lock,
then reads the hour in a separate statement. This serializes writers even for an
initially absent hour; the read sees the preceding committed writer. It also
serializes different-hour writes, a deliberate conservative throughput tradeoff.
Readers retain PostgreSQL MVCC behavior. Upserts and deletion of absent games
commit together; errors roll back the transaction. Other hours are untouched.
The per-row insertion helper alone does not enforce whole-observation ordering.

The newest existing bronze `sample_time` establishes observation order, including
hours containing old mixed observations. Older arrivals perform no writes. Equal
timestamps require equality of the entire hour's logical contents (game ID/name,
viewer and stream counts, sample time and provenance), otherwise loading fails.
Historical `load_clock` rows are proxies and do not establish observation order.
An existing bronze row with a missing time causes failure rather than a guess.

Empty or zero-aggregate observations always fail, including observations consisting
only of legitimate blank unassigned categories. Clearing an hour would discard
its ordering watermark and allow an older observation to resurrect it. Supporting
authoritative empty replacement requires a durable watermark and is outside this
change's no-migration scope.

Legacy nonempty `fetched_at`/`data` files remain supported. Optional `source` and
`request` must identify Twitch streams; optional integer `stream_count` must match
the raw list length. Missing/non-list data, malformed stream records, invalid
timestamps, negative/noninteger viewers, and explicit failure or incompleteness
markers fail before mutation. Numeric viewer strings remain supported. Blank
unassigned category strings retain the previous filtering behavior.

Completeness describes the configured sample, not every live Twitch stream. The
extractor records no pagination completion proof: matching counts and nonempty
data cannot detect an unmarked upstream truncation. Compatibility trusts the
saved observation contract. No bronze files, migrations, downstream queries or
unrelated loaders are changed.

`tests/test_twitch_hour_replacement.py` includes local validation tests and real
PostgreSQL tests using the existing separate-database fixture. Database tests cover
replacement, replay, ordering, hour isolation, retained identity, rollback after
an actual SQL failure, historical provenance, and overlapping same-hour loads
with bounded waits. They are designed for Controller execution; model roles do
not have the database socket capability.
