-- IGDB coverage for Steam Store-enriched games
-- Among games successfully enriched from Steam Store, how many have a matching IGDB record?

SELECT
    COUNT(*)                        AS total_store_enriched,
    COUNT(s.store_game_id)          AS linked_to_igdb,
    COUNT(*) - COUNT(s.store_game_id) AS not_linked,
    ROUND(
        COUNT(s.store_game_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100,
        2
    )                               AS igdb_coverage_pct
FROM games g
LEFT JOIN igdb_game_store_links s
    ON s.store = 'steam'
    AND s.steam_appid = g.appid
WHERE g.steam_store_success = TRUE;
