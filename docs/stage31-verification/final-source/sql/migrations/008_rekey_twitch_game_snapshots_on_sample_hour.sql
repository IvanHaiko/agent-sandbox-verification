-- Migration 008: re-key twitch_game_snapshots on (sample_hour, twitch_game_id).
--
-- snapshot_time defaults to CURRENT_TIMESTAMP, which is the transaction start
-- time -- one value for a whole load, but a different value on every retry.
-- The old UNIQUE (snapshot_time, twitch_game_id) therefore never matches a
-- prior run and duplicates accumulate on every re-run. The real business key
-- is when the observation happened, truncated to the hour Twitch sampling
-- runs at.
--
-- sample_time holds the actual observation instant, read from the raw JSON's
-- fetched_at field by src/transform.py. sample_hour = date_trunc('hour',
-- sample_time) is the new upsert key. snapshot_time is left in place as-is --
-- it is read by dbt models and sql/analytics/, outside this agent's zone --
-- and its meaning is now "time this row was loaded", not "time observed".
-- Renaming it and pointing those readers at sample_time is a follow-up
-- handoff for the warehouse agent, not done here.

ALTER TABLE twitch_game_snapshots
ADD COLUMN IF NOT EXISTS sample_time TIMESTAMP,
ADD COLUMN IF NOT EXISTS sample_hour TIMESTAMP;

-- Backfill existing rows. No bronze JSON survives for 4 of 6 historical runs,
-- so snapshot_time (load time) is the closest available proxy for sample_time
-- (observation time) and that is a known inaccuracy, not a design choice: the
-- raw file for the 2026-05-10 run is named streams_20260510_131724 (fetched
-- 13:17 UTC) but that run's snapshot_time is 14:15, so this backfill files
-- those rows under hour 14:00 instead of the true hour 13:00. There is
-- nothing left to recover the true time from for that run.
UPDATE twitch_game_snapshots
SET
    sample_time = snapshot_time,
    sample_hour = date_trunc('hour', snapshot_time)
WHERE sample_time IS NULL;

-- De-duplicate before the new constraint can be added. Keep the lowest id per
-- (sample_hour, twitch_game_id). Expected: exactly 40 rows removed
-- (1505 -> 1465), matching the 2026-05-14 09:12 double-run incident.
DELETE FROM twitch_game_snapshots a
USING twitch_game_snapshots b
WHERE a.sample_hour = b.sample_hour
    AND a.twitch_game_id = b.twitch_game_id
    AND a.id > b.id;

ALTER TABLE twitch_game_snapshots
ALTER COLUMN sample_hour SET NOT NULL;

ALTER TABLE twitch_game_snapshots
DROP CONSTRAINT IF EXISTS twitch_game_snapshots_snapshot_time_twitch_game_id_key;

ALTER TABLE twitch_game_snapshots
ADD CONSTRAINT twitch_game_snapshots_sample_hour_twitch_game_id_key
UNIQUE (sample_hour, twitch_game_id);

CREATE INDEX IF NOT EXISTS idx_twitch_game_snapshots_sample_hour
ON twitch_game_snapshots (sample_hour);
