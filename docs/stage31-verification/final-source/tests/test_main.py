import argparse
import ast
import re
import sys
from pathlib import Path

import pytest

from src import main


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def execute(self, query, params=None):
        self.connection.executed_queries.append((query, params))

    def fetchall(self):
        return self.connection.rows

    def fetchone(self):
        return self.connection.row


class FakeConnection:
    def __init__(self, rows=None, row=None):
        self.rows = rows or []
        self.row = row
        self.executed_queries = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True


def test_run_steamspy_all_page(monkeypatch, tmp_path):
    """
    Test that one SteamSpy all page is fetched, saved, and loaded.
    """

    fake_data = {
        "730": {
            "appid": 730,
            "name": "Counter-Strike 2",
            "positive": 100,
            "negative": 10,
        }
    }

    fake_file_path = tmp_path / "steamspy_all_page_0.json"

    calls = {
        "fetch": False,
        "save": False,
        "load": False,
    }

    def fake_fetch_steamspy_data(request_type, page):
        calls["fetch"] = True
        assert request_type == "all"
        assert page == 0
        return fake_data

    def fake_save_steamspy_raw_json(data, request_type, page):
        calls["save"] = True
        assert data == fake_data
        assert request_type == "all"
        assert page == 0
        return fake_file_path

    def fake_load_data(source, file_path, snapshot_date=None):
        calls["load"] = True
        assert source == "steamspy"
        assert file_path == fake_file_path
        assert snapshot_date == "2026-05-09"

    monkeypatch.setattr(main, "fetch_steamspy_data", fake_fetch_steamspy_data)
    monkeypatch.setattr(main, "save_steamspy_raw_json", fake_save_steamspy_raw_json)
    monkeypatch.setattr(main, "load_data", fake_load_data)

    result = main.run_steamspy_all_page(
        page=0,
        snapshot_date="2026-05-09",
    )

    assert result == fake_file_path
    assert calls == {
        "fetch": True,
        "save": True,
        "load": True,
    }


def test_run_steamspy_all_page_raises_error_for_empty_page(monkeypatch):
    """
    Test that run_steamspy_all_page raises an error if SteamSpy returns no records.
    """

    def fake_fetch_steamspy_data(request_type, page):
        return {}

    monkeypatch.setattr(main, "fetch_steamspy_data", fake_fetch_steamspy_data)

    with pytest.raises(ValueError, match="SteamSpy returned 0 records"):
        main.run_steamspy_all_page(page=0)


def test_run_steamspy_daily_stops_at_max_pages(monkeypatch, tmp_path):
    """
    Test that SteamSpy daily pipeline stops after max_pages.
    """

    fake_data = {
        str(appid): {
            "appid": appid,
            "name": f"Game {appid}",
        }
        for appid in range(1000)
    }

    fetched_pages = []
    loaded_files = []

    def fake_fetch_steamspy_data(request_type, page):
        assert request_type == "all"
        fetched_pages.append(page)
        return fake_data

    def fake_save_steamspy_raw_json(data, request_type, page):
        assert data == fake_data
        assert request_type == "all"
        return tmp_path / f"steamspy_all_page_{page}.json"

    def fake_load_data(source, file_path, snapshot_date=None):
        assert source == "steamspy"
        loaded_files.append(file_path)

    def fake_sleep(seconds):
        # Do nothing in tests.
        return None

    monkeypatch.setattr(main, "fetch_steamspy_data", fake_fetch_steamspy_data)
    monkeypatch.setattr(main, "save_steamspy_raw_json", fake_save_steamspy_raw_json)
    monkeypatch.setattr(main, "load_data", fake_load_data)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_steamspy_daily(
        start_page=0,
        max_pages=2,
        delay_seconds=5,
        snapshot_date="2026-05-09",
    )

    assert fetched_pages == [0, 1]
    assert loaded_files == [
        tmp_path / "steamspy_all_page_0.json",
        tmp_path / "steamspy_all_page_1.json",
    ]


def test_run_steamspy_daily_stops_on_last_page(monkeypatch, tmp_path):
    """
    Test that SteamSpy daily pipeline stops when a page has fewer than 1000 records.
    """

    first_page_data = {
        str(appid): {
            "appid": appid,
            "name": f"Game {appid}",
        }
        for appid in range(1000)
    }

    last_page_data = {
        str(appid): {
            "appid": appid,
            "name": f"Game {appid}",
        }
        for appid in range(100)
    }

    pages = {
        0: first_page_data,
        1: last_page_data,
    }

    fetched_pages = []

    def fake_fetch_steamspy_data(request_type, page):
        fetched_pages.append(page)
        return pages[page]

    def fake_save_steamspy_raw_json(data, request_type, page):
        return tmp_path / f"steamspy_all_page_{page}.json"

    def fake_load_data(source, file_path, snapshot_date=None):
        return None

    def fake_sleep(seconds):
        return None

    monkeypatch.setattr(main, "fetch_steamspy_data", fake_fetch_steamspy_data)
    monkeypatch.setattr(main, "save_steamspy_raw_json", fake_save_steamspy_raw_json)
    monkeypatch.setattr(main, "load_data", fake_load_data)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_steamspy_daily(
        start_page=0,
        delay_seconds=5,
    )

    assert fetched_pages == [0, 1]


def test_run_steam_store_appdetails(monkeypatch, tmp_path):
    """
    Test that one Steam Store appdetails response is fetched, saved, and
    loaded, and that the outcome load_data reports comes back to the
    caller alongside the saved file path.
    """

    fake_data = {
        "730": {
            "success": True,
            "data": {
                "steam_appid": 730,
                "name": "Counter-Strike 2",
            },
        }
    }

    fake_file_path = tmp_path / "steam_store_appdetails_730.json"

    calls = {
        "fetch": False,
        "save": False,
        "load": False,
    }

    def fake_fetch_appdetails(appid):
        calls["fetch"] = True
        assert appid == 730
        return fake_data

    def fake_save_steam_store_raw_json(data, appid):
        calls["save"] = True
        assert data == fake_data
        assert appid == 730
        return fake_file_path

    def fake_load_data(source, file_path, snapshot_date=None):
        calls["load"] = True
        assert source == "steam_store"
        assert file_path == fake_file_path
        return "ok"

    monkeypatch.setattr(main, "fetch_appdetails", fake_fetch_appdetails)
    monkeypatch.setattr(main, "save_steam_store_raw_json", fake_save_steam_store_raw_json)
    monkeypatch.setattr(main, "load_data", fake_load_data)

    result = main.run_steam_store_appdetails(appid=730)

    assert result == (fake_file_path, "ok")
    assert calls == {
        "fetch": True,
        "save": True,
        "load": True,
    }


def test_run_steam_store_appdetails_saves_and_loads_bronze_for_every_outcome(
    monkeypatch,
):
    """
    run_steam_store_appdetails no longer inspects the response itself to
    decide whether to save/load -- fetch_appdetails always returns an
    envelope, and it is always saved and handed to load_data, which is
    the one place (src/load.py) that now decides ok vs. refused/not_found/
    redirected/transport_error. This test locks in that main.py stays a
    thin fetch -> save -> load pipeline regardless of the envelope's
    outcome, and that the outcome load_data returns is passed through.
    """

    fake_envelope = {
        "envelope": 1,
        "outcome": "refused",
        "appid": 999999,
        "body": {"999999": {"success": False}},
    }

    calls = {"fetch": False, "save": False, "load": False}

    def fake_fetch_appdetails(appid):
        calls["fetch"] = True
        assert appid == 999999
        return fake_envelope

    def fake_save_steam_store_raw_json(data, appid):
        calls["save"] = True
        assert data == fake_envelope
        assert appid == 999999
        return "fake_path"

    def fake_load_data(source, file_path, snapshot_date=None):
        calls["load"] = True
        assert source == "steam_store"
        assert file_path == "fake_path"
        return "refused"

    monkeypatch.setattr(main, "fetch_appdetails", fake_fetch_appdetails)
    monkeypatch.setattr(
        main, "save_steam_store_raw_json", fake_save_steam_store_raw_json
    )
    monkeypatch.setattr(main, "load_data", fake_load_data)

    result = main.run_steam_store_appdetails(appid=999999)

    assert result == ("fake_path", "refused")
    assert calls == {"fetch": True, "save": True, "load": True}


def test_run_steam_store_enrich(monkeypatch, tmp_path):
    """
    Test that Steam Store enrichment processes appids from the database.
    """

    appids = [730, 570]

    processed_appids = []

    def fake_get_games_for_store_enrichment(limit, refresh_after_days=30):
        assert limit == 2
        return appids

    def fake_run_steam_store_appdetails(appid):
        processed_appids.append(appid)
        return tmp_path / f"steam_store_appdetails_{appid}.json", "ok"

    def fake_sleep(seconds):
        return None

    monkeypatch.setattr(
        main,
        "get_games_for_store_enrichment",
        fake_get_games_for_store_enrichment,
    )
    monkeypatch.setattr(
        main,
        "run_steam_store_appdetails",
        fake_run_steam_store_appdetails,
    )
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_steam_store_enrich(
        limit=2,
        delay_seconds=1,
    )

    assert processed_appids == [730, 570]


def test_run_steam_store_enrich_tallies_every_outcome_separately(
    monkeypatch, tmp_path, capsys
):
    """
    A run where Steam refuses or fails to answer must not read as fully
    "processed" -- each of the five outcomes is tallied on its own, and
    "Processed (ok)" only ever counts "ok".
    """

    appids = [1, 2, 3, 4, 5]
    outcomes_by_appid = {
        1: "ok",
        2: "refused",
        3: "not_found",
        4: "redirected",
        5: "transport_error",
    }

    def fake_get_games_for_store_enrichment(limit, refresh_after_days=30):
        return appids

    def fake_run_steam_store_appdetails(appid):
        outcome = outcomes_by_appid[appid]
        return tmp_path / f"steam_store_appdetails_{appid}.json", outcome

    def fake_sleep(seconds):
        return None

    monkeypatch.setattr(
        main,
        "get_games_for_store_enrichment",
        fake_get_games_for_store_enrichment,
    )
    monkeypatch.setattr(
        main,
        "run_steam_store_appdetails",
        fake_run_steam_store_appdetails,
    )
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_steam_store_enrich(
        limit=5,
        delay_seconds=1,
    )

    # The summary is the only thing an operator sees, so it is what the
    # test has to read. Asserting merely that the run did not raise would
    # have passed even while a total Steam outage reported "Failed: 0",
    # which is the defect this tally exists to make impossible.
    summary = capsys.readouterr().out

    assert "ok: 1" in summary
    assert "refused: 1" in summary
    assert "not_found: 1" in summary
    assert "redirected: 1" in summary
    assert "transport_error: 1" in summary
    # "Processed" must mean games actually enriched, not calls survived.
    assert "Processed (ok): 1" in summary


def test_run_steam_store_enrich_handles_failed_app(monkeypatch, tmp_path):
    """
    Test that Steam Store enrichment continues if one app fails, and that
    an unexpected exception (outside fetch_appdetails's own handling) is
    recorded as outcome "transport_error" -- there is no separate bucket
    for "something else entirely broke".
    """

    appids = [730, 999999, 570]

    processed_appids = []

    def fake_get_games_for_store_enrichment(limit, refresh_after_days=30):
        return appids

    def fake_run_steam_store_appdetails(appid):
        processed_appids.append(appid)

        if appid == 999999:
            raise RuntimeError("Fake API error")

        return tmp_path / f"steam_store_appdetails_{appid}.json", "ok"

    def fake_sleep(seconds):
        return None

    marked_results = []

    def fake_mark_steam_store_enrichment_result(
        appid,
        outcome,
        error_message=None,
        redirect_to=None,
        fetched_at=None,
        is_replay=False,
    ):
        marked_results.append((appid, outcome, error_message))

    monkeypatch.setattr(
        main,
        "get_games_for_store_enrichment",
        fake_get_games_for_store_enrichment,
    )
    monkeypatch.setattr(
        main,
        "run_steam_store_appdetails",
        fake_run_steam_store_appdetails,
    )
    monkeypatch.setattr(
        main,
        "mark_steam_store_enrichment_result",
        fake_mark_steam_store_enrichment_result,
    )
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_steam_store_enrich(
        limit=3,
        delay_seconds=1,
    )

    assert processed_appids == [730, 999999, 570]
    assert marked_results == [
        (999999, "transport_error", "Fake API error"),
    ]


def test_run_daily_pipeline(monkeypatch):
    """
    Test that full daily pipeline runs SteamSpy daily first
    and Steam Store enrichment second.
    """

    calls = []

    def fake_run_steamspy_daily(
        start_page,
        max_pages,
        delay_seconds,
        snapshot_date=None,
    ):
        calls.append("steamspy")
        assert start_page == 0
        assert max_pages == 2
        assert delay_seconds == 5
        assert snapshot_date == "2026-05-09"

    def fake_run_steam_store_enrich(
        limit,
        delay_seconds,
    ):
        calls.append("steam_store")
        assert limit == 10
        assert delay_seconds == 1

    monkeypatch.setattr(main, "run_steamspy_daily", fake_run_steamspy_daily)
    monkeypatch.setattr(main, "run_steam_store_enrich", fake_run_steam_store_enrich)

    main.run_daily_pipeline(
        steamspy_start_page=0,
        steamspy_max_pages=2,
        steamspy_delay_seconds=5,
        store_limit=10,
        store_delay_seconds=1,
        snapshot_date="2026-05-09",
    )

    assert calls == ["steamspy", "steam_store"]


def test_main_dispatches_daily(monkeypatch):
    """
    Test that the daily CLI command calls the full pipeline.
    """

    fake_args = argparse.Namespace(
        command="daily",
        steamspy_start_page=1,
        steamspy_max_pages=2,
        steamspy_delay=5,
        store_limit=20,
        store_delay=1,
        snapshot_date="2026-05-09",
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_daily_pipeline(
        steamspy_start_page,
        steamspy_max_pages,
        steamspy_delay_seconds,
        store_limit,
        store_delay_seconds,
        snapshot_date=None,
    ):
        calls.append(
            (
                steamspy_start_page,
                steamspy_max_pages,
                steamspy_delay_seconds,
                store_limit,
                store_delay_seconds,
                snapshot_date,
            )
        )

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_daily_pipeline", fake_run_daily_pipeline)

    main.main()

    assert calls == [
        (1, 2, 5, 20, 1, "2026-05-09"),
    ]


def test_get_unmapped_twitch_categories(monkeypatch):
    """
    Test that unmapped Twitch categories are read from PostgreSQL rows.
    """

    fake_connection = FakeConnection(
        rows=[
            ("32399", "Counter-Strike", None, 5000),
            ("21779", "League of Legends", None, 4000),
        ]
    )

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    result = main.get_unmapped_twitch_categories(limit=2)

    assert result == [
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
        },
        {
            "twitch_game_id": "21779",
            "twitch_game_name": "League of Legends",
        },
    ]
    # (max_attempts, retry_after_days, limit) with defaults 3 and 30.
    assert fake_connection.executed_queries[0][1] == (3, 30, 2)


def test_get_unmapped_twitch_categories_passes_custom_cooldown_and_max_attempts(
    monkeypatch,
):
    """
    Test that --retry-after-days and --max-attempts reach the SQL query.
    """

    fake_connection = FakeConnection(rows=[])

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    main.get_unmapped_twitch_categories(
        limit=10,
        retry_after_days=7,
        max_attempts=5,
    )

    assert fake_connection.executed_queries[0][1] == (5, 7, 10)


def test_run_igdb_search(monkeypatch, tmp_path):
    """
    Test that one IGDB search extracts raw data and loads it.
    """

    raw_path = tmp_path / "igdb.json"
    calls = []

    def fake_run_igdb_game_search(search_term, limit):
        calls.append(("search", search_term, limit))
        return raw_path

    def fake_load_data(source, file_path):
        calls.append(("load", source, file_path))

    monkeypatch.setattr(main, "run_igdb_game_search", fake_run_igdb_game_search)
    monkeypatch.setattr(main, "load_data", fake_load_data)

    result = main.run_igdb_search(
        search_term="Counter-Strike",
        limit=10,
    )

    assert result == raw_path
    assert calls == [
        ("search", "Counter-Strike", 10),
        ("load", "igdb", raw_path),
    ]


def test_get_steam_games_for_igdb_enrichment(monkeypatch):
    """
    Test that Steam games without IGDB Steam links are read from PostgreSQL rows.
    """

    fake_connection = FakeConnection(
        rows=[
            (730, "Counter-Strike 2"),
            (570, "Dota 2"),
        ]
    )

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    result = main.get_steam_games_for_igdb_enrichment(limit=2)

    assert result == [
        {
            "appid": 730,
            "name": "Counter-Strike 2",
        },
        {
            "appid": 570,
            "name": "Dota 2",
        },
    ]
    assert fake_connection.executed_queries[0][1] == (2,)


def test_normalize_game_name():
    """
    Test that names are normalized before fuzzy matching.
    """

    assert main.normalize_game_name("Counter-Strike: Global Offensive") == (
        "counter strike global offensive"
    )
    assert main.normalize_game_name("Dungeons & Dragons") == "dungeons and dragons"


def test_calculate_name_score():
    """
    Test that fuzzy name scores are returned from 0.0 to 1.0.
    """

    assert main.calculate_name_score("Counter-Strike", "Counter Strike") == 1.0
    assert main.calculate_name_score("", "Counter Strike") == 0.0
    assert main.calculate_name_score("Apex Legends", "Apex Legends Mobile") < 1.0


def test_get_observed_twitch_categories_for_candidates(monkeypatch):
    """
    Test that observed Twitch categories are read from PostgreSQL rows.
    """

    fake_connection = FakeConnection(
        rows=[
            ("32399", "Counter-Strike", 5000),
            ("21779", "League of Legends", 4000),
        ]
    )

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    result = main.get_observed_twitch_categories_for_candidates(limit=2)

    assert result == [
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
            "max_viewer_count": 5000,
        },
        {
            "twitch_game_id": "21779",
            "twitch_game_name": "League of Legends",
            "max_viewer_count": 4000,
        },
    ]
    assert fake_connection.executed_queries[0][1] == (2,)


def test_get_igdb_games_for_candidate_matching(monkeypatch):
    """
    Test that IGDB games are read from PostgreSQL rows.
    """

    fake_connection = FakeConnection(
        rows=[
            (123, "Counter-Strike 2", "counter-strike-2"),
            (456, "Dota 2", "dota-2"),
        ]
    )

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    result = main.get_igdb_games_for_candidate_matching()

    assert result == [
        {
            "igdb_game_id": 123,
            "name": "Counter-Strike 2",
            "slug": "counter-strike-2",
        },
        {
            "igdb_game_id": 456,
            "name": "Dota 2",
            "slug": "dota-2",
        },
    ]
    assert fake_connection.executed_queries[0][1] is None


def test_upsert_twitch_igdb_mapping_candidate(monkeypatch):
    """
    Test that one Twitch -> IGDB candidate is inserted or updated.
    """

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    main.upsert_twitch_igdb_mapping_candidate(
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
            "candidate_entity_type": "game",
            "igdb_game_id": 123,
            "name_score": 0.95,
            "final_score": 0.95,
            "candidate_method": "fuzzy_name",
            "reason": "Fuzzy name match.",
            "status": "pending",
        }
    )

    assert fake_connection.committed is True
    assert fake_connection.executed_queries[0][1] == (
        "32399",
        "Counter-Strike",
        "game",
        123,
        0.95,
        0.95,
        "fuzzy_name",
        "Fuzzy name match.",
        "pending",
    )


def test_upsert_twitch_igdb_mapping_candidate_never_overwrites_status(monkeypatch):
    """
    Test that the DO UPDATE clause does not reset status.

    A manual approve/reject must survive the weekly mapping DAG re-running
    this upsert with a freshly-derived (e.g. 'pending') status; only the
    INSERT branch is allowed to set status, so status is set once and left
    alone on every later conflict.
    """

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    main.upsert_twitch_igdb_mapping_candidate(
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
            "candidate_entity_type": "game",
            "igdb_game_id": 123,
            "name_score": 0.95,
            "final_score": 0.95,
            "candidate_method": "fuzzy_name",
            "reason": "Fuzzy name match.",
            "status": "pending",
        }
    )

    executed_query = fake_connection.executed_queries[0][0]
    do_update_clause = executed_query.split("DO UPDATE SET", 1)[1]

    assert "status" not in do_update_clause


def test_run_generate_twitch_igdb_candidates(monkeypatch):
    """
    Test that fuzzy matching stores top Twitch -> IGDB candidates.
    """

    inserted_candidates = []

    def fake_get_observed_twitch_categories_for_candidates(limit):
        assert limit == 2
        return [
            {
                "twitch_game_id": "32399",
                "twitch_game_name": "Counter-Strike",
                "max_viewer_count": 5000,
            },
        ]

    def fake_get_igdb_games_for_candidate_matching():
        return [
            {
                "igdb_game_id": 123,
                "name": "Counter Strike",
                "slug": "counter-strike",
            },
            {
                "igdb_game_id": 456,
                "name": "League of Legends",
                "slug": "league-of-legends",
            },
        ]

    def fake_upsert_twitch_igdb_mapping_candidate(candidate):
        inserted_candidates.append(candidate)

    monkeypatch.setattr(
        main,
        "get_observed_twitch_categories_for_candidates",
        fake_get_observed_twitch_categories_for_candidates,
    )
    monkeypatch.setattr(
        main,
        "get_igdb_games_for_candidate_matching",
        fake_get_igdb_games_for_candidate_matching,
    )
    monkeypatch.setattr(
        main,
        "upsert_twitch_igdb_mapping_candidate",
        fake_upsert_twitch_igdb_mapping_candidate,
    )

    main.run_generate_twitch_igdb_candidates(
        limit=2,
        min_score=0.75,
        top_n=1,
    )

    assert len(inserted_candidates) == 1
    assert inserted_candidates[0]["twitch_game_id"] == "32399"
    assert inserted_candidates[0]["igdb_game_id"] == 123
    assert inserted_candidates[0]["candidate_method"] == "fuzzy_name"
    assert inserted_candidates[0]["status"] == "pending"


def test_run_twitch_games_lookup_for_observed_batches_ids(monkeypatch, tmp_path):
    """
    Test that observed Twitch IDs are looked up and loaded in capped batches.
    """

    game_ids = ["1", "2", "3", "4", "5"]
    calls = []

    def fake_get_observed_twitch_game_ids_without_catalog(limit):
        assert limit == 5
        return game_ids

    def fake_run_twitch_games_lookup(batch_ids):
        calls.append(("lookup", batch_ids))
        return tmp_path / f"games_lookup_{len(calls)}.json"

    def fake_load_data(source, file_path):
        calls.append(("load", source, file_path))
        return 2

    monkeypatch.setattr(
        main,
        "get_observed_twitch_game_ids_without_catalog",
        fake_get_observed_twitch_game_ids_without_catalog,
    )
    monkeypatch.setattr(
        main,
        "run_twitch_games_lookup",
        fake_run_twitch_games_lookup,
    )
    monkeypatch.setattr(main, "load_data", fake_load_data)

    main.run_twitch_games_lookup_for_observed(
        limit=5,
        batch_size=2,
    )

    assert calls == [
        ("lookup", ["1", "2"]),
        ("load", "twitch_games_lookup", tmp_path / "games_lookup_1.json"),
        ("lookup", ["3", "4"]),
        ("load", "twitch_games_lookup", tmp_path / "games_lookup_3.json"),
        ("lookup", ["5"]),
        ("load", "twitch_games_lookup", tmp_path / "games_lookup_5.json"),
    ]


def test_generate_twitch_igdb_candidates_from_catalog(monkeypatch):
    """
    Test that Twitch Helix igdb_id rows become auto-approved candidates.
    """

    inserted_candidates = []

    def fake_get_twitch_catalog_igdb_candidate_rows(limit):
        assert limit == 1
        return [
            {
                "twitch_game_id": "32399",
                "twitch_game_name": "Counter-Strike",
                "igdb_id": 241,
                "igdb_name": "Counter-Strike",
            }
        ]

    def fake_upsert_twitch_igdb_mapping_candidate(candidate):
        inserted_candidates.append(candidate)

    monkeypatch.setattr(
        main,
        "get_twitch_catalog_igdb_candidate_rows",
        fake_get_twitch_catalog_igdb_candidate_rows,
    )
    monkeypatch.setattr(
        main,
        "upsert_twitch_igdb_mapping_candidate",
        fake_upsert_twitch_igdb_mapping_candidate,
    )

    main.generate_twitch_igdb_candidates_from_catalog(limit=1)

    assert inserted_candidates == [
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
            "candidate_entity_type": "game",
            "igdb_game_id": 241,
            "name_score": 1.0,
            "final_score": 1.0,
            "candidate_method": "twitch_helix_igdb_id",
            "reason": (
                "Twitch Helix Get Games returned igdb_id linking this "
                "Twitch category to IGDB."
            ),
            "status": "auto_approved",
        }
    ]


def test_has_igdb_steam_link(monkeypatch):
    """
    Test that Steam appid link checks read the EXISTS result.
    """

    fake_connection = FakeConnection(row=(True,))

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    result = main.has_igdb_steam_link(appid=730)

    assert result is True
    assert fake_connection.executed_queries[0][1] == ("730",)


def test_run_igdb_enrich_steam(monkeypatch, tmp_path):
    """
    Test that Steam IGDB enrichment searches, loads, and checks matches.
    """

    raw_path = tmp_path / "igdb.json"
    calls = []

    def fake_get_steam_games_for_igdb_enrichment(limit):
        assert limit == 2
        return [
            {
                "appid": 730,
                "name": "Counter-Strike 2",
            },
            {
                "appid": 570,
                "name": "Dota 2",
            },
        ]

    def fake_run_igdb_game_search(search_term, limit):
        calls.append(("search", search_term, limit))
        return raw_path

    def fake_load_data(source, file_path):
        calls.append(("load", source, file_path))

    def fake_has_igdb_steam_link(appid):
        calls.append(("has_link", appid))
        return appid == 730

    def fake_sleep(delay):
        calls.append(("sleep", delay))

    monkeypatch.setattr(
        main,
        "get_steam_games_for_igdb_enrichment",
        fake_get_steam_games_for_igdb_enrichment,
    )
    monkeypatch.setattr(main, "run_igdb_game_search", fake_run_igdb_game_search)
    monkeypatch.setattr(main, "load_data", fake_load_data)
    monkeypatch.setattr(main, "has_igdb_steam_link", fake_has_igdb_steam_link)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_igdb_enrich_steam(
        limit=2,
        search_limit=10,
        delay=0.5,
    )

    assert calls == [
        ("search", "Counter-Strike 2", 10),
        ("load", "igdb", raw_path),
        ("has_link", 730),
        ("sleep", 0.5),
        ("search", "Dota 2", 10),
        ("load", "igdb", raw_path),
        ("has_link", 570),
    ]


def test_mark_twitch_category_as_excluded(monkeypatch):
    """
    Test that known non-game Twitch categories are marked as excluded.
    """

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    main.mark_twitch_category_as_excluded(
        twitch_game_id="509658",
        twitch_game_name="Just Chatting",
        notes="Known non-game Twitch category.",
    )

    assert fake_connection.committed is True
    assert fake_connection.executed_queries[0][1] == (
        "509658",
        "Just Chatting",
        "Known non-game Twitch category.",
    )


def test_run_igdb_enrich_twitch(monkeypatch, tmp_path):
    """
    Test that Twitch enrichment excludes non-games, searches games, and
    records a search attempt after every completed search (empty or not).
    """

    raw_path = tmp_path / "igdb.json"
    calls = []

    def fake_get_unmapped_twitch_categories(limit, retry_after_days, max_attempts):
        assert limit == 3
        assert retry_after_days == 30
        assert max_attempts == 3
        return [
            {
                "twitch_game_id": "509658",
                "twitch_game_name": "Just Chatting",
            },
            {
                "twitch_game_id": "32399",
                "twitch_game_name": "Counter-Strike",
            },
            {
                "twitch_game_id": "999999",
                "twitch_game_name": "Some Obscure Category",
            },
        ]

    def fake_mark_twitch_category_as_excluded(twitch_game_id, twitch_game_name, notes):
        calls.append(("exclude", twitch_game_id, twitch_game_name, notes))

    def fake_run_igdb_game_search(search_term, limit):
        calls.append(("search", search_term, limit))
        return raw_path

    def fake_load_data(source, file_path):
        calls.append(("load", source, file_path))
        # Counter-Strike finds one match, the obscure category finds nothing.
        return 1 if source == "igdb" and "obscure" not in str(file_path) else 0

    def fake_record_igdb_search_attempt(twitch_game_id, twitch_game_name):
        calls.append(("record_attempt", twitch_game_id, twitch_game_name))

    def fake_sleep(delay):
        calls.append(("sleep", delay))

    monkeypatch.setattr(
        main,
        "get_unmapped_twitch_categories",
        fake_get_unmapped_twitch_categories,
    )
    monkeypatch.setattr(
        main,
        "mark_twitch_category_as_excluded",
        fake_mark_twitch_category_as_excluded,
    )
    monkeypatch.setattr(main, "run_igdb_game_search", fake_run_igdb_game_search)
    monkeypatch.setattr(main, "load_data", fake_load_data)
    monkeypatch.setattr(
        main,
        "record_igdb_search_attempt",
        fake_record_igdb_search_attempt,
    )
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    main.run_igdb_enrich_twitch(
        limit=3,
        search_limit=10,
        delay=0.5,
    )

    assert calls == [
        (
            "exclude",
            "509658",
            "Just Chatting",
            "Known non-game Twitch category.",
        ),
        ("search", "Counter-Strike", 10),
        ("load", "igdb", raw_path),
        ("record_attempt", "32399", "Counter-Strike"),
        ("sleep", 0.5),
        ("search", "Some Obscure Category", 10),
        ("load", "igdb", raw_path),
        ("record_attempt", "999999", "Some Obscure Category"),
    ]


def test_run_igdb_enrich_twitch_does_not_record_attempt_on_exception(monkeypatch, tmp_path):
    """
    Test that a failed request (not a completed empty search) does not count
    as a search attempt, but does count as a search error so the backlog
    head clears instead of retrying the same failure every run.
    """

    attempt_calls = []
    error_calls = []

    def fake_get_unmapped_twitch_categories(limit, retry_after_days, max_attempts):
        return [
            {
                "twitch_game_id": "32399",
                "twitch_game_name": "Counter-Strike",
            },
        ]

    def fake_run_igdb_game_search(search_term, limit):
        raise RuntimeError("Fake API error")

    def fake_record_igdb_search_attempt(twitch_game_id, twitch_game_name):
        attempt_calls.append((twitch_game_id, twitch_game_name))

    def fake_record_igdb_search_error(twitch_game_id, twitch_game_name):
        error_calls.append((twitch_game_id, twitch_game_name))

    monkeypatch.setattr(
        main,
        "get_unmapped_twitch_categories",
        fake_get_unmapped_twitch_categories,
    )
    monkeypatch.setattr(main, "run_igdb_game_search", fake_run_igdb_game_search)
    monkeypatch.setattr(
        main,
        "record_igdb_search_attempt",
        fake_record_igdb_search_attempt,
    )
    monkeypatch.setattr(
        main,
        "record_igdb_search_error",
        fake_record_igdb_search_error,
    )

    main.run_igdb_enrich_twitch(
        limit=1,
        search_limit=10,
        delay=0.5,
    )

    assert attempt_calls == []
    assert error_calls == [("32399", "Counter-Strike")]


def test_record_igdb_search_attempt(monkeypatch):
    """
    Test that a search attempt is recorded without touching mapping_status.
    """

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    main.record_igdb_search_attempt(
        twitch_game_id="32399",
        twitch_game_name="Counter-Strike",
    )

    assert fake_connection.committed is True
    executed_query, params = fake_connection.executed_queries[0]

    assert params == ("32399", "Counter-Strike")
    assert "mapping_status" not in executed_query


def test_record_igdb_search_error(monkeypatch):
    """
    Test that a search error is recorded against igdb_search_errors (not
    igdb_search_attempts), advances last_igdb_search_at, and does not touch
    mapping_status.
    """

    fake_connection = FakeConnection()

    def fake_get_db_connection():
        return fake_connection

    monkeypatch.setattr(main, "get_db_connection", fake_get_db_connection)

    main.record_igdb_search_error(
        twitch_game_id="32399",
        twitch_game_name="Counter-Strike",
    )

    assert fake_connection.committed is True
    executed_query, params = fake_connection.executed_queries[0]

    assert params == ("32399", "Counter-Strike")
    assert "igdb_search_errors" in executed_query
    assert "last_igdb_search_at" in executed_query
    assert "igdb_search_attempts" not in executed_query
    assert "mapping_status" not in executed_query


def test_main_dispatches_igdb_search(monkeypatch):
    """
    Test that the igdb-search CLI command calls the search pipeline.
    """

    fake_args = argparse.Namespace(
        command="igdb-search",
        search="Counter-Strike",
        limit=10,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_igdb_search(search_term, limit):
        calls.append((search_term, limit))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_igdb_search", fake_run_igdb_search)

    main.main()

    assert calls == [
        ("Counter-Strike", 10),
    ]


def test_main_dispatches_igdb_enrich_twitch(monkeypatch):
    """
    Test that the igdb-enrich-twitch CLI command calls the enrichment pipeline.
    """

    fake_args = argparse.Namespace(
        command="igdb-enrich-twitch",
        limit=20,
        search_limit=10,
        delay=1.0,
        retry_after_days=30,
        max_attempts=3,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_igdb_enrich_twitch(
        limit,
        search_limit,
        delay,
        retry_after_days,
        max_attempts,
    ):
        calls.append((limit, search_limit, delay, retry_after_days, max_attempts))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_igdb_enrich_twitch", fake_run_igdb_enrich_twitch)

    main.main()

    assert calls == [
        (20, 10, 1.0, 30, 3),
    ]


def test_main_dispatches_igdb_enrich_steam(monkeypatch):
    """
    Test that the igdb-enrich-steam CLI command calls the enrichment pipeline.
    """

    fake_args = argparse.Namespace(
        command="igdb-enrich-steam",
        limit=100,
        search_limit=10,
        delay=1.0,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_igdb_enrich_steam(limit, search_limit, delay):
        calls.append((limit, search_limit, delay))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_igdb_enrich_steam", fake_run_igdb_enrich_steam)

    main.main()

    assert calls == [
        (100, 10, 1.0),
    ]


def test_main_dispatches_generate_twitch_igdb_candidates(monkeypatch):
    """
    Test that the candidate generator CLI command calls the generator.
    """

    fake_args = argparse.Namespace(
        command="generate-twitch-igdb-candidates",
        limit=100,
        min_score=0.75,
        top_n=5,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_generate_twitch_igdb_candidates(limit, min_score, top_n):
        calls.append((limit, min_score, top_n))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(
        main,
        "run_generate_twitch_igdb_candidates",
        fake_run_generate_twitch_igdb_candidates,
    )

    main.main()

    assert calls == [
        (100, 0.75, 5),
    ]


def test_main_dispatches_twitch_streams(monkeypatch):
    """
    Test that the twitch-streams CLI command calls the streams pipeline.
    """

    fake_args = argparse.Namespace(
        command="twitch-streams",
        pages=2,
        delay=0.5,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_twitch_streams(pages, delay):
        calls.append((pages, delay))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_twitch_streams", fake_run_twitch_streams)

    main.main()

    assert calls == [(2, 0.5)]


def test_main_dispatches_steam_store_enrich_with_refresh_after_days(monkeypatch):
    """
    Test that steam-store-enrich passes --refresh-after-days to the pipeline.
    """

    fake_args = argparse.Namespace(
        command="steam-store-enrich",
        limit=50,
        delay=2,
        refresh_after_days=14,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_steam_store_enrich(limit, delay_seconds, refresh_after_days=30):
        calls.append((limit, delay_seconds, refresh_after_days))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_steam_store_enrich", fake_run_steam_store_enrich)

    main.main()

    assert calls == [(50, 2, 14)]


def test_main_dispatches_migrate(monkeypatch):
    """
    Test that the migrate CLI command calls run_migrations.
    """

    fake_args = argparse.Namespace(command="migrate")

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_migrations():
        calls.append("migrate")

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_migrations", fake_run_migrations)

    main.main()

    assert calls == ["migrate"]


# --- tasks/001: dispatch coverage for the six subcommands that had none ---
#
# monkeypatch.setattr(main, "<name>", fake) raises AttributeError by default
# (raising=True) if "<name>" is not an attribute of src.main at test time.
# That is what makes this idiom survive the coming refactor safely: once a
# callable moves out of src.main (task 003+) without a compatibility
# re-export -- which the refactor plan explicitly rules out -- these tests
# fail loudly at the setattr call instead of quietly patching a stub the
# production dispatch path no longer reaches.


def test_main_dispatches_steamspy_all_page(monkeypatch):
    """
    Test that the steamspy-all-page CLI command calls the single-page pipeline.
    """

    fake_args = argparse.Namespace(
        command="steamspy-all-page",
        page=3,
        snapshot_date="2026-05-09",
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_steamspy_all_page(page, snapshot_date=None):
        calls.append((page, snapshot_date))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_steamspy_all_page", fake_run_steamspy_all_page)

    main.main()

    assert calls == [(3, "2026-05-09")]


def test_main_dispatches_steamspy_daily(monkeypatch):
    """
    Test that the steamspy-daily CLI command calls the daily pipeline.
    """

    fake_args = argparse.Namespace(
        command="steamspy-daily",
        start_page=1,
        max_pages=5,
        delay=10,
        snapshot_date="2026-05-09",
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_steamspy_daily(
        start_page,
        max_pages,
        delay_seconds,
        snapshot_date=None,
    ):
        calls.append((start_page, max_pages, delay_seconds, snapshot_date))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_steamspy_daily", fake_run_steamspy_daily)

    main.main()

    assert calls == [(1, 5, 10, "2026-05-09")]


def test_main_dispatches_steam_store_appdetails(monkeypatch):
    """
    Test that the steam-store-appdetails CLI command calls the single-appid pipeline.
    """

    fake_args = argparse.Namespace(command="steam-store-appdetails", appid=730)

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_steam_store_appdetails(appid):
        calls.append(appid)

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(
        main, "run_steam_store_appdetails", fake_run_steam_store_appdetails
    )

    main.main()

    assert calls == [730]


def test_main_dispatches_twitch_games_lookup(monkeypatch, tmp_path):
    """
    Test that the twitch-games-lookup CLI command fetches and loads the
    requested ids directly (this subcommand has no dedicated pipeline
    function -- it calls the extractor and load_data straight from main()).
    """

    fake_args = argparse.Namespace(
        command="twitch-games-lookup", ids=["32399", "21779"]
    )

    raw_path = tmp_path / "games_lookup.json"
    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_twitch_games_lookup(ids):
        calls.append(("lookup", ids))
        return raw_path

    def fake_load_data(source, file_path):
        calls.append(("load", source, file_path))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(main, "run_twitch_games_lookup", fake_run_twitch_games_lookup)
    monkeypatch.setattr(main, "load_data", fake_load_data)

    main.main()

    assert calls == [
        ("lookup", ["32399", "21779"]),
        ("load", "twitch_games_lookup", raw_path),
    ]


def test_main_dispatches_twitch_games_lookup_observed(monkeypatch):
    """
    Test that the twitch-games-lookup-observed CLI command calls the batch pipeline.
    """

    fake_args = argparse.Namespace(
        command="twitch-games-lookup-observed",
        limit=500,
        batch_size=100,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_run_twitch_games_lookup_for_observed(limit, batch_size):
        calls.append((limit, batch_size))

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(
        main,
        "run_twitch_games_lookup_for_observed",
        fake_run_twitch_games_lookup_for_observed,
    )

    main.main()

    assert calls == [(500, 100)]


def test_main_dispatches_generate_twitch_igdb_candidates_from_catalog(monkeypatch):
    """
    Test that the generate-twitch-igdb-candidates-from-catalog CLI command
    calls the catalog-backed candidate generator.
    """

    fake_args = argparse.Namespace(
        command="generate-twitch-igdb-candidates-from-catalog",
        limit=500,
    )

    calls = []

    def fake_parse_args():
        return fake_args

    def fake_generate_twitch_igdb_candidates_from_catalog(limit):
        calls.append(limit)

    monkeypatch.setattr(main, "parse_args", fake_parse_args)
    monkeypatch.setattr(
        main,
        "generate_twitch_igdb_candidates_from_catalog",
        fake_generate_twitch_igdb_candidates_from_catalog,
    )

    main.main()

    assert calls == [500]


# Subcommand -> name of the test above (or an existing one) that dispatches
# it through main.main() and asserts it reaches its intended callable with
# the arguments the CLI parsed. This table is only trustworthy alongside
# test_all_parser_subcommands_have_a_recorded_dispatch_test below, which
# fails the moment this table and the live argparse parser disagree --
# whether a subcommand was added, removed, or renamed on either side.
DISPATCH_TEST_BY_SUBCOMMAND = {
    "steamspy-all-page": "test_main_dispatches_steamspy_all_page",
    "steamspy-daily": "test_main_dispatches_steamspy_daily",
    "steam-store-appdetails": "test_main_dispatches_steam_store_appdetails",
    "steam-store-enrich": (
        "test_main_dispatches_steam_store_enrich_with_refresh_after_days"
    ),
    "daily": "test_main_dispatches_daily",
    "igdb-search": "test_main_dispatches_igdb_search",
    "igdb-enrich-twitch": "test_main_dispatches_igdb_enrich_twitch",
    "igdb-enrich-steam": "test_main_dispatches_igdb_enrich_steam",
    "generate-twitch-igdb-candidates": (
        "test_main_dispatches_generate_twitch_igdb_candidates"
    ),
    "twitch-streams": "test_main_dispatches_twitch_streams",
    "twitch-games-lookup": "test_main_dispatches_twitch_games_lookup",
    "twitch-games-lookup-observed": (
        "test_main_dispatches_twitch_games_lookup_observed"
    ),
    "generate-twitch-igdb-candidates-from-catalog": (
        "test_main_dispatches_generate_twitch_igdb_candidates_from_catalog"
    ),
    "migrate": "test_main_dispatches_migrate",
}


def _live_parser_subcommands(capsys) -> set[str]:
    """
    Enumerate subcommands from the real, live argparse parser built by
    main.parse_args() -- not from a hand-typed list here in the test. An
    invalid command makes argparse itself print the full choice set in its
    usage line, which this reads back out.

    This is deliberately not "build the expected list by calling
    parse_args() and asserting against the same object" (the trap the task
    card names): the assertion below compares this live set against
    DISPATCH_TEST_BY_SUBCOMMAND, a table written independently of this
    function, not against itself.
    """

    original_argv = sys.argv
    sys.argv = ["prog", "__not_a_real_subcommand__"]
    try:
        with pytest.raises(SystemExit):
            main.parse_args()
    finally:
        sys.argv = original_argv

    usage = capsys.readouterr().err
    match = re.search(r"\{([^}]+)\}", usage)
    assert match, f"could not find subcommand choices in argparse usage: {usage!r}"

    return set(match.group(1).split(","))


def _test_function_sources() -> dict[str, str]:
    """
    Map test function name -> its source text, read from every tests/*.py
    file on disk with `ast`.

    tasks/001, review findings 1 and 4. Two things this must survive:

    - A dispatch test moved verbatim into another test file, as task 003
      onwards will do when callables and their tests move together. Reading
      only this module's globals() would call that "test function not found"
      while coverage is fully intact -- a false red whose easiest fix is
      deleting the assertion.
    - Any selective pytest invocation. Reading pytest's collected item list
      (`session.items`) looked like the fix for the first problem, but that
      list holds only the *selected* items, so running one test from the VS
      Code gutter, or `pytest -k`, or `--lf` after an unrelated failure,
      reported all fourteen dispatch tests as missing.

    Reading the files is independent of both: it does not care which tests
    were selected, or which file a test currently lives in.
    """

    sources: dict[str, str] = {}

    for path in sorted(Path(__file__).resolve().parent.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                segment = ast.get_source_segment(text, node)
                if segment is not None:
                    sources.setdefault(node.name, segment)

    return sources


def test_all_parser_subcommands_have_a_recorded_dispatch_test(capsys):
    """
    Every subcommand the live parser knows about must have exactly one entry
    in DISPATCH_TEST_BY_SUBCOMMAND, that entry must name a test function that
    actually exists somewhere in the collected suite, and that test's source
    must actually mention the subcommand it is claimed to cover. This fails
    if:
    - a subcommand is added to the parser and this table is not updated;
    - a subcommand is removed or renamed in the parser and the table still
      names the old one;
    - the table names a dispatch test that does not exist (a typo, or a
      test that was renamed without updating this table);
    - the table is repointed at a test that does not actually dispatch that
      subcommand (tasks/001 second pass, non-blocking finding 3: deleting
      test_main_dispatches_migrate and repointing "migrate" at
      test_main_dispatches_daily previously passed with migrate left
      uncovered -- this last check is what catches that).

    The last check matches `command="<subcommand>"`, quotes included, not a
    bare substring. Three subcommand names are prefixes of another
    ("daily" / "steamspy-daily", "twitch-games-lookup" /
    "twitch-games-lookup-observed", "generate-twitch-igdb-candidates" /
    "generate-twitch-igdb-candidates-from-catalog"), so a substring test let
    those three be repointed at their longer sibling and lose their only
    dispatch test silently -- review finding 2, demonstrated at 46 passed.
    The closing quote is what makes the match exact.
    """

    parser_subcommands = _live_parser_subcommands(capsys)
    table_subcommands = set(DISPATCH_TEST_BY_SUBCOMMAND)

    assert table_subcommands == parser_subcommands, (
        "DISPATCH_TEST_BY_SUBCOMMAND and the live argparse parser disagree: "
        f"only in table: {table_subcommands - parser_subcommands}, "
        f"only in parser: {parser_subcommands - table_subcommands}"
    )

    collected = _test_function_sources()
    missing_tests = {
        subcommand: test_name
        for subcommand, test_name in DISPATCH_TEST_BY_SUBCOMMAND.items()
        if test_name not in collected
    }

    assert missing_tests == {}, f"dispatch test functions not found: {missing_tests}"

    mismatched = {
        subcommand: test_name
        for subcommand, test_name in DISPATCH_TEST_BY_SUBCOMMAND.items()
        if f'command="{subcommand}"' not in collected[test_name]
    }

    assert mismatched == {}, (
        "dispatch tests recorded in DISPATCH_TEST_BY_SUBCOMMAND do not "
        f"mention the subcommand string they are claimed to cover: {mismatched}"
    )
