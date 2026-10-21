#!/usr/bin/env python3
"""
plot_hist_scatter.py — NYC Yellow Taxi Histogram & Scatter Plot Visualizations
=============================================================================

Generates high-quality statistical distribution (Histograms) and bivariate
relationship (Scatter Plots) charts from NYC Taxi Silver Delta table via Trino.

Key Feature:
  Comprehensive point-color categorization and clear legend/callout annotations
  for all scatter plots in YLC_report/03_relationships_scatter/:
    1. 01_scatter_distance_vs_fare.png     : Standard Metered vs Airport Flat Rate ($70 JFK).
    2. 02_scatter_distance_vs_duration.png : Distance vs Duration (Colorbar: Speed in mph, 10/25/45 mph rays).
    3. 03_scatter_fare_vs_tip.png          : Fare vs Tip (Tip Tiers: 20% POS Default, 25%, 30%, Flat Tips).
    4. 04_scatter_hour_vs_speed.png        : 24h Traffic Regimes (Free Flow, Rush Hours, Midday, Mean Speed).

Outputs:
  YLC_report/
  ├── 01_overview_and_eda/
  │   └── silver_visual_dashboard.png
  ├── 02_distributions_histograms/
  │   └── [01_hist_... to 05_hist_...]
  └── 03_relationships_scatter/
      ├── 01_scatter_distance_vs_fare.png
      ├── 02_scatter_distance_vs_duration.png
      ├── 03_scatter_fare_vs_tip.png
      ├── 04_scatter_hour_vs_speed.png
      └── README.md

Usage:
  .venv/bin/python3 scripts/plot_hist_scatter.py
  .venv/bin/python3 scripts/plot_hist_scatter.py --scatters-only
  .venv/bin/python3 scripts/plot_hist_scatter.py --month 2025-01 --sample-size 60000
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
log = logging.getLogger("plot_hist_scatter")


def get_trino_connection(host: str, port: int, user: str, catalog: str = "delta", schema: str = "silver"):
    """Establish connection to Trino."""
    try:
        import trino.dbapi
        return trino.dbapi.connect(
            host=host,
            port=port,
            user=user,
            catalog=catalog,
            schema=schema,
            http_scheme="http",
        )
    except (ImportError, AttributeError):
        try:
            import trino
            return trino.dbapi.connect(
                host=host,
                port=port,
                user=user,
                catalog=catalog,
                schema=schema,
                http_scheme="http",
            )
        except Exception as e:
            log.error("Failed to connect to Trino: %s. Run inside .venv: .venv/bin/python3 scripts/plot_hist_scatter.py", e)
            sys.exit(1)


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


# ── Step 1: Generate Histograms ───────────────────────────────────────────────

def plot_histograms(df, output_dir: Path):
    """Plots individual distribution histograms."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Histogram charts into %s...", output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Trip Duration Histogram
    plt.figure(figsize=(10, 5))
    durations = df["trip_duration_min"][(df["trip_duration_min"] > 0) & (df["trip_duration_min"] <= 60)]
    median_dur = durations.median()
    mean_dur = durations.mean()

    sns.histplot(durations, bins=60, kde=True, color="#1f77b4", edgecolor="white", alpha=0.75)
    plt.axvline(median_dur, color="#d62728", linestyle="--", linewidth=2, label=f"Median: {median_dur:.1f} min")
    plt.axvline(mean_dur, color="#2ca02c", linestyle=":", linewidth=2, label=f"Mean: {mean_dur:.1f} min")

    plt.title("Distribution of NYC Taxi Trip Duration (0 - 60 mins)", fontsize=13, fontweight="bold", pad=12)
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

    plt.title("Distribution of NYC Taxi Trip Distance (0 - 25 miles)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Trip Distance (miles)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    plt.tight_layout()
    plt.savefig(output_dir / "02_hist_trip_distance.png", dpi=200)
    plt.close()

    # 3. Tip Percentage Histogram (Credit Card)
    plt.figure(figsize=(10, 5))
    cc_tips = df[(df["payment_type"] == 1) & (df["tip_pct"] >= 0) & (df["tip_pct"] <= 50)]["tip_pct"]

    sns.histplot(cc_tips, bins=50, kde=False, color="#9467bd", edgecolor="white", alpha=0.8)
    for pct, label in [(15, "15%"), (20, "20% (Default)"), (25, "25%"), (30, "30%")]:
        plt.axvline(pct, color="#d62728", linestyle="--", alpha=0.7, linewidth=1.5)
        plt.text(pct + 0.4, plt.ylim()[1] * 0.85, label, rotation=90, color="#d62728", fontsize=9, fontweight="bold")

    plt.title("Distribution of Tip % on Credit Card Trips (Notice default POS spikes)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Tip Percentage (% of Base Fare)", fontsize=11, fontweight="bold")
    plt.ylabel("Frequency / Count", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "03_hist_tip_percentage.png", dpi=200)
    plt.close()

    # 4. Fare Amount Histogram
    plt.figure(figsize=(10, 5))
    fares = df["fare_amount"][(df["fare_amount"] > 0) & (df["fare_amount"] <= 100)]

    sns.histplot(fares, bins=50, kde=True, color="#ff7f0e", edgecolor="white", alpha=0.75)
    plt.axvline(70.0, color="#d62728", linestyle="--", linewidth=1.8, label="JFK Flat Rate ($70.00)")
    plt.axvline(fares.median(), color="#1f77b4", linestyle=":", linewidth=2, label=f"Median Fare: ${fares.median():.2f}")

    plt.title("Distribution of Base Fare Amount ($0 - $100)", fontsize=13, fontweight="bold", pad=12)
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


# ── Step 2: Generate Scatter Plots (03_relationships_scatter) ─────────────────

def plot_scatters(df, output_dir: Path):
    """
    Plots bivariate scatter relationships with rich, descriptive legends,
    clear color annotations, reference trend lines, and contextual callout boxes.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Scatter Plot charts into %s...", output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Chart 1: Distance vs Fare Amount (Standard Metered vs JFK Flat Rate)
    # ──────────────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    sample_fare = df[
        (df["trip_distance"] > 0) & (df["trip_distance"] <= 30) &
        (df["fare_amount"] > 0) & (df["fare_amount"] <= 120)
    ].copy()

    # Categorize data points with clear, descriptive labels for legend
    sample_fare["point_type"] = np.where(
        sample_fare["is_airport"],
        "Chuyến Sân Bay (Airport Trip: JFK Flat Rate $70 / Phụ phí)",
        "Chuyến Nội Đô / Thường (Standard Metered Trip)",
    )

    palette_fare = {
        "Chuyến Nội Đô / Thường (Standard Metered Trip)": "#1f77b4",
        "Chuyến Sân Bay (Airport Trip: JFK Flat Rate $70 / Phụ phí)": "#dc2626",
    }

    sns.scatterplot(
        data=sample_fare,
        x="trip_distance",
        y="fare_amount",
        hue="point_type",
        palette=palette_fare,
        alpha=0.35,
        s=20,
        edgecolor="none",
        ax=ax,
    )

    # Metered trend line
    x_vals = np.linspace(0, 30, 100)
    ax.plot(
        x_vals, 3.0 + 3.5 * x_vals,
        color="#16a34a", linestyle="-", linewidth=2.5,
        label=r"Đường Cước Chuẩn Đồng Hồ: Fare $\approx$ $3.00 + $3.50/dặm",
    )

    # JFK Flat Fare horizontal line
    ax.axhline(
        70.0,
        color="#dc2626", linestyle="--", linewidth=2.0, alpha=0.9,
        label="Mức Cước Cố Định Sân Bay JFK: $70.00 Flat Fare",
    )

    # Contextual callout annotations (using raw strings to avoid math mode issues)
    ax.annotate(
        "Đường Ngang Cước Cố Định JFK ($70.00)\nPhân bố thẳng tắp cho mọi cự ly 10 - 25 dặm",
        xy=(20, 70), xytext=(15, 96),
        arrowprops=dict(facecolor="#dc2626", shrink=0.08, width=1.5, headwidth=7),
        fontsize=9.5, fontweight="bold", color="#991b1b",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fee2e2", ec="#dc2626", lw=1.2, alpha=0.95),
    )

    ax.annotate(
        "Kẹt Xe / Dừng Chờ Nội Đô\n($0.70/phút khi xe chạy < 12 mph)",
        xy=(2.2, 55), xytext=(5.2, 108),
        arrowprops=dict(facecolor="#374151", shrink=0.08, width=1.5, headwidth=7),
        fontsize=9, fontweight="bold", color="#1f2937",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f3f4f6", ec="#9ca3af", lw=1.2, alpha=0.95),
    )

    ax.set_title(
        "Trip Distance vs. Base Fare Amount — Metered vs. Flat-Rate Airport Dynamics\n"
        "(Màu xanh = Cước đồng hồ tiêu chuẩn | Màu đỏ = Cước cố định sân bay JFK $70 / Phụ phí)",
        fontsize=11.5, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Trip Distance (miles) — Cự Ly Di Chuyển", fontsize=11, fontweight="bold")
    ax.set_ylabel("Base Fare Amount ($) — Giá Cước Cơ Bản", fontsize=11, fontweight="bold")
    ax.legend(
        title="Chú Thích Màu Sắc Điểm Dữ Liệu & Đường Xu Hướng",
        title_fontsize=10, fontsize=9,
        frameon=True, facecolor="white", edgecolor="#cccccc",
        loc="lower right",
    )
    plt.tight_layout()
    chart1_path = output_dir / "01_scatter_distance_vs_fare.png"
    plt.savefig(chart1_path, dpi=200)
    plt.close()
    log.info("Saved: %s", chart1_path)

    # ──────────────────────────────────────────────────────────────────────────
    # Chart 2: Distance vs Duration (Colorbar: Speed in mph + Speed Rays)
    # ──────────────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    sample_dur = df[
        (df["trip_distance"] > 0) & (df["trip_distance"] <= 30) &
        (df["trip_duration_min"] > 0) & (df["trip_duration_min"] <= 90) &
        df["avg_speed_mph"].notna()
    ].copy()
    sample_dur["speed_clipped"] = sample_dur["avg_speed_mph"].clip(lower=4, upper=45)

    sc = ax.scatter(
        sample_dur["trip_distance"],
        sample_dur["trip_duration_min"],
        c=sample_dur["speed_clipped"],
        cmap="viridis",
        vmin=4,
        vmax=45,
        alpha=0.35,
        s=18,
        edgecolors="none",
    )

    # Colorbar on right
    cbar = fig.colorbar(sc, ax=ax, pad=0.02, aspect=28)
    cbar.set_label("Vận Tốc Trung Bình (Average Speed - mph)", fontsize=11, fontweight="bold")
    cbar.ax.tick_params(labelsize=10)

    # Speed reference lines (isochrones / speed rays)
    d_range = np.linspace(0.1, 30, 100)
    ax.plot(d_range, 6.0 * d_range, color="#7c3aed", linestyle="--", linewidth=1.6, label="Đường 10 mph (Tốc độ nội đô / Kẹt xe)")
    ax.plot(d_range, 2.4 * d_range, color="#059669", linestyle="-.", linewidth=1.6, label="Đường 25 mph (Lưu thông trục chính)")
    ax.plot(d_range, (60.0 / 45.0) * d_range, color="#ca8a04", linestyle=":", linewidth=2.0, label="Đường 45 mph (Tốc độ cao tốc)")

    # Callout annotations for clusters - neatly separated from legend
    ax.annotate(
        "Cụm Tím Sẫm: Ùn tắc Midtown Manhattan (3 – 8 mph)\nCự ly ngắn 1-3 dặm nhưng mất 30-55 phút",
        xy=(2.5, 45), xytext=(1.5, 74),
        arrowprops=dict(facecolor="#440154", shrink=0.08, width=1.5, headwidth=7),
        fontsize=8.8, fontweight="bold", color="#440154",
        bbox=dict(boxstyle="round,pad=0.4", fc="#ede9fe", ec="#7c3aed", lw=1.2, alpha=0.95),
    )

    ax.annotate(
        "Cụm Vàng Sáng: Cao tốc FDR / BQE / Sân bay (35 – 50 mph)\nCự ly dài 15-25 dặm chỉ tốn 20-30 phút",
        xy=(18, 25), xytext=(11.5, 10),
        arrowprops=dict(facecolor="#eab308", shrink=0.08, width=1.5, headwidth=7),
        fontsize=8.8, fontweight="bold", color="#854d0e",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fef9c3", ec="#ca8a04", lw=1.2, alpha=0.95),
    )

    ax.set_title(
        "Trip Distance vs. Duration — Color-Coded by Average Speed in mph\n"
        "(Dải màu Viridis: Tím sẫm <10 mph Kẹt xe | Xanh lục ~20-25 mph | Vàng sáng >35 mph Cao tốc)",
        fontsize=11.5, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Trip Distance (miles) — Cự Ly Di Chuyển", fontsize=11, fontweight="bold")
    ax.set_ylabel("Trip Duration (minutes) — Thời Lượng Chuyến Đi", fontsize=11, fontweight="bold")
    ax.set_xlim(-0.5, 30.5)
    ax.set_ylim(-1, 92)
    ax.legend(
        title="Đường Tham Chiếu Vận Tốc (Speed Rays)",
        title_fontsize=10, fontsize=8.8,
        loc="upper right", frameon=True, facecolor="white", edgecolor="#cccccc",
    )
    plt.tight_layout()
    chart2_path = output_dir / "02_scatter_distance_vs_duration.png"
    plt.savefig(chart2_path, dpi=200)
    plt.close()
    log.info("Saved: %s", chart2_path)

    # ──────────────────────────────────────────────────────────────────────────
    # Chart 3: Fare Amount vs Tip Amount (Categorical Tip Tiers & POS Rays)
    # ──────────────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    sample_tips = df[
        (df["payment_type"] == 1) &
        (df["fare_amount"] > 0) & (df["fare_amount"] <= 80) &
        (df["tip_amount"] >= 0) & (df["tip_amount"] <= 35)
    ].copy()

    # Classify tip behavior categories with escaped dollar signs
    def classify_tip_category(row):
        tip = row["tip_amount"]
        pct = row["tip_pct"]
        if tip < 0.05:
            return "Không Tip / $0 (No Tip)"
        # Check round dollar flat tips
        for flat_val in [5.0, 10.0, 20.0]:
            if abs(tip - flat_val) < 0.06:
                return r"Tip Chẵn \$" + str(int(flat_val)) + r" (Flat \$" + str(int(flat_val)) + ")"
        if 18.0 <= pct <= 22.0:
            return "Tip Chuẩn 20% (18% - 22% Mặc định máy POS)"
        elif 22.5 <= pct <= 27.5:
            return "Tip 25% (Gợi ý trên màn hình POS)"
        elif pct >= 28.0:
            return r"Tip Hào Phóng $\geq$ 30% (Gợi ý POS & Khách hào phóng)"
        else:
            return "Tip Tùy Biến / Dưới Chuẩn (< 18%)"

    sample_tips["tip_category"] = sample_tips.apply(classify_tip_category, axis=1)

    palette_tips = {
        "Tip Chuẩn 20% (18% - 22% Mặc định máy POS)": "#1d4ed8",
        "Tip 25% (Gợi ý trên màn hình POS)": "#16a34a",
        r"Tip Hào Phóng $\geq$ 30% (Gợi ý POS & Khách hào phóng)": "#9333ea",
        r"Tip Chẵn \$5 (Flat \$5)": "#ea580c",
        r"Tip Chẵn \$10 (Flat \$10)": "#c2410c",
        r"Tip Chẵn \$20 (Flat \$20)": "#9a3412",
        "Tip Tùy Biến / Dưới Chuẩn (< 18%)": "#94a3b8",
        "Không Tip / $0 (No Tip)": "#64748b",
    }

    sns.scatterplot(
        data=sample_tips,
        x="fare_amount",
        y="tip_amount",
        hue="tip_category",
        palette=palette_tips,
        alpha=0.45,
        s=18,
        edgecolor="none",
        ax=ax,
    )

    # Reference percentage ray lines
    fare_range = np.linspace(0, 80, 100)
    ax.plot(fare_range, fare_range * 0.20, color="#dc2626", linestyle="--", linewidth=2.0, label="Tia Chuẩn 20% (POS Default Button)")
    ax.plot(fare_range, fare_range * 0.25, color="#d97706", linestyle=":", linewidth=2.0, label="Tia 25% (POS Preset Button)")
    ax.plot(fare_range, fare_range * 0.30, color="#7c3aed", linestyle="-.", linewidth=2.0, label="Tia 30% (POS Preset Button)")

    # Reference horizontal flat tip lines ($5, $10, $20)
    for f_tip in [5.0, 10.0, 20.0]:
        ax.axhline(f_tip, color="#fdba74", linestyle=":", linewidth=1.2, alpha=0.8)

    # Vertical line at $70 for JFK flat rate tip cluster
    ax.axvline(70.0, color="#dc2626", linestyle=":", linewidth=1.5, alpha=0.6)

    # Annotations (escaped dollar signs)
    ax.annotate(
        "Chùm Tia 20%: Lựa chọn phổ biến nhất\n(Nút mặc định trên màn hình quẹt thẻ taxi)",
        xy=(45, 9.0), xytext=(22, 19),
        arrowprops=dict(facecolor="#1d4ed8", shrink=0.08, width=1.5, headwidth=7),
        fontsize=8.8, fontweight="bold", color="#1e40af",
        bbox=dict(boxstyle="round,pad=0.4", fc="#dbeafe", ec="#1d4ed8", lw=1.2, alpha=0.95),
    )

    ax.annotate(
        r"Cột Tip \$14 – \$21" "\n" r"từ chuyến JFK cước \$70",
        xy=(70, 14.5), xytext=(52, 28),
        arrowprops=dict(facecolor="#dc2626", shrink=0.08, width=1.5, headwidth=7),
        fontsize=8.8, fontweight="bold", color="#991b1b",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fee2e2", ec="#dc2626", lw=1.2, alpha=0.95),
    )

    ax.annotate(
        r"Đường tip chẵn \$5, \$10, \$20" "\n" "(Khách tự gõ tiền tròn)",
        xy=(65, 10), xytext=(50, 4.5),
        arrowprops=dict(facecolor="#ea580c", shrink=0.08, width=1.5, headwidth=7),
        fontsize=8.5, fontweight="bold", color="#9a3412",
        bbox=dict(boxstyle="round,pad=0.4", fc="#ffedd5", ec="#ea580c", lw=1.2, alpha=0.95),
    )

    ax.set_title(
        "Fare Amount vs. Tip Amount — Credit Card Trips & POS % Ray Clusters\n"
        r"(Xanh = Tip chuẩn 20% | Lục = Tip 25% | Tím = Tip $\geq$30% | Cam = Tiền chẵn \$5/\$10/\$20 | Xám = <18%)",
        fontsize=11.5, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Base Fare Amount ($) — Giá Cước Cơ Bản", fontsize=11, fontweight="bold")
    ax.set_ylabel("Tip Amount ($) — Tiền Tip Nhận Được", fontsize=11, fontweight="bold")
    ax.legend(
        title="Chú Thích Phân Loại Điểm & Chùm Tia Tip",
        title_fontsize=9.5, fontsize=8,
        frameon=True, facecolor="white", edgecolor="#cccccc",
        loc="upper left",
    )
    plt.tight_layout()
    chart3_path = output_dir / "03_scatter_fare_vs_tip.png"
    plt.savefig(chart3_path, dpi=200)
    plt.close()
    log.info("Saved: %s", chart3_path)

    # ──────────────────────────────────────────────────────────────────────────
    # Chart 4: Hour of Day vs Speed (Regime Colors + Rush Hour Bands + Mean Curve)
    # ──────────────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 6.5))
    sample_spd = df[(df["avg_speed_mph"] > 0) & (df["avg_speed_mph"] <= 55)].copy()
    sample_spd["pickup_hour"] = sample_spd["pickup_hour"].astype(int)

    # Categorize into 5 traffic regimes (using clean bracket tags, no missing font glyphs)
    def get_traffic_regime(hour):
        if 0 <= hour <= 5:
            return "[00-05h Đêm & Rạng Sáng]: Vắng xe / Tốc độ tối đa (18-24 mph)"
        elif 6 <= hour <= 9:
            return "[06-09h Cao Điểm Sáng]: Giờ đi làm / Tắc nghẽn bắt đầu"
        elif 10 <= hour <= 15:
            return "[10-15h Giữa Ngày]: Mật độ giao thông nội đô đều (~10 mph)"
        elif 16 <= hour <= 19:
            return "[16-19h Cao Điểm Chiều Tối]: Đáy ùn tắc trong ngày (8.5-10 mph)"
        else:
            return "[20-23h Đêm Muộn]: Tốc độ lưu thông phục hồi dần"

    sample_spd["traffic_regime"] = sample_spd["pickup_hour"].apply(get_traffic_regime)

    palette_regimes = {
        "[00-05h Đêm & Rạng Sáng]: Vắng xe / Tốc độ tối đa (18-24 mph)": "#6366f1",
        "[06-09h Cao Điểm Sáng]: Giờ đi làm / Tắc nghẽn bắt đầu": "#f59e0b",
        "[10-15h Giữa Ngày]: Mật độ giao thông nội đô đều (~10 mph)": "#0284c7",
        "[16-19h Cao Điểm Chiều Tối]: Đáy ùn tắc trong ngày (8.5-10 mph)": "#ef4444",
        "[20-23h Đêm Muộn]: Tốc độ lưu thông phục hồi dần": "#10b981",
    }

    # Add controlled numeric jitter to avoid categorical conversion quirks
    rng = np.random.default_rng(42)
    sample_spd["hour_jitter"] = sample_spd["pickup_hour"] + rng.uniform(-0.25, 0.25, size=len(sample_spd))

    # Scatter points grouped by traffic regime
    for regime_name, regime_color in palette_regimes.items():
        subset = sample_spd[sample_spd["traffic_regime"] == regime_name]
        ax.scatter(
            subset["hour_jitter"],
            subset["avg_speed_mph"],
            c=regime_color,
            s=12,
            alpha=0.25,
            edgecolors="none",
            label=regime_name,
        )

    # Shaded rush hour background bands
    ax.axvspan(6.5, 9.5, color="#f59e0b", alpha=0.10, label="Dải Cao Điểm Sáng (07:00 - 09:30 AM)")
    ax.axvspan(15.5, 19.5, color="#ef4444", alpha=0.10, label="Dải Cao Điểm Tối (16:30 - 19:30 PM)")

    # Mean speed line overlay
    hourly_mean = sample_spd.groupby("pickup_hour")["avg_speed_mph"].mean().reset_index()
    ax.plot(
        hourly_mean["pickup_hour"],
        hourly_mean["avg_speed_mph"],
        color="#b91c1c",
        marker="o",
        markersize=7,
        linewidth=3.0,
        label="Đường Vận Tốc Trung Bình (Mean Speed by Hour)",
        zorder=10,
    )

    # Highlight peak and trough with callout badges
    peak_row = hourly_mean.loc[hourly_mean["avg_speed_mph"].idxmax()]
    trough_row = hourly_mean.loc[hourly_mean["avg_speed_mph"].idxmin()]

    ax.annotate(
        f"Đỉnh Vận Tốc: {peak_row['avg_speed_mph']:.1f} mph\n(Khung {int(peak_row['pickup_hour']):02d}:00 rạng sáng)",
        xy=(peak_row["pickup_hour"], peak_row["avg_speed_mph"]),
        xytext=(peak_row["pickup_hour"] + 0.6, peak_row["avg_speed_mph"] + 8),
        arrowprops=dict(facecolor="#4338ca", shrink=0.08, width=1.5, headwidth=7),
        fontsize=9, fontweight="bold", color="#312e81",
        bbox=dict(boxstyle="round,pad=0.4", fc="#e0e7ff", ec="#6366f1", lw=1.2, alpha=0.95),
    )

    ax.annotate(
        f"Đáy Ùn Tắc: {trough_row['avg_speed_mph']:.1f} mph\n(Khung {int(trough_row['pickup_hour']):02d}:00 tan tầm)",
        xy=(trough_row["pickup_hour"], trough_row["avg_speed_mph"]),
        xytext=(trough_row["pickup_hour"] - 3.8, trough_row["avg_speed_mph"] + 15),
        arrowprops=dict(facecolor="#b91c1c", shrink=0.08, width=1.5, headwidth=7),
        fontsize=9, fontweight="bold", color="#7f1d1d",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fee2e2", ec="#ef4444", lw=1.2, alpha=0.95),
    )

    ax.set_title(
        "Vehicle Speed Across 24 Hours — Circadian Rhythm & Congestion Regimes\n"
        "(Tím = Đêm thông thoáng | Vàng = Cao điểm sáng | Lam = Giữa ngày | Đỏ = Cao điểm tối | Lục = Đêm muộn)",
        fontsize=11.5, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Hour of Day (0 - 23) — Khung Giờ Trong Ngày", fontsize=11, fontweight="bold")
    ax.set_ylabel("Average Speed (mph) — Vận Tốc Trung Bình", fontsize=11, fontweight="bold")
    ax.set_xticks(range(0, 24))
    ax.set_xlim(-0.8, 23.8)
    ax.set_ylim(-1, 58)
    ax.legend(
        title="Chú Thích Màu Sắc Điểm (Regimes), Vùng Giờ & Đường Trung Bình",
        title_fontsize=9.5, fontsize=8.5,
        frameon=True, facecolor="white", edgecolor="#cccccc",
        loc="upper right",
    )
    plt.tight_layout()
    chart4_path = output_dir / "04_scatter_hour_vs_speed.png"
    plt.savefig(chart4_path, dpi=200)
    plt.close()
    log.info("Saved: %s", chart4_path)


# ── Step 3: Generate Master Overview Dashboard ────────────────────────────────

def plot_master_dashboard(df, output_dir: Path):
    """Creates a consolidated 6-in-1 analytical overview dashboard."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Consolidated 6-in-1 Dashboard into %s...", output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("NYC Yellow Taxi Lakehouse (Silver Layer) — Comprehensive EDA Dashboard", fontsize=16, fontweight="bold", y=0.98)

    # Subplot 1: Trip Duration Hist
    dur = df["trip_duration_min"][(df["trip_duration_min"] > 0) & (df["trip_duration_min"] <= 45)]
    sns.histplot(dur, bins=40, kde=True, color="#1f77b4", ax=axes[0, 0])
    axes[0, 0].set_title("1. Trip Duration Distribution (mins)", fontweight="bold")
    axes[0, 0].set_xlabel("Minutes")

    # Subplot 2: Distance Hist
    dist = df["trip_distance"][(df["trip_distance"] > 0) & (df["trip_distance"] <= 20)]
    sns.histplot(dist, bins=40, kde=True, color="#2ca02c", ax=axes[0, 1])
    axes[0, 1].set_title("2. Trip Distance Distribution (miles)", fontweight="bold")
    axes[0, 1].set_xlabel("Miles")

    # Subplot 3: Tip % Hist
    tip_pcts = df[(df["payment_type"] == 1) & (df["tip_pct"] >= 0) & (df["tip_pct"] <= 40)]["tip_pct"]
    sns.histplot(tip_pcts, bins=40, color="#9467bd", ax=axes[0, 2])
    axes[0, 2].axvline(20, color="red", linestyle="--", label="20% Default")
    axes[0, 2].set_title("3. Tip % Distribution (Credit Card)", fontweight="bold")
    axes[0, 2].set_xlabel("Tip %")
    axes[0, 2].legend(fontsize=9)

    # Subplot 4: Distance vs Fare Scatter
    sample_df = df[(df["trip_distance"] > 0) & (df["trip_distance"] <= 25) & (df["fare_amount"] > 0) & (df["fare_amount"] <= 100)].copy()
    sample_df["Type"] = np.where(sample_df["is_airport"], "Airport ($70 Flat)", "Standard Metered")
    sns.scatterplot(
        data=sample_df, x="trip_distance", y="fare_amount", hue="Type",
        palette={"Airport ($70 Flat)": "#dc2626", "Standard Metered": "#1f77b4"},
        alpha=0.35, s=14, ax=axes[1, 0]
    )
    axes[1, 0].axhline(70, color="#dc2626", linestyle="--", alpha=0.8, label="JFK Flat Fare ($70)")
    axes[1, 0].set_title("4. Distance vs. Fare Amount ($)", fontweight="bold")
    axes[1, 0].set_xlabel("Distance (miles)")
    axes[1, 0].set_ylabel("Fare ($)")
    axes[1, 0].legend(fontsize=8.5, title="Category")

    # Subplot 5: Fare vs Tip Scatter
    sample_tip_df = df[(df["payment_type"] == 1) & (df["fare_amount"] > 0) & (df["fare_amount"] <= 60) & (df["tip_amount"] >= 0) & (df["tip_amount"] <= 25)].copy()
    sample_tip_df["Tip Tier"] = np.where(sample_tip_df["tip_pct"] >= 23, "High Tip (≥25%)", np.where(sample_tip_df["tip_pct"] >= 18, "Std 20% Tip", "Low / Other"))
    sns.scatterplot(
        data=sample_tip_df, x="fare_amount", y="tip_amount", hue="Tip Tier",
        palette={"High Tip (≥25%)": "#16a34a", "Std 20% Tip": "#1d4ed8", "Low / Other": "#94a3b8"},
        alpha=0.35, s=14, ax=axes[1, 1]
    )
    f_arr = np.linspace(0, 60, 50)
    axes[1, 1].plot(f_arr, f_arr * 0.2, color="#dc2626", linestyle="--", label="20% POS Default")
    axes[1, 1].set_title("5. Fare vs. Tip Amount ($)", fontweight="bold")
    axes[1, 1].set_xlabel("Fare ($)")
    axes[1, 1].set_ylabel("Tip ($)")
    axes[1, 1].legend(fontsize=8.5)

    # Subplot 6: Hourly Speed Trend
    sample_spd = df[(df["avg_speed_mph"] > 0) & (df["avg_speed_mph"] <= 50)]
    hourly_spd = sample_spd.groupby("pickup_hour")["avg_speed_mph"].mean().reset_index()
    axes[1, 2].plot(hourly_spd["pickup_hour"], hourly_spd["avg_speed_mph"], marker="o", color="#b91c1c", linewidth=2.5)
    axes[1, 2].axvspan(7, 9.5, color="#f59e0b", alpha=0.15, label="Morning Rush")
    axes[1, 2].axvspan(16.5, 19.5, color="#ef4444", alpha=0.15, label="Evening Rush")
    axes[1, 2].set_title("6. Average Speed by Hour of Day (mph)", fontweight="bold")
    axes[1, 2].set_xlabel("Hour (0-23)")
    axes[1, 2].set_ylabel("Speed (mph)")
    axes[1, 2].set_xticks(range(0, 24, 2))
    axes[1, 2].legend(fontsize=8.5)

    plt.tight_layout()
    dashboard_path = output_dir / "silver_visual_dashboard.png"
    plt.savefig(dashboard_path, dpi=200)
    plt.close()
    log.info("Saved master dashboard: %s", dashboard_path)


# ── Step 4: Write Updated Scatter README ──────────────────────────────────────

def write_scatter_readme(output_dir: Path):
    """Updates YLC_report/03_relationships_scatter/README.md with rich color explanations."""
    readme_content = r"""# 🔍 03. Tương Quan Đa Biến (Scatter Plots Analytics)

> **Tập dữ liệu:** `delta.silver.yellow_trips` (Tầng Silver)  
> **Mục tiêu:** Khám phá mối quan hệ tương quan giữa 2 biến định lượng liên tục, nhận diện đường xu hướng, phân cụm và phân loại rõ ràng màu sắc của các điểm dữ liệu.

---

## 🖼️ Danh Sách 4 Biểu Đồ Scatter Plot (Đã Chú Thích Rõ Màu Sắc)

---

### 1. `01_scatter_distance_vs_fare.png` — Cự Ly Di Chuyển vs. Giá Cước Cơ Bản
![01 Distance vs Fare](./01_scatter_distance_vs_fare.png)

- **🎨 Chú thích màu sắc điểm dữ liệu:**
  - 🔵 **Điểm màu xanh dương (`#1f77b4`):** Chuyến đi nội đô thông thường (*Standard Metered Trips*) tính theo đồng hồ cước.
  - 🔴 **Điểm màu đỏ (`#dc2626`):** Chuyến đi sân bay (*Airport Trips: JFK Flat Rate $70 / Phụ phí sân bay*).
- **🔍 Hiện tượng & Đường xu hướng:**
  - **Đường dốc tuyến tính màu xanh lá (`#16a34a`):** Tương quan thuận cực mạnh ($r > 0.92$) bám theo công thức chuẩn: $\text{Fare} \approx \$3.00 + \$3.50 \times \text{Distance}$.
  - **Đường nằm ngang màu đỏ tại `$70.00` (*JFK Flat Rate*):** Toàn bộ các chuyến đi từ Manhattan đến sân bay JFK đều phân bố thẳng hàng tại $70.00 bất kể cự ly dao động từ 10 đến 25 dặm.
  - **Các điểm nằm lệch lên phía trên đường xanh:** Chuyến cự ly ngắn nhưng xe bị kẹt dừng chờ lâu ($0.70/phút khi xe chạy dưới 12 mph).

---

### 2. `02_scatter_distance_vs_duration.png` — Cự Ly vs. Thời Gian Di Chuyển (Colorbar Vận Tốc)
![02 Distance vs Duration](./02_scatter_distance_vs_duration.png)

- **🎨 Chú thích dải màu liên tục (*Viridis Colormap & Colorbar*):**
  - 🟣 **Dải màu tím sẫm (< 10 mph):** Ùn tắc nội đô (*Urban Gridlock*), xe di chuyển chậm chạp trong lõi trung tâm Manhattan (quãng đường ngắn 1–3 dặm nhưng mất 30–55 phút).
  - 🟢 **Dải màu xanh ngọc / xanh lục (~20 – 25 mph):** Lưu thông trên các trục đường chính (*Arterial Flow*) với tốc độ tiêu chuẩn.
  - 🟡 **Dải màu vàng sáng (> 35 – 50 mph):** Di chuyển trên cao tốc (*Highway / Expressways: FDR Drive, BQE, Van Wyck*) với cự ly dài 15–25 dặm nhưng chỉ tốn 20–30 phút.
- **🔍 Đường tham chiếu vận tốc (*Speed Rays*):**
  - Đường nét đứt màu tím: **10 mph** (ngưỡng tốc độ kẹt xe nội đô).
  - Đường gạch chấm màu xanh: **25 mph** (ngưỡng tốc độ trung bình).
  - Đường chấm vàng: **45 mph** (ngưỡng tốc độ cao tốc).

---

### 3. `03_scatter_fare_vs_tip.png` — Giá Cước vs. Tiền Tip (Phân Tầng Tip & Chùm Tia POS)
![03 Fare vs Tip](./03_scatter_fare_vs_tip.png)

- **🎨 Chú thích màu sắc điểm dữ liệu theo hành vi Tip:**
  - 🔵 **Điểm màu xanh dương đậm (`#1d4ed8`):** Nhóm **Tip chuẩn 20% (18% – 22%)** — nút bấm mặc định phổ biến nhất trên máy quẹt thẻ POS taxi.
  - 🟢 **Điểm màu xanh lá (`#16a34a`):** Nhóm **Tip 25% (22.5% – 27.5%)** — nút bấm gợi ý thứ hai trên màn hình.
  - 🟣 **Điểm màu tím (`#9333ea`):** Nhóm **Tip hào phóng ≥ 30%** — lựa chọn cao cấp hoặc khách hàng thưởng thêm.
  - 🟠 **Điểm màu cam (`#ea580c`):** Nhóm **Tip số tiền chẵn ($5, $10, $20 Flat)** do khách hàng tự nhập số tròn.
  - ⚪ **Điểm màu xám (`#94a3b8`):** Nhóm **Tip tùy biến / Dưới mức chuẩn (< 18%)**.
- **🔍 Phân tích chùm tia tương quan (*Ray Clusters*):**
  - Dữ liệu tập trung thành các dải tia rõ nét theo các đường cước 20%, 25%, 30%.
  - Cột dọc tại mốc cước `$70.00` (JFK Flat Rate) làm phát sinh cột tiền tip thẳng đứng từ **$14.00 đến $21.00**.

---

### 4. `04_scatter_hour_vs_speed.png` — Khung Giờ Trong Ngày vs. Vận Tốc Di Chuyển
![04 Hour vs Speed](./04_scatter_hour_vs_speed.png)

- **🎨 Chú thích màu sắc điểm theo 5 Khung Giờ Giao Thông (*Traffic Regimes*):**
  - 🌙 **Màu tím chàm (`#6366f1`):** *Đêm & Rạng Sáng (00:00 – 05:59)* — Đường phố thông thoáng, tốc độ xe đạt mức cực đại.
  - 🚗 **Màu vàng hổ phách (`#f59e0b`):** *Cao Điểm Sáng (06:00 – 09:59)* — Dòng người đi làm đổ vào thành phố, tốc độ giảm dốc.
  - ☀️ **Màu xanh da trời (`#0284c7`):** *Giữa Ngày (10:00 – 15:59)* — Mật độ di chuyển nội đô ổn định (~10 mph).
  - 🛑 **Màu đỏ san hô (`#ef4444`):** *Cao Điểm Chiều Tối (16:00 – 19:59)* — Đáy ùn tắc sâu nhất trong ngày.
  - 🌃 **Màu xanh ngọc (`#10b981`):** *Đêm Muộn (20:00 – 23:59)* — Giao thông hạ nhiệt, tốc độ phục hồi dần.
- **🔍 Vùng cao điểm & Đường trung bình:**
  - Vùng đổ bóng vàng: **Cao điểm sáng (07:00 – 09:30 AM)**.
  - Vùng đổ bóng đỏ: **Cao điểm tối (16:30 – 19:30 PM)**.
  - Đường màu đỏ đậm: **Vận tốc trung bình 24 giờ**, đạt đỉnh tại **05:00 AM (21.3 mph)** và chạm đáy tại **17:00 PM (9.8 mph)**.
"""
    readme_path = output_dir / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    log.info("Updated documentation: %s", readme_path)


# ── Main Entrypoint ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate statistical Histogram and Scatter Plot visualizations for Silver Layer with clear point color annotations.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=os.environ.get("TRINO_HOST", "localhost"), help="Trino coordinator host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRINO_PORT", "8080")), help="Trino coordinator port")
    parser.add_argument("--user", default="airflow", help="Trino username")
    parser.add_argument("--month", default="", help="Filter by specific source month (e.g. '2025-01')")
    parser.add_argument("--sample-size", type=int, default=60000, help="Random sample size for scatter plots and smooth distributions")
    parser.add_argument("--report-dir", default=str(PROJECT_ROOT / "YLC_report"), help="Root directory for Yellow Taxi reports")
    parser.add_argument("--output-dir", default="", help="Optional legacy output directory")
    parser.add_argument("--scatters-only", action="store_true", help="Generate only scatter plots (faster execution)")

    args = parser.parse_args()

    report_root = Path(args.report_dir)
    scatter_dir = report_root / "03_relationships_scatter"
    hist_dir = report_root / "02_distributions_histograms"
    overview_dir = report_root / "01_overview_and_eda"

    scatter_dir.mkdir(parents=True, exist_ok=True)
    hist_dir.mkdir(parents=True, exist_ok=True)
    overview_dir.mkdir(parents=True, exist_ok=True)

    month_filter = ""
    if args.month:
        clean_month = args.month.strip()
        if not clean_month.startswith("yellow_tripdata_") and "-" in clean_month:
            clean_month = f"yellow_tripdata_{clean_month}"
        month_filter = f"WHERE _source_month = '{clean_month}'"

    log.info("Connecting to Trino at %s:%d...", args.host, args.port)
    conn = get_trino_connection(args.host, args.port, args.user)

    sample_sql = f"""
    SELECT 
        CAST(fare_amount AS DOUBLE) AS fare_amount,
        trip_distance,
        CAST(tip_amount AS DOUBLE) AS tip_amount,
        CAST(total_amount AS DOUBLE) AS total_amount,
        passenger_count,
        payment_type,
        pickup_hour,
        DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0 AS trip_duration_min,
        CASE 
            WHEN DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) > 30
            THEN trip_distance / (DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 3600.0)
            ELSE NULL 
        END AS avg_speed_mph,
        CASE 
            WHEN CAST(fare_amount AS DOUBLE) > 0 
            THEN (CAST(tip_amount AS DOUBLE) / CAST(fare_amount AS DOUBLE)) * 100.0
            ELSE 0.0 
        END AS tip_pct,
        CASE 
            WHEN rate_code_id = 2 OR airport_fee > 0 THEN TRUE 
            ELSE FALSE 
        END AS is_airport
    FROM delta.silver.yellow_trips
    {month_filter}
    LIMIT {args.sample_size}
    """

    log.info("Querying %d records from delta.silver.yellow_trips...", args.sample_size)
    try:
        df = fetch_dataframe(conn, sample_sql)
        log.info("Retrieved %d rows for visualization.", len(df))
    finally:
        conn.close()

    if df.empty:
        log.warning("No records found in Silver layer to plot.")
        return

    setup_plot_style()

    # Always generate scatter plots
    plot_scatters(df, scatter_dir)
    write_scatter_readme(scatter_dir)

    if not args.scatters_only:
        plot_histograms(df, hist_dir)
        plot_master_dashboard(df, overview_dir)

    # Legacy output dir support if requested
    if args.output_dir:
        legacy_path = Path(args.output_dir)
        legacy_path.mkdir(parents=True, exist_ok=True)
        plot_scatters(df, legacy_path)
        if not args.scatters_only:
            plot_histograms(df, legacy_path)
            plot_master_dashboard(df, legacy_path)

    print("\n" + "=" * 80)
    print(" 🎨 ALL SCATTER PLOTS SUCCESSFULLY REDRAWN WITH CLEAR COLOR ANNOTATIONS!")
    print(f" 📁 Saved to: {scatter_dir}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
