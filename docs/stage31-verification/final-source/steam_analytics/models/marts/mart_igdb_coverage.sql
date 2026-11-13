SELECT
    COUNT(*) AS total_store_enriched,
    COUNT(sl.store_game_id) AS linked_to_igdb,
    COUNT(*) - COUNT(sl.store_game_id) AS not_linked,
    ROUND(
        COUNT(sl.store_game_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS igdb_coverage_pct
FROM {{ ref('stg_games') }} g
LEFT JOIN {{ ref('stg_igdb_game_store_links') }} sl
    ON sl.store = 'steam'
    AND sl.steam_appid = g.appid
WHERE g.steam_store_success = TRUE