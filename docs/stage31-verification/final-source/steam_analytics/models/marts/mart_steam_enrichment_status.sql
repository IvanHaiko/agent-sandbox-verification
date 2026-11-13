SELECT
    CASE
        WHEN steam_store_updated_at IS NULL THEN 'never_checked'
        WHEN steam_store_success = TRUE     THEN 'success'
        WHEN steam_store_success = FALSE    THEN 'failed_or_skipped'
    END AS status,
    COUNT(*) AS game_count,
    ROUND(COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER () * 100, 2) AS pct
FROM {{ ref('stg_games') }}
GROUP BY 1
ORDER BY 2 DESC