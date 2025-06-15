import os
import time
import psutil
import threading
import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from multiprocessing import Pool

import matplotlib.pyplot as plt
import seaborn as sns

import geopandas as gpd
import contextily as ctx
from sklearn.cluster import KMeans

NUM_CORES = 11

# Memory tracking
memory_log = []
track_running = True

# Cluster colors
CLUSTER_COLORS = {
    0: "#1f77b4",  # blue
    1: "#2ca02c",  # green
    2: "#d62728",  # red
}

# Functions for Memory Tracking
def start_memory_tracker():
    global track_running
    track_running = True
    threading.Thread(target=memory_tracker, daemon=True).start()

def stop_memory_tracker():
    global track_running
    track_running = False

def memory_tracker(interval=1.0):
    process = psutil.Process(os.getpid())
    while track_running:
        mem_mb = process.memory_info().rss / (1024 ** 2)
        memory_log.append((time.time(), mem_mb))
        time.sleep(interval)

def plot_memory_usage(output_path="ram_usage.png"):
    if not memory_log:
        print("No memory data recorded.")
        return
    timestamps, mem_usage = zip(*memory_log)
    timestamps = [t - timestamps[0] for t in timestamps]
    plt.figure(figsize=(8, 4))
    plt.plot(timestamps, mem_usage, label="RAM (MB)")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Memory Usage (MB)")
    plt.title("RAM Usage Over Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"RAM usage plot saved to {output_path}")
    plt.close()

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
def cluster_one_day(day_df, n_clusters=3):
    coords = day_df[["start_lat", "start_lng"]].to_numpy()
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(coords)
    day_df = day_df.copy()
    day_df["cluster"] = kmeans.labels_
    return day_df, kmeans.cluster_centers_

# Run cluster_one_day() for all days of the week (in parallel)
def parallel_cluster_all_days(df, n_clusters=3):
    grouped = [df[df["day_of_week"] == day] for day in df["day_of_week"].unique()]
    with Pool(processes=7) as pool:
        results = pool.starmap(cluster_one_day, [(group, n_clusters) for group in grouped])
    return results

# Plot the clutsers on a real map
def plot_clusters_with_map(day_df, centers, day_name, output_path):
    gdf = gpd.GeoDataFrame(
        day_df,
        geometry=gpd.points_from_xy(day_df["start_lng"], day_df["start_lat"]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    center_gdf = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(centers[:, 1], centers[:, 0]),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    gdf["color"] = gdf["cluster"].map(CLUSTER_COLORS)

    fig, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(ax=ax, color=gdf["color"], markersize=5)
    center_gdf.plot(ax=ax, color="black", marker="x", markersize=80)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_title(f"Clusters for {day_name}")
    plt.axis("off")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
