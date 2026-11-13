"""Frozen black-box tests derived only from the supplied contract and SQL schema."""
import copy
import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from src import load as loader
from src.transform import transform_igdb_search_results


def _file(tmp_path, payload, name="igdb_search.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _game(game_id=101, name="  Original Name  ", links=True):
    game = {"id": game_id, "name": name}
    if links:
        game["external_games"] = [
            {"category": 1, "uid": "501", "url": "https://store.steampowered.com/app/502/Example/"},
            {"category": 14, "uid": "601", "url": "https://www.twitch.tv/directory/game/Example"},
        ]
    return game


def _forbid_connection(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("validation must precede connection acquisition")

    monkeypatch.setattr(loader, "get_db_connection", forbidden)
    return calls


def _reject(payload, tmp_path, monkeypatch):
    untouched = copy.deepcopy(payload)
    calls = _forbid_connection(monkeypatch)
    with pytest.raises(ValueError):
        transform_igdb_search_results(payload)
    assert payload == untouched
    with pytest.raises(ValueError):
        loader.load_igdb_file(str(_file(tmp_path, payload)))
    assert calls == []


def _rows(db):
    # Explicit ordering and native JSONB decoding make snapshots independent of
    # JSON object order while retaining every stored value and timestamp.
    result = {}
    for table, key in (("igdb_games", "igdb_game_id"),
                       ("igdb_game_store_links", "id"),
                       ("twitch_categories", "twitch_game_id")):
        with db.cursor() as cur:
            cur.execute(f"SELECT * FROM {table} ORDER BY {key}")
            result[table] = cur.fetchall()
    db.commit()
    return result


def _one(db, query, params=()):
    with db.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    db.commit()
    return row


def _tick(db):
    # Advance the server clock between loader transactions, not Python time.
    with db.cursor() as cur:
        cur.execute("SELECT pg_sleep(0.025)")
    db.commit()


@pytest.mark.parametrize("payload", [None, [], "bad", 17, True, {},
    {"data": None}, {"data": {}}, {"data": "[]"}, {"data": 0}])
def test_malformed_envelopes(payload, tmp_path, monkeypatch):
    _reject(payload, tmp_path, monkeypatch)


@pytest.mark.parametrize("bad", [None, [], "game", 7,
    {"name": "Game"}, {"id": 1},
    {"id": 0, "name": "Game"}, {"id": -1, "name": "Game"},
    {"id": 2147483648, "name": "Game"}, {"id": True, "name": "Game"},
    {"id": False, "name": "Game"}, {"id": 1.0, "name": "Game"},
    {"id": "1", "name": "Game"}, {"id": None, "name": "Game"},
    {"id": 1, "name": None}, {"id": 1, "name": 42},
    {"id": 1, "name": ""}, {"id": 1, "name": " \t\n"}])
def test_malformed_records(bad, tmp_path, monkeypatch):
    _reject({"data": [_game(999), bad]}, tmp_path, monkeypatch)


@pytest.mark.parametrize("field,value", [
    (field, value)
    for field in ("external_games", "websites")
    for value in ({}, "bad", 1, [None], [[]], ["bad"],
                  [{"url": 1}], [{"url": False}], [{"url": []}], [{"url": {}}])
] + [("external_games", [{"uid": value}])
     for value in (True, False, 1.5, [], {})])
def test_malformed_nested_data(field, value, tmp_path, monkeypatch):
    game = _game(102)
    game[field] = value
    _reject({"data": [_game(101), game]}, tmp_path, monkeypatch)


@pytest.mark.parametrize("different", [False, True])
def test_duplicate_ids_prevalidate_entire_batch(different, tmp_path, monkeypatch):
    second = _game(101, "Changed" if different else "  Original Name  ")
    _reject({"data": [_game(), second]}, tmp_path, monkeypatch)


def test_empty_batch_without_connection(tmp_path, monkeypatch):
    calls = _forbid_connection(monkeypatch)
    payload = {"data": [], "ignored": {"anything": True}}
    assert transform_igdb_search_results(payload) == transform_igdb_search_results({"data": []})
    assert loader.load_igdb_file(str(_file(tmp_path, payload))) == 0
    assert calls == []


def test_json_decode_error_before_connection(tmp_path, monkeypatch):
    calls = _forbid_connection(monkeypatch)
    path = tmp_path / "igdb_invalid.json"
    path.write_text('{"data": [', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        loader.load_igdb_file(str(path))
    assert calls == []


@pytest.mark.parametrize("nested", [None, [], [{}, {"url": None}],
    [{"uid": None, "url": None}], [{"uid": "", "url": ""}],
    [{"uid": 0, "url": "https://unknown.example/game"}]])
def test_valid_nested_empty_values_and_input_immutability(nested):
    payload = {"data": [{"id": 2147483647, "name": "  Exact Name  ",
                        "external_games": nested, "websites": nested}],
               "request_metadata": "ignored"}
    before = copy.deepcopy(payload)
    first = transform_igdb_search_results(payload)
    second = transform_igdb_search_results({"data": copy.deepcopy(payload["data"])})
    assert first == second
    assert payload == before


def test_null_safe_replay_preserves_every_column_and_timestamp(db, tmp_path):
    game = _game()
    game.update({"summary": None, "slug": None, "rating": None,
                 "arbitrary_metadata": {"a": 1, "b": {"x": 2, "y": 3}}})
    payload = {"data": [game, _game(102, "No links", links=False)]}
    path = _file(tmp_path, payload)
    assert loader.load_igdb_file(str(path)) == 2
    before = _rows(db)
    assert len(before["igdb_games"]) == 2
    assert len(before["igdb_game_store_links"]) == 1
    assert len(before["twitch_categories"]) == 1
    _tick(db)
    assert loader.load_igdb_file(str(path)) == 2
    assert _rows(db) == before
    # A semantically identical raw_json object serialized with different key order.
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    _tick(db)
    assert loader.load_igdb_file(str(path)) == 2
    assert _rows(db) == before


def test_changed_metadata_advances_timestamp_and_null_transitions(db, tmp_path):
    game = _game(links=False)
    path = _file(tmp_path, {"data": [game]})
    assert loader.load_igdb_file(str(path)) == 1
    first = _one(db, "SELECT summary, updated_at FROM igdb_games WHERE igdb_game_id=101")
    assert first[0] is None
    game["summary"] = "new metadata"
    game["name"] = "Updated name"
    _file(tmp_path, {"data": [game]})
    _tick(db)
    assert loader.load_igdb_file(str(path)) == 1
    second = _one(db, "SELECT name, summary, updated_at FROM igdb_games WHERE igdb_game_id=101")
    assert second[:2] == ("Updated name", "new metadata")
    assert second[2] > first[1]
    game["summary"] = None
    _file(tmp_path, {"data": [game]})
    _tick(db)
    loader.load_igdb_file(str(path))
    third = _one(db, "SELECT summary, updated_at FROM igdb_games WHERE igdb_game_id=101")
    assert third[0] is None and third[1] > second[2]


def test_twitch_mapping_changes_advance_timestamp_and_links_remap(db, tmp_path):
    first_path = _file(tmp_path, {"data": [_game()]}, "igdb_first.json")
    assert loader.load_igdb_file(str(first_path)) == 1
    old = _one(db, "SELECT igdb_game_id, updated_at FROM twitch_categories WHERE twitch_game_id='601'")
    assert old[0] == 101
    game = _game(102, "New mapped game")
    path = _file(tmp_path, {"data": [game]}, "igdb_second.json")
    _tick(db)
    assert loader.load_igdb_file(str(path)) == 1
    new = _one(db, "SELECT igdb_game_id, twitch_game_name, updated_at FROM twitch_categories WHERE twitch_game_id='601'")
    assert new[:2] == (102, "New mapped game")
    assert new[2] > old[1]
    assert _one(db, "SELECT count(*), min(igdb_game_id) FROM igdb_game_store_links WHERE store='steam' AND store_game_id='502'") == (1, 102)
    stable = _rows(db)
    _tick(db)
    loader.load_igdb_file(str(path))
    assert _rows(db) == stable


def test_absent_links_and_categories_are_not_deleted(db, tmp_path):
    path = _file(tmp_path, {"data": [_game()]})
    loader.load_igdb_file(str(path))
    before = _rows(db)
    _file(tmp_path, {"data": [_game(links=False)]})
    assert loader.load_igdb_file(str(path)) == 1
    after = _rows(db)
    assert after["igdb_game_store_links"] == before["igdb_game_store_links"]
    assert after["twitch_categories"] == before["twitch_categories"]


@pytest.mark.parametrize("seam", ["upsert_igdb_game", "upsert_igdb_game_store_link", "upsert_twitch_category"])
def test_file_rollback_previous_file_durability_and_saved_retry(db, tmp_path, monkeypatch, seam):
    previous = _file(tmp_path, {"data": [_game()]}, "igdb_previous.json")
    assert loader.load_igdb_file(str(previous)) == 1
    before = _rows(db)
    changed = _game(101, "Must roll back")
    added = _game(102, "New game")
    added["external_games"][0]["url"] = "https://store.steampowered.com/app/503/New/"
    added["external_games"][1]["uid"] = "602"
    saved = _file(tmp_path, {"data": [changed, added]}, "igdb_saved.json")
    saved_bytes = saved.read_bytes()
    original = getattr(loader, seam)
    calls = []

    class InjectedWriteFailure(RuntimeError):
        pass

    def fail_after_write(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(True)
        if len(calls) == 2:
            raise InjectedWriteFailure("failed after a real write")
        return result

    with monkeypatch.context() as scoped:
        scoped.setattr(loader, seam, fail_after_write)
        with pytest.raises(InjectedWriteFailure):
            loader.load_igdb_file(str(saved))
    assert len(calls) == 2
    assert _rows(db) == before
    assert saved.read_bytes() == saved_bytes
    assert loader.load_igdb_file(str(saved)) == 2
    after = _rows(db)
    assert len(after["igdb_games"]) == 2
    assert len(after["igdb_game_store_links"]) == 2
    assert len(after["twitch_categories"]) == 2
    assert _one(db, "SELECT name FROM igdb_games WHERE igdb_game_id=101") == ("Must roll back",)
    _tick(db)
    assert loader.load_igdb_file(str(saved)) == 2
    assert _rows(db) == after


def test_mapping_precedence_raw_json_enums_and_utc_date(db, tmp_path):
    game = _game()
    game.update({"game_type": 0, "status": 0, "first_release_date": 86399,
                 "summary": "  Verbatim summary  ", "unknown": {"preserve": [1, None]},
                 "websites": [{"category": 13, "url": "https://store.steampowered.com/app/504/Web/"}]})
    untouched = copy.deepcopy(game)
    payload = {"data": [game], "irrelevant": 99}
    transformed = transform_igdb_search_results(payload)
    assert game == untouched
    assert transformed == transform_igdb_search_results({"data": [copy.deepcopy(game)]})
    assert loader.load_igdb_file(str(_file(tmp_path, payload))) == 1
    row = _one(db, "SELECT name, summary, raw_json, first_release_date, game_type, game_type_label, status, status_label FROM igdb_games WHERE igdb_game_id=101")
    assert row[:5] == (game["name"], game["summary"], game, date(1970, 1, 1), 0)
    assert isinstance(row[5], str) and row[5].strip()
    assert row[6] == 0
    assert isinstance(row[7], str) and row[7].strip()
    assert _one(db, "SELECT store_game_id, store_url FROM igdb_game_store_links WHERE store='steam'") == ("504", game["websites"][0]["url"])
    # Without a website, external Steam URL must win over conflicting uid.
    del game["websites"]
    game["id"] = 103
    game["external_games"] = [game["external_games"][0]]
    path = _file(tmp_path, {"data": [game]}, "igdb_external.json")
    assert loader.load_igdb_file(str(path)) == 1
    assert _one(db, "SELECT store_game_id FROM igdb_game_store_links WHERE igdb_game_id=103") == ("502",)


def test_public_helpers_with_fake_connection(tmp_path, monkeypatch):
    # Exercise helpers with precisely the arguments the public loader supplies;
    # no inferred helper signature or candidate-private helper is required.
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = None
    cursor.rowcount = 1
    monkeypatch.setattr(loader, "get_db_connection", lambda: connection)
    called = set()
    for name in ("upsert_igdb_game", "upsert_igdb_game_store_link", "upsert_twitch_category"):
        original = getattr(loader, name)

        def wrapper(*args, _name=name, _original=original, **kwargs):
            called.add(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(loader, name, wrapper)
    assert loader.load_igdb_file(str(_file(tmp_path, {"data": [_game()]}))) == 1
    assert called == {"upsert_igdb_game", "upsert_igdb_game_store_link", "upsert_twitch_category"}
    assert cursor.execute.called


def test_load_data_dispatches_igdb_file(tmp_path, monkeypatch):
    import inspect

    path = _file(tmp_path, {"data": []})
    calls = []

    def sentinel(file_path):
        calls.append(str(file_path))
        return 37

    monkeypatch.setattr(loader, "load_igdb_file", sentinel)
    # Inspect only the established public signature, never implementation.
    signature = inspect.signature(loader.load_data)
    values = {}
    for name, parameter in signature.parameters.items():
        if "source" in name:
            values[name] = "igdb"
        elif "path" in name or "file" in name:
            values[name] = str(path)
        elif parameter.default is inspect.Parameter.empty:
            pytest.fail(f"Public load_data argument {name!r} is not described by supplied contract")
    bound = signature.bind(**values)
    loader.load_data(*bound.args, **bound.kwargs)
    assert calls == [str(path)]


def test_raw_json_only_metadata_change_updates_game(db, tmp_path):
    game = _game(links=False)
    game["extra_metadata"] = {"version": 1}
    path = _file(tmp_path, {"data": [game]})
    loader.load_igdb_file(str(path))
    before = _one(db, "SELECT updated_at FROM igdb_games WHERE igdb_game_id=101")[0]
    game["extra_metadata"]["version"] = 2
    _file(tmp_path, {"data": [game]})
    _tick(db)
    assert loader.load_igdb_file(str(path)) == 1
    raw, after = _one(db, "SELECT raw_json, updated_at FROM igdb_games WHERE igdb_game_id=101")
    assert raw == game and after > before


def test_store_url_update_preserves_unique_identity(db, tmp_path):
    game = _game()
    path = _file(tmp_path, {"data": [game]})
    loader.load_igdb_file(str(path))
    identity = _one(db, "SELECT id, created_at FROM igdb_game_store_links WHERE store='steam' AND store_game_id='502'")
    url = "https://store.steampowered.com/app/502/Updated_Title/"
    game["external_games"][0]["url"] = url
    _file(tmp_path, {"data": [game]})
    _tick(db)
    assert loader.load_igdb_file(str(path)) == 1
    assert _one(db, "SELECT count(*) FROM igdb_game_store_links") == (1,)
    assert _one(db, "SELECT id, created_at, store_url FROM igdb_game_store_links WHERE store='steam' AND store_game_id='502'") == (*identity, url)
