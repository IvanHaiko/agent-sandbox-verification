WITH latest_snapshots AS (
    SELECT DISTINCT ON (appid)
        appid,
        owners,
        ccu,
        positive,
        negative,
        total_reviews,
        review_score,
        snapshot_date
    FROM {{ ref('stg_game_snapshots') }}
    ORDER BY appid, snapshot_date DESC
)
SELECT
    g.appid,
    g.name,
    g.developer,
    g.publisher,
    ls.owners,
    ls.ccu,
    ls.positive,
    ls.negative,
    ls.total_reviews,
    ls.review_score,
    ls.snapshot_date,
    CASE WHEN sl.store_game_id IS NOT NULL THEN TRUE ELSE FALSE END AS linked_to_igdb
FROM {{ ref('stg_games') }} g
JOIN latest_snapshots ls ON ls.appid = g.appid
LEFT JOIN {{ ref('stg_igdb_game_store_links') }} sl
    ON sl.store = 'steam'
    AND sl.steam_appid = g.appid
ORDER BY ls.ccu DESC NULLS LAST
LIMIT 100