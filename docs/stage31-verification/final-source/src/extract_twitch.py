import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# Twitch API endpoints
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_STREAMS_URL = "https://api.twitch.tv/helix/streams"
TWITCH_GAMES_URL = "https://api.twitch.tv/helix/games"

# Directory where we store raw Twitch API responses
RAW_DATA_DIR = Path("data/raw")


def get_twitch_credentials() -> tuple[str, str]:
    """
    Load Twitch API credentials from .env.

    Required variables:
    - TWITCH_CLIENT_ID
    - TWITCH_CLIENT_SECRET
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
    Request an app access token from Twitch.

    We use the client_credentials flow because this ETL does not need
    access to any private user data.
    """

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

    return access_token


def fetch_top_streams(
    client_id: str,
    access_token: str,
    pages: int = 1,
    delay: float = 1.0,
) -> dict:
    """
    Fetch top live streams from Twitch.

    Twitch returns streams, not aggregated game stats.
    Later, transform.py will group these streams by game_id/game_name.

    Each page can contain up to 100 streams.
    """

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
    }

    all_streams = []
    pagination_cursor = None

    for page_number in range(pages):
        params = {
            "first": 100,
        }

        if pagination_cursor:
            params["after"] = pagination_cursor

        response = requests.get(
            TWITCH_STREAMS_URL,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        page_data = response.json()

        streams = page_data.get("data", [])
        all_streams.extend(streams)

        pagination_cursor = (
            page_data.get("pagination", {})
            .get("cursor")
        )

        print(
            f"Fetched Twitch streams page {page_number + 1}/{pages}: "
            f"{len(streams)} streams"
        )

        # Stop if Twitch did not return a next page cursor.
        if not pagination_cursor:
            break

        # Do not sleep after the last requested page.
        if page_number < pages - 1:
            time.sleep(delay)

    return {
        "source": "twitch",
        "request": "streams",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "stream_count": len(all_streams),
        "data": all_streams,
    }


def fetch_twitch_games_by_ids(
    client_id: str,
    access_token: str,
    game_ids: list[str],
) -> dict:
    """
    Fetch Twitch game/category metadata by Twitch game IDs.
    """

    if not game_ids:
        raise ValueError("game_ids cannot be empty")

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
    }

    params = [
        ("id", game_id)
        for game_id in game_ids
    ]

    response = requests.get(
        TWITCH_GAMES_URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    response_json = response.json()
    games = response_json.get("data", [])

    return {
        "source": "twitch",
        "request": "games_lookup",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "game_ids": game_ids,
        "result_count": len(games),
        "data": games,
    }


def save_raw_twitch_data(data: dict) -> Path:
    """
    Save raw Twitch API response to data/raw/twitch/streams/YYYY-MM-DD/.
    """

    now = datetime.now(timezone.utc)

    date_part = now.strftime("%Y-%m-%d")
    timestamp_part = now.strftime("%Y%m%d_%H%M%S")

    output_dir = RAW_DATA_DIR / "twitch" / "streams" / date_part
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"streams_{timestamp_part}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return output_path


def save_raw_twitch_games_lookup(data: dict) -> Path:
    """
    Save raw Twitch Get Games response to data/raw/twitch/games_lookup/YYYY-MM-DD/.
    """

    now = datetime.now(timezone.utc)

    date_part = now.strftime("%Y-%m-%d")
    timestamp_part = now.strftime("%Y%m%d_%H%M%S")

    output_dir = RAW_DATA_DIR / "twitch" / "games_lookup" / date_part
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"games_lookup_{timestamp_part}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return output_path


def run_twitch_streams_extract(pages: int, delay: float) -> Path:
    """
    Full extract flow:
    1. Load Twitch credentials.
    2. Get app access token.
    3. Fetch top streams.
    4. Save raw JSON.
    """

    client_id, client_secret = get_twitch_credentials()
    access_token = get_app_access_token(client_id, client_secret)

    data = fetch_top_streams(
        client_id=client_id,
        access_token=access_token,
        pages=pages,
        delay=delay,
    )

    output_path = save_raw_twitch_data(data)

    print(f"Saved Twitch raw data to: {output_path}")

    return output_path


def run_twitch_games_lookup(game_ids: list[str]) -> Path:
    """
    Full Twitch games lookup flow:
    1. Load Twitch credentials.
    2. Get app access token.
    3. Fetch game/category metadata by IDs.
    4. Save raw JSON.
    """

    client_id, client_secret = get_twitch_credentials()
    access_token = get_app_access_token(client_id, client_secret)

    data = fetch_twitch_games_by_ids(
        client_id=client_id,
        access_token=access_token,
        game_ids=game_ids,
    )

    output_path = save_raw_twitch_games_lookup(data)

    print(f"Found {data['result_count']} Twitch games")
    print(f"Saved Twitch games lookup raw data to: {output_path}")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract data from Twitch Helix API."
    )

    subparsers = parser.add_subparsers(dest="command")

    games_lookup_parser = subparsers.add_parser(
        "games-lookup",
        help="Lookup Twitch game/category metadata by Twitch game IDs.",
    )

    games_lookup_parser.add_argument(
        "--ids",
        nargs="+",
        required=True,
        help="One or more Twitch game IDs.",
    )

    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="Number of Twitch streams pages to fetch. Each page has up to 100 streams.",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between Twitch API pages.",
    )

    args = parser.parse_args()

    if args.command == "games-lookup":
        run_twitch_games_lookup(args.ids)
        return

    if args.pages < 1:
        raise ValueError("--pages must be at least 1")

    if args.delay < 0:
        raise ValueError("--delay cannot be negative")

    run_twitch_streams_extract(
        pages=args.pages,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
