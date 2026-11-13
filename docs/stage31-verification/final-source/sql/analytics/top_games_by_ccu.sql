SELECT
    g.appid,
    g.name,
    s.ccu,
    s.positive,
    s.negative,
    s.total_reviews,
    s.review_score,
    s.snapshot_date
FROM game_snapshots s
JOIN games g
    ON s.appid = g.appid
WHERE s.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM game_snapshots
)
ORDER BY s.ccu DESC
LIMIT 50;