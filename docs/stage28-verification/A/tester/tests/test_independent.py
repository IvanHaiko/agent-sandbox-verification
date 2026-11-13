"""Blind contract tests, designed without candidate source or execution."""
import copy
import datetime as dt
import json
from unittest.mock import MagicMock

import pytest

from src import load
from src.transform import transform_igdb_search_results


def _game(identifier=1, name="Game", steam="101", twitch="201"):
    game = {"id": identifier, "name": name}
    links = []
    if steam is not None:
        links.append({"category": 1, "uid": steam,
                      "url": f"https://store.steampowered.com/app/{steam}/"})
    if twitch is not None:
        links.append({"category": 14, "uid": twitch,
                      "url": f"https://www.twitch.tv/directory/game/{name}"})
    if links:
        game["external_games"] = links
    return game


def _file(tmp_path, payload, name="igdb_search_results_test.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _snapshot(db):
    return {table: db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("igdb_games", "igdb_game_store_links", "twitch_categories")}


def _forbid_connection(monkeypatch):
    probe = MagicMock(side_effect=AssertionError("connection acquired before validation"))
    monkeypatch.setattr(load, "get_db_connection", probe)
    return probe


@pytest.mark.parametrize("payload", [None, [], "data", 1, True, {},
                                      {"data": None}, {"data": {}},
                                      {"data": "[]"}, {"data": 0}])
def test_invalid_envelopes_raise_before_connection(payload, tmp_path, monkeypatch):
    probe = _forbid_connection(monkeypatch)
    with pytest.raises(ValueError):
        transform_igdb_search_results(payload)
    with pytest.raises(ValueError):
        load.load_igdb_file(_file(tmp_path, payload))
    probe.assert_not_called()


@pytest.mark.parametrize("record", [None, [], "game", {}, {"id": 1},
    {"id": True, "name": "Game"}, {"id": False, "name": "Game"},
    {"id": 0, "name": "Game"}, {"id": -1, "name": "Game"},
    {"id": 2147483648, "name": "Game"}, {"id": 1.0, "name": "Game"},
    {"id": "1", "name": "Game"}, {"id": None, "name": "Game"},
    {"id": 1, "name": None}, {"id": 1, "name": 123},
    {"id": 1, "name": ""}, {"id": 1, "name": " \t\n"}])
def test_invalid_records_reject_entire_batch(record, tmp_path, monkeypatch):
    probe = _forbid_connection(monkeypatch)
    payload = {"data": [_game(), record]}
    before = copy.deepcopy(payload)
    with pytest.raises(ValueError):
        transform_igdb_search_results(payload)
    assert payload == before
    with pytest.raises(ValueError):
        load.load_igdb_file(_file(tmp_path, payload))
    probe.assert_not_called()


@pytest.mark.parametrize("second_name", ["Game", "Different"])
def test_duplicate_game_ids_rejected(second_name, tmp_path, monkeypatch):
    probe = _forbid_connection(monkeypatch)
    payload = {"data": [_game(), _game(name=second_name)]}
    with pytest.raises(ValueError):
        transform_igdb_search_results(payload)
    with pytest.raises(ValueError):
        load.load_igdb_file(_file(tmp_path, payload))
    probe.assert_not_called()


_NESTED_BAD = [(field, value) for field in ("external_games", "websites")
               for value in ({}, "links", 2, True, [None], [[]], ["url"],
                             [{"url": 123}], [{"url": False}], [{"url": []}])]
_NESTED_BAD += [("external_games", [{"category": 1, "uid": value}])
                for value in (True, False, 1.2, [], {})]


@pytest.mark.parametrize("field,value", _NESTED_BAD)
def test_malformed_nested_data_rejected_before_connection(field, value, tmp_path, monkeypatch):
    probe = _forbid_connection(monkeypatch)
    bad = _game(2)
    bad[field] = value
    payload = {"data": [_game(), bad]}
    before = copy.deepcopy(payload)
    with pytest.raises(ValueError):
        transform_igdb_search_results(payload)
    with pytest.raises(ValueError):
        load.load_igdb_file(_file(tmp_path, payload))
    assert payload == before
    probe.assert_not_called()


@pytest.mark.parametrize("optional", [None, [], [{}], [{"url": None}], [{"url": ""}],
    [{"url": "https://example.invalid/unknown"}]])
def test_valid_nested_empty_and_unknown_values_preserve_input(optional):
    payload = {"data": [{"id": 2147483647, "name": "  Keep Name  ",
                         "external_games": optional, "websites": optional}],
               "metadata": {"ignored": True}}
    before = copy.deepcopy(payload)
    result = transform_igdb_search_results(payload)
    assert result
    assert payload == before
    assert result == transform_igdb_search_results(copy.deepcopy(before))
    for uid in (None, "", "123", 123, 0, -3):
        transform_igdb_search_results({"data": [{"id": 1, "name": "Valid",
            "external_games": [{"uid": uid, "url": None}]}]})


def test_empty_batch_and_malformed_json_never_connect(tmp_path, monkeypatch):
    probe = _forbid_connection(monkeypatch)
    empty = {"data": [], "request": "ignored"}
    transform_igdb_search_results(empty)
    assert load.load_igdb_file(_file(tmp_path, empty)) == 0
    path = tmp_path / "igdb_search_results_broken.json"
    path.write_text('{"data": [', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load.load_igdb_file(path)
    probe.assert_not_called()


@pytest.mark.parametrize("seam", ["upsert_igdb_game", "upsert_igdb_game_store_link",
                                   "upsert_twitch_category"])
def test_file_failure_rolls_back_prior_updates_and_retry_is_durable(seam, db, tmp_path, monkeypatch):
    saved = _file(tmp_path, {"data": [_game()]}, "igdb_search_results_previous.json")
    assert load.load_igdb_file(saved) == 1
    before = _snapshot(db)
    db.commit()
    pending = _file(tmp_path, {"data": [_game(name="Changed"), _game(2, "Second", "102", "202")]},
                    "igdb_search_results_pending.json")
    original = getattr(load, seam)
    calls = 0

    def fail_after_write(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            raise RuntimeError("injected write failure")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(load, seam, fail_after_write)
        with pytest.raises(RuntimeError, match="injected write failure"):
            load.load_igdb_file(pending)
    assert calls == 2
    assert _snapshot(db) == before
    db.commit()
    assert pending.exists()
    assert load.load_igdb_file(pending) == 2
    after = _snapshot(db)
    assert {table: len(rows) for table, rows in after.items()} == {
        "igdb_games": 2, "igdb_game_store_links": 2, "twitch_categories": 2}
    assert db.execute("SELECT name FROM igdb_games WHERE igdb_game_id=1").fetchone() == ("Changed",)
    db.commit()
    assert load.load_igdb_file(pending) == 2
    assert _snapshot(db) == after


def test_identical_replay_is_null_safe_and_ignores_json_key_order(db, tmp_path):
    game = _game()
    game.update({"summary": None, "slug": None, "rating": None,
                 "custom_metadata": {"z": None, "a": {"y": 2, "x": 1}}})
    payload = {"data": [game]}
    path = _file(tmp_path, payload)
    assert load.load_igdb_file(path) == 1
    for table, column in (("igdb_games", "updated_at"), ("twitch_categories", "updated_at"),
                          ("igdb_game_store_links", "created_at")):
        db.execute(f"UPDATE {table} SET {column} = TIMESTAMP '2001-01-01 00:00:00'")
    db.commit()
    before = _snapshot(db)
    assert all(len(rows) == 1 for rows in before.values())
    db.commit()
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    assert load.load_igdb_file(path) == 1
    assert _snapshot(db) == before
    db.commit()
    assert load.load_igdb_file(path) == 1
    assert _snapshot(db) == before


def test_changed_metadata_and_mapping_advance_timestamps_without_deletion(db, tmp_path):
    path = _file(tmp_path, {"data": [_game()]})
    assert load.load_igdb_file(path) == 1
    db.execute("UPDATE igdb_games SET updated_at=TIMESTAMP '2001-01-01'")
    db.execute("UPDATE twitch_categories SET updated_at=TIMESTAMP '2001-01-01'")
    db.commit()
    changed = _game(2, "New mapping", "101", "201")
    changed["summary"] = "New summary"
    assert load.load_igdb_file(_file(tmp_path, {"data": [changed]})) == 1
    assert db.execute("SELECT igdb_game_id, twitch_game_name, updated_at > TIMESTAMP '2001-01-01' "
                      "FROM twitch_categories WHERE twitch_game_id='201'").fetchone() == (2, "New mapping", True)
    assert db.execute("SELECT igdb_game_id FROM igdb_game_store_links WHERE store='steam' AND store_game_id='101'").fetchone() == (2,)
    db.execute("UPDATE igdb_games SET updated_at=TIMESTAMP '2001-01-01' WHERE igdb_game_id=2")
    db.commit()
    metadata = {"id": 2, "name": "New mapping", "summary": "Changed again"}
    assert load.load_igdb_file(_file(tmp_path, {"data": [metadata]})) == 1
    assert db.execute("SELECT summary, updated_at > TIMESTAMP '2001-01-01' FROM igdb_games WHERE igdb_game_id=2").fetchone() == ("Changed again", True)
    assert db.execute("SELECT count(*) FROM igdb_game_store_links").fetchone() == (1,)
    assert db.execute("SELECT count(*) FROM twitch_categories").fetchone() == (1,)


def test_compatibility_raw_json_utc_and_link_precedence(db, tmp_path):
    game = _game(name="  Verbatim Name  ", steam=None, twitch=None)
    game.update({"first_release_date": 1609457400, "game_type": 0, "status": 0,
                 "external_games": [{"category": 1, "uid": "111", "url": "https://store.steampowered.com/app/222/"}],
                 "websites": [{"category": 13, "url": "https://store.steampowered.com/app/333/"}]})
    assert load.load_igdb_file(_file(tmp_path, {"data": [game]})) == 1
    row = db.execute("SELECT name, raw_json, first_release_date, game_type, status, game_type_label, status_label FROM igdb_games").fetchone()
    assert row[:5] == ("  Verbatim Name  ", game, dt.date(2020, 12, 31), 0, 0)
    assert isinstance(row[5], str) and row[5]
    assert isinstance(row[6], str) and row[6]
    assert db.execute("SELECT store, store_game_id FROM igdb_game_store_links").fetchall() == [("steam", "333")]
    external_only = copy.deepcopy(game)
    external_only["id"] = 2
    external_only.pop("websites")
    assert load.load_igdb_file(_file(tmp_path, {"data": [external_only]})) == 1
    assert db.execute("SELECT store_game_id FROM igdb_game_store_links WHERE igdb_game_id=2").fetchall() == [("222",)]


def test_public_helpers_remain_compatible_with_fake_connections(tmp_path, monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = None
    monkeypatch.setattr(load, "get_db_connection", lambda: connection)
    assert load.load_igdb_file(_file(tmp_path, {"data": [_game()]})) == 1
    assert cursor.execute.called or connection.execute.called


def test_load_data_dispatches_igdb_saved_file(tmp_path, monkeypatch):
    path = _file(tmp_path, {"data": [_game()]}, "igdb_search_results_20261009_120000.json")
    observed = []

    def loader(file_path):
        observed.append(str(file_path))
        return 1

    monkeypatch.setattr(load, "load_igdb_file", loader)
    load.load_data(path)
    assert observed == [str(path)]
