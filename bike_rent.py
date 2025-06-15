from glob import glob
from functions import *
from tqdm import tqdm
import pandas as pd
import time

DATA_PATH = "data/*.csv"

def main():
    start = time.time()
    start_memory_tracker()

    file_paths = glob(DATA_PATH)
    print(f"Found {len(file_paths)} files.")

    with Pool(NUM_CORES) as pool:
        results = list(tqdm(pool.imap_unordered(process_file, file_paths), total=len(file_paths)))

    cleaned_dfs = [res[0] for res in results]
    total_removed_coords = sum(res[1] for res in results)
    total_removed_outliers = sum(res[2] for res in results)

    print(f"Rows removed (coords): {total_removed_coords}")
    print(f"Rows removed (outliers): {total_removed_outliers}")

    df_all = pd.concat(cleaned_dfs, ignore_index=True)
    df_all = calculate_speed(df_all)

    top_stations, top_paths, weekday_stats, top_routes = run_sequential_analyses(df_all)

    print("\nTop 10 Start Stations:")
    print(top_stations)

    print("\nTop 10 Slowest Paths (avg minutes per km):")
    print(top_paths)

    print("\nTrip Stats by Day of the Week:")
    print(weekday_stats)
    print("Fastest day:", weekday_stats['avg_speed'].idxmax())
    print("Slowest day:", weekday_stats['avg_speed'].idxmin())

    print("\nTop 10 Most Frequent Routes:")
    print(top_routes)

    plot_memory_usage("ram_usage.png")

    # --- VISUALIZATION ---
    plot_stat_by_day(weekday_stats, 'avg_duration', 'Average Duration (min)', 'avg_duration_by_day.png')
    plot_stat_by_day(weekday_stats, 'avg_distance', 'Average Distance (km)', 'avg_distance_by_day.png')
    plot_stat_by_day(weekday_stats, 'trip_count', 'Trip Count', 'trip_count_by_day.png', agg_func='value')

    stop_memory_tracker()

    end = time.time()
    print(f"Total execution time: {end - start:.2f} seconds")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()