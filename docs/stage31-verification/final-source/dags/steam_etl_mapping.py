from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="steam_etl_mapping",
    default_args=default_args,
    description="Twitch to IGDB mapping pipeline",
    schedule="0 12 * * 0",  # каждое воскресенье в 12:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    twitch_games_lookup = BashOperator(
        task_id="twitch_games_lookup_observed",
        bash_command="cd /opt/airflow && python -m src.main twitch-games-lookup-observed --limit 500",
    )

    candidates_from_catalog = BashOperator(
        task_id="generate_candidates_from_catalog",
        bash_command="cd /opt/airflow && python -m src.main generate-twitch-igdb-candidates-from-catalog --limit 500",
    )

    fuzzy_candidates = BashOperator(
        task_id="generate_fuzzy_candidates",
        bash_command="cd /opt/airflow && python -m src.main generate-twitch-igdb-candidates --limit 3000",
    )

    twitch_games_lookup >> candidates_from_catalog >> fuzzy_candidates