"""
bronze.py — Bronze Layer Tasks (NYC Taxi Lakehouse)
===================================================
Self-contained PySpark logic for source month detection, validation, and Delta Lake ingestion.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from delta.tables import DeltaTable
from pyspark.sql import functions as F

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parents[1]
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from utils.spark import get_spark_session

try:
    from airflow.exceptions import AirflowException
except ImportError:
    class AirflowException(Exception):  # type: ignore[no-redef]
        """Fallback when running outside of Airflow environment."""
        pass

log = logging.getLogger(__name__)

# ── Paths & Constants ──────────────────────────────────────────────────────────
DATA_DIR = Path("/opt/airflow/data" if Path("/opt/airflow/data").exists() else Path(__file__).resolve().parents[2] / "data")
NYC_TLC_BASE_URL = os.environ.get("NYC_TLC_BASE_URL", "https://d37ci6vzurychx.cloudfront.net/trip-data")

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
        # Check if 4 digit year e.g. "2025"
        if part.isdigit() and len(part) == 4:
            year = int(part)
            for m in range(1, 13):
                results.append(f"{prefix}_{year}-{m:02d}")
        elif ".." in part:
            # Range e.g. "2025-01..2025-06"
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


def file_checksum(path: Path) -> str:
    """SHA-256 of the first 64 KB."""
    sha = hashlib.sha256()
    with path.open("rb") as f:
        sha.update(f.read(65536))
    return sha.hexdigest()[:16]


def get_source_month(**context) -> str:
    """Derive target month from DAG Param or default to '2025'."""
    param_val = context.get("params", {}).get("source_month", "").strip() if context else ""
    return param_val or "2025"


def check_data_files(**context) -> None:
    """Validate that target data source(s) exist (locally or via remote NYC TLC CDN)."""
    dataset_type = get_dataset_type(**context)
    prefix, _ = get_dataset_info(dataset_type)
    source_month = get_source_month(**context)
    source_mode = context.get("params", {}).get("source_mode", "AUTO") if context else "AUTO"

    if source_month and source_month != "ALL":
        month_stems = expand_month_inputs(source_month, prefix)
        for target_stem in month_stems:
            local_file = DATA_DIR / f"{target_stem}.parquet"
            if local_file.exists() and source_mode in ("AUTO", "LOCAL"):
                log.info("Validated local data file: %s (%d bytes)", local_file.name, local_file.stat().st_size)
            else:
                remote_url = f"{NYC_TLC_BASE_URL}/{target_stem}.parquet"
                log.info("Remote data stream ready: %s", remote_url)
    else:
        # ALL mode: check local files matching prefix
        local_files = list(DATA_DIR.glob(f"{prefix}_*.parquet")) if DATA_DIR.exists() else []
        if local_files:
            log.info("Validated %d local parquet file(s) for '%s' in %s", len(local_files), dataset_type, DATA_DIR)
        else:
            log.info("No local parquet files matching %s_*.parquet in %s. Remote download will be used.", prefix, DATA_DIR)


def ingest_bronze_source(spark, source_identifier: str | Path, dataset_type: str = "yellow") -> None:
    """Ingests a single parquet file (local Path or remote HTTP/S3 URL) into Bronze Delta table."""
    prefix, table_name = get_dataset_info(dataset_type)
    bronze_path = f"s3a://bronze/{table_name}"

    if isinstance(source_identifier, Path):
        source_month = normalize_month_stem(source_identifier.stem, prefix)
        checksum = file_checksum(source_identifier)
        batch_id = f"{source_month}_{checksum}"
        source_uri = str(source_identifier)
    else:
        # Remote URL or stem
        if source_identifier.startswith("http://") or source_identifier.startswith("https://") or source_identifier.startswith("s3a://"):
            source_uri = source_identifier
            stem = source_identifier.split("/")[-1].replace(".parquet", "")
            source_month = normalize_month_stem(stem, prefix)
        else:
            source_month = normalize_month_stem(source_identifier, prefix)
            source_uri = f"{NYC_TLC_BASE_URL}/{source_month}.parquet"
        batch_id = f"remote_{source_month}"

    log.info("--- Bronze Ingestion [%s]: %s (Batch: %s, Table: %s) ---", dataset_type, source_uri, batch_id, bronze_path)

    # Idempotency check with partition pruning
    try:
        if DeltaTable.isDeltaTable(spark, bronze_path):
            existing_df = spark.read.format("delta").load(bronze_path)
            already_ingested = (
                existing_df
                .filter(F.col("_source_month") == source_month)
                .filter(F.col("_batch_id") == batch_id)
                .limit(1)
                .count() > 0
            )
            if already_ingested:
                log.info("Batch '%s' already in Bronze Delta table %s — skipping.", batch_id, bronze_path)
                return
    except Exception as e:
        log.debug("Delta table check notice: %s", e)

    temp_path: str | None = None
    try:
        if isinstance(source_identifier, Path):
            parquet_read_path = str(source_identifier)
        elif source_uri.startswith("http://") or source_uri.startswith("https://"):
            log.info("Streaming remote parquet to temporary buffer from: %s", source_uri)
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                temp_path = tmp.name
            urllib.request.urlretrieve(source_uri, temp_path)
            file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
            log.info("Streamed %.2f MB to temporary buffer: %s", file_size_mb, temp_path)
            parquet_read_path = temp_path
        else:
            parquet_read_path = source_uri

        raw_df = spark.read.parquet(parquet_read_path)

        # Drop pandas temporary index column if present
        if "__index_level_0__" in raw_df.columns:
            raw_df = raw_df.drop("__index_level_0__")

        # Cast drift-prone columns to string to prevent schema merge type collision across months
        drift_cols = [
            "rate_code", "RatecodeID", "vendor_id", "VendorID", "store_and_fwd_flag",
            "dispatching_base_num", "Affiliated_base_number", "SR_Flag", "sr_flag"
        ]
        for col_name in drift_cols:
            if col_name in raw_df.columns:
                raw_df = raw_df.withColumn(col_name, F.col(col_name).cast("string"))

        bronze_df = (
            raw_df
            .withColumn("_source_file", F.lit(source_uri))
            .withColumn("_source_month", F.lit(source_month))
            .withColumn("_dataset_type", F.lit(dataset_type))
            .withColumn("_ingested_at", F.current_timestamp())
            .withColumn("_batch_id", F.lit(batch_id))
        )

        writer = bronze_df.write.format("delta").mode("append").option("mergeSchema", "true")
        if not DeltaTable.isDeltaTable(spark, bronze_path):
            writer = writer.partitionBy("_source_month")
        writer.save(bronze_path)
        log.info("Successfully appended %s to Bronze Delta table (%s).", source_uri, bronze_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            log.debug("Cleaned up temporary buffer: %s", temp_path)


def ingest_bronze(**context) -> None:
    """Main Airflow task callable to ingest Parquet files into Bronze Delta table."""
    dataset_type = get_dataset_type(**context)
    prefix, _ = get_dataset_info(dataset_type)
    source_month = get_source_month(**context)
    source_mode = context.get("params", {}).get("source_mode", "AUTO") if context else "AUTO"

    targets: list[str | Path] = []

    if source_month and source_month != "ALL":
        month_stems = expand_month_inputs(source_month, prefix)
        for stem in month_stems:
            local_file = DATA_DIR / f"{stem}.parquet"
            if local_file.exists() and source_mode in ("AUTO", "LOCAL"):
                targets.append(local_file)
            else:
                targets.append(f"{NYC_TLC_BASE_URL}/{stem}.parquet")
    else:
        # ALL mode: scan local files matching prefix
        if DATA_DIR.exists():
            targets.extend(sorted(DATA_DIR.glob(f"{prefix}_*.parquet")))
        if not targets:
            raise AirflowException(f"No local files matching '{prefix}_*.parquet' in {DATA_DIR} and no specific source_month provided.")

    log.info("Starting Bronze ingestion for %d source(s) (Dataset: %s)...", len(targets), dataset_type)
    spark = get_spark_session(f"AirflowBronzeIngestion_{dataset_type}")
    try:
        for target in targets:
            ingest_bronze_source(spark, target, dataset_type)
            spark.catalog.clearCache()

        log.info("=== Bronze Ingestion complete for %d source(s) (%s) ===", len(targets), dataset_type)
    finally:
        spark.stop()

