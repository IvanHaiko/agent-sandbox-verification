SELECT
    g.appid,
    g.name,
    s.positive,
    s.negative,
    s.total_reviews,
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
AND s.total_reviews >= 1000
ORDER BY s.review_score DESC, s.total_reviews DESC
LIMIT 50;