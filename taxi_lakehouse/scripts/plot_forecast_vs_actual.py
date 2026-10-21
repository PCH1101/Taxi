"""
plot_forecast_vs_actual.py — Trino BI Visualization for 24-Hour Forecast
========================================================================
Connects to Trino, queries `delta.gold.forecast_hourly_metrics`,
and generates an executive visualization dashboard showing predicted demand,
predicted revenue, average fare, and underlying weather conditions.
"""

from __future__ import annotations

import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trino

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports" / "06_weather_forecast_models"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def plot_forecast_dashboard(host: str = "localhost", port: int = 8080) -> Path:
    """Query Trino and generate 24-Hour Forecast Dashboard."""
    log.info("Connecting to Trino at %s:%d to fetch forecasts...", host, port)
    conn = trino.dbapi.connect(
        host=host,
        port=port,
        user="forecast-dashboard",
        catalog="delta",
        schema="gold",
        http_scheme="http",
    )
    query = """
        SELECT 
            forecast_time_str,
            forecast_hour,
            predicted_trip_count,
            predicted_total_revenue,
            predicted_avg_fare,
            temperature_2m,
            apparent_temperature,
            precipitation,
            weather_condition,
            wind_speed_10m,
            is_rush_hour
        FROM delta.gold.forecast_hourly_metrics
        ORDER BY forecast_timestamp ASC
        LIMIT 24
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise ValueError("No forecast records found in delta.gold.forecast_hourly_metrics.")

    log.info("Fetched %d forecast hours.", len(df))
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True)
    x = np.arange(len(df))
    x_labels = [f"{r['forecast_hour']:02d}:00\n({r['weather_condition']})" for _, r in df.iterrows()]

    # ── Panel 1: Demand ───────────────────────────────────────────────────────
    axes[0].bar(x, df["predicted_trip_count"], color="steelblue", alpha=0.85, width=0.6, label="Predicted Trips (Demand)")
    axes[0].set_ylabel("Trips / Hour", fontsize=11, fontweight="bold")
    axes[0].set_title("Dự Báo Nhu Cầu Chuyến Đi (NYC Taxi Trip Demand) Cho 24 Giờ Tiếp Theo", fontsize=13, fontweight="bold", pad=10)
    for i, v in enumerate(df["predicted_trip_count"]):
        if v > 0:
            axes[0].text(i, v + 40, f"{v:,}", ha="center", fontsize=8, rotation=0, fontweight="bold")
    axes[0].legend(loc="upper left")

    # ── Panel 2: Revenue & Avg Fare ───────────────────────────────────────────
    color_rev = "forestgreen"
    color_fare = "darkorange"
    axes[1].plot(x, df["predicted_total_revenue"], color=color_rev, marker="o", lw=2.5, label="Total Revenue ($)")
    axes[1].set_ylabel("Total Revenue ($)", fontsize=11, fontweight="bold", color=color_rev)
    axes[1].tick_params(axis="y", labelcolor=color_rev)

    ax2_fare = axes[1].twinx()
    ax2_fare.plot(x, df["predicted_avg_fare"], color=color_fare, linestyle="--", marker="s", lw=2, label="Avg Fare ($/trip)")
    ax2_fare.set_ylabel("Avg Fare ($ / trip)", fontsize=11, fontweight="bold", color=color_fare)
    ax2_fare.tick_params(axis="y", labelcolor=color_fare)
    axes[1].set_title("Dự Báo Tổng Doanh Thu ($) & Cước Phí Bình Quân ($/Chuyến)", fontsize=13, fontweight="bold", pad=10)

    # ── Panel 3: Weather Variables (Temperature & Precipitation) ──────────────
    axes[2].plot(x, df["temperature_2m"], color="crimson", marker="^", lw=2, label="Nhiệt Độ 2m (°C)")
    axes[2].plot(x, df["apparent_temperature"], color="salmon", linestyle=":", lw=1.8, label="Cảm Giác Nhiệt (°C)")
    axes[2].set_ylabel("Nhiệt Độ (°C)", fontsize=11, fontweight="bold", color="crimson")
    axes[2].tick_params(axis="y", labelcolor="crimson")

    ax3_precip = axes[2].twinx()
    ax3_precip.bar(x, df["precipitation"], color="dodgerblue", alpha=0.4, width=0.4, label="Lượng Mưa (mm)")
    ax3_precip.set_ylabel("Lượng Mưa (mm)", fontsize=11, fontweight="bold", color="dodgerblue")
    ax3_precip.tick_params(axis="y", labelcolor="dodgerblue")
    axes[2].set_title("Diễn Biến Thời Tiết Dự Báo (Nhiệt Độ & Lượng Mưa)", fontsize=13, fontweight="bold", pad=10)

    axes[2].set_xticks(x)
    axes[2].set_xticklabels(x_labels, fontsize=9)
    axes[2].set_xlabel("Khung Giờ & Trạng Thái Thời Tiết", fontsize=11, fontweight="bold", labelpad=10)

    # Combined legends
    lines_rev, labels_rev = axes[1].get_legend_handles_labels()
    lines_fare, labels_fare = ax2_fare.get_legend_handles_labels()
    axes[1].legend(lines_rev + lines_fare, labels_rev + labels_fare, loc="upper left")

    lines_temp, labels_temp = axes[2].get_legend_handles_labels()
    lines_p, labels_p = ax3_precip.get_legend_handles_labels()
    axes[2].legend(lines_temp + lines_p, labels_temp + labels_p, loc="upper left")

    plt.tight_layout()
    output_path = REPORTS_DIR / "forecast_24h_dashboard.png"
    plt.savefig(output_path, dpi=160)
    plt.close()

    log.info("Saved forecast dashboard to %s", output_path)
    return output_path


if __name__ == "__main__":
    plot_forecast_dashboard()
