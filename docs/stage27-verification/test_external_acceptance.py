"""Coordinator-authored from the frozen contract before either implementation exists."""
import importlib
import os
from pathlib import Path
import uuid

import psycopg
from psycopg import sql as pgsql
import pytest


@pytest.fixture
def split():
    return importlib.import_module("src.sql_statements").split_sql_statements


@pytest.mark.parametrize(("source", "expected"), [
    (" ; ; \n", []),
    ("-- only ; ' $$\r/* outer /* inner ; */ end */;", []),
    (" SELECT 1 ; SELECT 2 ", ["SELECT 1", "SELECT 2"]),
    ("SELECT 'a;b'';c';SELECT 2;", ["SELECT 'a;b'';c'", "SELECT 2"]),
    ('SELECT "a;""b"; SELECT 2', ['SELECT "a;""b"', "SELECT 2"]),
    (r"SELECT E'a\';b', e'c\\';SELECT 2", [r"SELECT E'a\';b', e'c\\'", "SELECT 2"]),
    ("SELECT 'a\\';SELECT 2", ["SELECT 'a\\'", "SELECT 2"]),
    ("DO $$ BEGIN PERFORM ';'; END $$; SELECT 2", ["DO $$ BEGIN PERFORM ';'; END $$", "SELECT 2"]),
    ("SELECT $Ab_9$ '; $$ $ab_9$ -- /* $Ab_9$;SELECT 2", ["SELECT $Ab_9$ '; $$ $ab_9$ -- /* $Ab_9$", "SELECT 2"]),
    ("SELECT 1 /* a ; /* ' $$ */ b */;-- comment ;\rSELECT 2;-- eof", ["SELECT 1 /* a ; /* ' $$ */ b */", "-- comment ;\rSELECT 2"]),
    ("SELECT 1-- ;\n;SELECT 2", ["SELECT 1-- ;", "SELECT 2"]),
    ("SELECT a$tag$, $1; SELECT 2", ["SELECT a$tag$, $1", "SELECT 2"]),
    ("SELECT someE'x\\';SELECT 2", ["SELECT someE'x\\'", "SELECT 2"]),
    ("/* retained */ SELECT 1; /* comment only */", ["/* retained */ SELECT 1"]),
])
def test_lexical_regions(split, source, expected):
    assert split(source) == expected


@pytest.mark.parametrize("source", [
    "SELECT 1; SELECT 'broken", 'SELECT 1; SELECT "broken',
    "SELECT 1; DO $$broken", "SELECT $tag$broken$TAG$",
    "SELECT 1; /* outer /* inner */", r"SELECT E'broken\'",
])
def test_unterminated_rejected(split, source):
    with pytest.raises(ValueError, match="^Unterminated SQL"):
        split(source)


@pytest.fixture
def isolated_db(monkeypatch):
    from src import migrations
    schema = "stage27_" + uuid.uuid4().hex
    params = dict(dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
                  password=os.environ["POSTGRES_PASSWORD"], host=os.environ["POSTGRES_HOST"],
                  port=os.environ["POSTGRES_PORT"])
    with psycopg.connect(**params, autocommit=True) as admin:
        admin.execute(pgsql.SQL("CREATE SCHEMA {}").format(pgsql.Identifier(schema)))
    def connection():
        conn = psycopg.connect(**params)
        conn.execute(pgsql.SQL("SET search_path TO {}").format(pgsql.Identifier(schema)))
        return conn
    monkeypatch.setattr(migrations, "get_db_connection", connection)
    try:
        yield connection
    finally:
        with psycopg.connect(**params, autocommit=True) as admin:
            admin.execute(pgsql.SQL("DROP SCHEMA {} CASCADE").format(pgsql.Identifier(schema)))


def write(directory, filename, body):
    (directory / filename).write_text(body, encoding="utf-8")


def test_postgresql_dollar_body_and_replay(isolated_db, tmp_path):
    from src.migrations import run_migrations
    write(tmp_path, "002_values.sql", """/* nested /* ; */ done */
        CREATE FUNCTION val() RETURNS text LANGUAGE plpgsql AS $body$
        BEGIN RETURN 'Grüße;it''s fine'; END; $body$;
        DO $$ BEGIN INSERT INTO sample VALUES (val()); END $$;
        INSERT INTO sample VALUES (E'escaped\\';semicolon');
    """)
    write(tmp_path, "001_table.sql", "CREATE TABLE sample (value text)")
    write(tmp_path, "003_empty.sql", "-- nothing ;\n/* /* nested */ */")
    (tmp_path / "ignored.txt").write_text("INVALID SQL")
    (tmp_path / "nested").mkdir()
    write(tmp_path / "nested", "000_nested.sql", "INVALID SQL")
    run_migrations(tmp_path)
    run_migrations(tmp_path)
    with isolated_db() as conn:
        assert conn.execute("SELECT value FROM sample ORDER BY value").fetchall() == [
            ("Grüße;it's fine",), ("escaped';semicolon",)]
        assert conn.execute("SELECT filename FROM schema_migrations ORDER BY filename").fetchall() == [
            ("001_table.sql",), ("002_values.sql",), ("003_empty.sql",)]


def test_postgresql_file_rollback_and_prior_commit(isolated_db, tmp_path):
    from src.migrations import run_migrations
    write(tmp_path, "001_ok.sql", "CREATE TABLE sample (value text); INSERT INTO sample VALUES ('prior')")
    write(tmp_path, "002_bad.sql", "INSERT INTO sample VALUES ('partial;value'); SELECT no_such_column FROM sample")
    with pytest.raises(psycopg.Error):
        run_migrations(tmp_path)
    with isolated_db() as conn:
        assert conn.execute("SELECT value FROM sample").fetchall() == [("prior",)]
        assert conn.execute("SELECT filename FROM schema_migrations").fetchall() == [("001_ok.sql",)]
    write(tmp_path, "002_bad.sql", "INSERT INTO sample VALUES ('fixed')")
    run_migrations(tmp_path)
    with isolated_db() as conn:
        assert conn.execute("SELECT value FROM sample ORDER BY value").fetchall() == [("fixed",), ("prior",)]


def test_file_validated_before_execute(monkeypatch, tmp_path):
    from src import migrations
    from tests.test_migrations import FakeConnection
    write(tmp_path, "001_bad.sql", "SELECT 'valid'; SELECT 'unterminated")
    conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: conn)
    with pytest.raises(ValueError, match="^Unterminated SQL"):
        migrations.run_migrations(tmp_path)
    assert not any("SELECT 'valid'" in query for query, _ in conn.executed_queries)
    assert not any("INSERT INTO schema_migrations" in query for query, _ in conn.executed_queries)


def test_statement_calls_and_empty_recording(monkeypatch, tmp_path):
    from src import migrations
    from tests.test_migrations import FakeConnection
    write(tmp_path, "001_ok.sql", "SELECT 'a;b'; SELECT 2;")
    write(tmp_path, "002_empty.sql", "/* comment */; -- eof")
    conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: conn)
    migrations.run_migrations(tmp_path)
    queries = [q for q, _ in conn.executed_queries]
    assert "SELECT 'a;b'" in queries
    assert "SELECT 2" in queries
    recorded = [p[0] for q, p in conn.executed_queries if "INSERT INTO schema_migrations" in q]
    assert recorded == ["001_ok.sql", "002_empty.sql"]
    assert conn.committed == 3
