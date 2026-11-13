-- Migration 013: null out is_free = TRUE where it was never confirmed by
-- Steam Store.
--
-- Before this fix, transform_steamspy_game read is_free = (price == 0),
-- but SteamSpy sends price == "0" both for genuinely free-to-play games
-- and for unreleased/delisted apps -- the source itself cannot tell those
-- two apart. 6 100 games were flagged is_free = TRUE on that non-evidence.
-- 834 more carry is_free = TRUE confirmed independently by Steam Store
-- (steam_store_success = TRUE) -- those are left untouched.
--
-- Only TRUE values are nulled, never FALSE. This asymmetry is
-- intentional, not an oversight: price > 0 reliably means "not free" --
-- SteamSpy would not report a positive price for a free game -- so an
-- unconfirmed is_free = FALSE stays a fact worth keeping. price == 0 does
-- not mean "free", it means "SteamSpy did not say", which is exactly the
-- fabricated-zero failure this project treats as a defect elsewhere (see
-- sample_time_source in migration 010). Nulling FALSE too would throw
-- away real information to make the asymmetry disappear instead of
-- explaining it.
--
-- Affected appids were exported to data/audit/ before this ran:
-- 013_pre_migration_free_unconfirmed_6100.csv (6 100 rows, appid, name,
-- is_free, steam_store_success, steam_store_updated_at, updated_at) --
-- gitignored, same pattern as migration 012's pre-migration dump.
--
-- No provenance column is added for is_free the way sample_time_source
-- was added for Twitch sample_time. That case recorded which of two
-- approximations of the same fact a value was, load time standing in for
-- observation time. This case is different: price == 0 is not a worse
-- version of "is_free = TRUE", it is a different claim (unknown, not
-- free-but-uncertain), and provenance is already derivable from
-- steam_store_success without a new column.

UPDATE games
SET
    is_free = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE
    is_free = TRUE
    AND steam_store_success IS NOT TRUE;
