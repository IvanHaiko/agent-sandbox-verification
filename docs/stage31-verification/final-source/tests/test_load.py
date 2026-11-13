import json
from datetime import datetime

import pytest

from src import load


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def execute(self, query, params):
        self.connection.executed_queries.append((query, params))

    def fetchall(self):
        return self.connection.rows


class FakeConnection:
    def __init__(self, rows=None):
        self.executed_queries = []
        self.committed = False
        self.rows = rows if rows is not None else []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True


def test_load_twitch_file_inserts_snapshots(monkeypatch, tmp_path):
    """
    Test that Twitch raw streams are transformed and inserted into PostgreSQL.
    """

    raw_data = {
        "fetched_at": "2026-05-13T12:28:52.040293+00:00",
        "data": [
            {
                "game_id": "32399",
                "game_name": "Counter-Strike",
                "viewer_count": 100,
            },
            {
                "game_id": "32399",
                "game_name": "Counter-Strike",
                "viewer_count": 50,
            },
            {
                "game_id": "21779",
                "game_name": "League of Legends",
                "viewer_count": 200,
            },
        ]
    }

    file_path = tmp_path / "streams.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(raw_data, file)

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    result = load.load_twitch_file(file_path)

    assert result == 2
    assert fake_connection.committed is True
    assert len(fake_connection.executed_queries) == 2

    inserted_params = [
        params
        for query, params in fake_connection.executed_queries
    ]

    sample_time = datetime(2026, 5, 13, 12, 28, 52, 40293)
    sample_hour = datetime(2026, 5, 13, 12, 0, 0)

    assert (
        "32399", "Counter-Strike", 150, 2, sample_time, sample_hour
    ) in inserted_params
    assert (
        "21779", "League of Legends", 200, 1, sample_time, sample_hour
    ) in inserted_params


def test_load_twitch_file_uses_on_conflict_do_update_on_sample_hour(monkeypatch, tmp_path):
    """
    Test that the Twitch snapshot INSERT upserts on (sample_hour,
    twitch_game_id) so repeated loads of the same file update the existing
    row in place instead of erroring or creating a duplicate.
    """

    raw_data = {
        "fetched_at": "2026-05-13T12:28:52.040293+00:00",
        "data": [
            {
                "game_id": "32399",
                "game_name": "Counter-Strike",
                "viewer_count": 100,
            },
        ]
    }

    file_path = tmp_path / "streams.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(raw_data, file)

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    load.load_twitch_file(file_path)
    load.load_twitch_file(file_path)

    insert_queries = [
        query
        for query, _params in fake_connection.executed_queries
    ]

    assert all(
        "ON CONFLICT (sample_hour, twitch_game_id) DO UPDATE" in q
        for q in insert_queries
    )
    assert len(insert_queries) == 2


def test_load_twitch_file_always_writes_bronze_sample_time_source(monkeypatch, tmp_path):
    """
    Test that every row inserted by the loader is marked sample_time_source
    = 'bronze', since sample_time here always comes from the raw JSON's
    fetched_at (migration 010). 'load_clock' only ever describes historical
    rows backfilled before that migration existed and is never written by
    the loader itself.
    """

    raw_data = {
        "fetched_at": "2026-05-13T12:28:52.040293+00:00",
        "data": [
            {
                "game_id": "32399",
                "game_name": "Counter-Strike",
                "viewer_count": 100,
            },
        ]
    }

    file_path = tmp_path / "streams.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(raw_data, file)

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    load.load_twitch_file(file_path)

    executed_query, _params = fake_connection.executed_queries[0]

    assert "sample_time_source" in executed_query
    assert "'bronze'" in executed_query


def test_load_steam_store_file_loads_game_on_ok_outcome(monkeypatch, tmp_path):
    """
    An envelope with outcome "ok" is loaded into the games table, same as
    a plain steam_store response always was, and the returned outcome is
    "ok".
    """

    envelope = {
        "envelope": 1,
        "source": "steam_store",
        "outcome": "ok",
        "appid": 730,
        "request": {"appids": 730},
        "url": "https://store.steampowered.com/api/appdetails?appids=730",
        "fetched_at": "2026-08-12T10:00:00+00:00",
        "http_status": 200,
        "error": None,
        "redirect_to": None,
        "body": {
            "730": {
                "success": True,
                "data": {
                    "steam_appid": 730,
                    "name": "Counter-Strike 2",
                    "developers": ["Valve"],
                    "publishers": ["Valve"],
                    "is_free": True,
                    "release_date": {"coming_soon": False, "date": "21 Aug, 2012"},
                    "header_image": "https://example.com/header.jpg",
                    "genres": [],
                },
            }
        },
    }

    file_path = tmp_path / "730_20260812_100000.json"
    file_path.write_text(json.dumps(envelope), encoding="utf-8")

    fake_connection = FakeConnection()

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    def fail_if_called(
        appid, outcome, error_message=None, redirect_to=None, fetched_at=None
    ):
        raise AssertionError(
            "mark_steam_store_enrichment_result should not run for outcome=ok"
        )

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fail_if_called)

    result = load.load_steam_store_file(file_path, "2026-08-12")

    assert result == "ok"

    game_insert_queries = [
        (q, p) for q, p in fake_connection.executed_queries if "INSERT INTO games" in q
    ]
    assert len(game_insert_queries) == 1

    _query, params = game_insert_queries[0]
    assert params == (
        730,
        "Counter-Strike 2",
        "Valve",
        "Valve",
        True,
        "21 Aug, 2012",
        "https://example.com/header.jpg",
        "2026-08-12T10:00:00+00:00",
    )


def test_load_steam_store_file_records_refused_without_loading_game(
    monkeypatch, tmp_path
):
    """
    outcome "refused" (success: false) must not reach the games table's
    metadata columns -- only steam_store_outcome / steam_store_last_error
    via mark_steam_store_enrichment_result.
    """

    envelope = {
        "envelope": 1,
        "source": "steam_store",
        "outcome": "refused",
        "appid": 999999,
        "request": {"appids": 999999},
        "url": "https://store.steampowered.com/api/appdetails?appids=999999",
        "fetched_at": "2026-08-12T10:00:00+00:00",
        "http_status": 200,
        "error": None,
        "redirect_to": None,
        "body": {"999999": {"success": False}},
    }

    file_path = tmp_path / "999999_20260812_100000.json"
    file_path.write_text(json.dumps(envelope), encoding="utf-8")

    def fake_get_db_connection():
        raise AssertionError(
            "no games-table connection should be opened for outcome=refused"
        )

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    marked = []

    def fake_mark(
        appid,
        outcome,
        error_message=None,
        redirect_to=None,
        fetched_at=None,
        is_replay=False,
    ):
        marked.append((appid, outcome, error_message))

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fake_mark)

    result = load.load_steam_store_file(file_path, "2026-08-12")

    assert result == "refused"
    assert marked == [(999999, "refused", "Steam Store returned success=false")]


def test_load_steam_store_file_records_not_found_distinctly_from_refused(
    monkeypatch, tmp_path
):
    """
    outcome "not_found" and outcome "refused" must record different
    messages -- collapsing them into one string was the original defect.
    """

    envelope = {
        "envelope": 1,
        "source": "steam_store",
        "outcome": "not_found",
        "appid": 123456,
        "request": {"appids": 123456},
        "url": "https://store.steampowered.com/api/appdetails?appids=123456",
        "fetched_at": "2026-08-12T10:00:00+00:00",
        "http_status": 200,
        "error": None,
        "redirect_to": None,
        "body": {},
    }

    file_path = tmp_path / "123456_20260812_100000.json"
    file_path.write_text(json.dumps(envelope), encoding="utf-8")

    marked = []

    def fake_mark(
        appid,
        outcome,
        error_message=None,
        redirect_to=None,
        fetched_at=None,
        is_replay=False,
    ):
        marked.append((appid, outcome, error_message))

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fake_mark)

    result = load.load_steam_store_file(file_path, "2026-08-12")

    assert result == "not_found"
    assert marked == [(123456, "not_found", "No Steam Store response wrapper found")]
    assert marked[0][2] != "Steam Store returned success=false"


def test_load_steam_store_file_records_transport_error_message(monkeypatch, tmp_path):
    """
    outcome "transport_error" carries its own captured error text and it
    must be what gets recorded, not a generic message.
    """

    envelope = {
        "envelope": 1,
        "source": "steam_store",
        "outcome": "transport_error",
        "appid": 730,
        "request": {"appids": 730},
        "url": None,
        "fetched_at": "2026-08-12T10:00:00+00:00",
        "http_status": None,
        "error": "Connection timed out",
        "redirect_to": None,
        "body": None,
    }

    file_path = tmp_path / "730_20260812_100000.json"
    file_path.write_text(json.dumps(envelope), encoding="utf-8")

    marked = []

    def fake_mark(
        appid,
        outcome,
        error_message=None,
        redirect_to=None,
        fetched_at=None,
        is_replay=False,
    ):
        marked.append((appid, outcome, error_message))

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fake_mark)

    result = load.load_steam_store_file(file_path, "2026-08-12")

    assert result == "transport_error"
    assert marked == [(730, "transport_error", "Connection timed out")]


def test_load_steam_store_file_records_redirected_and_loads_target_metadata(
    monkeypatch, tmp_path
):
    """
    outcome "redirected": the requested appid (100) never receives game
    metadata -- only a terminal mark with the typed redirect target. The
    body describes a different appid (80), and that appid's own games row
    gets loaded exactly like an "ok" response for appid 80 would.
    """

    envelope = {
        "envelope": 1,
        "source": "steam_store",
        "outcome": "redirected",
        "appid": 100,
        "request": {"appids": 100},
        "url": "https://store.steampowered.com/api/appdetails?appids=100",
        "fetched_at": "2026-08-12T10:00:00+00:00",
        "http_status": 200,
        "error": None,
        "redirect_to": 80,
        "body": {
            "100": {
                "success": True,
                "data": {
                    "steam_appid": 80,
                    "name": "Counter-Strike: Condition Zero",
                    "developers": ["Valve"],
                    "publishers": ["Valve"],
                    "is_free": False,
                    "release_date": {"coming_soon": False, "date": "1 Mar, 2004"},
                    "header_image": "https://example.com/80.jpg",
                    "genres": [],
                },
            }
        },
    }

    file_path = tmp_path / "100_20260812_100000.json"
    file_path.write_text(json.dumps(envelope), encoding="utf-8")

    fake_connection = FakeConnection()

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    marked = []

    def fake_mark(
        appid,
        outcome,
        error_message=None,
        redirect_to=None,
        fetched_at=None,
        is_replay=False,
    ):
        marked.append((appid, outcome, error_message, redirect_to))

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fake_mark)

    result = load.load_steam_store_file(file_path, "2026-08-12")

    assert result == "redirected"

    # The requested appid (100) is marked terminal with its target, never
    # loaded as a game itself.
    assert marked == [(100, "redirected", "Steam Store redirected appid 100 to 80", 80)]

    game_insert_queries = [
        (q, p) for q, p in fake_connection.executed_queries if "INSERT INTO games" in q
    ]
    assert len(game_insert_queries) == 1

    _query, params = game_insert_queries[0]
    assert params[0] == 80
    assert params[1] == "Counter-Strike: Condition Zero"


def test_load_steam_store_file_loads_legacy_file_without_envelope(
    monkeypatch, tmp_path
):
    """
    A legacy bronze file (no "envelope" key, exactly the shape the
    ~3 148 pre-fix files on disk have) must still load into games,
    unchanged, via parse_steam_store_envelope's outcome="ok" fallback.
    """

    legacy_body = {
        "730": {
            "success": True,
            "data": {
                "steam_appid": 730,
                "name": "Counter-Strike 2",
                "developers": ["Valve"],
                "publishers": ["Valve"],
                "is_free": True,
                "release_date": {"coming_soon": False, "date": "21 Aug, 2012"},
                "header_image": "https://example.com/header.jpg",
                "genres": [],
            },
        }
    }

    file_path = tmp_path / "730_legacy.json"
    file_path.write_text(json.dumps(legacy_body), encoding="utf-8")

    fake_connection = FakeConnection()

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    def fail_if_called(
        appid, outcome, error_message=None, redirect_to=None, fetched_at=None
    ):
        raise AssertionError("legacy files are always outcome=ok, mark should not run")

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fail_if_called)

    result = load.load_steam_store_file(file_path, "2026-08-12")

    assert result == "ok"

    game_insert_queries = [
        (q, p) for q, p in fake_connection.executed_queries if "INSERT INTO games" in q
    ]
    assert len(game_insert_queries) == 1
    assert game_insert_queries[0][1][0] == 730


def test_load_steam_store_file_raises_loudly_for_legacy_file_that_was_refused(
    monkeypatch, tmp_path
):
    """
    A legacy file (no "envelope" key) is unconditionally read as outcome
    "ok" by parse_steam_store_envelope -- there is no legacy "refused"
    shape. If the embedded body actually says success: false, transform
    correctly returns None, but the envelope carries no appid (legacy
    files never do) to mark a result against. This used to be a silent
    no-op: no exception, no log, no database write. It must now be loud.
    """

    legacy_body = {"999999": {"success": False}}

    file_path = tmp_path / "999999_legacy.json"
    file_path.write_text(json.dumps(legacy_body), encoding="utf-8")

    def fake_get_db_connection():
        raise AssertionError("no connection should be opened before raising")

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    with pytest.raises(ValueError, match="outcome 'ok'"):
        load.load_steam_store_file(file_path, "2026-08-12")


def test_mark_steam_store_enrichment_result_increments_attempts_not_errors(
    monkeypatch,
):
    """
    Every non-transport outcome (refused / not_found / redirected)
    increments steam_store_attempts and leaves steam_store_errors alone
    -- Steam answered, even if the answer was a refusal.
    """

    fake_connection = FakeConnection()

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    load.mark_steam_store_enrichment_result(
        appid=999999,
        outcome="refused",
        error_message="Steam Store returned success=false",
        fetched_at="2026-08-12T10:00:00+00:00",
    )

    query, params = fake_connection.executed_queries[0]

    assert "steam_store_fetched_at IS NOT DISTINCT FROM %s" in query
    assert "COALESCE(steam_store_attempts, 0) + %s" in query
    # An answer of any kind clears the consecutive-failure counter, so the
    # errors column is assigned a literal zero rather than incremented.
    assert "steam_store_errors = 0" in query
    assert params == (
        "refused",
        None,
        False,
        "2026-08-12T10:00:00+00:00",
        1,
        "Steam Store returned success=false",
        "2026-08-12T10:00:00+00:00",
        999999,
    )


def test_mark_steam_store_enrichment_result_increments_errors_not_attempts(
    monkeypatch,
):
    """
    transport_error is the one outcome where Steam did not answer at all
    -- it must bump steam_store_errors, not steam_store_attempts, so a
    run of network failures never spends the three chances meant for a
    real refusal or not_found answer.
    """

    fake_connection = FakeConnection()

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    load.mark_steam_store_enrichment_result(
        appid=730,
        outcome="transport_error",
        error_message="Connection timed out",
    )

    _query, params = fake_connection.executed_queries[0]

    assert params == (
        "transport_error",
        None,
        False,
        None,
        0,
        False,
        None,
        1,
        "Connection timed out",
        None,
        730,
    )


def test_mark_steam_store_enrichment_result_does_not_increment_on_replay(
    monkeypatch,
):
    """
    Replaying the exact same envelope (identical fetched_at) must not
    increment either counter -- the whole point of keying the CASE
    expression on fetched_at rather than always adding 1. This is what
    keeps a re-run of the same bronze file (rule 2: a failed load re-runs
    without re-hitting the API) from looking like a second real attempt.
    """

    fake_connection = FakeConnection()

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    load.mark_steam_store_enrichment_result(
        appid=730,
        outcome="transport_error",
        error_message="Connection timed out",
        fetched_at="2026-08-12T10:00:00+00:00",
    )
    load.mark_steam_store_enrichment_result(
        appid=730,
        outcome="transport_error",
        error_message="Connection timed out",
        fetched_at="2026-08-12T10:00:00+00:00",
    )

    assert len(fake_connection.executed_queries) == 2
    # Both calls issue the identical CASE-guarded UPDATE; a fake cursor
    # cannot evaluate the CASE itself (that is Postgres's job, exercised
    # against the live database in this session's manual verification),
    # but it can confirm both calls pass the same fetched_at into the
    # comparison, which is what makes the guard fire identically both
    # times.
    _query1, params1 = fake_connection.executed_queries[0]
    _query2, params2 = fake_connection.executed_queries[1]
    assert params1 == params2


def test_mark_steam_store_enrichment_result_rejects_ok_and_failed_legacy():
    """
    "ok" is recorded by insert_game, and "failed_legacy" is only ever
    written by migration 014's one-time backfill -- this function must
    refuse both rather than silently accepting a value it should never
    receive from the loader.
    """

    with pytest.raises(ValueError, match="ok"):
        load.mark_steam_store_enrichment_result(appid=730, outcome="ok")

    with pytest.raises(ValueError, match="failed_legacy"):
        load.mark_steam_store_enrichment_result(appid=730, outcome="failed_legacy")


def test_get_games_for_store_enrichment_query_covers_every_outcome_branch(
    monkeypatch,
):
    """
    The backlog query must branch by steam_store_outcome, not apply one
    cooldown to everything -- this locks in the shape rather than the
    live data, since the fake connection returns no rows either way.
    """

    fake_connection = FakeConnection(rows=[(100,), (200,)])

    monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

    result = load.get_games_for_store_enrichment(limit=50, refresh_after_days=30)

    assert result == [100, 200]

    query, params = fake_connection.executed_queries[0]

    assert params == (30, 50)

    # never asked
    assert "steam_store_outcome IS NULL" in query
    # ok: refresh_after_days, unchanged
    assert "steam_store_outcome = 'ok'" in query
    # refused and failed_legacy share the 30-day cooldown, no ceiling
    assert "steam_store_outcome IN ('refused', 'failed_legacy')" in query
    assert "INTERVAL '30 days'" in query
    # not_found: 90 days, no ceiling
    assert "steam_store_outcome = 'not_found'" in query
    assert "INTERVAL '90 days'" in query
    # transport_error: escalating pause driven by consecutive failures,
    # capped at 30 days, and no ceiling at all -- our own fault must never
    # remove a game when a refusal by Steam does not.
    assert "steam_store_outcome = 'transport_error'" in query
    assert "steam_store_errors < 3" not in query
    assert "LEAST(" in query
    assert "POWER(2, GREATEST(COALESCE(steam_store_errors, 1), 1) - 1)" in query
    # redirected is terminal -- it must not appear in any WHERE branch
    assert "redirected" not in query


def test_load_data_supports_twitch(monkeypatch, tmp_path):
    """
    Test that load_data dispatches Twitch files to the Twitch loader.
    """

    file_path = tmp_path / "streams.json"
    file_path.write_text("{}", encoding="utf-8")

    calls = []

    def fake_load_twitch_file(file_path_arg):
        calls.append(file_path_arg)
        return 3

    monkeypatch.setattr(load, "load_twitch_file", fake_load_twitch_file)

    result = load.load_data(
        source="twitch",
        file_path=file_path,
    )

    assert result == 3
    assert calls == [file_path]


def test_load_twitch_games_lookup_file_upserts_catalog(monkeypatch, tmp_path):
    """
    Test that Twitch games lookup raw data is loaded into the catalog.
    """

    raw_data = {
        "data": [
            {
                "id": "32399",
                "name": "Counter-Strike",
                "box_art_url": "https://example.com/box.jpg",
                "igdb_id": "115",
            }
        ]
    }

    file_path = tmp_path / "games_lookup.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(raw_data, file)

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    result = load.load_twitch_games_lookup_file(file_path)

    assert result == 1
    assert fake_connection.committed is True
    assert fake_connection.executed_queries[0][1] == (
        "32399",
        "Counter-Strike",
        "https://example.com/box.jpg",
        115,
        "games_lookup",
    )


def test_load_data_supports_twitch_games_lookup(monkeypatch, tmp_path):
    """
    Test that load_data dispatches Twitch games lookup files to the catalog loader.
    """

    file_path = tmp_path / "games_lookup.json"
    file_path.write_text("{}", encoding="utf-8")

    calls = []

    def fake_load_twitch_games_lookup_file(file_path_arg):
        calls.append(file_path_arg)
        return 1

    monkeypatch.setattr(
        load,
        "load_twitch_games_lookup_file",
        fake_load_twitch_games_lookup_file,
    )

    result = load.load_data(
        source="twitch_games_lookup",
        file_path=file_path,
    )

    assert result == 1
    assert calls == [file_path]


def test_load_igdb_file_upserts_games_links_and_twitch_categories(monkeypatch, tmp_path):
    """
    Test that IGDB raw search data is transformed and loaded into PostgreSQL.
    """

    raw_data = {
        "data": [
            {
                "id": 123,
                "name": "Counter-Strike 2",
                "slug": "counter-strike-2",
                "summary": "Tactical shooter.",
                "url": "https://www.igdb.com/games/counter-strike-2",
                "first_release_date": 0,
                "external_games": [
                    {
                        "uid": "32399",
                        "url": "https://www.twitch.tv/directory/category/counter-strike",
                    },
                ],
                "websites": [
                    {
                        "url": "https://store.steampowered.com/app/730/CounterStrike",
                    },
                ],
            }
        ]
    }

    file_path = tmp_path / "igdb_games.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(raw_data, file)

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(load, "get_db_connection", fake_get_db_connection)

    result = load.load_igdb_file(file_path)

    assert result == 1
    assert fake_connection.committed is True
    assert len(fake_connection.executed_queries) == 3

    game_params = fake_connection.executed_queries[0][1]
    store_link_params = fake_connection.executed_queries[1][1]
    twitch_category_params = fake_connection.executed_queries[2][1]

    assert game_params[0] == 123
    assert game_params[1] == "Counter-Strike 2"
    assert json.loads(game_params[18]) == raw_data["data"][0]

    assert store_link_params == (
        123,
        "steam",
        "730",
        "https://store.steampowered.com/app/730/CounterStrike",
    )

    assert twitch_category_params == (
        "32399",
        "Counter-Strike 2",
        True,
        123,
        "mapped",
        "igdb_external_game",
        1.0,
        "Mapped from IGDB external_games Twitch UID.",
    )


def test_load_data_supports_igdb(monkeypatch, tmp_path):
    """
    Test that load_data dispatches IGDB files to the IGDB loader.
    """

    file_path = tmp_path / "igdb_games.json"
    file_path.write_text("{}", encoding="utf-8")

    calls = []

    def fake_load_igdb_file(file_path_arg):
        calls.append(file_path_arg)
        return 1

    monkeypatch.setattr(load, "load_igdb_file", fake_load_igdb_file)

    result = load.load_data(
        source="igdb",
        file_path=file_path,
    )

    assert result == 1
    assert calls == [file_path]


def test_mark_steam_store_enrichment_result_resets_errors_on_any_answer(
    monkeypatch,
):
    """
    steam_store_errors counts *consecutive* failures on our side, so any
    answer at all clears it.

    A lifetime counter would mean three unrelated outages across years
    permanently removed a game from the catalogue -- a harsher consequence
    for a fault of ours than for a refusal by Steam, which carries no
    ceiling at all. The reset is written as a literal zero rather than an
    increment, so it is also idempotent under a replay.
    """

    for outcome in ("refused", "not_found", "redirected"):
        fake_connection = FakeConnection()
        monkeypatch.setattr(load, "get_db_connection", lambda: fake_connection)

        load.mark_steam_store_enrichment_result(
            appid=999999,
            outcome=outcome,
            error_message="whatever Steam said",
            redirect_to=80 if outcome == "redirected" else None,
            fetched_at="2026-08-12T10:00:00+00:00",
        )

        query, _params = fake_connection.executed_queries[0]

        assert "steam_store_errors = 0" in query, outcome
        assert "COALESCE(steam_store_errors, 0) + %s" not in query, outcome
