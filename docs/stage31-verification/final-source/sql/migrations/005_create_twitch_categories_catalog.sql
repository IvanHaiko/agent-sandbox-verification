CREATE TABLE IF NOT EXISTS twitch_categories_catalog (
    twitch_game_id TEXT PRIMARY KEY,
    twitch_game_name TEXT NOT NULL,
    box_art_url TEXT,
    igdb_id INTEGER,

    source TEXT NOT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_twitch_categories_catalog_name
ON twitch_categories_catalog (twitch_game_name);

CREATE INDEX IF NOT EXISTS idx_twitch_categories_catalog_igdb_id
ON twitch_categories_catalog (igdb_id);
