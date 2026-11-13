"""Migration SQL and transaction regressions against real PostgreSQL."""

from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from src.migrations import run_migrations


@pytest.fixture
def migration_case(db, tmp_path):
    """Give each case its own schema and remove only its migration records."""
    schema = f"migration_test_{uuid4().hex}"
    db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    db.commit()
    try:
        yield db, tmp_path, schema
    finally:
        db.rollback()
        db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        filenames = [path.name for path in tmp_path.glob("*.sql")]
        db.execute(
            "DELETE FROM schema_migrations WHERE filename = ANY(%s)",
            (filenames,),
        )
        db.commit()


def test_complete_sql_and_noop_files_are_applied_once(migration_case):
    db, directory, schema = migration_case
    migration = directory / f"001_{schema}_messages.sql"
    migration.write_text(
        f"""-- A line comment; must not become a separate statement.
CREATE TABLE {schema}.messages (body TEXT NOT NULL);
/* A block comment; must also remain intact. */
INSERT INTO {schema}.messages VALUES ('one;two');
DO $migration$
BEGIN
    INSERT INTO {schema}.messages VALUES ('three;four');
END;
$migration$;
""",
        encoding="utf-8",
    )
    (directory / f"002_{schema}_blank.sql").write_text(" \n\t", encoding="utf-8")
    (directory / f"003_{schema}_comment.sql").write_text(
        "-- A comment-only file;\n/* Another comment; */\n", encoding="utf-8"
    )

    run_migrations(directory)
    run_migrations(directory)

    assert db.execute(f"SELECT body FROM {schema}.messages ORDER BY body").fetchall() == [
        ("one;two",),
        ("three;four",),
    ]
    filenames = sorted(path.name for path in directory.glob("*.sql"))
    assert db.execute(
        "SELECT filename FROM schema_migrations "
        "WHERE filename = ANY(%s) ORDER BY filename",
        (filenames,),
    ).fetchall() == [(name,) for name in filenames]


def test_failed_file_rolls_back_and_corrected_retry_is_safe(migration_case):
    db, directory, schema = migration_case
    first = directory / f"001_{schema}_setup.sql"
    second = directory / f"002_{schema}_failing.sql"
    first.write_text(
        f"CREATE TABLE {schema}.messages (body TEXT NOT NULL);"
        f"INSERT INTO {schema}.messages VALUES ('committed');",
        encoding="utf-8",
    )
    second.write_text(
        f"CREATE TABLE {schema}.rolled_back (id INTEGER);"
        f"INSERT INTO {schema}.messages VALUES ('must roll back');"
        "SELECT 1 / 0;",
        encoding="utf-8",
    )

    with pytest.raises(psycopg.errors.DivisionByZero):
        run_migrations(directory)

    assert db.execute(f"SELECT body FROM {schema}.messages").fetchall() == [
        ("committed",)
    ]
    assert db.execute("SELECT to_regclass(%s)", (f"{schema}.rolled_back",)).fetchone() == (
        None,
    )
    assert db.execute(
        "SELECT filename FROM schema_migrations WHERE filename = ANY(%s)",
        ([first.name, second.name],),
    ).fetchall() == [(first.name,)]

    second.write_text(
        f"CREATE TABLE {schema}.rolled_back (id INTEGER);"
        f"INSERT INTO {schema}.messages VALUES ('retried');",
        encoding="utf-8",
    )
    run_migrations(directory)
    run_migrations(directory)

    assert db.execute(f"SELECT body FROM {schema}.messages ORDER BY body").fetchall() == [
        ("committed",),
        ("retried",),
    ]
    assert db.execute(
        "SELECT filename FROM schema_migrations "
        "WHERE filename = ANY(%s) ORDER BY filename",
        ([first.name, second.name],),
    ).fetchall() == [(first.name,), (second.name,)]
