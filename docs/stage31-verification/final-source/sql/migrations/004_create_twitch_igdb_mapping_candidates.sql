CREATE TABLE IF NOT EXISTS twitch_igdb_mapping_candidates (
    id BIGSERIAL PRIMARY KEY,

    twitch_game_id TEXT NOT NULL,
    twitch_game_name TEXT NOT NULL,

    candidate_entity_type TEXT NOT NULL,
    -- game / collection / franchise / non_game

    igdb_game_id INTEGER REFERENCES igdb_games(igdb_game_id) ON DELETE SET NULL,

    name_score NUMERIC,
    final_score NUMERIC,

    candidate_method TEXT NOT NULL,
    -- exact_external_uid / exact_name / fuzzy_name / collection_match / exclusion_list / ai_suggested

    reason TEXT,

    status TEXT NOT NULL DEFAULT 'pending',
    -- pending / auto_approved / approved / rejected

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (
        twitch_game_id,
        candidate_entity_type,
        igdb_game_id,
        candidate_method
    )
);

CREATE INDEX IF NOT EXISTS idx_twitch_igdb_mapping_candidates_twitch_game_id
ON twitch_igdb_mapping_candidates (twitch_game_id);

CREATE INDEX IF NOT EXISTS idx_twitch_igdb_mapping_candidates_igdb_game_id
ON twitch_igdb_mapping_candidates (igdb_game_id);

CREATE INDEX IF NOT EXISTS idx_twitch_igdb_mapping_candidates_status
ON twitch_igdb_mapping_candidates (status);

CREATE INDEX IF NOT EXISTS idx_twitch_igdb_mapping_candidates_final_score
ON twitch_igdb_mapping_candidates (final_score DESC);