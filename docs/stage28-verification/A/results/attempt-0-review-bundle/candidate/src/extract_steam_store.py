import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


# Base URL for the Steam Store API appdetails endpoint
STEAM_STORE_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

# Directory where we store raw JSON responses
RAW_DATA_DIR = Path("data/raw")

# Basic headers for polite API usage
REQUEST_HEADERS = {
    "User-Agent": "steam-etl-learning-project/0.1"
}

# Version of the bronze envelope shape written by save_raw_json below.
# A bare integer, not inferred from which keys happen to be present, so a
# future shape change cannot be mistaken for this one.
ENVELOPE_VERSION = 1


def build_envelope(
    *,
    appid: int,
    request: dict[str, Any],
    url: str | None,
    fetched_at: str | None,
    outcome: str,
    http_status: int | None,
    body: dict[str, Any] | None,
    error: str | None,
    redirect_to: int | None = None,
) -> dict[str, Any]:
    """
    Build one Steam Store bronze envelope.

    outcome is one of:
    - "ok"              wrapper present, success: true, data.steam_appid
                        matches the requested appid.      body = response.
    - "refused"         wrapper present, success: false.  body = response.
    - "not_found"       response present, no usable wrapper for this
                        appid (missing key, or a value that is not a
                        JSON object).                     body = response.
    - "redirected"      wrapper present, success: true, but data carries a
                        *different* appid than the one requested. The
                        target appid goes in redirect_to (a typed field),
                        never folded into prose.           body = response.
    - "transport_error" no response at all (bad HTTP status, empty body,
                        invalid JSON, network/timeout failure). body = null.

    body, when present, is the Steam Store response verbatim -- the
    envelope carries metadata about the request, it does not rewrite what
    Steam said. redirect_to is metadata about the fetch too (which appid
    the response actually described), not a rewrite of body -- it is only
    non-null when outcome == "redirected".

    redirect_to is additive: envelope-version-1 files written before this
    field existed simply lack the key, so any reader must use .get(...)
    with a default rather than indexing it directly.
    """

    # transport_error means no answer arrived, so there is no moment of
    # receiving one. Stamping the attempt clock into fetched_at would make
    # the field claim an answer that never came -- the same fabrication
    # migration 010 had to undo for Twitch sample_time and migration 013
    # for is_free. When we tried is recorded by the file name and, in the
    # database, by steam_store_updated_at.
    if outcome == "transport_error":
        fetched_at = None
        body = None

    return {
        "envelope": ENVELOPE_VERSION,
        "source": "steam_store",
        "outcome": outcome,
        "appid": appid,
        "request": request,
        "url": url,
        "fetched_at": fetched_at,
        "http_status": http_status,
        "error": error,
        "body": body,
        "redirect_to": redirect_to,
    }


def _as_positive_int(value: Any) -> int | None:
    """
    Parse value as a positive integer, or return None.

    Used only to read data.steam_appid out of a Steam Store response to
    compare it against the requested appid -- kept local and minimal
    rather than importing src.transform.to_int, so the extract layer does
    not depend on the transform layer for something this small.
    """

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def fetch_appdetails(appid: int) -> dict[str, Any]:
    """
    Fetch app details from the Steam Store API.

    Returns a bronze envelope (see build_envelope) for every outcome the
    API can produce, instead of raising. A bad HTTP status, an empty body,
    invalid JSON, and a network/timeout failure are all classified as
    "transport_error" rather than thrown, so a caller can always save
    bronze and record the result -- including the failure -- for every
    call. Only a caller error (a non-positive appid) still raises, because
    no request was ever attempted and there is nothing to record.
    """

    if appid <= 0:
        raise ValueError("appid must be a positive integer")

    # Query parameters sent to the Steam Store API
    request_params = {
        "appids": appid,
    }

    fetched_at = datetime.now(timezone.utc).isoformat()

    def transport_error_envelope(
        message: str,
        url: str | None = None,
        http_status: int | None = None,
    ) -> dict[str, Any]:
        return build_envelope(
            appid=appid,
            request=request_params,
            url=url,
            fetched_at=fetched_at,
            outcome="transport_error",
            http_status=http_status,
            body=None,
            error=message,
        )

    # Send GET request to the API
    try:
        response = requests.get(
            STEAM_STORE_APPDETAILS_URL,
            params=request_params,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
    except requests.exceptions.RequestException as error:
        print(f"Transport error fetching appid {appid}: {error}")
        return transport_error_envelope(str(error))

    # Print basic response info for debugging
    print(f"Request URL: {response.url}")
    print(f"Status code: {response.status_code}")

    url = response.url
    http_status = response.status_code

    # A failed HTTP status is a transport-level fact, not a Steam Store
    # answer about this appid.
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        return transport_error_envelope(str(error), url=url, http_status=http_status)

    # An empty body means nothing was said, not that nothing exists.
    if not response.text.strip():
        return transport_error_envelope(
            f"Steam Store returned an empty response for appid={appid}",
            url=url,
            http_status=http_status,
        )

    try:
        body = response.json()
    except requests.exceptions.JSONDecodeError as error:
        print("Response is not valid JSON.")
        print("Response preview:")
        print(response.text[:500])
        return transport_error_envelope(
            f"invalid JSON: {error}",
            url=url,
            http_status=http_status,
        )

    app_wrapper = body.get(str(appid)) if isinstance(body, dict) else None

    # A value present under this appid's key that is not itself a JSON
    # object (e.g. {"730": "maintenance"}) carries no success/data fields
    # to read. It is functionally the same "nothing usable for this
    # appid" fact as a missing key, so it is normalized to None here and
    # falls into the same not_found branch below -- without this,
    # app_wrapper.get("success") a few lines down would raise
    # AttributeError before anything had been saved to bronze.
    if not isinstance(app_wrapper, dict):
        app_wrapper = None

    if app_wrapper is None:
        return build_envelope(
            appid=appid,
            request=request_params,
            url=url,
            fetched_at=fetched_at,
            outcome="not_found",
            http_status=http_status,
            body=body,
            error=None,
        )

    if not app_wrapper.get("success"):
        return build_envelope(
            appid=appid,
            request=request_params,
            url=url,
            fetched_at=fetched_at,
            outcome="refused",
            http_status=http_status,
            body=body,
            error=None,
        )

    # success: true still needs one more check: Steam sometimes answers
    # about a *different* appid than the one requested (a merged or
    # retired store page redirecting to its replacement). data.steam_appid
    # is the source's own statement of which game this response actually
    # describes, so it is compared against the appid we asked for.
    response_data = app_wrapper.get("data") or {}
    response_appid = _as_positive_int(response_data.get("steam_appid"))

    if response_appid is not None and response_appid != appid:
        return build_envelope(
            appid=appid,
            request=request_params,
            url=url,
            fetched_at=fetched_at,
            outcome="redirected",
            http_status=http_status,
            body=body,
            error=None,
            redirect_to=response_appid,
        )

    return build_envelope(
        appid=appid,
        request=request_params,
        url=url,
        fetched_at=fetched_at,
        outcome="ok",
        http_status=http_status,
        body=body,
        error=None,
    )


def save_raw_json(data: dict[str, Any], appid: int) -> Path:
    """
    Save raw Steam Store API response as a JSON file.

    Raw files are organized by:
    data/raw/steam_store/appdetails/{date}/
    """

    # Create date partition for raw data
    run_date = datetime.now(timezone.utc).date().isoformat()

    # Build output directory
    output_dir = RAW_DATA_DIR / "steam_store" / "appdetails" / run_date
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create UTC timestamp for unique file names
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Build output file path
    file_path = output_dir / f"{appid}_{timestamp}.json"

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
        description="Extract raw app details from Steam Store API"
    )

    # Required appid argument
    parser.add_argument(
        "--appid",
        type=int,
        required=True,
        help="Steam appid, for example: --appid 730",
    )

    return parser.parse_args()


def main() -> None:
    """
    Main script entry point.
    """

    # Read command-line arguments
    args = parse_args()

    if args.appid <= 0:
        raise ValueError("--appid must be a positive integer")

    print(f"Fetching Steam Store appdetails for appid: {args.appid}")

    # Fetch raw data from Steam Store API
    data = fetch_appdetails(args.appid)

    # Save raw data to local JSON file
    file_path = save_raw_json(data, args.appid)

    print(f"Saved raw JSON to: {file_path}")


if __name__ == "__main__":
    main()
