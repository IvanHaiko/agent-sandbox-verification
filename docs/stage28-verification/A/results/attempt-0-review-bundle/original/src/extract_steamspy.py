import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


# Base URL for the SteamSpy API
STEAMSPY_API_URL = "https://steamspy.com/api.php"

# Directory where we store raw JSON responses
RAW_DATA_DIR = Path("data/raw")

# Supported SteamSpy request types
SUPPORTED_REQUEST_TYPES = {
    "top100in2weeks",
    "top100owned",
    "all",
    "appdetails",
}

# Basic headers for polite API usage
REQUEST_HEADERS = {
    "User-Agent": "steam-etl-learning-project/0.1"
}


def fetch_steamspy_data(
    request_type: str,
    page: int | None = None,
    appid: int | None = None,
) -> dict[str, Any]:
    """
    Fetch data from the SteamSpy API.

    Supported request types:
    - top100in2weeks
    - top100owned
    - all
    - appdetails
    """

    if request_type not in SUPPORTED_REQUEST_TYPES:
        raise ValueError(f"Unsupported SteamSpy request type: {request_type}")

    # Base query parameters sent to the SteamSpy API
    params: dict[str, Any] = {
        "request": request_type,
    }

    # Add page parameter only for paginated requests like "all"
    if page is not None:
        params["page"] = page

    # Add appid parameter only for app-specific requests like "appdetails"
    if appid is not None:
        params["appid"] = appid

    # Send GET request to the API
    response = requests.get(
        STEAMSPY_API_URL,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=30,
    )

    # Print basic response info for debugging
    print(f"Request URL: {response.url}")
    print(f"Status code: {response.status_code}")

    # Raise an error if the HTTP request failed
    response.raise_for_status()

    # Check if response body is empty
    if not response.text.strip():
        raise ValueError(
            f"SteamSpy returned an empty response for request_type='{request_type}'"
        )

    try:
        # Convert JSON response to Python dictionary
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print("Response is not valid JSON.")
        print("Response preview:")
        print(response.text[:500])
        raise


def build_output_filename(
    request_type: str,
    page: int | None = None,
    appid: int | None = None,
) -> str:
    """
    Build a clear file name for the raw JSON output.
    """

    # Create UTC timestamp for unique file names
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Add request-specific details to the file name
    if request_type == "all" and page is not None:
        return f"page_{page}_{timestamp}.json"

    if request_type == "appdetails" and appid is not None:
        return f"{appid}_{timestamp}.json"

    return f"{request_type}_{timestamp}.json"


def save_raw_json(
    data: dict[str, Any],
    request_type: str,
    page: int | None = None,
    appid: int | None = None,
) -> Path:
    """
    Save raw SteamSpy API response as a JSON file.

    Raw files are organized by:
    data/raw/steamspy/{request_type}/{date}/
    """

    # Create date partition for raw data
    run_date = datetime.now(timezone.utc).date().isoformat()

    # Build output directory
    output_dir = RAW_DATA_DIR / "steamspy" / request_type / run_date
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build output file path
    file_name = build_output_filename(
        request_type=request_type,
        page=page,
        appid=appid,
    )
    file_path = output_dir / file_name

    # Save data to JSON file with readable formatting
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return file_path


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    # Create CLI argument parser
    parser = argparse.ArgumentParser(
        description="Extract raw data from SteamSpy API"
    )

    # Required argument: SteamSpy request type
    parser.add_argument(
        "request_type",
        choices=sorted(SUPPORTED_REQUEST_TYPES),
        help="SteamSpy request type",
    )

    # Optional page argument for paginated requests
    parser.add_argument(
        "--page",
        type=int,
        help="Page number for paginated SteamSpy requests, for example: all --page 0",
    )

    # Optional appid argument for app-specific requests
    parser.add_argument(
        "--appid",
        type=int,
        help="Steam appid for app-specific requests, for example: appdetails --appid 730",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """
    Validate command-line argument combinations.
    """

    # appdetails requires appid
    if args.request_type == "appdetails" and args.appid is None:
        raise ValueError("appdetails request requires --appid")

    # appid should only be used with appdetails
    if args.request_type != "appdetails" and args.appid is not None:
        raise ValueError("--appid can only be used with appdetails")

    # page should only be used with all
    if args.request_type != "all" and args.page is not None:
        raise ValueError("--page can only be used with all")

    # page should not be negative
    if args.page is not None and args.page < 0:
        raise ValueError("--page cannot be negative")

    # appid should be positive
    if args.appid is not None and args.appid <= 0:
        raise ValueError("--appid must be a positive integer")

    # If request_type is "all" and page is not provided, use page 0 by default
    if args.request_type == "all" and args.page is None:
        args.page = 0


def count_records(data: dict[str, Any], request_type: str) -> int:
    """
    Count records in the API response.
    """

    # appdetails returns data for one specific app
    if request_type == "appdetails":
        return 1 if data else 0

    # list-like responses are usually dictionaries where each key is an appid
    return len(data)


def main() -> None:
    """
    Main script entry point.
    """

    # Read command-line arguments
    args = parse_args()

    # Validate argument combinations
    validate_args(args)

    print(f"Fetching SteamSpy data: {args.request_type}")

    # Fetch raw data from SteamSpy
    data = fetch_steamspy_data(
        request_type=args.request_type,
        page=args.page,
        appid=args.appid,
    )

    # Save raw data to local JSON file
    file_path = save_raw_json(
        data=data,
        request_type=args.request_type,
        page=args.page,
        appid=args.appid,
    )

    print(f"Saved raw JSON to: {file_path}")
    print(f"Records fetched: {count_records(data, args.request_type)}")


if __name__ == "__main__":
    main()
