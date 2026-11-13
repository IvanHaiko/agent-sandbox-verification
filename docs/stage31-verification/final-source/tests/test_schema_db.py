"""
The schema, built from scratch and checked by behaviour.

These tests assert what the database *does*, never what a migration file says.
A constraint is proven by violating it, not by finding its name in `pg_constraint`
— the string form of a check is exactly the kind of assertion that passed while
`ON CONFLICT (snapshot_time, twitch_game_id)` was silently unreachable.
"""

import re

import psycopg
import pytest

from tests.conftest import ROOT


def test_every_migration_applied(test_database):
    """The chain applies end to end on an empty database, with nothing skipped."""

    from src.db import get_db_connection

    on_disk = {p.name for p in (ROOT / "sql" / "migrations").glob("*.sql")}

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT filename FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}

    assert on_disk, "no migrations found — the fixture built nothing"
    assert applied == on_disk, f"not applied: {sorted(on_disk - applied)}"


def test_migrations_are_idempotent(test_database):
    """Re-running the runner applies nothing and raises nothing."""

    from src.db import get_db_connection
    from src.migrations import run_migrations

    run_migrations(ROOT / "sql" / "migrations")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM schema_migrations")
            after = cursor.fetchone()[0]

    assert after == len(list((ROOT / "sql" / "migrations").glob("*.sql")))


def test_filename_order_matches_numeric_order():
    """
    The runner applies files in *filename* order, so filename order must agree
    with the numbers a human reads.

    `006` is absent from the sequence, which is harmless — but adding it later
    would apply it after `007`, and a three-digit prefix stops sorting correctly
    the day someone writes `1000_`. This test fails on that day rather than in
    production.
    """

    names = sorted(p.name for p in (ROOT / "sql" / "migrations").glob("*.sql"))
    numbers = [int(re.match(r"(\d+)", n).group(1)) for n in names]

    assert numbers == sorted(numbers), f"filename order disagrees with numbers: {names}"
    assert all(len(re.match(r"(\d+)", n).group(1)) == 3 for n in names), (
        "a prefix that is not three digits breaks filename ordering"
    )


def test_snapshot_is_unique_per_game_and_day(db):
    """A day's snapshot for one game cannot be stored twice."""

    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO games (appid, name) VALUES (1, 'x') ON CONFLICT DO NOTHING"
        )
        cursor.execute(
            "INSERT INTO game_snapshots (appid, snapshot_date) VALUES (1, '2026-05-09')"
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            cursor.execute(
                "INSERT INTO game_snapshots (appid, snapshot_date) VALUES (1, '2026-05-09')"
            )


def test_twitch_sample_is_unique_per_hour_and_category(db):
    """
    The key that was broken for months: two rows for the same category in the
    same observation hour must be impossible.

    Before migration 008 the conflict target contained `snapshot_time`, which
    defaults to the insert clock, so two loads four milliseconds apart both
    landed.
    """

    row = (
        "INSERT INTO twitch_game_snapshots "
        "(sample_hour, twitch_game_id, twitch_game_name, viewer_count, stream_count) "
        "VALUES ('2026-05-14 09:00', '32399', 'Counter-Strike', 100, 5)"
    )

    with db.cursor() as cursor:
        cursor.execute(row)
        with pytest.raises(psycopg.errors.UniqueViolation):
            cursor.execute(row)


def test_steam_store_outcome_rejects_an_unknown_value(db):
    """Only the five recorded outcomes, plus the legacy marker, are storable."""

    with db.cursor() as cursor:
        cursor.execute("INSERT INTO games (appid, name) VALUES (2, 'y')")
        with pytest.raises(psycopg.errors.CheckViolation):
            cursor.execute(
                "UPDATE games SET steam_store_outcome = 'probably_fine' WHERE appid = 2"
            )


@pytest.mark.parametrize(
    "outcome, expected",
    [("ok", True), ("refused", False), ("not_found", False), ("failed_legacy", False)],
)
def test_success_flag_is_derived_not_stored(db, outcome, expected):
    """
    `steam_store_success` is generated from the outcome, so the two cannot drift.

    Proven by writing only the outcome and reading back the boolean.
    """

    with db.cursor() as cursor:
        cursor.execute("INSERT INTO games (appid, name) VALUES (3, 'z')")
        cursor.execute(
            "UPDATE games SET steam_store_outcome = %s WHERE appid = 3", (outcome,)
        )
        cursor.execute("SELECT steam_store_success FROM games WHERE appid = 3")
        assert cursor.fetchone()[0] is expected


def test_success_flag_cannot_be_written_directly(db):
    """A generated column refuses assignment — that is what makes drift impossible."""

    with db.cursor() as cursor:
        cursor.execute("INSERT INTO games (appid, name) VALUES (4, 'w')")
        # Named precisely: a bare `psycopg.errors.Error` would also be satisfied
        # by UndefinedColumn, so dropping the column entirely would leave this
        # test green and still reading as proof that it is generated.
        with pytest.raises(psycopg.errors.GeneratedAlways):
            cursor.execute(
                "UPDATE games SET steam_store_success = true WHERE appid = 4"
            )


def test_sample_time_source_rejects_an_unknown_value(db):
    """`bronze` or `load_clock` — the provenance flag cannot hold prose."""

    with db.cursor() as cursor:
        with pytest.raises(psycopg.errors.CheckViolation):
            cursor.execute(
                "INSERT INTO twitch_game_snapshots "
                "(sample_hour, twitch_game_id, twitch_game_name, sample_time_source) "
                "VALUES ('2026-05-14 10:00', '1', 'a', 'probably_bronze')"
            )
