"""IGDB bronze validation, timestamp stability and file recovery contracts."""

import copy
import json
from datetime import date

import psycopg
import pytest

from src import load
from src.transform import transform_igdb_search_results


def save_payload(tmp_path, payload):
    path = tmp_path / "igdb.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


INVALID_ENVELOPES = [None, [], "data", 1, {}, {"data": None},
                     {"data": {}}, {"data": "[]"}, {"data": 0}]
INVALID_GAMES = [None, [], "game", {}, {"id": 1}, {"name": "Game"}]
INVALID_GAMES += [{"id": value, "name": "Game"}
                  for value in [None, True, False, 0, -1, 2147483648, "1", 1.0]]
INVALID_GAMES += [{"id": 1, "name": value}
                  for value in [None, 1, True, "", " \t\n"]]
for nested_field in ("external_games", "websites"):
    for invalid_items in ({}, "", 0, False, [None], [1], [[]], ["item"]):
        INVALID_GAMES.append({"id": 1, "name": "Game", nested_field: invalid_items})
    for invalid_url in (1, False, [], {}):
        INVALID_GAMES.append({"id": 1, "name": "Game",
                              nested_field: [{"url": invalid_url}]})
for invalid_uid in (True, False, 1.5, [], {}):
    INVALID_GAMES.append({"id": 1, "name": "Game",
                          "external_games": [{"uid": invalid_uid}]})
INVALID_PAYLOADS = INVALID_ENVELOPES + [
    {"data": [{"id": 99, "name": "Valid first"}, game]}
    for game in INVALID_GAMES
] + [{"data": [{"id": 1, "name": "Game"}] * 2}]


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_invalid_batch_rejected_before_connection(payload, monkeypatch, tmp_path):
    original = copy.deepcopy(payload)

    def forbidden_connection():
        pytest.fail("Invalid batch acquired a database connection")

    monkeypatch.setattr(load, "get_db_connection", forbidden_connection)
    with pytest.raises(ValueError):
        transform_igdb_search_results(payload)
    assert payload == original
    with pytest.raises(ValueError):
        load.load_igdb_file(save_payload(tmp_path, payload))


def test_empty_and_malformed_json_do_not_connect(monkeypatch, tmp_path):
    def forbidden_connection():
        pytest.fail("Empty or malformed file acquired a connection")

    monkeypatch.setattr(load, "get_db_connection", forbidden_connection)
    payload = {"data": [], "metadata": {"ignored": True}}
    assert transform_igdb_search_results(payload) == []
    path = save_payload(tmp_path, payload)
    assert load.load_data("igdb", path) == 0
    path.write_text('{"data": [', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load.load_igdb_file(path)


@pytest.mark.parametrize("value", [None, []])
def test_nullable_collections_and_identifier_boundaries(value):
    game = {"id": 2147483647, "name": "  Verbatim name  ",
            "external_games": value, "websites": value}
    original = copy.deepcopy(game)
    record = transform_igdb_search_results({"data": [game]})[0]
    assert record["igdb_game"]["name"] == game["name"]
    assert record["igdb_game"]["raw_json"] == original
    assert record["store_links"] == record["twitch_categories"] == []
    assert game == original


def test_valid_nested_fields_preserve_precedence_and_raw_json():
    website_url = "https://store.steampowered.com/app/730/website"
    game = {"id": 1, "name": " Game ", "first_release_date": 0,
            "game_type": 0, "status": 4,
            "external_games": [
                {"uid": "wrong", "url": "https://store.steampowered.com/app/730/external"},
                {"uid": 55, "url": "https://twitch.tv/directory/game/game"},
                {"uid": 9, "url": "https://www.gog.com/game/game"},
                {}, {"url": None, "uid": None}, {"url": "", "uid": ""},
                {"uid": "ignored", "url": "https://example.com"},
                {"uid": 0, "url": "https://www.gog.com/game/empty"}],
            "websites": [{"url": website_url}, {}, {"url": None}]}
    original = copy.deepcopy(game)
    record = transform_igdb_search_results({"data": [game], "ignored": 3})[0]
    assert set(record) == {"igdb_game", "store_links", "twitch_categories"}
    assert record["igdb_game"]["raw_json"] == original
    assert record["igdb_game"]["first_release_date"] == date(1970, 1, 1)
    assert record["igdb_game"]["game_type_label"] == "main_game"
    assert record["igdb_game"]["status_label"] == "early_access"
    assert record["store_links"] == [
        {"igdb_game_id": 1, "store": "steam", "store_game_id": "730",
         "store_url": website_url},
        {"igdb_game_id": 1, "store": "gog", "store_game_id": "9",
         "store_url": "https://www.gog.com/game/game"}]
    assert record["twitch_categories"][0]["twitch_game_id"] == "55"
    assert game == original


def linked_game(game_id=1, name="Game"):
    return {"id": game_id, "name": name, "summary": None,
            "external_games": [
                {"uid": "category", "url": "https://twitch.tv/directory/game/game"}],
            "websites": [{"url": "https://store.steampowered.com/app/730/game"}]}


@pytest.mark.parametrize("website_urls,expected_ids", [
    (["https://store.steampowered.com/app/740/website"], ["730", "740"]),
    (["https://store.steampowered.com/app/730/website"], ["730"]),
    (["https://store.steampowered.com/app/740/first",
      "https://store.steampowered.com/app/750/second"], ["730", "740", "750"]),
    (["https://store.steampowered.com/app/740/first",
      "https://store.steampowered.com/app/730/replacement",
      "https://store.steampowered.com/app/740/replacement"], ["730", "740"]),
    ([None, "https://example.com", "https://store.steampowered.com/app/bad"],
     ["730"]),
])
def test_steam_website_precedence_with_conflicting_ids(website_urls, expected_ids):
    game = linked_game()
    game["external_games"].extend([
        {"uid": "wrong", "url": "https://store.steampowered.com/app/730/external"},
        {"uid": "9", "url": "https://www.gog.com/game/game"}])
    game["websites"] = [{"url": url} for url in website_urls]
    original = copy.deepcopy(game)
    record = transform_igdb_search_results({"data": [game]})[0]
    steam_links = [link for link in record["store_links"] if link["store"] == "steam"]
    assert [link["store_game_id"] for link in steam_links] == expected_ids
    expected_urls = {"730": game["external_games"][1]["url"]}
    for url in website_urls:
        if url and url.rsplit("/", 2)[-2].isdigit():
            expected_urls[url.rsplit("/", 2)[-2]] = url
    assert {link["store_game_id"]: link["store_url"] for link in steam_links} == expected_urls
    assert [link["store_game_id"] for link in record["store_links"]
            if link["store"] == "gog"] == ["9"]
    assert record["twitch_categories"][0]["twitch_game_id"] == "category"
    assert record["igdb_game"]["raw_json"] == original
    assert game == original


def test_conflicting_steam_website_is_persisted_and_replayed(test_database, tmp_path):
    game = linked_game()
    game["external_games"].append(
        {"uid": "wrong", "url": "https://store.steampowered.com/app/720/external"})
    path = save_payload(tmp_path, {"data": [game]})
    assert load.load_igdb_file(path) == 1
    with load.get_db_connection() as connection:
        assert connection.execute(
            "SELECT store_game_id, store_url FROM igdb_game_store_links "
            "WHERE store='steam' ORDER BY store_game_id"
        ).fetchall() == [("720", game["external_games"][1]["url"]),
                         ("730", game["websites"][0]["url"])]
    first = database_rows()
    assert load.load_igdb_file(path) == 1
    assert database_rows() == first

    # A later website adds its new mapping without deleting committed links.
    game["websites"][0]["url"] = "https://store.steampowered.com/app/740/website"
    assert load.load_igdb_file(save_payload(tmp_path, {"data": [game]})) == 1
    with load.get_db_connection() as connection:
        assert connection.execute(
            "SELECT store_game_id FROM igdb_game_store_links ORDER BY store_game_id"
        ).fetchall() == [("720",), ("730",), ("740",)]


def database_rows():
    """Read all persisted values, including timestamps, in a fresh transaction."""
    with load.get_db_connection() as connection:
        return {
            table: connection.execute(
                f"SELECT *, {timestamp} FROM {table} ORDER BY 1"
            ).fetchall()
            for table, timestamp in (("igdb_games", "updated_at"),
                                     ("igdb_game_store_links", "created_at"),
                                     ("twitch_categories", "updated_at"))
        }


def test_replay_and_changes_across_transactions(test_database, tmp_path):
    game = linked_game()
    path = save_payload(tmp_path, {"data": [game]})
    assert load.load_igdb_file(path) == 1
    first = database_rows()
    assert [len(rows) for rows in first.values()] == [1, 1, 1]
    reordered = dict(reversed(list(game.items())))
    assert load.load_igdb_file(save_payload(tmp_path, {"data": [reordered]})) == 1
    assert database_rows() == first

    game["summary"] = "Changed from null"
    load.load_igdb_file(save_payload(tmp_path, {"data": [game]}))
    second = database_rows()
    assert second["igdb_games"][0][-1] > first["igdb_games"][0][-1]
    assert second["twitch_categories"] == first["twitch_categories"]
    assert second["igdb_game_store_links"] == first["igdb_game_store_links"]
    game["summary"] = None
    game["name"] = "Renamed"
    load.load_igdb_file(save_payload(tmp_path, {"data": [game]}))
    third = database_rows()
    assert third["igdb_games"][0][1] == "Renamed"
    assert third["igdb_games"][0][3] is None
    assert third["igdb_games"][0][-1] > second["igdb_games"][0][-1]
    assert third["twitch_categories"][0][1] == "Renamed"
    assert third["twitch_categories"][0][-1] > second["twitch_categories"][0][-1]
    assert third["igdb_game_store_links"] == first["igdb_game_store_links"]

    # Missing links in a later answer leave previous mappings intact.
    load.load_igdb_file(save_payload(tmp_path, {"data": [{"id": 1, "name": "Renamed"}]}))
    fourth = database_rows()
    assert fourth["igdb_game_store_links"] == third["igdb_game_store_links"]
    assert fourth["twitch_categories"] == third["twitch_categories"]


def test_store_and_category_remapping(test_database, tmp_path):
    load.load_igdb_file(save_payload(tmp_path, {"data": [linked_game()]}))
    first = database_rows()
    remapped = linked_game(2, "Other game")
    remapped["websites"][0]["url"] += "/new"
    load.load_igdb_file(save_payload(tmp_path, {"data": [remapped]}))
    second = database_rows()
    assert [len(rows) for rows in second.values()] == [2, 1, 1]
    assert second["igdb_game_store_links"][0][1] == 2
    assert second["igdb_game_store_links"][0][4].endswith("/new")
    assert second["igdb_game_store_links"][0][-1] == first["igdb_game_store_links"][0][-1]
    assert second["twitch_categories"][0][3] == 2
    assert second["twitch_categories"][0][-1] > first["twitch_categories"][0][-1]
    load.load_igdb_file(save_payload(tmp_path, {"data": [remapped]}))
    assert database_rows() == second


@pytest.mark.parametrize("helper_name", [
    "upsert_igdb_game", "upsert_igdb_game_store_link", "upsert_twitch_category"])
def test_write_failure_rolls_back_entire_file_and_saved_retry_succeeds(
    test_database, tmp_path, monkeypatch, helper_name
):
    load.load_igdb_file(save_payload(tmp_path, {"data": [linked_game()]}))
    prior = database_rows()
    batch = [linked_game(1, "Updated prior row"), linked_game(2, "New row")]
    batch[1]["external_games"][0]["uid"] = "new-category"
    path = save_payload(tmp_path, {"data": batch})
    original = getattr(load, helper_name)
    calls = 0

    def fail_after_write(connection, record):
        nonlocal calls
        original(connection, record)
        calls += 1
        if calls == 2:
            # A real SQL error aborts the transaction after earlier writes.
            connection.execute("SELECT 1 / 0")

    with monkeypatch.context() as patch:
        patch.setattr(load, helper_name, fail_after_write)
        with pytest.raises(psycopg.errors.DivisionByZero):
            load.load_igdb_file(path)
    assert calls == 2
    assert database_rows() == prior
    assert load.load_igdb_file(path) == 2
    recovered = database_rows()
    assert [len(rows) for rows in recovered.values()] == [2, 1, 2]
    assert recovered["igdb_games"][0][1] == "Updated prior row"
    assert recovered["igdb_game_store_links"][0][1] == 2
    assert recovered["twitch_categories"][0][3] == 1
    assert recovered["twitch_categories"][1][3] == 2
    assert load.load_igdb_file(path) == 2
    assert database_rows() == recovered


def test_shared_category_keeps_last_game_precedence_on_replay(test_database, tmp_path):
    path = save_payload(tmp_path, {"data": [linked_game(1), linked_game(2, "Winner")]})
    assert load.load_igdb_file(path) == 2
    first = database_rows()
    assert [len(rows) for rows in first.values()] == [2, 1, 1]
    assert first["twitch_categories"][0][3] == 2
    assert first["igdb_game_store_links"][0][1] == 2
    assert load.load_igdb_file(path) == 2
    assert database_rows() == first


@pytest.mark.parametrize("field,value", [
    ("is_game", False), ("igdb_game_id", 1), ("mapping_method", "manual"),
    ("mapping_confidence", 0.5), ("notes", "Reviewed")])
def test_category_helper_null_safe_updates(test_database, field, value):
    record = transform_igdb_search_results({"data": [linked_game()]})[0]
    category = record["twitch_categories"][0].copy()
    category[field] = None
    with load.get_db_connection() as connection:
        load.upsert_igdb_game(connection, record["igdb_game"])
        load.upsert_twitch_category(connection, category)
    first = database_rows()["twitch_categories"]
    with load.get_db_connection() as connection:
        load.upsert_twitch_category(connection, category)
    assert database_rows()["twitch_categories"] == first

    category[field] = value
    with load.get_db_connection() as connection:
        load.upsert_twitch_category(connection, category)
    second = database_rows()["twitch_categories"]
    assert second[0][-1] > first[0][-1]
    with load.get_db_connection() as connection:
        assert connection.execute(
            f"SELECT {field} FROM twitch_categories"
        ).fetchone()[0] == value
    category[field] = None
    with load.get_db_connection() as connection:
        load.upsert_twitch_category(connection, category)
    third = database_rows()["twitch_categories"]
    assert third[0][-1] > second[0][-1]
    with load.get_db_connection() as connection:
        assert connection.execute(
            f"SELECT {field} FROM twitch_categories"
        ).fetchone()[0] is None
    with load.get_db_connection() as connection:
        load.upsert_twitch_category(connection, category)
    assert database_rows()["twitch_categories"] == third
