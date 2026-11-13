"""
Every loader, run twice against the same bronze file, must change nothing.

This is the test that did not exist. `test_load_twitch_file_uses_on_conflict`
asserted that the SQL *string* contained `ON CONFLICT … DO NOTHING` and its
docstring claimed that proved no duplicates; duplicates were in the database at
the time. A string cannot be idempotent. A second run can.

The digest deliberately excludes bookkeeping timestamps (`created_at`,
`updated_at`, `steam_store_updated_at`) — those move on any write and say
nothing about whether the *data* moved.

The attempt counters are asserted **by value**, not only compared across the two
runs. An earlier version of this file claimed the `is_replay` guard was covered
"in both directions" while the comparison was `0 == 0`, and a review proved the
claim empty: making an answered request never count as an attempt passed the
whole suite. Both directions now mean something specific — an answer counts once,
a replay counts nothing — and each was verified by re-running that mutation and
watching this file fail.
"""

import pytest

from tests.conftest import table_digest

GAMES = "appid, name, developer, publisher, is_free, release_date, header_image"
GAME_STATE = (
    "appid, steam_store_outcome, steam_store_redirect_to, "
    "steam_store_attempts, steam_store_errors, steam_store_success"
)
SNAPSHOTS = (
    "appid, snapshot_date, positive, negative, total_reviews, review_score, "
    "owners, price, initialprice, discount, ccu"
)
TWITCH = (
    "sample_hour, twitch_game_id, twitch_game_name, viewer_count, "
    "stream_count, sample_time, sample_time_source"
)
CATALOG = "twitch_game_id, twitch_game_name, box_art_url, igdb_id, source"
IGDB = "igdb_game_id, name, slug, first_release_date, total_rating"
LINKS = "igdb_game_id, store, store_game_id, store_url"


def load_twice(source, path, tables, snapshot_date=None):
    """Load the same file twice, returning the digests taken after each run."""

    from src.db import get_db_connection
    from src.load import load_data

    def digests():
        with get_db_connection() as connection:
            return {t: table_digest(connection, t, cols) for t, cols in tables.items()}

    load_data(source, path, snapshot_date=snapshot_date)
    first = digests()

    load_data(source, path, snapshot_date=snapshot_date)
    second = digests()

    return first, second


def test_steamspy_page_loads_once(test_database, fixture_path):
    tables = {"games": GAMES, "game_snapshots": SNAPSHOTS}
    first, second = load_twice(
        "steamspy", fixture_path("steamspy_all_page.json"), tables, "2026-05-09"
    )

    assert first["games"][0] == 7, "the fixture holds 7 games"
    assert first["game_snapshots"][0] == 7
    assert first == second, "a second load changed the data"


def test_a_later_observation_of_the_same_day_wins(test_database, fixture_path):
    """
    Idempotence is not "ignore the second file" — it is "the same key ends up in
    one row holding the newer answer".

    Every other loader test replays a byte-identical file, which any conflict
    policy survives. A review proved it: turning `insert_snapshot`'s
    `ON CONFLICT … DO UPDATE` into `DO NOTHING` left the whole suite green,
    while in production it would mean SteamSpy's afternoon revision is silently
    discarded.

    The two fixtures here are real observations of the same five games two days
    apart, caught as a sale ended: `price` and `discount` both move, which are
    exactly the fields this project is about.
    """

    import json

    from src.db import get_db_connection
    from src.load import load_data

    before = fixture_path("steamspy_revision_before.json")
    after = fixture_path("steamspy_revision_after.json")
    expected = json.loads(after.read_text(encoding="utf-8"))

    load_data("steamspy", before, snapshot_date="2026-05-09")
    load_data("steamspy", after, snapshot_date="2026-05-09")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM game_snapshots")
            assert cursor.fetchone()[0] == len(expected), (
                "a revision created rows instead of updating them"
            )

            cursor.execute(
                "SELECT appid, price, discount FROM game_snapshots ORDER BY appid"
            )
            stored = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    for appid, record in expected.items():
        assert stored[int(appid)] == (int(record["price"]), int(record["discount"])), (
            f"appid {appid} kept the older observation"
        )


def test_steamspy_never_claims_a_game_is_free(test_database, fixture_path):
    """
    `price == 0` supports nothing, so SteamSpy may write `false` or nothing at all.

    Four of the fixture's games report `price: "0"` and are **not** free — the
    Store confirms it — which is the trap that produced 6 100 fabricated values.
    A review found this was asserted nowhere at the database level: reintroducing
    `is_free = True` for a zero price passed the entire suite, because the value
    was only ever compared to itself inside a digest.
    """

    from src.db import get_db_connection
    from src.load import load_data

    load_data(
        "steamspy", fixture_path("steamspy_all_page.json"), snapshot_date="2026-05-09"
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM games WHERE is_free IS TRUE")
            assert cursor.fetchone()[0] == 0, "SteamSpy asserted free-to-play"

            cursor.execute(
                "SELECT is_free FROM games WHERE appid = 271590"  # GTA V Legacy, price 0
            )
            assert cursor.fetchone()[0] is None, "a zero price became a claim"

            cursor.execute(
                "SELECT is_free FROM games WHERE appid = 1623730"  # Palworld, price 2999
            )
            assert cursor.fetchone()[0] is False, "a positive price supports 'not free'"


def test_twitch_streams_load_once(test_database, fixture_path):
    tables = {"twitch_game_snapshots": TWITCH}
    first, second = load_twice("twitch", fixture_path("twitch_streams.json"), tables)

    assert first["twitch_game_snapshots"][0] > 0
    assert first == second, "a second load of the same sample duplicated rows"


def test_twitch_sample_hour_comes_from_the_file_not_the_clock(
    test_database, fixture_path
):
    """
    The observation hour must be read from the payload's `fetched_at`.

    If it were taken from the insert clock, replaying a file would file the same
    observation under whatever hour the replay happened in — the defect migration
    010 had to undo after 008 wrote a 58-minute load delay into the data.
    """

    import json

    from src.db import get_db_connection
    from src.load import load_data

    payload = json.loads(
        fixture_path("twitch_streams.json").read_text(encoding="utf-8")
    )
    expected_hour = payload["fetched_at"][:13]

    load_data("twitch", fixture_path("twitch_streams.json"))

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT to_char(sample_hour, 'YYYY-MM-DD\"T\"HH24') "
                "FROM twitch_game_snapshots"
            )
            hours = [row[0] for row in cursor.fetchall()]

    assert hours == [expected_hour]


def test_twitch_games_lookup_loads_once(test_database, fixture_path):
    tables = {"twitch_categories_catalog": CATALOG}
    first, second = load_twice(
        "twitch_games_lookup", fixture_path("twitch_games_lookup.json"), tables
    )

    assert first["twitch_categories_catalog"][0] == 12
    assert first == second


def test_categories_without_an_igdb_id_survive_the_load(test_database, fixture_path):
    """
    Dota 2 and Counter-Strike carry no `igdb_id` from Helix. They must land in
    the catalogue anyway, with a null id — dropping them is how 13.7% of observed
    attention became invisible at rung one.

    The fixture also holds non-game categories with no id (Just Chatting's
    neighbours). Both kinds must survive the load: deciding that a category is
    not a game is a later, explicit step, not something a loader does by
    dropping rows it cannot resolve.
    """

    from src.db import get_db_connection
    from src.load import load_data

    load_data("twitch_games_lookup", fixture_path("twitch_games_lookup.json"))

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT twitch_game_name FROM twitch_categories_catalog "
                "WHERE igdb_id IS NULL ORDER BY twitch_game_name"
            )
            names = [row[0] for row in cursor.fetchall()]

    assert {"Counter-Strike", "Dota 2"} <= set(names), "a real game was dropped"
    assert len(names) == 6, "non-game categories must survive the load too"


def test_igdb_search_loads_once(test_database, fixture_path):
    """
    Counts are asserted per table, not just `> 0` on one of them.

    A review pointed out that comparing two digests proves nothing when both
    tables are empty: making the store-link upsert a no-op left this test green,
    because it then compared one empty table to another.
    """

    tables = {"igdb_games": IGDB, "igdb_game_store_links": LINKS}
    first, second = load_twice("igdb", fixture_path("igdb_games_search.json"), tables)

    assert first["igdb_games"][0] == 1, "the fixture holds one IGDB game"
    assert first["igdb_game_store_links"][0] >= 1, "its store links were dropped"
    assert first == second


def test_igdb_store_links_get_a_typed_steam_appid(test_database, fixture_path):
    """
    Migration 016 adds steam_appid / is_bundle as generated columns.

    The fixture (`8228`, `2959`, `362774` from a real IGDB search response,
    plus `114795` spliced in from a separate archive file) carries every uid
    shape the columns need to distinguish: a plain numeric steam uid, a
    comma-separated bundle uid, a non-steam uid that is not numeric (Epic),
    and -- the case that made the columns' store = 'steam' guard worth
    having -- a non-steam uid that *is* purely numeric (PlayStation).
    Without that last shape, dropping the guard from the steam_appid
    expression alone is invisible to this test: every other non-steam uid in
    the fixture is a GUID or SKU that already yields NULL on its own.

    game_type for 362774, read from raw_json (not game_type_label, which is
    unbackfilled for 5 916 of 24 542 igdb_games rows and is NULL for this
    row), is 3 -- IGDB_GAME_TYPES maps that to 'bundle'. That happens to
    agree with the column here, but only because this particular row is one
    of the 10 (of 16) comma-uid rows IGDB did classify as bundle/pack; 6
    others are not, which is the actual reason detection is by uid shape and
    not by game_type -- see migration 016's comment for the measurement.
    """

    from src.db import get_db_connection

    fixture = fixture_path("igdb_games_search_steam_uid_shapes.json")

    tables = {"igdb_game_store_links": LINKS + ", steam_appid, is_bundle"}
    first, second = load_twice("igdb", fixture, tables)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            # 362774: the comma-separated bundle uid.
            cursor.execute(
                "SELECT steam_appid, is_bundle FROM igdb_game_store_links "
                "WHERE igdb_game_id = 362774 AND store = 'steam'"
            )
            bundle_row = cursor.fetchone()

            # 8228: a plain numeric steam uid.
            cursor.execute(
                "SELECT steam_appid, is_bundle FROM igdb_game_store_links "
                "WHERE igdb_game_id = 8228 AND store = 'steam'"
            )
            single_appid_row = cursor.fetchone()

            # 2959: a non-steam (Epic) uid, alongside its own steam link.
            cursor.execute(
                "SELECT steam_appid, is_bundle FROM igdb_game_store_links "
                "WHERE igdb_game_id = 2959 AND store = 'epic' "
                "AND store_game_id = 'afded2bee4b4421981e30547bfe30636'"
            )
            non_steam_row = cursor.fetchone()

            # 114795: a non-steam (PlayStation) uid that is purely numeric --
            # the case that catches a store = 'steam' guard dropped from the
            # steam_appid expression alone. Every other non-steam uid in this
            # fixture is a GUID or SKU, which already yields NULL with or
            # without the guard.
            cursor.execute(
                "SELECT steam_appid, is_bundle FROM igdb_game_store_links "
                "WHERE igdb_game_id = 114795 AND store = 'playstation' "
                "AND store_game_id = '232352'"
            )
            numeric_non_steam_row = cursor.fetchone()

    assert bundle_row == (None, True), "a bundle uid must not fabricate an appid"
    assert single_appid_row == (204290, False), "a plain uid must cast cleanly"
    assert non_steam_row == (None, None), (
        "a non-steam row must not claim to know whether it is a bundle"
    )
    assert numeric_non_steam_row == (None, None), (
        "a numeric non-steam uid must not fabricate a steam_appid -- this is "
        "what the store = 'steam' guard on steam_appid exists to stop"
    )

    assert first == second, "loading the fixture twice moved the store links"
    assert first["igdb_game_store_links"][0] >= 5, (
        "expected steam (x2), epic (x2) and the bundle row"
    )


def seed_game(appid: int) -> None:
    """
    Put the appid in `games` first.

    Store enrichment only ever runs over appids SteamSpy already catalogued, so
    in production the row always exists. A test that skips this step measures an
    UPDATE against no rows and passes for the wrong reason.
    """

    from src.db import get_db_connection

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO games (appid, name) VALUES (%s, %s) "
                "ON CONFLICT (appid) DO NOTHING",
                (appid, f"seeded-{appid}"),
            )
        connection.commit()


@pytest.mark.parametrize(
    "fixture, appid, expected_outcome, expected_attempts",
    [
        ("steam_store_ok.json", 730, "ok", 1),
        ("steam_store_refused.json", 280, "refused", 1),
        ("steam_store_redirected.json", 100, "redirected", 1),
        # A legacy file carries no `fetched_at`, so the replay guard compares
        # NULL to NULL, matches, and counts nothing. That asymmetry is not an
        # oversight: a file that cannot date itself gives the loader no way to
        # tell a first read from a replay, and the project's rule is that what
        # cannot be known is not asserted. Pinned here so a future change to the
        # guard is a decision rather than a side effect.
        ("steam_store_legacy_no_envelope.json", 730, "ok", 0),
    ],
)
def test_steam_store_outcomes_load_once(
    test_database, fixture_path, fixture, appid, expected_outcome, expected_attempts
):
    """
    Each envelope outcome lands, and a replay does not move the counters.

    The legacy file — a bare body with no envelope — must still read as `ok`:
    3 148 of those exist and bronze is never rewritten, so the loader carries the
    compatibility instead.
    """

    from src.db import get_db_connection
    from src.load import load_data

    seed_game(appid)

    outcome = load_data(
        "steam_store", fixture_path(fixture), snapshot_date="2026-08-12"
    )
    assert outcome == expected_outcome

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT steam_store_outcome, steam_store_attempts, steam_store_errors "
                "FROM games WHERE appid = %s",
                (appid,),
            )
            stored = cursor.fetchone()

        first = table_digest(connection, "games", GAME_STATE)

    assert stored is not None, "the requested appid was never marked"
    assert stored[0] == expected_outcome

    # The counters are asserted by value, not only compared to themselves.
    # Comparing a counter across two runs proves nothing while it sits at zero:
    # a review found that `attempts_increment = 0` — an answer never counting as
    # an attempt — survived the whole suite, and the transport_error backoff
    # reads exactly that counter.
    assert stored[1] == expected_attempts, "the attempt counter did not move as stated"
    assert stored[2] == 0, "an answer clears the consecutive-failure counter"

    load_data("steam_store", fixture_path(fixture), snapshot_date="2026-08-12")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT steam_store_attempts FROM games WHERE appid = %s", (appid,)
            )
            attempts_after_replay = cursor.fetchone()[0]

        second = table_digest(connection, "games", GAME_STATE)

    assert attempts_after_replay == expected_attempts, (
        "replaying a stored response spent an attempt"
    )
    assert first == second, "replaying a stored response changed the row"


def test_redirect_marks_the_requested_appid_not_only_the_target(
    test_database, fixture_path
):
    """
    Asking for 100 and receiving 80 must mark 100 as `redirected` with the target
    recorded. Writing only the target is what left 26 appids at the head of the
    backlog, re-fetched every run and reported as processed.
    """

    from src.db import get_db_connection
    from src.load import load_data

    seed_game(100)
    load_data(
        "steam_store",
        fixture_path("steam_store_redirected.json"),
        snapshot_date="2026-08-12",
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT steam_store_outcome, steam_store_redirect_to FROM games "
                "WHERE appid = 100"
            )
            row = cursor.fetchone()

    assert row == ("redirected", 80)
