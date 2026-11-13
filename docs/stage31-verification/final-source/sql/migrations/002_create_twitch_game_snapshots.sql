CREATE TABLE IF NOT EXISTS twitch_game_snapshots (
    id BIGSERIAL PRIMARY KEY,

    snapshot_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    twitch_game_id TEXT NOT NULL,
    twitch_game_name TEXT NOT NULL,

    viewer_count INTEGER NOT NULL DEFAULT 0,
    stream_count INTEGER NOT NULL DEFAULT 0,

    source TEXT NOT NULL DEFAULT 'twitch',

    UNIQUE (snapshot_time, twitch_game_id)
);

CREATE INDEX IF NOT EXISTS idx_twitch_game_snapshots_game_id
ON twitch_game_snapshots (twitch_game_id);

CREATE INDEX IF NOT EXISTS idx_twitch_game_snapshots_snapshot_time
ON twitch_game_snapshots (snapshot_time);

CREATE INDEX IF NOT EXISTS idx_twitch_game_snapshots_viewer_count
ON twitch_game_snapshots (viewer_count DESC);
