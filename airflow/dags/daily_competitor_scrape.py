from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from scraper.pipeline import run_daily_scrape, run_executive_summary


def _run_brand_scrape(brand: str) -> None:
    import asyncio

    asyncio.run(run_daily_scrape(brand))


def _run_daily_summary() -> None:
    run_executive_summary()


with DAG(
    dag_id="daily_competitor_scrape",
    start_date=datetime(2024, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["competitor", "daily"],
) as dag:
    istikbal = PythonOperator(
        task_id="scrape_istikbal_daily",
        python_callable=_run_brand_scrape,
        op_kwargs={"brand": "istikbal"},
    )
    bellona = PythonOperator(
        task_id="scrape_bellona_daily",
        python_callable=_run_brand_scrape,
        op_kwargs={"brand": "bellona"},
    )
    dogtas = PythonOperator(
        task_id="scrape_dogtas_daily",
        python_callable=_run_brand_scrape,
        op_kwargs={"brand": "dogtas"},
    )
    executive_summary = PythonOperator(
        task_id="generate_executive_summary",
        python_callable=_run_daily_summary,
    )

    [istikbal, bellona, dogtas] >> executive_summary
