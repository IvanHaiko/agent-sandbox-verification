-- Top Steam games by latest CCU (concurrent users), from most recent snapshot
-- Uses game_snapshots for CCU data, joined to games for metadata.
-- Shows whether each game is also linked to IGDB.

WITH latest_snapshots AS (
    SELECT DISTINCT ON (appid)
        appid,
        owners,
        ccu,
        snapshot_date
    FROM game_snapshots
    ORDER BY appid, snapshot_date DESC
)
SELECT
    g.appid,
    g.name,
    g.developer,
    g.publisher,
    ls.owners                           AS owners_range,
    ls.ccu                              AS latest_ccu,
    ls.snapshot_date,
    g.steam_store_success,
    CASE WHEN sl.store_game_id IS NOT NULL THEN TRUE ELSE FALSE END AS linked_to_igdb,
    sl.igdb_game_id
FROM games g
JOIN latest_snapshots ls
    ON ls.appid = g.appid
LEFT JOIN igdb_game_store_links sl
    ON sl.store = 'steam'
    AND sl.steam_appid = g.appid
ORDER BY ls.ccu DESC NULLS LAST
LIMIT 100;
