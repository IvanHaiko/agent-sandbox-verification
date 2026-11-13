CREATE TABLE IF NOT EXISTS igdb_games (
    igdb_game_id INTEGER PRIMARY KEY,

    name TEXT NOT NULL,
    slug TEXT,
    summary TEXT,
    url TEXT,

    first_release_date DATE,

    rating NUMERIC,
    rating_count INTEGER,
    aggregated_rating NUMERIC,
    aggregated_rating_count INTEGER,
    total_rating NUMERIC,
    total_rating_count INTEGER,

    hypes INTEGER,
    follows INTEGER,

    game_type INTEGER,
    status INTEGER,

    raw_json JSONB NOT NULL,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_igdb_games_name
ON igdb_games (name);

CREATE INDEX IF NOT EXISTS idx_igdb_games_slug
ON igdb_games (slug);

CREATE INDEX IF NOT EXISTS idx_igdb_games_total_rating
ON igdb_games (total_rating DESC);


CREATE TABLE IF NOT EXISTS igdb_game_store_links (
    id BIGSERIAL PRIMARY KEY,

    igdb_game_id INTEGER NOT NULL REFERENCES igdb_games(igdb_game_id) ON DELETE CASCADE,

    store TEXT NOT NULL,
    store_game_id TEXT NOT NULL,
    store_url TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (store, store_game_id)
);

CREATE INDEX IF NOT EXISTS idx_igdb_game_store_links_igdb_game_id
ON igdb_game_store_links (igdb_game_id);

CREATE INDEX IF NOT EXISTS idx_igdb_game_store_links_store_game_id
ON igdb_game_store_links (store, store_game_id);


CREATE TABLE IF NOT EXISTS twitch_categories (
    twitch_game_id TEXT PRIMARY KEY,
    twitch_game_name TEXT NOT NULL,

    is_game BOOLEAN,

    igdb_game_id INTEGER REFERENCES igdb_games(igdb_game_id) ON DELETE SET NULL,

    mapping_status TEXT NOT NULL DEFAULT 'unmapped',
    mapping_method TEXT,
    mapping_confidence NUMERIC,
    notes TEXT,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_twitch_categories_igdb_game_id
ON twitch_categories (igdb_game_id);

CREATE INDEX IF NOT EXISTS idx_twitch_categories_mapping_status
ON twitch_categories (mapping_status);