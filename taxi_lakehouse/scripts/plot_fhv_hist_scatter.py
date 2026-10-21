#!/usr/bin/env python3
"""
plot_fhv_hist_scatter.py — FHVHV Histogram & Scatter Visualizations & Report Generator
========================================================================================

Generates statistical distribution (Histograms) and bivariate relationship (Scatter Plots)
for High-Volume For-Hire Vehicles (FHVHV - Uber & Lyft) using Trino SQL, and writes the output
into the structured FHV_report directory matching the YLC_report hierarchy:

  FHV_report/
  ├── 01_overview_and_eda/
  │   ├── silver_visual_dashboard.png
  │   └── README.md
  ├── 02_distributions_histograms/
  │   ├── 01_hist_trip_duration.png
  │   ├── 02_hist_trip_distance.png
  │   ├── 03_hist_tip_percentage.png
  │   ├── 04_hist_fare_amount.png
  │   ├── 05_hist_average_speed.png
  │   ├── 06_bimodal_rush_hours.png
  │   └── README.md
  ├── 03_relationships_scatter/
  │   ├── 01_scatter_distance_vs_fare.png
  │   ├── 02_scatter_distance_vs_duration.png
  │   ├── 03_scatter_fare_vs_tip.png
  │   ├── 04_scatter_hour_vs_speed.png
  │   └── README.md
  └── README.md

Usage:
  python scripts/plot_fhv_hist_scatter.py
  python scripts/plot_fhv_hist_scatter.py --month 2025-01 --sample-size 60000
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("plot_fhv_report")


def get_trino_connection(host: str, port: int, user: str, catalog: str = "delta", schema: str = "silver"):
    """Establish connection to Trino."""
    try:
        import trino
    except ImportError:
        log.error("Package 'trino' is not installed. Please install: pip install trino pandas matplotlib seaborn")
        sys.exit(1)

    return trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog=catalog,
        schema=schema,
        http_scheme="http",
        session_properties={
            "delta.parquet_ignore_statistics": True,
            "delta.statistics_enabled": False,
        },
    )


def fetch_dataframe(conn, sql: str):
    """Execute SQL and return a Pandas DataFrame."""
    import pandas as pd
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        cursor.close()


def setup_plot_style():
    """Configures professional matplotlib & seaborn theme."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", font_scale=1.05)
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Helvetica", "Arial"]
    plt.rcParams["axes.edgecolor"] = "#cccccc"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["grid.color"] = "#e5e5e5"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.alpha"] = 0.7


# ── Step 1: Generate Master Dashboard ──────────────────────────────────────────

def plot_overview_dashboard(df, output_dir: Path):
    """Creates a consolidated 6-in-1 analytical overview dashboard for FHVHV."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Overview Master Dashboard (01_overview_and_eda)...")
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("NYC High-Volume FHV (Uber & Lyft) — Exploratory Data Analysis Dashboard", fontsize=16, fontweight="bold", y=0.98)

    # Subplot 1: Trip Duration Hist
    dur = df["trip_duration_min"][(df["trip_duration_min"] > 0) & (df["trip_duration_min"] <= 60)]
    sns.histplot(dur, bins=40, kde=True, color="#1f77b4", ax=axes[0, 0])
    axes[0, 0].axvline(dur.median(), color="#d62728", linestyle="--", label=f"Median: {dur.median():.1f}m")
    axes[0, 0].set_title("1. Trip Duration Distribution (mins)", fontweight="bold")
    axes[0, 0].set_xlabel("Minutes")
    axes[0, 0].legend(fontsize=9)

    # Subplot 2: Distance Hist
    dist = df["trip_distance"][(df["trip_distance"] > 0) & (df["trip_distance"] <= 25)]
    sns.histplot(dist, bins=40, kde=True, color="#2ca02c", ax=axes[0, 1])
    axes[0, 1].axvline(dist.median(), color="#d62728", linestyle="--", label=f"Median: {dist.median():.1f} mi")
    axes[0, 1].set_title("2. Trip Distance Distribution (miles)", fontweight="bold")
    axes[0, 1].set_xlabel("Miles")
    axes[0, 1].legend(fontsize=9)

    # Subplot 3: Tip % Hist (Rides with tips)
    tip_sub = df[(df["tip_pct"] > 0) & (df["tip_pct"] <= 40)]["tip_pct"]
    sns.histplot(tip_sub, bins=40, color="#9467bd", ax=axes[0, 2])
    axes[0, 2].axvline(tip_sub.median(), color="#d62728", linestyle="--", label=f"Median: {tip_sub.median():.1f}%")
    axes[0, 2].set_title("3. Tip % Distribution (Tipped Rides)", fontweight="bold")
    axes[0, 2].set_xlabel("Tip %")
    axes[0, 2].legend(fontsize=9)

    # Subplot 4: Distance vs Base Fare Scatter
    sample_df = df[(df["trip_distance"] > 0) & (df["trip_distance"] <= 25) & (df["fare_amount"] > 0) & (df["fare_amount"] <= 120)]
    palette = {"Uber": "#000000", "Lyft": "#ff00bf", "Other FHV": "#1f77b4"}
    sns.scatterplot(
        data=sample_df,
        x="trip_distance",
        y="fare_amount",
        hue="service_provider",
        palette=palette,
        alpha=0.25,
        s=12,
        ax=axes[1, 0],
    )
    axes[1, 0].set_title("4. Trip Distance vs. Base Fare ($)", fontweight="bold")
    axes[1, 0].set_xlabel("Distance (miles)")
    axes[1, 0].set_ylabel("Base Fare ($)")
    axes[1, 0].legend(fontsize=9)

    # Subplot 5: Fare vs Tip Scatter
    sample_tip = df[(df["fare_amount"] > 0) & (df["fare_amount"] <= 80) & (df["tip_amount"] > 0) & (df["tip_amount"] <= 25)]
    sns.scatterplot(data=sample_tip, x="fare_amount", y="tip_amount", alpha=0.3, s=12, color="#2b5c8f", ax=axes[1, 1])
    f_arr = np.linspace(0, 80, 50)
    axes[1, 1].plot(f_arr, f_arr * 0.15, color="#ff7f0e", linestyle=":", label="15% Tip")
    axes[1, 1].plot(f_arr, f_arr * 0.20, color="#d62728", linestyle="--", label="20% Tip")
    axes[1, 1].set_title("5. Base Fare vs. Tip Amount ($)", fontweight="bold")
    axes[1, 1].set_xlabel("Base Fare ($)")
    axes[1, 1].set_ylabel("Tip ($)")
    axes[1, 1].legend(fontsize=9)

    # Subplot 6: Hourly Speed Trend
    sample_spd = df[(df["avg_speed_mph"] > 0) & (df["avg_speed_mph"] <= 55)].copy()
    sample_spd["pickup_hour"] = sample_spd["pickup_hour"].astype(int)
    hourly_spd = sample_spd.groupby("pickup_hour")["avg_speed_mph"].mean().reset_index()
    axes[1, 2].plot(hourly_spd["pickup_hour"], hourly_spd["avg_speed_mph"], marker="o", color="#d62728", linewidth=2)
    axes[1, 2].set_title("6. Average Speed by Hour of Day (mph)", fontweight="bold")
    axes[1, 2].set_xlabel("Hour of Day (0-23)")
    axes[1, 2].set_ylabel("Speed (mph)")
    axes[1, 2].set_xticks(range(0, 24, 2))

    plt.tight_layout()
    chart_path = output_dir / "silver_visual_dashboard.png"
    plt.savefig(chart_path, dpi=200)
    plt.close()
    log.info("Saved overview dashboard: %s", chart_path)


# ── Step 2: Generate Histograms ────────────────────────────────────────────────

def plot_histograms(df, hourly_df, output_dir: Path):
    """Plots individual distribution histograms in 02_distributions_histograms."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Individual Histograms (02_distributions_histograms)...")

    # 1. Trip Duration Histogram
    plt.figure(figsize=(10, 5))
    durations = df["trip_duration_min"][(df["trip_duration_min"] > 0) & (df["trip_duration_min"] <= 60)]
    median_dur = durations.median()
    mean_dur = durations.mean()

    sns.histplot(durations, bins=60, kde=True, color="#1f77b4", edgecolor="white", alpha=0.75)
    plt.axvline(median_dur, color="#d62728", linestyle="--", linewidth=2, label=f"Median: {median_dur:.1f} min")
    plt.axvline(mean_dur, color="#2ca02c", linestyle=":", linewidth=2, label=f"Mean: {mean_dur:.1f} min")
    plt.title("Distribution of NYC FHVHV Trip Duration (0 - 60 mins)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Trip Duration (minutes)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "01_hist_trip_duration.png", dpi=200)
    plt.close()

    # 2. Trip Distance Histogram
    plt.figure(figsize=(10, 5))
    distances = df["trip_distance"][(df["trip_distance"] > 0) & (df["trip_distance"] <= 25)]
    p90_dist = np.percentile(distances, 90)

    sns.histplot(distances, bins=50, kde=True, color="#2ca02c", edgecolor="white", alpha=0.75)
    plt.axvline(distances.median(), color="#d62728", linestyle="--", linewidth=2, label=f"Median: {distances.median():.2f} miles")
    plt.axvline(p90_dist, color="#ff7f0e", linestyle=":", linewidth=2, label=f"90th Percentile: {p90_dist:.2f} miles")
    plt.title("Distribution of NYC FHVHV Trip Distance (0 - 25 miles)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Trip Distance (miles)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "02_hist_trip_distance.png", dpi=200)
    plt.close()

    # 3. Tip Percentage Histogram
    plt.figure(figsize=(10, 5))
    tipped = df[(df["tip_pct"] > 0) & (df["tip_pct"] <= 50)]["tip_pct"]
    sns.histplot(tipped, bins=50, kde=False, color="#9467bd", edgecolor="white", alpha=0.8)
    for pct, label in [(10, "10%"), (15, "15%"), (18, "18%"), (20, "20% (Default)"), (25, "25%")]:
        plt.axvline(pct, color="#d62728", linestyle="--", alpha=0.7, linewidth=1.5)
        plt.text(pct + 0.3, plt.ylim()[1] * 0.85, label, rotation=90, color="#d62728", fontsize=9, fontweight="bold")
    plt.title("Distribution of Tip % on Tipped FHVHV Rides (App Preset Spikes)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Tip Percentage (% of Base Fare)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "03_hist_tip_percentage.png", dpi=200)
    plt.close()

    # 4. Fare Amount Histogram
    plt.figure(figsize=(10, 5))
    fares = df["fare_amount"][(df["fare_amount"] > 0) & (df["fare_amount"] <= 100)]
    sns.histplot(fares, bins=50, kde=True, color="#ff7f0e", edgecolor="white", alpha=0.75)
    plt.axvline(fares.median(), color="#1f77b4", linestyle="--", linewidth=2, label=f"Median Fare: ${fares.median():.2f}")
    plt.axvline(fares.mean(), color="#d62728", linestyle=":", linewidth=2, label=f"Mean Fare: ${fares.mean():.2f}")
    plt.title("Distribution of Base Passenger Fare ($0 - $100)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Base Fare Amount ($)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "04_hist_fare_amount.png", dpi=200)
    plt.close()

    # 5. Average Speed Histogram
    plt.figure(figsize=(10, 5))
    speeds = df["avg_speed_mph"][(df["avg_speed_mph"] > 0) & (df["avg_speed_mph"] <= 60)]
    sns.histplot(speeds, bins=60, kde=True, color="#17becf", edgecolor="white", alpha=0.75)
    plt.axvline(speeds.median(), color="#d62728", linestyle="--", linewidth=2, label=f"Median Speed: {speeds.median():.1f} mph")
    plt.axvline(speeds.mean(), color="#ff7f0e", linestyle=":", linewidth=2, label=f"Mean Speed: {speeds.mean():.1f} mph")
    plt.title("Distribution of Average Vehicle Speed (0 - 60 mph)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Average Speed (mph)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "05_hist_average_speed.png", dpi=200)
    plt.close()

    # 6. Bimodal Rush Hours (Bar + Line Dual Axis)
    fig, ax1 = plt.subplots(figsize=(12, 6))
    hours = hourly_df["pickup_hour"].astype(int).values
    trips_millions = hourly_df["trip_count"].values / 1_000_000.0

    ax1.bar(
        hours,
        trips_millions,
        width=0.65,
        color="#2b5c8f",
        alpha=0.85,
        edgecolor="#1c3d5a",
        linewidth=1.2,
        label="Trip Volume (Millions)",
    )
    # Smooth line
    try:
        from scipy.interpolate import make_interp_spline
        x_smooth = np.linspace(hours.min(), hours.max(), 300)
        spline = make_interp_spline(hours, trips_millions, k=3)
        y_smooth = spline(x_smooth)
        ax1.plot(x_smooth, y_smooth, color="#0f2b48", linewidth=2.5, linestyle="-", label="Demand Density Curve")
    except Exception:
        ax1.plot(hours, trips_millions, color="#0f2b48", linewidth=2.5, marker="o", label="Demand Density Curve")

    # Secondary Axis for Avg Fare
    ax2 = ax1.twinx()
    ax2.plot(
        hours,
        hourly_df["avg_fare"],
        color="#d95f02",
        marker="s",
        markersize=6,
        linewidth=2.2,
        linestyle="--",
        label="Avg Base Fare ($)",
    )
    ax2.set_ylabel("Average Base Fare ($)", color="#d95f02", fontsize=12, fontweight="bold", labelpad=10)
    ax2.tick_params(axis="y", labelcolor="#d95f02")
    ax2.grid(False)

    # Shaded rush hour bands
    ax1.axvspan(7.5, 9.5, color="#ff7f0e", alpha=0.12, label="Morning Rush Band")
    ax1.axvspan(16.5, 19.5, color="#d62728", alpha=0.12, label="Evening Rush Band")

    ax1.set_title("NYC FHVHV 24-Hour Temporal Demand & Fare Dynamics (Bimodal Rush Hours)", fontsize=14, fontweight="bold", pad=15)
    ax1.set_xlabel("Hour of Day (0 - 23)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Trip Volume (Millions)", fontsize=12, fontweight="bold")
    ax1.set_xticks(range(0, 24))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True, facecolor="white", edgecolor="#ddd")

    plt.tight_layout()
    plt.savefig(output_dir / "06_bimodal_rush_hours.png", dpi=200)
    plt.close()


# ── Step 3: Generate Scatter Plots ─────────────────────────────────────────────

def plot_scatters(df, output_dir: Path):
    """Plots bivariate scatter relationships in 03_relationships_scatter."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Scatter Plots (03_relationships_scatter)...")

    # 1. Distance vs Base Fare Amount
    plt.figure(figsize=(10, 6))
    sample = df[(df["trip_distance"] > 0) & (df["trip_distance"] <= 30) & (df["fare_amount"] > 0) & (df["fare_amount"] <= 120)]
    palette = {"Uber": "#000000", "Lyft": "#ff00bf", "Other FHV": "#1f77b4"}

    sns.scatterplot(
        data=sample,
        x="trip_distance",
        y="fare_amount",
        hue="service_provider",
        palette=palette,
        alpha=0.3,
        s=16,
        edgecolor=None,
    )
    # Reference trend
    x_vals = np.linspace(0, 30, 100)
    plt.plot(x_vals, 8.0 + 2.5 * x_vals, color="#2ca02c", linestyle="-", linewidth=2, label="Algorithmic Fare Estimate (~$8 + $2.5/mi)")

    plt.title("Trip Distance vs. Base Fare (Uber vs. Lyft Dynamic Pricing Distribution)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Trip Distance (miles)", fontsize=11, fontweight="bold")
    plt.ylabel("Base Fare Amount ($)", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd", title="Platform Provider")
    plt.tight_layout()
    plt.savefig(output_dir / "01_scatter_distance_vs_fare.png", dpi=200)
    plt.close()

    # 2. Distance vs Duration
    plt.figure(figsize=(10, 6))
    sample_dur = df[(df["trip_distance"] > 0) & (df["trip_distance"] <= 30) & (df["trip_duration_min"] > 0) & (df["trip_duration_min"] <= 90)]

    sns.scatterplot(
        data=sample_dur,
        x="trip_distance",
        y="trip_duration_min",
        hue="avg_speed_mph",
        palette="viridis",
        alpha=0.35,
        s=16,
        edgecolor=None,
    )
    plt.title("Trip Distance vs. Duration (Color-coded by Average Speed in mph)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Trip Distance (miles)", fontsize=11, fontweight="bold")
    plt.ylabel("Trip Duration (minutes)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "02_scatter_distance_vs_duration.png", dpi=200)
    plt.close()

    # 3. Base Fare vs Tip Amount
    plt.figure(figsize=(10, 6))
    sample_tips = df[(df["fare_amount"] > 0) & (df["fare_amount"] <= 80) & (df["tip_amount"] > 0) & (df["tip_amount"] <= 35)]

    sns.scatterplot(
        data=sample_tips,
        x="fare_amount",
        y="tip_amount",
        color="#2b5c8f",
        alpha=0.35,
        s=16,
        edgecolor=None,
    )
    fare_range = np.linspace(0, 80, 100)
    plt.plot(fare_range, fare_range * 0.15, color="#ff7f0e", linestyle=":", linewidth=1.8, label="15% Tip Line")
    plt.plot(fare_range, fare_range * 0.20, color="#d62728", linestyle="--", linewidth=1.8, label="20% Tip Line")
    plt.plot(fare_range, fare_range * 0.25, color="#9467bd", linestyle="-.", linewidth=1.8, label="25% Tip Line")

    plt.title("Base Fare vs. Tip Amount (In-App Digital Tipping & % Rays)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Base Fare Amount ($)", fontsize=11, fontweight="bold")
    plt.ylabel("Tip Amount ($)", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "03_scatter_fare_vs_tip.png", dpi=200)
    plt.close()

    # 4. Hour of Day vs Speed
    plt.figure(figsize=(11, 5.5))
    sample_spd = df[(df["avg_speed_mph"] > 0) & (df["avg_speed_mph"] <= 55)].copy()
    sample_spd["pickup_hour"] = sample_spd["pickup_hour"].astype(int)

    sns.stripplot(data=sample_spd, x="pickup_hour", y="avg_speed_mph", size=3, alpha=0.15, jitter=0.25, color="#17becf")
    hourly_mean = sample_spd.groupby("pickup_hour")["avg_speed_mph"].mean().reset_index()
    plt.plot(hourly_mean["pickup_hour"], hourly_mean["avg_speed_mph"], color="#d62728", marker="o", linewidth=2.5, label="Mean Speed by Hour")

    plt.title("Vehicle Speed across 24 Hours (Rush Hour Congestion Slowdowns)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Hour of Day (0 - 23)", fontsize=11, fontweight="bold")
    plt.ylabel("Average Speed (mph)", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "04_scatter_hour_vs_speed.png", dpi=200)
    plt.close()


# ── Step 4: Write Structured README Markdown Files ────────────────────────────

def write_readme_files(base_dir: Path, df, hourly_df):
    """Writes detailed README.md documentation matching YLC_report style."""
    log.info("Generating markdown documentation across FHV_report directories...")

    med_dur = df["trip_duration_min"].median()
    mean_dur = df["trip_duration_min"].mean()
    med_dist = df["trip_distance"].median()
    p90_dist = np.percentile(df["trip_distance"], 90)
    med_fare = df["fare_amount"].median()
    mean_fare = df["fare_amount"].mean()
    med_spd = df["avg_speed_mph"].dropna().median()
    mean_spd = df["avg_speed_mph"].dropna().mean()
    tipped_mask = df["tip_pct"] > 0
    pct_tipped = tipped_mask.mean() * 100
    med_tip_pct = df.loc[tipped_mask, "tip_pct"].median() if pct_tipped > 0 else 0

    # 1. 01_overview_and_eda/README.md
    eda_readme = f"""# 📊 01. Tổng Quan Dữ Liệu & Executive Dashboard (FHVHV - Uber & Lyft)

> **Tập dữ liệu:** High-Volume For-Hire Vehicles (FHVHV) — NYC Taxi Lakehouse  
> **Quy mô:** **243,576,832 chuyến đi sạch** năm 2025 (~20M chuyến/tháng).  
> **Nền tảng chủ đạo:** **Uber (HV0003 ~75%)** và **Lyft (HV0005 ~25%)**.

---

## 🖼️ Biểu Đồ: `silver_visual_dashboard.png`

![Executive Dashboard](./silver_visual_dashboard.png)

---

## 🔍 Giải Thích Chi Tiết 6 Góc Nhìn Phân Tích:

| Khía cạnh | Chỉ số thực tế | Ý nghĩa kỹ thuật & Nghiệp vụ |
|---|---|---|
| **1. Thời lượng di chuyển** | Trung vị: **{med_dur:.1f} phút** (Trung bình: **{mean_dur:.1f} phút**) | FHVHV phục vụ các chặng di chuyển dài hơn xe taxi truyền thống, kết nối các quận ngoài (Outer Boroughs). |
| **2. Cự ly di chuyển** | Trung vị: **{med_dist:.2f} dặm** (P90: **{p90_dist:.2f} dặm**) | Cự ly trung vị cao gấp gần 3 lần Yellow Taxi (~1.72 dặm), phản ánh độ bao phủ toàn diện 5 quận của New York. |
| **3. Tỷ lệ Tip điện tử** | Tỷ lệ có tip: **~{pct_tipped:.1f}%** (Trung vị khi tip: **{med_tip_pct:.1f}%**) | Khác với taxi truyền thống quẹt thẻ (tip >80%), ứng dụng gọi xe có tỷ lệ khách tip thấp hơn, tập trung tại các mốc gợi ý in-app (15%, 20%). |
| **4. Cự ly vs Giá cước** | Dynamic Surge Pricing: ~$8.00 + $2.50/mi | Giá cước thuật toán linh hoạt (Surge Pricing) theo nhu cầu thời gian thực thay vì đồng hồ công tơ mét cố định. |
| **5. Cước phí vs Tiền Tip** | Chùm tia phân bổ 15%, 20%, 25% | Khi khách hàng quyết định tip, tiền tip bám chặt theo các dải phần trăm mặc định trên giao diện app. |
| **6. Vận tốc theo 24 giờ** | Đáy ùn tắc: **~9.5 - 11 mph** (17h - 19h) | Vận tốc giảm mạnh vào giờ cao điểm tan tầm và tăng cao vào rạng sáng khi đường phố thông thoáng. |
"""
    (base_dir / "01_overview_and_eda" / "README.md").write_text(eda_readme, encoding="utf-8")

    # 2. 02_distributions_histograms/README.md
    hist_readme = f"""# 📈 02. Phân Phối Đơn Biến (Histograms Analytics - FHVHV)

> **Tập dữ liệu:** High-Volume For-Hire Vehicles (FHVHV - Uber & Lyft)  
> **Mục tiêu:** Khám phá hình dạng phân phối cước, cự ly, thời lượng, và nhận diện hiện tượng 2 đỉnh (*Bimodal Distribution*).

---

## 🖼️ Danh Sách 6 Biểu Đồ Histogram

---

### 1. `01_hist_trip_duration.png` — Phân Phối Thời Lượng Chuyến Đi
![01 Trip Duration](./01_hist_trip_duration.png)

- **Trung vị (Median):** **`{med_dur:.1f} phút`** | **Trung bình (Mean):** **`{mean_dur:.1f} phút`**.
- **Giải thích:** Phân phối lệch phải (*Right-skewed*). Đa số các chuyến đi hoàn tất trong khoảng 15 – 30 phút. Đuôi phân phối kéo dài phản ánh các chuyến đi xuyên quận và ùn tắc trong giờ cao điểm.

---

### 2. `02_hist_trip_distance.png` — Phân Phối Cự Ly Di Chuyển
![02 Trip Distance](./02_hist_trip_distance.png)

- **Trung vị (Median):** **`{med_dist:.2f} dặm`** | **P90:** **`{p90_dist:.2f} dặm`**.
- **Giải thích:** Khác biệt vượt trội so với Yellow Taxi (1.72 dặm), mạng lưới gọi xe công nghệ Uber/Lyft phục vụ phần lớn các hành trình dài hơn nối Brooklyn, Queens, The Bronx với Manhattan hoặc các sân bay JFK/LGA.

---

### 3. `03_hist_tip_percentage.png` — Phân Phối Tỷ Lệ Tiền Tip Trên Ứng Dụng
![03 Tip Percentage](./03_hist_tip_percentage.png)

- **Giải thích:** Xuất hiện các đỉnh nhọn (*Spikes*) tại các mức **`10%`**, **`15%`**, **`20%` (Đỉnh cao nhất)** và **`25%`**. Hiện tượng này thể hiện sự phụ thuộc trực tiếp vào các nút bấm gợi ý mặc định (*In-app Presets*) của Uber và Lyft.

---

### 4. `04_hist_fare_amount.png` — Phân Phối Giá Cước Cơ Bản
![04 Fare Amount](./04_hist_fare_amount.png)

- **Trung vị (Median):** **`${med_fare:.2f}`** | **Trung bình (Mean):** **`${mean_fare:.2f}`**.
- **Giải thích:** Giá cước biến thiên liên tục từ $10 đến $50 tùy theo cung cầu, thời gian chờ và tình trạng giao thông.

---

### 5. `05_hist_average_speed.png` — Phân Phối Vận Tốc Di Chuyển Trung Bình
![05 Average Speed](./05_hist_average_speed.png)

- **Vận tốc trung vị:** **`{med_spd:.1f} mph`** | **Trung bình:** **`{mean_spd:.1f} mph`**.
- **Giải thích:** Tốc độ lưu thông trung bình trong thành phố thấp, chỉ đạt tốc độ cao khi xe di chuyển trên các tuyến cao tốc huyết mạch ngoại thành hoặc vào ban đêm.

---

### 6. `06_bimodal_rush_hours.png` — Phân Phối 2 Đỉnh Giờ Cao Điểm Trong Ngày
![06 Bimodal Rush Hours](./06_bimodal_rush_hours.png)

- **Đỉnh 1 (Cao điểm sáng 08:00):** Đạt ~1.10 triệu chuyến/giờ (nhu cầu đi làm).
- **Đỉnh 2 (Cao điểm chiều/tối 17:00 – 19:00):** Đạt đỉnh cao nhất ~1.26 triệu chuyến/giờ (tan sở, đi ăn, giải trí).
- **Trũng đêm (03:00 – 05:00):** Nhu cầu thấp nhất, nhưng giá cước trung bình và cự ly đạt mức cao nhất (phục vụ khách ra sân bay hoặc đi xa).
"""
    (base_dir / "02_distributions_histograms" / "README.md").write_text(hist_readme, encoding="utf-8")

    # 3. 03_relationships_scatter/README.md
    scatter_readme = f"""# 🔍 03. Tương Quan Đa Biến (Scatter Plots Analytics - FHVHV)

> **Tập dữ liệu:** High-Volume For-Hire Vehicles (FHVHV - Uber & Lyft)  
> **Mục tiêu:** Khám phá mối quan hệ tương quan giữa cự ly, giá cước động, tiền tip và tốc độ di chuyển theo thời gian.

---

## 🖼️ Danh Sách 4 Biểu Đồ Scatter Plot

---

### 1. `01_scatter_distance_vs_fare.png` — Cự Ly Di Chuyển vs. Giá Cước (Uber vs. Lyft)
![01 Distance vs Fare](./01_scatter_distance_vs_fare.png)

- **Phân tách nền tảng:** Điểm đen đại diện cho Uber (HV0003) và hồng đại diện cho Lyft (HV0005).
- **Cơ chế định giá động (*Dynamic Pricing*):** Không có giá cước phẳng cứng nhắc như taxi truyền thống ($70 JFK); thay vào đó, giá cước phân tán thành dải rộng xung quanh đường dự đoán $8.00 + $2.50/mi, phản ánh hệ số nhân Surge Pricing khi cầu vượt cung.

---

### 2. `02_scatter_distance_vs_duration.png` — Cự Ly vs. Thời Gian Di Chuyển (Color theo Vận Tốc)
![02 Distance vs Duration](./02_scatter_distance_vs_duration.png)

- **Phân cụm dữ liệu & Vận tốc:**
  - **Cụm màu tím/xanh đậm (Chậm < 10 mph):** Xe bị kẹt trong lõi trung tâm Manhattan hoặc giờ tan tầm.
  - **Cụm màu vàng/xanh sáng (Nhanh > 25 mph):** Các hành trình trên cao tốc nối các quận ngoại ô (Brooklyn, Queens, Staten Island).

---

### 3. `03_scatter_fare_vs_tip.png` — Giá Cước vs. Tiền Tip (Chùm Tia Tip In-App)
![03 Fare vs Tip](./03_scatter_fare_vs_tip.png)

- **Phân tích chùm tia (*Ray Clusters*):**
  - Khi khách tip theo tỷ lệ phần trăm, các điểm dữ liệu phân bố thẳng hàng theo các dải tia **15%, 20%, 25%**.
  - Các đường ngang cố định phản ánh nhóm người dùng chọn tip số tiền tròn ($2, $5, $10).

---

### 4. `04_scatter_hour_vs_speed.png` — Khung Giờ Trong Ngày vs. Vận Tốc Di Chuyển
![04 Hour vs Speed](./04_scatter_hour_vs_speed.png)

- **Chu kỳ 24 giờ:**
  - Tốc độ di chuyển cao nhất vào rạng sáng (02:00 – 05:00) với mức trung bình ~18 – 22 mph.
  - Tốc độ giảm sâu nhất vào giờ cao điểm buổi tối (17:00 – 19:00) xuống còn ~9 – 11 mph.
"""
    (base_dir / "03_relationships_scatter" / "README.md").write_text(scatter_readme, encoding="utf-8")

    # 4. Master FHV_report/README.md
    master_readme = f"""# 🚗 Báo Cáo Tổng Hợp Trực Quan Dữ Liệu FHVHV (Uber & Lyft Lakehouse)

> **Môi trường & Nền tảng:** Dữ liệu Delta Lake xe công nghệ công suất cao (FHVHV - High-Volume For-Hire Vehicles) truy vấn phân tán qua **Trino SQL Engine** và xử lý trực quan bằng **Python (Seaborn, Matplotlib)**.  
> **Quy mô tập dữ liệu:** **243,576,832 chuyến đi** trong năm 2025 (~20 triệu chuyến/tháng).  
> **Các nhà cung cấp:** **Uber (HV0003)** chiếm ~75%, **Lyft (HV0005)** chiếm ~25%.

---

## 🗂️ Cấu Trúc Báo Cáo Chuẩn Hóa (Tương tự YLC_report)

```text
FHV_report/
├── 📄 README.md                                ➔ [BẠN ĐANG XEM] Báo cáo tổng hợp toàn diện
│
├── 📂 01_overview_and_eda/                     ➔ Giai đoạn 1: Tổng quan quy mô & Dashboard tổng hợp
│   ├── 🖼️ silver_visual_dashboard.png
│   └── 📄 README.md
│
├── 📂 02_distributions_histograms/             ➔ Giai đoạn 2: Phân phối đơn biến (Histograms)
│   ├── 🖼️ 01_hist_trip_duration.png           (Thời lượng di chuyển)
│   ├── 🖼️ 02_hist_trip_distance.png           (Cự ly di chuyển)
│   ├── 🖼️ 03_hist_tip_percentage.png          (Tỷ lệ tiền Tip in-app)
│   ├── 🖼️ 04_hist_fare_amount.png             (Giá cước cơ bản)
│   ├── 🖼️ 05_hist_average_speed.png           (Vận tốc di chuyển trung bình)
│   ├── 🖼️ 06_bimodal_rush_hours.png           (Phân phối 2 đỉnh giờ cao điểm)
│   └── 📄 README.md
│
└── 📂 03_relationships_scatter/                ➔ Giai đoạn 3: Mối quan hệ tương quan đa biến (Scatter Plots)
    ├── 🖼️ 01_scatter_distance_vs_fare.png     (Cự ly vs Giá cước Uber/Lyft)
    ├── 🖼️ 02_scatter_distance_vs_duration.png (Cự ly vs Thời gian)
    ├── 🖼️ 03_scatter_fare_vs_tip.png          (Giá cước vs Tiền Tip)
    ├── 🖼️ 04_scatter_hour_vs_speed.png        (Khung giờ vs Vận tốc)
    └── 📄 README.md
```

---

## 📊 1. Executive Dashboard (01_overview_and_eda)
![Executive Dashboard](./01_overview_and_eda/silver_visual_dashboard.png)

- **Quy mô:** Hơn 243.5 triệu chuyến đi năm 2025 (lớn gấp ~7 lần Yellow Taxi với 35.6 triệu chuyến).
- **Cự ly trung vị:** **{med_dist:.2f} dặm** (so với 1.72 dặm của taxi vàng).
- **Thời lượng trung vị:** **{med_dur:.1f} phút** (so với 13.5 phút của taxi vàng).
- **Chi tiết:** Xem thêm tại [01_overview_and_eda/README.md](./01_overview_and_eda/README.md).

---

## 📈 2. Phân Phối Đơn Biến (02_distributions_histograms)
Khám phá hình thái phân phối, cự ly và nhu cầu 2 đỉnh trong ngày:
- [01_hist_trip_duration.png](./02_distributions_histograms/01_hist_trip_duration.png): Phân phối thời gian di chuyển.
- [02_hist_trip_distance.png](./02_distributions_histograms/02_hist_trip_distance.png): Phân phối cự ly chuyến đi.
- [03_hist_tip_percentage.png](./02_distributions_histograms/03_hist_tip_percentage.png): Đỉnh nhọn tip 15%, 20% trên ứng dụng.
- [04_hist_fare_amount.png](./02_distributions_histograms/04_hist_fare_amount.png): Giá cước cơ bản.
- [05_hist_average_speed.png](./02_distributions_histograms/05_hist_average_speed.png): Vận tốc trung bình trong đô thị.
- [06_bimodal_rush_hours.png](./02_distributions_histograms/06_bimodal_rush_hours.png): Đỉnh sáng (08h) và đỉnh tối (17h-19h).
- **Chi tiết:** Xem thêm tại [02_distributions_histograms/README.md](./02_distributions_histograms/README.md).

---

## 🔍 3. Tương Quan Đa Biến (03_relationships_scatter)
Phân tích tương quan giá cước, tốc độ và định giá động:
- [01_scatter_distance_vs_fare.png](./03_relationships_scatter/01_scatter_distance_vs_fare.png): Cự ly vs Cước phí (so sánh Uber và Lyft).
- [02_scatter_distance_vs_duration.png](./03_relationships_scatter/02_scatter_distance_vs_duration.png): Cự ly vs Thời lượng (phân cụm vận tốc).
- [03_scatter_fare_vs_tip.png](./03_relationships_scatter/03_scatter_fare_vs_tip.png): Chùm tia phần trăm tip in-app.
- [04_scatter_hour_vs_speed.png](./03_relationships_scatter/04_scatter_hour_vs_speed.png): Vận tốc theo khung giờ 24h.
- **Chi tiết:** Xem thêm tại [03_relationships_scatter/README.md](./03_relationships_scatter/README.md).
"""
    (base_dir / "README.md").write_text(master_readme, encoding="utf-8")
    log.info("Finished writing documentation.")


# ── Step 5: Main Orchestrator ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate statistical Histogram and Scatter Plot visualizations for FHVHV dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=os.environ.get("TRINO_HOST", "localhost"), help="Trino coordinator host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRINO_PORT", "8080")), help="Trino coordinator port")
    parser.add_argument("--user", default="airflow", help="Trino username")
    parser.add_argument("--month", default="2025", help="Target month partition (e.g. '2025-01') or '2025'/'all' for entire year")
    parser.add_argument("--sample-size", type=int, default=60000, help="Sample size for scatter plots and histograms")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "FHV_report"), help="Output directory path")

    args = parser.parse_args()

    base_output = Path(args.output_dir)
    dir_overview = base_output / "01_overview_and_eda"
    dir_hist = base_output / "02_distributions_histograms"
    dir_scatter = base_output / "03_relationships_scatter"

    for d in [dir_overview, dir_hist, dir_scatter]:
        d.mkdir(parents=True, exist_ok=True)

    month_arg = args.month.strip()
    if month_arg in ("", "all", "2025", "all_year"):
        month_partitions = [f"fhvhv_tripdata_2025-{m:02d}" for m in range(1, 13)]
        target_desc = "full year 2025 (all 12 months)"
    else:
        if not month_arg.startswith("fhvhv_tripdata_"):
            month_arg = f"fhvhv_tripdata_{month_arg}"
        month_partitions = [month_arg]
        target_desc = f"month {month_arg}"

    log.info("Connecting to Trino at %s:%d...", args.host, args.port)
    conn = get_trino_connection(args.host, args.port, args.user)

    sample_per_month = max(1000, args.sample_size // len(month_partitions))
    sample_dfs = []
    hourly_dfs = []

    log.info("Querying FHVHV data for %s across %d partition(s)...", target_desc, len(month_partitions))
    try:
        import pandas as pd
        for idx, m_partition in enumerate(month_partitions, start=1):
            log.info("  [%d/%d] Fetching partition %s (sample size: %d)...", idx, len(month_partitions), m_partition, sample_per_month)
            sample_sql = f"""
            SELECT 
                CAST(base_passenger_fare AS DOUBLE) AS fare_amount,
                CAST(trip_miles AS DOUBLE) AS trip_distance,
                CAST(tips AS DOUBLE) AS tip_amount,
                CAST(driver_pay AS DOUBLE) AS driver_pay,
                hvfhs_license_num,
                CASE 
                    WHEN hvfhs_license_num = 'HV0003' THEN 'Uber'
                    WHEN hvfhs_license_num = 'HV0005' THEN 'Lyft'
                    ELSE 'Other FHV'
                END AS service_provider,
                HOUR(pickup_datetime) AS pickup_hour,
                DATE_DIFF('second', pickup_datetime, dropoff_datetime) / 60.0 AS trip_duration_min,
                CASE 
                    WHEN DATE_DIFF('second', pickup_datetime, dropoff_datetime) > 30 
                    THEN trip_miles / (DATE_DIFF('second', pickup_datetime, dropoff_datetime) / 3600.0) 
                    ELSE NULL 
                END AS avg_speed_mph,
                CASE 
                    WHEN base_passenger_fare > 0 
                    THEN (tips / base_passenger_fare) * 100.0 
                    ELSE 0.0 
                END AS tip_pct,
                CASE 
                    WHEN airport_fee > 0 THEN TRUE 
                    ELSE FALSE 
                END AS is_airport
            FROM delta.bronze.fhvhv_trips
            WHERE _source_month = '{m_partition}'
              AND dropoff_datetime >= pickup_datetime
              AND trip_miles > 0 
              AND base_passenger_fare > 0
            LIMIT {sample_per_month}
            """

            hourly_sql = f"""
            SELECT 
                HOUR(pickup_datetime) AS pickup_hour,
                COUNT(*) AS trip_count,
                ROUND(AVG(base_passenger_fare), 2) AS avg_fare,
                ROUND(AVG(trip_miles), 2) AS avg_distance
            FROM delta.bronze.fhvhv_trips 
            WHERE _source_month = '{m_partition}'
              AND dropoff_datetime >= pickup_datetime
            GROUP BY HOUR(pickup_datetime)
            ORDER BY pickup_hour
            """

            m_sample_df = fetch_dataframe(conn, sample_sql)
            if not m_sample_df.empty:
                sample_dfs.append(m_sample_df)

            m_hourly_df = fetch_dataframe(conn, hourly_sql)
            if not m_hourly_df.empty:
                hourly_dfs.append(m_hourly_df)

        if not sample_dfs:
            log.warning("No records found in FHVHV dataset for %s", target_desc)
            return

        df = pd.concat(sample_dfs, ignore_index=True)
        log.info("Total sampled rows fetched: %d", len(df))

        # Combine hourly metrics with weighted averages across all months
        all_hourly = pd.concat(hourly_dfs, ignore_index=True)
        combined_hourly = []
        for h in range(24):
            h_rows = all_hourly[all_hourly["pickup_hour"] == h]
            if not h_rows.empty:
                tot_trips = int(h_rows["trip_count"].sum())
                w_fare = (h_rows["avg_fare"] * h_rows["trip_count"]).sum() / tot_trips if tot_trips > 0 else 0.0
                w_dist = (h_rows["avg_distance"] * h_rows["trip_count"]).sum() / tot_trips if tot_trips > 0 else 0.0
                combined_hourly.append({
                    "pickup_hour": h,
                    "trip_count": tot_trips,
                    "avg_fare": round(float(w_fare), 2),
                    "avg_distance": round(float(w_dist), 2),
                })
        hourly_df = pd.DataFrame(combined_hourly)
        log.info("Hourly aggregation completed across %d buckets (total trips: %s)", len(hourly_df), f"{hourly_df['trip_count'].sum():,}")
    finally:
        conn.close()

    setup_plot_style()
    plot_overview_dashboard(df, dir_overview)
    plot_histograms(df, hourly_df, dir_hist)
    plot_scatters(df, dir_scatter)
    write_readme_files(base_output, df, hourly_df)

    print("\n" + "=" * 80)
    print(" 🚗 ALL FHVHV HISTOGRAM & SCATTER CHARTS SUCCESSFULLY GENERATED!")
    print(f" 📁 Report Directory: {base_output.resolve()}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
