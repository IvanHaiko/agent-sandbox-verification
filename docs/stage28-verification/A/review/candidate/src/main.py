import argparse
import re
import time
from pathlib import Path

from rapidfuzz import fuzz

from src.db import get_db_connection
from src.extract_igdb import run_igdb_game_search
from src.extract_steam_store import (
    fetch_appdetails,
    save_raw_json as save_steam_store_raw_json,
)
from src.extract_steamspy import (
    count_records,
    fetch_steamspy_data,
    save_raw_json as save_steamspy_raw_json,
)
from src.extract_twitch import run_twitch_games_lookup, run_twitch_streams_extract
from src.migrations import run_migrations
from src.load import (
    get_games_for_store_enrichment,
    load_data,
    mark_steam_store_enrichment_result,
)


# SteamSpy "all" returns up to 1000 games per page.
STEAMSPY_ALL_PAGE_SIZE = 1000

NON_GAME_TWITCH_CATEGORIES = {
    "Just Chatting",
    "IRL",
    "Pools, Hot Tubs, and Beaches",
    "Special Events",
    "Sports",
    "Food & Drink",
    "Always On",
    "Music",
    "Art",
    "Makers & Crafting",
    "Science & Technology",
    "Talk Shows & Podcasts",
}


def normalize_game_name(name: str) -> str:
    """
    Normalize game/category names before fuzzy matching.
    """

    normalized = name.lower()
    normalized = normalized.replace("&", "and")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def calculate_name_score(left_name: str, right_name: str) -> float:
    """
    Calculate a conservative fuzzy name similarity score.

    token_set_ratio alone is too permissive:
    "Apex Legends" and "Apex Legends Mobile" can score 1.0.

    We combine multiple scores and apply a penalty when one name has
    extra words compared to the other.
    """

    left_normalized = normalize_game_name(left_name)
    right_normalized = normalize_game_name(right_name)

    if not left_normalized or not right_normalized:
        return 0.0

    if left_normalized == right_normalized:
        return 1.0

    token_set_score = fuzz.token_set_ratio(left_normalized, right_normalized) / 100
    token_sort_score = fuzz.token_sort_ratio(left_normalized, right_normalized) / 100
    ratio_score = fuzz.ratio(left_normalized, right_normalized) / 100

    left_tokens = set(left_normalized.split())
    right_tokens = set(right_normalized.split())

    shared_tokens = left_tokens & right_tokens
    all_tokens = left_tokens | right_tokens

    token_overlap = len(shared_tokens) / len(all_tokens) if all_tokens else 0.0

    length_ratio = min(
        len(left_normalized),
        len(right_normalized),
    ) / max(
        len(left_normalized),
        len(right_normalized),
    )

    final_score = (
        token_set_score * 0.35
        + token_sort_score * 0.25
        + ratio_score * 0.25
        + token_overlap * 0.10
        + length_ratio * 0.05
    )

    return round(final_score, 4)


def run_steamspy_all_page(
    page: int,
    snapshot_date: str | None = None,
) -> Path:
    """
    Run pipeline for one SteamSpy 'all' page.

    Steps:
    1. Fetch raw SteamSpy data for one page.
    2. Save raw JSON to data/raw/.
    3. Load raw JSON into PostgreSQL.
    """

    print(f"Fetching SteamSpy 'all' page {page}...")

    data = fetch_steamspy_data(
        request_type="all",
        page=page,
    )

    records_count = count_records(data, request_type="all")

    if records_count == 0:
        raise ValueError(f"SteamSpy returned 0 records for page {page}")

    file_path = save_steamspy_raw_json(
        data=data,
        request_type="all",
        page=page,
    )

    print(f"Saved raw JSON to: {file_path}")
    print(f"Records fetched: {records_count}")

    print("Loading data into PostgreSQL...")

    load_data(
        source="steamspy",
        file_path=file_path,
        snapshot_date=snapshot_date,
    )

    print(f"Loaded SteamSpy page {page} into PostgreSQL.")

    return file_path


def run_steamspy_daily(
    start_page: int = 0,
    max_pages: int | None = None,
    delay_seconds: int = 65,
    snapshot_date: str | None = None,
) -> None:
    """
    Run daily SteamSpy pipeline.

    This function fetches SteamSpy 'all' pages one by one,
    saves each raw JSON response, and loads it into PostgreSQL.

    The loop stops when:
    - SteamSpy returns 0 records
    - SteamSpy returns fewer than 1000 records
    - max_pages is reached
    """

    page = start_page
    pages_loaded = 0
    total_records_loaded = 0

    print("Starting SteamSpy daily pipeline...")
    print(f"Start page: {start_page}")
    print(f"Delay between pages: {delay_seconds} seconds")

    if max_pages is not None:
        print(f"Max pages: {max_pages}")

    while True:
        print("-" * 60)
        print(f"Processing SteamSpy page {page}...")

        data = fetch_steamspy_data(
            request_type="all",
            page=page,
        )

        records_count = count_records(data, request_type="all")

        if records_count == 0:
            print(f"No records returned for page {page}. Stopping.")
            break

        file_path = save_steamspy_raw_json(
            data=data,
            request_type="all",
            page=page,
        )

        print(f"Saved raw JSON to: {file_path}")
        print(f"Records fetched: {records_count}")

        load_data(
            source="steamspy",
            file_path=file_path,
            snapshot_date=snapshot_date,
        )

        print(f"Loaded page {page} into PostgreSQL.")

        pages_loaded += 1
        total_records_loaded += records_count

        if records_count < STEAMSPY_ALL_PAGE_SIZE:
            print(f"Last page detected: page {page}.")
            break

        if max_pages is not None and pages_loaded >= max_pages:
            print(f"Reached max_pages={max_pages}. Stopping.")
            break

        page += 1

        print(f"Waiting {delay_seconds} seconds before next request...")
        time.sleep(delay_seconds)

    print("-" * 60)
    print("SteamSpy daily pipeline finished.")
    print(f"Pages loaded: {pages_loaded}")
    print(f"Records loaded: {total_records_loaded}")


def run_steam_store_appdetails(appid: int) -> tuple[Path, str]:
    """
    Run Steam Store appdetails enrichment for one game.

    Steps:
    1. Fetch a Steam Store appdetails envelope for one appid.
       fetch_appdetails never raises for anything the API itself can say
       or fail to say -- it classifies the outcome (ok / refused /
       not_found / redirected / transport_error) instead.
    2. Save that envelope to data/raw/ unconditionally, so bronze exists
       for every outcome, including a refusal or a transport failure.
    3. Hand the saved file to load_data, which loads game metadata for
       "ok" and "redirected" (under the appid Steam actually described)
       and otherwise records the outcome on the requested appid's row
       without touching game metadata.

    Returns the saved file's path and the outcome load_data recorded, so
    a caller (run_steam_store_enrich below) can tally outcomes instead of
    treating every non-exception return as "processed".
    """

    if appid <= 0:
        raise ValueError("appid must be a positive integer")

    print(f"Fetching Steam Store appdetails for appid {appid}...")

    envelope = fetch_appdetails(appid)

    file_path = save_steam_store_raw_json(
        data=envelope,
        appid=appid,
    )

    print(f"Saved raw JSON to: {file_path}")

    print("Recording Steam Store result in PostgreSQL...")

    outcome = load_data(
        source="steam_store",
        file_path=file_path,
    )

    print(f"Processed Steam Store result for appid {appid}: {outcome}")

    return file_path, outcome


# The outcomes load_steam_store_file can hand back, in the order they are
# reported by run_steam_store_enrich's summary below.
STEAM_STORE_OUTCOMES = ("ok", "refused", "not_found", "redirected", "transport_error")


def run_steam_store_enrich(
    limit: int = 100,
    delay_seconds: int = 1,
    refresh_after_days: int = 30,
) -> None:
    """
    Run Steam Store metadata enrichment for games from the database.

    Steps:
    1. Find games with missing metadata in PostgreSQL.
    2. Fetch Steam Store appdetails for each appid.
    3. Save raw JSON.
    4. Load metadata into PostgreSQL.

    run_steam_store_appdetails saves bronze and records a result for
    every outcome (ok, refused, not_found, redirected, transport_error)
    rather than raising to signal a refusal, so those five are tallied
    separately below by the outcome load_data actually returned -- a run
    where Steam refuses every request must not read as "Processed: N,
    Failed: 0" the way it used to when fetch_appdetails stopped raising
    but the counting here was never updated to match. "unexpected errors"
    is reserved for something going wrong outside Steam's own answer (a
    network exception outside fetch_appdetails's own handling, a DB
    error, and so on) -- those are folded into the transport_error tally
    too (both mean "we do not have a confirmed answer, and the reason is
    on our side"), but counted separately as well so the two are never
    hidden inside one number.
    """

    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")

    if refresh_after_days <= 0:
        raise ValueError("refresh_after_days must be a positive integer")

    print("Starting Steam Store enrichment pipeline...")
    print(f"Limit: {limit}")
    print(f"Delay between requests: {delay_seconds} seconds")
    print(f"Refresh after days: {refresh_after_days}")

    appids = get_games_for_store_enrichment(limit=limit, refresh_after_days=refresh_after_days)

    if not appids:
        print("No games found for Steam Store enrichment.")
        return

    print(f"Games selected for enrichment: {len(appids)}")

    outcome_counts = {outcome: 0 for outcome in STEAM_STORE_OUTCOMES}
    unexpected_error_count = 0

    for index, appid in enumerate(appids, start=1):
        print("-" * 60)
        print(f"[{index}/{len(appids)}] Processing appid {appid}...")

        try:
            _file_path, outcome = run_steam_store_appdetails(appid)
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        except Exception as error:
            unexpected_error_count += 1
            outcome_counts["transport_error"] += 1
            error_message = str(error)
            print(f"Failed to enrich appid {appid}: {error_message}")

            # is_replay is passed explicitly even though False is the
            # default: this path is by construction a new event, never a
            # re-read of a stored file, and saying so here is what stops
            # the counter guard from swallowing it. fetched_at stays None
            # because no answer arrived -- the attempt is timestamped by
            # steam_store_updated_at instead.
            mark_steam_store_enrichment_result(
                appid=appid,
                outcome="transport_error",
                error_message=error_message[:1000],
                is_replay=False,
            )

        if index < len(appids):
            print(f"Waiting {delay_seconds} seconds before next request...")
            time.sleep(delay_seconds)

    print("-" * 60)
    print("Steam Store enrichment pipeline finished.")

    for outcome in STEAM_STORE_OUTCOMES:
        print(f"{outcome}: {outcome_counts[outcome]}")

    print(f"Unexpected errors (outside Steam's own answer): {unexpected_error_count}")
    print(f"Processed (ok): {outcome_counts['ok']}")


def run_daily_pipeline(
    steamspy_start_page: int = 0,
    steamspy_max_pages: int | None = None,
    steamspy_delay_seconds: int = 65,
    store_limit: int = 500,
    store_delay_seconds: int = 1,
    snapshot_date: str | None = None,
) -> None:
    """
    Run the full daily Steam analytics pipeline.

    Steps:
    1. Fetch SteamSpy 'all' pages and load daily snapshots.
    2. Enrich games with Steam Store metadata.

    This is the command that Airflow will eventually run.
    """

    print("=" * 80)
    print("Starting full daily Steam pipeline...")
    print("=" * 80)

    print("Step 1/2: Running SteamSpy daily snapshots...")

    run_steamspy_daily(
        start_page=steamspy_start_page,
        max_pages=steamspy_max_pages,
        delay_seconds=steamspy_delay_seconds,
        snapshot_date=snapshot_date,
    )

    print("=" * 80)
    print("Step 2/2: Running Steam Store metadata enrichment...")

    run_steam_store_enrich(
        limit=store_limit,
        delay_seconds=store_delay_seconds,
    )

    print("=" * 80)
    print("Full daily Steam pipeline finished.")
    print("=" * 80)


def get_unmapped_twitch_categories(
    limit: int,
    retry_after_days: int = 30,
    max_attempts: int = 3,
) -> list[dict]:
    """
    Get Twitch categories that are not mapped to IGDB yet, ordered for the
    crawler backlog.

    We take category ids/names from twitch_game_snapshots because this table
    contains real Twitch categories observed during our Twitch extraction runs.

    Order: categories never searched first (NULLS FIRST), then the ones
    searched longest ago, then -- as a tiebreaker -- the ones with the highest
    peak viewer_count ever observed. The previous `ORDER BY twitch_game_name`
    spent the whole budget on categories starting with digits or punctuation,
    so a high-viewership category could go unsearched indefinitely.

    A category is excluded from the backlog once igdb_search_attempts reaches
    max_attempts, and is skipped until retry_after_days have passed since
    last_igdb_search_at.

    The observed categories are aggregated once in a CTE rather than joined
    row-by-row and collapsed with SELECT DISTINCT. DISTINCT over the raw
    snapshot rows returned one row per distinct (id, name) pair, so a category
    Twitch has renamed appeared twice -- consuming two slots of the crawler's
    LIMIT and sending it to search a name that is no longer current. The name
    is therefore taken from the most recent sample, not picked arbitrarily.
    """

    query = """
        WITH observed AS (
            SELECT
                twitch_game_id,
                MAX(viewer_count) AS max_viewer_count,
                (array_agg(
                    twitch_game_name ORDER BY sample_hour DESC
                ))[1] AS twitch_game_name
            FROM twitch_game_snapshots
            GROUP BY twitch_game_id
        )
        SELECT
            o.twitch_game_id,
            o.twitch_game_name,
            c.last_igdb_search_at,
            o.max_viewer_count
        FROM observed o
        LEFT JOIN twitch_categories c
            ON c.twitch_game_id = o.twitch_game_id
        WHERE
            (c.twitch_game_id IS NULL OR c.mapping_status = 'unmapped')
            AND (c.igdb_search_attempts IS NULL OR c.igdb_search_attempts < %s)
            AND (
                c.last_igdb_search_at IS NULL
                OR c.last_igdb_search_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            )
        ORDER BY
            c.last_igdb_search_at ASC NULLS FIRST,
            o.max_viewer_count DESC NULLS LAST
        LIMIT %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (max_attempts, retry_after_days, limit))
            rows = cursor.fetchall()

    return [
        {
            "twitch_game_id": row[0],
            "twitch_game_name": row[1],
        }
        for row in rows
    ]


def get_steam_games_for_igdb_enrichment(limit: int) -> list[dict]:
    """
    Get Steam games that do not have an IGDB Steam store link yet.

    We prefer Steam Store-enriched games because their names are usually cleaner
    than SteamSpy names.
    """

    query = """
        SELECT
            g.appid,
            g.name
        FROM games g
        LEFT JOIN igdb_game_store_links s
            ON s.store = 'steam'
            AND s.store_game_id = g.appid::TEXT
        WHERE
            s.id IS NULL
            AND g.name IS NOT NULL
            AND g.steam_store_success = TRUE
        ORDER BY
            g.appid
        LIMIT %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

    return [
        {
            "appid": row[0],
            "name": row[1],
        }
        for row in rows
    ]


def get_observed_twitch_categories_for_candidates(limit: int) -> list[dict]:
    """
    Get distinct Twitch categories observed in Twitch stream snapshots.

    We use max viewer_count to prioritize the most important categories.
    """

    query = """
        SELECT
            t.twitch_game_id,
            t.twitch_game_name,
            MAX(t.viewer_count) AS max_viewer_count
        FROM twitch_game_snapshots t
        GROUP BY
            t.twitch_game_id,
            t.twitch_game_name
        ORDER BY
            max_viewer_count DESC
        LIMIT %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

    return [
        {
            "twitch_game_id": row[0],
            "twitch_game_name": row[1],
            "max_viewer_count": row[2],
        }
        for row in rows
    ]


def get_observed_twitch_game_ids_without_catalog(limit: int) -> list[str]:
    """
    Get distinct Twitch game IDs from snapshots that are missing from the catalog.
    """

    query = """
        SELECT DISTINCT t.twitch_game_id
        FROM twitch_game_snapshots t
        LEFT JOIN twitch_categories_catalog c
            ON c.twitch_game_id = t.twitch_game_id
        WHERE c.twitch_game_id IS NULL
        ORDER BY t.twitch_game_id
        LIMIT %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

    return [row[0] for row in rows]


def get_igdb_games_for_candidate_matching() -> list[dict]:
    """
    Get IGDB games available in the local database.
    """

    query = """
        SELECT
            igdb_game_id,
            name,
            slug
        FROM igdb_games
        WHERE name IS NOT NULL
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return [
        {
            "igdb_game_id": row[0],
            "name": row[1],
            "slug": row[2],
        }
        for row in rows
    ]


def get_twitch_catalog_igdb_candidate_rows(limit: int) -> list[dict]:
    """
    Get Twitch catalog rows with IGDB IDs that can become mapping candidates.
    """

    query = """
        SELECT
            c.twitch_game_id,
            c.twitch_game_name,
            c.igdb_id,
            i.name AS igdb_name
        FROM twitch_categories_catalog c
        JOIN igdb_games i
            ON i.igdb_game_id = c.igdb_id
        LEFT JOIN twitch_igdb_mapping_candidates mc
            ON mc.twitch_game_id = c.twitch_game_id
            AND mc.igdb_game_id = c.igdb_id
            AND mc.candidate_method = 'twitch_helix_igdb_id'
        WHERE c.igdb_id IS NOT NULL
          AND mc.id IS NULL
        LIMIT %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

    return [
        {
            "twitch_game_id": row[0],
            "twitch_game_name": row[1],
            "igdb_id": row[2],
            "igdb_name": row[3],
        }
        for row in rows
    ]


def upsert_twitch_igdb_mapping_candidate(candidate: dict) -> None:
    """
    Insert or update one Twitch -> IGDB mapping candidate.

    status is set on INSERT only and is never overwritten by DO UPDATE. The
    weekly mapping DAG re-runs this upsert for every candidate it re-derives;
    if it also overwrote status, it would erase any manual approve/reject a
    human made in the meantime. approve/reject is the human decision the
    fuzzy-match quarantine (rule 4) depends on, so it must survive re-runs.
    """

    query = """
        INSERT INTO twitch_igdb_mapping_candidates (
            twitch_game_id,
            twitch_game_name,
            candidate_entity_type,
            igdb_game_id,
            name_score,
            final_score,
            candidate_method,
            reason,
            status,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (
            twitch_game_id,
            candidate_entity_type,
            igdb_game_id,
            candidate_method
        )
        DO UPDATE SET
            twitch_game_name = EXCLUDED.twitch_game_name,
            name_score = EXCLUDED.name_score,
            final_score = EXCLUDED.final_score,
            reason = EXCLUDED.reason,
            updated_at = CURRENT_TIMESTAMP
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    candidate["twitch_game_id"],
                    candidate["twitch_game_name"],
                    candidate["candidate_entity_type"],
                    candidate["igdb_game_id"],
                    candidate["name_score"],
                    candidate["final_score"],
                    candidate["candidate_method"],
                    candidate["reason"],
                    candidate["status"],
                ),
            )

        connection.commit()


def has_igdb_steam_link(appid: int) -> bool:
    """
    Check if a Steam appid is already linked to an IGDB game.
    """

    query = """
        SELECT EXISTS (
            SELECT 1
            FROM igdb_game_store_links
            WHERE
                store = 'steam'
                AND store_game_id = %s
        )
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (str(appid),))
            return cursor.fetchone()[0]


def run_igdb_search(search_term: str, limit: int) -> Path:
    """
    Search IGDB for one game/category name and load results into PostgreSQL.
    """

    print(f"Searching IGDB for: {search_term}")

    raw_path = run_igdb_game_search(
        search_term=search_term,
        limit=limit,
    )

    load_data("igdb", raw_path)

    return raw_path


def run_twitch_streams(pages: int = 1, delay: float = 1.0) -> None:
    """
    Extract top Twitch live streams and load into twitch_game_snapshots.

    Steps:
    1. Fetch paginated top streams from Twitch Helix /streams.
    2. Save raw JSON to data/raw/twitch/streams/.
    3. Transform and load aggregated game snapshots into PostgreSQL.
    """

    print(f"Fetching {pages} page(s) of Twitch top streams...")

    raw_path = run_twitch_streams_extract(pages=pages, delay=delay)
    count = load_data("twitch", raw_path) or 0

    print(f"Loaded {count} Twitch game snapshots.")


def run_twitch_games_lookup_for_observed(limit: int, batch_size: int) -> None:
    """
    Lookup Twitch category metadata for observed Twitch game IDs.
    """

    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    safe_batch_size = min(batch_size, 100)
    game_ids = get_observed_twitch_game_ids_without_catalog(limit=limit)

    if not game_ids:
        print("No observed Twitch game IDs are missing from the catalog.")
        return

    total_loaded = 0

    print(f"Found {len(game_ids)} observed Twitch game IDs missing from catalog")
    print(f"Batch size: {safe_batch_size}")

    for start_index in range(0, len(game_ids), safe_batch_size):
        batch_ids = game_ids[start_index:start_index + safe_batch_size]
        batch_number = (start_index // safe_batch_size) + 1

        print(
            f"Processing Twitch games lookup batch {batch_number}: "
            f"{len(batch_ids)} IDs"
        )

        raw_path = run_twitch_games_lookup(batch_ids)
        loaded_count = load_data("twitch_games_lookup", raw_path) or 0
        total_loaded += loaded_count

    print(
        "Twitch games lookup for observed categories finished. "
        f"IDs looked up: {len(game_ids)}, "
        f"Catalog rows loaded: {total_loaded}"
    )


def run_generate_twitch_igdb_candidates(
    limit: int,
    min_score: float,
    top_n: int,
) -> None:
    """
    Generate Twitch -> IGDB mapping candidates using fuzzy name matching.

    This does not create final mappings.
    It only stores possible candidates for later review/approval.
    """

    twitch_categories = get_observed_twitch_categories_for_candidates(limit=limit)
    igdb_games = get_igdb_games_for_candidate_matching()

    print(f"Loaded {len(twitch_categories)} Twitch categories")
    print(f"Loaded {len(igdb_games)} IGDB games")

    inserted_candidates = 0
    categories_with_candidates = 0

    for index, category in enumerate(twitch_categories, start=1):
        twitch_game_id = category["twitch_game_id"]
        twitch_game_name = category["twitch_game_name"]

        scored_candidates = []

        for igdb_game in igdb_games:
            score = calculate_name_score(
                twitch_game_name,
                igdb_game["name"],
            )

            if score >= min_score:
                scored_candidates.append(
                    {
                        "igdb_game_id": igdb_game["igdb_game_id"],
                        "igdb_name": igdb_game["name"],
                        "score": score,
                    }
                )

        scored_candidates.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        top_candidates = scored_candidates[:top_n]

        print(
            f"[{index}/{len(twitch_categories)}] "
            f"{twitch_game_name} ({twitch_game_id}) -> "
            f"{len(top_candidates)} candidates"
        )

        if top_candidates:
            categories_with_candidates += 1

        for candidate in top_candidates:
            upsert_twitch_igdb_mapping_candidate(
                {
                    "twitch_game_id": twitch_game_id,
                    "twitch_game_name": twitch_game_name,
                    "candidate_entity_type": "game",
                    "igdb_game_id": candidate["igdb_game_id"],
                    "name_score": candidate["score"],
                    "final_score": candidate["score"],
                    "candidate_method": "fuzzy_name",
                    "reason": (
                        f"Fuzzy name match: Twitch '{twitch_game_name}' "
                        f"vs IGDB '{candidate['igdb_name']}'."
                    ),
                    "status": "pending",
                }
            )

            inserted_candidates += 1

    print(
        "Twitch -> IGDB candidate generation finished. "
        f"Categories processed: {len(twitch_categories)}, "
        f"Categories with candidates: {categories_with_candidates}, "
        f"Candidates inserted/updated: {inserted_candidates}"
    )


def generate_twitch_igdb_candidates_from_catalog(limit: int) -> None:
    """
    Create mapping candidates where Twitch catalog has igdb_id and local IGDB exists.
    """

    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    rows = get_twitch_catalog_igdb_candidate_rows(limit=limit)

    print(f"Loaded {len(rows)} Twitch catalog IGDB candidate rows")

    inserted_candidates = 0

    for row in rows:
        twitch_game_name = row["twitch_game_name"]
        igdb_name = row["igdb_name"]

        if normalize_game_name(twitch_game_name) == normalize_game_name(igdb_name):
            name_score = 1.0
        else:
            name_score = calculate_name_score(twitch_game_name, igdb_name)

        upsert_twitch_igdb_mapping_candidate(
            {
                "twitch_game_id": row["twitch_game_id"],
                "twitch_game_name": twitch_game_name,
                "candidate_entity_type": "game",
                "igdb_game_id": row["igdb_id"],
                "name_score": name_score,
                "final_score": 1.0,
                "candidate_method": "twitch_helix_igdb_id",
                "reason": (
                    "Twitch Helix Get Games returned igdb_id linking this "
                    "Twitch category to IGDB."
                ),
                "status": "auto_approved",
            }
        )

        inserted_candidates += 1

    print(
        "Twitch catalog IGDB candidate generation finished. "
        f"Candidates inserted/updated: {inserted_candidates}"
    )


def run_igdb_enrich_steam(
    limit: int,
    search_limit: int,
    delay: float,
) -> None:
    """
    Search IGDB for Steam games and load results into PostgreSQL.

    This enriches our local IGDB catalog from the Steam games table.
    A game is considered matched if IGDB results contain a Steam store link
    with the same appid.
    """

    games = get_steam_games_for_igdb_enrichment(limit=limit)

    print(f"Found {len(games)} Steam games for IGDB enrichment")

    searched = 0
    matched = 0
    not_matched = 0
    failed = 0

    for index, game in enumerate(games, start=1):
        appid = game["appid"]
        name = game["name"]

        print(f"[{index}/{len(games)}] Searching IGDB for appid {appid}: {name}")

        try:
            raw_path = run_igdb_game_search(
                search_term=name,
                limit=search_limit,
            )

            load_data("igdb", raw_path)

            searched += 1

            if has_igdb_steam_link(appid):
                matched += 1
                print(f"Matched Steam appid {appid} to IGDB")
            else:
                not_matched += 1
                print(f"No IGDB Steam link found for appid {appid}")

        except Exception as exc:
            failed += 1
            print(f"Failed to enrich appid {appid} ({name}): {exc}")

        if index < len(games):
            time.sleep(delay)

    print(
        "IGDB Steam enrichment finished. "
        f"Searched: {searched}, "
        f"Matched: {matched}, "
        f"Not matched: {not_matched}, "
        f"Failed: {failed}"
    )


def mark_twitch_category_as_excluded(
    twitch_game_id: str,
    twitch_game_name: str,
    notes: str,
) -> None:
    """
    Store known non-game Twitch categories as excluded.

    This prevents us from repeatedly searching IGDB for categories like
    Just Chatting or IRL.
    """

    query = """
        INSERT INTO twitch_categories (
            twitch_game_id,
            twitch_game_name,
            is_game,
            igdb_game_id,
            mapping_status,
            mapping_method,
            mapping_confidence,
            notes,
            updated_at
        )
        VALUES (%s, %s, FALSE, NULL, 'excluded', 'non_game_exclusion_list', 1.0, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (twitch_game_id)
        DO UPDATE SET
            twitch_game_name = EXCLUDED.twitch_game_name,
            is_game = EXCLUDED.is_game,
            igdb_game_id = EXCLUDED.igdb_game_id,
            mapping_status = EXCLUDED.mapping_status,
            mapping_method = EXCLUDED.mapping_method,
            mapping_confidence = EXCLUDED.mapping_confidence,
            notes = EXCLUDED.notes,
            updated_at = CURRENT_TIMESTAMP
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    twitch_game_id,
                    twitch_game_name,
                    notes,
                ),
            )

        connection.commit()


def record_igdb_search_attempt(twitch_game_id: str, twitch_game_name: str) -> None:
    """
    Record that an IGDB search was attempted for a Twitch category, whether
    or not it found anything.

    This is bookkeeping about the crawler, not about the mapping outcome, so
    it deliberately does not touch mapping_status. Without this, a category
    IGDB has never heard of is indistinguishable from one we have not asked
    about yet, and get_unmapped_twitch_categories keeps re-selecting it
    forever. mapping_status stays at its column default ('unmapped') on
    first insert, which is correct: this row is still in the backlog, just
    lower priority.
    """

    query = """
        INSERT INTO twitch_categories (
            twitch_game_id,
            twitch_game_name,
            last_igdb_search_at,
            igdb_search_attempts,
            updated_at
        )
        VALUES (%s, %s, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (twitch_game_id)
        DO UPDATE SET
            twitch_game_name = EXCLUDED.twitch_game_name,
            last_igdb_search_at = CURRENT_TIMESTAMP,
            igdb_search_attempts = twitch_categories.igdb_search_attempts + 1,
            updated_at = CURRENT_TIMESTAMP
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    twitch_game_id,
                    twitch_game_name,
                ),
            )

        connection.commit()


def record_igdb_search_error(twitch_game_id: str, twitch_game_name: str) -> None:
    """
    Record that an IGDB search for a Twitch category was attempted but
    failed before it could produce an answer (request error, timeout, etc).

    This is deliberately a separate counter from igdb_search_attempts, which
    counts completed searches (found something or found nothing). "We could
    not ask IGDB" is not the same fact as "IGDB answered and found nothing",
    and should not spend a category's --max-attempts budget of honest tries.

    It still advances last_igdb_search_at, so get_unmapped_twitch_categories'
    retry_after_days cooldown applies and a category that fails every time
    is not stuck at the permanent head of the backlog -- it just comes back
    after the cooldown, indefinitely. mapping_status is not touched, for the
    same reason record_igdb_search_attempt leaves it alone.
    """

    query = """
        INSERT INTO twitch_categories (
            twitch_game_id,
            twitch_game_name,
            last_igdb_search_at,
            igdb_search_errors,
            updated_at
        )
        VALUES (%s, %s, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (twitch_game_id)
        DO UPDATE SET
            twitch_game_name = EXCLUDED.twitch_game_name,
            last_igdb_search_at = CURRENT_TIMESTAMP,
            igdb_search_errors = twitch_categories.igdb_search_errors + 1,
            updated_at = CURRENT_TIMESTAMP
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    twitch_game_id,
                    twitch_game_name,
                ),
            )

        connection.commit()


def run_igdb_enrich_twitch(
    limit: int,
    search_limit: int,
    delay: float,
    retry_after_days: int = 30,
    max_attempts: int = 3,
) -> None:
    """
    Search IGDB for unmapped Twitch categories.

    This is the first version of our Twitch -> IGDB mapping pipeline.

    For each observed Twitch category:
    - skip known non-game categories
    - search IGDB by Twitch category name
    - load IGDB results into PostgreSQL
    - record the attempt, whether the search found something or came back
      empty, so the backlog query can drain instead of re-asking forever
    - if the search itself fails (request error, timeout), record a search
      error instead -- it still resets the backlog cooldown, but does not
      count against --max-attempts, since IGDB never actually answered
    """

    categories = get_unmapped_twitch_categories(
        limit=limit,
        retry_after_days=retry_after_days,
        max_attempts=max_attempts,
    )

    print(f"Found {len(categories)} unmapped Twitch categories")

    searched = 0
    empty = 0
    excluded = 0
    failed = 0

    for index, category in enumerate(categories, start=1):
        twitch_game_id = category["twitch_game_id"]
        twitch_game_name = category["twitch_game_name"]

        print(
            f"[{index}/{len(categories)}] Processing Twitch category: "
            f"{twitch_game_name} ({twitch_game_id})"
        )

        if twitch_game_name in NON_GAME_TWITCH_CATEGORIES:
            mark_twitch_category_as_excluded(
                twitch_game_id=twitch_game_id,
                twitch_game_name=twitch_game_name,
                notes="Known non-game Twitch category.",
            )

            excluded += 1
            print(f"Excluded non-game category: {twitch_game_name}")

            continue

        try:
            raw_path = run_igdb_game_search(
                search_term=twitch_game_name,
                limit=search_limit,
            )

            results_loaded = load_data("igdb", raw_path) or 0

            record_igdb_search_attempt(
                twitch_game_id=twitch_game_id,
                twitch_game_name=twitch_game_name,
            )

            searched += 1

            if results_loaded == 0:
                empty += 1
                print(f"No IGDB results found for: {twitch_game_name}")

        except Exception as exc:
            failed += 1

            record_igdb_search_error(
                twitch_game_id=twitch_game_id,
                twitch_game_name=twitch_game_name,
            )

            print(
                f"Failed to enrich Twitch category "
                f"{twitch_game_name} ({twitch_game_id}): {exc}"
            )

        if index < len(categories):
            time.sleep(delay)

    print(
        "IGDB Twitch enrichment finished. "
        f"Searched: {searched}, "
        f"Empty results: {empty}, "
        f"Excluded: {excluded}, "
        f"Failed: {failed}"
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the pipeline runner.
    """

    parser = argparse.ArgumentParser(
        description="Run Steam Gaming Analytics ETL pipeline."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # Command 1:
    # python -m src.main steamspy-all-page --page 0
    all_page_parser = subparsers.add_parser(
        "steamspy-all-page",
        help="Extract and load one SteamSpy 'all' page.",
    )

    all_page_parser.add_argument(
        "--page",
        type=int,
        default=0,
        help="SteamSpy page number.",
    )

    all_page_parser.add_argument(
        "--snapshot-date",
        help="Snapshot date in YYYY-MM-DD format. Defaults to today in load.py.",
    )

    # Command 2:
    # python -m src.main steamspy-daily --max-pages 2 --delay 5
    daily_parser = subparsers.add_parser(
        "steamspy-daily",
        help="Extract and load all SteamSpy 'all' pages.",
    )

    daily_parser.add_argument(
        "--start-page",
        type=int,
        default=0,
        help="Page to start from.",
    )

    daily_parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of pages to process. Useful for development.",
    )

    daily_parser.add_argument(
        "--delay",
        type=int,
        default=65,
        help="Delay between SteamSpy 'all' page requests in seconds.",
    )

    daily_parser.add_argument(
        "--snapshot-date",
        help="Snapshot date in YYYY-MM-DD format. Defaults to today in load.py.",
    )

    # Command 3:
    # python -m src.main steam-store-appdetails --appid 730
    store_appdetails_parser = subparsers.add_parser(
        "steam-store-appdetails",
        help="Extract and load Steam Store appdetails for one appid.",
    )

    store_appdetails_parser.add_argument(
        "--appid",
        type=int,
        required=True,
        help="Steam appid.",
    )

    # Command 4:
    # python -m src.main steam-store-enrich --limit 100 --delay 1
    store_enrich_parser = subparsers.add_parser(
        "steam-store-enrich",
        help="Enrich games with Steam Store metadata.",
    )

    store_enrich_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of games to enrich.",
    )

    store_enrich_parser.add_argument(
        "--delay",
        type=int,
        default=1,
        help="Delay between Steam Store requests in seconds.",
    )

    store_enrich_parser.add_argument(
        "--refresh-after-days",
        type=int,
        default=30,
        help="Re-enrich games whose Steam Store data is older than this many days.",
    )

    # Command 5:
    # python -m src.main daily --steamspy-max-pages 2 --steamspy-delay 5 --store-limit 20 --store-delay 1
    daily_full_parser = subparsers.add_parser(
        "daily",
        help="Run full daily pipeline: SteamSpy snapshots + Steam Store enrichment.",
    )

    daily_full_parser.add_argument(
        "--steamspy-start-page",
        type=int,
        default=0,
        help="SteamSpy page to start from.",
    )

    daily_full_parser.add_argument(
        "--steamspy-max-pages",
        type=int,
        help="Maximum number of SteamSpy pages to process. Useful for development.",
    )

    daily_full_parser.add_argument(
        "--steamspy-delay",
        type=int,
        default=65,
        help="Delay between SteamSpy 'all' page requests in seconds.",
    )

    daily_full_parser.add_argument(
        "--store-limit",
        type=int,
        default=500,
        help="Maximum number of games to enrich from Steam Store.",
    )

    daily_full_parser.add_argument(
        "--store-delay",
        type=int,
        default=1,
        help="Delay between Steam Store requests in seconds.",
    )

    daily_full_parser.add_argument(
        "--snapshot-date",
        help="Snapshot date in YYYY-MM-DD format. Defaults to today in load.py.",
    )

    igdb_search_parser = subparsers.add_parser(
        "igdb-search",
        help="Search IGDB for one game/category name and load results into PostgreSQL.",
    )

    igdb_search_parser.add_argument(
        "--search",
        required=True,
        help="Game or category name to search in IGDB.",
    )

    igdb_search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of IGDB search results.",
    )

    igdb_enrich_twitch_parser = subparsers.add_parser(
        "igdb-enrich-twitch",
        help="Search IGDB for unmapped Twitch categories.",
    )

    igdb_enrich_twitch_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of unmapped Twitch categories to process.",
    )

    igdb_enrich_twitch_parser.add_argument(
        "--search-limit",
        type=int,
        default=10,
        help="Maximum number of IGDB results per Twitch category.",
    )

    igdb_enrich_twitch_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between IGDB searches.",
    )

    igdb_enrich_twitch_parser.add_argument(
        "--retry-after-days",
        type=int,
        default=30,
        help=(
            "Do not re-search a Twitch category until this many days have "
            "passed since its last IGDB search attempt."
        ),
    )

    igdb_enrich_twitch_parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help=(
            "Drop a Twitch category from the backlog once it has been "
            "searched this many times without becoming mapped."
        ),
    )

    igdb_enrich_steam_parser = subparsers.add_parser(
        "igdb-enrich-steam",
        help="Search IGDB for Steam games and load matching metadata.",
    )

    igdb_enrich_steam_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of Steam games to process.",
    )

    igdb_enrich_steam_parser.add_argument(
        "--search-limit",
        type=int,
        default=10,
        help="Maximum number of IGDB results per Steam game.",
    )

    igdb_enrich_steam_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between IGDB searches.",
    )

    generate_twitch_igdb_candidates_parser = subparsers.add_parser(
        "generate-twitch-igdb-candidates",
        help="Generate Twitch to IGDB mapping candidates using fuzzy matching.",
    )

    generate_twitch_igdb_candidates_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of observed Twitch categories to process.",
    )

    generate_twitch_igdb_candidates_parser.add_argument(
        "--min-score",
        type=float,
        default=0.75,
        help="Minimum fuzzy name score from 0.0 to 1.0.",
    )

    generate_twitch_igdb_candidates_parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Maximum number of candidates to store per Twitch category.",
    )

    # Command: python -m src.main twitch-streams --pages 2 --delay 1.0
    twitch_streams_parser = subparsers.add_parser(
        "twitch-streams",
        help="Extract top Twitch live streams and load into twitch_game_snapshots.",
    )

    twitch_streams_parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="Number of Twitch streams pages to fetch. Each page has up to 100 streams.",
    )

    twitch_streams_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between Twitch API pages.",
    )

    twitch_games_lookup_parser = subparsers.add_parser(
        "twitch-games-lookup",
        help="Lookup Twitch game/category metadata and load it into the catalog.",
    )

    twitch_games_lookup_parser.add_argument(
        "--ids",
        nargs="+",
        required=True,
        help="One or more Twitch game IDs.",
    )

    twitch_games_lookup_observed_parser = subparsers.add_parser(
        "twitch-games-lookup-observed",
        help="Lookup metadata for observed Twitch game IDs missing from the catalog.",
    )

    twitch_games_lookup_observed_parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of observed Twitch game IDs to lookup.",
    )

    twitch_games_lookup_observed_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum Twitch game IDs per lookup request. Values above 100 are capped.",
    )

    generate_twitch_igdb_candidates_from_catalog_parser = subparsers.add_parser(
        "generate-twitch-igdb-candidates-from-catalog",
        help="Generate high-confidence Twitch to IGDB candidates from Twitch igdb_id.",
    )

    generate_twitch_igdb_candidates_from_catalog_parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of catalog-backed candidates to generate.",
    )

    # Command: python -m src.main migrate
    subparsers.add_parser(
        "migrate",
        help="Apply pending SQL migrations from sql/migrations in filename order.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Main CLI entry point.
    """

    args = parse_args()

    if args.command == "steamspy-all-page":
        if args.page < 0:
            raise ValueError("--page cannot be negative")

        run_steamspy_all_page(
            page=args.page,
            snapshot_date=args.snapshot_date,
        )

    elif args.command == "steamspy-daily":
        if args.start_page < 0:
            raise ValueError("--start-page cannot be negative")

        if args.max_pages is not None and args.max_pages <= 0:
            raise ValueError("--max-pages must be a positive integer")

        if args.delay < 0:
            raise ValueError("--delay cannot be negative")

        run_steamspy_daily(
            start_page=args.start_page,
            max_pages=args.max_pages,
            delay_seconds=args.delay,
            snapshot_date=args.snapshot_date,
        )

    elif args.command == "steam-store-appdetails":
        if args.appid <= 0:
            raise ValueError("--appid must be a positive integer")

        run_steam_store_appdetails(appid=args.appid)

    elif args.command == "steam-store-enrich":
        if args.limit <= 0:
            raise ValueError("--limit must be a positive integer")

        if args.delay < 0:
            raise ValueError("--delay cannot be negative")

        if args.refresh_after_days <= 0:
            raise ValueError("--refresh-after-days must be a positive integer")

        run_steam_store_enrich(
            limit=args.limit,
            delay_seconds=args.delay,
            refresh_after_days=args.refresh_after_days,
        )

    elif args.command == "daily":
        if args.steamspy_start_page < 0:
            raise ValueError("--steamspy-start-page cannot be negative")

        if args.steamspy_max_pages is not None and args.steamspy_max_pages <= 0:
            raise ValueError("--steamspy-max-pages must be a positive integer")

        if args.steamspy_delay < 0:
            raise ValueError("--steamspy-delay cannot be negative")

        if args.store_limit <= 0:
            raise ValueError("--store-limit must be a positive integer")

        if args.store_delay < 0:
            raise ValueError("--store-delay cannot be negative")

        run_daily_pipeline(
            steamspy_start_page=args.steamspy_start_page,
            steamspy_max_pages=args.steamspy_max_pages,
            steamspy_delay_seconds=args.steamspy_delay,
            store_limit=args.store_limit,
            store_delay_seconds=args.store_delay,
            snapshot_date=args.snapshot_date,
        )

    elif args.command == "igdb-search":
        run_igdb_search(
            search_term=args.search,
            limit=args.limit,
        )

    elif args.command == "igdb-enrich-twitch":
        run_igdb_enrich_twitch(
            limit=args.limit,
            search_limit=args.search_limit,
            delay=args.delay,
            retry_after_days=args.retry_after_days,
            max_attempts=args.max_attempts,
        )

    elif args.command == "igdb-enrich-steam":
        run_igdb_enrich_steam(
            limit=args.limit,
            search_limit=args.search_limit,
            delay=args.delay,
        )

    elif args.command == "generate-twitch-igdb-candidates":
        run_generate_twitch_igdb_candidates(
            limit=args.limit,
            min_score=args.min_score,
            top_n=args.top_n,
        )

    elif args.command == "twitch-streams":
        if args.pages < 1:
            raise ValueError("--pages must be at least 1")

        if args.delay < 0:
            raise ValueError("--delay cannot be negative")

        run_twitch_streams(
            pages=args.pages,
            delay=args.delay,
        )

    elif args.command == "twitch-games-lookup":
        raw_path = run_twitch_games_lookup(args.ids)
        load_data("twitch_games_lookup", raw_path)

    elif args.command == "twitch-games-lookup-observed":
        run_twitch_games_lookup_for_observed(
            limit=args.limit,
            batch_size=args.batch_size,
        )

    elif args.command == "generate-twitch-igdb-candidates-from-catalog":
        generate_twitch_igdb_candidates_from_catalog(limit=args.limit)

    elif args.command == "migrate":
        run_migrations()


if __name__ == "__main__":
    main()
