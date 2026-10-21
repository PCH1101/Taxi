"""
gold.py — Gold Layer (NYC Taxi Lakehouse)
================================================================
Executes transformations for the Gold layer using PySpark on top of Delta Lake.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parents[1]
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from delta.tables import DeltaTable
from pyspark.sql import functions as F
from scripts.silver import expand_month_inputs
from utils.spark import get_spark_session

log = logging.getLogger(__name__)

DATASET_CONFIG = {
    "yellow": {"prefix": "yellow_tripdata", "silver_table": "yellow_trips", "gold_table": "hourly_zone_metrics"},
    "green": {"prefix": "green_tripdata", "silver_table": "green_trips", "gold_table": "green_hourly_zone_metrics"},
    "fhv": {"prefix": "fhv_tripdata", "silver_table": "fhv_trips", "gold_table": "fhv_hourly_zone_metrics"},
    "fhvhv": {"prefix": "fhvhv_tripdata", "silver_table": "fhvhv_trips", "gold_table": "fhvhv_hourly_zone_metrics"},
}


def rebuild_gold(**context) -> None:
    """Airflow task callable to execute Gold layer transformations via PySpark."""
    dataset_type = str(context.get("params", {}).get("dataset_type", "yellow")).strip().lower() if context else "yellow"
    if dataset_type not in DATASET_CONFIG:
        dataset_type = "yellow"

    cfg = DATASET_CONFIG[dataset_type]
    silver_trips_path = f"s3a://silver/{cfg['silver_table']}"
    gold_metrics_path = f"s3a://gold/{cfg['gold_table']}"
    dim_zones_path = "s3a://silver/dim_taxi_zones"

    param_val = context.get("params", {}).get("source_month", "").strip() if context else ""
    source_month = param_val or "ALL"

    log.info("=== Starting Gold Stage for %s (source_month: %s) ===", dataset_type, source_month)

    spark = get_spark_session(f"AirflowGoldTransform_{dataset_type}")

    try:
        # Load Silver tables
        if not DeltaTable.isDeltaTable(spark, silver_trips_path):
            log.warning("Silver trips table not found at %s. Skipping Gold.", silver_trips_path)
            return

        silver_df = spark.read.format("delta").load(silver_trips_path)

        if DeltaTable.isDeltaTable(spark, dim_zones_path):
            dim_zones_df = spark.read.format("delta").load(dim_zones_path)
        else:
            log.warning("Dim zones table not found at %s. Using empty DF.", dim_zones_path)
            dim_zones_df = spark.createDataFrame([], schema="location_id INT, borough STRING, zone_name STRING, service_zone STRING")

        # Apply source_month filter if needed
        if source_month and source_month != "ALL":
            target_stems = expand_month_inputs(source_month, cfg["prefix"])
            if target_stems:
                silver_df = silver_df.filter(F.col("_source_month").isin(target_stems))
            else:
                silver_df = silver_df.filter(F.col("_source_month").contains(source_month))

        # Register Temp Views
        silver_df.createOrReplaceTempView("silver_trips_raw")
        dim_zones_df.createOrReplaceTempView("dim_taxi_zones")

        if dataset_type == "fhv":
            gold_df = spark.sql("""
            WITH silver_trips AS (
                SELECT
                    pickup_datetime,
                    dropoff_datetime,
                    substring(cast(pickup_date as string), 1, 7) as pickup_month,
                    pickup_date,
                    pickup_hour,
                    pu_location_id,
                    dispatching_base_num,
                    sr_flag,
                    _source_month,
                    (unix_timestamp(dropoff_datetime) - unix_timestamp(pickup_datetime)) / 60.0 as duration_minutes
                FROM silver_trips_raw
                WHERE (unix_timestamp(dropoff_datetime) - unix_timestamp(pickup_datetime)) >= 0
            ),

            aggregated_metrics AS (
                SELECT
                    pickup_month,
                    pickup_date,
                    pickup_hour,
                    pu_location_id,
                    count(*) as trip_count,
                    count(distinct dispatching_base_num) as active_bases,
                    sum(case when sr_flag is not null and sr_flag != '' then 1 else 0 end) as shared_rides,
                    cast(round(avg(duration_minutes), 2) as decimal(8, 2)) as avg_duration_minutes,
                    concat_ws(',', collect_set(_source_month)) as _source_months
                FROM silver_trips
                GROUP BY
                    pickup_month,
                    pickup_date,
                    pickup_hour,
                    pu_location_id
            ),

            enriched_gold AS (
                SELECT
                    agg.pickup_month,
                    agg.pickup_date,
                    agg.pickup_hour,
                    agg.pu_location_id,
                    dim.borough,
                    dim.zone_name,
                    dim.service_zone,
                    agg.trip_count,
                    agg.active_bases,
                    agg.shared_rides,
                    agg.avg_duration_minutes,
                    agg._source_months,
                    current_timestamp() as _gold_built_at
                FROM aggregated_metrics agg
                LEFT JOIN dim_taxi_zones dim
                    ON agg.pu_location_id = dim.location_id
            )

            SELECT * FROM enriched_gold
            """)
        else:
            # Yellow / Green taxi schema with revenue and fare metrics
            gold_df = spark.sql("""
            WITH silver_trips AS (
                SELECT
                    tpep_pickup_datetime,
                    tpep_dropoff_datetime,
                    substring(cast(pickup_date as string), 1, 7) as pickup_month,
                    pickup_date,
                    pickup_hour,
                    pu_location_id,
                    passenger_count,
                    trip_distance,
                    fare_amount,
                    tip_amount,
                    total_amount,
                    _source_month,
                    (unix_timestamp(tpep_dropoff_datetime) - unix_timestamp(tpep_pickup_datetime)) / 60.0 as duration_minutes
                FROM silver_trips_raw
                WHERE (unix_timestamp(tpep_dropoff_datetime) - unix_timestamp(tpep_pickup_datetime)) >= 0
            ),

            aggregated_metrics AS (
                SELECT
                    pickup_month,
                    pickup_date,
                    pickup_hour,
                    pu_location_id,
                    count(*) as trip_count,
                    cast(sum(total_amount) as decimal(18, 2)) as total_revenue,
                    cast(sum(fare_amount) as decimal(18, 2)) as total_fare,
                    cast(sum(tip_amount) as decimal(18, 2)) as total_tip,
                    cast(
                        case 
                            when sum(fare_amount) = 0 then null
                            else round(sum(tip_amount) / sum(fare_amount), 4)
                        end as decimal(8, 4)
                    ) as tip_rate,
                    cast(round(avg(trip_distance), 2) as decimal(8, 2)) as avg_trip_distance,
                    cast(round(avg(duration_minutes), 2) as decimal(8, 2)) as avg_duration_minutes,
                    cast(round(avg(passenger_count), 2) as decimal(6, 2)) as avg_passenger_count,
                    concat_ws(',', collect_set(_source_month)) as _source_months
                FROM silver_trips
                GROUP BY
                    pickup_month,
                    pickup_date,
                    pickup_hour,
                    pu_location_id
            ),

            enriched_gold AS (
                SELECT
                    agg.pickup_month,
                    agg.pickup_date,
                    agg.pickup_hour,
                    agg.pu_location_id,
                    dim.borough,
                    dim.zone_name,
                    dim.service_zone,
                    agg.trip_count,
                    agg.total_revenue,
                    agg.total_fare,
                    agg.total_tip,
                    agg.tip_rate,
                    agg.avg_trip_distance,
                    agg.avg_duration_minutes,
                    agg.avg_passenger_count,
                    agg._source_months,
                    current_timestamp() as _gold_built_at
                FROM aggregated_metrics agg
                LEFT JOIN dim_taxi_zones dim
                    ON agg.pu_location_id = dim.location_id
            )

            SELECT * FROM enriched_gold
            """)

        log.info("--- Step 1: Overwriting Gold Delta Table (%s) ---", gold_metrics_path)
        (
            gold_df.write
            .format("delta")
            .mode("overwrite")
            .option("mergeSchema", "true")
            .partitionBy("pickup_month")
            .save(gold_metrics_path)
        )

        log.info("=== Gold Stage Completed Successfully for %s ===", dataset_type)

    finally:
        spark.stop()
