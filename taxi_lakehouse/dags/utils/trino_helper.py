"""
trino_helper.py — Utility for running Trino queries in Airflow tasks for Delta Lake.
"""

from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)


def get_trino_connection(
    host: str = "trino",
    port: int = 8080,
    user: str = "airflow",
    catalog: str = "delta",
    schema: str = "bronze",
    max_retries: int = 8,
    retry_delay: float = 5.0,
):
    """Return a Trino DBAPI connection with retry handling."""
    try:
        import trino
    except ImportError as exc:
        raise ImportError("pip install trino (comes with apache-airflow-providers-trino)") from exc

    for attempt in range(1, max_retries + 1):
        try:
            conn = trino.dbapi.connect(
                host=host,
                port=port,
                user=user,
                catalog=catalog,
                schema=schema,
                http_scheme="http",
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()
            cursor.close()
            return conn
        except Exception as exc:
            msg = str(exc)
            if "SERVER_STARTING_UP" in msg or "initializing" in msg or attempt < max_retries:
                log.warning(
                    "Trino connection attempt %d/%d not ready (%s). Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    msg[:100],
                    retry_delay,
                )
                time.sleep(retry_delay)
            else:
                raise

    return trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog=catalog,
        schema=schema,
        http_scheme="http",
    )


def register_delta_tables_in_trino(conn=None) -> None:
    """Creates schemas and registers Delta Lake tables in Trino."""
    close_conn = False
    if conn is None:
        conn = get_trino_connection()
        close_conn = True

    cursor = conn.cursor()

    # 1. Create schemas with explicit S3 locations
    schemas = [
        ("bronze", "s3://bronze/"),
        ("silver", "s3://silver/"),
        ("gold", "s3://gold/"),
    ]
    for s_name, loc in schemas:
        try:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS delta.{s_name} WITH (location = '{loc}')")
            log.info("Schema delta.%s ensured at %s", s_name, loc)
        except Exception as e:
            log.debug("Schema notice: %s", e)

    # 2. Register Delta Lake tables using Trino delta system procedure
    tables = [
        ("bronze", "yellow_trips", "s3://bronze/yellow_trips"),
        ("bronze", "green_trips", "s3://bronze/green_trips"),
        ("bronze", "fhv_trips", "s3://bronze/fhv_trips"),
        ("bronze", "fhvhv_trips", "s3://bronze/fhvhv_trips"),
        ("bronze", "quarantine", "s3://bronze/quarantine"),
        ("silver", "yellow_trips", "s3://silver/yellow_trips"),
        ("silver", "green_trips", "s3://silver/green_trips"),
        ("silver", "fhv_trips", "s3://silver/fhv_trips"),
        ("silver", "fhvhv_trips", "s3://silver/fhvhv_trips"),
        ("silver", "dim_taxi_zones", "s3://silver/dim_taxi_zones"),
        ("silver", "dim_weather_hourly", "s3://silver/dim_weather_hourly"),
        ("gold", "hourly_zone_metrics", "s3://gold/hourly_zone_metrics"),
        ("gold", "fhv_hourly_zone_metrics", "s3://gold/fhv_hourly_zone_metrics"),
        ("gold", "green_hourly_zone_metrics", "s3://gold/green_hourly_zone_metrics"),
        ("gold", "fhvhv_hourly_zone_metrics", "s3://gold/fhvhv_hourly_zone_metrics"),
        ("gold", "weather_taxi_features_hourly", "s3://gold/weather_taxi_features_hourly"),
        ("gold", "forecast_hourly_metrics", "s3://gold/forecast_hourly_metrics"),
    ]

    for schema_name, table_name, table_loc in tables:
        try:
            cursor.execute(f"""
                CALL delta.system.register_table(
                    schema_name => '{schema_name}',
                    table_name => '{table_name}',
                    table_location => '{table_loc}'
                )
            """)
            log.info("Registered Trino table delta.%s.%s -> %s", schema_name, table_name, table_loc)
        except Exception as e:
            err_msg = str(e)
            if "ALREADY_EXISTS" in err_msg or "already exists" in err_msg:
                log.debug("Table delta.%s.%s already registered.", schema_name, table_name)
            else:
                log.info("Register table notice for delta.%s.%s: %s", schema_name, table_name, err_msg[:120])

    cursor.close()
    if close_conn:
        conn.close()


def flush_trino_metadata_cache(conn=None) -> None:
    """Flush Trino metadata cache for all tables.

    Must be called after any Spark write/delete to prevent 
    HIVE_CANNOT_OPEN_SPLIT errors caused by stale file references.
    """
    close_conn = False
    if conn is None:
        conn = get_trino_connection()
        close_conn = True

    cursor = conn.cursor()
    try:
        # Flush the full catalog metadata cache (covers all Silver tables)
        cursor.execute("CALL delta.system.flush_metadata_cache()")
        log.info("Trino Delta metadata cache flushed successfully.")
    except Exception as e:
        log.warning("Could not flush Trino metadata cache: %s", e)
    finally:
        cursor.close()
        if close_conn:
            conn.close()


def run_query(cursor, sql: str, max_retries: int = 4, retry_delay: float = 3.0) -> list[Any]:
    """Execute SQL statement and return rows."""
    log.info("Executing:\n%s", sql.strip())
    for attempt in range(1, max_retries + 1):
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as exc:
            if ("SERVER_STARTING_UP" in str(exc) or "initializing" in str(exc)) and attempt < max_retries:
                log.warning("Trino initializing (attempt %d/%d). Retrying in %.1fs...", attempt, max_retries, retry_delay)
                time.sleep(retry_delay)
            else:
                raise


def run_assertion(cursor, check_name: str, sql: str, expect_zero: bool = True) -> tuple[bool, int]:
    """Run a QC assertion query."""
    rows = run_query(cursor, sql)
    count = rows[0][0] if rows else 0

    if expect_zero:
        passed = count == 0
    else:
        passed = count > 0

    status = "✅ PASS" if passed else "❌ FAIL"
    log.info("[%s] %s — value: %s", status, check_name, count)
    return passed, count


def build_quality_check_suite(source_month: str) -> list[tuple[str, str, bool]]:
    """Return list of (check_name, sql, expect_zero) assertions for Delta Lake."""
    month_filter = (
        f"_source_month = '{source_month}'"
        if source_month and source_month != "ALL"
        else "1=1"
    )

    return [
        (
            "B1_bronze_not_empty",
            "SELECT count(*) FROM delta.bronze.yellow_trips",
            False,
        ),
        (
            "S1_silver_not_empty",
            f"SELECT count(*) FROM delta.silver.yellow_trips WHERE {month_filter}",
            False,
        ),
        (
            "S2_silver_no_null_pickup",
            f"SELECT count(*) FROM delta.silver.yellow_trips WHERE {month_filter} AND tpep_pickup_datetime IS NULL",
            True,
        ),
        (
            "S3_silver_dropoff_gte_pickup",
            f"SELECT count(*) FROM delta.silver.yellow_trips WHERE {month_filter} AND tpep_dropoff_datetime < tpep_pickup_datetime",
            True,
        ),
        (
            "S4_silver_positive_distance",
            f"SELECT count(*) FROM delta.silver.yellow_trips WHERE {month_filter} AND trip_distance <= 0",
            True,
        ),
        (
            "G1_gold_not_empty",
            "SELECT count(*) FROM delta.gold.hourly_zone_metrics",
            False,
        ),
        (
            "G2_gold_no_duplicate_keys",
            """
            SELECT count(*)
            FROM (
                SELECT pickup_month, pickup_date, pickup_hour, pu_location_id
                FROM delta.gold.hourly_zone_metrics
                GROUP BY pickup_month, pickup_date, pickup_hour, pu_location_id
                HAVING count(*) > 1
            )
            """,
            True,
        ),
        (
            "G3_gold_valid_hours",
            "SELECT count(*) FROM delta.gold.hourly_zone_metrics WHERE pickup_hour < 0 OR pickup_hour > 23",
            True,
        ),
    ]
