from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.extract_steam_store import ENVELOPE_VERSION as STEAM_STORE_ENVELOPE_VERSION


# IGDB game_type enum (integer -> label)
IGDB_GAME_TYPES: dict[int, str] = {
    0: "main_game",
    1: "dlc_addon",
    2: "expansion",
    3: "bundle",
    4: "standalone_expansion",
    5: "mod",
    6: "episode",
    7: "season",
    8: "remake",
    9: "remaster",
    10: "expanded_game",
    11: "port",
    12: "fork",
    13: "pack",
    14: "update",
}

# IGDB status enum (integer -> label)
IGDB_STATUSES: dict[int, str] = {
    0: "released",
    2: "alpha",
    3: "beta",
    4: "early_access",
    5: "offline",
    6: "cancelled",
    7: "rumored",
    8: "delisted",
}


def to_int(value: Any, default: int = 0) -> int:
    """
    Convert a value to integer.

    Some APIs return numbers as strings.
    If conversion fails, return the default value.
    """

    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def calculate_review_score(positive: int, negative: int) -> float | None:
    """
    Calculate review score as positive / total_reviews.

    Returns None if there are no reviews.
    """

    total_reviews = positive + negative

    if total_reviews == 0:
        return None

    return round(positive / total_reviews, 4)


def split_comma_separated_values(value: str | None) -> list[str]:
    """
    Split a comma-separated string into a clean list.

    Example:
    'Action, Free To Play' -> ['Action', 'Free To Play']
    """

    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def transform_steamspy_game(data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Transform one raw SteamSpy game object into clean records.

    Used for SteamSpy responses like:
    - all
    - top100owned
    - top100in2weeks
    - appdetails

    Returns:
    - game data for the games table
    - snapshot data for the game_snapshots table
    - genre names for genres/game_genres
    """

    appid = to_int(data.get("appid"))

    if appid <= 0:
        return None

    positive = to_int(data.get("positive"))
    negative = to_int(data.get("negative"))

    total_reviews = positive + negative
    review_score = calculate_review_score(positive, negative)

    raw_price = data.get("price")
    price = to_int(raw_price)

    initialprice = to_int(data.get("initialprice"))
    discount = to_int(data.get("discount"))
    ccu = to_int(data.get("ccu"))

    # SteamSpy sends "price": "0" both for genuinely free-to-play games and
    # for unreleased/delisted apps that have no price yet -- the source
    # itself cannot tell those apart, so price == 0 is recorded as unknown
    # rather than guessed as free. price > 0 does reliably mean "not free",
    # so that half of the signal is kept. Missing price entirely is also
    # unknown; Steam Store metadata fills is_free with a confirmed value
    # later, in insert_game's steam_store branch.
    if raw_price is None:
        is_free = None
    elif price > 0:
        is_free = False
    else:
        is_free = None

    game = {
        "appid": appid,
        "name": data.get("name"),
        "developer": data.get("developer"),
        "publisher": data.get("publisher"),
        "is_free": is_free,
        "release_date": None,
        "header_image": None,
    }

    snapshot = {
        "appid": appid,
        "positive": positive,
        "negative": negative,
        "total_reviews": total_reviews,
        "review_score": review_score,
        "owners": data.get("owners"),
        "price": price,
        "initialprice": initialprice,
        "discount": discount,
        "ccu": ccu,
    }

    genres = split_comma_separated_values(data.get("genre"))

    return {
        "source": "steamspy",
        "game": game,
        "snapshot": snapshot,
        "genres": genres,
    }


def parse_steam_store_envelope(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a Steam Store bronze file into a uniform envelope shape.

    Two shapes exist on disk:

    - Envelope files (envelope == STEAM_STORE_ENVELOPE_VERSION), written
      by extract_steam_store.py's fetch_appdetails for every outcome:
      "ok", "refused", "not_found", "redirected", "transport_error".
      STEAM_STORE_ENVELOPE_VERSION here is imported from
      extract_steam_store.ENVELOPE_VERSION rather than declared again, so
      the writer's constant and the reader's constant cannot drift apart
      -- a version bump in one file that is not reflected in the other is
      exactly the failure mode the next rule guards against.
    - Legacy files (no "envelope" key) -- the ~3 148 files on disk from
      before this fix, when the extractor returned before saving anything
      on a failure. Every legacy file therefore represents a successful
      response by construction; there is no legacy "refused" or
      "not_found" file to normalize. Legacy files are read as outcome
      "ok", fetched_at unknown (the file does not say when it was
      fetched), with the whole file as "body" -- exactly the shape
      transform_steam_store_game already expects.

    A third case is not tolerated: a file that carries an "envelope" key
    whose value is neither missing nor the version this reader knows.
    "envelope" is an explicit version, not something to infer from which
    keys happen to be present, so an unrecognized version must fail
    loudly here rather than being read as a legacy "ok" -- silently
    degrading would read every outcome in a whole run (including real
    refusals and transport failures) as a fabricated success.

    Old files are read as-is and never rewritten; this function is the
    compatibility layer, not a migration of the files themselves.
    """

    if not isinstance(raw_data, dict) or "envelope" not in raw_data:
        return {
            "envelope": None,
            "source": "steam_store",
            "outcome": "ok",
            "appid": None,
            "request": None,
            "url": None,
            "fetched_at": None,
            "http_status": None,
            "error": None,
            "body": raw_data,
        }

    envelope_version = raw_data["envelope"]

    if envelope_version != STEAM_STORE_ENVELOPE_VERSION:
        raise ValueError(
            f"Unknown Steam Store envelope version {envelope_version!r}; "
            f"this reader only understands {STEAM_STORE_ENVELOPE_VERSION!r} "
            "or no 'envelope' key at all (legacy). Update "
            "parse_steam_store_envelope to handle the new shape before "
            "reading files written with it -- refusing to guess is safer "
            "than silently reading a whole run's outcomes as fabricated "
            "'ok' results."
        )

    return raw_data


def transform_steam_store_game(raw_response: dict[str, Any]) -> dict[str, Any] | None:
    """
    Transform one raw Steam Store appdetails response into clean records.

    Steam Store appdetails usually has this structure:
    {
        "730": {
            "success": true,
            "data": {
                "steam_appid": 730,
                "name": "Counter-Strike 2",
                ...
            }
        }
    }

    Returns:
    - game data for the games table
    - genre names for genres/game_genres

    It does not return snapshot data because Steam Store does not provide
    SteamSpy-style metrics like positive, negative, owners, or ccu.
    """

    if not raw_response:
        return None

    app_wrapper = next(iter(raw_response.values()))

    if not app_wrapper.get("success"):
        return None

    data = app_wrapper.get("data", {})

    appid = to_int(data.get("steam_appid"))

    if appid <= 0:
        return None

    release_date_data = data.get("release_date") or {}
    release_date = release_date_data.get("date")

    developers = data.get("developers") or []
    publishers = data.get("publishers") or []

    developer = ", ".join(developers) if developers else None
    publisher = ", ".join(publishers) if publishers else None

    genres = [
        genre.get("description")
        for genre in data.get("genres", [])
        if genre.get("description")
    ]

    game = {
        "appid": appid,
        "name": data.get("name"),
        "developer": developer,
        "publisher": publisher,
        "is_free": data.get("is_free"),
        "release_date": release_date,
        "header_image": data.get("header_image"),
    }

    return {
        "source": "steam_store",
        "game": game,
        "snapshot": None,
        "genres": genres,
    }


# Fixed messages for the two envelope outcomes that do not carry their own
# error text (fetch_appdetails only fills "error" for transport_error).
# refused and not_found used to collapse into the same free-text string in
# steam_store_last_error; keeping them as distinct constants is what keeps
# them apart in the column.
STEAM_STORE_OUTCOME_MESSAGES = {
    "refused": "Steam Store returned success=false",
    "not_found": "No Steam Store response wrapper found",
}



@dataclass(frozen=True)
class _SteamStoreLoad:
    """Prepared metadata and optional mark, executed in that order by the loader."""

    outcome: str
    record: dict[str, Any] | None = None
    fetched_at: str | None = None
    mark: dict[str, Any] | None = None


def _prepare_steam_store_ok(envelope: dict[str, Any], file_path: Path) -> _SteamStoreLoad:
    record = transform_steam_store_game(envelope["body"])
    if record is not None:
        return _SteamStoreLoad("ok", record, envelope.get("fetched_at"))

    appid = envelope.get("appid")
    if appid:
        return _SteamStoreLoad("refused", mark={
            "appid": appid,
            "outcome": "refused",
            "error_message": "ok envelope did not yield a parsable game",
            "fetched_at": envelope.get("fetched_at"),
            "is_replay": True,
        })

    raise ValueError(
        f"Legacy Steam Store file {file_path} was read as outcome "
        "'ok' (the unconditional legacy fallback) but its body did "
        "not yield a parsable game -- most likely an embedded "
        "success: false that the legacy shape cannot distinguish "
        "from a real ok. Refusing to silently drop it."
    )


def _prepare_steam_store_redirected(
    envelope: dict[str, Any], appid: int,
) -> _SteamStoreLoad:
    redirect_to = envelope.get("redirect_to")
    record = transform_steam_store_game(envelope["body"])
    fetched_at = envelope.get("fetched_at")
    return _SteamStoreLoad("redirected", record, fetched_at, {
        "appid": appid,
        "outcome": "redirected",
        "error_message": f"Steam Store redirected appid {appid} to {redirect_to}",
        "redirect_to": redirect_to,
        "fetched_at": fetched_at,
        "is_replay": True,
    })


def _prepare_steam_store_load(envelope: dict[str, Any], file_path: Path) -> _SteamStoreLoad:
    """Interpret outcomes without database effects or additional input validation."""

    outcome = envelope["outcome"]
    if outcome == "ok":
        return _prepare_steam_store_ok(envelope, file_path)

    appid = envelope.get("appid")
    if not appid:
        return _SteamStoreLoad(outcome)
    if outcome == "redirected":
        return _prepare_steam_store_redirected(envelope, appid)

    if outcome == "transport_error":
        message = envelope.get("error") or "Steam Store transport error"
    else:
        message = STEAM_STORE_OUTCOME_MESSAGES.get(outcome, f"Steam Store outcome: {outcome}")

    return _SteamStoreLoad(outcome, mark={
        "appid": appid,
        "outcome": outcome,
        "error_message": message[:1000],
        "fetched_at": envelope.get("fetched_at"),
        "is_replay": True,
    })


def parse_twitch_fetched_at(raw_data: dict) -> datetime:
    """
    Parse the fetched_at timestamp written by the Twitch extractor.

    fetched_at is the real moment the API was called (src/extract_twitch.py
    writes it with datetime.now(timezone.utc).isoformat()). This is the
    observation time for every stream in the file, and it is what makes the
    snapshot business key (sample_hour, twitch_game_id) meaningful. Falling
    back to "now" here would just move the same bug -- the insert clock
    standing in for the observation time -- one layer down, so a missing or
    unparseable value is a hard failure, not a silent substitution.
    """

    fetched_at_raw = raw_data.get("fetched_at")

    if not fetched_at_raw:
        raise ValueError(
            "Twitch raw data is missing 'fetched_at'; cannot determine sample_time."
        )

    try:
        parsed = datetime.fromisoformat(fetched_at_raw)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Twitch raw data has an unparseable 'fetched_at': {fetched_at_raw!r}"
        ) from error

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed


def transform_twitch_streams(raw_data: dict) -> list[dict]:
    """
    Transform raw Twitch streams into aggregated game-level snapshots.

    Twitch /streams returns individual live streams.
    For analytics, we aggregate them by game_id and game_name.

    Every output row carries the same sample_time: the fetched_at instant
    recorded by the extractor for the whole file. One raw file is one moment
    of observation, even though building it can span several paginated
    requests.

    Output example:
    [
        {
            "twitch_game_id": "32399",
            "twitch_game_name": "Counter-Strike",
            "viewer_count": 123456,
            "stream_count": 7,
            "sample_time": datetime(2026, 5, 13, 12, 28, 52, 40293),
        }
    ]
    """

    sample_time = parse_twitch_fetched_at(raw_data)

    streams = raw_data.get("data", [])

    games = {}

    for stream in streams:
        game_id = stream.get("game_id")
        game_name = stream.get("game_name")
        viewer_count = to_int(stream.get("viewer_count")) or 0

        # Some Twitch streams may not have a game assigned.
        # We skip them because they cannot be grouped by game.
        if not game_id or not game_name:
            continue

        if game_id not in games:
            games[game_id] = {
                "twitch_game_id": game_id,
                "twitch_game_name": game_name,
                "viewer_count": 0,
                "stream_count": 0,
                "sample_time": sample_time,
            }

        games[game_id]["viewer_count"] += viewer_count
        games[game_id]["stream_count"] += 1

    return list(games.values())


def transform_twitch_games_lookup(raw_data: dict) -> list[dict]:
    """
    Transform Twitch Helix Get Games response into catalog rows.
    """

    categories = []

    for item in raw_data.get("data", []):
        twitch_game_id = item.get("id")
        twitch_game_name = item.get("name")

        if not twitch_game_id or not twitch_game_name:
            continue

        raw_igdb_id = item.get("igdb_id")
        igdb_id = to_int(raw_igdb_id, default=-1)

        categories.append(
            {
                "twitch_game_id": str(twitch_game_id),
                "twitch_game_name": twitch_game_name,
                "box_art_url": item.get("box_art_url"),
                "igdb_id": igdb_id if igdb_id > 0 else None,
                "source": "games_lookup",
            }
        )

    return categories


def unix_timestamp_to_date(timestamp: int | None):
    """
    Convert IGDB Unix timestamp to Python date.
    """

    if timestamp is None:
        return None

    return datetime.fromtimestamp(timestamp, timezone.utc).date()


def transform_igdb_game(game: dict) -> dict:
    """
    Transform one IGDB game object into a flat igdb_games record.

    game_type and status are stored as both their raw integer value and a
    human-readable label decoded from the IGDB enum tables.
    """

    game_type = game.get("game_type")
    status = game.get("status")

    return {
        "igdb_game_id": game["id"],
        "name": game["name"],
        "slug": game.get("slug"),
        "summary": game.get("summary"),
        "url": game.get("url"),
        "first_release_date": unix_timestamp_to_date(game.get("first_release_date")),
        "rating": game.get("rating"),
        "rating_count": game.get("rating_count"),
        "aggregated_rating": game.get("aggregated_rating"),
        "aggregated_rating_count": game.get("aggregated_rating_count"),
        "total_rating": game.get("total_rating"),
        "total_rating_count": game.get("total_rating_count"),
        "hypes": game.get("hypes"),
        "follows": game.get("follows"),
        "game_type": game_type,
        "game_type_label": IGDB_GAME_TYPES.get(game_type) if game_type is not None else None,
        "status": status,
        "status_label": IGDB_STATUSES.get(status) if status is not None else None,
        "raw_json": game,
    }


def detect_store_from_url(url: str | None) -> str | None:
    """
    Detect store name from an external URL.
    """

    if not url:
        return None

    normalized_url = url.lower()

    if "store.steampowered.com/app/" in normalized_url:
        return "steam"

    if "store.epicgames.com" in normalized_url or "epicgames.com/store" in normalized_url:
        return "epic"

    if "gog.com" in normalized_url:
        return "gog"

    if "microsoft.com" in normalized_url or "xbox.com" in normalized_url:
        return "microsoft"

    if "store.playstation.com" in normalized_url:
        return "playstation"

    if "nintendo.com" in normalized_url:
        return "nintendo"

    return None


def extract_steam_appid_from_url(url: str | None) -> str | None:
    """
    Extract Steam appid from a Steam store URL.
    """

    if not url:
        return None

    marker = "store.steampowered.com/app/"

    if marker not in url:
        return None

    after_marker = url.split(marker, 1)[1]
    appid = after_marker.split("/", 1)[0]

    return appid if appid.isdigit() else None


def extract_igdb_store_links(game: dict) -> list[dict]:
    """
    Extract store links from IGDB external_games and websites.

    These are distribution/store links:
    Steam, Epic, GOG, Microsoft/Xbox, PlayStation, Nintendo.
    """

    links = {}

    for item in game.get("external_games", []):
        url = item.get("url")
        store = detect_store_from_url(url)

        if not store:
            continue

        store_game_id = item.get("uid")

        if store == "steam":
            store_game_id = extract_steam_appid_from_url(url) or store_game_id

        if not store_game_id:
            continue

        key = (store, str(store_game_id))

        links[key] = {
            "igdb_game_id": game["id"],
            "store": store,
            "store_game_id": str(store_game_id),
            "store_url": url,
        }

    for item in game.get("websites", []):
        url = item.get("url")
        store = detect_store_from_url(url)

        if not store:
            continue

        store_game_id = None

        if store == "steam":
            store_game_id = extract_steam_appid_from_url(url)

        if not store_game_id:
            continue

        key = (store, str(store_game_id))

        links[key] = {
            "igdb_game_id": game["id"],
            "store": store,
            "store_game_id": str(store_game_id),
            "store_url": url,
        }

    return list(links.values())


def extract_twitch_game_id_from_url(url: str | None) -> str | None:
    """
    Extract Twitch category identifier from IGDB external_games.

    For Twitch, IGDB usually stores the real Twitch game_id in uid.
    URL is only used as a fallback indicator.
    """

    if not url:
        return None

    if "twitch.tv/directory/" not in url.lower():
        return None

    return None


def extract_igdb_twitch_categories(game: dict) -> list[dict]:
    """
    Extract Twitch category links from IGDB external_games.

    This creates rows for twitch_categories.
    """

    categories = {}

    for item in game.get("external_games", []):
        url = item.get("url")

        if not url or "twitch.tv/directory/" not in url.lower():
            continue

        twitch_game_id = item.get("uid")

        if not twitch_game_id:
            continue

        key = str(twitch_game_id)

        categories[key] = {
            "twitch_game_id": key,
            "twitch_game_name": game["name"],
            "is_game": True,
            "igdb_game_id": game["id"],
            "mapping_status": "mapped",
            "mapping_method": "igdb_external_game",
            "mapping_confidence": 1.0,
            "notes": "Mapped from IGDB external_games Twitch UID.",
        }

    return list(categories.values())


def transform_igdb_search_results(raw_data: dict) -> list[dict]:
    """
    Transform IGDB search raw JSON into structured records.

    One raw file can contain multiple IGDB games.
    """

    transformed_records = []

    for game in raw_data.get("data", []):
        transformed_records.append(
            {
                "igdb_game": transform_igdb_game(game),
                "store_links": extract_igdb_store_links(game),
                "twitch_categories": extract_igdb_twitch_categories(game),
            }
        )

    return transformed_records


if __name__ == "__main__":
    steamspy_sample = {
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

    steam_store_sample = {
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

    print(transform_steamspy_game(steamspy_sample))
    print(transform_steam_store_game(steam_store_sample))
