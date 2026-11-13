"""Validation and transaction-level guarantees for saved IGDB answers."""

import copy
import json
from datetime import date

import psycopg
import pytest

from src import load
from src.db import get_db_connection
from src.transform import transform_igdb_search_results


INVALID_ENVELOPES = [None, [], "answer", 1, {}, {"data": None}, {"data": {}}, {"data": ""}]
INVALID_GAMES = [
    None, [], "game", {}, {"id": True, "name": "Game"},
    {"id": False, "name": "Game"}, {"id": 0, "name": "Game"},
    {"id": -1, "name": "Game"}, {"id": 2147483648, "name": "Game"},
    {"id": "1", "name": "Game"}, {"id": 1.0, "name": "Game"},
    {"id": 1}, {"id": 1, "name": None}, {"id": 1, "name": 5},
    {"id": 1, "name": ""}, {"id": 1, "name": " \t\n"},
]
for collection in ("external_games", "websites"):
    for bad in ({}, "", 1, [None], [[]], ["entry"], [{"url": 1}], [{"url": False}]):
        INVALID_GAMES.append({"id": 1, "name": "Game", collection: bad})
for uid in (True, False, 1.5, [], {}):
    INVALID_GAMES.append({"id": 1, "name": "Game", "external_games": [{"uid": uid}]})
INVALID_BATCHES = INVALID_ENVELOPES + [
    {"data": [{"id": 2, "name": "Valid first"}, game]} for game in INVALID_GAMES
] + [{"data": [{"id": 1, "name": "Same"}, {"id": 1, "name": "Same"}]}]


def save(tmp_path, data, name="answer.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("raw", INVALID_BATCHES)
def test_invalid_batch_rejected_without_connection(raw, monkeypatch, tmp_path):
    original = copy.deepcopy(raw)

    def forbidden():
        pytest.fail("invalid batch opened a connection")

    monkeypatch.setattr(load, "get_db_connection", forbidden)
    with pytest.raises(ValueError):
        transform_igdb_search_results(raw)
    with pytest.raises(ValueError):
        load.load_igdb_file(save(tmp_path, raw))
    assert raw == original


def test_empty_and_malformed_json_without_connection(monkeypatch, tmp_path):
    def forbidden():
        pytest.fail("empty or malformed input opened a connection")

    monkeypatch.setattr(load, "get_db_connection", forbidden)
    assert transform_igdb_search_results({"data": [], "extra": 1}) == []
    assert load.load_igdb_file(save(tmp_path, {"data": []})) == 0
    path = tmp_path / "broken.json"
    path.write_text('{"data":', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load.load_igdb_file(path)


def test_valid_fields_null_collections_and_precedence():
    game = {
        "id": 2147483647, "name": "  Game  ", "first_release_date": 0,
        "game_type": 0, "status": 0, "summary": None,
        "external_games": [
            {"uid": 999, "url": "https://store.steampowered.com/app/42/external"},
            {"uid": 123, "url": "https://twitch.tv/directory/category/game"},
            {"uid": "", "url": "https://gog.com/game/ignored"},
            {"uid": None, "url": None}, {},
        ],
        "websites": [{"url": "https://store.steampowered.com/app/42/website"}, {}],
    }
    original = copy.deepcopy(game)
    record = transform_igdb_search_results({"data": [game], "ignored": True})[0]
    assert game == original
    assert record["igdb_game"]["name"] == "  Game  "
    assert record["igdb_game"]["raw_json"] == original
    assert record["igdb_game"]["first_release_date"] == date(1970, 1, 1)
    assert record["igdb_game"]["game_type_label"] == "main_game"
    assert record["store_links"] == [{
        "igdb_game_id": 2147483647, "store": "steam", "store_game_id": "42",
        "store_url": "https://store.steampowered.com/app/42/website",
    }]
    assert record["twitch_categories"][0]["twitch_game_id"] == "123"
    null_game = {"id": 1, "name": "Nulls", "external_games": None, "websites": None}
    null_record = transform_igdb_search_results({"data": [null_game]})[0]
    assert null_record["store_links"] == null_record["twitch_categories"] == []
    assert null_record["igdb_game"]["raw_json"] == null_game


def linked_game(game_id=1, name="First"):
    return {
        "id": game_id, "name": name, "summary": None,
        "external_games": [{"uid": "twitch-1", "url": "https://twitch.tv/directory/category/game"}],
        "websites": [{"url": "https://store.steampowered.com/app/42/game"}],
    }


def persisted():
    # Fresh connection per read: timestamps are compared across transactions.
    with get_db_connection() as connection:
        return {
            table: connection.execute(
                f"SELECT *, {'created_at' if table == 'igdb_game_store_links' else 'updated_at'} "
                f"FROM {table} ORDER BY 1"
            ).fetchall()
            for table in ("igdb_games", "igdb_game_store_links", "twitch_categories")
        }


def test_replay_preserves_all_values_then_updates_and_retains_links(test_database, tmp_path):
    game = linked_game()
    path = save(tmp_path, {"data": [game]})
    assert load.load_igdb_file(path) == 1
    initial = persisted()
    # Reorder object keys without changing JSONB content.
    reordered = dict(reversed(list(game.items())))
    save(tmp_path, {"data": [reordered]})
    assert load.load_igdb_file(path) == 1
    assert persisted() == initial

    changed = linked_game(name="Changed")
    changed["summary"] = "New summary"
    save(tmp_path, {"data": [changed]})
    assert load.load_igdb_file(path) == 1
    updated = persisted()
    assert updated["igdb_games"][0][-1] > initial["igdb_games"][0][-1]
    assert updated["twitch_categories"][0][-1] > initial["twitch_categories"][0][-1]
    assert updated["igdb_game_store_links"] == initial["igdb_game_store_links"]
    assert updated["igdb_games"][0][1] == "Changed"
    assert updated["twitch_categories"][0][1] == "Changed"

    save(tmp_path, {"data": [{"id": 1, "name": "Changed"}]})
    load.load_igdb_file(path)
    retained = persisted()
    assert retained["igdb_game_store_links"] == updated["igdb_game_store_links"]
    assert retained["twitch_categories"] == updated["twitch_categories"]


def test_remapping_preserves_unique_link_and_created_at(test_database, tmp_path):
    path = save(tmp_path, {"data": [linked_game()]})
    load.load_igdb_file(path)
    initial = persisted()
    remapped = linked_game(2, "Second")
    remapped["websites"][0]["url"] += "/new"
    save(tmp_path, {"data": [remapped]})
    load.load_igdb_file(path)
    updated = persisted()
    assert len(updated["igdb_games"]) == 2
    assert len(updated["igdb_game_store_links"]) == len(updated["twitch_categories"]) == 1
    assert updated["igdb_game_store_links"][0][1] == 2
    assert updated["igdb_game_store_links"][0][-1] == initial["igdb_game_store_links"][0][-1]
    assert updated["twitch_categories"][0][3] == 2
    assert updated["twitch_categories"][0][-1] > initial["twitch_categories"][0][-1]


@pytest.mark.parametrize("helper", ["upsert_igdb_game", "upsert_igdb_game_store_link", "upsert_twitch_category"])
@pytest.mark.parametrize("database_error", [False, True])
def test_write_failure_rolls_back_prior_updates_and_retry_succeeds(
    test_database, tmp_path, monkeypatch, helper, database_error,
):
    committed_path = save(tmp_path, {"data": [linked_game()]}, "committed.json")
    load.load_igdb_file(committed_path)
    initial = persisted()
    second = linked_game(2, "New game")
    second["external_games"][0]["uid"] = "twitch-2"
    second["websites"][0]["url"] = "https://store.steampowered.com/app/43/game"
    retry_path = save(tmp_path, {"data": [linked_game(name="Updated"), second]}, "retry.json")
    original = getattr(load, helper)
    calls = 0

    def fail_after_write(connection, record):
        nonlocal calls
        original(connection, record)
        calls += 1
        if calls == 2:
            if database_error:
                connection.execute("SELECT 1 / 0")
            raise RuntimeError("injected write failure")

    with monkeypatch.context() as patch:
        patch.setattr(load, helper, fail_after_write)
        expected = psycopg.errors.DivisionByZero if database_error else RuntimeError
        with pytest.raises(expected):
            load.load_igdb_file(retry_path)
    assert persisted() == initial
    assert load.load_igdb_file(retry_path) == 2
    successful = persisted()
    assert all(len(rows) == 2 for rows in successful.values())
    assert load.load_igdb_file(retry_path) == 2
    assert persisted() == successful


def test_shared_mapping_keys_replay_and_last_game_precedence(test_database, tmp_path):
    first = linked_game(1, "First")
    second = linked_game(2, "Second")
    second["websites"][0]["url"] += "/second"
    path = save(tmp_path, {"data": [first, second]})
    assert load.load_igdb_file(path) == 2
    initial = persisted()
    assert len(initial["igdb_games"]) == 2
    assert len(initial["igdb_game_store_links"]) == len(initial["twitch_categories"]) == 1
    assert initial["igdb_game_store_links"][0][1] == 2
    assert initial["igdb_game_store_links"][0][4] == second["websites"][0]["url"]
    assert initial["twitch_categories"][0][3] == 2
    assert load.load_igdb_file(path) == 2
    assert persisted() == initial

    # A legitimate precedence change must still remap and advance the Twitch
    # timestamp. Store links retain their original row identity and created_at.
    save(tmp_path, {"data": [second, first]})
    assert load.load_igdb_file(path) == 2
    reversed_rows = persisted()
    assert reversed_rows["igdb_games"] == initial["igdb_games"]
    assert reversed_rows["igdb_game_store_links"][0][1] == 1
    assert reversed_rows["igdb_game_store_links"][0][4] == first["websites"][0]["url"]
    assert reversed_rows["igdb_game_store_links"][0][0] == initial["igdb_game_store_links"][0][0]
    assert reversed_rows["igdb_game_store_links"][0][-1] == initial["igdb_game_store_links"][0][-1]
    assert reversed_rows["twitch_categories"][0][3] == 1
    assert reversed_rows["twitch_categories"][0][-1] > initial["twitch_categories"][0][-1]
    assert load.load_igdb_file(path) == 2
    assert persisted() == reversed_rows

    # Changing a game whose mapping is superseded updates that game's metadata
    # without refreshing the final mapping's timestamp.
    second["name"] = "Second revised"
    save(tmp_path, {"data": [second, first]})
    assert load.load_igdb_file(path) == 2
    revised = persisted()
    assert revised["igdb_game_store_links"] == reversed_rows["igdb_game_store_links"]
    assert revised["twitch_categories"] == reversed_rows["twitch_categories"]
    assert revised["igdb_games"][1][1] == "Second revised"
    assert revised["igdb_games"][1][-1] > reversed_rows["igdb_games"][1][-1]
