"""Frozen independent contract tests; implementation imports are intentionally lazy."""

import inspect
from uuid import uuid4

import pytest


@pytest.fixture
def split_sql():
    from src.sql_statements import split_sql_statements

    return split_sql_statements


def test_boundaries_preserve_original_fragments(split_sql):
    source = " \t; SELECT  1\n + 2 ;\r\nSELECT 3\t; ; SELECT 4  "
    original = source[:]
    assert split_sql(source) == ["SELECT  1\n + 2", "SELECT 3", "SELECT 4"]
    assert source == original
    assert split_sql("") == []
    assert split_sql(" \r\n ; ; \t") == []


def test_standard_strings_and_identifiers(split_sql):
    statements = [
        "SELECT 'a;b''c;d'",
        'SELECT "a;b""c;d" FROM "t;u"',
        "SELECT 'backslash\\'",  # Standard strings do not backslash-escape quotes.
        "SELECT '/* -- $$ ; */', '-- ;', 'é;雪'",
    ]
    assert split_sql(";\n".join(statements) + ";") == statements


@pytest.mark.parametrize("prefix", ["E", "e"])
def test_escape_strings_preserve_escaped_quotes(split_sql, prefix):
    statement = "SELECT " + prefix + r"'one\';two\\;three'';four'"
    assert split_sql(statement + "; SELECT 7;") == [statement, "SELECT 7"]
    even_slashes = "SELECT " + prefix + "'tail" + "\\" * 2 + "'"
    assert split_sql(even_slashes + "; SELECT 8") == [even_slashes, "SELECT 8"]


@pytest.mark.parametrize("identifier", ["nameE", "namee", "_E", "field1E"])
def test_escape_prefix_requires_token_boundary(split_sql, identifier):
    statement = "SELECT " + identifier + "'tail\\'"
    assert split_sql(statement + ";SELECT 2;") == [statement, "SELECT 2"]
    escaped = r"SELECT(E'a\';b')"
    assert split_sql(escaped + "; SELECT 3") == [escaped, "SELECT 3"]


@pytest.mark.parametrize("tag", ["", "a", "_", "a_09", "Tag"])
def test_dollar_quote_delimiters_are_exact(split_sql, tag):
    delimiter = "$" + tag + "$"
    body = "one; ' \" -- /* $$ $other$ $tag$ ; two"
    # An untagged body must not contain its own closing delimiter.
    if not tag:
        body = body.replace("$$", "$x$")
    statement = "SELECT " + delimiter + body + delimiter
    assert split_sql(statement + ";SELECT 2") == [statement, "SELECT 2"]
    case_sensitive = "SELECT $Tag$a; $tag$b; $TAG$c; $Tag$"
    assert split_sql(case_sensitive + ";SELECT 3") == [case_sensitive, "SELECT 3"]


def test_dollar_sequences_in_identifiers_and_parameters(split_sql):
    statements = [
        "SELECT foo$tag$bar", "SELECT foo$$bar", "SELECT _x$Tag$y",
        "SELECT $1, $12", "SELECT $9bad$", "SELECT $a-b$",
        "SELECT($ok$a;b$ok$)",
    ]
    assert split_sql(";".join(statements) + ";") == statements


def test_nested_comments_and_region_precedence(split_sql):
    first = "/* outer ; ' \" $$ /* nested ; */ still ; */ SELECT 1"
    second = "SELECT '/* not comment ; */', \"-- ;\" /* trailing ; */"
    assert split_sql(first + ";" + second + ";") == [first, second]
    assert split_sql("/* one /* two */ three */; -- end ; ' $$") == []
    assert split_sql("SELECT 1 /* -- ' \" $$ ; */; SELECT 2") == [
        "SELECT 1 /* -- ' \" $$ ; */", "SELECT 2"
    ]


@pytest.mark.parametrize("newline", ["\r", "\n", "\r\n"])
def test_line_comments_end_at_cr_or_lf(split_sql, newline):
    first = "-- ; ' \" /* $$" + newline + "SELECT 1"
    second = "-- another ;" + newline + "SELECT 2"
    assert split_sql(first + ";" + second + "; -- eof ' /*") == [first, second]
    assert split_sql("-- comment to EOF; ' /* $$") == []
    assert split_sql("SELECT 1 -- EOF ; ' /*") == ["SELECT 1 -- EOF ; ' /*"]


@pytest.mark.parametrize("bad", [
    "SELECT 'open", 'SELECT "open', "SELECT E'escaped\\'",
    "SELECT e'open", "SELECT $$open", "SELECT $Tag$open $tag$",
    "/* open", "/* outer /* inner */", "SELECT 1; SELECT 'open",
    'SELECT 1; SELECT "open', "SELECT 1; /* outer /* inner */",
])
def test_unterminated_regions_raise_value_error(split_sql, bad):
    with pytest.raises(ValueError, match=r"^Unterminated SQL"):
        split_sql(bad)


def test_comment_only_fragments_do_not_execute(split_sql):
    source = "; /* a ; */; -- b ;\r; /* c /* d */ */; SELECT 1; /* eof */"
    assert split_sql(source) == ["SELECT 1"]
    assert split_sql("/* leading */ SELECT 1 /* trailing */") == [
        "/* leading */ SELECT 1 /* trailing */"
    ]


class _CursorTrace:
    """Observe the public DB-API execute seam while using a real cursor."""

    def __init__(self, cursor, events):
        self.cursor = cursor
        self.events = events

    def execute(self, query, *args, **kwargs):
        self.events.append(("execute", query))
        self.cursor.execute(query, *args, **kwargs)
        return self

    def __enter__(self):
        self.cursor.__enter__()
        return self

    def __exit__(self, *args):
        return self.cursor.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class _ConnectionTrace:
    def __init__(self, connection, events):
        self.connection = connection
        self.events = events

    def cursor(self, *args, **kwargs):
        return _CursorTrace(self.connection.cursor(*args, **kwargs), self.events)

    def execute(self, query, *args, **kwargs):
        self.events.append(("execute", query))
        return self.connection.execute(query, *args, **kwargs)

    def commit(self):
        self.events.append(("commit", None))
        return self.connection.commit()

    def rollback(self):
        self.events.append(("rollback", None))
        return self.connection.rollback()

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.connection.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.connection, name)


@pytest.fixture
def migration_db(test_database, monkeypatch):
    """Own ledger and data schema, with no fallback to the fixture's public schema."""
    from psycopg import sql
    from src.db import get_db_connection
    from src import migrations

    schema = "independent_" + uuid4().hex
    events = []
    connections = []
    observer = get_db_connection()
    observer.autocommit = True
    before = observer.execute(
        "SELECT to_jsonb(t) FROM public.schema_migrations AS t"
    ).fetchall()
    observer.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    observer.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))

    def connect():
        connection = get_db_connection()
        connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        connection.execute("SET standard_conforming_strings = on")
        connection.commit()  # Isolation setup, outside the runner's traced commits.
        connections.append(connection)
        return _ConnectionTrace(connection, events)

    monkeypatch.setattr(migrations, "get_db_connection", connect)
    try:
        yield migrations.run_migrations, observer, events
    finally:
        for connection in connections:
            if not connection.closed:
                connection.rollback()
                connection.close()
        after = observer.execute(
            "SELECT to_jsonb(t) FROM public.schema_migrations AS t"
        ).fetchall()
        observer.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        observer.close()
        assert sorted(map(repr, after)) == sorted(map(repr, before))


def _write(directory, name, text):
    (directory / name).write_text(text, encoding="utf-8")


def _ledger_names(observer):
    # Read rows without assuming private ledger column names or extra columns.
    rows = observer.execute("SELECT to_jsonb(t) FROM schema_migrations AS t").fetchall()
    return [value for (row,) in rows for value in row.values()
            if isinstance(value, str) and value.endswith(".sql")]


def test_postgres_quotes_functions_do_and_nested_comments(migration_db, tmp_path):
    run, observer, events = migration_db
    statements = [
        'CREATE TABLE "values;table" ("text;value" text)',
        "INSERT INTO \"values;table\" VALUES ('été;雪''s')",
        "CREATE FUNCTION make_text() RETURNS text LANGUAGE plpgsql AS $Body$\n"
        "BEGIN RETURN 'function;value'; END;\n$Body$",
        "DO $$ BEGIN INSERT INTO \"values;table\" VALUES (make_text()); END; $$",
        "/* outer ; /* nested ; */ done */ INSERT INTO \"values;table\" VALUES ('last;value')",
    ]
    _write(tmp_path, "001_complex.sql", ";\n".join(statements) + ";")
    run(migrations_dir=tmp_path)
    assert observer.execute('SELECT "text;value" FROM "values;table" ORDER BY 1').fetchall() == [
        ("function;value",), ("last;value",), ("été;雪's",)
    ]
    assert _ledger_names(observer) == ["001_complex.sql"]
    executed = [query for kind, query in events if kind == "execute"]
    for statement in statements:
        assert executed.count(statement) == 1
    assert sum(kind == "commit" for kind, _ in events) == 2


def test_failed_file_rolls_back_but_prior_file_stays_committed(migration_db, tmp_path):
    from psycopg import Error

    run, observer, events = migration_db
    _write(tmp_path, "001_good.sql", "CREATE TABLE kept (n integer); INSERT INTO kept VALUES (1);")
    _write(tmp_path, "002_bad.sql", "INSERT INTO kept VALUES (2); CREATE TABLE vanished (n integer); SELECT 1 / 0;")
    _write(tmp_path, "003_later.sql", "INSERT INTO kept VALUES (3);")
    with pytest.raises(Error):
        run(tmp_path)
    assert observer.execute("SELECT n FROM kept").fetchall() == [(1,)]
    assert observer.execute("SELECT to_regclass('vanished')").fetchone() == (None,)
    assert _ledger_names(observer) == ["001_good.sql"]
    _write(tmp_path, "002_bad.sql", "INSERT INTO kept VALUES (2);")
    run(tmp_path)
    assert observer.execute("SELECT n FROM kept ORDER BY n").fetchall() == [(1,), (2,), (3,)]
    assert sorted(_ledger_names(observer)) == ["001_good.sql", "002_bad.sql", "003_later.sql"]


@pytest.mark.parametrize("tail", ["SELECT 'open", 'SELECT "open', "DO $Body$ BEGIN;", "/* unclosed"])
def test_whole_file_is_validated_before_execution(migration_db, tmp_path, tail):
    run, observer, events = migration_db
    _write(tmp_path, "001_first.sql", "CREATE TABLE stable (n integer); INSERT INTO stable VALUES (1);")
    first = "INSERT INTO stable VALUES (2)"
    _write(tmp_path, "002_invalid.sql", first + ";" + tail)
    with pytest.raises(ValueError, match=r"^Unterminated SQL"):
        run(tmp_path)
    assert observer.execute("SELECT n FROM stable").fetchall() == [(1,)]
    assert _ledger_names(observer) == ["001_first.sql"]
    # Rollback alone is insufficient: the earlier statement must never be sent.
    executed = [str(query) for kind, query in events if kind == "execute"]
    assert not any(first in query for query in executed)


def test_replay_skips_filenames_even_when_contents_change(migration_db, tmp_path):
    run, observer, events = migration_db
    _write(tmp_path, "001_replay.sql", "CREATE TABLE replayed (n integer); INSERT INTO replayed VALUES (1);")
    run(tmp_path)
    ledger_before = observer.execute("SELECT to_jsonb(t) FROM schema_migrations t").fetchall()
    _write(tmp_path, "001_replay.sql", "SELECT 'unterminated")
    events.clear()
    run(tmp_path)
    assert observer.execute("SELECT n FROM replayed").fetchall() == [(1,)]
    assert observer.execute("SELECT to_jsonb(t) FROM schema_migrations t").fetchall() == ledger_before
    assert not any("unterminated" in str(query) for kind, query in events if kind == "execute")
    assert sum(kind == "commit" for kind, _ in events) == 1


def test_empty_comment_files_recorded_once_and_commit_per_file(migration_db, tmp_path):
    run, observer, events = migration_db
    _write(tmp_path, "001_empty.sql", "")
    _write(tmp_path, "002_comments.sql", "; /* outer /* inner */ */; -- EOF ; ' $$")
    _write(tmp_path, "003_value.sql", "CREATE TABLE single_value (n integer); INSERT INTO single_value VALUES (9)")
    run(tmp_path)
    assert sorted(_ledger_names(observer)) == ["001_empty.sql", "002_comments.sql", "003_value.sql"]
    assert sum(kind == "commit" for kind, _ in events) == 4
    assert observer.execute("SELECT n FROM single_value").fetchall() == [(9,)]
    events.clear()
    run(tmp_path)
    assert len(_ledger_names(observer)) == 3
    assert sum(kind == "commit" for kind, _ in events) == 1


def test_discovery_is_immediate_sql_only_and_filename_sorted(migration_db, tmp_path, capsys):
    run, observer, events = migration_db
    # Write in reverse order; dependencies force filename rather than creation order.
    _write(tmp_path, "020_insert.sql", "INSERT INTO ordered VALUES ('UTF-8: 雪;é');")
    _write(tmp_path, "010_create.sql", "CREATE TABLE ordered (value text);")
    _write(tmp_path, "000_ignored.txt", "SELECT 1 / 0;")
    nested = tmp_path / "nested"
    nested.mkdir()
    _write(nested, "000_nested.sql", "SELECT 1 / 0;")
    run(migrations_dir=tmp_path)
    assert observer.execute("SELECT value FROM ordered").fetchall() == [("UTF-8: 雪;é",)]
    assert sorted(_ledger_names(observer)) == ["010_create.sql", "020_insert.sql"]
    output = capsys.readouterr().out
    assert output.strip(), "A successful migration run must retain console summaries"


def test_public_runner_signature_and_empty_directory(migration_db, tmp_path):
    run, observer, events = migration_db
    parameters = inspect.signature(run).parameters
    assert list(parameters) == ["migrations_dir"]
    assert parameters["migrations_dir"].default is None
    assert run(migrations_dir=tmp_path) is None
    assert _ledger_names(observer) == []
    assert sum(kind == "commit" for kind, _ in events) == 1
