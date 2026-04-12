from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from scraper.pipeline import run_weekly_report_generation


def _run_weekly_report() -> None:
    run_weekly_report_generation(send_email=True)


with DAG(
    dag_id="weekly_reporting_delivery",
    start_date=datetime(2024, 1, 1),
    schedule="0 7 * * 1",
    catchup=False,
    max_active_runs=1,
    tags=["competitor", "weekly", "reporting"],
) as dag:
    generate_and_send = PythonOperator(
        task_id="generate_and_send_weekly_report",
        python_callable=_run_weekly_report,
    )
