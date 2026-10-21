"""
taxi_forecast_dag.py — Daily 24-Hour Taxi Demand & Revenue Forecast Pipeline
=============================================================================
Scheduled pipeline that:
  1. Refreshes recent weather observations and next 48h forecast from Open-Meteo.
  2. Executes 24-Hour sequential LightGBM batch inference for NYC taxi demand & revenue.
  3. Writes forecast metrics to Delta Lake Gold (s3a://gold/forecast_hourly_metrics).
  4. Flushes Trino cache and ensures catalog tables are query-ready.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parent
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from scripts.predict_24h import run_batch_forecast_24h
from scripts.weather_etl import run_weather_etl
from utils.trino_helper import flush_trino_metadata_cache, register_delta_tables_in_trino

log = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def weather_refresh_wrapper(**context) -> None:
    """Task 1: Fetch and update recent weather observations & forecast."""
    log.info("Executing Weather Refresh Task...")
    run_weather_etl(include_forecast=True)


def batch_forecast_wrapper(**context) -> None:
    """Task 2: Run LightGBM 24-hour forward inference."""
    log.info("Executing Batch Forecast Task...")
    run_batch_forecast_24h()


def trino_refresh_wrapper(**context) -> None:
    """Task 3: Register Delta tables and flush Trino cache."""
    log.info("Executing Trino Register & Metadata Cache Flush Task...")
    register_delta_tables_in_trino()
    flush_trino_metadata_cache()


with DAG(
    dag_id="taxi_weather_forecast_pipeline",
    default_args=default_args,
    description="Daily 24-hour ahead NYC taxi demand & revenue forecasting using weather variation",
    schedule_interval="0 0 * * *",  # Run daily at midnight UTC
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    tags=["forecast", "lightgbm", "weather", "delta-lake", "trino"],
) as dag:

    t1_weather_refresh = PythonOperator(
        task_id="refresh_weather_forecast",
        python_callable=weather_refresh_wrapper,
    )

    t2_batch_forecast = PythonOperator(
        task_id="generate_24h_forecast",
        python_callable=batch_forecast_wrapper,
    )

    t3_trino_refresh = PythonOperator(
        task_id="register_and_flush_trino",
        python_callable=trino_refresh_wrapper,
    )

    t1_weather_refresh >> t2_batch_forecast >> t3_trino_refresh
