from pathlib import Path

from src.db import get_db_connection
from src.sql_statements import split_sql_statements


def run_migrations(migrations_dir: Path | None = None) -> None:
    """
    Apply pending SQL migration files from migrations_dir in filename order.

    Creates schema_migrations table on first run.
    Files already recorded in schema_migrations are skipped.
    Each file is split at SQL statement boundaries and each statement is executed
    individually, then the filename is recorded and committed atomically.
    """

    if migrations_dir is None:
        migrations_dir = Path("sql/migrations")

    migration_files = sorted(migrations_dir.glob("*.sql"))

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT filename FROM schema_migrations ORDER BY filename"
            )
            applied = {row[0] for row in cursor.fetchall()}

        if not migration_files:
            print("No migration files found.")
            return

        applied_count = 0
        skipped_count = 0

        for migration_file in migration_files:
            filename = migration_file.name

            if filename in applied:
                print(f"  skip: {filename}")
                skipped_count += 1
                continue

            print(f"  apply: {filename}")
            sql = migration_file.read_text(encoding="utf-8")
            statements = split_sql_statements(sql)

            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

                cursor.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                )

            connection.commit()
            print(f"  done: {filename}")
            applied_count += 1

    print(
        f"Migrations complete. Applied: {applied_count}, Skipped: {skipped_count}"
    )
