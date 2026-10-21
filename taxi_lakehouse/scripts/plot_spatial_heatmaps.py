#!/usr/bin/env python3
"""
plot_spatial_heatmaps.py — Spatial & Geographic Heatmap Visualizations
======================================================================

Extracts spatial mobility patterns from NYC Taxi Silver Delta tables
(`delta.silver.yellow_trips` and `delta.silver.dim_taxi_zones`) via Trino SQL
and produces high-resolution spatial heatmap charts and an interactive Leaflet HTML map.

Outputs in reports/figures/:
  1. spatial_borough_od_heatmap.png      : Borough-to-Borough OD Flow Matrix Heatmap
  2. spatial_zone_netflow_heatmap.png    : Supply-Demand Imbalance (Net Flow: Dropoffs - Pickups)
  3. spatial_zone_revenue_heatmap.png    : Top Zones Multi-Metric Revenue & Tip Heatmap
  4. spatial_airport_dispersal_heatmap.png : Airport (JFK & LGA) to Top Dropoff Zones Matrix
  5. interactive_spatial_heatmap.html    : Interactive Leaflet map with Zone Heatmap & Net-Flow markers

Usage:
  python scripts/plot_spatial_heatmaps.py
  python scripts/plot_spatial_heatmaps.py --month 2025-01
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("plot_spatial_heatmaps")

# Representative Geographic Coordinates (Centroids) for Key NYC Taxi Zones
NYC_ZONE_COORDINATES: dict[int, tuple[float, float]] = {
    132: (40.6413, -73.7781),  # JFK Airport
    138: (40.7769, -73.8740),  # LaGuardia Airport
    1: (40.6895, -74.1745),    # Newark Airport (EWR)
    236: (40.7781, -73.9554),  # Upper East Side North
    237: (40.7681, -73.9634),  # Upper East Side South
    161: (40.7553, -73.9784),  # Midtown Center
    162: (40.7533, -73.9724),  # Midtown East
    163: (40.7610, -73.9805),  # Midtown North
    186: (40.7505, -73.9910),  # Penn Station/Madison Sq West
    230: (40.7580, -73.9855),  # Times Sq/Theatre District
    142: (40.7753, -73.9818),  # Lincoln Square East
    141: (40.7628, -73.9587),  # Lenox Hill West
    234: (40.7408, -73.9896),  # Flatiron
    239: (40.7850, -73.9760),  # Upper West Side South
    238: (40.7930, -73.9710),  # Upper West Side North
    140: (40.7650, -73.9540),  # Lenox Hill East
    48: (40.7600, -73.9920),   # Clinton East
    68: (40.7480, -74.0010),   # East Chelsea
    246: (40.7520, -74.0040),  # West Chelsea/Hudson Yards
    79: (40.7280, -73.9870),   # East Village
    107: (40.7370, -73.9840),  # Gramercy
    170: (40.7450, -73.9780),  # Murray Hill
    233: (40.7490, -73.9680),  # UN/Turtle Bay South
    229: (40.7540, -73.9640),  # Sutton Place/Turtle Bay North
    143: (40.7780, -73.9880),  # Lincoln Square West
    144: (40.7200, -73.9980),  # Little Italy/Chinatown
    249: (40.7340, -74.0030),  # West Village
    158: (40.7380, -74.0080),  # Meatpacking District
    113: (40.7300, -73.9990),  # Greenwich Village North
    114: (40.7270, -74.0000),  # Greenwich Village South
    87: (40.7070, -74.0090),   # Financial District North
    88: (40.7040, -74.0130),   # Financial District South
    12: (40.7020, -74.0160),   # Battery Park
    231: (40.7190, -74.0100),  # TriBeCa/Civic Center
    255: (40.7180, -73.9620),  # Williamsburg (South)
    256: (40.7220, -73.9570),  # Williamsburg (North)
    80: (40.7150, -73.9400),   # East Williamsburg
    61: (40.6930, -73.9900),   # Crown Heights North
    66: (40.7000, -73.9870),   # DUMBO/Vinegar Hill
    33: (40.6900, -73.9950),   # Brooklyn Heights
    7: (40.7650, -73.9250),    # Astoria
    146: (40.7450, -73.9450),  # Long Island City/Queens Plaza
}


def get_trino_connection(host: str, port: int, user: str, catalog: str = "delta", schema: str = "silver"):
    """Establish Trino DBAPI connection."""
    try:
        import trino
    except ImportError:
        log.error("Missing 'trino' package. Install with: pip install trino pandas matplotlib seaborn folium")
        sys.exit(1)

    return trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog=catalog,
        schema=schema,
        http_scheme="http",
    )


def fetch_df(conn, sql: str):
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


def setup_matplotlib_style():
    """Sets clean styling for charts."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="white", font_scale=1.0)
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]


# ── Chart 1: Borough-to-Borough OD Flow Heatmap ──────────────────────────────
def plot_borough_od_heatmap(conn, month_filter: str, output_path: Path):
    """Generates Borough Origin-Destination Flow Matrix Heatmap."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Borough Origin-Destination Flow Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    SELECT 
        COALESCE(pz.borough, 'Unknown') AS pu_borough,
        COALESCE(dz.borough, 'Unknown') AS do_borough,
        COUNT(*) AS trip_count
    FROM delta.silver.yellow_trips t
    LEFT JOIN delta.silver.dim_taxi_zones pz ON t.pu_location_id = pz.location_id
    LEFT JOIN delta.silver.dim_taxi_zones dz ON t.do_location_id = dz.location_id
    {where_clause}
    GROUP BY pz.borough, dz.borough
    """
    df = fetch_df(conn, sql)
    if df.empty:
        return

    # Pivot into 2D Matrix (Millions of trips)
    pivot_df = df.pivot(index="pu_borough", columns="do_borough", values="trip_count").fillna(0)
    pivot_millions = pivot_df / 1_000_000.0

    # Sort boroughs by total traffic
    borough_order = pivot_df.sum(axis=1).sort_values(ascending=False).index.tolist()
    pivot_millions = pivot_millions.reindex(index=borough_order, columns=borough_order).fillna(0)

    plt.figure(figsize=(9, 7.5))
    sns.heatmap(
        pivot_millions,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        linewidths=1.2,
        linecolor="white",
        cbar_kws={"label": "Trip Volume (Millions)"},
    )

    plt.title("NYC Taxi Borough Origin-Destination Flow Heatmap", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Dropoff Borough (Destination)", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Pickup Borough (Origin)", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    log.info("Saved: %s", output_path)


# ── Chart 2: Supply-Demand Imbalance (Net Flow) Heatmap ───────────────────────
def plot_zone_netflow_heatmap(conn, month_filter: str, output_path: Path, limit: int = 25):
    """Generates Net Flow (Dropoffs - Pickups) Heatmap for Top Zones."""
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    log.info("Generating Zone Supply-Demand Imbalance (Net Flow) Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    WITH pickups AS (
        SELECT pu_location_id AS loc_id, COUNT(*) AS pickup_count
        FROM delta.silver.yellow_trips
        {where_clause}
        GROUP BY pu_location_id
    ),
    dropoffs AS (
        SELECT do_location_id AS loc_id, COUNT(*) AS dropoff_count
        FROM delta.silver.yellow_trips
        {where_clause}
        GROUP BY do_location_id
    )
    SELECT 
        z.location_id,
        z.borough,
        z.zone_name,
        COALESCE(p.pickup_count, 0) AS pickups,
        COALESCE(d.dropoff_count, 0) AS dropoffs,
        (COALESCE(d.dropoff_count, 0) - COALESCE(p.pickup_count, 0)) AS net_flow
    FROM delta.silver.dim_taxi_zones z
    LEFT JOIN pickups p ON z.location_id = p.loc_id
    LEFT JOIN dropoffs d ON z.location_id = d.loc_id
    WHERE COALESCE(p.pickup_count, 0) + COALESCE(d.dropoff_count, 0) > 100000
    ORDER BY (COALESCE(p.pickup_count, 0) + COALESCE(d.dropoff_count, 0)) DESC
    LIMIT {limit}
    """
    df = fetch_df(conn, sql)
    if df.empty:
        return

    df["label"] = df["borough"] + " - " + df["zone_name"]
    df = df.sort_values(by="net_flow", ascending=True)

    plt.figure(figsize=(11, 8.5))
    matrix_df = pd.DataFrame({
        "Net Flow (Dropoffs - Pickups)": df["net_flow"].values,
        "Total Pickups": df["pickups"].values,
        "Total Dropoffs": df["dropoffs"].values,
    }, index=df["label"].values)

    # Convert Net Flow to thousands for display
    norm_netflow = matrix_df[["Net Flow (Dropoffs - Pickups)"]] / 1_000.0

    sns.heatmap(
        norm_netflow,
        annot=True,
        fmt="+.1f",
        cmap="vlag",
        center=0,
        linewidths=1.0,
        linecolor="#eee",
        cbar_kws={"label": "Net Vehicle Flow in Thousands (+ Surplus, - Deficit)"},
    )

    plt.title(
        f"Top {limit} Taxi Zones: Vehicle Supply-Demand Imbalance (Net Flow Heatmap)\n(Red = Deficit/High Pickup Demand, Blue = Surplus/Excess Dropoffs)",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    plt.ylabel("Taxi Zone (Borough - Zone)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    log.info("Saved: %s", output_path)


# ── Chart 3: Multi-Metric Zone Economics Heatmap ─────────────────────────────
def plot_zone_revenue_heatmap(conn, month_filter: str, output_path: Path, limit: int = 20):
    """Generates normalized Multi-Metric Revenue & Tip Heatmap across Top Zones."""
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    log.info("Generating Multi-Metric Zone Economics Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    SELECT 
        COALESCE(z.borough, 'Unknown') || ' - ' || COALESCE(z.zone_name, 'Unknown') AS zone_label,
        COUNT(*) AS total_trips,
        ROUND(SUM(t.total_amount) / 1000000.0, 2) AS total_rev_millions,
        ROUND(AVG(CAST(t.total_amount AS DOUBLE)), 2) AS avg_fare_per_trip,
        ROUND(AVG(t.trip_distance), 2) AS avg_distance_miles,
        ROUND(
            AVG(
                CASE WHEN CAST(t.fare_amount AS DOUBLE) > 0 
                     THEN CAST(t.tip_amount AS DOUBLE) / CAST(t.fare_amount AS DOUBLE) * 100.0 
                     ELSE 0 END
            ), 2
        ) AS avg_tip_pct
    FROM delta.silver.yellow_trips t
    LEFT JOIN delta.silver.dim_taxi_zones z ON t.pu_location_id = z.location_id
    {where_clause}
    GROUP BY z.borough, z.zone_name
    ORDER BY SUM(t.total_amount) DESC
    LIMIT {limit}
    """
    df = fetch_df(conn, sql)
    if df.empty:
        return

    df = df.set_index("zone_label")
    display_df = df[["total_rev_millions", "avg_fare_per_trip", "avg_distance_miles", "avg_tip_pct"]].astype(float).copy()
    display_df.columns = ["Total Revenue ($M)", "Avg Fare ($)", "Avg Distance (mi)", "Avg Tip Rate (%)"]

    # Min-max normalization per column for visually harmonious heatmap coloring
    norm_df = (display_df - display_df.min()) / (display_df.max() - display_df.min())
    norm_df = norm_df.astype(float)

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        norm_df,
        annot=display_df.round(2),
        fmt=".2f",
        cmap="magma",
        linewidths=1.0,
        linecolor="#eee",
        cbar_kws={"label": "Relative Metric Intensity (Normalized 0 to 1)"},
    )

    plt.title(f"Top {limit} Taxi Zones by Total Revenue: Multi-Metric Economic Heatmap", fontsize=12, fontweight="bold", pad=15)
    plt.ylabel("Pickup Zone", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    log.info("Saved: %s", output_path)


# ── Chart 4: Airport Dispersal Corridor Matrix Heatmap ────────────────────────
def plot_airport_dispersal_heatmap(conn, month_filter: str, output_path: Path, limit: int = 15):
    """Generates Airport to Top Dropoff Zones flow matrix."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    log.info("Generating Airport Dispersal Corridor Heatmap...")
    where_clause = f"WHERE {month_filter}" if month_filter else ""
    airport_where = f"{where_clause} {'AND' if where_clause else 'WHERE'} (t.pu_location_id IN (132, 138))"

    sql = f"""
    SELECT 
        CASE t.pu_location_id 
            WHEN 132 THEN 'JFK Airport (Queens)' 
            WHEN 138 THEN 'LaGuardia Airport (Queens)' 
        END AS airport_origin,
        COALESCE(dz.borough, 'Unknown') || ' - ' || COALESCE(dz.zone_name, 'Unknown') AS dropoff_zone,
        COUNT(*) AS trip_count
    FROM delta.silver.yellow_trips t
    LEFT JOIN delta.silver.dim_taxi_zones dz ON t.do_location_id = dz.location_id
    {airport_where}
    GROUP BY t.pu_location_id, dz.borough, dz.zone_name
    """
    df = fetch_df(conn, sql)
    if df.empty:
        return

    # Pivot
    pivot_df = df.pivot(index="dropoff_zone", columns="airport_origin", values="trip_count").fillna(0)
    pivot_df["total_airport_dropoffs"] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values(by="total_airport_dropoffs", ascending=False).head(limit)
    pivot_df = pivot_df.drop(columns=["total_airport_dropoffs"])

    # Convert to thousands
    pivot_k = (pivot_df / 1_000.0).astype(float)

    plt.figure(figsize=(9, 7.5))
    sns.heatmap(
        pivot_k,
        annot=True,
        fmt=".1f",
        cmap="cividis",
        linewidths=1.2,
        linecolor="white",
        cbar_kws={"label": "Passenger Dropoffs (Thousands)"},
    )

    plt.title(f"Airport Dispersal Corridor: Top {limit} Destination Zones from JFK & LGA", fontsize=12, fontweight="bold", pad=15)
    plt.xlabel("Airport of Origin", fontsize=11, fontweight="bold", labelpad=8)
    plt.ylabel("Dropoff Destination Zone", fontsize=11, fontweight="bold", labelpad=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    log.info("Saved: %s", output_path)


# ── Chart 5: Interactive Geographic Leaflet Map (HTML) ────────────────────────
def generate_interactive_leaflet_map(conn, month_filter: str, output_path: Path):
    """Generates an interactive Leaflet/Folium spatial heatmap with Zone circles and Net-Flow markers."""
    try:
        import folium
        from folium.plugins import HeatMap
    except ImportError:
        log.warning("folium not installed. Skipping interactive HTML map.")
        return

    log.info("Building Interactive Leaflet Map (%s)...", output_path)
    where_clause = f"WHERE {month_filter}" if month_filter else ""

    sql = f"""
    WITH pickups AS (
        SELECT pu_location_id AS loc_id, COUNT(*) AS pickup_count, ROUND(AVG(CAST(total_amount AS DOUBLE)), 2) AS avg_fare
        FROM delta.silver.yellow_trips
        {where_clause}
        GROUP BY pu_location_id
    ),
    dropoffs AS (
        SELECT do_location_id AS loc_id, COUNT(*) AS dropoff_count
        FROM delta.silver.yellow_trips
        {where_clause}
        GROUP BY do_location_id
    )
    SELECT 
        z.location_id,
        z.borough,
        z.zone_name,
        COALESCE(p.pickup_count, 0) AS pickups,
        COALESCE(d.dropoff_count, 0) AS dropoffs,
        (COALESCE(d.dropoff_count, 0) - COALESCE(p.pickup_count, 0)) AS net_flow,
        COALESCE(p.avg_fare, 0.0) AS avg_fare
    FROM delta.silver.dim_taxi_zones z
    LEFT JOIN pickups p ON z.location_id = p.loc_id
    LEFT JOIN dropoffs d ON z.location_id = d.loc_id
    WHERE z.location_id IN ({','.join(map(str, NYC_ZONE_COORDINATES.keys()))})
    """
    df = fetch_df(conn, sql)
    if df.empty:
        return

    # Base Map centered at NYC (with multi-basemap support)
    m = folium.Map(location=[40.7484, -73.9857], zoom_start=12, tiles=None)

    # Add reliable, fast basemap layers
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>",
        name="CartoDB Light (Default)",
        subdomains="abcd",
        max_zoom=19,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>",
        name="CartoDB Dark (Night Mode)",
        subdomains="abcd",
        max_zoom=19,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ",
        name="Esri Streets",
        max_zoom=18,
    ).add_to(m)

    # Heatmap data points (lat, lon, weight)
    heat_data = []
    for _, row in df.iterrows():
        loc_id = int(row["location_id"])
        if loc_id in NYC_ZONE_COORDINATES:
            lat, lon = NYC_ZONE_COORDINATES[loc_id]
            weight = float(row["pickups"])
            heat_data.append([lat, lon, weight])

    HeatMap(heat_data, radius=22, blur=15, max_zoom=14, name="🔥 Pickup Density Heatmap").add_to(m)

    # Net-flow imbalance circles
    feature_group = folium.FeatureGroup(name="Zone Net Flow Markers")
    for _, row in df.iterrows():
        loc_id = int(row["location_id"])
        if loc_id in NYC_ZONE_COORDINATES:
            lat, lon = NYC_ZONE_COORDINATES[loc_id]
            net_flow = int(row["net_flow"])
            pickups = int(row["pickups"])
            dropoffs = int(row["dropoffs"])
            avg_fare = float(row["avg_fare"])
            zone_name = row["zone_name"]
            borough = row["borough"]

            color = "#d62728" if net_flow < 0 else "#2ca02c"
            status = f"Deficit (Pickups > Dropoffs by {-net_flow:,})" if net_flow < 0 else f"Surplus (Dropoffs > Pickups by {net_flow:,})"

            popup_html = f"""
            <div style="font-family: sans-serif; font-size: 13px; line-height: 1.4; width: 220px;">
                <h4 style="margin: 0 0 5px 0; color: #1c3d5a;">{borough}: {zone_name}</h4>
                <b>Status:</b> <span style="color:{color};">{status}</span><br>
                <b>Total Pickups:</b> {pickups:,}<br>
                <b>Total Dropoffs:</b> {dropoffs:,}<br>
                <b>Net Flow:</b> {net_flow:+,}<br>
                <b>Avg Fare:</b> ${avg_fare:.2f}
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=max(5, min(20, pickups / 150000)),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(feature_group)

    feature_group.add_to(m)
    folium.LayerControl().add_to(m)

    m.save(str(output_path))
    log.info("Saved Interactive Map: %s", output_path)


# ── Main Runner ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Generate Spatial & Geographic Heatmaps for NYC Taxi Silver Layer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=os.environ.get("TRINO_HOST", "localhost"), help="Trino coordinator host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TRINO_PORT", "8080")), help="Trino coordinator port")
    parser.add_argument("--user", default="airflow", help="Trino username")
    parser.add_argument("--month", default="", help="Filter by specific source month (e.g. '2025-01')")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "reports" / "figures"), help="Output directory")

    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    month_filter = ""
    if args.month:
        clean_m = args.month.strip()
        if not clean_m.startswith("yellow_tripdata_") and "-" in clean_m:
            clean_m = f"yellow_tripdata_{clean_m}"
        month_filter = f"_source_month = '{clean_m}'"

    log.info("Connecting to Trino at %s:%d...", args.host, args.port)
    conn = get_trino_connection(args.host, args.port, args.user)

    setup_matplotlib_style()

    try:
        # 1. Borough OD Matrix Heatmap
        plot_borough_od_heatmap(conn, month_filter, out_dir / "spatial_borough_od_heatmap.png")

        # 2. Zone Net-Flow Supply/Demand Imbalance Heatmap
        plot_zone_netflow_heatmap(conn, month_filter, out_dir / "spatial_zone_netflow_heatmap.png")

        # 3. Multi-Metric Zone Economics Heatmap
        plot_zone_revenue_heatmap(conn, month_filter, out_dir / "spatial_zone_revenue_heatmap.png")

        # 4. Airport Dispersal Corridor Matrix Heatmap
        plot_airport_dispersal_heatmap(conn, month_filter, out_dir / "spatial_airport_dispersal_heatmap.png")

        # 5. Interactive Leaflet HTML Map
        generate_interactive_leaflet_map(conn, month_filter, out_dir / "interactive_spatial_heatmap.html")

        print("\n" + "=" * 80)
        print(" 🗺️ ALL SPATIAL & GEOGRAPHIC HEATMAPS GENERATED!")
        print(f" 📁 Saved to: {out_dir}")
        print("=" * 80 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
