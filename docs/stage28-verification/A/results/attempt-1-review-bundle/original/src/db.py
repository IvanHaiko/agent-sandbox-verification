import os

from dotenv import load_dotenv
import psycopg


# Load environment variables from the .env file
load_dotenv()


def get_db_connection():
    """
    Create and return a PostgreSQL database connection.

    Database settings are loaded from environment variables:
    - POSTGRES_DB
    - POSTGRES_USER
    - POSTGRES_PASSWORD
    - POSTGRES_HOST
    - POSTGRES_PORT
    """

    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")

    if not db_name:
        raise ValueError("POSTGRES_DB is not set in .env")

    if not db_user:
        raise ValueError("POSTGRES_USER is not set in .env")

    if not db_password:
        raise ValueError("POSTGRES_PASSWORD is not set in .env")

    connection = psycopg.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
    )

    return connection


def test_db_connection():
    """
    Test the database connection with a simple SELECT query.
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user;")
            result = cursor.fetchone()

    print("Connected successfully!")
    print(f"Database: {result[0]}")
    print(f"User: {result[1]}")


if __name__ == "__main__":
    test_db_connection()