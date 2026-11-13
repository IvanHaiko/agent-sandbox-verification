-- Add human-readable label columns for IGDB game_type and status integer enums.
-- The original integer columns are preserved for exact API fidelity.
ALTER TABLE igdb_games
ADD COLUMN IF NOT EXISTS game_type_label TEXT,
ADD COLUMN IF NOT EXISTS status_label TEXT;
