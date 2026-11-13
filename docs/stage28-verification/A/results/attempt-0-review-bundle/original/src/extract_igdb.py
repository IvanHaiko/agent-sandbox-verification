import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"

RAW_DATA_DIR = Path("data/raw")

# In-memory token cache: client_id -> (access_token, expiry_monotonic)
# Tokens are refreshed 60 seconds before expiry to avoid using a stale token.
_token_cache: dict[str, tuple[str, float]] = {}


def get_twitch_credentials() -> tuple[str, str]:
    """
    Load Twitch API credentials from .env.

    IGDB uses Twitch OAuth credentials.
    """

    load_dotenv()

    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")

    if not client_id:
        raise ValueError("Missing TWITCH_CLIENT_ID in .env")

    if not client_secret:
        raise ValueError("Missing TWITCH_CLIENT_SECRET in .env")

    return client_id, client_secret


def get_app_access_token(client_id: str, client_secret: str) -> str:
    """
    Return a valid Twitch app access token, reusing a cached one if still valid.

    Tokens from Twitch expire in ~60 days. The cache avoids a token request on
    every IGDB call within the same process. A 60-second buffer before expiry
    ensures we never hand out a token that is about to expire.
    """

    cached = _token_cache.get(client_id)
    if cached:
        access_token, expiry = cached
        if time.monotonic() < expiry:
            return access_token

    response = requests.post(
        TWITCH_TOKEN_URL,
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    access_token = data.get("access_token")

    if not access_token:
        raise ValueError(f"Twitch token response does not contain access_token: {data}")

    expires_in = data.get("expires_in", 3600)
    _token_cache[client_id] = (access_token, time.monotonic() + expires_in - 60)

    return access_token


def slugify_filename(value: str) -> str:
    """
    Convert a search query into a safe filename part.
    """

    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")

    return value or "igdb_search"


def build_igdb_game_search_query(search_term: str, limit: int) -> str:
    """
    Build an IGDB discovery query body.

    IGDB uses a text query language in the POST request body.
    This field list is intentionally broad because we are still exploring
    the useful structure for our future database schema.
    """

    safe_search_term = search_term.replace('"', '\\"')

    return f"""
search "{safe_search_term}";
fields
    id,
    name,
    slug,
    url,
    summary,
    storyline,
    first_release_date,
    status,
    game_type,
    parent_game,
    version_parent,
    version_title,
    rating,
    rating_count,
    aggregated_rating,
    aggregated_rating_count,
    total_rating,
    total_rating_count,
    hypes,
    follows,
    genres.name,
    themes.name,
    keywords.name,
    game_modes.name,
    player_perspectives.name,
    platforms.name,
    release_dates.date,
    release_dates.platform.name,
    release_dates.region,
    involved_companies.company.name,
    involved_companies.developer,
    involved_companies.publisher,
    websites.url,
    websites.category,
    external_games.uid,
    external_games.category,
    external_games.url,
    collection.name,
    collections.name,
    franchise.name,
    franchises.name;
limit {limit};
"""


def search_igdb_games(
    client_id: str,
    access_token: str,
    search_term: str,
    limit: int = 10,
) -> dict:
    """
    Search games in IGDB by name and return raw JSON wrapped with metadata.
    """

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    query = build_igdb_game_search_query(
        search_term=search_term,
        limit=limit,
    )

    response = requests.post(
        IGDB_GAMES_URL,
        headers=headers,
        data=query,
        timeout=30,
    )

    response.raise_for_status()

    return {
        "source": "igdb",
        "request": "games_search",
        "search_term": search_term,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(response.json()),
        "data": response.json(),
    }


def save_raw_igdb_data(data: dict) -> Path:
    """
    Save raw IGDB game search response to data/raw/igdb/games_search/YYYY-MM-DD/.
    """

    now = datetime.now(timezone.utc)

    date_part = now.strftime("%Y-%m-%d")
    timestamp_part = now.strftime("%Y%m%d_%H%M%S")

    search_term = data.get("search_term", "igdb_search")
    filename_part = slugify_filename(search_term)

    output_dir = RAW_DATA_DIR / "igdb" / "games_search" / date_part
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{filename_part}_{timestamp_part}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return output_path


def run_igdb_game_search(search_term: str, limit: int) -> Path:
    """
    Full IGDB extract flow:
    1. Load Twitch credentials.
    2. Get Twitch app access token.
    3. Search IGDB games.
    4. Save raw JSON.
    """

    client_id, client_secret = get_twitch_credentials()
    access_token = get_app_access_token(client_id, client_secret)

    data = search_igdb_games(
        client_id=client_id,
        access_token=access_token,
        search_term=search_term,
        limit=limit,
    )

    output_path = save_raw_igdb_data(data)

    print(f"Found {data['result_count']} IGDB results for: {search_term}")
    print(f"Saved IGDB raw data to: {output_path}")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract game metadata from IGDB API."
    )

    parser.add_argument(
        "--search",
        required=True,
        help="Game name to search in IGDB.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of IGDB results to fetch.",
    )

    args = parser.parse_args()

    if args.limit < 1:
        raise ValueError("--limit must be at least 1")

    run_igdb_game_search(
        search_term=args.search,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()