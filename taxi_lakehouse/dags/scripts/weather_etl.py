"""
weather_etl.py — Open-Meteo Weather Ingestion & Transformation
==============================================================
Pulls hourly weather data for New York City (NYC) from Open-Meteo API,
imputes missing data (Forward-Fill & Interpolation), computes temperature ranges
and weather condition classifications, then writes to Bronze (Raw) and Silver (Delta Lake).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

# Ensure dags directory is in sys.path
DAGS_DIR = Path(__file__).resolve().parents[1]
if str(DAGS_DIR) not in sys.path:
    sys.path.insert(0, str(DAGS_DIR))

from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
from delta.tables import DeltaTable
from utils.spark import get_spark_session

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ── Paths & Endpoints ─────────────────────────────────────────────────────────
NYC_LATITUDE = 40.7128
NYC_LONGITUDE = -74.0060
NYC_TIMEZONE = "America/New_York"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

BRONZE_WEATHER_PATH = "s3a://bronze/weather"
SILVER_WEATHER_PATH = "s3a://silver/dim_weather_hourly"
SILVER_TAXI_PATH = "s3a://silver/yellow_trips"


def classify_wmo_weather_code(code: Optional[int]) -> str:
    """Maps WMO weather interpretation code to clear semantic category."""
    if code is None:
        return "unknown"
    if code == 0:
        return "clear"
    elif code in (1, 2, 3):
        return "cloudy"
    elif code in (45, 48):
        return "fog"
    elif code in (51, 53, 55, 56, 57):
        return "drizzle"
    elif code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    elif code in (71, 73, 75, 77, 85, 86):
        return "snow"
    elif code in (95, 96, 99):
        return "storm"
    return "other"


def fetch_open_meteo_api(
    url: str,
    params: Dict[str, Any],
    max_retries: int = 5,
    backoff_factor: float = 2.0,
) -> Dict[str, Any]:
    """Fetch data from Open-Meteo REST API with exponential backoff."""
    query_str = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query_str}"
    log.info("Requesting Open-Meteo: %s", full_url)

    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "TaxiLakehousePipeline/1.0 (Airflow-DE)"},
    )

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    return payload
                else:
                    log.warning("HTTP %d on attempt %d/%d", response.status, attempt, max_retries)
        except Exception as e:
            last_error = e
            wait_time = backoff_factor ** attempt
            log.warning("Open-Meteo fetch failed (attempt %d/%d): %s. Retrying in %.1fs...", attempt, max_retries, e, wait_time)
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to fetch Open-Meteo data after {max_retries} attempts: {last_error}")


def fetch_weather_historical(start_date: str, end_date: str) -> Dict[str, Any]:
    """Fetch historical hourly weather data for NYC."""
    params = {
        "latitude": NYC_LATITUDE,
        "longitude": NYC_LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,snowfall,weather_code,cloud_cover,wind_speed_10m",
        "timezone": NYC_TIMEZONE,
    }
    return fetch_open_meteo_api(OPEN_METEO_ARCHIVE_URL, params)


def fetch_weather_forecast(forecast_days: int = 2) -> Dict[str, Any]:
    """Fetch next 24-48 hours weather forecast for NYC."""
    params = {
        "latitude": NYC_LATITUDE,
        "longitude": NYC_LONGITUDE,
        "forecast_days": forecast_days,
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,snowfall,weather_code,cloud_cover,wind_speed_10m",
        "timezone": NYC_TIMEZONE,
    }
    return fetch_open_meteo_api(OPEN_METEO_FORECAST_URL, params)


def impute_and_clean_weather_records(raw_hourly: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Clean and impute hourly records with forward-fill and calculate metrics."""
    times = raw_hourly.get("time", [])
    if not times:
        return []

    temps = list(raw_hourly.get("temperature_2m", []))
    humidities = list(raw_hourly.get("relative_humidity_2m", []))
    apparent_temps = list(raw_hourly.get("apparent_temperature", []))
    precips = list(raw_hourly.get("precipitation", []))
    snowfalls = list(raw_hourly.get("snowfall", []))
    weather_codes = list(raw_hourly.get("weather_code", []))
    cloud_covers = list(raw_hourly.get("cloud_cover", []))
    wind_speeds = list(raw_hourly.get("wind_speed_10m", []))

    n = len(times)

    def forward_fill_list(series: List[Any], default_val: Any) -> List[Any]:
        filled = []
        last_val = default_val
        for x in series:
            if x is not None:
                last_val = x
            filled.append(last_val)
        return filled

    temps = forward_fill_list(temps, 15.0)
    humidities = forward_fill_list(humidities, 60.0)
    apparent_temps = forward_fill_list(apparent_temps, 15.0)
    precips = forward_fill_list(precips, 0.0)
    snowfalls = forward_fill_list(snowfalls, 0.0)
    weather_codes = forward_fill_list(weather_codes, 0)
    cloud_covers = forward_fill_list(cloud_covers, 20)
    wind_speeds = forward_fill_list(wind_speeds, 10.0)

    # Compute daily min/max for diurnal temp range
    daily_temps: Dict[str, List[float]] = {}
    for i in range(n):
        date_str = times[i].split("T")[0]
        t = float(temps[i])
        daily_temps.setdefault(date_str, []).append(t)

    daily_ranges = {d: (max(vals) - min(vals)) for d, vals in daily_temps.items()}

    cleaned_records: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)

    for i in range(n):
        t_str = times[i]
        date_str = t_str.split("T")[0]
        cur_temp = float(temps[i])
        prev_temp = float(temps[i - 1]) if i > 0 else cur_temp
        temp_delta_1h = round(cur_temp - prev_temp, 2)
        temp_range_day = round(daily_ranges.get(date_str, 0.0), 2)

        w_code = int(weather_codes[i])
        condition = classify_wmo_weather_code(w_code)

        cleaned_records.append(
            {
                "weather_time_str": t_str.replace("T", " ") + ":00",
                "weather_date": date_str,
                "weather_month": date_str[:7],
                "weather_hour": int(t_str.split("T")[1].split(":")[0]),
                "temperature_2m": cur_temp,
                "relative_humidity_2m": float(humidities[i]),
                "apparent_temperature": float(apparent_temps[i]),
                "precipitation": float(precips[i]),
                "snowfall": float(snowfalls[i]),
                "weather_code": w_code,
                "weather_condition": condition,
                "is_clear": 1 if condition == "clear" else 0,
                "is_cloudy": 1 if condition == "cloudy" else 0,
                "is_rain": 1 if condition in ("rain", "drizzle") else 0,
                "is_snow": 1 if condition == "snow" else 0,
                "is_storm": 1 if condition == "storm" else 0,
                "cloud_cover": int(cloud_covers[i]),
                "wind_speed_10m": float(wind_speeds[i]),
                "temp_range_day": temp_range_day,
                "temp_delta_1h": temp_delta_1h,
                "_ingested_at": now_utc,
            }
        )

    return cleaned_records


def run_weather_etl(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_forecast: bool = True,
    **kwargs: Any,
) -> None:
    """Execute complete Weather ETL: Extract Open-Meteo -> Bronze -> Silver Delta."""
    log.info("=== Starting Weather Ingestion & Transformation ===")

    # Auto-detect date range if not explicitly provided
    if not start_date or not end_date:
        start_date = "2025-01-01"
        end_date = "2025-12-31"
        log.info("Defaulting weather historical range to full year 2025 (%s to %s)", start_date, end_date)

    # 1. Extract from Open-Meteo API
    log.info("Fetching historical weather from Open-Meteo: %s to %s...", start_date, end_date)
    hist_payload = fetch_weather_historical(start_date, end_date)
    raw_hourly = hist_payload.get("hourly", {})

    forecast_records: List[Dict[str, Any]] = []
    if include_forecast:
        try:
            log.info("Fetching next 48h forecast from Open-Meteo...")
            fore_payload = fetch_weather_forecast(forecast_days=2)
            forecast_records = impute_and_clean_weather_records(fore_payload.get("hourly", {}))
            log.info("Fetched %d hourly forecast records.", len(forecast_records))
        except Exception as e:
            log.warning("Could not fetch weather forecast (non-blocking): %s", e)

    # 2. Impute & Clean Historical records
    historical_records = impute_and_clean_weather_records(raw_hourly)
    log.info("Processed %d hourly historical weather records.", len(historical_records))

    all_records = historical_records + forecast_records
    if not all_records:
        log.warning("No weather records to process. Aborting.")
        return

    # Deduplicate by weather_time_str
    seen_times = set()
    deduped_records = []
    for r in all_records:
        t_key = r["weather_time_str"]
        if t_key not in seen_times:
            seen_times.add(t_key)
            deduped_records.append(r)

    log.info("Total unique weather hours to write: %d", len(deduped_records))

    # 3. Write Raw Payload to Bronze
    spark = get_spark_session("WeatherETL")
    try:
        bronze_raw_df = spark.createDataFrame(
            [{"source": "open-meteo", "payload": json.dumps(hist_payload), "ingested_at": str(datetime.now(timezone.utc))}]
        )
        bronze_raw_df.write.format("delta").mode("append").save(f"{BRONZE_WEATHER_PATH}_raw")
        log.info("Successfully recorded raw weather payload to %s_raw", BRONZE_WEATHER_PATH)
    except Exception as e:
        log.warning("Could not save raw payload to Bronze Delta (continuing): %s", e)

    # 4. Construct Silver DataFrame with Schema
    schema = StructType(
        [
            StructField("weather_time_str", StringType(), False),
            StructField("weather_date", StringType(), False),
            StructField("weather_month", StringType(), False),
            StructField("weather_hour", IntegerType(), False),
            StructField("temperature_2m", DoubleType(), False),
            StructField("relative_humidity_2m", DoubleType(), False),
            StructField("apparent_temperature", DoubleType(), False),
            StructField("precipitation", DoubleType(), False),
            StructField("snowfall", DoubleType(), False),
            StructField("weather_code", IntegerType(), False),
            StructField("weather_condition", StringType(), False),
            StructField("is_clear", IntegerType(), False),
            StructField("is_cloudy", IntegerType(), False),
            StructField("is_rain", IntegerType(), False),
            StructField("is_snow", IntegerType(), False),
            StructField("is_storm", IntegerType(), False),
            StructField("cloud_cover", IntegerType(), False),
            StructField("wind_speed_10m", DoubleType(), False),
            StructField("temp_range_day", DoubleType(), False),
            StructField("temp_delta_1h", DoubleType(), False),
            StructField("_ingested_at", TimestampType(), False),
        ]
    )

    silver_df = spark.createDataFrame(deduped_records, schema=schema).withColumn(
        "weather_timestamp", F.to_timestamp(F.col("weather_time_str"), "yyyy-MM-dd HH:mm:ss")
    )

    # 5. Save or Merge into Silver Delta Table
    if DeltaTable.isDeltaTable(spark, SILVER_WEATHER_PATH):
        log.info("Merging weather records into existing Delta table at %s...", SILVER_WEATHER_PATH)
        delta_tbl = DeltaTable.forPath(spark, SILVER_WEATHER_PATH)
        (
            delta_tbl.alias("target")
            .merge(
                silver_df.alias("source"),
                "target.weather_timestamp = source.weather_timestamp",
            )
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
    else:
        log.info("Creating new Silver Delta table at %s...", SILVER_WEATHER_PATH)
        (
            silver_df.write.format("delta")
            .mode("overwrite")
            .partitionBy("weather_month")
            .save(SILVER_WEATHER_PATH)
        )

    log.info("✅ Weather Silver transformation successfully completed!")


if __name__ == "__main__":
    run_weather_etl()
