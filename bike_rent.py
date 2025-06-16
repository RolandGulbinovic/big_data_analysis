from glob import glob
from functions import *
from tqdm import tqdm
import pandas as pd
import time
import os
from multiprocessing import Pool, freeze_support

DATA_PATH = "data/*.csv"

def main():
    start = time.time()

    # Starting memory tracking

    # --- Data Reading & Cleaning ---
    file_paths = glob(DATA_PATH)
    print(f"Found {len(file_paths)} files.")
    file_chunks = chunkify(file_paths, NUM_CORES)

    with Pool(processes=NUM_CORES) as pool:
        results = list(tqdm(pool.imap_unordered(process_file_chunk, file_chunks), total=len(file_chunks)))

    # --- Combine cleaned data ---
    dfs, removed_invalids, removed_outliers = zip(*results)
    df_all = pd.concat(dfs, ignore_index=True)
    print(f"Rows removed (coords): {sum(removed_invalids)}")
    print(f"Rows removed (outliers): {sum(removed_outliers)}")

    df_all = calculate_speed(df_all)

    # --- Statistical Analyses ---
    top_stations, top_paths, weekday_stats, top_routes = run_sequential_analyses(df_all)
    print("\nTop 10 Start Stations:")
    print(top_stations)
    print("\nTop 10 Slowest Paths:")
    print(top_paths)
    print("\nTrip Stats by Day:")
    print(weekday_stats)
    print("Fastest:", weekday_stats['avg_speed'].idxmax(), "Slowest:", weekday_stats['avg_speed'].idxmin())
    print("\nTop 10 Routes:")
    print(top_routes)

    # --- Directory for saving ---
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # --- Clustering by Station Volume ---
    print("Starting volume clustering...")
    parallel_cluster_volume_and_plot(df_all, n_clusters=3, processes=NUM_CORES)
    print("Volume clustering complete.")

    # --- Clustering Full Trips ---
    print("Starting full trip clustering...")
    trip_results = parallel_trip_route_clustering(df_all, n_clusters=3, output_dir=output_dir)
    for r in trip_results:
        print(r)
    print("Full trip clustering complete.")

    # --- Visualizations ---
    plot_stat_by_day(weekday_stats, 'avg_duration', 'Average Duration (min)', f'{output_dir}/avg_duration_by_day.png')
    plot_stat_by_day(weekday_stats, 'avg_distance', 'Average Distance (km)', f'{output_dir}/avg_distance_by_day.png')
    plot_stat_by_day(weekday_stats, 'trip_count', 'Trip Count', f'{output_dir}/trip_count_by_day.png', agg_func='value')

    # --- Stop memory tracking ---

    print(f"Total execution time: {time.time() - start:.2f} seconds")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()

    start_memory_tracker_thread(interval=0.5)

    main()

    save_memory_log("output/memory_log.csv")
    plot_memory_usage("output/memory_log.csv", "output/ram_usage.png")