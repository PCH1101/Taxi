"""
silver.py — Silver & Quarantine Tasks (NYC Taxi Lakehouse)
=========================================================
Self-contained PySpark logic for Quality Gates, Quarantine isolation, and Silver transformations.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    TimestampType,
)

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parents[1]
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from utils.spark import get_spark_session

log = logging.getLogger(__name__)

# ── Paths & Constants ──────────────────────────────────────────────────────────
DATA_DIR = Path("/opt/airflow/data" if Path("/opt/airflow/data").exists() else Path(__file__).resolve().parents[2] / "data")
BRONZE_PATH = "s3a://bronze/yellow_trips"
SILVER_PATH = "s3a://silver/yellow_trips"
QUARANTINE_PATH = "s3a://bronze/quarantine"
DIM_ZONES_PATH = "s3a://silver/dim_taxi_zones"
QUARANTINE_PATH = "s3a://bronze/quarantine"
NYC_LOOKUP_CSV_URL = os.environ.get("NYC_LOOKUP_CSV_URL", "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv")

DATASET_CONFIG = {
    "yellow": {"prefix": "yellow_tripdata", "table_name": "yellow_trips"},
    "green": {"prefix": "green_tripdata", "table_name": "green_trips"},
    "fhv": {"prefix": "fhv_tripdata", "table_name": "fhv_trips"},
    "fhvhv": {"prefix": "fhvhv_tripdata", "table_name": "fhvhv_trips"},
}


def get_dataset_info(dataset_type: str = "yellow") -> tuple[str, str]:
    """Returns (prefix, table_name) for a given dataset type."""
    clean_type = (dataset_type or "yellow").strip().lower()
    config = DATASET_CONFIG.get(clean_type, DATASET_CONFIG["yellow"])
    return config["prefix"], config["table_name"]


def get_dataset_type(**context) -> str:
    """Extract dataset_type from DAG context params, defaulting to 'yellow'."""
    val = context.get("params", {}).get("dataset_type", "yellow") if context else "yellow"
    clean_val = str(val).strip().lower()
    return clean_val if clean_val in DATASET_CONFIG else "yellow"


def normalize_month_stem(month_str: str, prefix: str = "yellow_tripdata") -> str:
    """Normalize input like '2024-01' or '{prefix}_2024-01' to '{prefix}_2024-01'."""
    clean = month_str.strip()
    if clean.endswith(".parquet"):
        clean = clean[:-8]
    for p in ["yellow_tripdata_", "green_tripdata_", "fhvhv_tripdata_", "fhv_tripdata_"]:
        if clean.startswith(p):
            clean = clean[len(p):]
            break
    if "-" in clean:
        clean = f"{prefix}_{clean}"
    return clean


def expand_month_inputs(input_str: str, prefix: str = "yellow_tripdata") -> list[str]:
    """Expands year or range or list into canonical stems (e.g. '2025' -> 12 months)."""
    clean = input_str.strip()
    if not clean or clean == "ALL":
        return []

    parts = [p.strip() for p in clean.split(",") if p.strip()]
    results: list[str] = []
    for part in parts:
        if part.isdigit() and len(part) == 4:
            year = int(part)
            for m in range(1, 13):
                results.append(f"{prefix}_{year}-{m:02d}")
        elif ".." in part:
            try:
                start_m, end_m = part.split("..", 1)
                for p in ["yellow_tripdata_", "green_tripdata_", "fhvhv_tripdata_", "fhv_tripdata_"]:
                    start_m = start_m.replace(p, "")
                    end_m = end_m.replace(p, "")
                sy, sm = map(int, start_m.strip().split("-"))
                ey, em = map(int, end_m.strip().split("-"))
                cur_y, cur_m = sy, sm
                while (cur_y < ey) or (cur_y == ey and cur_m <= em):
                    results.append(f"{prefix}_{cur_y}-{cur_m:02d}")
                    cur_m += 1
                    if cur_m > 12:
                        cur_m = 1
                        cur_y += 1
            except Exception:
                results.append(normalize_month_stem(part, prefix))
        else:
            results.append(normalize_month_stem(part, prefix))
    return results


def ingest_dim_zones(spark) -> None:
    """Ingests taxi_zone_lookup.csv into Delta format at s3a://silver/dim_taxi_zones."""
    csv_file = DATA_DIR / "taxi_zone_lookup.csv"
    temp_csv: str | None = None

    try:
        if csv_file.exists():
            csv_source = str(csv_file)
        else:
            log.info("Streaming remote taxi_zone_lookup.csv from: %s", NYC_LOOKUP_CSV_URL)
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                temp_csv = tmp.name
            urllib.request.urlretrieve(NYC_LOOKUP_CSV_URL, temp_csv)
            csv_source = temp_csv

        log.info("Ingesting Taxi Zones Dimension from: %s", csv_source)
        zones_df = (
            spark.read.option("header", "true")
            .option("inferSchema", "true")
            .csv(csv_source)
            .select(
                F.col("LocationID").cast(IntegerType()).alias("location_id"),
                F.col("Borough").cast(StringType()).alias("borough"),
                F.col("Zone").cast(StringType()).alias("zone_name"),
                F.col("service_zone").cast(StringType()).alias("service_zone"),
            )
        )

        (
            zones_df.write
            .format("delta")
            .mode("overwrite")
            .save(DIM_ZONES_PATH)
        )
        log.info("Dimension table written: %s (%d rows)", DIM_ZONES_PATH, zones_df.count())
    except Exception as e:
        log.warning("Could not ingest taxi zone lookup dimension: %s", e)
    finally:
        if temp_csv and os.path.exists(temp_csv):
            os.remove(temp_csv)


def populate_silver(**context) -> None:
    """Airflow task callable to transform Bronze into Silver & Quarantine Delta tables."""
    dataset_type = get_dataset_type(**context)
    prefix, table_name = get_dataset_info(dataset_type)
    bronze_path = f"s3a://bronze/{table_name}"
    silver_path = f"s3a://silver/{table_name}"
    quarantine_path = QUARANTINE_PATH

    param_val = context.get("params", {}).get("source_month", "").strip() if context else ""
    source_month = param_val or "2025"

    spark = get_spark_session(f"AirflowSilverTransform_{dataset_type}")

    try:
        if not DeltaTable.isDeltaTable(spark, bronze_path):
            log.warning("Bronze Delta table does not exist at %s. Skipping Silver for %s.", bronze_path, dataset_type)
            return

        bronze_df = spark.read.format("delta").load(bronze_path)

        # Ingest taxi zones lookup dimension
        ingest_dim_zones(spark)

        # Determine target months
        if source_month and source_month != "ALL":
            months_to_process = expand_month_inputs(source_month, prefix)
        else:
            bronze_months = [row._source_month for row in bronze_df.select("_source_month").distinct().collect()]
            if DeltaTable.isDeltaTable(spark, silver_path):
                silver_df = spark.read.format("delta").load(silver_path)
                silver_months = set(row._source_month for row in silver_df.select("_source_month").distinct().collect())
                months_to_process = [m for m in bronze_months if m not in silver_months]
            else:
                months_to_process = bronze_months

        if not months_to_process:
            log.info("No new months to process for Silver layer (%s).", dataset_type)
            return

        log.info("Transforming Silver & Quarantine for dataset '%s', months: %s", dataset_type, months_to_process)

        for month in months_to_process:
            log.info("--- Transforming %s month: %s ---", dataset_type, month)
            batch_df = bronze_df.filter(F.col("_source_month") == month)
            cols = batch_df.columns

            # Determine pickup and dropoff timestamps
            pickup_col = F.lit(None).cast(TimestampType())
            dropoff_col = F.lit(None).cast(TimestampType())

            for c in ["tpep_pickup_datetime", "lpep_pickup_datetime", "pickup_datetime", "Pickup_datetime"]:
                if c in cols:
                    pickup_col = F.col(c).cast(TimestampType())
                    break

            for c in ["tpep_dropoff_datetime", "lpep_dropoff_datetime", "dropoff_datetime", "dropOff_datetime", "DropOff_datetime"]:
                if c in cols:
                    dropoff_col = F.col(c).cast(TimestampType())
                    break

            norm_df = (
                batch_df
                .withColumn("_pickup_ts", pickup_col)
                .withColumn("_dropoff_ts", dropoff_col)
            )

            # Derive target year dynamically from month stem
            clean_stem = month
            for p in ["yellow_tripdata_", "green_tripdata_", "fhvhv_tripdata_", "fhv_tripdata_"]:
                clean_stem = clean_stem.replace(p, "")
            parts = clean_stem.split("-")
            target_year = int(parts[0]) if (parts and parts[0].isdigit()) else 2025
            min_valid_date = f"{target_year - 1}-12-01 00:00:00"
            max_valid_date = f"{target_year + 1}-01-15 23:59:59"

            # Quality Gate Conditions (Strict Year Range + Valid Physics)
            valid_timestamps = (
                F.col("_pickup_ts").isNotNull()
                & F.col("_dropoff_ts").isNotNull()
                & (F.col("_pickup_ts") >= F.to_timestamp(F.lit(min_valid_date)))
                & (F.col("_pickup_ts") <= F.to_timestamp(F.lit(max_valid_date)))
                & (F.col("_dropoff_ts") >= F.col("_pickup_ts"))
            )

            # Flexible column extraction helper
            def get_col(name: str, target_type, default_val=None, alt_names: list[str] | None = None):
                candidates = [name] + (alt_names or [])
                for cn in candidates:
                    if cn in cols:
                        return F.col(cn).cast(target_type)
                return F.lit(default_val).cast(target_type)

            # Dataset-specific validation condition
            if dataset_type == "fhv":
                valid_condition = valid_timestamps
            elif dataset_type in ("yellow", "green"):
                valid_numerics = (
                    (F.col("trip_distance") > 0)
                    & (F.col("passenger_count") > 0)
                    & (F.col("total_amount") >= 0)
                )
                if "PULocationID" in cols:
                    valid_numerics = valid_numerics & F.col("PULocationID").isNotNull()
                if "DOLocationID" in cols:
                    valid_numerics = valid_numerics & F.col("DOLocationID").isNotNull()
                valid_condition = valid_timestamps & valid_numerics
            else:  # fhvhv
                valid_condition = valid_timestamps

            # ── Step A: Idempotent Cleanup (Delete prior month partition if re-running) ───
            if DeltaTable.isDeltaTable(spark, silver_path):
                try:
                    silver_tbl = DeltaTable.forPath(spark, silver_path)
                    has_records = (
                        silver_tbl.toDF()
                        .filter(F.col("_source_month") == month)
                        .limit(1)
                        .count() > 0
                    )
                    if has_records:
                        log.info("Cleaning prior records in Silver (%s) for month: %s", silver_path, month)
                        silver_tbl.delete(F.col("_source_month") == month)
                except Exception as e:
                    log.warning("Could not delete prior Silver records for month %s: %s", month, e)

            if DeltaTable.isDeltaTable(spark, quarantine_path):
                try:
                    quarantine_tbl = DeltaTable.forPath(spark, quarantine_path)
                    has_quarantine = (
                        quarantine_tbl.toDF()
                        .filter(F.col("_source_month") == month)
                        .limit(1)
                        .count() > 0
                    )
                    if has_quarantine:
                        log.info("Cleaning prior records in Quarantine for month: %s", month)
                        quarantine_tbl.delete(F.col("_source_month") == month)
                except Exception as e:
                    log.warning("Could not delete prior Quarantine records for month %s: %s", month, e)

            # ── Step B: Silver (Valid rows & In-batch Deduplication) ───────────────────────
            if dataset_type == "fhv":
                dedup_keys = ["_pickup_ts", "_dropoff_ts"]
                if "dispatching_base_num" in cols:
                    dedup_keys.append("dispatching_base_num")
                if "PUlocationID" in cols or "PULocationID" in cols:
                    dedup_keys.append("PUlocationID" if "PUlocationID" in cols else "PULocationID")

                silver_batch = (
                    norm_df.filter(valid_condition)
                    .dropDuplicates(dedup_keys)
                    .select(
                        get_col("dispatching_base_num", StringType()).alias("dispatching_base_num"),
                        F.col("_pickup_ts").alias("pickup_datetime"),
                        F.col("_dropoff_ts").alias("dropoff_datetime"),
                        F.date_format(F.col("_pickup_ts"), "yyyy-MM").alias("pickup_month"),
                        F.to_date(F.col("_pickup_ts")).alias("pickup_date"),
                        F.hour(F.col("_pickup_ts")).cast(IntegerType()).alias("pickup_hour"),
                        get_col("PUlocationID", IntegerType(), alt_names=["PULocationID", "pu_location_id"]).alias("pu_location_id"),
                        get_col("DOlocationID", IntegerType(), alt_names=["DOLocationID", "do_location_id"]).alias("do_location_id"),
                        get_col("SR_Flag", StringType(), alt_names=["sr_flag"]).alias("sr_flag"),
                        get_col("Affiliated_base_number", StringType(), alt_names=["affiliated_base_number"]).alias("affiliated_base_number"),
                        F.lit(dataset_type).alias("_dataset_type"),
                        F.col("_source_file"),
                        F.col("_source_month"),
                        F.col("_ingested_at"),
                        F.col("_batch_id"),
                        F.current_timestamp().alias("_transformed_at"),
                    )
                )
            else:
                dedup_keys = ["_pickup_ts", "_dropoff_ts"]
                for k in ["trip_distance", "trip_miles", "VendorID", "vendor_id", "hvfhs_license_num", "PULocationID", "pulocationid", "DOLocationID", "dolocationid", "fare_amount", "base_passenger_fare"]:
                    if k in cols and k not in dedup_keys:
                        dedup_keys.append(k)

                # Vendor ID: for FHVHV map HV0003 -> 3 (Uber), HV0005 -> 5 (Lyft)
                vendor_expr = get_col("VendorID", IntegerType(), alt_names=["vendor_id"])
                if "hvfhs_license_num" in cols:
                    vendor_expr = (
                        F.when(F.col("hvfhs_license_num") == "HV0003", F.lit(3))
                        .when(F.col("hvfhs_license_num") == "HV0005", F.lit(5))
                        .otherwise(get_col("VendorID", IntegerType(), alt_names=["vendor_id"]))
                    )

                # Total Amount: for FHVHV calculate base_passenger_fare + tolls + bcf + sales_tax + congestion + airport_fee + tips
                if "total_amount" in cols:
                    total_amount_expr = get_col("total_amount", DecimalType(12, 2))
                elif "base_passenger_fare" in cols:
                    total_amount_expr = (
                        F.coalesce(get_col("base_passenger_fare", DoubleType()), F.lit(0.0))
                        + F.coalesce(get_col("tolls", DoubleType()), F.lit(0.0))
                        + F.coalesce(get_col("bcf", DoubleType()), F.lit(0.0))
                        + F.coalesce(get_col("sales_tax", DoubleType()), F.lit(0.0))
                        + F.coalesce(get_col("congestion_surcharge", DoubleType()), F.lit(0.0))
                        + F.coalesce(get_col("airport_fee", DoubleType()), F.lit(0.0))
                        + F.coalesce(get_col("tips", DoubleType()), F.lit(0.0))
                    ).cast(DecimalType(12, 2))
                else:
                    total_amount_expr = F.lit(None).cast(DecimalType(12, 2))

                silver_batch = (
                    norm_df.filter(valid_condition)
                    .dropDuplicates(dedup_keys)
                    .select(
                        vendor_expr.alias("vendor_id"),
                        F.col("_pickup_ts").alias("tpep_pickup_datetime"),
                        F.col("_dropoff_ts").alias("tpep_dropoff_datetime"),
                        F.date_format(F.col("_pickup_ts"), "yyyy-MM").alias("pickup_month"),
                        F.to_date(F.col("_pickup_ts")).alias("pickup_date"),
                        F.hour(F.col("_pickup_ts")).cast(IntegerType()).alias("pickup_hour"),
                        get_col("passenger_count", IntegerType()).alias("passenger_count"),
                        get_col("trip_distance", DoubleType(), alt_names=["trip_miles"]).alias("trip_distance"),
                        get_col("RatecodeID", IntegerType(), alt_names=["rate_code"]).alias("rate_code_id"),
                        get_col("store_and_fwd_flag", StringType()).alias("store_and_fwd_flag"),
                        get_col("PULocationID", IntegerType(), alt_names=["pu_location_id", "pulocationid"]).alias("pu_location_id"),
                        get_col("DOLocationID", IntegerType(), alt_names=["do_location_id", "dolocationid"]).alias("do_location_id"),
                        get_col("payment_type", IntegerType()).alias("payment_type"),
                        get_col("fare_amount", DecimalType(12, 2), alt_names=["base_passenger_fare"]).alias("fare_amount"),
                        get_col("extra", DecimalType(12, 2), alt_names=["surcharge"]).alias("extra"),
                        get_col("mta_tax", DecimalType(12, 2)).alias("mta_tax"),
                        get_col("tip_amount", DecimalType(12, 2), alt_names=["tips"]).alias("tip_amount"),
                        get_col("tolls_amount", DecimalType(12, 2), alt_names=["tolls"]).alias("tolls_amount"),
                        get_col("improvement_surcharge", DecimalType(12, 2), default_val=0.0).alias("improvement_surcharge"),
                        total_amount_expr.alias("total_amount"),
                        get_col("congestion_surcharge", DecimalType(12, 2), default_val=0.0).alias("congestion_surcharge"),
                        get_col("Airport_fee", DecimalType(12, 2), default_val=0.0, alt_names=["airport_fee"]).alias("airport_fee"),
                        get_col("driver_pay", DecimalType(12, 2), default_val=0.0).alias("driver_pay"),
                        get_col("hvfhs_license_num", StringType()).alias("hvfhs_license_num"),
                        F.lit(dataset_type).alias("_dataset_type"),
                        F.col("_source_file"),
                        F.col("_source_month"),
                        F.col("_ingested_at"),
                        F.col("_batch_id"),
                        F.current_timestamp().alias("_transformed_at"),
                    )
                )

            log.info("Writing valid records to Silver Delta table (%s)...", silver_path)
            (
                silver_batch.write
                .format("delta")
                .mode("append")
                .option("mergeSchema", "true")
                .partitionBy("pickup_month", "pickup_date")
                .save(silver_path)
            )

            # ── Quarantine (Invalid rows) ─────────────────────────────────────
            quarantine_batch = (
                norm_df.filter(~valid_condition)
                .withColumn(
                    "fail_reason",
                    F.when(
                        F.col("_pickup_ts").isNull() | F.col("_dropoff_ts").isNull(),
                        "null_timestamps",
                    )
                    .when(
                        (F.col("_pickup_ts") < F.to_timestamp(F.lit(min_valid_date)))
                        | (F.col("_pickup_ts") > F.to_timestamp(F.lit(max_valid_date))),
                        "out_of_target_year_range",
                    )
                    .when(F.col("_dropoff_ts") < F.col("_pickup_ts"), "dropoff_before_pickup")
                    .otherwise("invalid_numeric_fields"),
                )
                .withColumn("_dataset_type", F.lit(dataset_type))
                .withColumn("_quarantined_at", F.current_timestamp())
                .drop("_pickup_ts", "_dropoff_ts")
            )

            (
                quarantine_batch.write
                .format("delta")
                .mode("append")
                .option("mergeSchema", "true")
                .save(quarantine_path)
            )

            spark.catalog.clearCache()

        log.info("=== Silver & Quarantine complete for dataset '%s', months: %s ===", dataset_type, months_to_process)

    finally:
        spark.stop()
