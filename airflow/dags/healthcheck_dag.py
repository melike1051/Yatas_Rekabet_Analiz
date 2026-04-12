from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator


with DAG(
    dag_id="platform_healthcheck",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["bootstrap"],
) as dag:
    start = EmptyOperator(task_id="start")
    finish = EmptyOperator(task_id="finish")

    start >> finish
