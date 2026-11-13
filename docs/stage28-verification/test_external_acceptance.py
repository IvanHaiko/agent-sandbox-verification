"""Held-out coordinator suite authored before either candidate. No private helper names."""
import copy
import json

import pytest

from src import load, transform
from src.db import get_db_connection


def game(identity=71001, name="Example"):
    return {"id": identity, "name": name, "summary": None,
            "external_games": [{"uid": "81001", "url": "https://www.twitch.tv/directory/category/example"}],
            "websites": [{"url": "https://store.steampowered.com/app/91001/Example"}]}


def write(tmp_path, payload):
    path = tmp_path / "saved.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


BAD = [None, [], {}, {"data": None}, {"data": {}}, {"data": "bad"},
       {"data": [None]}, {"data": [{"id": True, "name": "x"}]},
       {"data": [{"id": 0, "name": "x"}]}, {"data": [{"id": -1, "name": "x"}]},
       {"data": [{"id": 2147483648, "name": "x"}]},
       {"data": [{"id": "1", "name": "x"}]}, {"data": [{"id": 1}]},
       {"data": [{"id": 1, "name": "  "}]}, {"data": [{"id": 1, "name": 5}]},
       {"data": [game(), game()]},
       *[{"data": [dict(game(), **{field: value})]} for field, value in
         [("external_games", {}), ("websites", "oops"), ("external_games", [None]),
          ("websites", [5]), ("websites", [{"url": 7}]),
          ("external_games", [{"url": []}]), ("external_games", [{"uid": True}]),
          ("external_games", [{"uid": []}])]]]


@pytest.mark.parametrize("payload", BAD)
def test_malformed_transform(payload):
    with pytest.raises(ValueError):
        transform.transform_igdb_search_results(payload)


@pytest.mark.parametrize("payload", BAD)
def test_malformed_before_connection(payload, monkeypatch, tmp_path):
    calls = []
    def forbidden():
        calls.append(True)
        raise AssertionError("database acquired for invalid input")
    monkeypatch.setattr(load, "get_db_connection", forbidden)
    with pytest.raises(ValueError):
        load.load_igdb_file(write(tmp_path, payload))
    assert not calls


def test_late_invalid_before_connection(monkeypatch, tmp_path):
    monkeypatch.setattr(load, "get_db_connection", lambda: pytest.fail("late validation"))
    with pytest.raises(ValueError):
        load.load_igdb_file(write(tmp_path, {"data": [game(), {"id": 2}]}))


def test_empty_without_database(monkeypatch, tmp_path):
    monkeypatch.setattr(load, "get_db_connection", lambda: pytest.fail("empty acquired database"))
    assert transform.transform_igdb_search_results({"data": []}) == []
    assert load.load_igdb_file(write(tmp_path, {"data": []})) == 0


def test_null_nested_and_input_preservation():
    payload = {"data": [{"id": 2147483647, "name": "  Kept  ",
                         "external_games": None, "websites": None}]}
    before = copy.deepcopy(payload)
    result = transform.transform_igdb_search_results(payload)
    assert payload == before
    assert result[0]["igdb_game"]["name"] == "  Kept  "
    assert result[0]["igdb_game"]["raw_json"] == before["data"][0]
    assert result[0]["store_links"] == result[0]["twitch_categories"] == []


def test_existing_link_precedence():
    payload = {"data": [dict(game(), external_games=[
        {"url": "https://store.steampowered.com/app/91001/External", "uid": 777},
        {"url": None, "uid": None}, {"url": "https://unknown.invalid/x", "uid": "x"}])]}
    before = copy.deepcopy(payload)
    result = transform.transform_igdb_search_results(payload)[0]
    assert result["store_links"] == [{"igdb_game_id": 71001, "store": "steam",
        "store_game_id": "91001", "store_url": game()["websites"][0]["url"]}]
    assert payload == before


def rows():
    with get_db_connection() as conn:
        return {table: conn.execute("SELECT row_to_json(t)::text FROM " + table + " t ORDER BY 1").fetchall()
                for table in ("igdb_games", "igdb_game_store_links", "twitch_categories")}


def test_postgres_replay_and_changed_values(test_database, tmp_path):
    payload = {"data": [game()]}
    path = write(tmp_path, payload)
    assert load.load_data("igdb", path) == 1
    before = rows()
    # A stored sentinel makes a timestamp rewrite visible without sleeps or clock assumptions.
    with get_db_connection() as conn:
        conn.execute("UPDATE igdb_games SET updated_at='2000-01-01'")
        conn.execute("UPDATE twitch_categories SET updated_at='2000-01-01'")
    before = rows()
    reordered = {"data": [dict(reversed(list(payload["data"][0].items())))]}
    assert load.load_igdb_file(write(tmp_path, reordered)) == 1
    assert rows() == before
    payload["data"][0]["name"] = "Changed"
    payload["data"][0]["summary"] = "new summary"
    assert load.load_igdb_file(write(tmp_path, payload)) == 1
    with get_db_connection() as conn:
        assert conn.execute("SELECT name,summary,updated_at>'2000-01-02' FROM igdb_games").fetchone() == ("Changed", "new summary", True)
        assert conn.execute("SELECT twitch_game_name,updated_at>'2000-01-02' FROM twitch_categories").fetchone() == ("Changed", True)
        assert conn.execute("SELECT count(*) FROM igdb_game_store_links").fetchone()[0] == 1


@pytest.mark.parametrize("seam", ["upsert_igdb_game_store_link", "upsert_twitch_category"])
def test_postgres_failure_rolls_back_and_saved_retry(test_database, tmp_path, monkeypatch, seam):
    original = {"data": [game()]}
    load.load_igdb_file(write(tmp_path, original))
    before = rows()
    second = game(71002, "Second")
    second["external_games"][0]["uid"] = "81002"
    second["websites"][0]["url"] = "https://store.steampowered.com/app/91002/Second"
    payload = {"data": [dict(game(), name="Updated"), second]}
    path = write(tmp_path, payload)
    fn = getattr(load, seam)
    def failing(conn, record):
        if record["igdb_game_id"] == 71002:
            raise RuntimeError("injected write failure")
        return fn(conn, record)
    with monkeypatch.context() as patch:
        patch.setattr(load, seam, failing)
        with pytest.raises(RuntimeError, match="injected write failure"):
            load.load_igdb_file(path)
    assert rows() == before
    assert load.load_igdb_file(path) == 2
    final = rows()
    assert all(len(v) == 2 for v in final.values())
    assert load.load_igdb_file(path) == 2
    assert rows() == final


def test_postgres_remap_and_no_absence_delete(test_database, tmp_path):
    load.load_igdb_file(write(tmp_path, {"data": [game()]}))
    load.load_igdb_file(write(tmp_path, {"data": [game(71002, "Mapped elsewhere")]}))
    with get_db_connection() as conn:
        assert conn.execute("SELECT igdb_game_id FROM igdb_game_store_links").fetchone()[0] == 71002
        assert conn.execute("SELECT igdb_game_id FROM twitch_categories").fetchone()[0] == 71002
    load.load_igdb_file(write(tmp_path, {"data": [{"id": 71002, "name": "Sparse"}]}))
    with get_db_connection() as conn:
        assert conn.execute("SELECT count(*) FROM igdb_game_store_links").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM twitch_categories").fetchone()[0] == 1
