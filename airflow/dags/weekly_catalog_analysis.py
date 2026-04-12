from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from scraper.pipeline import (
    run_catalog_diff_for_all_brands,
    run_catalog_scrape,
    run_product_spec_extraction,
    run_weekly_report_generation,
)


def _run_brand_catalog(brand: str) -> None:
    import asyncio

    asyncio.run(run_catalog_scrape(brand))


def _run_catalog_diff() -> None:
    run_catalog_diff_for_all_brands()


def _run_product_spec_extraction() -> None:
    run_product_spec_extraction(limit=250, include_existing=True)


def _run_weekly_report_generation() -> None:
    run_weekly_report_generation(send_email=False)


with DAG(
    dag_id="weekly_catalog_analysis",
    start_date=datetime(2024, 1, 1),
    schedule="0 23 * * 0",
    catchup=False,
    max_active_runs=1,
    tags=["competitor", "weekly", "catalog"],
) as dag:
    istikbal = PythonOperator(
        task_id="scrape_istikbal_catalog",
        python_callable=_run_brand_catalog,
        op_kwargs={"brand": "istikbal"},
    )
    bellona = PythonOperator(
        task_id="scrape_bellona_catalog",
        python_callable=_run_brand_catalog,
        op_kwargs={"brand": "bellona"},
    )
    dogtas = PythonOperator(
        task_id="scrape_dogtas_catalog",
        python_callable=_run_brand_catalog,
        op_kwargs={"brand": "dogtas"},
    )
    analyze_diffs = PythonOperator(
        task_id="analyze_catalog_diffs",
        python_callable=_run_catalog_diff,
    )
    extract_product_specs = PythonOperator(
        task_id="extract_product_specs",
        python_callable=_run_product_spec_extraction,
    )
    generate_weekly_report = PythonOperator(
        task_id="generate_weekly_report_artifacts",
        python_callable=_run_weekly_report_generation,
    )

    [istikbal, bellona, dogtas] >> analyze_diffs >> extract_product_specs >> generate_weekly_report
