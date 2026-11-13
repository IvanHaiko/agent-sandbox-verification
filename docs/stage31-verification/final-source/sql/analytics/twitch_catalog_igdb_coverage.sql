-- Twitch categories catalog: IGDB ID coverage
-- Shows what share of known Twitch categories have a direct igdb_id from Twitch Helix API.

SELECT
    COUNT(*)                                                    AS total_categories,
    COUNT(*) FILTER (WHERE igdb_id IS NOT NULL)                 AS with_helix_igdb_id,
    COUNT(*) FILTER (WHERE igdb_id IS NULL)                     AS without_igdb_id,
    ROUND(
        COUNT(*) FILTER (WHERE igdb_id IS NOT NULL)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100,
        2
    )                                                           AS helix_igdb_coverage_pct
FROM twitch_categories_catalog;
