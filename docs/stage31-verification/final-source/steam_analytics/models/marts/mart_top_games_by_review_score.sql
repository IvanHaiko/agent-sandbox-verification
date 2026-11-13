WITH latest_snapshots AS (
    SELECT DISTINCT ON (appid)
        appid,
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
    ls.positive,
    ls.negative,
    ls.total_reviews,
    ls.review_score,
    ls.ccu,
    ls.snapshot_date
FROM {{ ref('stg_games') }} g
JOIN latest_snapshots ls ON ls.appid = g.appid
WHERE ls.total_reviews >= 1000
ORDER BY ls.review_score DESC, ls.total_reviews DESC
LIMIT 50