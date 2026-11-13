from src import migrations


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def execute(self, query, params=None):
        self.connection.executed_queries.append((query, params))

    def fetchall(self):
        return self.connection.fetchall_result


class FakeConnection:
    def __init__(self, applied_filenames=None):
        self.executed_queries = []
        self.committed = 0
        self.fetchall_result = [(f,) for f in (applied_filenames or [])]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed += 1


def test_run_migrations_creates_schema_migrations_table(monkeypatch, tmp_path):
    """
    Test that schema_migrations table is created on first run.
    """

    fake_conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    create_queries = [
        q for q, _ in fake_conn.executed_queries
        if "CREATE TABLE IF NOT EXISTS schema_migrations" in q.replace("\n", " ")
    ]
    assert len(create_queries) == 1


def test_run_migrations_applies_files_in_filename_order(monkeypatch, tmp_path):
    """
    Test that migration files are applied in ascending filename order.
    """

    (tmp_path / "002_create_bar.sql").write_text("CREATE TABLE bar (id SERIAL)")
    (tmp_path / "001_create_foo.sql").write_text("CREATE TABLE foo (id SERIAL)")

    fake_conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    recorded = [
        params[0]
        for q, params in fake_conn.executed_queries
        if params and "INSERT INTO schema_migrations" in q
    ]
    assert recorded == ["001_create_foo.sql", "002_create_bar.sql"]


def test_run_migrations_skips_already_applied(monkeypatch, tmp_path):
    """
    Test that files already recorded in schema_migrations are not re-applied.
    """

    (tmp_path / "001_create_foo.sql").write_text("CREATE TABLE foo (id SERIAL)")
    (tmp_path / "002_create_bar.sql").write_text("CREATE TABLE bar (id SERIAL)")

    fake_conn = FakeConnection(applied_filenames=["001_create_foo.sql"])
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    recorded = [
        params[0]
        for q, params in fake_conn.executed_queries
        if params and "INSERT INTO schema_migrations" in q
    ]
    assert recorded == ["002_create_bar.sql"]

    foo_sql_executed = any(
        "CREATE TABLE foo" in q
        for q, _ in fake_conn.executed_queries
    )
    assert not foo_sql_executed


def test_run_migrations_commits_each_migration_independently(monkeypatch, tmp_path):
    """
    Test that each migration is committed in its own transaction after apply.
    """

    (tmp_path / "001_create_foo.sql").write_text("CREATE TABLE foo (id SERIAL)")
    (tmp_path / "002_create_bar.sql").write_text("CREATE TABLE bar (id SERIAL)")

    fake_conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    # One commit for CREATE TABLE schema_migrations + one per migration file applied
    assert fake_conn.committed >= 3


def test_run_migrations_executes_complete_sql_file(monkeypatch, tmp_path):
    sql = """-- A comment; with a semicolon
CREATE TABLE messages (body TEXT);
INSERT INTO messages VALUES ('one;two');
DO $migration$
BEGIN
    INSERT INTO messages VALUES ('three;four');
END;
$migration$;
"""
    (tmp_path / "001_messages.sql").write_text(sql, encoding="utf-8")
    fake_conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    assert fake_conn.executed_queries[2:] == [
        (sql, None),
        (
            "INSERT INTO schema_migrations (filename) VALUES (%s)",
            ("001_messages.sql",),
        ),
    ]
    assert fake_conn.committed == 2


def test_run_migrations_records_blank_file_without_executing_sql(monkeypatch, tmp_path):
    (tmp_path / "001_blank.sql").write_text(" \n\t", encoding="utf-8")
    fake_conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    assert fake_conn.executed_queries[2:] == [
        (
            "INSERT INTO schema_migrations (filename) VALUES (%s)",
            ("001_blank.sql",),
        ),
    ]
    assert fake_conn.committed == 2


def test_run_migrations_no_files(monkeypatch, tmp_path):
    """
    Test that run_migrations exits cleanly when no SQL files are found.

    schema_migrations table is still created (one commit), but no migration
    SQL is executed and no filenames are recorded.
    """

    fake_conn = FakeConnection()
    monkeypatch.setattr(migrations, "get_db_connection", lambda: fake_conn)

    migrations.run_migrations(tmp_path)

    # One commit for CREATE TABLE schema_migrations, nothing else applied.
    assert fake_conn.committed == 1

    recorded = [
        params[0]
        for q, params in fake_conn.executed_queries
        if params and "INSERT INTO schema_migrations" in q
    ]
    assert recorded == []
