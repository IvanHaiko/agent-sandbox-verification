from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="steam_etl_daily",
    default_args=default_args,
    description="Daily Steam ETL pipeline",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    steamspy = BashOperator(
        task_id="steamspy_daily",
        bash_command="cd /opt/airflow && python -m src.main steamspy-daily --max-pages 50",
    )

    steam_store = BashOperator(
        task_id="steam_store_enrich",
        bash_command="cd /opt/airflow && python -m src.main steam-store-enrich --limit 7000",
    )

    igdb_delay = BashOperator(
        task_id="igdb_delay",
        bash_command="sleep 1800",
    )

    igdb_enrich = BashOperator(
        task_id="igdb_enrich_steam",
        bash_command="cd /opt/airflow && python -m src.main igdb-enrich-steam --limit 7000",
    )

    twitch_streams = BashOperator(
        task_id="twitch_streams",
        bash_command="cd /opt/airflow && python -m src.main twitch-streams --pages 50 --delay 1.0",
    )

    steam_store >> igdb_delay >> igdb_enrich