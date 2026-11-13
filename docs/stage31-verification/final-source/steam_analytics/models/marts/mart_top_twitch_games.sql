WITH latest_twitch AS (
    SELECT DISTINCT ON (twitch_game_id)
        twitch_game_id,
        twitch_game_name,
        viewer_count,
        stream_count,
        snapshot_time
    FROM {{ ref('stg_twitch_game_snapshots') }}
    ORDER BY twitch_game_id, snapshot_time DESC
),
latest_steam AS (
    SELECT DISTINCT ON (appid)
        appid,
        owners
    FROM {{ ref('stg_game_snapshots') }}
    ORDER BY appid, snapshot_date DESC
)
SELECT
    lt.snapshot_time,
    lt.twitch_game_name,
    lt.viewer_count,
    lt.stream_count,
    c.candidate_method,
    c.final_score AS mapping_score,
    sl.steam_appid,
    g.name AS steam_name,
    ls.owners AS steam_owners_range
FROM latest_twitch lt
LEFT JOIN {{ ref('stg_twitch_igdb_mapping_candidates') }} c
    ON c.twitch_game_id = lt.twitch_game_id
    AND c.status = 'auto_approved'
LEFT JOIN {{ ref('stg_igdb_game_store_links') }} sl
    ON sl.igdb_game_id = c.igdb_game_id
    AND sl.store = 'steam'
LEFT JOIN {{ ref('stg_games') }} g
    ON g.appid = sl.steam_appid
LEFT JOIN latest_steam ls ON ls.appid = g.appid
ORDER BY lt.viewer_count DESC
LIMIT 50