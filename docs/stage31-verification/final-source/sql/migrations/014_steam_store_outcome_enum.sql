-- Migration 014: outcome-driven Steam Store retry policy.
--
-- Steam Store enrichment previously recorded only a boolean
-- steam_store_success, which could not tell "the game refused to
-- answer, try again" from "the game does not exist, never ask again"
-- from "our own request failed, try again soon". This migration
-- replaces the boolean with an enum, steam_store_outcome, that carries
-- five ongoing values plus one backfill-only value:
--
--   ok               response carried what was asked for
--   refused          source answered, success: false -- may become
--                    available later (unreleased / region-locked / hidden)
--   not_found        no wrapper at all for the requested appid -- usually
--                    removed from the catalogue and not coming back
--   redirected       the response carried a *different* appid's data --
--                    terminal, this appid is never asked again
--   transport_error  no usable answer arrived at all
--   failed_legacy    backfill only, see below -- never written by the
--                    loader going forward
--
-- steam_store_redirect_to carries the target appid when outcome is
-- redirected, as a typed integer column rather than folding it into
-- steam_store_last_error's free text.
--
-- steam_store_attempts counts every outcome where Steam actually
-- answered (ok, refused, not_found, redirected). steam_store_errors
-- counts only transport_error, on its own counter, so a failure to ask
-- never spends one of the chances meant for an actual answer -- the same
-- separation already made for the IGDB search backlog in migration 011.
--
-- Backfill. steam_store_success = TRUE (9 648 rows) becomes 'ok': those
-- games were genuinely fetched and parsed successfully, so nothing is
-- lost by the tighter classification.
--
-- steam_store_success = FALSE (8 864 rows) becomes 'failed_legacy', not
-- 'refused'. This is deliberate and it is a real loss of precision, not
-- an oversight: before this fix, a refusal, a missing wrapper and a
-- transport failure all collapsed into the same FALSE value, and the
-- bronze that would have told them apart was never written for the
-- failure case (that was the original defect this project's Phase 0 set
-- out to fix). There is no way to recover which of the three each of
-- these 8 864 rows actually was. 'failed_legacy' says so plainly, the
-- same way 'load_clock' says "this is a stand-in, not a real observation
-- time" in sample_time_source (migration 010) -- a coarse record must
-- look coarse rather than pretend to a precision the source data cannot
-- support.
--
-- steam_store_attempts and steam_store_errors are left at their column
-- default of 0 for every backfilled row. Neither the 'ok' cooldown nor
-- the 'failed_legacy' cooldown reads either counter (see
-- get_games_for_store_enrichment in src/load.py), and no backfilled row
-- is ever classified transport_error, so there is nothing for an
-- invented count to protect -- and inventing one would be exactly the
-- fabricated-precision failure this migration exists to remove.
--
-- steam_store_success = NULL (26 990 rows, never checked) is left NULL
-- for steam_store_outcome too. NULL means "never asked", these rows were
-- never asked, so that is still the true statement.
--
-- steam_store_success itself survives as a generated column
-- (steam_store_outcome = 'ok'), so the two existing dbt marts that read
-- it (mart_igdb_coverage, mart_steam_enrichment_status) and the ad hoc
-- queries in sql/analytics/ keep working unchanged -- the boolean is now
-- derived from the enum instead of living beside it, so the two cannot
-- drift apart the way steam_store_success itself used to drift from the
-- true outcome. Postgres cannot convert an existing column into a
-- GENERATED column with a plain ALTER, so it is dropped and re-added
-- under the same name within this migration, after the enum backfill
-- above has already copied out everything the boolean knew.
--
-- One live object does depend on the column: public.stg_games, a dbt
-- staging VIEW (SELECT ... steam_store_success ... FROM games), which
-- blocks a plain DROP COLUMN. The \d games output above does not show
-- it -- that only lists FK-referencing tables, not views -- it was
-- found instead by checking pg_depend, which shows exactly one
-- dependent, this view. Nothing else in the database depends on the
-- column: the two dbt marts that read steam_store_success
-- (mart_igdb_coverage, mart_steam_enrichment_status) are materialized as
-- TABLEs, not views, so they hold no live dependency on it and are
-- simply stale content-wise, same as after any upstream data change,
-- until the next dbt run.
--
-- CASCADE therefore drops stg_games along with the column. This is a
-- migration-owned change to a live warehouse object, not an edit to any
-- file under steam_analytics/ -- stg_games.sql itself is untouched, its
-- compiled SQL is unaffected (it already just SELECTs
-- steam_store_success, which still exists afterward with identical
-- values, now generated instead of stored), and `dbt build` (or `dbt run
-- --select stg_games+`) recreates the view and everything downstream of
-- it exactly as before. It must be run once after this migration
-- applies -- flagged here and in the session report, rather than invoked
-- from this ingestion-owned migration, which has no business running dbt.
--
-- ---------------------------------------------------------------------
-- Added on 2026-08-12, after this file had already been applied. The
-- text below changes nothing that ran. It records the rule this
-- migration is the reason for.
--
-- A migration owned by the raw layer may not drop an object owned by
-- another layer. If a DROP needs CASCADE, stop and show through
-- pg_depend what will go, before executing rather than after. Here the
-- dependency was found by a review pass once stg_games was already gone,
-- which is an autopsy, not a decision. The check is cheap:
--
--   SELECT DISTINCT dependent.relname, dependent.relkind
--   FROM pg_depend d
--   JOIN pg_rewrite r ON r.oid = d.objid
--   JOIN pg_class dependent ON dependent.oid = r.ev_class
--   WHERE d.refobjid = 'games'::regclass
--     AND d.refobjsubid = (
--         SELECT attnum FROM pg_attribute
--         WHERE attrelid = 'games'::regclass
--           AND attname = 'steam_store_success'
--     )
--
-- The recovery, when it finally ran, also exposed why dbt had looked
-- broken: the connection profile lived in ~/.dbt with the pre-move port
-- 5432. It now lives in steam_analytics/profiles.yml, in the repository.
-- ---------------------------------------------------------------------
--
-- The loader (src/load.py) stops writing steam_store_success directly
-- as of this migration -- it writes steam_store_outcome only, and the
-- boolean simply follows.

ALTER TABLE games
ADD COLUMN steam_store_outcome TEXT
    CHECK (steam_store_outcome IN ('ok', 'refused', 'not_found', 'redirected', 'transport_error', 'failed_legacy'));

ALTER TABLE games
ADD COLUMN steam_store_redirect_to INTEGER;

ALTER TABLE games
ADD COLUMN steam_store_attempts INTEGER NOT NULL DEFAULT 0;

ALTER TABLE games
ADD COLUMN steam_store_errors INTEGER NOT NULL DEFAULT 0;

UPDATE games
SET steam_store_outcome = 'ok'
WHERE steam_store_success = TRUE;

UPDATE games
SET steam_store_outcome = 'failed_legacy'
WHERE steam_store_success = FALSE;

ALTER TABLE games
DROP COLUMN steam_store_success CASCADE;

ALTER TABLE games
ADD COLUMN steam_store_success BOOLEAN
    GENERATED ALWAYS AS (steam_store_outcome = 'ok') STORED;
