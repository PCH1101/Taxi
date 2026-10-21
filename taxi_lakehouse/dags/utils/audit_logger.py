"""
audit_logger.py — Pipeline Execution & Audit Logger for PostgreSQL
===================================================================
Persists pipeline trigger metadata, execution timestamps, duration, and
row counts across Bronze, Silver, Quarantine, and Gold lakehouse tiers.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)


def get_postgres_connection():
    """Establishes connection to PostgreSQL database."""
    host = os.environ.get("POSTGRES_HOST", "postgres" if Path("/.dockerenv").exists() else "localhost")
    port = int(os.environ.get("POSTGRES_PORT", 5432))
    user = os.environ.get("POSTGRES_USER", "airflow")
    password = os.environ.get("POSTGRES_PASSWORD", "airflow")
    dbname = os.environ.get("POSTGRES_DB", "airflow")

    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=5,
    )


def init_audit_table() -> None:
    """Creates the pipeline_execution_history table if it does not exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS pipeline_execution_history (
        id SERIAL PRIMARY KEY,
        dag_id VARCHAR(100) NOT NULL,
        run_id VARCHAR(255) NOT NULL,
        dataset_type VARCHAR(50) DEFAULT 'yellow',
        source_month VARCHAR(100),
        source_mode VARCHAR(50),
        execution_start_time TIMESTAMP WITH TIME ZONE,
        execution_end_time TIMESTAMP WITH TIME ZONE,
        duration_seconds DOUBLE PRECISION,
        bronze_rows BIGINT DEFAULT 0,
        silver_rows BIGINT DEFAULT 0,
        quarantine_rows BIGINT DEFAULT 0,
        gold_rows BIGINT DEFAULT 0,
        status VARCHAR(50) NOT NULL,
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Ensure dataset_type column exists if table was previously created
    ALTER TABLE pipeline_execution_history 
    ADD COLUMN IF NOT EXISTS dataset_type VARCHAR(50) DEFAULT 'yellow';

    CREATE INDEX IF NOT EXISTS idx_pipeline_history_dag_run 
    ON pipeline_execution_history (dag_id, run_id);

    CREATE INDEX IF NOT EXISTS idx_pipeline_history_created_at 
    ON pipeline_execution_history (created_at DESC);
    """
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
            conn.commit()
        log.info("PostgreSQL audit table 'pipeline_execution_history' verified/ready.")
    except Exception as e:
        log.warning("Could not initialize PostgreSQL audit table: %s", e)


def record_pipeline_audit(
    dag_id: str,
    run_id: str,
    dataset_type: str = "yellow",
    source_month: str = "ALL",
    source_mode: str = "AUTO",
    execution_start_time: datetime | None = None,
    execution_end_time: datetime | None = None,
    bronze_rows: int = 0,
    silver_rows: int = 0,
    quarantine_rows: int = 0,
    gold_rows: int = 0,
    status: str = "SUCCESS",
    error_message: str | None = None,
) -> None:
    """Inserts a pipeline run audit record into PostgreSQL."""
    init_audit_table()

    if execution_start_time and execution_end_time:
        duration_seconds = (execution_end_time - execution_start_time).total_seconds()
    else:
        duration_seconds = 0.0

    insert_sql = """
    INSERT INTO pipeline_execution_history (
        dag_id,
        run_id,
        dataset_type,
        source_month,
        source_mode,
        execution_start_time,
        execution_end_time,
        duration_seconds,
        bronze_rows,
        silver_rows,
        quarantine_rows,
        gold_rows,
        status,
        error_message
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    );
    """
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (
                        dag_id,
                        run_id,
                        dataset_type,
                        source_month,
                        source_mode,
                        execution_start_time or datetime.now(timezone.utc),
                        execution_end_time or datetime.now(timezone.utc),
                        duration_seconds,
                        bronze_rows,
                        silver_rows,
                        quarantine_rows,
                        gold_rows,
                        status,
                        error_message,
                    ),
                )
            conn.commit()
        log.info("Audit log recorded in PostgreSQL for Run ID: %s (Status: %s)", run_id, status)
    except Exception as e:
        log.error("Failed to write pipeline audit record to PostgreSQL: %s", e)
