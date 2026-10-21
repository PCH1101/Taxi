#!/usr/bin/env python3
"""
plot_bar_hourly_demand.py — Bar Chart + Line Chart: 24-Hour Demand & Fare Distribution
========================================================================

Extracts 24-hour temporal demand from NYC Taxi Silver Delta table via Trino SQL
and generates an annotated English chart highlighting the classic Bimodal Rush Hours pattern.

Output:
  reports/figures/bimodal_rush_hours.png
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("plot_bar_hourly_demand")


def get_trino_connection(host: str, port: int, user: str, catalog: str = "delta", schema: str = "silver"):
    """Connect to Trino SQL engine."""
    try:
        import trino
    except ImportError:
        log.error("trino package missing. Install via: pip install trino pandas matplotlib seaborn")
        sys.exit(1)

    return trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog=catalog,
        schema=schema,
        http_scheme="http",
    )


def fetch_hourly_data(conn, month_filter: str = ""):
    """Queries hourly trip counts and metrics."""
    import pandas as pd

    where_clause = f"WHERE {month_filter}" if month_filter else ""
    sql = f"""
    SELECT 
        pickup_hour,
        COUNT(*) AS trip_count,
        ROUND(AVG(CAST(total_amount AS DOUBLE)), 2) AS avg_total_fare,
        ROUND(AVG(trip_distance), 2) AS avg_distance,
        ROUND(AVG(DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0), 1) AS avg_duration_min
    FROM delta.silver.yellow_trips
    {where_clause}
    GROUP BY pickup_hour
    ORDER BY pickup_hour
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        cursor.close()


def plot_bimodal_chart(df, output_path: Path):
    """Draws an English annotated chart visualizing Bimodal Rush Hours."""
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns

    sns.set_theme(style="whitegrid", font_scale=1.05)
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

    fig, ax1 = plt.subplots(figsize=(12, 6.5))

    hours = df["pickup_hour"].values
    trips_millions = df["trip_count"].values / 1_000_000.0  # Convert to Millions

    # Bar chart for trip volume
    bars = ax1.bar(
        hours,
        trips_millions,
        color="#2b5c8f",
        alpha=0.78,
        width=0.72,
        edgecolor="#1c3d5a",
        linewidth=1.2,
        label="Trip Volume (Millions)",
    )

    # Highlight Peak Bars
    # Morning peak (8-9 AM) and Evening peak (17-19 PM)
    morning_peak_hr = 9
    evening_peak_hr = 18

    # Smooth spline / curve overlay
    try:
        from scipy.interpolate import make_interp_spline
        x_smooth = np.linspace(hours.min(), hours.max(), 300)
        spline = make_interp_spline(hours, trips_millions, k=3)
        y_smooth = spline(x_smooth)
        ax1.plot(x_smooth, y_smooth, color="#0f2b48", linewidth=2.5, linestyle="-", label="Demand Density Curve")
    except Exception:
        ax1.plot(hours, trips_millions, color="#0f2b48", linewidth=2.5, marker="o", label="Demand Density Curve")

    # Dual axis for Average Total Fare ($)
    ax2 = ax1.twinx()
    ax2.plot(
        hours,
        df["avg_total_fare"],
        color="#d95f02",
        marker="s",
        markersize=6,
        linewidth=2.2,
        linestyle="--",
        label="Avg Total Fare ($)",
    )
    ax2.set_ylabel("Average Total Fare ($)", color="#d95f02", fontsize=12, fontweight="bold", labelpad=10)
    ax2.tick_params(axis="y", labelcolor="#d95f02")
    ax2.grid(False)

    # Annotations & Callouts in English
    # 1. Morning Peak Callout
    morning_y = trips_millions[morning_peak_hr]
    ax1.annotate(
        "Peak 1: Morning Commute\n(08:00 - 09:00 AM)\n~1.5M trips",
        xy=(morning_peak_hr, morning_y),
        xytext=(morning_peak_hr - 3.5, morning_y + 0.55),
        arrowprops=dict(facecolor="#d62728", edgecolor="#d62728", arrowstyle="->", lw=2),
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff2f2", ec="#d62728", lw=1.5),
        fontsize=10,
        fontweight="bold",
        ha="center",
    )

    # 2. Evening Peak Callout
    evening_y = trips_millions[evening_peak_hr]
    ax1.annotate(
        "Peak 2: Evening Rush & Dinner\n(17:00 - 19:00 PM)\n~2.56M trips (Highest Peak)",
        xy=(evening_peak_hr, evening_y),
        xytext=(evening_peak_hr - 1.5, evening_y + 0.5),
        arrowprops=dict(facecolor="#d62728", edgecolor="#d62728", arrowstyle="->", lw=2),
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff2f2", ec="#d62728", lw=1.5),
        fontsize=10,
        fontweight="bold",
        ha="center",
    )

    # 3. Overnight Valley Callout
    valley_y = trips_millions[4]
    ax1.annotate(
        "Overnight Valley\n(02:00 - 05:00 AM)\nLowest Demand (~166k trips)",
        xy=(4, valley_y),
        xytext=(4, valley_y + 0.8),
        arrowprops=dict(facecolor="#555", edgecolor="#555", arrowstyle="->", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.4", fc="#f8f9fa", ec="#999", lw=1),
        fontsize=9,
        ha="center",
    )

    # Shaded Rush Hour Bands
    ax1.axvspan(7.5, 9.5, color="#ff7f0e", alpha=0.12, label="Morning Rush Band")
    ax1.axvspan(16.5, 19.5, color="#d62728", alpha=0.12, label="Evening Rush Band")

    # Titles and Axes
    ax1.set_title(
        "NYC Taxi Demand across 24 Hours: Classic Bimodal Rush Hours Distribution",
        fontsize=14,
        fontweight="bold",
        pad=18,
    )
    ax1.set_xlabel("Hour of Day (0 - 23, 24-Hour Clock)", fontsize=12, fontweight="bold", labelpad=8)
    ax1.set_ylabel("Total Trips (Millions)", color="#2b5c8f", fontsize=12, fontweight="bold", labelpad=10)
    ax1.tick_params(axis="y", labelcolor="#2b5c8f")
    ax1.set_xticks(range(0, 24))
    ax1.set_ylim(0, max(trips_millions) * 1.35)

    # Combined Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True, facecolor="white", edgecolor="#ccc", fontsize=9.5)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=220)
    plt.close()
    log.info("Successfully generated bimodal chart at: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate English Bimodal Rush Hours visualization.")
    parser.add_argument("--host", default=os.environ.get("TRINO_HOST", "localhost"), help="Trino host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRINO_PORT", "8080")), help="Trino port")
    parser.add_argument("--user", default="airflow", help="Trino user")
    parser.add_argument("--month", default="", help="Filter by month (e.g. 2025-01)")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "figures" / "bimodal_rush_hours.png"),
        help="Target output image path",
    )

    args = parser.parse_args()

    month_filter = ""
    if args.month:
        clean_m = args.month.strip()
        if not clean_m.startswith("yellow_tripdata_") and "-" in clean_m:
            clean_m = f"yellow_tripdata_{clean_m}"
        month_filter = f"_source_month = '{clean_m}'"

    log.info("Connecting to Trino at %s:%d...", args.host, args.port)
    conn = get_trino_connection(args.host, args.port, args.user)

    try:
        log.info("Querying 24-hour aggregation from delta.silver.yellow_trips...")
        df = fetch_hourly_data(conn, month_filter)
        log.info("Fetched hourly statistics (%d rows).", len(df))
        plot_bimodal_chart(df, Path(args.output))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
