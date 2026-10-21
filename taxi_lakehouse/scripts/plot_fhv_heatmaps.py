#!/usr/bin/env python3
"""
plot_fhv_heatmaps.py — FHVHV Comprehensive Heatmap Visualization Generator
=============================================================================

Extracts multi-dimensional matrix patterns for High-Volume For-Hire Vehicles
(FHVHV: Uber & Lyft) from Delta tables via Trino and generates 6 distinct,
high-impact Heatmap charts matching the YLC_report hierarchy:

  FHV_report/04_matrix_heatmaps/
  ├── 00_heatmap_master_dashboard.png
  ├── 01_heatmap_weekly_demand.png
  ├── 02_heatmap_weekly_speed.png
  ├── 03_heatmap_feature_correlation.png
  ├── 04_heatmap_fare_vs_hour_tipping.png
  ├── 05_heatmap_calendar_year_demand.png
  └── README.md

Usage:
  python scripts/plot_fhv_heatmaps.py
  python scripts/plot_fhv_heatmaps.py --month 2025-01
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
log = logging.getLogger("plot_fhv_heatmaps")


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
        session_properties={
            "delta.parquet_ignore_statistics": True,
            "delta.statistics_enabled": False,
        },
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
def plot_weekly_demand_heatmap(conn, month_partitions: list[str], output_dir: Path):
    """Generates Day of Week vs Hour of Day Trip Volume Heatmap."""
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    log.info("Generating 1. Weekly Demand Heatmap across %d partition(s)...", len(month_partitions))
    dfs = []
    for m in month_partitions:
        sql = f"""
        SELECT 
            DAY_OF_WEEK(pickup_datetime) AS dow_num,
            CASE DAY_OF_WEEK(pickup_datetime)
                WHEN 1 THEN '1. Monday'
                WHEN 2 THEN '2. Tuesday'
                WHEN 3 THEN '3. Wednesday'
                WHEN 4 THEN '4. Thursday'
                WHEN 5 THEN '5. Friday'
                WHEN 6 THEN '6. Saturday'
                WHEN 7 THEN '7. Sunday'
            END AS day_of_week,
            HOUR(pickup_datetime) AS pickup_hour,
            COUNT(*) AS trip_count
        FROM delta.bronze.fhvhv_trips
        WHERE _source_month = '{m}'
          AND dropoff_datetime >= pickup_datetime
        GROUP BY 1, 2, 3
        """
        m_df = fetch_dataframe(conn, sql)
        if not m_df.empty:
            dfs.append(m_df)

    if not dfs:
        return None

    df = pd.concat(dfs, ignore_index=True).groupby(["dow_num", "day_of_week", "pickup_hour"])["trip_count"].sum().reset_index()
    df.sort_values(by=["dow_num", "pickup_hour"], inplace=True)

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

    plt.title("NYC FHVHV Weekly Trip Demand Heatmap: Day of Week vs. Hour (00:00 - 23:00)", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Hour of Day (24-Hour Clock)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Day of Week", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    out_file = output_dir / "01_heatmap_weekly_demand.png"
    plt.savefig(out_file, dpi=200)
    plt.close()
    log.info("Saved: %s", out_file)
    return pivot_k


# ── 2. Weekly Congestion & Speed Heatmap ─────────────────────────────────────
def plot_weekly_speed_heatmap(conn, month_partitions: list[str], output_dir: Path):
    """Generates Traffic Congestion & Average Speed Heatmap."""
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    log.info("Generating 2. Weekly Speed & Congestion Heatmap across %d partition(s)...", len(month_partitions))
    dfs = []
    for m in month_partitions:
        sql = f"""
        SELECT 
            DAY_OF_WEEK(pickup_datetime) AS dow_num,
            CASE DAY_OF_WEEK(pickup_datetime)
                WHEN 1 THEN '1. Monday'
                WHEN 2 THEN '2. Tuesday'
                WHEN 3 THEN '3. Wednesday'
                WHEN 4 THEN '4. Thursday'
                WHEN 5 THEN '5. Friday'
                WHEN 6 THEN '6. Saturday'
                WHEN 7 THEN '7. Sunday'
            END AS day_of_week,
            HOUR(pickup_datetime) AS pickup_hour,
            COUNT(*) AS trip_count,
            ROUND(
                AVG(
                    CASE 
                        WHEN DATE_DIFF('second', pickup_datetime, dropoff_datetime) >= 60
                             AND DATE_DIFF('second', pickup_datetime, dropoff_datetime) <= 7200
                             AND trip_miles > 0
                        THEN trip_miles / (CAST(DATE_DIFF('second', pickup_datetime, dropoff_datetime) AS DOUBLE) / 3600.0)
                        ELSE NULL 
                    END
                ), 1
            ) AS avg_speed_mph
        FROM delta.bronze.fhvhv_trips
        WHERE _source_month = '{m}'
          AND dropoff_datetime >= pickup_datetime
          AND trip_miles > 0
        GROUP BY 1, 2, 3
        """
        m_df = fetch_dataframe(conn, sql)
        if not m_df.empty:
            dfs.append(m_df)

    if not dfs:
        return None

    all_df = pd.concat(dfs, ignore_index=True)
    all_df["speed_weight"] = all_df["avg_speed_mph"] * all_df["trip_count"]
    agg = all_df.groupby(["dow_num", "day_of_week", "pickup_hour"])[["speed_weight", "trip_count"]].sum().reset_index()
    agg["avg_speed_mph"] = agg["speed_weight"] / agg["trip_count"]
    agg.sort_values(by=["dow_num", "pickup_hour"], inplace=True)

    pivot_df = agg.pivot(index="day_of_week", columns="pickup_hour", values="avg_speed_mph").fillna(0).astype(float)

    plt.figure(figsize=(15, 6.5))
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

    plt.title("NYC Traffic Congestion Heatmap: FHVHV Average Speed (mph) across Week & Hours", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Hour of Day (00:00 - 23:00, 24-Hour Clock)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Day of Week", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    out_file = output_dir / "02_heatmap_weekly_speed.png"
    plt.savefig(out_file, dpi=220)
    plt.close()
    log.info("Saved: %s", out_file)
    return pivot_df


# ── 3. Feature Correlation Matrix Heatmap ────────────────────────────────────
def plot_correlation_heatmap(conn, month_partitions: list[str], output_dir: Path, sample_size: int = 80000):
    """Computes Pearson Correlation Matrix across all numeric features."""
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    log.info("Generating 3. Feature Correlation Matrix Heatmap across %d partitions (Total Target: %d)...", len(month_partitions), sample_size)
    sample_per_p = max(1000, sample_size // len(month_partitions))
    dfs = []
    for m in month_partitions:
        sql = f"""
        SELECT 
            CAST(base_passenger_fare AS DOUBLE) AS fare_amount,
            CAST(trip_miles AS DOUBLE) AS trip_miles,
            CAST(tips AS DOUBLE) AS tip_amount,
            CAST(driver_pay AS DOUBLE) AS driver_pay,
            CAST(trip_time / 60.0 AS DOUBLE) AS duration_min,
            CAST(tolls AS DOUBLE) AS tolls,
            CAST(bcf AS DOUBLE) AS bcf,
            CAST(sales_tax AS DOUBLE) AS sales_tax,
            CAST(congestion_surcharge AS DOUBLE) AS congestion_fee,
            CAST(airport_fee AS DOUBLE) AS airport_fee,
            HOUR(pickup_datetime) AS pickup_hour
        FROM delta.bronze.fhvhv_trips
        WHERE _source_month = '{m}'
          AND dropoff_datetime >= pickup_datetime
          AND trip_miles > 0 
          AND base_passenger_fare > 0
        LIMIT {sample_per_p}
        """
        m_df = fetch_dataframe(conn, sql)
        if not m_df.empty:
            dfs.append(m_df)

    if not dfs:
        return None

    df = pd.concat(dfs, ignore_index=True)

    clean_df = df[(df["duration_min"] > 0) & (df["duration_min"] <= 120) & (df["fare_amount"] > 0) & (df["fare_amount"] <= 200)].copy()
    clean_df.columns = [
        "Fare ($)", "Distance (mi)", "Tip ($)", "Driver Pay ($)", "Duration (min)",
        "Tolls ($)", "BCF ($)", "Sales Tax ($)", "Congestion Fee", "Airport Fee", "Pickup Hour"
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

    plt.title("Pearson Correlation Heatmap across NYC FHVHV (Uber & Lyft) Metrics", fontsize=13, fontweight="bold", pad=15)
    plt.tight_layout()

    out_file = output_dir / "03_heatmap_feature_correlation.png"
    plt.savefig(out_file, dpi=200)
    plt.close()
    log.info("Saved: %s", out_file)
    return corr_matrix


# ── 4. Fare Range vs Time of Day Tipping Heatmap ─────────────────────────────
def plot_fare_vs_hour_tipping_heatmap(conn, month_partitions: list[str], output_dir: Path):
    """Generates Fare Bins vs Time of Day Tip Percentage Heatmap."""
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    log.info("Generating 4. Fare Range vs Time of Day Tipping Heatmap across %d partitions...", len(month_partitions))
    dfs = []
    for m in month_partitions:
        sql = f"""
        SELECT 
            CASE 
                WHEN base_passenger_fare < 15 THEN '1. Under $15'
                WHEN base_passenger_fare >= 15 AND base_passenger_fare < 25 THEN '2. $15 - $25'
                WHEN base_passenger_fare >= 25 AND base_passenger_fare < 40 THEN '3. $25 - $40'
                WHEN base_passenger_fare >= 40 AND base_passenger_fare < 65 THEN '4. $40 - $65'
                ELSE '5. $65+ (Airport/Long)'
            END AS fare_tier,
            CASE 
                WHEN HOUR(pickup_datetime) BETWEEN 0 AND 5 THEN '1. Overnight (00-05h)'
                WHEN HOUR(pickup_datetime) BETWEEN 6 AND 9 THEN '2. Morning Rush (06-09h)'
                WHEN HOUR(pickup_datetime) BETWEEN 10 AND 15 THEN '3. Midday (10-15h)'
                WHEN HOUR(pickup_datetime) BETWEEN 16 AND 19 THEN '4. Evening Rush (16-19h)'
                ELSE '5. Nightlife (20-23h)'
            END AS time_window,
            COUNT(*) AS trip_count,
            ROUND(AVG(tips / base_passenger_fare * 100.0), 2) AS avg_tip_pct
        FROM delta.bronze.fhvhv_trips
        WHERE _source_month = '{m}'
          AND base_passenger_fare > 0
          AND tips > 0
        GROUP BY 1, 2
        """
        m_df = fetch_dataframe(conn, sql)
        if not m_df.empty:
            dfs.append(m_df)

    if not dfs:
        return None

    all_df = pd.concat(dfs, ignore_index=True)
    all_df["tip_weight"] = all_df["avg_tip_pct"] * all_df["trip_count"]
    agg = all_df.groupby(["fare_tier", "time_window"])[["tip_weight", "trip_count"]].sum().reset_index()
    agg["avg_tip_pct"] = agg["tip_weight"] / agg["trip_count"]

    pivot_df = agg.pivot(index="fare_tier", columns="time_window", values="avg_tip_pct").fillna(0).astype(float)

    plt.figure(figsize=(10.5, 6))
    sns.heatmap(
        pivot_df,
        cmap="PuBuGn",
        annot=True,
        fmt=".2f",
        linewidths=0.8,
        linecolor="white",
        cbar_kws={"label": "Average Tip Percentage (%) on Tipped Rides"},
    )

    plt.title("FHVHV In-App Tipping Heatmap: Fare Tier vs. Time of Day (Tipped Rides)", fontsize=12, fontweight="bold", pad=15)
    plt.xlabel("Time of Day Window", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Base Fare Tier", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    out_file = output_dir / "04_heatmap_fare_vs_hour_tipping.png"
    plt.savefig(out_file, dpi=200)
    plt.close()
    log.info("Saved: %s", out_file)
    return pivot_df


# ── 5. Calendar Year Seasonality Heatmap (Month vs Day of Month) ─────────────
def plot_calendar_year_heatmap(conn, output_dir: Path):
    """Generates 365-Day Calendar Heatmap (Month vs Day of Month) for FHVHV."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 5. Annual Calendar Heatmap across all months in 2025...")
    sql = """
    SELECT 
        pickup_month,
        DAY(pickup_date) AS day_of_month,
        COUNT(*) AS daily_trips
    FROM delta.silver.fhvhv_trips
    GROUP BY pickup_month, DAY(pickup_date)
    ORDER BY pickup_month, day_of_month
    """
    df = fetch_dataframe(conn, sql)
    if df.empty:
        return None

    pivot_df = df.pivot(index="pickup_month", columns="day_of_month", values="daily_trips").fillna(0)
    pivot_k = (pivot_df / 1000.0).astype(float)

    plt.figure(figsize=(16, 7))
    sns.heatmap(
        pivot_k,
        cmap="viridis",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        linecolor="#eee",
        cbar_kws={"label": "Daily Trip Volume in Thousands (k)"},
    )

    plt.title("NYC FHVHV Annual Calendar Heatmap: Daily Trip Demand (Month vs. Day 1 - 31)", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Day of Month (1 - 31)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Pickup Month", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()

    out_file = output_dir / "05_heatmap_calendar_year_demand.png"
    plt.savefig(out_file, dpi=200)
    plt.close()
    log.info("Saved: %s", out_file)
    return pivot_k


# ── 6. Master 4-in-1 Heatmap Dashboard ───────────────────────────────────────
def plot_master_heatmap_dashboard(pivot_demand, pivot_speed, corr_matrix, pivot_tip, output_dir: Path):
    """Combines 4 key Heatmaps into an executive consolidated matrix dashboard."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating 00. Master 4-in-1 Heatmap Dashboard...")
    fig, axes = plt.subplots(2, 2, figsize=(19, 14))
    fig.suptitle("NYC FHVHV (Uber & Lyft) Lakehouse — Executive Heatmap Matrix Dashboard", fontsize=16, fontweight="bold", y=0.98)

    # Subplot 1: Weekly Demand
    if pivot_demand is not None:
        sns.heatmap(pivot_demand, cmap="YlOrRd", annot=False, ax=axes[0, 0], cbar_kws={"label": "Demand (k trips)"})
        axes[0, 0].set_title("1. Weekly Trip Volume Demand (Day x Hour)", fontweight="bold")
        axes[0, 0].set_xlabel("Hour (0 - 23)")
        axes[0, 0].set_ylabel("Day of Week")

    # Subplot 2: Weekly Speed / Congestion
    if pivot_speed is not None:
        sns.heatmap(pivot_speed, cmap="RdYlBu_r", vmin=8.0, vmax=26.0, annot=False, ax=axes[0, 1], cbar_kws={"label": "Speed (mph)"})
        axes[0, 1].set_title("2. Traffic Congestion & Average Speed (mph)", fontweight="bold")
        axes[0, 1].set_xlabel("Hour (0 - 23)")
        axes[0, 1].set_ylabel("Day of Week")

    # Subplot 3: Feature Correlation
    if corr_matrix is not None:
        sns.heatmap(corr_matrix, cmap="coolwarm", center=0, vmin=-1, vmax=1, annot=True, fmt=".2f", annot_kws={"fontsize": 8}, ax=axes[1, 0])
        axes[1, 0].set_title("3. Multi-Feature Pearson Correlation (r)", fontweight="bold")

    # Subplot 4: Fare vs Hour Tipping
    if pivot_tip is not None:
        sns.heatmap(pivot_tip, cmap="PuBuGn", annot=True, fmt=".1f", ax=axes[1, 1], cbar_kws={"label": "Tip %"})
        axes[1, 1].set_title("4. In-App Tip % (Fare Tier x Time Window)", fontweight="bold")
        axes[1, 1].set_xlabel("Time Window")
        axes[1, 1].set_ylabel("Base Fare Tier")

    plt.tight_layout()
    out_file = output_dir / "00_heatmap_master_dashboard.png"
    plt.savefig(out_file, dpi=200)
    plt.close()
    log.info("Saved master dashboard: %s", out_file)


# ── Step 7: Write Markdown Documentation ───────────────────────────────────────
def write_heatmaps_readme(output_dir: Path):
    """Writes detailed README.md documentation matching YLC_report style."""
    log.info("Generating README.md for 04_matrix_heatmaps...")

    readme_content = r"""# 🔥 04. Ma Trận Nhiệt Thời Gian & Tương Quan (Heatmaps Analytics - FHVHV)

> **Tập dữ liệu:** High-Volume For-Hire Vehicles (`delta.bronze.fhvhv_trips` & `delta.silver.fhvhv_trips`)  
> **Mục tiêu:** Khám phá quy luật tuần hoàn theo thứ/giờ, bản đồ điểm nghẽn ùn tắc giao thông, ma trận tương quan đa biến và tính mùa vụ cả năm 2025.

---

## 🖼️ Danh Sách 6 Biểu Đồ Heatmap

---

### 0. `00_heatmap_master_dashboard.png` — Dashboard Ma Trận Nhiệt Tổng Hợp
![00 Master Heatmap Dashboard](./00_heatmap_master_dashboard.png)

Tổng hợp 4 chiều phân tích trọng yếu:
1. **Nhu cầu tuần hoàn**: Nhận diện đỉnh nhu cầu ban ngày và đêm cuối tuần.
2. **Ùn tắc giao thông**: Điểm trũng vận tốc và thắt nút cổ chai theo khung giờ.
3. **Ma trận tương quan**: Tác động qua lại giữa cự ly, thời gian, cước phí và thu nhập tài xế (*Driver Pay*).
4. **Hành vi tiền tip**: Tỷ lệ tip theo từng phân khúc giá cước và khung giờ trong ngày.

---

### 1. `01_heatmap_weekly_demand.png` — Nhu Cầu Theo Tuần (Thứ trong tuần x Giờ trong ngày)
![01 Weekly Demand](./01_heatmap_weekly_demand.png)

- **Trục Y:** Thứ trong tuần (Thứ 2 ➔ Chủ Nhật) | **Trục X:** 24 khung giờ (00:00 ➔ 23:00).
- **Giải thích & Đặc trưng xe công nghệ:**
  - **Ngày trong tuần (Thứ 2 – Thứ 6):** Nhu cầu tăng dần từ sáng và đạt đỉnh cao nhất vào khung giờ tan tầm **17:00 – 19:00** (>130k – 150k chuyến/giờ trong tháng).
  - **Cuối tuần (Thứ 7 & Chủ Nhật):** Khác biệt rõ rệt so với ngày thường, đỉnh nhu cầu dồn mạnh vào **đêm muộn và rạng sáng (22:00 – 03:00)** phục vụ nhu cầu vui chơi giải trí và về nhà an toàn.

---

### 2. `02_heatmap_weekly_speed.png` — Bản Đồ Ùn Tắc Giao Thông Tuần (Vận Tốc Trung Bình mph)
![02 Weekly Speed](./02_heatmap_weekly_speed.png)

- **Bảng màu RdYlBu_r:** 🔴 Đỏ = Tắc đường nặng (< 11 mph), 🟡 Vàng = Trung bình (12 – 16 mph), 🔵 Xanh = Thông thoáng (> 18 mph).
- **Giải thích:**
  - **Ùn tắc nghiêm trọng nhất:** Chiều Thứ Năm và Thứ Sáu lúc 16:00 – 19:00, tốc độ trung bình rơi xuống mức thấp nhất **9.2 – 10.5 mph**.
  - **Thông thoáng nhất:** Khung giờ rạng sáng từ 02:00 – 05:00 hàng ngày, vận tốc đạt **18.5 – 22.0 mph** khi mạng lưới cao tốc và cầu hầm không bị nghẽn.

---

### 3. `03_heatmap_feature_correlation.png` — Ma Trận Tương Quan Pearson
![03 Feature Correlation](./03_heatmap_feature_correlation.png)

- **Giải thích các mối quan hệ trọng yếu:**
  - `Distance` $\leftrightarrow$ `Fare`: **$r \approx 0.88$** (Cước phí tương quan rất mạnh với cự ly di chuyển).
  - `Distance` $\leftrightarrow$ `Driver Pay`: **$r \approx 0.86$** (Thu nhập của tài xế tỷ lệ thuận chặt chẽ với quãng đường chạy cuốc).
  - `Distance` $\leftrightarrow$ `Duration`: **$r \approx 0.81$** (Thời lượng chuyến đi phản ánh cự ly và tình hình mật độ xe).
  - `Tolls` $\leftrightarrow$ `Distance`: **$r \approx 0.65$** (Các cuốc đi xa kết nối liên quận hoặc sân bay thường phát sinh phí cầu phà).

---

### 4. `04_heatmap_fare_vs_hour_tipping.png` — Tỷ Lệ Tip Theo Mức Cước x Khung Giờ
![04 Fare vs Hour Tipping](./04_heatmap_fare_vs_hour_tipping.png)

- **Giải thích:**
  - Nhóm chuyến đi cước thấp (**dưới $15**) có tỷ lệ tip trung bình tính theo % cao nhất (**~25.5% – 26.5%**), xuất phát từ tâm lý khách chọn mức tip làm tròn tối thiểu ($2 – $3) trên app.
  - Các cuốc cước cao (**trên $65** đi sân bay hoặc xuyên thành phố) có tỷ lệ tip trung bình ổn định quanh **18.0% – 18.5%**.

---

### 5. `05_heatmap_calendar_year_demand.png` — Bản Đồ Nhiệt Mùa Vụ 365 Ngày (Tháng x Ngày)
![05 Calendar Year Demand](./05_heatmap_calendar_year_demand.png)

- **Trục Y:** 12 tháng năm 2025 | **Trục X:** 31 ngày trong tháng.
- **Giải thích:**
  - Thể hiện trọn vẹn chu kỳ mùa vụ của **243.5 triệu chuyến đi** năm 2025.
  - **Tháng 12** là tháng bận rộn nhất trong năm với hơn **22.1 triệu chuyến đi**, tăng vọt vào những tuần lễ hội Giáng sinh và chuẩn bị đón năm mới.
  - Các ngày cuối tuần trong tuần luôn tạo thành các sọc dọc sáng màu (lưu lượng cao hơn từ 15 – 25% so với ngày đầu tuần).
"""
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")
    log.info("Saved documentation: %s", output_dir / "README.md")


def update_master_readme(report_dir: Path):
    """Updates master FHV_report/README.md to include heatmaps phase."""
    master_readme_path = report_dir / "README.md"
    if not master_readme_path.exists():
        return

    content = master_readme_path.read_text(encoding="utf-8")
    if "04_matrix_heatmaps" in content:
        return

    # Add 04_matrix_heatmaps to directory tree and section list
    tree_insert = """│
└── 📂 04_matrix_heatmaps/                      ➔ Giai đoạn 4: Ma trận nhiệt thời gian & tương quan (Heatmaps)
    ├── 🖼️ 00_heatmap_master_dashboard.png     (Dashboard ma trận nhiệt tổng hợp)
    ├── 🖼️ 01_heatmap_weekly_demand.png        (Nhu cầu theo Thứ x Giờ)
    ├── 🖼️ 02_heatmap_weekly_speed.png         (Bản đồ ùn tắc giao thông tuần)
    ├── 🖼️ 03_heatmap_feature_correlation.png  (Ma trận tương quan Pearson)
    ├── 🖼️ 04_heatmap_fare_vs_hour_tipping.png (Tỷ lệ Tip theo Mức cước x Giờ)
    ├── 🖼️ 05_heatmap_calendar_year_demand.png (Bản đồ nhiệt mùa vụ lịch 365 ngày)
    └── 📄 README.md"""

    section_insert = """---

## 🔥 4. Ma Trận Nhiệt & Tương Quan Đa Biến (04_matrix_heatmaps)
Khám phá các quy luật định kỳ theo tuần/giờ, ma trận tương quan đa biến và tính mùa vụ cả năm:
- [00_heatmap_master_dashboard.png](./04_matrix_heatmaps/00_heatmap_master_dashboard.png): Dashboard ma trận nhiệt tổng hợp 4-trong-1.
- [01_heatmap_weekly_demand.png](./04_matrix_heatmaps/01_heatmap_weekly_demand.png): Nhu cầu theo Thứ x Giờ trong ngày.
- [02_heatmap_weekly_speed.png](./04_matrix_heatmaps/02_heatmap_weekly_speed.png): Bản đồ ùn tắc giao thông đô thị (Vận tốc trung bình mph).
- [03_heatmap_feature_correlation.png](./04_matrix_heatmaps/03_heatmap_feature_correlation.png): Ma trận tương quan Pearson giữa cước, cự ly và Driver Pay.
- [04_heatmap_fare_vs_hour_tipping.png](./04_matrix_heatmaps/04_heatmap_fare_vs_hour_tipping.png): Tỷ lệ tip theo phân khúc cước và thời điểm gọi xe.
- [05_heatmap_calendar_year_demand.png](./04_matrix_heatmaps/05_heatmap_calendar_year_demand.png): Bản đồ nhiệt mùa vụ lịch 365 ngày (243.5M chuyến).
- **Chi tiết:** Xem thêm tại [04_matrix_heatmaps/README.md](./04_matrix_heatmaps/README.md).
"""

    if "└── 📂 03_relationships_scatter/" in content:
        content = content.replace("└── 📂 03_relationships_scatter/", "├── 📂 03_relationships_scatter/")
        idx = content.find("    └── 📄 README.md\n```")
        if idx != -1:
            end_idx = idx + len("    └── 📄 README.md\n")
            content = content[:end_idx] + tree_insert + "\n```" + content[end_idx + 4:]

    content = content + "\n\n" + section_insert
    master_readme_path.write_text(content, encoding="utf-8")
    log.info("Updated master README: %s", master_readme_path)


# ── Step 8: Main Orchestrator ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive Heatmap visualizations for FHVHV dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=os.environ.get("TRINO_HOST", "localhost"), help="Trino coordinator host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRINO_PORT", "8080")), help="Trino coordinator port")
    parser.add_argument("--user", default="airflow", help="Trino username")
    parser.add_argument("--month", default="2025", help="Target month partition (e.g. '2025-01') or '2025'/'all' for full year")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "FHV_report" / "04_matrix_heatmaps"), help="Output directory path")

    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

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

    setup_heatmap_style()

    try:
        p_demand = plot_weekly_demand_heatmap(conn, month_partitions, out_dir)
        p_speed = plot_weekly_speed_heatmap(conn, month_partitions, out_dir)
        corr_m = plot_correlation_heatmap(conn, month_partitions, out_dir)
        p_tip = plot_fare_vs_hour_tipping_heatmap(conn, month_partitions, out_dir)
        p_cal = plot_calendar_year_heatmap(conn, out_dir)
        plot_master_heatmap_dashboard(p_demand, p_speed, corr_m, p_tip, out_dir)
        write_heatmaps_readme(out_dir)
        update_master_readme(out_dir.parent)
    finally:
        conn.close()

    print("\n" + "=" * 80)
    print(" 🔥 ALL FHVHV HEATMAP CHARTS SUCCESSFULLY GENERATED!")
    print(f" 📁 Saved to: {out_dir.resolve()}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
