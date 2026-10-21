"""
spark.py — SparkSession factory for Delta Lake and MinIO S3A within Airflow DAGs.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip


def get_spark_session(app_name: str = "TaxiLakehouseAirflow") -> SparkSession:
    """Creates and returns a SparkSession configured with Delta Lake and MinIO S3A."""
    # Support both local MinIO and Cloud S3 endpoints (Cloudflare R2, AWS S3, etc.)
    default_endpoint = "http://minio:9000" if Path("/.dockerenv").exists() else "http://localhost:9000"
    s3_endpoint = os.environ.get("S3_ENDPOINT", os.environ.get("MINIO_ENDPOINT", default_endpoint))
    access_key = os.environ.get("S3_ACCESS_KEY", os.environ.get("MINIO_PIPELINE_ACCESS_KEY", "pipeline-access-key"))
    secret_key = os.environ.get("S3_SECRET_KEY", os.environ.get("MINIO_PIPELINE_SECRET_KEY", "pipeline-secret-key-change-me"))
    s3_region = os.environ.get("S3_REGION", "us-east-1")
    is_ssl = s3_endpoint.lower().startswith("https://")

    driver_mem = os.environ.get("SPARK_DRIVER_MEMORY", "2g")
    master = os.environ.get("SPARK_MASTER", "local[2]")

    extra_packages = [
        "org.apache.hadoop:hadoop-aws:3.3.4",
        "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    ]

    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        # Memory & CPU Constraints (Strict 2GB Limit)
        .config("spark.driver.memory", driver_mem)
        .config("spark.driver.memoryOverhead", "384m")
        .config(
            "spark.driver.extraJavaOptions",
            "-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35 -XX:G1ReservePercent=15 -Djava.net.preferIPv4Stack=true",
        )
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.default.parallelism", "2")
        .config("spark.memory.fraction", "0.6")
        .config("spark.memory.storageFraction", "0.3")
        # Delta Lake Integration
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        # Object Storage / S3A FileSystem configurations (Disk buffer to prevent Off-Heap OOM)
        .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", access_key)
        .config("spark.hadoop.fs.s3a.secret.key", secret_key)
        .config("spark.hadoop.fs.s3a.endpoint.region", s3_region)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "true" if is_ssl else "false")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.hadoop.fs.s3a.fast.upload", "true")
        .config("spark.hadoop.fs.s3a.fast.upload.buffer", "disk")
        .config("spark.hadoop.fs.s3a.multipart.size", "16777216")
        .config("spark.hadoop.fs.s3a.threads.max", "4")
        # Optimizations & Fault Tolerance
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
        .config("spark.sql.files.ignoreMissingFiles", "true")
        .config("spark.sql.files.ignoreCorruptFiles", "true")
        .config("spark.databricks.delta.retentionDurationCheck.enabled", "false")
        .config("spark.databricks.delta.vacuum.parallelDelete.enabled", "true")
    )

    spark = configure_spark_with_delta_pip(builder, extra_packages=extra_packages).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark

