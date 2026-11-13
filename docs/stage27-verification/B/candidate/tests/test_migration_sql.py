"""Lexical boundaries and migration atomicity, including real PostgreSQL."""

from uuid import uuid4

import psycopg
import pytest
from psycopg import sql as pg_sql

from src import migrations
from src.db import get_db_connection
from src.sql_statements import split_sql_statements
from tests.test_migrations import FakeConnection


@pytest.mark.parametrize(
    "source, expected",
    [
        (" ;\n; SELECT 1; SELECT 2 ", ["SELECT 1", "SELECT 2"]),
        ("-- only; ' $$\r/* nested /* ; */ */; -- eof", []),
        (
            "-- lead;\rSELECT 'a;''b'; /* tail; */ SELECT 2; -- end",
            ["-- lead;\rSELECT 'a;''b'", "/* tail; */ SELECT 2"],
        ),
        (r"SELECT 'a\'; SELECT 2;", [r"SELECT 'a\'", "SELECT 2"]),
        ('SELECT "a;""b"; SELECT 2', ['SELECT "a;""b"', 'SELECT 2']),
        (
            r"SELECT E'a\';b', e'c\\'';d'; SELECT 2;",
            [r"SELECT E'a\';b', e'c\\'';d'", "SELECT 2"],
        ),
        (
            "DO $$ BEGIN PERFORM ';'; -- ' /*\n END; $$; SELECT 2",
            ["DO $$ BEGIN PERFORM ';'; -- ' /*\n END; $$", "SELECT 2"],
        ),
        (
            "SELECT $Tag_9$a;$tag_9$;$$;/*$Tag_9$; SELECT 2",
            ["SELECT $Tag_9$a;$tag_9$;$$;/*$Tag_9$", "SELECT 2"],
        ),
        (
            "SELECT foo$tag$, bar$$, $1; SELECT 2",
            ["SELECT foo$tag$, bar$$, $1", "SELECT 2"],
        ),
        (
            r"SELECT nameE'a\'; SELECT 2;",
            [r"SELECT nameE'a\'", "SELECT 2"],
        ),
        (
            "/* ' $$ -- ; /* deeper */ */ SELECT 1 -- ;\n; SELECT 2",
            ["/* ' $$ -- ; /* deeper */ */ SELECT 1 -- ;", "SELECT 2"],
        ),
        ("SELECT 1 -- eof ; ' /*", ["SELECT 1 -- eof ; ' /*"]),
        ("-- crlf ;\r\nSELECT 1;-- lf ;\nSELECT 2", [
            "-- crlf ;\r\nSELECT 1", "-- lf ;\nSELECT 2",
        ]),
    ],
)
def test_split_preserves_sql_regions(source, expected):
    original = source
    assert split_sql_statements(source) == expected
    assert source == original


@pytest.mark.parametrize(
    "unfinished",
    ["'abc", '"abc', "E'abc\\", "e'abc\\'", "$$abc", "$Tag$abc$tag$",
     "/* abc", "/* outer /* inner */"],
)
def test_split_rejects_unterminated_regions(unfinished):
    with pytest.raises(ValueError, match="^Unterminated SQL"):
        split_sql_statements("SELECT 1; " + unfinished)


def test_runner_validates_whole_file_before_execution(monkeypatch, tmp_path):
    (tmp_path / "001_bad.sql").write_text("SELECT 123; SELECT 'unfinished")
    connection = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: connection)

    with pytest.raises(ValueError, match="^Unterminated SQL"):
        migrations.run_migrations(tmp_path)

    assert connection.committed == 1
    assert not any("SELECT 123" in query for query, _ in connection.executed_queries)
    assert not any(params for _, params in connection.executed_queries)


def test_runner_executes_fragments_and_records_empty_files(monkeypatch, tmp_path):
    (tmp_path / "002_text.sql").write_text("SELECT 'café;'; SELECT 2", encoding="utf-8")
    (tmp_path / "001_empty.sql").write_text("-- comment;\n/* nested /* ; */ */;")
    (tmp_path / "ignored.txt").write_text("SELECT 'broken")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "000_bad.sql").write_text("SELECT 'broken")
    connection = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: connection)

    migrations.run_migrations(tmp_path)

    assert connection.committed == 3
    queries = connection.executed_queries[2:]
    assert queries == [
        ("INSERT INTO schema_migrations (filename) VALUES (%s)", ("001_empty.sql",)),
        ("SELECT 'café;'", None),
        ("SELECT 2", None),
        ("INSERT INTO schema_migrations (filename) VALUES (%s)", ("002_text.sql",)),
    ]


@pytest.fixture
def migration_schema_db(test_database, monkeypatch):
    """Give the runner a private schema inside the existing disposable database."""
    schema = "migration_sql_" + uuid4().hex
    with get_db_connection() as connection:
        connection.execute(pg_sql.SQL("CREATE SCHEMA {}").format(pg_sql.Identifier(schema)))

    def connect():
        connection = get_db_connection()
        connection.execute(
            pg_sql.SQL("SET search_path TO {}").format(pg_sql.Identifier(schema))
        )
        connection.commit()
        return connection

    monkeypatch.setattr(migrations, "get_db_connection", connect)
    try:
        yield connect
    finally:
        with get_db_connection() as connection:
            connection.execute(
                pg_sql.SQL("DROP SCHEMA {} CASCADE").format(pg_sql.Identifier(schema))
            )


def test_runner_quoted_bodies_and_rerun_db(migration_schema_db, tmp_path):
    first = tmp_path / "001_bodies.sql"
    first.write_text(
        r"""
        CREATE TABLE "values;table" (value text);
        /* outer ; /* inner ; */ still outer */
        CREATE FUNCTION value_text() RETURNS text LANGUAGE plpgsql AS $Body$
        BEGIN
            RETURN 'function;value';
        END;
        $Body$;
        DO $$ BEGIN
            INSERT INTO "values;table" VALUES (value_text());
            INSERT INTO "values;table" VALUES (E'escaped\';quote');
        END; $$;
        INSERT INTO "values;table" VALUES ('café;''quoted')
        """,
        encoding="utf-8",
    )
    (tmp_path / "002_comments.sql").write_text("/* only /* ; */ comments */ -- eof")

    migrations.run_migrations(tmp_path)
    # Applied filenames are skipped even when their contents have since changed.
    first.write_text("SELECT 'unterminated")
    migrations.run_migrations(tmp_path)

    with migration_schema_db() as connection:
        assert connection.execute(
            'SELECT value FROM "values;table" ORDER BY value'
        ).fetchall() == [("café;'quoted",), ("escaped';quote",), ("function;value",)]
        assert connection.execute(
            "SELECT filename FROM schema_migrations ORDER BY filename"
        ).fetchall() == [("001_bodies.sql",), ("002_comments.sql",)]


def test_runner_failure_rolls_back_only_current_file_db(migration_schema_db, tmp_path):
    (tmp_path / "001_good.sql").write_text(
        "CREATE TABLE kept (value text); INSERT INTO kept VALUES ('committed;value');"
    )
    failing = tmp_path / "002_bad.sql"
    failing.write_text(
        "CREATE TABLE discarded (value text);"
        "INSERT INTO kept VALUES ('rolled;back'); SELECT 1 / 0;"
    )

    with pytest.raises(psycopg.errors.DivisionByZero):
        migrations.run_migrations(tmp_path)

    with migration_schema_db() as connection:
        assert connection.execute("SELECT * FROM kept").fetchall() == [("committed;value",)]
        assert connection.execute("SELECT to_regclass('discarded')").fetchone() == (None,)
        assert connection.execute("SELECT filename FROM schema_migrations").fetchall() == [
            ("001_good.sql",)
        ]

    failing.write_text("CREATE TABLE discarded (value text); INSERT INTO kept VALUES ('fixed');")
    migrations.run_migrations(tmp_path)
    migrations.run_migrations(tmp_path)
    with migration_schema_db() as connection:
        assert connection.execute("SELECT * FROM kept ORDER BY value").fetchall() == [
            ("committed;value",), ("fixed",)
        ]
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone() == (2,)
