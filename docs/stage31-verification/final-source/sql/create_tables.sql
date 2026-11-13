-- Create tables for the Steam Gaming Analytics MVP.
-- This schema stores stable game data, historical metric snapshots,
-- and a simple many-to-many relationship between games and genres.

DROP TABLE IF EXISTS game_genres;
DROP TABLE IF EXISTS game_snapshots;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS games;


CREATE TABLE IF NOT EXISTS games (
    -- Steam application ID. This is the main unique identifier for each game.
    appid INTEGER PRIMARY KEY,

    -- Game name. Prefer Steam Store name if available.
    name TEXT NOT NULL,

    -- Main developer name for MVP.
    developer TEXT,

    -- Main publisher name for MVP.
    publisher TEXT,

    -- Whether the game is free-to-play.
    -- Prefer Steam Store is_free if available.
    is_free BOOLEAN,

    -- Release date from Steam Store.
    -- Stored as text for MVP because Steam dates may have different formats:
    -- '21 Aug, 2012', 'Coming soon', 'To be announced', etc.
    release_date TEXT,

    -- Main header image URL from Steam Store.
    header_image TEXT,

    -- Last Steam Store enrichment attempt and result.
    steam_store_updated_at TIMESTAMP,
    steam_store_success BOOLEAN,
    steam_store_last_error TEXT,

    -- Timestamp when this row was first inserted.
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Timestamp when this row was last updated.
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE game_snapshots (
    -- Internal unique ID for each snapshot row.
    snapshot_id BIGSERIAL PRIMARY KEY,

    -- Steam application ID. References the games table.
    appid INTEGER NOT NULL REFERENCES games(appid) ON DELETE CASCADE,

    -- Date when this snapshot was collected.
    snapshot_date DATE NOT NULL,

    -- Number of positive Steam reviews at snapshot time.
    positive INTEGER NOT NULL DEFAULT 0,

    -- Number of negative Steam reviews at snapshot time.
    negative INTEGER NOT NULL DEFAULT 0,

    -- Total number of reviews: positive + negative.
    total_reviews INTEGER NOT NULL DEFAULT 0,

    -- Calculated review score: positive / (positive + negative).
    -- Example: 0.8670 means 86.70%.
    review_score NUMERIC(5, 4),

    -- Estimated owners range from SteamSpy.
    -- Example: '100,000,000 .. 200,000,000'
    owners TEXT,

    -- Current price, usually stored in cents.
    -- Example: 1999 means 19.99.
    price INTEGER NOT NULL DEFAULT 0,

    -- Initial price before discount, usually stored in cents.
    initialprice INTEGER NOT NULL DEFAULT 0,

    -- Discount percentage.
    -- Example: 50 means 50%.
    discount INTEGER NOT NULL DEFAULT 0,

    -- Current concurrent users from SteamSpy.
    ccu INTEGER NOT NULL DEFAULT 0,

    -- Timestamp when this snapshot row was inserted.
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicate daily snapshots for the same game.
    UNIQUE (appid, snapshot_date)
);


CREATE TABLE genres (
    -- Internal unique ID for each genre.
    genre_id BIGSERIAL PRIMARY KEY,

    -- Genre name, for example: Action, RPG, Strategy.
    name TEXT NOT NULL UNIQUE
);


CREATE TABLE game_genres (
    -- Steam application ID. References the games table.
    appid INTEGER NOT NULL REFERENCES games(appid) ON DELETE CASCADE,

    -- Genre ID. References the genres table.
    genre_id BIGINT NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,

    -- One game can have each genre only once.
    PRIMARY KEY (appid, genre_id)
);


-- Index for faster lookup of snapshots by date.
CREATE INDEX idx_game_snapshots_snapshot_date
ON game_snapshots(snapshot_date);


-- Index for faster lookup of snapshots by appid.
CREATE INDEX idx_game_snapshots_appid
ON game_snapshots(appid);


-- Index for faster sorting/filtering by current concurrent users.
CREATE INDEX idx_game_snapshots_ccu
ON game_snapshots(ccu);


-- Index for faster sorting/filtering by calculated review score.
CREATE INDEX idx_game_snapshots_review_score
ON game_snapshots(review_score);


-- Index for faster sorting/filtering by total review count.
CREATE INDEX idx_game_snapshots_total_reviews
ON game_snapshots(total_reviews);


-- Index for faster lookup of genres by name.
CREATE INDEX idx_genres_name
ON genres(name);
