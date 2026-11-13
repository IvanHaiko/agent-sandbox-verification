"""
Queries executed against the real schema, and the retry policy proven by behaviour.

Every function here was previously covered only by tests that asserted on the
SQL *string* against a fake connection. That is how a `SELECT DISTINCT` with an
`ORDER BY` expression outside the select list — rejected by Postgres, always —
passed the entire suite and failed on the live database.

The smoke tests below are deliberately dull: call it, on an empty schema, and let
Postgres parse it. The behavioural tests encode the retry decisions from
`ARCHITECTURE.md` 2.1, where the cost of being wrong is not an exception but a
crawler that quietly never asks again.
"""

import pytest


def seed_game(appid, outcome=None, updated_days_ago=None, errors=0):
    """Insert a game in a chosen enrichment state."""

    from src.db import get_db_connection

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO games (appid, name) VALUES (%s, %s) "
                "ON CONFLICT (appid) DO NOTHING",
                (appid, f"game-{appid}"),
            )
            if outcome is not None:
                cursor.execute(
                    """
                    UPDATE games
                    SET steam_store_outcome = %s,
                        steam_store_errors = %s,
                        steam_store_updated_at = CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
                    WHERE appid = %s
                    """,
                    (outcome, errors, updated_days_ago, appid),
                )
        connection.commit()


# --------------------------------------------------------------------------
# Smoke: the SQL is valid and the function returns what it promises
# --------------------------------------------------------------------------


def test_read_queries_are_valid_sql(test_database):
    """
    Every read path runs against the real schema.

    An empty result is a fine outcome — the point is that Postgres accepted the
    statement. A mocked connection accepts anything, including syntax Postgres
    never would.
    """

    from src import main
    from src.load import get_games_for_store_enrichment

    assert get_games_for_store_enrichment(limit=5) == []
    assert main.get_unmapped_twitch_categories(limit=5) == []
    assert main.get_steam_games_for_igdb_enrichment(limit=5) == []
    assert main.get_observed_twitch_categories_for_candidates(limit=5) == []
    assert main.get_observed_twitch_game_ids_without_catalog(limit=5) == []
    assert main.get_igdb_games_for_candidate_matching() == []
    assert main.get_twitch_catalog_igdb_candidate_rows(limit=5) == []
    assert main.has_igdb_steam_link(730) is False


@pytest.mark.parametrize("bad_limit", [0, -1])
def test_backlog_rejects_a_meaningless_limit(test_database, bad_limit):
    from src.load import get_games_for_store_enrichment

    with pytest.raises(ValueError):
        get_games_for_store_enrichment(limit=bad_limit)


# --------------------------------------------------------------------------
# The retry policy, per outcome
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome, days_ago, errors, eligible, why",
    [
        (None, None, 0, True, "never asked — always eligible, no cooldown"),
        ("ok", 10, 0, False, "refreshed 30 days, not yet"),
        ("ok", 40, 0, True, "refresh window passed"),
        ("refused", 10, 0, False, "refusal cools down 30 days"),
        ("refused", 40, 0, True, "a refusal can become an answer — unreleased ships"),
        ("failed_legacy", 40, 0, True, "treated as refused: the cautious guess"),
        ("not_found", 40, 0, False, "removed from the catalogue: 90 days"),
        ("not_found", 100, 0, True, "still checked eventually, never dropped for good"),
        ("redirected", 400, 0, False, "terminal — it will never answer for itself"),
        ("transport_error", 0, 1, False, "first failure pauses one day"),
        ("transport_error", 2, 1, True, "one day passed"),
        ("transport_error", 10, 5, False, "fifth consecutive failure pauses 16 days"),
        ("transport_error", 20, 5, True, "16 days passed"),
        (
            "transport_error",
            40,
            99,
            True,
            "the pause is capped at 30 days, never terminal",
        ),
    ],
)
def test_enrichment_backlog_follows_the_outcome(
    test_database, outcome, days_ago, errors, eligible, why
):
    """
    Cooldown depth follows what the outcome says about the future, not one
    number for everything. The `redirected` and capped-`transport_error` rows
    are the two that matter most: the first must never return, the second must
    never stop returning.
    """

    from src.load import get_games_for_store_enrichment

    seed_game(4242, outcome=outcome, updated_days_ago=days_ago, errors=errors)
    backlog = get_games_for_store_enrichment(limit=10)

    assert (4242 in backlog) is eligible, why


def test_a_fault_of_ours_never_removes_a_game_permanently(test_database):
    """
    99 consecutive transport errors still leave the game eligible after the
    capped pause.

    The first version of this policy benched a game after three lifetime errors,
    which made our own network worse for a game than a refusal by Steam — which
    carries no ceiling at all.
    """

    from src.load import get_games_for_store_enrichment

    seed_game(777, outcome="transport_error", updated_days_ago=31, errors=99)

    assert 777 in get_games_for_store_enrichment(limit=10)


# --------------------------------------------------------------------------
# Crawler bookkeeping: asking and failing to ask are different facts
# --------------------------------------------------------------------------


def read_category(twitch_game_id):
    from src.db import get_db_connection

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT igdb_search_attempts, igdb_search_errors "
                "FROM twitch_categories WHERE twitch_game_id = %s",
                (twitch_game_id,),
            )
            return cursor.fetchone()


def test_a_search_that_found_nothing_is_recorded(test_database):
    """
    Without this the crawler cannot tell "IGDB has never heard of it" from "we
    have not asked yet", and re-requests the same categories forever.
    """

    from src.main import record_igdb_search_attempt

    record_igdb_search_attempt("29595", "Dota 2")
    assert read_category("29595") == (1, 0)

    record_igdb_search_attempt("29595", "Dota 2")
    assert read_category("29595") == (2, 0)


def test_a_failure_to_ask_spends_a_different_budget(test_database):
    """
    An error must not consume an attempt: "IGDB answered, nothing found" and
    "we could not reach IGDB" are different facts about the same category.

    Called twice on purpose. The first call inserts, and a review proved that
    stopping there never reaches the `ON CONFLICT DO UPDATE` branch — the one
    that would spend an attempt if someone added the wrong column to it. A test
    that exercises only the INSERT path protects nothing on the second failure,
    which is the interesting one.
    """

    from src.main import record_igdb_search_error

    record_igdb_search_error("32399", "Counter-Strike")
    assert read_category("32399") == (0, 1)

    record_igdb_search_error("32399", "Counter-Strike")
    assert read_category("32399") == (0, 2), "consecutive failures must accumulate"


def test_an_error_after_an_answer_does_not_spend_an_attempt(test_database):
    """The two counters stay independent when both paths touch the same row."""

    from src.main import record_igdb_search_attempt, record_igdb_search_error

    record_igdb_search_attempt("29595", "Dota 2")
    record_igdb_search_error("29595", "Dota 2")

    assert read_category("29595") == (1, 1)


def test_recorded_categories_leave_the_backlog(test_database):
    """The whole point of the bookkeeping: the head of the queue must move."""

    from src.db import get_db_connection
    from src.main import get_unmapped_twitch_categories, record_igdb_search_attempt

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for game_id, name in [("29595", "Dota 2"), ("32399", "Counter-Strike")]:
                cursor.execute(
                    "INSERT INTO twitch_game_snapshots "
                    "(sample_hour, twitch_game_id, twitch_game_name, viewer_count) "
                    "VALUES ('2026-05-14 09:00', %s, %s, 1000)",
                    (game_id, name),
                )
        connection.commit()

    before = get_unmapped_twitch_categories(limit=10)
    assert len(before) == 2

    record_igdb_search_attempt("29595", "Dota 2")
    after = get_unmapped_twitch_categories(limit=10, max_attempts=1)

    assert len(after) == 1, "a recorded attempt did not shrink the backlog"


# --------------------------------------------------------------------------
# The human decision the quarantine depends on
# --------------------------------------------------------------------------


def test_a_reupsert_does_not_reset_a_reviewed_candidate(test_database):
    """
    The weekly DAG re-derives every candidate. If the upsert also wrote status,
    a human approve or reject would be erased on the next Sunday — silently, and
    with no record that a decision had ever been made.
    """

    from src.db import get_db_connection
    from src.main import upsert_twitch_igdb_mapping_candidate

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO igdb_games (igdb_game_id, name, raw_json) "
                "VALUES (115, 'League of Legends', '{}')"
            )
        connection.commit()

    candidate = {
        "twitch_game_id": "21779",
        "twitch_game_name": "League of Legends",
        "candidate_entity_type": "game",
        "igdb_game_id": 115,
        "name_score": 1.0,
        "final_score": 1.0,
        "candidate_method": "twitch_helix_igdb_id",
        "reason": "helix",
        "status": "auto_approved",
    }
    upsert_twitch_igdb_mapping_candidate(candidate)

    # the same candidate re-derived by a later run, defaulting to pending
    upsert_twitch_igdb_mapping_candidate({**candidate, "status": "pending"})

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM twitch_igdb_mapping_candidates "
                "WHERE twitch_game_id = '21779'"
            )
            assert cursor.fetchone()[0] == "auto_approved"
