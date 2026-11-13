-- Migration 016: typed, numeric Steam appid on igdb_game_store_links, and a
-- flag for the comma-separated bundle uids.
--
-- store_game_id (IGDB calls the same value "uid") is TEXT because IGDB's
-- other stores use free-form identifiers -- Epic's uid is a GUID, Microsoft's
-- is a store SKU. Steam's uid is almost always a bare numeric appid, but 16
-- of 16 366 steam rows carry several appids packed into one string,
-- comma-separated, because IGDB modelled a bundle / GOTY / collection
-- edition as a single external_games entry instead of one row per appid.
-- Marts that want an integer appid have been casting store_game_id inline,
-- which works for 16 350 rows and throws on the other 16. This migration
-- moves that cast into the schema, once, as a generated column, so every
-- mart reads a typed steam_appid instead of repeating the cast (and the
-- failure) itself.
--
-- steam_appid: uid cast to integer when store = 'steam' and the uid is
-- purely numeric, else NULL. NULL covers two different situations on
-- purpose -- a non-steam row (Epic, Microsoft, GOG, ...), where the concept
-- does not apply at all, and a steam bundle row, where it does apply but a
-- single integer cannot represent it. Both get NULL because this project
-- writes null rather than guessing (see ARCHITECTURE.md 2.1) -- nothing here
-- attempts to pick one appid out of a bundle string.
--
-- is_bundle: TRUE when store = 'steam' and the uid contains a comma, NULL
-- for every non-steam row, FALSE for a single-appid steam row. The NULL for
-- non-steam rows is deliberate, not an oversight -- we have never asked IGDB
-- whether an Epic or Microsoft uid packs several ids, so "not a bundle" would
-- be an unearned claim. Only "steam and comma-separated" is actually known.
--
-- Naming this column is_bundle is already an interpretation of what a
-- comma-separated uid means. Measured from game_type in raw_json (not
-- game_type_label, which is unbackfilled for 5 916 of 24 542 igdb_games
-- rows, including this table's own comma-uid rows -- reading the label
-- column here would have quietly undercounted):
--
--   SELECT g.raw_json->>'game_type', count(*)
--   FROM igdb_game_store_links l
--   JOIN igdb_games g ON g.igdb_game_id = l.igdb_game_id
--   WHERE l.store = 'steam' AND l.store_game_id LIKE '%,%'
--   GROUP BY 1;
--
-- game_type 3 (bundle) = 9, game_type 13 (pack) = 1, game_type 0
-- (main_game) = 6 of the 16 comma-separated steam rows -- so 10 of 16 carry
-- some non-main_game classification, not a bundle-only 5, and the other 6
-- are IGDB main_game entries (GOTY editions, deluxe editions, collections)
-- that pack several appids into one uid without IGDB ever flagging them as
-- anything but a plain game. game_type still cannot be the test: those 6
-- would be missed entirely. The column is generated from the shape of the
-- uid -- does it contain a comma -- never from game_type, and this comment
-- is here so a future reader does not assume otherwise.
--
-- Both columns are GENERATED ALWAYS ... STORED, the same device migration
-- 014 used for steam_store_success -- derived from source columns that
-- remain the single source of truth, so the derived value and the source
-- can never drift apart, and computed once at write time rather than on
-- every read. store_game_id itself is untouched: the verbatim uid stays
-- exactly as IGDB sent it, nothing is rewritten, nothing is deleted, and no
-- row is added or removed by this migration. 16 366 steam links before,
-- 16 366 after.
--
-- The store = 'steam' guard must run before the ::int cast is even
-- attempted, or the cast raises on the 3 950 microsoft and 2 185 epic rows,
-- whose uids are GUIDs and SKUs, not numbers. Verified directly against
-- this database, not assumed: a CASE WHEN with the store check as the first
-- AND-ed condition never evaluates uid::int for a non-matching arm --
--
--   SELECT store, uid, CASE WHEN store = 'steam' AND uid ~ '^[0-9]+$'
--          THEN uid::int ELSE NULL END
--   FROM (VALUES ('epic', 'afded2bee4b4421981e30547bfe30636'),
--                ('steam', '204290'),
--                ('steam', '204281,204282'),
--                ('microsoft', '9NBLGGH4R315')) v(store, uid)
--
-- returns (NULL, 204290, NULL, NULL) with no error, and the same expression
-- built as an actual GENERATED ... STORED column on a scratch table behaves
-- identically -- both checked live against port 5433 while writing this
-- migration, not inferred from how CASE is documented to behave.
--
-- No DROP anywhere in this file. The pg_depend check migration 014 exists to
-- remind future migrations to run (adapted to this table) found exactly one
-- dependent object, the dbt view stg_igdb_game_store_links, and adding
-- columns does not touch it -- there is nothing here for that view, or
-- anything else, to depend on losing.
--
-- An index on steam_appid alone is added below on the stated assumption
-- that the marts join on it. That assumption was wrong -- read against the
-- live plan one migration later, all three marts that touch steam_appid
-- read this table with a Seq Scan feeding a hash join, never an index
-- probe -- and migration 017 drops it rather than have this paragraph
-- rewritten to match. See 017 for the exact plan per mart, the pg_depend
-- check that preceded the drop, and how a trimmed-down EXPLAIN of one mart
-- gave the opposite, wrong answer before the real compiled SQL was used.
-- Left here, not deleted, so the mistake and its correction both stay on
-- the record.

ALTER TABLE igdb_game_store_links
ADD COLUMN steam_appid INTEGER
    GENERATED ALWAYS AS (
        CASE
            WHEN store = 'steam' AND store_game_id ~ '^[0-9]+$'
                THEN store_game_id::integer
            ELSE NULL
        END
    ) STORED;

ALTER TABLE igdb_game_store_links
ADD COLUMN is_bundle BOOLEAN
    GENERATED ALWAYS AS (
        CASE
            WHEN store = 'steam'
                THEN (store_game_id LIKE '%,%')
            ELSE NULL
        END
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_igdb_game_store_links_steam_appid
ON igdb_game_store_links (steam_appid);
