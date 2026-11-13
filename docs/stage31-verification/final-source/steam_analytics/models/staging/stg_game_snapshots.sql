SELECT
    appid,
    snapshot_date,
    owners,
    ccu,
    positive,
    negative,
    positive + negative AS total_reviews,
    review_score
FROM game_snapshots