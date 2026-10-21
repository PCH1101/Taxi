"""
feature_engineering.py — Build Gold Features for Taxi Demand & Revenue Forecasting
==================================================================================
Combines city-wide hourly NYC Taxi metrics with Open-Meteo hourly weather observations.
Computes calendar features, US holiday flags, weather interaction terms, and time-series
lag & rolling features. Saves output to Delta Lake at `s3a://gold/weather_taxi_features_hourly`.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parents[1]
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from delta.tables import DeltaTable
from pyspark.sql import Window, functions as F
from utils.spark import get_spark_session
from utils.trino_helper import flush_trino_metadata_cache, register_delta_tables_in_trino

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ── Paths ──────────────────────────────────────────────────────────────────────
GOLD_HOURLY_ZONE_PATH = "s3a://gold/hourly_zone_metrics"
SILVER_WEATHER_PATH = "s3a://silver/dim_weather_hourly"
GOLD_FEATURES_PATH = "s3a://gold/weather_taxi_features_hourly"

# 2025 US Federal Holidays
US_HOLIDAYS_2025 = [
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # Martin Luther King Jr. Day
    "2025-02-17",  # Washington's Birthday (Presidents' Day)
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-10-13",  # Columbus Day
    "2025-11-11",  # Veterans Day
    "2025-11-27",  # Thanksgiving Day
    "2025-12-25",  # Christmas Day
]


def build_weather_taxi_features(**kwargs: Any) -> None:
    """Aggregates city-wide taxi demand & revenue and joins with weather features."""
    log.info("=== Starting Feature Engineering: Taxi Demand & Weather ===")

    spark = get_spark_session("TaxiWeatherFeatureEngineering")

    # 1. Validate source tables
    if not DeltaTable.isDeltaTable(spark, GOLD_HOURLY_ZONE_PATH):
        raise RuntimeError(f"Missing Gold hourly zone metrics at {GOLD_HOURLY_ZONE_PATH}")
    if not DeltaTable.isDeltaTable(spark, SILVER_WEATHER_PATH):
        raise RuntimeError(f"Missing Silver weather table at {SILVER_WEATHER_PATH}")

    log.info("Loading Gold Zone metrics from %s...", GOLD_HOURLY_ZONE_PATH)
    zone_metrics_df = spark.read.format("delta").load(GOLD_HOURLY_ZONE_PATH)

    log.info("Loading Silver Weather from %s...", SILVER_WEATHER_PATH)
    weather_df = spark.read.format("delta").load(SILVER_WEATHER_PATH)

    # 2. Aggregate citywide hourly taxi metrics
    # Note: Filter to year 2025 to avoid partial boundary days from late 2024
    city_taxi_df = (
        zone_metrics_df.filter(F.col("pickup_date") >= F.lit("2025-01-01"))
        .filter(F.col("pickup_date") <= F.lit("2025-12-31"))
        .groupBy("pickup_date", "pickup_hour")
        .agg(
            F.sum("trip_count").cast("bigint").alias("trip_count"),
            F.round(F.sum("total_revenue"), 2).cast("double").alias("total_revenue"),
            F.round(F.sum("total_fare"), 2).cast("double").alias("total_fare"),
            F.round(F.sum("total_tip"), 2).cast("double").alias("total_tip"),
            F.round(F.avg("avg_trip_distance"), 2).cast("double").alias("avg_trip_distance"),
            F.round(F.avg("avg_duration_minutes"), 2).cast("double").alias("avg_duration_minutes"),
            F.round(F.avg("avg_passenger_count"), 2).cast("double").alias("avg_passenger_count"),
        )
    )

    # 3. Prepare Weather columns for joining
    weather_clean_df = weather_df.select(
        F.col("weather_date"),
        F.col("weather_hour"),
        F.col("temperature_2m"),
        F.col("relative_humidity_2m"),
        F.col("apparent_temperature"),
        F.col("precipitation"),
        F.col("snowfall"),
        F.col("weather_code"),
        F.col("weather_condition"),
        F.col("is_clear"),
        F.col("is_cloudy"),
        F.col("is_rain"),
        F.col("is_snow"),
        F.col("is_storm"),
        F.col("cloud_cover"),
        F.col("wind_speed_10m"),
        F.col("temp_range_day"),
        F.col("temp_delta_1h"),
    )

    # 4. Join City Taxi metrics with Weather on date & hour
    joined_df = city_taxi_df.join(
        weather_clean_df,
        (city_taxi_df["pickup_date"] == weather_clean_df["weather_date"])
        & (city_taxi_df["pickup_hour"] == weather_clean_df["weather_hour"]),
        how="inner",
    ).drop("weather_date", "weather_hour")

    # 5. Add Calendar & Holiday Features
    holiday_col = F.when(F.col("pickup_date").isin(US_HOLIDAYS_2025), F.lit(1)).otherwise(F.lit(0))

    joined_df = (
        joined_df.withColumn(
            "pickup_timestamp",
            F.to_timestamp(
                F.concat(
                    F.col("pickup_date"),
                    F.lit(" "),
                    F.lpad(F.col("pickup_hour").cast("string"), 2, "0"),
                    F.lit(":00:00"),
                ),
                "yyyy-MM-dd HH:mm:ss",
            ),
        )
        .withColumn("day_of_week", F.dayofweek(F.col("pickup_date")))  # 1=Sunday, 7=Saturday
        .withColumn("day_of_month", F.dayofmonth(F.col("pickup_date")))
        .withColumn("month", F.month(F.col("pickup_date")))
        .withColumn(
            "is_weekend",
            F.when(F.col("day_of_week").isin([1, 7]), F.lit(1)).otherwise(F.lit(0)),
        )
        .withColumn("is_us_holiday", holiday_col)
    )

    # 6. Interaction & Domain Features
    # Rush hours: Morning 7-9 AM, Evening 17-19 PM on weekdays
    is_weekday = F.col("is_weekend") == 0
    is_morning_rush = is_weekday & F.col("pickup_hour").isin([7, 8, 9])
    is_evening_rush = is_weekday & F.col("pickup_hour").isin([17, 18, 19])

    joined_df = (
        joined_df.withColumn(
            "is_rush_hour",
            F.when(is_morning_rush | is_evening_rush, F.lit(1)).otherwise(F.lit(0)),
        )
        .withColumn("rain_rush_hour", F.col("is_rain") * F.col("is_rush_hour"))
        .withColumn("snow_rush_hour", F.col("is_snow") * F.col("is_rush_hour"))
        .withColumn("cold_extreme", F.when(F.col("temperature_2m") <= 0.0, F.lit(1)).otherwise(F.lit(0)))
        .withColumn("hot_extreme", F.when(F.col("temperature_2m") >= 30.0, F.lit(1)).otherwise(F.lit(0)))
    )

    # 7. Time Series Lag & Rolling Features
    # Strict order by timestamp over entire continuous timeline
    w = Window.orderBy("pickup_timestamp")
    w_3h = Window.orderBy("pickup_timestamp").rowsBetween(-3, -1)
    w_24h = Window.orderBy("pickup_timestamp").rowsBetween(-24, -1)

    features_df = (
        joined_df.withColumn("demand_lag_1h", F.lag("trip_count", 1).over(w))
        .withColumn("demand_lag_2h", F.lag("trip_count", 2).over(w))
        .withColumn("demand_lag_24h", F.lag("trip_count", 24).over(w))
        .withColumn("demand_lag_168h", F.lag("trip_count", 168).over(w))
        .withColumn("revenue_lag_1h", F.lag("total_revenue", 1).over(w))
        .withColumn("revenue_lag_2h", F.lag("total_revenue", 2).over(w))
        .withColumn("revenue_lag_24h", F.lag("total_revenue", 24).over(w))
        .withColumn("revenue_lag_168h", F.lag("total_revenue", 168).over(w))
        .withColumn("demand_rolling_mean_3h", F.round(F.avg("trip_count").over(w_3h), 2))
        .withColumn("demand_rolling_mean_24h", F.round(F.avg("trip_count").over(w_24h), 2))
        .withColumn("revenue_rolling_mean_3h", F.round(F.avg("total_revenue").over(w_3h), 2))
        .withColumn("revenue_rolling_mean_24h", F.round(F.avg("total_revenue").over(w_24h), 2))
        .withColumn("_feature_built_at", F.lit(datetime.now(timezone.utc)))
    )

    # 8. Save to Delta Lake Gold table
    log.info("Writing Feature Store table to Delta Lake at %s...", GOLD_FEATURES_PATH)
    (
        features_df.write.format("delta")
        .mode("overwrite")
        .partitionBy("month")
        .save(GOLD_FEATURES_PATH)
    )

    log.info("Registering Gold feature table in Trino...")
    register_delta_tables_in_trino()
    flush_trino_metadata_cache()

    log.info("✅ Feature engineering completed successfully!")


if __name__ == "__main__":
    build_weather_taxi_features()
