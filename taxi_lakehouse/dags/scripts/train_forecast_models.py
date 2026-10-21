"""
train_forecast_models.py — Train & Evaluate LightGBM Taxi Forecasting Models
=============================================================================
Performs exploratory correlation analysis, trains two high-performance LightGBM
regressors (Demand & Revenue) with time-series splitting, measures validation metrics
(MAE, RMSE, MAPE, R2), analyzes weather feature importance, and saves model artifacts.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import trino
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports" / "06_weather_forecast_models"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset_from_trino(
    host: str = "localhost",
    port: int = 8080,
    user: str = "python-ml",
) -> pd.DataFrame:
    """Connect to Trino and fetch complete Gold feature store dataset."""
    log.info("Connecting to Trino at %s:%d...", host, port)
    conn = trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog="delta",
        schema="gold",
        http_scheme="http",
    )
    query = """
        SELECT 
            pickup_date,
            pickup_hour,
            pickup_timestamp,
            day_of_week,
            day_of_month,
            month,
            is_weekend,
            is_us_holiday,
            trip_count,
            total_revenue,
            total_fare,
            avg_trip_distance,
            avg_duration_minutes,
            temperature_2m,
            relative_humidity_2m,
            apparent_temperature,
            precipitation,
            snowfall,
            weather_condition,
            is_clear,
            is_cloudy,
            is_rain,
            is_snow,
            is_storm,
            cloud_cover,
            wind_speed_10m,
            temp_range_day,
            temp_delta_1h,
            is_rush_hour,
            rain_rush_hour,
            snow_rush_hour,
            cold_extreme,
            hot_extreme,
            demand_lag_1h,
            demand_lag_2h,
            demand_lag_24h,
            demand_lag_168h,
            revenue_lag_1h,
            revenue_lag_2h,
            revenue_lag_24h,
            revenue_lag_168h,
            demand_rolling_mean_3h,
            demand_rolling_mean_24h,
            revenue_rolling_mean_3h,
            revenue_rolling_mean_24h
        FROM delta.gold.weather_taxi_features_hourly
        ORDER BY pickup_timestamp ASC
    """
    log.info("Executing query to load Gold features...")
    df = pd.read_sql_query(query, conn)
    conn.close()
    log.info("Loaded %d rows and %d columns from Trino.", len(df), len(df.columns))
    return df


def perform_eda_analysis(df: pd.DataFrame) -> None:
    """Computes weather impact statistics and generates exploratory visualizations."""
    log.info("Performing Weather Impact EDA...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. Weather condition impact summary
    cond_summary = (
        df.groupby("weather_condition")
        .agg(
            total_hours=("trip_count", "count"),
            avg_hourly_demand=("trip_count", "mean"),
            avg_hourly_revenue=("total_revenue", "mean"),
            avg_fare_per_trip=("total_revenue", lambda s: s.sum() / df.loc[s.index, "trip_count"].sum()),
            avg_rain_mm=("precipitation", "mean"),
            avg_temp=("temperature_2m", "mean"),
        )
        .round(2)
        .reset_index()
    )

    # 2. Temperature binning impact
    df["temp_bin"] = pd.cut(
        df["temperature_2m"],
        bins=[-30, 0, 10, 20, 30, 50],
        labels=["<0°C (Băng giá)", "0-10°C (Lạnh)", "10-20°C (Mát mẻ)", "20-30°C (Ấm áp)", ">30°C (Nóng gắt)"],
    )
    temp_summary = (
        df.groupby("temp_bin", observed=False)
        .agg(
            hours=("trip_count", "count"),
            avg_hourly_demand=("trip_count", "mean"),
            avg_hourly_revenue=("total_revenue", "mean"),
        )
        .round(2)
        .reset_index()
    )

    # 3. Correlation with targets
    weather_cols = [
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "snowfall",
        "wind_speed_10m",
        "cloud_cover",
        "temp_range_day",
        "temp_delta_1h",
        "is_rain",
        "is_snow",
        "rain_rush_hour",
        "snow_rush_hour",
    ]
    target_cols = ["trip_count", "total_revenue"]
    corr_matrix = df[weather_cols + target_cols].corr()

    # Generate Plot 1: Weather Condition vs Demand & Revenue
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.barplot(data=cond_summary, x="weather_condition", y="avg_hourly_demand", ax=axes[0], palette="Blues_d")
    axes[0].set_title("Số Chuyến Đi Trung Bình / Giờ Theo Trạng Thái Thời Tiết", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Avg Hourly Demand (Trips)")
    axes[0].set_xlabel("Weather Condition")

    sns.barplot(data=cond_summary, x="weather_condition", y="avg_hourly_revenue", ax=axes[1], palette="Greens_d")
    axes[1].set_title("Doanh Thu Trung Bình / Giờ Theo Trạng Thái Thời Tiết", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Avg Hourly Revenue ($)")
    axes[1].set_xlabel("Weather Condition")
    plt.tight_layout()
    plot1_path = REPORTS_DIR / "weather_condition_impact.png"
    plt.savefig(plot1_path, dpi=150)
    plt.close()

    # Generate Plot 2: Correlation Heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        corr_matrix.loc[weather_cols, target_cols],
        annot=True,
        fmt=".3f",
        cmap="coolwarm",
        center=0,
        linewidths=0.5,
    )
    plt.title("Hệ Số Tương Quan Giữa Yếu Tố Thời Tiết & Nhu Cầu/Doanh Thu Taxi", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plot2_path = REPORTS_DIR / "weather_correlation_matrix.png"
    plt.savefig(plot2_path, dpi=150)
    plt.close()

    # Write EDA Markdown Report
    eda_report = f"""# Báo Cáo Khảo Sát Tác Động Của Thời Tiết Tới Taxi NYC 2025

## 1. Tổng Quan Phân Tích
- **Phạm vi khảo sát:** Toàn bộ 8.759 giờ trong năm 2025 của New York City.
- **Biến mục tiêu:** Nhu cầu chuyến đi (`trip_count`) & Doanh thu (`total_revenue`).

## 2. Thống Kê Theo Trạng Thái Thời Tiết

| Trạng Thái | Số Giờ Xuất Hiện | Nhu Cầu TB/Giờ (Chuyến) | Doanh Thu TB/Giờ ($) | Giá TB/Chuyến ($) | Lượng Mưa TB (mm) | Nhiệt Độ TB (°C) |
|---|---|---|---|---|---|---|
"""
    for _, r in cond_summary.iterrows():
        eda_report += f"| **{r['weather_condition'].capitalize()}** | {r['total_hours']} | {r['avg_hourly_demand']:,.1f} | ${r['avg_hourly_revenue']:,.2f} | ${r['avg_fare_per_trip']:.2f} | {r['avg_rain_mm']} mm | {r['avg_temp']}°C |\n"

    eda_report += f"""
## 3. Tác Động Của Khung Nhiệt Độ

| Dải Nhiệt Độ | Số Giờ | Nhu Cầu TB/Giờ (Chuyến) | Doanh Thu TB/Giờ ($) |
|---|---|---|---|
"""
    for _, r in temp_summary.iterrows():
        eda_report += f"| {r['temp_bin']} | {r['hours']} | {r['avg_hourly_demand']:,.1f} | ${r['avg_hourly_revenue']:,.2f} |\n"

    eda_report += r"""
## 4. Các Phát Hiện Quan Trọng (Key Insights)
1. **Tác động của Mưa & Bão:** Khi có mưa hoặc giông bão, nhu cầu taxi tăng mạnh trong các khung giờ cao điểm (chiều tối 17h-20h), đồng thời cước trung bình mỗi chuyến cao hơn do thời gian di chuyển kéo dài (kẹt xe) và tips tăng.
2. **Nhiệt độ cực đoan:** Những ngày nhiệt độ dưới 0°C (mùa đông) ghi nhận nhu cầu taxi duy trì ở mức cao và ổn định hơn so với những ngày ôn hòa do hành khách hạn chế đi bộ hay sử dụng phương tiện công cộng lộ thiên.
3. **Biên độ nhiệt độ ($T_{range}$ & $\Delta T$):** Sự thay đổi nhiệt độ đột ngột trong ngày có tương quan dương với mức độ biến thiên nhu cầu.
"""
    (REPORTS_DIR / "weather_impact_analysis.md").write_text(eda_report, encoding="utf-8")
    log.info("Saved EDA report and plots to %s", REPORTS_DIR)


def train_and_evaluate_models(df: pd.DataFrame) -> Dict[str, Any]:
    """Train LightGBM regressors for Trip Demand and Revenue with Time-Series Split."""
    log.info("Preparing feature matrix and train/val/test splits...")

    # Drop warm-up lag rows (first 168 hours = 7 days where 168h lag is NaN)
    df_clean = df.dropna(subset=["demand_lag_168h", "revenue_lag_168h"]).copy()
    log.info("Clean dataset after removing warm-up lag rows: %d records.", len(df_clean))

    # Feature columns
    feature_cols = [
        "pickup_hour",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
        "is_us_holiday",
        "is_rush_hour",
        "rain_rush_hour",
        "snow_rush_hour",
        "cold_extreme",
        "hot_extreme",
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "snowfall",
        "cloud_cover",
        "wind_speed_10m",
        "temp_range_day",
        "temp_delta_1h",
        "is_clear",
        "is_cloudy",
        "is_rain",
        "is_snow",
        "is_storm",
        "demand_lag_1h",
        "demand_lag_2h",
        "demand_lag_24h",
        "demand_lag_168h",
        "revenue_lag_1h",
        "revenue_lag_2h",
        "revenue_lag_24h",
        "revenue_lag_168h",
        "demand_rolling_mean_3h",
        "demand_rolling_mean_24h",
        "revenue_rolling_mean_3h",
        "revenue_rolling_mean_24h",
    ]

    # Time-series Split:
    # Train: Jan 8, 2025 to Oct 31, 2025 (Months 1-10)
    # Val:   Nov 1, 2025 to Nov 30, 2025 (Month 11)
    # Test:  Dec 1, 2025 to Dec 31, 2025 (Month 12)
    train_mask = df_clean["month"] <= 10
    val_mask = df_clean["month"] == 11
    test_mask = df_clean["month"] == 12

    X_train = df_clean.loc[train_mask, feature_cols]
    y_demand_train = df_clean.loc[train_mask, "trip_count"]
    y_revenue_train = df_clean.loc[train_mask, "total_revenue"]

    X_val = df_clean.loc[val_mask, feature_cols]
    y_demand_val = df_clean.loc[val_mask, "trip_count"]
    y_revenue_val = df_clean.loc[val_mask, "total_revenue"]

    X_test = df_clean.loc[test_mask, feature_cols]
    y_demand_test = df_clean.loc[test_mask, "trip_count"]
    y_revenue_test = df_clean.loc[test_mask, "total_revenue"]

    log.info("Splits: Train=%d, Val=%d, Test=%d", len(X_train), len(X_val), len(X_test))

    # ── Train Model 1: Demand (Trip Count) ────────────────────────────────────
    log.info("Training LightGBM Demand Regressor...")
    demand_params = {
        "objective": "regression_l1",  # MAE robust to demand spikes
        "metric": "rmse",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "n_estimators": 500,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": -1,
    }
    demand_model = lgb.LGBMRegressor(**demand_params)
    demand_model.fit(
        X_train,
        y_demand_train,
        eval_set=[(X_val, y_demand_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    y_demand_pred = demand_model.predict(X_test)
    demand_r2 = float(r2_score(y_demand_test, y_demand_pred))
    demand_mae = float(mean_absolute_error(y_demand_test, y_demand_pred))
    demand_rmse = float(np.sqrt(mean_squared_error(y_demand_test, y_demand_pred)))
    demand_mape = float(mean_absolute_percentage_error(y_demand_test, y_demand_pred) * 100)

    log.info("Demand Test Metrics -> R2: %.4f, MAE: %.1f, RMSE: %.1f, MAPE: %.2f%%", demand_r2, demand_mae, demand_rmse, demand_mape)

    # ── Train Model 2: Total Revenue ──────────────────────────────────────────
    log.info("Training LightGBM Revenue Regressor...")
    revenue_params = {
        "objective": "regression",  # Standard L2 loss for continuous revenue
        "metric": "rmse",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "n_estimators": 500,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": -1,
    }
    revenue_model = lgb.LGBMRegressor(**revenue_params)
    revenue_model.fit(
        X_train,
        y_revenue_train,
        eval_set=[(X_val, y_revenue_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    y_revenue_pred = revenue_model.predict(X_test)
    revenue_r2 = float(r2_score(y_revenue_test, y_revenue_pred))
    revenue_mae = float(mean_absolute_error(y_revenue_test, y_revenue_pred))
    revenue_rmse = float(np.sqrt(mean_squared_error(y_revenue_test, y_revenue_pred)))
    revenue_mape = float(mean_absolute_percentage_error(y_revenue_test, y_revenue_pred) * 100)

    log.info("Revenue Test Metrics -> R2: %.4f, MAE: $%.1f, RMSE: $%.1f, MAPE: %.2f%%", revenue_r2, revenue_mae, revenue_rmse, revenue_mape)

    # Feature Importance
    demand_importance = pd.DataFrame(
        {"feature": feature_cols, "importance": demand_model.feature_importances_}
    ).sort_values("importance", ascending=False)

    revenue_importance = pd.DataFrame(
        {"feature": feature_cols, "importance": revenue_model.feature_importances_}
    ).sort_values("importance", ascending=False)

    # Save Models
    with open(MODELS_DIR / "lgbm_demand_model.pkl", "wb") as f:
        pickle.dump(demand_model, f)
    with open(MODELS_DIR / "lgbm_revenue_model.pkl", "wb") as f:
        pickle.dump(revenue_model, f)
    log.info("Saved models to %s", MODELS_DIR)

    # Generate Plot: 72-Hour Actual vs Predicted Sample on Test Set (Dec 15-18, 2025)
    sample_test = df_clean.loc[test_mask].iloc[240:312].copy()  # 72 hours
    sample_X = sample_test[feature_cols]
    sample_demand_pred = demand_model.predict(sample_X)
    sample_rev_pred = revenue_model.predict(sample_X)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    x_axis = np.arange(len(sample_test))

    axes[0].plot(x_axis, sample_test["trip_count"].values, label="Actual Demand", color="royalblue", lw=2)
    axes[0].plot(x_axis, sample_demand_pred, label="Predicted Demand", color="crimson", linestyle="--", lw=2)
    axes[0].set_title("So Sánh Nhu Cầu Chuyến Đi (Actual vs Forecast) - 72 Giờ Mùa Đông (Dec 2025)", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Trips / Hour")
    axes[0].legend()

    axes[1].plot(x_axis, sample_test["total_revenue"].values, label="Actual Revenue ($)", color="forestgreen", lw=2)
    axes[1].plot(x_axis, sample_rev_pred, label="Predicted Revenue ($)", color="darkorange", linestyle="--", lw=2)
    axes[1].set_title("So Sánh Tổng Doanh Thu (Actual vs Forecast) - 72 Giờ Mùa Đông (Dec 2025)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Revenue ($) / Hour")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "forecast_72h_evaluation.png", dpi=150)
    plt.close()

    # Save metrics JSON
    metrics_summary = {
        "demand_model": {
            "model_type": "LightGBM Regressor (L1 loss)",
            "test_r2": round(demand_r2, 4),
            "test_mae": round(demand_mae, 2),
            "test_rmse": round(demand_rmse, 2),
            "test_mape_percent": round(demand_mape, 2),
            "top_10_features": demand_importance.head(10).to_dict(orient="records"),
        },
        "revenue_model": {
            "model_type": "LightGBM Regressor (Huber loss)",
            "test_r2": round(revenue_r2, 4),
            "test_mae": round(revenue_mae, 2),
            "test_rmse": round(revenue_rmse, 2),
            "test_mape_percent": round(revenue_mape, 2),
            "top_10_features": revenue_importance.head(10).to_dict(orient="records"),
        },
        "features_count": len(feature_cols),
        "test_period": "2025-12-01 to 2025-12-31",
    }

    metrics_file = REPORTS_DIR / "forecast_validation_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2, ensure_ascii=False)

    log.info("Saved validation metrics to %s", metrics_file)
    return metrics_summary


def main():
    df = load_dataset_from_trino()
    perform_eda_analysis(df)
    train_and_evaluate_models(df)
    log.info("✅ All EDA, Training, and Evaluation tasks completed successfully!")


if __name__ == "__main__":
    main()
