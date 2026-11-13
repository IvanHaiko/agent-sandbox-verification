import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from src.db import get_db_connection
from src.transform import (
    parse_steam_store_envelope,
    transform_igdb_search_results,
    transform_steam_store_game,
    transform_steamspy_game,
    transform_twitch_games_lookup,
    transform_twitch_streams,
)


# Fixed messages for the two envelope outcomes that do not carry their own
# error text (fetch_appdetails only fills "error" for transport_error).
# refused and not_found used to collapse into the same free-text string in
# steam_store_last_error; keeping them as distinct constants is what keeps
# them apart in the column.
STEAM_STORE_OUTCOME_MESSAGES = {
    "refused": "Steam Store returned success=false",
    "not_found": "No Steam Store response wrapper found",
}


def load_json_file(file_path: Path) -> dict[str, Any]:
    """
    Load a JSON file and return its content as a Python object.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def insert_game(
    cursor,
    game: dict[str, Any],
    source: str,
    fetched_at: str | None = None,
) -> None:
    """
    Insert or update a game record.

    Steam Store data has higher priority for stable game fields,
    because it usually contains more accurate game metadata.

    fetched_at (source == "steam_store" only) is the envelope's own fetch
    timestamp, not the load time -- it is what makes steam_store_attempts
    idempotent under a bronze replay (see the CASE expression below).
    """

    if source == "steam_store":
        # steam_store_success is a generated column (migration 014) --
        # this INSERT/UPDATE writes steam_store_outcome only, and the
        # boolean follows on its own. steam_store_redirect_to is cleared
        # because an "ok" load, whether from a direct fetch or from
        # loading a redirect's target metadata, is never itself a
        # redirect.
        #
        # steam_store_attempts only increments when this fetch's
        # timestamp differs from the one already on the row (migration
        # 015) -- reaching this branch always means Steam answered "ok",
        # but reaching it can also mean "the exact same bronze file was
        # just loaded a second time" (rule 2: a failed load re-runs
        # without re-hitting the API), which must never look like a
        # second real attempt. Two legacy files (fetched_at unknown, so
        # NULL) for the same appid loaded back to back would collide
        # here and under-count -- accepted, because legacy files can only
        # ever be outcome "ok" and no cooldown or ceiling for "ok" reads
        # steam_store_attempts at all, so the undercount changes no
        # decision.
        cursor.execute(
            """
            INSERT INTO games (
                appid,
                name,
                developer,
                publisher,
                is_free,
                release_date,
                header_image,
                steam_store_updated_at,
                steam_store_outcome,
                steam_store_redirect_to,
                steam_store_attempts,
                steam_store_last_error,
                steam_store_fetched_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'ok', NULL, 1, NULL, %s)
            ON CONFLICT (appid) DO UPDATE
            SET
                name = COALESCE(EXCLUDED.name, games.name),
                developer = COALESCE(EXCLUDED.developer, games.developer),
                publisher = COALESCE(EXCLUDED.publisher, games.publisher),
                is_free = COALESCE(EXCLUDED.is_free, games.is_free),
                release_date = COALESCE(EXCLUDED.release_date, games.release_date),
                header_image = COALESCE(EXCLUDED.header_image, games.header_image),
                steam_store_updated_at = CURRENT_TIMESTAMP,
                steam_store_outcome = 'ok',
                steam_store_redirect_to = NULL,
                steam_store_attempts = CASE
                    WHEN games.steam_store_fetched_at IS NOT DISTINCT FROM EXCLUDED.steam_store_fetched_at
                    THEN COALESCE(games.steam_store_attempts, 0)
                    ELSE COALESCE(games.steam_store_attempts, 0) + 1
                END,
                steam_store_errors = 0,
                steam_store_last_error = NULL,
                steam_store_fetched_at = EXCLUDED.steam_store_fetched_at,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (
                game["appid"],
                game["name"],
                game["developer"],
                game["publisher"],
                game["is_free"],
                game["release_date"],
                game["header_image"],
                fetched_at,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO games (
                appid,
                name,
                developer,
                publisher,
                is_free,
                release_date,
                header_image
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (appid) DO UPDATE
            SET
                name = COALESCE(games.name, EXCLUDED.name),
                developer = COALESCE(games.developer, EXCLUDED.developer),
                publisher = COALESCE(games.publisher, EXCLUDED.publisher),
                is_free = COALESCE(games.is_free, EXCLUDED.is_free),
                release_date = COALESCE(games.release_date, EXCLUDED.release_date),
                header_image = COALESCE(games.header_image, EXCLUDED.header_image),
                updated_at = CURRENT_TIMESTAMP;
            """,
            (
                game["appid"],
                game["name"],
                game["developer"],
                game["publisher"],
                game["is_free"],
                game["release_date"],
                game["header_image"],
            ),
        )


def insert_snapshot(
    cursor,
    snapshot: dict[str, Any] | None,
    snapshot_date: str,
) -> None:
    """
    Insert or update a daily game snapshot.
    """

    if snapshot is None:
        return

    cursor.execute(
        """
        INSERT INTO game_snapshots (
            appid,
            snapshot_date,
            positive,
            negative,
            total_reviews,
            review_score,
            owners,
            price,
            initialprice,
            discount,
            ccu
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (appid, snapshot_date) DO UPDATE
        SET
            positive = EXCLUDED.positive,
            negative = EXCLUDED.negative,
            total_reviews = EXCLUDED.total_reviews,
            review_score = EXCLUDED.review_score,
            owners = EXCLUDED.owners,
            price = EXCLUDED.price,
            initialprice = EXCLUDED.initialprice,
            discount = EXCLUDED.discount,
            ccu = EXCLUDED.ccu;
        """,
        (
            snapshot["appid"],
            snapshot_date,
            snapshot["positive"],
            snapshot["negative"],
            snapshot["total_reviews"],
            snapshot["review_score"],
            snapshot["owners"],
            snapshot["price"],
            snapshot["initialprice"],
            snapshot["discount"],
            snapshot["ccu"],
        ),
    )


def get_or_create_genre(cursor, genre_name: str) -> int:
    """
    Insert a genre if it does not exist and return its genre_id.
    """

    cursor.execute(
        """
        INSERT INTO genres (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING
        RETURNING genre_id;
        """,
        (genre_name,),
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    cursor.execute(
        """
        SELECT genre_id
        FROM genres
        WHERE name = %s;
        """,
        (genre_name,),
    )

    return cursor.fetchone()[0]


def insert_game_genres(
    cursor,
    appid: int,
    genres: list[str],
) -> None:
    """
    Insert genre records and link them to a game.
    """

    for genre_name in genres:
        genre_id = get_or_create_genre(cursor, genre_name)

        cursor.execute(
            """
            INSERT INTO game_genres (appid, genre_id)
            VALUES (%s, %s)
            ON CONFLICT (appid, genre_id) DO NOTHING;
            """,
            (appid, genre_id),
        )


def insert_twitch_game_snapshot(connection, snapshot: dict) -> None:
    """
    Insert or update one aggregated Twitch game snapshot.

    One row represents Twitch attention for one game at one observed hour.
    The business key is (sample_hour, twitch_game_id): sample_hour is
    date_trunc('hour', sample_time), and sample_time is the real observation
    instant carried through from the raw JSON's fetched_at by
    transform_twitch_streams. snapshot_time keeps its old meaning of "row
    insert time" and is not touched here.

    sample_time_source is always written as 'bronze' here: this function only
    ever runs against a raw file that has already been saved to disk, and
    sample_time above is fetched_at from that same file by construction (see
    transform_twitch_streams / parse_twitch_fetched_at). 'load_clock' -- the
    other value the column allows -- describes historical rows backfilled
    before bronze existed, in migration 010; the loader itself never has a
    reason to write it.

    A conflict on the same hour means a retried or re-run load for that
    sampling window -- typically an Airflow retry after a partial failure --
    so the most recent attempt is assumed to be the more complete one and
    wins.
    """

    sample_time = snapshot["sample_time"]
    sample_hour = sample_time.replace(minute=0, second=0, microsecond=0)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO twitch_game_snapshots (
                twitch_game_id,
                twitch_game_name,
                viewer_count,
                stream_count,
                sample_time,
                sample_hour,
                sample_time_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'bronze')
            ON CONFLICT (sample_hour, twitch_game_id) DO UPDATE
            SET
                twitch_game_name = EXCLUDED.twitch_game_name,
                viewer_count = EXCLUDED.viewer_count,
                stream_count = EXCLUDED.stream_count,
                sample_time = EXCLUDED.sample_time,
                sample_time_source = EXCLUDED.sample_time_source
            """,
            (
                snapshot["twitch_game_id"],
                snapshot["twitch_game_name"],
                snapshot["viewer_count"],
                snapshot["stream_count"],
                sample_time,
                sample_hour,
            ),
        )


def upsert_igdb_game(connection, game: dict) -> None:
    """
    Insert or update one IGDB game.

    IGDB is our global game catalog.
    It is separate from Steam-specific games.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO igdb_games (
                igdb_game_id,
                name,
                slug,
                summary,
                url,
                first_release_date,
                rating,
                rating_count,
                aggregated_rating,
                aggregated_rating_count,
                total_rating,
                total_rating_count,
                hypes,
                follows,
                game_type,
                game_type_label,
                status,
                status_label,
                raw_json,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (igdb_game_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                summary = EXCLUDED.summary,
                url = EXCLUDED.url,
                first_release_date = EXCLUDED.first_release_date,
                rating = EXCLUDED.rating,
                rating_count = EXCLUDED.rating_count,
                aggregated_rating = EXCLUDED.aggregated_rating,
                aggregated_rating_count = EXCLUDED.aggregated_rating_count,
                total_rating = EXCLUDED.total_rating,
                total_rating_count = EXCLUDED.total_rating_count,
                hypes = EXCLUDED.hypes,
                follows = EXCLUDED.follows,
                game_type = EXCLUDED.game_type,
                game_type_label = EXCLUDED.game_type_label,
                status = EXCLUDED.status,
                status_label = EXCLUDED.status_label,
                raw_json = EXCLUDED.raw_json,
                updated_at = CURRENT_TIMESTAMP
            WHERE (
                igdb_games.name,
                igdb_games.slug,
                igdb_games.summary,
                igdb_games.url,
                igdb_games.first_release_date,
                igdb_games.rating,
                igdb_games.rating_count,
                igdb_games.aggregated_rating,
                igdb_games.aggregated_rating_count,
                igdb_games.total_rating,
                igdb_games.total_rating_count,
                igdb_games.hypes,
                igdb_games.follows,
                igdb_games.game_type,
                igdb_games.game_type_label,
                igdb_games.status,
                igdb_games.status_label,
                igdb_games.raw_json
            ) IS DISTINCT FROM (
                EXCLUDED.name,
                EXCLUDED.slug,
                EXCLUDED.summary,
                EXCLUDED.url,
                EXCLUDED.first_release_date,
                EXCLUDED.rating,
                EXCLUDED.rating_count,
                EXCLUDED.aggregated_rating,
                EXCLUDED.aggregated_rating_count,
                EXCLUDED.total_rating,
                EXCLUDED.total_rating_count,
                EXCLUDED.hypes,
                EXCLUDED.follows,
                EXCLUDED.game_type,
                EXCLUDED.game_type_label,
                EXCLUDED.status,
                EXCLUDED.status_label,
                EXCLUDED.raw_json
            )
            """,
            (
                game["igdb_game_id"],
                game["name"],
                game["slug"],
                game["summary"],
                game["url"],
                game["first_release_date"],
                game["rating"],
                game["rating_count"],
                game["aggregated_rating"],
                game["aggregated_rating_count"],
                game["total_rating"],
                game["total_rating_count"],
                game["hypes"],
                game["follows"],
                game["game_type"],
                game["game_type_label"],
                game["status"],
                game["status_label"],
                json.dumps(game["raw_json"]),
            ),
        )


def upsert_igdb_game_store_link(connection, link: dict) -> None:
    """
    Insert or update one IGDB store link.

    Store links represent distribution platforms:
    Steam, Epic, GOG, Microsoft/Xbox, PlayStation, Nintendo.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO igdb_game_store_links (
                igdb_game_id,
                store,
                store_game_id,
                store_url
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (store, store_game_id)
            DO UPDATE SET
                igdb_game_id = EXCLUDED.igdb_game_id,
                store_url = EXCLUDED.store_url
            """,
            (
                link["igdb_game_id"],
                link["store"],
                link["store_game_id"],
                link["store_url"],
            ),
        )


def upsert_twitch_category(connection, category: dict) -> None:
    """
    Insert or update one Twitch category mapping.

    Twitch categories are not stores.
    Some are games, some are non-game categories.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
            WHERE (
                twitch_categories.twitch_game_name,
                twitch_categories.is_game,
                twitch_categories.igdb_game_id,
                twitch_categories.mapping_status,
                twitch_categories.mapping_method,
                twitch_categories.mapping_confidence,
                twitch_categories.notes
            ) IS DISTINCT FROM (
                EXCLUDED.twitch_game_name,
                EXCLUDED.is_game,
                EXCLUDED.igdb_game_id,
                EXCLUDED.mapping_status,
                EXCLUDED.mapping_method,
                EXCLUDED.mapping_confidence,
                EXCLUDED.notes
            )
            """,
            (
                category["twitch_game_id"],
                category["twitch_game_name"],
                category["is_game"],
                category["igdb_game_id"],
                category["mapping_status"],
                category["mapping_method"],
                category["mapping_confidence"],
                category["notes"],
            ),
        )


def upsert_twitch_category_catalog(connection, category: dict) -> None:
    """
    Insert/update one Twitch category catalog row.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO twitch_categories_catalog (
                twitch_game_id,
                twitch_game_name,
                box_art_url,
                igdb_id,
                source,
                first_seen_at,
                last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (twitch_game_id)
            DO UPDATE SET
                twitch_game_name = EXCLUDED.twitch_game_name,
                box_art_url = EXCLUDED.box_art_url,
                igdb_id = EXCLUDED.igdb_id,
                source = EXCLUDED.source,
                last_seen_at = CURRENT_TIMESTAMP;
            """,
            (
                category["twitch_game_id"],
                category["twitch_game_name"],
                category["box_art_url"],
                category["igdb_id"],
                category["source"],
            ),
        )


def load_transformed_record(
    cursor,
    transformed_record: dict[str, Any] | None,
    snapshot_date: str,
    fetched_at: str | None = None,
) -> None:
    """
    Load one transformed record into PostgreSQL.

    fetched_at is only meaningful for source == "steam_store" -- see
    insert_game.
    """

    if transformed_record is None:
        return

    source = transformed_record["source"]
    game = transformed_record["game"]
    snapshot = transformed_record["snapshot"]
    genres = transformed_record["genres"]

    insert_game(cursor, game, source, fetched_at=fetched_at)
    insert_snapshot(cursor, snapshot, snapshot_date)
    insert_game_genres(cursor, game["appid"], genres)


def iter_steamspy_games(raw_data: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Yield SteamSpy game objects from different SteamSpy response shapes.

    SteamSpy appdetails returns one game object:
    {
        "appid": 730,
        "name": "Counter-Strike: Global Offensive",
        ...
    }

    SteamSpy all/top responses return a dictionary of games:
    {
        "730": {...},
        "570": {...}
    }
    """

    if "appid" in raw_data:
        yield raw_data
    else:
        yield from raw_data.values()


def load_steamspy_file(file_path: Path, snapshot_date: str) -> None:
    """
    Load a SteamSpy JSON file into PostgreSQL.
    """

    raw_data = load_json_file(file_path)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for raw_game in iter_steamspy_games(raw_data):
                transformed_record = transform_steamspy_game(raw_game)
                load_transformed_record(cursor, transformed_record, snapshot_date)


def _load_steam_store_ok(
    envelope: dict[str, Any],
    snapshot_date: str,
    file_path: Path,
) -> str:
    """
    Load the games-table side of an "ok" envelope.

    Returns the outcome actually recorded, which is "ok" unless the body
    turns out not to parse into a game after all (see below).
    """

    transformed_record = transform_steam_store_game(envelope["body"])

    if transformed_record is None:
        # An envelope claiming "ok" whose body does not actually parse
        # into a game (e.g. no steam_appid, or -- for a legacy file --
        # an embedded success: false that the legacy shape cannot tell
        # apart from a real ok) is a data problem worth surfacing, not a
        # silent no-op.
        appid = envelope.get("appid")

        if appid:
            # Real envelopes always carry an appid, so this is the
            # ordinary path: record it as "refused" (we have no confirmed
            # game data for this appid, the same fact "refused" already
            # means) with a message that says specifically why.
            mark_steam_store_enrichment_result(
                appid=appid,
                outcome="refused",
                error_message="ok envelope did not yield a parsable game",
                fetched_at=envelope.get("fetched_at"),
                is_replay=True,
            )

            return "refused"

        # Only a legacy file (no "envelope" key) ever reaches here with
        # no appid -- parse_steam_store_envelope's legacy fallback always
        # sets appid to None, and legacy files are unconditionally read
        # as outcome "ok" regardless of what their embedded body actually
        # says. If that body's real success field is false, transform
        # correctly returns None here, but with no appid there is no
        # games row to mark against -- previously this branch was a
        # complete no-op: no exception, no log line, no database write.
        # None of the 3 194 files on disk hit this today (checked while
        # writing this fix), but the path must be loud the day one does,
        # not silently vanish it.
        raise ValueError(
            f"Legacy Steam Store file {file_path} was read as outcome "
            "'ok' (the unconditional legacy fallback) but its body did "
            "not yield a parsable game -- most likely an embedded "
            "success: false that the legacy shape cannot distinguish "
            "from a real ok. Refusing to silently drop it."
        )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            load_transformed_record(
                cursor,
                transformed_record,
                snapshot_date,
                fetched_at=envelope.get("fetched_at"),
            )

    return "ok"


def _load_steam_store_redirected(
    envelope: dict[str, Any],
    appid: int,
    snapshot_date: str,
) -> str:
    """
    Load the games-table side of a "redirected" envelope.

    The body is a real Steam Store answer -- just about a different
    appid than the one requested. It is loaded into the games table under
    the appid Steam actually described (transform_steam_store_game reads
    appid from data.steam_appid, not from the envelope), exactly as an
    "ok" response for that appid would be. The *requested* appid's own
    row never receives this game's metadata -- that would put, for
    example, appid 100's name on Counter-Strike: Condition Zero's data,
    which is appid 80's game. It only records the fact and direction of
    the redirect via mark_steam_store_enrichment_result below, which is
    also what makes the requested appid terminal in
    get_games_for_store_enrichment's backlog query.
    """

    redirect_to = envelope.get("redirect_to")
    target_record = transform_steam_store_game(envelope["body"])

    if target_record is not None:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                load_transformed_record(
                    cursor,
                    target_record,
                    snapshot_date,
                    fetched_at=envelope.get("fetched_at"),
                )

    mark_steam_store_enrichment_result(
        appid=appid,
        outcome="redirected",
        error_message=f"Steam Store redirected appid {appid} to {redirect_to}",
        redirect_to=redirect_to,
        fetched_at=envelope.get("fetched_at"),
        is_replay=True,
    )

    return "redirected"


def load_steam_store_file(file_path: Path, snapshot_date: str) -> str:
    """
    Load a Steam Store appdetails bronze file into PostgreSQL.

    The file may hold any of five outcomes (see
    transform.parse_steam_store_envelope): "ok" and "redirected" both load
    game metadata (for the requested appid and the target appid,
    respectively); "refused", "not_found" and "transport_error" already
    have their bronze on disk by the time this runs, and only update the
    games row's steam_store_outcome / steam_store_last_error via
    mark_steam_store_enrichment_result, so a refusal is recorded rather
    than silently producing no database change at all.

    Returns the outcome that was recorded, so a caller (run_steam_store_
    enrich in src/main.py) can tally all five outcomes separately instead
    of treating every non-exception return as "processed".
    """

    raw_data = load_json_file(file_path)
    envelope = parse_steam_store_envelope(raw_data)
    outcome = envelope["outcome"]

    if outcome == "ok":
        return _load_steam_store_ok(envelope, snapshot_date, file_path)

    appid = envelope.get("appid")

    if not appid:
        # No business key to mark against; the bronze file on disk is
        # still the record of what happened. This should not occur for
        # any file this loader actually wrote (fetch_appdetails always
        # carries appid), only if a hand-edited file omitted it.
        return outcome

    if outcome == "redirected":
        return _load_steam_store_redirected(envelope, appid, snapshot_date)

    if outcome == "transport_error":
        error_message = envelope.get("error") or "Steam Store transport error"
    else:
        error_message = STEAM_STORE_OUTCOME_MESSAGES.get(
            outcome, f"Steam Store outcome: {outcome}"
        )

    fetched_at = envelope.get("fetched_at")

    mark_steam_store_enrichment_result(
        appid=appid,
        outcome=outcome,
        error_message=error_message[:1000],
        fetched_at=fetched_at,
        is_replay=True,
    )

    return outcome


def load_twitch_file(file_path: str | Path) -> int:
    """
    Load Twitch raw streams JSON into twitch_game_snapshots.

    Raw Twitch data contains individual streams.
    We transform them into aggregated game-level snapshots first.
    """

    raw_data = load_json_file(Path(file_path))
    snapshots = transform_twitch_streams(raw_data)

    with get_db_connection() as connection:
        for snapshot in snapshots:
            insert_twitch_game_snapshot(connection, snapshot)

        connection.commit()

    print(f"Loaded {len(snapshots)} Twitch game snapshots")

    return len(snapshots)


def load_twitch_games_lookup_file(file_path: str | Path) -> int:
    """
    Load Twitch games lookup raw JSON into twitch_categories_catalog.
    """

    raw_data = load_json_file(Path(file_path))
    categories = transform_twitch_games_lookup(raw_data)

    with get_db_connection() as connection:
        for category in categories:
            upsert_twitch_category_catalog(connection, category)

        connection.commit()

    print(f"Loaded {len(categories)} Twitch category catalog rows")

    return len(categories)


def load_igdb_file(file_path: str | Path) -> int:
    """
    Load IGDB raw game search JSON into PostgreSQL.

    One raw search file can contain multiple IGDB games.

    For each game we load:
    - igdb_games
    - igdb_game_store_links
    - twitch_categories, if IGDB has Twitch external UID
    """

    raw_data = load_json_file(Path(file_path))
    records = transform_igdb_search_results(raw_data)

    if not records:
        return 0

    loaded_games = 0
    loaded_store_links = 0
    loaded_twitch_categories = 0

    # Multiple games can claim the same category. Keep the existing last-game
    # precedence without transient remapping that advances updated_at on replay.
    final_categories = {
        category["twitch_game_id"]: category
        for record in records
        for category in record["twitch_categories"]
    }

    with get_db_connection() as connection:
        for record in records:
            upsert_igdb_game(connection, record["igdb_game"])
            loaded_games += 1

            for link in record["store_links"]:
                upsert_igdb_game_store_link(connection, link)
                loaded_store_links += 1

            for category in record["twitch_categories"]:
                if final_categories[category["twitch_game_id"]] is category:
                    upsert_twitch_category(connection, category)
                loaded_twitch_categories += 1

        connection.commit()

    print(
        "Loaded IGDB data: "
        f"{loaded_games} games, "
        f"{loaded_store_links} store links, "
        f"{loaded_twitch_categories} Twitch categories"
    )

    return loaded_games


def load_data(
    source: str,
    file_path: str | Path,
    snapshot_date: str | None = None,
) -> int | str | None:
    """
    Load a raw JSON file into PostgreSQL based on source type.

    This function is used by pipeline orchestrators like src/main.py.
    Most sources return a row count; "steam_store" returns the outcome
    string recorded (see load_steam_store_file), since "how many rows"
    is not the useful fact for a source whose whole point is classifying
    which of several outcomes a single appid got.
    """

    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if source == "steamspy":
        load_steamspy_file(file_path, snapshot_date)
    elif source == "steam_store":
        return load_steam_store_file(file_path, snapshot_date)
    elif source == "twitch":
        return load_twitch_file(file_path)
    elif source == "twitch_games_lookup":
        return load_twitch_games_lookup_file(file_path)
    elif source == "igdb":
        return load_igdb_file(file_path)
    else:
        raise ValueError(f"Unsupported source: {source}")


STEAM_STORE_MARKABLE_OUTCOMES = {
    "refused",
    "not_found",
    "redirected",
    "transport_error",
}


def mark_steam_store_enrichment_result(
    appid: int,
    outcome: str,
    error_message: str | None = None,
    redirect_to: int | None = None,
    fetched_at: str | None = None,
    is_replay: bool = False,
) -> None:
    """
    Record a Steam Store enrichment attempt that did not load game
    metadata directly -- "ok" is recorded inside insert_game() as part of
    loading the game itself, and never reaches this function.

    steam_store_attempts counts every outcome where Steam actually
    answered (refused, not_found, redirected); steam_store_errors counts
    only transport_error, on its own counter, so a failure to *ask* never
    spends one of the chances meant for an actual *answer* (see
    ARCHITECTURE.md 2.1 and migration 011's identical split for the IGDB
    backlog). redirect_to is only ever non-null for outcome ==
    "redirected"; every other call passes None, which clears any stale
    value a prior redirect may have left.

    fetched_at is the envelope's own fetch timestamp. It stays None for
    transport_error: no answer arrived, so no moment of receiving one
    exists, and inventing it would repeat the mistake migration 010 had to
    undo for Twitch and migration 013 for is_free. The time of the
    *attempt* is steam_store_updated_at, which is set on every outcome.

    is_replay says this call re-reads a stored bronze file and may
    therefore be repeating an answer already counted, in which case
    fetched_at identifies it and an identical one leaves the counters
    alone. Re-loading a file is an expected recovery path: rule 2 says a
    failed *load* re-runs without re-hitting the API.

    The flag defaults to False, meaning "this is a new event, count it".
    Forgetting it on a path that reads a file over-counts, which shows up
    in the counters and can be corrected. The opposite default would let a
    caller with no fetched_at -- the unexpected-exception path in
    run_steam_store_enrich -- compare NULL against NULL, match, and record
    a real failure as nothing at all. Silent under-counting is the class of
    defect the whole of Phase 0 exists to remove, so the unsafe direction
    is the one that has to be spelled out.

    steam_store_errors resets to zero on every answered outcome, so it
    counts *consecutive* failures on our side. A lifetime counter would
    mean three unrelated network blips across years permanently removed a
    game from the catalogue, and a fault of ours must never be a harsher
    consequence than a refusal by Steam, which carries no ceiling at all.
    """

    if appid <= 0:
        raise ValueError("appid must be a positive integer")

    if outcome not in STEAM_STORE_MARKABLE_OUTCOMES:
        raise ValueError(
            f"mark_steam_store_enrichment_result does not accept "
            f"outcome={outcome!r}; expected one of "
            f"{sorted(STEAM_STORE_MARKABLE_OUTCOMES)}. 'ok' is recorded by "
            "insert_game, and 'failed_legacy' is only ever written by "
            "migration 014's one-time backfill, never by the loader."
        )

    answered = outcome != "transport_error"

    attempts_increment = 1 if answered else 0
    errors_increment = 0 if answered else 1

    # An answer of any kind clears the consecutive-failure counter, even on
    # a replay: setting it to zero twice is the same as setting it once.
    errors_expression = (
        "0"
        if answered
        else """CASE
                        WHEN %s AND steam_store_fetched_at IS NOT DISTINCT FROM %s
                        THEN COALESCE(steam_store_errors, 0)
                        ELSE COALESCE(steam_store_errors, 0) + %s
                    END"""
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE games
                SET
                    steam_store_updated_at = CURRENT_TIMESTAMP,
                    steam_store_outcome = %s,
                    steam_store_redirect_to = %s,
                    steam_store_attempts = CASE
                        WHEN %s AND steam_store_fetched_at IS NOT DISTINCT FROM %s
                        THEN COALESCE(steam_store_attempts, 0)
                        ELSE COALESCE(steam_store_attempts, 0) + %s
                    END,
                    steam_store_errors = {errors_expression},
                    steam_store_last_error = %s,
                    steam_store_fetched_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE appid = %s;
                """,
                (
                    outcome,
                    redirect_to,
                    is_replay,
                    fetched_at,
                    attempts_increment,
                    *(() if answered else (is_replay, fetched_at, errors_increment)),
                    error_message,
                    fetched_at,
                    appid,
                ),
            )


def get_games_for_store_enrichment(
    limit: int = 100,
    refresh_after_days: int = 30,
) -> list[int]:
    """
    Get appids for games that need Steam Store metadata enrichment.

    Cooldown and attempt ceiling follow the last attempt's outcome, not
    one shared rule for every row -- that is the entire reason
    steam_store_outcome is an enum instead of a boolean (see
    ARCHITECTURE.md 2.1):

    - steam_store_outcome IS NULL (never asked): always eligible, no
      cooldown.
    - "ok": refresh_after_days (default 30, caller-controlled) -- the
      pre-existing behaviour, unchanged.
    - "refused" and "failed_legacy": 30 days, no attempt ceiling. A
      refusal often means unreleased, region-locked, or temporarily
      hidden, and any of those can change; a ceiling would permanently
      drop a game whose announcement-to-release gap runs past three
      30-day cycles. failed_legacy (migration 014's backfill for rows
      whose specific failure kind was never recorded) is treated as
      "refused" rather than "not_found" because 30 days is the more
      cautious of the two guesses -- it returns the game to circulation
      instead of freezing it on an assumption.
    - "not_found": 90 days, no attempt ceiling. Missing entirely from the
      catalogue usually means removed, so it is checked less often than a
      refusal, but for the same reason as above it is never dropped for
      good on a guess.
    - "transport_error": an escalating pause of 1, 2, 4, 8, 16 then 30
      days, capped at 30, driven by steam_store_errors -- which counts
      *consecutive* failures and is reset to zero by any answer. There is
      no ceiling and no terminal state: the failure is on our side, and a
      fault of ours must never remove a game from the catalogue when a
      refusal by Steam does not. An earlier version stopped re-asking
      after three lifetime errors, which meant three unrelated outages
      across years silently shrank the universe.
    - "redirected": excluded entirely (not present in any branch below).
      The requested appid will never answer for itself again -- see
      _load_steam_store_redirected -- so there is nothing to cool down,
      it simply never re-qualifies.
    """

    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    if refresh_after_days <= 0:
        raise ValueError("refresh_after_days must be a positive integer")

    query = """
        SELECT appid
        FROM games
        WHERE
            steam_store_outcome IS NULL
            OR (
                steam_store_outcome = 'ok'
                AND steam_store_updated_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            )
            OR (
                steam_store_outcome IN ('refused', 'failed_legacy')
                AND steam_store_updated_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
            )
            OR (
                steam_store_outcome = 'not_found'
                AND steam_store_updated_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
            )
            OR (
                steam_store_outcome = 'transport_error'
                AND steam_store_updated_at < CURRENT_TIMESTAMP - (
                    LEAST(
                        30,
                        POWER(2, GREATEST(COALESCE(steam_store_errors, 1), 1) - 1)
                    ) * INTERVAL '1 day'
                )
            )
        ORDER BY
            steam_store_updated_at NULLS FIRST,
            appid
        LIMIT %s;
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (refresh_after_days, limit))
            rows = cursor.fetchall()

    return [row[0] for row in rows]


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Load Steam raw JSON data into PostgreSQL."
    )

    parser.add_argument(
        "source",
        choices=["steamspy", "steam_store", "twitch", "twitch_games_lookup", "igdb"],
        help="Data source type.",
    )

    parser.add_argument(
        "file_path",
        help="Path to the raw JSON file.",
    )

    parser.add_argument(
        "--snapshot-date",
        default=date.today().isoformat(),
        help="Snapshot date in YYYY-MM-DD format. Defaults to today.",
    )

    return parser.parse_args()


def main() -> None:
    """
    CLI entry point for loading transformed Steam data into PostgreSQL.
    """

    args = parse_args()
    file_path = Path(args.file_path)

    load_data(
        source=args.source,
        file_path=file_path,
        snapshot_date=args.snapshot_date,
    )

    print("Load completed successfully.")
    print(f"Source: {args.source}")
    print(f"File: {file_path}")
    print(f"Snapshot date: {args.snapshot_date}")


if __name__ == "__main__":
    main()
