-- Migration 009: track IGDB search attempts on twitch_categories.
--
-- Before this, a Twitch category that an IGDB search found nothing for was
-- indistinguishable from a category nobody had searched for yet: an empty
-- result wrote nothing back to the database. Combined with a backlog query
-- that had a fixed ORDER BY twitch_game_name and no failure memory, the same
-- alphabetically-first categories were re-searched on every run and the
-- backlog never drained. This migration only adds the bookkeeping columns.
-- The crawler change lives in src/main.py.
--
-- mapping_status is deliberately left alone. It is a finite state machine
-- about mapping outcome (unmapped / mapped / excluded). "We searched and
-- found nothing" is a fact about the crawler, not a mapping decision, so it
-- gets its own columns instead of overloading mapping_status.

ALTER TABLE twitch_categories
ADD COLUMN IF NOT EXISTS last_igdb_search_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS igdb_search_attempts INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_twitch_categories_last_igdb_search_at
ON twitch_categories (last_igdb_search_at);
