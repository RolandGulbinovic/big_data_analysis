import os
import time
import csv
import threading
from math import radians, sin, cos, sqrt, atan2
from multiprocessing import Pool, Process, Manager

import psutil

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

import geopandas as gpd
import contextily as ctx
from shapely.geometry import LineString

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

NUM_CORES = 11

# Cluster colors
CLUSTER_COLORS = {
    0: "#1f77b4",  # blue
    1: "#2ca02c",  # green
    2: "#d62728",  # red
}


# Ram Usage tracking (System-wide)
_memory_log = []

def _memory_tracker_system(interval=0.5):
    while True:
        used_mb = psutil.virtual_memory().used / 1024**2
        _memory_log.append((time.time(), used_mb))
        time.sleep(interval)

def start_memory_tracker_thread(interval=0.5):
    t = threading.Thread(target=_memory_tracker_system,
                         args=(interval,),
                         daemon=True)
    t.start()
    return t

def save_memory_log(path="output/memory_log.csv"):
    if not _memory_log:
        print("No memory data recorded.")
        return
    df = pd.DataFrame(_memory_log, columns=["timestamp","used_mb"])
    df["timestamp"] -= df["timestamp"].iloc[0]
    df.to_csv(path, index=False)
    print(f"Memory log saved to {path}")

def plot_memory_usage(log_path="output/memory_log.csv",
                      output_path="output/ram_usage.png"):
    df = pd.read_csv(log_path)
    plt.figure(figsize=(10,5))
    plt.plot(df["timestamp"], df["used_mb"])
    plt.xlabel("Time (s)")
    plt.ylabel("System RAM Used (MB)")
    plt.title("RAM Usage Over Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"RAM usage plot saved to {output_path}")

# Remove invalid coordinates
def is_valid_coordinate(lat, lng):
    return -90 <= lat <= 90 and -180 <= lng <= 180

# calculate haversine distance
def haversine(row):
    lat1, lon1, lat2, lon2 = map(radians, [row['start_lat'], row['start_lng'], row['end_lat'], row['end_lng']])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1-a))

# Read and process the files by calculating haversine distance and getting rid of invalid/outliers

def chunkify(lst, n_chunks):
    k, m = divmod(len(lst), n_chunks)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n_chunks)]

def process_file_chunk(file_chunk):
    all_dfs = []
    total_removed_invalid = 0
    total_removed_outliers = 0

    for file_path in file_chunk:
        df, removed_invalid, removed_outliers = process_file(file_path)
        all_dfs.append(df)
        total_removed_invalid += removed_invalid
        total_removed_outliers += removed_outliers

    return pd.concat(all_dfs, ignore_index=True), total_removed_invalid, total_removed_outliers


def process_file(file_path):
    df = pd.read_csv(file_path, parse_dates=['started_at', 'ended_at'])
    initial_len = len(df)
    df = df.dropna(subset=['start_lat', 'start_lng', 'end_lat', 'end_lng'])
    df = df[df.apply(lambda r: is_valid_coordinate(r['start_lat'], r['start_lng']) and
                               is_valid_coordinate(r['end_lat'], r['end_lng']), axis=1)]
    removed_invalid = initial_len - len(df)

    df['duration_min'] = (df['ended_at'] - df['started_at']).dt.total_seconds() / 60
    df['distance_km'] = df.apply(haversine, axis=1)
    df['day_of_week'] = df['started_at'].dt.day_name()

    clean_len = len(df)
    df = df[(df['duration_min'] > 1) & (df['duration_min'] < 240) &
            (df['distance_km'] > 0.1) & (df['distance_km'] < 50)]
    removed_outliers = clean_len - len(df)

    return df, removed_invalid, removed_outliers

def calculate_speed(df):
    df['speed_kmh'] = df['distance_km'] / (df['duration_min'] / 60)
    return df

# Calculate different statistics. This is done sequentially because its faster
def run_sequential_analyses(df, top_n=10):
    top_stations = df['start_station_name'].value_counts().head(top_n)

    df['duration_per_km'] = df['duration_min'] / df['distance_km']
    filtered = df[df['duration_per_km'] < 60]
    top_paths = filtered.groupby(['start_station_name', 'end_station_name']).agg(
        avg_ratio=('duration_per_km', 'mean'),
        count=('ride_id', 'count')
    ).sort_values('avg_ratio', ascending=False).head(top_n)

    weekday_stats = df.groupby('day_of_week').agg(
        avg_duration=('duration_min', 'mean'),
        avg_distance=('distance_km', 'mean'),
        avg_speed=('speed_kmh', 'mean'),
        trip_count=('ride_id', 'count')
    ).sort_values('trip_count', ascending=False)

    df['route'] = df['start_station_name'] + " → " + df['end_station_name']
    top_routes = df['route'].value_counts().head(top_n)

    return top_stations, top_paths, weekday_stats, top_routes

# Plotting
def plot_stat_by_day(data, column, y_label, output_path, agg_func='mean'):
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if agg_func == 'mean':
        stats = data.groupby("day_of_week")[column].mean().reindex(weekday_order)
    elif agg_func == 'count':
        stats = data['day_of_week'].value_counts().reindex(weekday_order)
    elif agg_func == 'value':
        stats = data[column].reindex(weekday_order)
    else:
        raise ValueError("agg_func must be 'mean', 'count', or 'value'")
    stats = stats.transpose()
    plt.figure(figsize=(10, 5))
    sns.barplot(x=stats.index, y=stats.values)
    plt.title(f"{column.replace('_', ' ').title()} by Day of the Week")
    plt.xlabel("Day of the Week")
    plt.ylabel(y_label)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Saved: {output_path}")
    plt.close()

# K-means clustering for starting station - one day
def cluster_one_day_volume(day_df, n_clusters=3):
    grouped = day_df.groupby(['start_station_name', 'start_lat', 'start_lng']) \
                    .size().reset_index(name='ride_count')

    coords = grouped[['start_lat', 'start_lng', 'ride_count']].to_numpy()
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(coords)

    grouped["cluster"] = kmeans.labels_
    return grouped, kmeans.cluster_centers_

# Run cluster_one_day() for all days of the week (in parallel)
def parallel_cluster_by_volume_all_days(df, n_clusters=3, processes=7):
    grouped_days = [df[df["day_of_week"] == day] for day in df["day_of_week"].unique()]
    with Pool(processes=processes) as pool:
        results = pool.starmap(cluster_one_day_volume, [(day_df, n_clusters) for day_df in grouped_days])
    return results

# Plot the clutsers on a real map
def plot_volume_clusters_with_map(clustered_df, centers, day_name, output_path):
    gdf = gpd.GeoDataFrame(
        clustered_df,
        geometry=gpd.points_from_xy(clustered_df["start_lng"], clustered_df["start_lat"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    center_gdf = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(centers[:, 1], centers[:, 0]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    # Use the fixed color palette
    gdf["color"] = gdf["cluster"].map(CLUSTER_COLORS)

    fig, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(ax=ax, color=gdf["color"], markersize=gdf["ride_count"] / 10)
    center_gdf.plot(ax=ax, color="black", marker="x", markersize=80)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_title(f"Clusters by Station Ride Volume — {day_name}")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()

# Clustering the count of trips for each station.
def cluster_and_plot_volume_one_day(day_df, day_name, n_clusters=3, output_dir="output"):
    grouped = day_df.groupby(['start_station_name', 'start_lat', 'start_lng']) \
        .size().reset_index(name='ride_count')

    coords = grouped[['start_lat', 'start_lng', 'ride_count']].to_numpy()
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(coords)
    grouped["cluster"] = kmeans.labels_

    # Create GeoDataFrames
    gdf = gpd.GeoDataFrame(
        grouped,
        geometry=gpd.points_from_xy(grouped["start_lng"], grouped["start_lat"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    center_gdf = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(kmeans.cluster_centers_[:, 1], kmeans.cluster_centers_[:, 0]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    gdf["color"] = gdf["cluster"].map(CLUSTER_COLORS)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(ax=ax, color=gdf["color"], markersize=gdf["ride_count"] / 10)
    center_gdf.plot(ax=ax, color="black", marker="x", markersize=80)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_title(f"Clusters by Station Ride Volume — {day_name}")
    plt.axis("off")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"volume_cluster_{day_name}.png")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()

    return (day_name, kmeans.cluster_centers_)


def parallel_cluster_volume_and_plot(df, n_clusters=3, processes=7):
    grouped_days = [(df[df["day_of_week"] == day], day) for day in df["day_of_week"].unique()]
    with Pool(processes=processes) as pool:
        results = pool.starmap(
            cluster_and_plot_volume_one_day,
            [(day_df, day, n_clusters, "output") for day_df, day in grouped_days]
        )
    return results


# Different approach to clustering - clustering full trips instead of just the starting positions
def cluster_full_trip_routes(df, day_name, n_clusters=5, output_dir="output"):
    df = df.copy()

    # Select and scale coordinates
    coords = df[["start_lat", "start_lng", "end_lat", "end_lng"]].to_numpy()
    coords_scaled = StandardScaler().fit_transform(coords)

    # Fit KMeans
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    df["trip_cluster"] = kmeans.fit_predict(coords_scaled)

    # Create LineStrings for plotting
    df["geometry"] = df.apply(
        lambda r: LineString([(r["start_lng"], r["start_lat"]), (r["end_lng"], r["end_lat"])]),
        axis=1
    )
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326").to_crs(epsg=3857)

    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, f"trip_clusters_{day_name}.png")

    fig, ax = plt.subplots(figsize=(6, 8))  # Narrower, to match station clusters
    gdf.plot(ax=ax, column="trip_cluster", cmap="tab10", linewidth=1, alpha=0.6, legend=False)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_title(f"Trip Route Clusters — {day_name}", fontsize=12)
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    plt.savefig(plot_path, bbox_inches='tight', dpi=150)
    plt.close()

    return f"Saved: {plot_path}"


def parallel_trip_route_clustering(df_all, n_clusters=5, processes=7, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    grouped = [(df_all[df_all["day_of_week"] == day], day, n_clusters, output_dir)
               for day in df_all["day_of_week"].unique()]
    with Pool(processes=processes) as pool:
        results = pool.starmap(cluster_full_trip_routes, grouped)
    return results
