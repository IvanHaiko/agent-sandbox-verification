from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="steam_etl_weekly",
    default_args=default_args,
    description="Weekly full Steam ETL pipeline (all pages)",
    schedule="0 3 * * 0",  # каждое воскресенье в 3:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    steamspy_full = BashOperator(
        task_id="steamspy_full",
        bash_command="cd /opt/airflow && python -m src.main steamspy-daily",
    )

    steam_store = BashOperator(
        task_id="steam_store_enrich",
        bash_command="cd /opt/airflow && python -m src.main steam-store-enrich --limit 2000",
    )

    twitch_streams = BashOperator(
        task_id="twitch_streams",
        bash_command="cd /opt/airflow && python -m src.main twitch-streams",
    )

    igdb_enrich = BashOperator(
        task_id="igdb_enrich_steam",
        bash_command="cd /opt/airflow && python -m src.main igdb-enrich-steam --limit 500",
    )

    steamspy_full >> steam_store >> twitch_streams >> igdb_enrich