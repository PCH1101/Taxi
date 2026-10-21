#!/usr/bin/env python3
"""
plot_heatmaps.py — Comprehensive Heatmap Visualization Generator
====================================================================

Extracts multi-dimensional matrix patterns from NYC Taxi Silver Delta table via Trino
and generates 6 distinct, high-impact Heatmap charts:

Generated in reports/Heatmaps/ & reports/figures/:
  1. heatmap_weekly_demand.png        : Day of Week vs Hour of Day (Trip Demand Volume)
  2. heatmap_weekly_speed.png         : Day of Week vs Hour of Day (Congestion & Speed mph)
  3. heatmap_feature_correlation.png  : Pearson Correlation Matrix across all numeric features
  4. heatmap_fare_vs_hour_tipping.png : Fare Range vs Time of Day Tipping Rates (%)
  5. heatmap_borough_od_flow.png      : Pickup vs Dropoff Borough Mobility Matrix
  6. heatmap_calendar_year_demand.png : 365-Day Calendar Year Seasonality Heatmap
  7. heatmap_master_dashboard.png     : Consolidated 4-in-1 Analytical Heatmap Dashboard

Usage:
  python scripts/plot_heatmaps.py
  python scripts/plot_heatmaps.py --month 2025-01
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
log = logging.getLogger("plot_heatmaps")


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


def fetch_dataframe(conn, sql: str):
    """Execute SQL query and return a Pandas DataFrame."""
    import pandas as pd
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        cursor.close()


def setup_heatmap_style():
    """Sets clean styling for heatmaps."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="white", font_scale=1.0)
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]


# ── 1. Weekly Demand Heatmap (Day of Week vs Hour) ──────────────────────────
def plot_weekly_demand_heatmap(conn, month_filter: str, output_paths: list[Path]):
    """Generates Day of Week vs Hour of Day Trip Volume Heatmap."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 1. Weekly Demand Heatmap (Day of Week vs Hour)...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    SELECT 
        DAY_OF_WEEK(tpep_pickup_datetime) AS dow_num,
        CASE DAY_OF_WEEK(tpep_pickup_datetime)
            WHEN 1 THEN '1. Monday'
            WHEN 2 THEN '2. Tuesday'
            WHEN 3 THEN '3. Wednesday'
            WHEN 4 THEN '4. Thursday'
            WHEN 5 THEN '5. Friday'
            WHEN 6 THEN '6. Saturday'
            WHEN 7 THEN '7. Sunday'
        END AS day_of_week,
        pickup_hour,
        COUNT(*) AS trip_count
    FROM delta.silver.yellow_trips
    {where_clause}
    GROUP BY 1, 2, 3
    ORDER BY dow_num, pickup_hour
    """
    df = fetch_dataframe(conn, sql)
    if df.empty:
        return

    # Pivot: Day of Week on Y-axis, Hour on X-axis (Thousands of trips)
    pivot_df = df.pivot(index="day_of_week", columns="pickup_hour", values="trip_count").fillna(0)
    pivot_k = (pivot_df / 1000.0).astype(float)

    plt.figure(figsize=(14, 6))
    sns.heatmap(
        pivot_k,
        cmap="YlOrRd",
        annot=True,
        fmt=".0f",
        linewidths=0.6,
        linecolor="#f5f5f5",
        cbar_kws={"label": "Trip Volume in Thousands (k)"},
    )

    plt.title("Weekly Trip Demand Heatmap: Day of Week vs. Hour of Day (00:00 - 23:00)", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Hour of Day (24-Hour Clock)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Day of Week", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    for out in output_paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=200)
    plt.close()
    log.info("Saved: %s", output_paths[0])


# ── 2. Weekly Congestion & Speed Heatmap ─────────────────────────────────────
def plot_weekly_speed_heatmap(conn, month_filter: str, output_paths: list[Path]):
    """Generates Traffic Congestion & Average Speed Heatmap."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 2. Weekly Speed & Congestion Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""
    extra_filter = f"{where_clause} {'AND' if where_clause else 'WHERE'} trip_distance > 0"

    sql = f"""
    SELECT 
        DAY_OF_WEEK(tpep_pickup_datetime) AS dow_num,
        CASE DAY_OF_WEEK(tpep_pickup_datetime)
            WHEN 1 THEN '1. Monday'
            WHEN 2 THEN '2. Tuesday'
            WHEN 3 THEN '3. Wednesday'
            WHEN 4 THEN '4. Thursday'
            WHEN 5 THEN '5. Friday'
            WHEN 6 THEN '6. Saturday'
            WHEN 7 THEN '7. Sunday'
        END AS day_of_week,
        pickup_hour,
        ROUND(
            AVG(
                CASE 
                    WHEN DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) >= 60
                         AND DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) <= 7200
                    THEN trip_distance / (CAST(DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) AS DOUBLE) / 3600.0)
                    ELSE NULL 
                END
            ), 1
        ) AS avg_speed_mph
    FROM delta.silver.yellow_trips
    {extra_filter}
    GROUP BY 1, 2, 3
    ORDER BY dow_num, pickup_hour
    """
    df = fetch_dataframe(conn, sql)
    if df.empty:
        return

    pivot_df = df.pivot(index="day_of_week", columns="pickup_hour", values="avg_speed_mph").fillna(0).astype(float)

    plt.figure(figsize=(15, 6.5))
    # Red = Severe Congestion (< 10 mph), Yellow = Moderate, Blue/Green = Free-Flowing (> 20 mph)
    sns.heatmap(
        pivot_df,
        cmap="RdYlBu_r",
        vmin=8.0,
        vmax=26.0,
        annot=True,
        fmt=".1f",
        annot_kws={"fontsize": 9.5, "fontweight": "bold"},
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "Average Speed (mph) — [Red: Congestion, Blue: Fast Flow]"},
    )

    plt.title("NYC Traffic Congestion Heatmap: Average Speed (mph) across Week & Hours", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Hour of Day (00:00 - 23:00, 24-Hour Clock)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Day of Week", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    for out in output_paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=220)
    plt.close()
    log.info("Saved: %s", output_paths[0])


# ── 3. Feature Correlation Matrix Heatmap ────────────────────────────────────
def plot_correlation_heatmap(conn, month_filter: str, output_paths: list[Path], sample_size: int = 80000):
    """Computes Pearson Correlation Matrix across all numeric features."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 3. Feature Correlation Matrix Heatmap (Sample: %d)...", sample_size)
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    SELECT 
        CAST(fare_amount AS DOUBLE) AS fare_amount,
        trip_distance,
        CAST(tip_amount AS DOUBLE) AS tip_amount,
        CAST(total_amount AS DOUBLE) AS total_amount,
        CAST(tolls_amount AS DOUBLE) AS tolls_amount,
        CAST(extra AS DOUBLE) AS extra_charge,
        CAST(congestion_surcharge AS DOUBLE) AS congestion_fee,
        CAST(airport_fee AS DOUBLE) AS airport_fee,
        passenger_count,
        pickup_hour,
        DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0 AS duration_min
    FROM delta.silver.yellow_trips
    {where_clause}
    LIMIT {sample_size}
    """
    df = fetch_dataframe(conn, sql)
    if df.empty:
        return

    # Filter out extreme outliers for clean correlation
    clean_df = df[(df["duration_min"] > 0) & (df["duration_min"] <= 120) & (df["fare_amount"] > 0) & (df["fare_amount"] <= 200)]
    clean_df.columns = [
        "Fare ($)", "Distance (mi)", "Tip ($)", "Total ($)", "Tolls ($)",
        "Extra ($)", "Congestion Fee", "Airport Fee", "Passengers", "Pickup Hour", "Duration (min)"
    ]

    corr_matrix = clean_df.corr(method="pearson").astype(float)

    plt.figure(figsize=(10, 8.5))
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        vmin=-1,
        vmax=1,
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "Pearson Correlation Coefficient (r)"},
    )

    plt.title("Pearson Correlation Heatmap across NYC Taxi Metrics", fontsize=13, fontweight="bold", pad=15)
    plt.tight_layout()

    for out in output_paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=200)
    plt.close()
    log.info("Saved: %s", output_paths[0])


# ── 4. Fare Range vs Time of Day Tipping Heatmap ─────────────────────────────
def plot_fare_vs_hour_tipping_heatmap(conn, month_filter: str, output_paths: list[Path]):
    """Generates Fare Bins vs Time of Day Tip Percentage Heatmap."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 4. Fare Range vs Time of Day Tipping Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""
    cc_filter = f"{where_clause} {'AND' if where_clause else 'WHERE'} payment_type = 1 AND fare_amount > 0"

    sql = f"""
    SELECT 
        CASE 
            WHEN fare_amount < 10 THEN '1. Under $10'
            WHEN fare_amount >= 10 AND fare_amount < 20 THEN '2. $10 - $20'
            WHEN fare_amount >= 20 AND fare_amount < 40 THEN '3. $20 - $40'
            WHEN fare_amount >= 40 AND fare_amount < 70 THEN '4. $40 - $70'
            ELSE '5. $70+ (Airport/Long)'
        END AS fare_tier,
        CASE 
            WHEN pickup_hour BETWEEN 0 AND 5 THEN '1. Overnight (00-05h)'
            WHEN pickup_hour BETWEEN 6 AND 9 THEN '2. Morning Rush (06-09h)'
            WHEN pickup_hour BETWEEN 10 AND 15 THEN '3. Midday (10-15h)'
            WHEN pickup_hour BETWEEN 16 AND 19 THEN '4. Evening Rush (16-19h)'
            ELSE '5. Nightlife (20-23h)'
        END AS time_window,
        ROUND(AVG(CAST(tip_amount AS DOUBLE) / CAST(fare_amount AS DOUBLE) * 100.0), 2) AS avg_tip_pct
    FROM delta.silver.yellow_trips
    {cc_filter}
    GROUP BY 1, 2
    """
    df = fetch_dataframe(conn, sql)
    if df.empty:
        return

    pivot_df = df.pivot(index="fare_tier", columns="time_window", values="avg_tip_pct").fillna(0).astype(float)

    plt.figure(figsize=(9.5, 6))
    sns.heatmap(
        pivot_df,
        cmap="PuBuGn",
        annot=True,
        fmt=".2f",
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "Average Tip Percentage (%)"},
    )

    plt.title("Credit Card Tip Percentage Heatmap: Fare Tier vs. Time of Day", fontsize=12, fontweight="bold", pad=15)
    plt.xlabel("Time of Day Window", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Fare Tier", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    for out in output_paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=200)
    plt.close()
    log.info("Saved: %s", output_paths[0])


# ── 5. Calendar Year Seasonality Heatmap (Month vs Day of Month) ─────────────
def plot_calendar_year_heatmap(conn, month_filter: str, output_paths: list[Path]):
    """Generates 365-Day Calendar Heatmap (Month vs Day of Month)."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 5. Calendar Year Seasonality Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    SELECT 
        pickup_month,
        DAY(tpep_pickup_datetime) AS day_of_month,
        COUNT(*) AS daily_trips
    FROM delta.silver.yellow_trips
    {where_clause}
    GROUP BY pickup_month, DAY(tpep_pickup_datetime)
    ORDER BY pickup_month, day_of_month
    """
    df = fetch_dataframe(conn, sql)
    if df.empty:
        return

    # Pivot: Month on Y-axis, Day of month on X-axis (Thousands of trips)
    pivot_df = df.pivot(index="pickup_month", columns="day_of_month", values="daily_trips").fillna(0)
    pivot_k = (pivot_df / 1000.0).astype(float)

    plt.figure(figsize=(15, 6.5))
    sns.heatmap(
        pivot_k,
        cmap="viridis",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        linecolor="#eee",
        cbar_kws={"label": "Daily Trip Volume in Thousands (k)"},
    )

    plt.title("Annual Calendar Heatmap: Daily Trip Demand (Month vs. Day 1 - 31)", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Day of Month (1 - 31)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Pickup Month", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    for out in output_paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=200)
    plt.close()
    log.info("Saved: %s", output_paths[0])


# ── 6. Master 4-in-1 Heatmap Dashboard ───────────────────────────────────────
def plot_heatmap_master_dashboard(conn, month_filter: str, output_paths: list[Path]):
    """Consolidates 4 key Heatmaps into a unified executive dashboard."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 6. Master 4-in-1 Heatmap Dashboard...")
    fig, axes = plt.subplots(2, 2, figsize=(18, 13))
    fig.suptitle("NYC Taxi Lakehouse (Silver Layer) — Executive Heatmap Matrix Dashboard", fontsize=15, fontweight="bold", y=0.98)

    where_clause = f"WHERE {month_filter}" if month_filter else ""

    # Subplot 1: Weekly Demand
    sql_demand = f"""
    SELECT 
        CASE DAY_OF_WEEK(tpep_pickup_datetime)
            WHEN 1 THEN '1. Mon' WHEN 2 THEN '2. Tue' WHEN 3 THEN '3. Wed'
            WHEN 4 THEN '4. Thu' WHEN 5 THEN '5. Fri' WHEN 6 THEN '6. Sat' WHEN 7 THEN '7. Sun'
        END AS dow,
        pickup_hour,
        COUNT(*) / 1000.0 AS trips_k
    FROM delta.silver.yellow_trips
    {where_clause}
    GROUP BY 1, 2
    """
    df1 = fetch_dataframe(conn, sql_demand)
    if not df1.empty:
        p1 = df1.pivot(index="dow", columns="pickup_hour", values="trips_k").fillna(0).astype(float)
        sns.heatmap(p1, cmap="YlOrRd", ax=axes[0, 0], cbar_kws={"label": "Trips (k)"})
        axes[0, 0].set_title("1. Weekly Demand Profile (Hour vs. Day)", fontweight="bold")
        axes[0, 0].set_xlabel("Hour (0-23)")
        axes[0, 0].set_ylabel("Day of Week")

    # Subplot 2: Weekly Speed (Congestion)
    sql_speed = f"""
    SELECT 
        CASE DAY_OF_WEEK(tpep_pickup_datetime)
            WHEN 1 THEN '1. Mon' WHEN 2 THEN '2. Tue' WHEN 3 THEN '3. Wed'
            WHEN 4 THEN '4. Thu' WHEN 5 THEN '5. Fri' WHEN 6 THEN '6. Sat' WHEN 7 THEN '7. Sun'
        END AS dow,
        pickup_hour,
        ROUND(
            AVG(
                CASE 
                    WHEN DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) >= 60
                         AND DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) <= 7200
                    THEN trip_distance / (CAST(DATE_DIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime) AS DOUBLE) / 3600.0)
                    ELSE NULL 
                END
            ), 1
        ) AS speed_mph
    FROM delta.silver.yellow_trips
    {where_clause} {'AND' if where_clause else 'WHERE'} trip_distance > 0
    GROUP BY 1, 2
    """
    df2 = fetch_dataframe(conn, sql_speed)
    if not df2.empty:
        p2 = df2.pivot(index="dow", columns="pickup_hour", values="speed_mph").fillna(0).astype(float)
        sns.heatmap(p2, cmap="RdYlBu_r", vmin=8.0, vmax=26.0, ax=axes[0, 1], cbar_kws={"label": "Speed (mph)"})
        axes[0, 1].set_title("2. Traffic Congestion Map (Average Speed in mph)", fontweight="bold")
        axes[0, 1].set_xlabel("Hour (0-23)")
        axes[0, 1].set_ylabel("Day of Week")

    # Subplot 3: Borough OD Flow
    sql_od = f"""
    SELECT 
        COALESCE(pz.borough, 'Unknown') AS pu_borough,
        COALESCE(dz.borough, 'Unknown') AS do_borough,
        COUNT(*) / 1000000.0 AS trips_m
    FROM delta.silver.yellow_trips t
    LEFT JOIN delta.silver.dim_taxi_zones pz ON t.pu_location_id = pz.location_id
    LEFT JOIN delta.silver.dim_taxi_zones dz ON t.do_location_id = dz.location_id
    {where_clause}
    GROUP BY pz.borough, dz.borough
    """
    df3 = fetch_dataframe(conn, sql_od)
    if not df3.empty:
        p3 = df3.pivot(index="pu_borough", columns="do_borough", values="trips_m").fillna(0).astype(float)
        sns.heatmap(p3, cmap="magma", annot=True, fmt=".2f", ax=axes[1, 0], cbar_kws={"label": "Trips (Millions)"})
        axes[1, 0].set_title("3. Borough Origin-Destination Flow Matrix", fontweight="bold")
        axes[1, 0].set_xlabel("Dropoff Borough")
        axes[1, 0].set_ylabel("Pickup Borough")

    # Subplot 4: Tipping Rate by Fare & Time
    sql_tip = f"""
    SELECT 
        CASE 
            WHEN fare_amount < 15 THEN '1. Under $15'
            WHEN fare_amount >= 15 AND fare_amount < 30 THEN '2. $15 - $30'
            WHEN fare_amount >= 30 AND fare_amount < 60 THEN '3. $30 - $60'
            ELSE '4. $60+ (Airport/Long)'
        END AS fare_tier,
        CASE 
            WHEN pickup_hour BETWEEN 0 AND 5 THEN 'Overnight'
            WHEN pickup_hour BETWEEN 6 AND 9 THEN 'Morning Rush'
            WHEN pickup_hour BETWEEN 10 AND 15 THEN 'Midday'
            WHEN pickup_hour BETWEEN 16 AND 19 THEN 'Evening Rush'
            ELSE 'Nightlife'
        END AS time_win,
        ROUND(AVG(CAST(tip_amount AS DOUBLE) / CAST(fare_amount AS DOUBLE) * 100.0), 2) AS avg_tip_pct
    FROM delta.silver.yellow_trips
    {where_clause} {'AND' if where_clause else 'WHERE'} payment_type = 1 AND fare_amount > 0
    GROUP BY 1, 2
    """
    df4 = fetch_dataframe(conn, sql_tip)
    if not df4.empty:
        p4 = df4.pivot(index="fare_tier", columns="time_win", values="avg_tip_pct").fillna(0).astype(float)
        sns.heatmap(p4, cmap="PuBuGn", annot=True, fmt=".1f", ax=axes[1, 1], cbar_kws={"label": "Tip %"})
        axes[1, 1].set_title("4. Credit Card Tip % (Fare Tier vs. Time Window)", fontweight="bold")
        axes[1, 1].set_xlabel("Time Window")
        axes[1, 1].set_ylabel("Fare Tier")

    plt.tight_layout()
    for out in output_paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out, dpi=200)
    plt.close()
    log.info("Saved master dashboard: %s", output_paths[0])


# ── Main Runner ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive multi-dimensional Heatmaps for NYC Taxi Silver layer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=os.environ.get("TRINO_HOST", "localhost"), help="Trino coordinator host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRINO_PORT", "8080")), help="Trino coordinator port")
    parser.add_argument("--user", default="airflow", help="Trino username")
    parser.add_argument("--month", default="", help="Filter by specific source month (e.g. '2025-01')")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "reports" / "Heatmaps"), help="Primary output directory")

    args = parser.parse_args()

    primary_out = Path(args.output_dir)
    secondary_out = PROJECT_ROOT / "reports" / "figures"
    for d in [primary_out, secondary_out]:
        d.mkdir(parents=True, exist_ok=True)

    month_filter = ""
    if args.month:
        clean_m = args.month.strip()
        if not clean_m.startswith("yellow_tripdata_") and "-" in clean_m:
            clean_m = f"yellow_tripdata_{clean_m}"
        month_filter = f"_source_month = '{clean_m}'"

    log.info("Connecting to Trino at %s:%d...", args.host, args.port)
    conn = get_trino_connection(args.host, args.port, args.user)

    setup_heatmap_style()

    try:
        # 1. Weekly Demand Heatmap
        plot_weekly_demand_heatmap(
            conn, month_filter,
            [primary_out / "heatmap_weekly_demand.png", secondary_out / "heatmap_weekly_demand.png"],
        )

        # 2. Weekly Speed & Congestion Heatmap
        plot_weekly_speed_heatmap(
            conn, month_filter,
            [primary_out / "heatmap_weekly_speed.png", secondary_out / "heatmap_weekly_speed.png"],
        )

        # 3. Feature Correlation Matrix Heatmap
        plot_correlation_heatmap(
            conn, month_filter,
            [primary_out / "heatmap_feature_correlation.png", secondary_out / "heatmap_feature_correlation.png"],
        )

        # 4. Fare Range vs Time of Day Tipping Heatmap
        plot_fare_vs_hour_tipping_heatmap(
            conn, month_filter,
            [primary_out / "heatmap_fare_vs_hour_tipping.png", secondary_out / "heatmap_fare_vs_hour_tipping.png"],
        )

        # 5. Calendar Year Seasonality Heatmap
        plot_calendar_year_heatmap(
            conn, month_filter,
            [primary_out / "heatmap_calendar_year_demand.png", secondary_out / "heatmap_calendar_year_demand.png"],
        )

        # 6. Master 4-in-1 Heatmap Dashboard
        plot_heatmap_master_dashboard(
            conn, month_filter,
            [primary_out / "heatmap_master_dashboard.png", secondary_out / "heatmap_master_dashboard.png"],
        )

        print("\n" + "=" * 80)
        print(" 🔥 ALL HEATMAP CHARTS SUCCESSFULLY GENERATED!")
        print(f" 📁 Saved to: {primary_out} and {secondary_out}")
        print("=" * 80 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
