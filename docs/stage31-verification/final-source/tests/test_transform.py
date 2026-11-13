from datetime import datetime

import pytest

from src import extract_steam_store
from src.transform import (
    IGDB_GAME_TYPES,
    IGDB_STATUSES,
    STEAM_STORE_ENVELOPE_VERSION,
    calculate_review_score,
    detect_store_from_url,
    extract_igdb_store_links,
    extract_igdb_twitch_categories,
    extract_steam_appid_from_url,
    parse_steam_store_envelope,
    parse_twitch_fetched_at,
    split_comma_separated_values,
    to_int,
    transform_igdb_game,
    transform_igdb_search_results,
    transform_steam_store_game,
    transform_steamspy_game,
    transform_twitch_games_lookup,
    transform_twitch_streams,
    unix_timestamp_to_date,
)


def test_to_int_converts_string_number():
    assert to_int("1999") == 1999


def test_to_int_converts_integer():
    assert to_int(500) == 500


def test_to_int_returns_default_for_invalid_value():
    assert to_int("not-a-number") == 0


def test_to_int_returns_custom_default_for_none():
    assert to_int(None, default=-1) == -1


def test_calculate_review_score():
    assert calculate_review_score(80, 20) == 0.8


def test_calculate_review_score_returns_none_when_no_reviews():
    assert calculate_review_score(0, 0) is None


def test_split_comma_separated_values():
    result = split_comma_separated_values("Action, Free To Play, RPG")

    assert result == ["Action", "Free To Play", "RPG"]


def test_split_comma_separated_values_returns_empty_list_for_empty_value():
    assert split_comma_separated_values("") == []


def test_transform_steamspy_game():
    raw_data = {
        "appid": 730,
        "name": "Counter-Strike: Global Offensive",
        "developer": "Valve",
        "publisher": "Valve",
        "positive": 7642084,
        "negative": 1173003,
        "owners": "100,000,000 .. 200,000,000",
        "price": "0",
        "initialprice": "0",
        "discount": "0",
        "ccu": 1013936,
        "genre": "Action, Free To Play",
    }

    result = transform_steamspy_game(raw_data)

    assert result["source"] == "steamspy"

    assert result["game"] == {
        "appid": 730,
        "name": "Counter-Strike: Global Offensive",
        "developer": "Valve",
        "publisher": "Valve",
        # price == "0" does not distinguish free-to-play from
        # unreleased/delisted, so SteamSpy alone leaves is_free unknown --
        # see test_transform_steamspy_is_free_* below.
        "is_free": None,
        "release_date": None,
        "header_image": None,
    }

    assert result["snapshot"] == {
        "appid": 730,
        "positive": 7642084,
        "negative": 1173003,
        "total_reviews": 8815087,
        "review_score": 0.8669,
        "owners": "100,000,000 .. 200,000,000",
        "price": 0,
        "initialprice": 0,
        "discount": 0,
        "ccu": 1013936,
    }

    assert result["genres"] == ["Action", "Free To Play"]


def test_transform_steamspy_is_free_unknown_when_price_is_zero():
    """
    SteamSpy sends price == "0" both for genuinely free-to-play games and
    for unreleased/delisted apps that have no price yet. The source cannot
    tell those apart, so is_free must come out unknown (None), not True.
    """

    raw_data = {
        "appid": 12345,
        "name": "Some Unreleased Game",
        "price": "0",
    }

    result = transform_steamspy_game(raw_data)

    assert result["game"]["is_free"] is None


def test_transform_steamspy_is_free_false_when_price_positive():
    """
    price > 0 does reliably mean "not free" -- that half of the signal is
    kept even though price == 0 is not.
    """

    raw_data = {
        "appid": 730,
        "name": "Counter-Strike: Global Offensive",
        "price": "1999",
    }

    result = transform_steamspy_game(raw_data)

    assert result["game"]["is_free"] is False


def test_transform_steamspy_is_free_unknown_when_price_missing():
    raw_data = {
        "appid": 730,
        "name": "Counter-Strike: Global Offensive",
    }

    result = transform_steamspy_game(raw_data)

    assert result["game"]["is_free"] is None


def test_transform_steam_store_game():
    raw_response = {
        "730": {
            "success": True,
            "data": {
                "steam_appid": 730,
                "name": "Counter-Strike 2",
                "developers": ["Valve"],
                "publishers": ["Valve"],
                "is_free": True,
                "release_date": {
                    "coming_soon": False,
                    "date": "21 Aug, 2012",
                },
                "header_image": "https://example.com/header.jpg",
                "genres": [
                    {"id": "1", "description": "Action"},
                    {"id": "37", "description": "Free To Play"},
                ],
            },
        }
    }

    result = transform_steam_store_game(raw_response)

    assert result["source"] == "steam_store"

    assert result["game"] == {
        "appid": 730,
        "name": "Counter-Strike 2",
        "developer": "Valve",
        "publisher": "Valve",
        "is_free": True,
        "release_date": "21 Aug, 2012",
        "header_image": "https://example.com/header.jpg",
    }

    assert result["snapshot"] is None
    assert result["genres"] == ["Action", "Free To Play"]


def test_transform_steam_store_game_returns_none_if_response_is_empty():
    assert transform_steam_store_game({}) is None


def test_parse_steam_store_envelope_reads_current_envelope_as_is():
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
        "body": {"730": {"success": True, "data": {"steam_appid": 730}}},
    }

    assert parse_steam_store_envelope(envelope) == envelope


def test_parse_steam_store_envelope_reads_legacy_file_as_ok():
    """
    Legacy bronze files (written before this fix) have no "envelope" key
    and only ever exist for successful responses -- the old extractor
    returned before saving anything on a failure. They must be read as
    outcome "ok" with the whole file as body, unchanged, so the ~3 148
    files already on disk keep loading exactly as before.
    """

    legacy_body = {
        "730": {
            "success": True,
            "data": {"steam_appid": 730, "name": "Counter-Strike 2"},
        }
    }

    envelope = parse_steam_store_envelope(legacy_body)

    assert envelope["envelope"] is None
    assert envelope["outcome"] == "ok"
    assert envelope["fetched_at"] is None
    assert envelope["body"] == legacy_body


def test_steam_store_envelope_version_constant_is_shared_with_extractor():
    """
    The writer's constant (extract_steam_store.ENVELOPE_VERSION) and the
    reader's constant (transform.STEAM_STORE_ENVELOPE_VERSION) must be the
    exact same object, not two integers that merely happen to be equal
    today -- bumping one without the other is what makes an unrecognized
    version silently degrade into "legacy" instead of failing loudly.
    """

    assert STEAM_STORE_ENVELOPE_VERSION is extract_steam_store.ENVELOPE_VERSION


def test_parse_steam_store_envelope_raises_for_unknown_version():
    """
    An "envelope" key present with a value this reader does not
    recognize must fail loudly, not be read as legacy "ok". Silently
    degrading would read every outcome in the file -- including a real
    refusal or transport failure -- as a fabricated success.
    """

    envelope = {
        "envelope": STEAM_STORE_ENVELOPE_VERSION + 1,
        "source": "steam_store",
        "outcome": "ok",
        "appid": 730,
        "body": {"730": {"success": True, "data": {"steam_appid": 730}}},
    }

    with pytest.raises(ValueError, match="Unknown Steam Store envelope version"):
        parse_steam_store_envelope(envelope)


def test_transform_steam_store_game_returns_none_if_success_is_false():
    raw_response = {
        "730": {
            "success": False,
        }
    }

    assert transform_steam_store_game(raw_response) is None

def test_transform_twitch_streams_aggregates_by_game():
    raw_data = {
        "source": "twitch",
        "request": "streams",
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
                "viewer_count": 250,
            },
            {
                "game_id": "21779",
                "game_name": "League of Legends",
                "viewer_count": 500,
            },
        ],
    }

    result = transform_twitch_streams(raw_data)

    assert len(result) == 2

    expected_sample_time = datetime(2026, 5, 13, 12, 28, 52, 40293)

    result_by_game_id = {
        game["twitch_game_id"]: game
        for game in result
    }

    assert result_by_game_id["32399"] == {
        "twitch_game_id": "32399",
        "twitch_game_name": "Counter-Strike",
        "viewer_count": 350,
        "stream_count": 2,
        "sample_time": expected_sample_time,
    }

    assert result_by_game_id["21779"] == {
        "twitch_game_id": "21779",
        "twitch_game_name": "League of Legends",
        "viewer_count": 500,
        "stream_count": 1,
        "sample_time": expected_sample_time,
    }


def test_transform_twitch_streams_raises_when_fetched_at_missing():
    """
    Test that a raw Twitch file without fetched_at fails loudly instead of
    silently using the insert clock as the observation time.
    """

    raw_data = {
        "data": [
            {
                "game_id": "32399",
                "game_name": "Counter-Strike",
                "viewer_count": 100,
            },
        ],
    }

    with pytest.raises(ValueError, match="fetched_at"):
        transform_twitch_streams(raw_data)


def test_transform_twitch_streams_raises_when_fetched_at_unparseable():
    raw_data = {
        "fetched_at": "not-a-timestamp",
        "data": [],
    }

    with pytest.raises(ValueError, match="fetched_at"):
        transform_twitch_streams(raw_data)


def test_parse_twitch_fetched_at_converts_offset_aware_to_naive_utc():
    raw_data = {"fetched_at": "2026-05-13T12:28:52.040293+00:00"}

    result = parse_twitch_fetched_at(raw_data)

    assert result == datetime(2026, 5, 13, 12, 28, 52, 40293)
    assert result.tzinfo is None


def test_transform_twitch_games_lookup_converts_igdb_id():
    raw_data = {
        "source": "twitch",
        "request": "games_lookup",
        "data": [
            {
                "id": "32399",
                "name": "Counter-Strike",
                "box_art_url": "https://example.com/box.jpg",
                "igdb_id": "115",
            }
        ],
    }

    result = transform_twitch_games_lookup(raw_data)

    assert result == [
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
            "box_art_url": "https://example.com/box.jpg",
            "igdb_id": 115,
            "source": "games_lookup",
        }
    ]


def test_transform_twitch_games_lookup_sets_missing_igdb_id_to_none():
    raw_data = {
        "data": [
            {
                "id": "21779",
                "name": "League of Legends",
                "box_art_url": "https://example.com/lol.jpg",
            },
            {
                "id": "516575",
                "name": "VALORANT",
                "box_art_url": "https://example.com/valorant.jpg",
                "igdb_id": "",
            },
        ],
    }

    result = transform_twitch_games_lookup(raw_data)

    assert result[0]["igdb_id"] is None
    assert result[1]["igdb_id"] is None


def test_transform_twitch_games_lookup_returns_empty_list_for_empty_data():
    assert transform_twitch_games_lookup({"data": []}) == []


def test_transform_twitch_games_lookup_skips_rows_missing_id_or_name():
    raw_data = {
        "data": [
            {
                "name": "Missing ID",
                "igdb_id": "1",
            },
            {
                "id": "123",
                "igdb_id": "2",
            },
            {
                "id": "456",
                "name": "Valid Game",
                "igdb_id": "3",
            },
        ],
    }

    result = transform_twitch_games_lookup(raw_data)

    assert result == [
        {
            "twitch_game_id": "456",
            "twitch_game_name": "Valid Game",
            "box_art_url": None,
            "igdb_id": 3,
            "source": "games_lookup",
        }
    ]


def test_unix_timestamp_to_date():
    result = unix_timestamp_to_date(0)

    assert result.isoformat() == "1970-01-01"


def test_unix_timestamp_to_date_returns_none_for_missing_value():
    assert unix_timestamp_to_date(None) is None


def test_transform_igdb_game():
    raw_game = {
        "id": 123,
        "name": "Counter-Strike 2",
        "slug": "counter-strike-2",
        "summary": "Tactical shooter.",
        "url": "https://www.igdb.com/games/counter-strike-2",
        "first_release_date": 0,
        "rating": 85.5,
        "rating_count": 10,
        "aggregated_rating": 90.0,
        "aggregated_rating_count": 5,
        "total_rating": 87.0,
        "total_rating_count": 15,
        "hypes": 100,
        "follows": 200,
        "game_type": 0,
        "status": 0,
    }

    result = transform_igdb_game(raw_game)

    assert result["igdb_game_id"] == 123
    assert result["name"] == "Counter-Strike 2"
    assert result["first_release_date"].isoformat() == "1970-01-01"
    assert result["raw_json"] == raw_game


def test_detect_store_from_url():
    assert detect_store_from_url("https://store.steampowered.com/app/730") == "steam"
    assert detect_store_from_url("https://store.epicgames.com/example") == "epic"
    assert detect_store_from_url("https://www.gog.com/game/example") == "gog"
    assert detect_store_from_url(None) is None


def test_extract_steam_appid_from_url():
    result = extract_steam_appid_from_url(
        "https://store.steampowered.com/app/730/CounterStrike"
    )

    assert result == "730"


def test_extract_igdb_store_links_deduplicates_steam_links():
    raw_game = {
        "id": 123,
        "name": "Counter-Strike 2",
        "external_games": [
            {
                "uid": "old-id",
                "url": "https://store.steampowered.com/app/730/CounterStrike",
            },
        ],
        "websites": [
            {
                "url": "https://store.steampowered.com/app/730/CounterStrike",
            },
        ],
    }

    result = extract_igdb_store_links(raw_game)

    assert result == [
        {
            "igdb_game_id": 123,
            "store": "steam",
            "store_game_id": "730",
            "store_url": "https://store.steampowered.com/app/730/CounterStrike",
        }
    ]


def test_extract_igdb_twitch_categories():
    raw_game = {
        "id": 123,
        "name": "Counter-Strike 2",
        "external_games": [
            {
                "uid": "32399",
                "url": "https://www.twitch.tv/directory/category/counter-strike",
            },
        ],
    }

    result = extract_igdb_twitch_categories(raw_game)

    assert result == [
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike 2",
            "is_game": True,
            "igdb_game_id": 123,
            "mapping_status": "mapped",
            "mapping_method": "igdb_external_game",
            "mapping_confidence": 1.0,
            "notes": "Mapped from IGDB external_games Twitch UID.",
        }
    ]


def test_transform_igdb_search_results():
    raw_data = {
        "data": [
            {
                "id": 123,
                "name": "Counter-Strike 2",
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

    result = transform_igdb_search_results(raw_data)

    assert len(result) == 1
    assert result[0]["igdb_game"]["igdb_game_id"] == 123
    assert result[0]["store_links"][0]["store_game_id"] == "730"
    assert result[0]["twitch_categories"][0]["twitch_game_id"] == "32399"


def test_transform_igdb_game_decodes_known_game_type():
    """
    Test that a known game_type integer is decoded to its label.
    """

    game = {
        "id": 1,
        "name": "Some DLC",
        "game_type": 1,
        "status": 0,
    }

    result = transform_igdb_game(game)

    assert result["game_type"] == 1
    assert result["game_type_label"] == "dlc_addon"
    assert result["status"] == 0
    assert result["status_label"] == "released"


def test_transform_igdb_game_decodes_known_status():
    """
    Test several known status integers map to the correct label.
    """

    for status_int, expected_label in [
        (4, "early_access"),
        (6, "cancelled"),
        (8, "delisted"),
    ]:
        game = {"id": 1, "name": "Game", "game_type": 0, "status": status_int}
        result = transform_igdb_game(game)
        assert result["status_label"] == expected_label, (
            f"status {status_int} should decode to {expected_label!r}"
        )


def test_transform_igdb_game_labels_none_when_fields_absent():
    """
    Test that missing game_type and status produce None labels.
    """

    game = {"id": 1, "name": "Game"}

    result = transform_igdb_game(game)

    assert result["game_type"] is None
    assert result["game_type_label"] is None
    assert result["status"] is None
    assert result["status_label"] is None


def test_transform_igdb_game_labels_none_for_unknown_integer():
    """
    Test that an integer not present in the enum maps produces None label.
    """

    game = {"id": 1, "name": "Game", "game_type": 999, "status": 999}

    result = transform_igdb_game(game)

    assert result["game_type"] == 999
    assert result["game_type_label"] is None
    assert result["status"] == 999
    assert result["status_label"] is None


def test_igdb_game_types_and_statuses_are_complete():
    """
    Sanity-check that both enum dicts are non-empty and contain expected keys.
    """

    assert 0 in IGDB_GAME_TYPES
    assert IGDB_GAME_TYPES[0] == "main_game"

    assert 0 in IGDB_STATUSES
    assert IGDB_STATUSES[0] == "released"

