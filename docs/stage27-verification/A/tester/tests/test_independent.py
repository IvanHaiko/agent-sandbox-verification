"""Blind tests of the public splitter and migration runner contracts."""

import inspect
import uuid

import pytest


@pytest.fixture
def split_sql():
    # Deferred import lets pytest collect this suite on the original source.
    from src.sql_statements import split_sql_statements

    return split_sql_statements


def test_boundaries_preserve_exact_fragments_and_final_statement(split_sql):
    source = " \nSELECT  1 ;\t;\r\n SELECT\t2\n;  SELECT 3  "
    original = source
    assert split_sql(source) == ["SELECT  1", "SELECT\t2", "SELECT 3"]
    assert source == original
    assert split_sql(" \r\n;;\t;") == []
    assert split_sql("") == []


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT 'left;right', 'it''s;quoted'",
        'SELECT "semi;colon", "double"";quote" FROM "t;able"',
        r"SELECT E'left\';right;end', E'it''s;fine'",
        r"SELECT e'back\\slash;end', e'\";/*literal*/'",
        r"SELECT 'back\'; SELECT 'standard;string'",
        "SELECT '/* -- $$ ; */', \"--/*;$$\"",
    ],
)
def test_quoted_regions_and_standard_backslash_semantics(split_sql, statement):
    # One case intentionally contains two statements: a standard string's
    # backslash does not escape its closing quote.
    expected = (
        [r"SELECT 'back\'", "SELECT 'standard;string'"]
        if statement == r"SELECT 'back\'; SELECT 'standard;string'"
        else [statement]
    )
    assert split_sql(statement + "; SELECT 9;") == expected + ["SELECT 9"]


def test_e_prefix_requires_identifier_token_boundary(split_sql):
    for prefix in ("nameE", "namee", "_E", "x1e", "caféE", "name$E"):
        statement = "SELECT " + prefix + "'text\\'"
        assert split_sql(statement + "; SELECT 2;") == [statement, "SELECT 2"]
    for prefix in ("E", "e"):
        statement = "SELECT (" + prefix + "'text\\';still inside')"
        assert split_sql(statement + "; SELECT 2;") == [statement, "SELECT 2"]


@pytest.mark.parametrize(
    "statement",
    [
        "DO $$ BEGIN RAISE NOTICE 'a;b'; /* ; */ END $$",
        "SELECT $tag$one; ' -- /* $$ two$tag$",
        "SELECT $_tag9$one;$other$two;$_tag9$",
        "SELECT $A$one;$a$two;$A$",
        "SELECT $a$one;$A$two;$a$",
    ],
)
def test_dollar_quotes_keep_bodies_and_case_sensitive_tags(split_sql, statement):
    assert split_sql(statement + "; SELECT 42") == [statement, "SELECT 42"]


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT identifier$tag$",
        "SELECT identifier$$text",
        "SELECT café$tag$",
        "SELECT $1, $12",
        "SELECT $9tag$",
        "SELECT $a-b$",
    ],
)
def test_dollar_like_identifier_and_parameter_text_is_not_a_quote(split_sql, statement):
    assert split_sql(statement + "; SELECT 7;") == [statement, "SELECT 7"]


def test_comments_are_nested_line_terminated_and_preserved(split_sql):
    first = "-- lead; ' \" $$\rSELECT 1 /* outer; /* inner ; */ tail */"
    second = "-- other;\nSELECT 2 -- tail;\r\n+ 3"
    assert split_sql(first + ";" + second + "; -- EOF comment;") == [first, second]
    assert split_sql("/* outer /* inner */ end */;-- x;\r;-- y;\n;-- eof") == []
    assert split_sql("SELECT 1; /* ' \" $$ -- ; /* nested */ */") == ["SELECT 1"]
    assert split_sql("SELECT 1 -- EOF ;") == ["SELECT 1 -- EOF ;"]
    assert split_sql("SELECT 1 -- CR ;\r; SELECT 2") == ["SELECT 1 -- CR ;", "SELECT 2"]


@pytest.mark.parametrize(
    "source",
    [
        "SELECT 'never closed",
        'SELECT "never closed',
        r"SELECT E'escaped closing\'",
        "SELECT e'ends with backslash\\",
        "SELECT $$never closed;",
        "SELECT $tag$closed with wrong case$TAG$",
        "SELECT $_x1$never closed",
        "SELECT 1; /* not closed",
        "/* outer /* inner */",
    ],
)
def test_unterminated_regions_raise_required_value_error(split_sql, source):
    with pytest.raises(ValueError, match=r"^Unterminated SQL"):
        split_sql(source)


class _CursorRecorder:
    def __init__(self, cursor, executions):
        self.cursor = cursor
        self.executions = executions

    def __enter__(self):
        self.cursor.__enter__()
        return self

    def __exit__(self, *args):
        return self.cursor.__exit__(*args)

    def execute(self, query, *args, **kwargs):
        self.executions.append(query)
        return self.cursor.execute(query, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class _ConnectionRecorder:
    def __init__(self, connection, executions, commits):
        self.connection = connection
        self.executions = executions
        self.commits = commits

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.connection.__exit__(*args)

    def cursor(self, *args, **kwargs):
        return _CursorRecorder(self.connection.cursor(*args, **kwargs), self.executions)

    def execute(self, query, *args, **kwargs):
        self.executions.append(query)
        return self.connection.execute(query, *args, **kwargs)

    def commit(self):
        self.commits.append(True)
        return self.connection.commit()

    def __getattr__(self, name):
        return getattr(self.connection, name)


@pytest.fixture
def isolated_runner(test_database, monkeypatch):
    from psycopg import sql
    from src.db import get_db_connection
    from src import migrations

    schema = "independent_" + uuid.uuid4().hex
    with get_db_connection() as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        connection.commit()

    executions, commits = [], []

    def connect():
        connection = get_db_connection()
        connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        connection.commit()
        return _ConnectionRecorder(connection, executions, commits)

    def rows(query):
        with get_db_connection() as connection:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            return connection.execute(query).fetchall()

    monkeypatch.setattr(migrations, "get_db_connection", connect)
    try:
        yield migrations.run_migrations, rows, executions, commits
    finally:
        with get_db_connection() as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
            connection.commit()


def _write(directory, name, text):
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_real_postgres_quoted_function_do_and_nested_comment_execution(isolated_runner, tmp_path):
    run, rows, executions, commits = isolated_runner
    statements = [
        'CREATE TABLE "semi;table" (id integer PRIMARY KEY, note text)',
        'INSERT INTO "semi;table" VALUES (1, \'café;it\'\'s\')',
        '''CREATE FUNCTION add_row() RETURNS void LANGUAGE plpgsql AS $body$
BEGIN
    INSERT INTO "semi;table" VALUES (2, E'escaped\\\';quote');
END
$body$''',
        "SELECT add_row()",
        '''/* outer; /* nested; */ tail */ DO $$ BEGIN
    INSERT INTO "semi;table" VALUES (3, 'DO;body');
END $$''',
    ]
    _write(tmp_path, "001_complex.sql", ";\n".join(statements) + ";")
    run(tmp_path)
    assert rows('SELECT * FROM "semi;table" ORDER BY id') == [
        (1, "café;it's"), (2, "escaped';quote"), (3, "DO;body")
    ]
    assert [q for q in executions if isinstance(q, str) and q.strip() in statements] == statements
    assert len(commits) == 2
    assert len(rows("SELECT * FROM schema_migrations")) == 1


def test_failed_file_rolls_back_ddl_data_and_ledger_but_prior_file_commits(isolated_runner, tmp_path):
    from psycopg import Error

    run, rows, executions, commits = isolated_runner
    _write(tmp_path, "001_keep.sql", "CREATE TABLE kept (note text); INSERT INTO kept VALUES ('kept;value');")
    bad = _write(tmp_path, "002_fail.sql", "INSERT INTO kept VALUES ('lost'); CREATE TABLE lost (id integer); SELECT 1 / 0;")
    with pytest.raises(Error):
        run(tmp_path)
    assert rows("SELECT * FROM kept") == [("kept;value",)]
    assert rows("SELECT to_regclass('lost')") == [(None,)]
    ledger = rows("SELECT * FROM schema_migrations")
    assert len(ledger) == 1
    assert "001_keep.sql" in ledger[0]
    assert len(commits) == 2
    bad.write_text("INSERT INTO kept VALUES ('repaired;value');", encoding="utf-8")
    run(tmp_path)
    assert rows("SELECT * FROM kept ORDER BY note") == [("kept;value",), ("repaired;value",)]
    assert len(rows("SELECT * FROM schema_migrations")) == 2


def test_malformed_file_is_validated_before_any_of_its_statements_execute(isolated_runner, tmp_path):
    run, rows, executions, commits = isolated_runner
    _write(tmp_path, "001_good.sql", "CREATE TABLE retained (note text); INSERT INTO retained VALUES ('before;failure');")
    first = "INSERT INTO retained VALUES ('must never execute')"
    _write(tmp_path, "002_bad.sql", first + "; SELECT $wrong$unfinished")
    with pytest.raises(ValueError, match=r"^Unterminated SQL"):
        run(tmp_path)
    assert first not in [q.strip() for q in executions if isinstance(q, str)]
    assert rows("SELECT * FROM retained") == [("before;failure",)]
    assert len(rows("SELECT * FROM schema_migrations")) == 1
    assert len(commits) == 2


def test_discovery_order_utf8_empty_files_and_filename_replay(isolated_runner, tmp_path, capsys):
    run, rows, executions, commits = isolated_runner
    _write(tmp_path, "030_empty.sql", " ; ; \n")
    _write(tmp_path, "020_comments.sql", "-- semicolon;\r/* outer /* inner */ end */;")
    changed = _write(tmp_path, "010_data.sql", "INSERT INTO ordering VALUES ('naïve;雪')")
    _write(tmp_path, "001_table.sql", "CREATE TABLE ordering (note text);")
    _write(tmp_path, "000_ignored.txt", "SELECT broken syntax")
    nested = tmp_path / "nested"
    nested.mkdir()
    _write(nested, "000_ignored.sql", "SELECT broken syntax")
    run(tmp_path)
    assert rows("SELECT * FROM ordering") == [("naïve;雪",)]
    ledger = rows("SELECT * FROM schema_migrations")
    assert len(ledger) == 4
    assert {value for row in ledger for value in row if isinstance(value, str)} >= {
        "001_table.sql", "010_data.sql", "020_comments.sql", "030_empty.sql"
    }
    assert len(commits) == 5
    output = capsys.readouterr().out
    assert output.strip(), "The runner must retain console summaries"
    before = len(executions)
    # Filename-based replay must skip even a now-malformed applied file.
    changed.write_text("SELECT 'unterminated", encoding="utf-8")
    run(tmp_path)
    assert rows("SELECT * FROM ordering") == [("naïve;雪",)]
    assert len(rows("SELECT * FROM schema_migrations")) == 4
    assert len(commits) == 6
    assert not any("unterminated" in q for q in executions[before:] if isinstance(q, str))


def test_runner_public_signature_keeps_optional_directory():
    from src.migrations import run_migrations

    signature = inspect.signature(run_migrations)
    assert list(signature.parameters) == ["migrations_dir"]
    assert signature.parameters["migrations_dir"].default is None
