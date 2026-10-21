"""
taxi_pipeline_dag.py — NYC Taxi Lakehouse Pipeline (Bronze ➔ Silver ➔ Gold)
============================================================================

Streamlined 3-stage Medallion data lakehouse pipeline:
  1. bronze_layer : Validates and ingests Parquet files into Bronze Delta table.
  2. silver_layer : Applies Quality Gates, separates Quarantine & Silver data.
  3. gold_layer   : Aggregates analytical metrics and registers tables into Trino.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parent
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from scripts.bronze import check_data_files, ingest_bronze
from scripts.silver import populate_silver
from scripts.gold import rebuild_gold
from utils.trino_helper import register_delta_tables_in_trino, flush_trino_metadata_cache
from utils.audit_logger import record_pipeline_audit
from utils.spark import get_spark_session
from delta.tables import DeltaTable

log = logging.getLogger(__name__)


def run_bronze_stage(**context) -> None:
    """Stage 1: Validate files and ingest into Bronze Delta table."""
    check_data_files(**context)
    ingest_bronze(**context)


def run_gold_stage(**context) -> None:
    """Stage 3: Execute Gold layer transformations and register tables in Trino."""
    rebuild_gold(**context)
    register_delta_tables_in_trino()
    flush_trino_metadata_cache()


def run_audit_stage(**context) -> None:
    """Stage 4: Record pipeline run execution metrics and row counts into PostgreSQL."""
    dag_obj = context.get("dag")
    dag_id = dag_obj.dag_id if dag_obj else "taxi_monthly_pipeline"
    run_id = context.get("run_id", "manual_run")
    params = context.get("params", {})
    dataset_type = str(params.get("dataset_type", "yellow")).lower()
    source_month = params.get("source_month", "2025")
    source_mode = params.get("source_mode", "AUTO")
    dag_run = context.get("dag_run")
    start_time = dag_run.start_date if dag_run else datetime.now(timezone.utc)
    end_time = datetime.now(timezone.utc)

    bronze_table = f"s3a://bronze/{dataset_type}_trips"
    silver_table = f"s3a://silver/{dataset_type}_trips"
    gold_table = "s3a://gold/hourly_zone_metrics" if dataset_type == "yellow" else f"s3a://gold/{dataset_type}_hourly_zone_metrics"

    # Gather row counts from Delta tables
    bronze_rows, silver_rows, quarantine_rows, gold_rows = 0, 0, 0, 0
    spark = get_spark_session(f"AirflowAuditCounter_{dataset_type}")
    try:
        if DeltaTable.isDeltaTable(spark, bronze_table):
            bronze_rows = spark.read.format("delta").load(bronze_table).count()
        if DeltaTable.isDeltaTable(spark, silver_table):
            silver_rows = spark.read.format("delta").load(silver_table).count()
        if DeltaTable.isDeltaTable(spark, "s3a://bronze/quarantine"):
            quarantine_rows = spark.read.format("delta").load("s3a://bronze/quarantine").count()
        if DeltaTable.isDeltaTable(spark, gold_table):
            gold_rows = spark.read.format("delta").load(gold_table).count()
    except Exception as e:
        log.warning("Could not compute Delta row counts for audit: %s", e)
    finally:
        spark.stop()

    record_pipeline_audit(
        dag_id=dag_id,
        run_id=run_id,
        dataset_type=dataset_type,
        source_month=str(source_month),
        source_mode=str(source_mode),
        execution_start_time=start_time,
        execution_end_time=end_time,
        bronze_rows=bronze_rows,
        silver_rows=silver_rows,
        quarantine_rows=quarantine_rows,
        gold_rows=gold_rows,
        status="SUCCESS",
    )


# ── DAG Configuration ──────────────────────────────────────────────────────────
default_args = {
    "owner": "hieu",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="taxi_monthly_pipeline",
    description="Streamlined NYC Taxi Medallion Pipeline (Bronze ➔ Silver ➔ Gold ➔ Audit)",
    schedule=None,
    max_active_runs=1,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args=default_args,
    tags=["taxi", "lakehouse", "deltalake", "pyspark", "trino", "postgres", "fhv"],
    params={
        "dataset_type": Param(
            default="yellow",
            type="string",
            enum=["yellow", "green", "fhv", "fhvhv"],
            description="Tập dữ liệu NYC TLC: 'yellow' (Yellow Taxi), 'green' (Green Taxi), 'fhv' (For-Hire Vehicle), 'fhvhv' (High Volume FHV).",
        ),
        "source_month": Param(
            default="2025-01",
            type="string",
            description="Target month(s): e.g. '2025-01' (1 month), '2025-01..2025-06' (range), or '2025' (all 12 months).",
        ),
        "source_mode": Param(
            default="REMOTE_NYC_CDN",
            type="string",
            enum=["REMOTE_NYC_CDN", "AUTO", "LOCAL"],
            description="Source Mode: 'REMOTE_NYC_CDN' (zero-disk stream from NYC TLC), 'AUTO' (local file if present, else remote CDN), 'LOCAL' (local data/ only).",
        ),
    },
) as dag:

    # ── Stage 1: Bronze Ingestion ────────────────────────────────────────────
    bronze_layer = PythonOperator(
        task_id="bronze_layer",
        python_callable=run_bronze_stage,
        doc_md="Validates data directory and ingests Parquet files into Bronze Delta table.",
    )

    # ── Stage 2: Silver & Quarantine ─────────────────────────────────────────
    silver_layer = PythonOperator(
        task_id="silver_layer",
        python_callable=populate_silver,
        doc_md="Applies Quality Gates, splits valid data to Silver and invalid rows to Quarantine.",
    )

    # ── Stage 3: Gold & Trino Registration ───────────────────────────────────
    gold_layer = PythonOperator(
        task_id="gold_layer",
        python_callable=run_gold_stage,
        doc_md="Executes PySpark SQL transformations for the Gold layer.",
    )

    # ── Stage 4: PostgreSQL Audit Logging ────────────────────────────────────
    audit_layer = PythonOperator(
        task_id="audit_layer",
        python_callable=run_audit_stage,
        doc_md="Records pipeline execution metrics, duration, and tier row counts into PostgreSQL.",
    )

    # ── Clean, intuitive linear flow ─────────────────────────────────────────
    bronze_layer >> silver_layer >> gold_layer >> audit_layer
