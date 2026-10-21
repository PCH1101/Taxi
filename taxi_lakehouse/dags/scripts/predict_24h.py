"""
predict_24h.py — 24-Hour Ahead Batch Forecast for Taxi Demand & Revenue
=======================================================================
Pulls Open-Meteo weather forecast for NYC for the upcoming 24 hours,
constructs sequential time-series feature vectors using trained LightGBM models,
generates hourly predictions for Trip Demand and Revenue, and writes results
into Delta Lake Gold (`s3a://gold/forecast_hourly_metrics`) and Trino.
"""

from __future__ import annotations

import logging
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parents[1]
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

import numpy as np
import pandas as pd
from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
from scripts.feature_engineering import US_HOLIDAYS_2025
from scripts.weather_etl import fetch_weather_forecast, impute_and_clean_weather_records
from utils.spark import get_spark_session
from utils.trino_helper import flush_trino_metadata_cache, register_delta_tables_in_trino

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

GOLD_FEATURES_PATH = "s3a://gold/weather_taxi_features_hourly"
GOLD_FORECAST_PATH = "s3a://gold/forecast_hourly_metrics"

MODELS_DIR = DAGS_DIR / "models"
if not MODELS_DIR.exists():
    MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


def load_trained_models() -> Tuple[Any, Any]:
    """Load pre-trained LightGBM Demand and Revenue models."""
    demand_path = MODELS_DIR / "lgbm_demand_model.pkl"
    revenue_path = MODELS_DIR / "lgbm_revenue_model.pkl"

    if not demand_path.exists() or not revenue_path.exists():
        raise FileNotFoundError(f"Missing model files in {MODELS_DIR}. Please run train_forecast_models.py first.")

    with open(demand_path, "rb") as f:
        demand_model = pickle.load(f)
    with open(revenue_path, "rb") as f:
        revenue_model = pickle.load(f)

    log.info("Successfully loaded Demand and Revenue LightGBM models from %s", MODELS_DIR)
    return demand_model, revenue_model


def run_batch_forecast_24h(**kwargs: Any) -> None:
    """Execute 24-hour forward forecast and save predictions to Delta Lake Gold."""
    log.info("=== Starting 24-Hour Batch Forecast Pipeline ===")

    demand_model, revenue_model = load_trained_models()
    feature_cols = demand_model.feature_name_

    # 1. Fetch upcoming weather forecast from Open-Meteo
    log.info("Fetching upcoming weather forecast from Open-Meteo...")
    weather_payload = fetch_weather_forecast(forecast_days=2)
    cleaned_weather = impute_and_clean_weather_records(weather_payload.get("hourly", {}))
    if not cleaned_weather:
        raise RuntimeError("Failed to fetch weather forecast records from Open-Meteo.")

    # Convert to DataFrame and sort by time
    weather_df = pd.DataFrame(cleaned_weather).sort_values("weather_time_str").reset_index(drop=True)
    # Take the next 24 hours
    forecast_weather = weather_df.iloc[:24].copy().reset_index(drop=True)
    log.info("Loaded 24 forecast hours: %s to %s", forecast_weather["weather_time_str"].iloc[0], forecast_weather["weather_time_str"].iloc[-1])

    # 2. Load historical actuals from Delta Lake to seed lag features
    spark = get_spark_session("TaxiForecastBatch")
    if not DeltaTable.isDeltaTable(spark, GOLD_FEATURES_PATH):
        raise RuntimeError(f"Feature store not found at {GOLD_FEATURES_PATH}")

    log.info("Reading seed historical features from Delta Lake at %s...", GOLD_FEATURES_PATH)
    recent_features_df = (
        spark.read.format("delta")
        .load(GOLD_FEATURES_PATH)
        .orderBy(F.col("pickup_timestamp").desc())
        .limit(168)
        .toPandas()
        .sort_values("pickup_timestamp")
        .reset_index(drop=True)
    )

    # 3. Iterative Multi-step Forecasting for 24 Hours
    # Lags buffer: keep track of recent trip_count and total_revenue
    history_demand = list(recent_features_df["trip_count"].values)
    history_revenue = list(recent_features_df["total_revenue"].values)

    forecast_results: List[Dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)

    for step in range(len(forecast_weather)):
        row = forecast_weather.iloc[step]
        t_str = row["weather_time_str"]
        dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")

        d_lag_1h = history_demand[-1]
        d_lag_2h = history_demand[-2] if len(history_demand) >= 2 else d_lag_1h
        d_lag_24h = history_demand[-24] if len(history_demand) >= 24 else d_lag_1h
        d_lag_168h = history_demand[-168] if len(history_demand) >= 168 else d_lag_24h

        r_lag_1h = history_revenue[-1]
        r_lag_2h = history_revenue[-2] if len(history_revenue) >= 2 else r_lag_1h
        r_lag_24h = history_revenue[-24] if len(history_revenue) >= 24 else r_lag_1h
        r_lag_168h = history_revenue[-168] if len(history_revenue) >= 168 else r_lag_24h

        d_roll_3h = float(np.mean(history_demand[-3:]))
        d_roll_24h = float(np.mean(history_demand[-24:]))
        r_roll_3h = float(np.mean(history_revenue[-3:]))
        r_roll_24h = float(np.mean(history_revenue[-24:]))

        is_weekend = 1 if dt.weekday() in (5, 6) else 0
        date_str = dt.strftime("%Y-%m-%d")
        is_holiday = 1 if date_str in US_HOLIDAYS_2025 else 0

        is_rush = 1 if (is_weekend == 0 and dt.hour in (7, 8, 9, 17, 18, 19)) else 0
        rain_rush = row["is_rain"] * is_rush
        snow_rush = row["is_snow"] * is_rush
        cold_ext = 1 if row["temperature_2m"] <= 0.0 else 0
        hot_ext = 1 if row["temperature_2m"] >= 30.0 else 0

        # Construct single feature row matching training columns
        features = {
            "pickup_hour": dt.hour,
            "day_of_week": (dt.weekday() + 1) % 7 + 1,  # Spark format: 1=Sun, 7=Sat
            "day_of_month": dt.day,
            "month": dt.month,
            "is_weekend": is_weekend,
            "is_us_holiday": is_holiday,
            "is_rush_hour": is_rush,
            "rain_rush_hour": rain_rush,
            "snow_rush_hour": snow_rush,
            "cold_extreme": cold_ext,
            "hot_extreme": hot_ext,
            "temperature_2m": row["temperature_2m"],
            "apparent_temperature": row["apparent_temperature"],
            "precipitation": row["precipitation"],
            "snowfall": row["snowfall"],
            "cloud_cover": row["cloud_cover"],
            "wind_speed_10m": row["wind_speed_10m"],
            "temp_range_day": row["temp_range_day"],
            "temp_delta_1h": row["temp_delta_1h"],
            "is_clear": row["is_clear"],
            "is_cloudy": row["is_cloudy"],
            "is_rain": row["is_rain"],
            "is_snow": row["is_snow"],
            "is_storm": row["is_storm"],
            "demand_lag_1h": d_lag_1h,
            "demand_lag_2h": d_lag_2h,
            "demand_lag_24h": d_lag_24h,
            "demand_lag_168h": d_lag_168h,
            "revenue_lag_1h": r_lag_1h,
            "revenue_lag_2h": r_lag_2h,
            "revenue_lag_24h": r_lag_24h,
            "revenue_lag_168h": r_lag_168h,
            "demand_rolling_mean_3h": d_roll_3h,
            "demand_rolling_mean_24h": d_roll_24h,
            "revenue_rolling_mean_3h": r_roll_3h,
            "revenue_rolling_mean_24h": r_roll_24h,
        }

        X_input = pd.DataFrame([features])[feature_cols]

        pred_demand = max(0, int(round(demand_model.predict(X_input)[0])))
        pred_revenue = max(0.0, float(round(revenue_model.predict(X_input)[0], 2)))
        pred_avg_fare = round(pred_revenue / pred_demand, 2) if pred_demand > 0 else 0.0

        # Update dynamic history
        history_demand.append(pred_demand)
        history_revenue.append(pred_revenue)

        forecast_results.append(
            {
                "forecast_time_str": t_str,
                "forecast_date": date_str,
                "forecast_month": date_str[:7],
                "forecast_hour": dt.hour,
                "predicted_trip_count": pred_demand,
                "predicted_total_revenue": pred_revenue,
                "predicted_avg_fare": pred_avg_fare,
                "temperature_2m": row["temperature_2m"],
                "apparent_temperature": row["apparent_temperature"],
                "precipitation": row["precipitation"],
                "snowfall": row["snowfall"],
                "weather_condition": row["weather_condition"],
                "cloud_cover": row["cloud_cover"],
                "wind_speed_10m": row["wind_speed_10m"],
                "temp_range_day": row["temp_range_day"],
                "temp_delta_1h": row["temp_delta_1h"],
                "is_rush_hour": is_rush,
                "forecast_generated_at": generated_at,
            }
        )

    log.info("Generated %d hourly forecasts.", len(forecast_results))

    # 4. Write to Delta Lake Gold table
    pd_pred_df = pd.DataFrame(forecast_results)
    pred_df = spark.createDataFrame(pd_pred_df).withColumn(
        "forecast_timestamp", F.to_timestamp(F.col("forecast_time_str"), "yyyy-MM-dd HH:mm:ss")
    )

    if DeltaTable.isDeltaTable(spark, GOLD_FORECAST_PATH):
        log.info("Merging forecasts into existing Delta table at %s...", GOLD_FORECAST_PATH)
        delta_tbl = DeltaTable.forPath(spark, GOLD_FORECAST_PATH)
        (
            delta_tbl.alias("target")
            .merge(
                pred_df.alias("source"),
                "target.forecast_timestamp = source.forecast_timestamp",
            )
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
    else:
        log.info("Creating new Gold Forecast table at %s...", GOLD_FORECAST_PATH)
        (
            pred_df.write.format("delta")
            .mode("overwrite")
            .partitionBy("forecast_month")
            .save(GOLD_FORECAST_PATH)
        )

    log.info("Registering forecast table in Trino...")
    register_delta_tables_in_trino()
    flush_trino_metadata_cache()

    log.info("✅ 24-Hour forecast batch pipeline completed successfully!")


if __name__ == "__main__":
    run_batch_forecast_24h()
