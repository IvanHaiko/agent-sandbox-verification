-- Top Twitch games (by viewer count) with optional auto-approved IGDB mapping and Steam link.
-- This is the key cross-source join: Twitch -> IGDB -> Steam, using LEFT JOINs to keep unmapped Twitch games visible.
-- Only includes the most recent snapshot per Twitch game.

WITH latest_snapshots AS (
    SELECT DISTINCT ON (twitch_game_id)
        twitch_game_id,
        twitch_game_name,
        viewer_count,
        stream_count,
        snapshot_time
    FROM twitch_game_snapshots
    ORDER BY twitch_game_id, snapshot_time DESC
),
latest_steam_snapshots AS (
    SELECT DISTINCT ON (appid)
        appid,
        owners
    FROM game_snapshots
    ORDER BY appid, snapshot_date DESC
)
SELECT
    ls.snapshot_time,
    ls.twitch_game_name,
    ls.viewer_count,
    ls.stream_count,
    c.candidate_method,
    c.final_score          AS mapping_score,
    i.igdb_game_id,
    i.name                 AS igdb_name,
    s.steam_appid,
    g.name                 AS steam_name,
    ss.owners              AS steam_owners_range
FROM latest_snapshots ls
LEFT JOIN twitch_igdb_mapping_candidates c
    ON c.twitch_game_id = ls.twitch_game_id
    AND c.status = 'auto_approved'
LEFT JOIN igdb_games i
    ON i.igdb_game_id = c.igdb_game_id
LEFT JOIN igdb_game_store_links s
    ON s.igdb_game_id = i.igdb_game_id
    AND s.store = 'steam'
LEFT JOIN games g
    ON g.appid = s.steam_appid
LEFT JOIN latest_steam_snapshots ss
    ON ss.appid = g.appid
ORDER BY ls.viewer_count DESC
LIMIT 50;
