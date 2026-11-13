-- Migration 010: fix the sample_time backfill for the two runs bronze
-- survives for, and mark where every row's sample_time actually came from.
--
-- Migration 008 said "no bronze JSON survives for 4 of 6 historical runs"
-- and used snapshot_time (row insert time) as a stand-in for sample_time
-- (observation time) for every row, including the 2026-05-10 run, filing it
-- under hour 14:00. That claim was wrong: bronze survives for 2 of the 6
-- runs, in data/raw/twitch/streams/2026-05-10/ and .../2026-05-13/. Both raw
-- files carry a fetched_at field that is the true observation instant, read
-- by src/transform.py's parse_twitch_fetched_at. This migration corrects the
-- two runs bronze exists for, and records for every row whether sample_time
-- is a real observation time or a load-time stand-in, instead of repeating
-- 008's mistake of writing down an unverified claim as settled fact.
--
-- sample_time_source has two values:
--   'bronze'     -- sample_time was read from the raw JSON's fetched_at
--   'load_clock' -- sample_time is snapshot_time (row insert time) -- the
--                   true observation instant is not recoverable
--
-- The loader (src/load.py insert_twitch_game_snapshot) always writes
-- 'bronze' going forward -- see the comment there. 'load_clock' only ever
-- describes historical rows backfilled by 008 before this migration existed.

ALTER TABLE twitch_game_snapshots
ADD COLUMN IF NOT EXISTS sample_time_source TEXT NOT NULL DEFAULT 'load_clock';

ALTER TABLE twitch_game_snapshots
ADD CONSTRAINT twitch_game_snapshots_sample_time_source_check
CHECK (sample_time_source IN ('bronze', 'load_clock'));

-- 2026-05-13 run (streams_20260513_122852.json, fetched_at
-- 2026-05-13T12:28:52.040293+00:00, 38 rows): the 008 backfill already put
-- these rows at the right sample_hour (12:00), because snapshot_time and
-- fetched_at happened to fall in the same hour. Only the provenance flag
-- needs correcting here -- the values were already right.
UPDATE twitch_game_snapshots
SET sample_time_source = 'bronze'
WHERE sample_hour = TIMESTAMP '2026-05-13 12:00:00';

-- 2026-05-10 run (streams_20260510_131724.json, fetched_at
-- 2026-05-10T13:17:24.117094+00:00, 38 rows): the 008 backfill filed these
-- rows under hour 14:00 (snapshot_time / load clock) instead of the true
-- hour 13:00. The UNIQUE (sample_hour, twitch_game_id) constraint on this
-- table is the safety check for this move: if any row already existed at
-- 13:00 for one of these twitch_game_ids, this UPDATE fails with a unique
-- violation and the whole migration file rolls back rather than silently
-- merging two observations. A manual query before writing this file
-- confirmed zero rows at sample_hour 13:00 for 2026-05-10, and the
-- constraint re-checks that fact live, not just at authoring time.
UPDATE twitch_game_snapshots
SET
    sample_time = TIMESTAMP '2026-05-10 13:17:24.117094',
    sample_hour = TIMESTAMP '2026-05-10 13:00:00',
    sample_time_source = 'bronze'
WHERE sample_hour = TIMESTAMP '2026-05-10 14:00:00';

-- The remaining 4 historical runs (2026-05-13 19:00, 2026-05-14 09:00 and
-- 13:00, 2026-05-15 06:00) have no surviving bronze. They keep the column
-- default 'load_clock' -- sample_time stays snapshot_time and no observation
-- time is invented for them here.

-- Dedup tie-break, corrected for consistency, not for behaviour: 008's
-- DELETE kept MIN(id) -- the older of each duplicate pair -- when collapsing
-- the 1505 -> 1465 double-run rows. src/load.py's ON CONFLICT ... DO UPDATE
-- documents and implements the opposite rule for every future write --
-- last write wins, on the reasoning that a retry usually carries more
-- complete data than the run it retries. The two rules were never actually
-- in tension in practice: the duplicate pairs 008 removed were checked to be
-- identical in (viewer_count, stream_count, twitch_game_name), so MIN(id)
-- versus MAX(id) picked between two rows holding the same values and
-- nothing was lost either way. The rule for all writes from here on is the
-- one src/load.py already implements and this migration does not change:
-- last write wins.
