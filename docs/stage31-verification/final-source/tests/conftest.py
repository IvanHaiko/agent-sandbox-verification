"""
Shared fixtures for the tests that use a real PostgreSQL database.

Why a real database at all: the 120 tests that mock the connection cannot fail
on invalid SQL. A `SELECT DISTINCT` with an `ORDER BY` expression outside the
select list passed the whole suite and failed only against Postgres. Neither can
a mocked connection prove idempotency — `ON CONFLICT (snapshot_time, …)` read as
protection for months while `snapshot_time` defaulted to the insert clock and
the clause could never match.

The tests here run against a **separate database** on the same server
(`steam_analytics_test` by default), built from `create_tables.sql` plus every
migration in order, and dropped afterwards. The working database is never
touched: a different database, not merely a different schema, so a mistaken
unqualified statement cannot reach real rows.
"""

import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

load_dotenv(ROOT / ".env")

TEST_DB_NAME = os.getenv("POSTGRES_TEST_DB", "steam_analytics_test")

#: Set in CI. Turns "the server is unreachable" from a skip into a failure —
#: a suite that silently skips its only real tests reports green for the wrong
#: reason, which is the failure mode this whole file exists to remove.
REQUIRE_DB = os.getenv("REQUIRE_DB_TESTS") == "1"


def _admin_connection() -> psycopg.Connection:
    """Connect to the maintenance database; CREATE DATABASE needs autocommit."""

    return psycopg.connect(
        dbname="postgres",
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        autocommit=True,
    )


def _server_reachable() -> str | None:
    """Return None if the server answers, otherwise the reason it did not."""

    try:
        with _admin_connection():
            return None
    except psycopg.OperationalError as exc:
        return str(exc).strip().splitlines()[0]


@pytest.fixture(scope="session")
def test_database() -> str:
    """
    Create `steam_analytics_test` from scratch, apply the full migration chain,
    yield its name, drop it at the end.

    `POSTGRES_DB` is repointed for the whole session, so every function under
    test reaches the test database through the ordinary `get_db_connection()`
    without knowing it is under test.
    """

    working_db = os.getenv("POSTGRES_DB")
    if TEST_DB_NAME == working_db:
        pytest.fail(
            f"POSTGRES_TEST_DB is {TEST_DB_NAME!r}, the same as POSTGRES_DB. "
            "The next statement in this fixture is an unconditional DROP DATABASE, "
            "so this is refused rather than trusted to the environment."
        )

    reason = _server_reachable()
    if reason is not None:
        message = f"PostgreSQL is not reachable: {reason}"
        if REQUIRE_DB:
            pytest.fail(message + " (REQUIRE_DB_TESTS=1)")
        pytest.skip(message + " — start it with `docker compose up -d postgres`")

    with _admin_connection() as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')

    original_db = os.environ.get("POSTGRES_DB")
    os.environ["POSTGRES_DB"] = TEST_DB_NAME

    try:
        from src.db import get_db_connection
        from src.migrations import run_migrations

        base_schema = (ROOT / "sql" / "create_tables.sql").read_text(encoding="utf-8")
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(base_schema)
            connection.commit()

        run_migrations(ROOT / "sql" / "migrations")

        yield TEST_DB_NAME
    finally:
        if original_db is None:
            os.environ.pop("POSTGRES_DB", None)
        else:
            os.environ["POSTGRES_DB"] = original_db

        with _admin_connection() as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')


@pytest.fixture
def db(test_database):
    """A connection to the test database, rolled back and closed after the test."""

    from src.db import get_db_connection

    connection = get_db_connection()
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _clean_tables(request):
    """
    Empty every data table before each database test.

    `schema_migrations` is deliberately preserved: it records what the session
    built, and truncating it would invite a re-run of migrations that are
    already applied.
    """

    if "test_database" not in request.fixturenames:
        yield
        return

    from src.db import get_db_connection

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename <> 'schema_migrations'
                """
            )
            tables = [row[0] for row in cursor.fetchall()]
            if tables:
                names = ", ".join(f'"{t}"' for t in tables)
                cursor.execute(f"TRUNCATE {names} RESTART IDENTITY CASCADE")
        connection.commit()

    yield


@pytest.fixture
def fixture_path():
    """Resolve a name under tests/fixtures/, failing loudly if it is missing."""

    def _resolve(name: str) -> Path:
        path = FIXTURES / name
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing — see tests/fixtures/README.md; fixtures are "
                "cut from data/raw/, never written by hand"
            )
        return path

    return _resolve


def table_digest(connection, table: str, columns: str = "*") -> tuple[int, str]:
    """
    Row count and an order-independent digest of a table's contents.

    Used by the idempotency tests: a loader run twice must not change either
    number. The count alone is not enough — a second run that overwrites values
    in place leaves the count untouched, which is exactly how a same-hour
    re-write produced an hour matching no single observation.
    """

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        count = cursor.fetchone()[0]
        cursor.execute(
            f"""
            SELECT coalesce(md5(string_agg(row_hash, '' ORDER BY row_hash)), '')
            FROM (SELECT md5(t::text) AS row_hash
                  FROM (SELECT {columns} FROM {table}) t) hashed
            """
        )
        digest = cursor.fetchone()[0]

    return count, digest
