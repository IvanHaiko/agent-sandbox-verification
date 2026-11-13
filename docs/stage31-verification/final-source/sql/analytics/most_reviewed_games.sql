SELECT
    g.appid,
    g.name,
    s.total_reviews,
    s.positive,
    s.negative,
    s.review_score,
    s.ccu,
    s.snapshot_date
FROM game_snapshots s
JOIN games g
    ON s.appid = g.appid
WHERE s.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM game_snapshots
)
ORDER BY s.total_reviews DESC
LIMIT 50;