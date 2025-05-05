import pymongo
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm
import os
import csv

# Connect to MongoDB and return the data.
def connect_to_mongodb(uri="mongodb://localhost:27017/", db_name="vessel_db", collection_name="raw_vessel_data"):
    client = pymongo.MongoClient(uri)
    db = client[db_name]
    return db[collection_name]

# Load a small sample of data for testing (for speed and memory)
def load_data_sample(collection, sample_fraction=0.075):
    print("Fetching a random sample from MongoDB:")

    total_docs = collection.count_documents({})
    sample_size = int(total_docs * sample_fraction)

    pipeline = [{'$sample': {'size': sample_size}}]
    data = list(collection.aggregate(pipeline))

    df = pd.DataFrame(data)
    df['# Timestamp'] = pd.to_datetime(df['# Timestamp'])
    df = df.sort_values(by=['MMSI', '# Timestamp'])

    print(f"✅ Loaded {len(df)} rows (approx. {sample_fraction * 100:.0f}%)")
    return df


# Calculate delta t in milliseconds between subsequent data points per vessel.
def calculate_delta_t(df):
    delta_t_list = []

    print("Calculating delta t per vessel...")
    for mmsi, group in tqdm(df.groupby('MMSI')):
        group = group.sort_values('# Timestamp')
        deltas = group['# Timestamp'].diff().dropna()
        delta_ms = deltas.dt.total_seconds() * 1000  # Convert to ms
        delta_t_list.extend(delta_ms.tolist())

    return delta_t_list

# Generate and save histogram of delta t values.
def plot_histogram(delta_t_list, output_path="output/delta_t_histogram.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.hist(delta_t_list, bins=100, color='skyblue', edgecolor='black')
    plt.title("Histogram of Delta t (ms) Between Vessel Data Points")
    plt.xlabel("Delta t (ms)")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.show()

# Return summary of deltas
def analyze_deltas(delta_t_list,  output_path="output/delta_summaries.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    total = len(delta_t_list)
    mean = sum(delta_t_list) / total
    min_val = min(delta_t_list)
    max_val = max(delta_t_list)

    # Print results
    print(f"Total delta t entries: {total}")
    print(f"Mean delta t: {mean:.2f} ms")
    print(f"Min delta t: {min_val:.2f} ms")
    print(f"Max delta t: {max_val:.2f} ms")

    # Save to CSV
    summary = [
        ["Metric", "Value (ms)"],
        ["Total delta t entries", total],
        ["Mean delta t", f"{mean:.2f}"],
        ["Min delta t", f"{min_val:.2f}"],
        ["Max delta t", f"{max_val:.2f}"]
    ]

    with open(output_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(summary)

    print(f"Summary saved to {output_path}")

# Generate and save histogram of logged delta t values (logging is needed for visualisation because of outliers)
def plot_histogram_log(delta_t_list, output_path="output/log_delta.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.hist(delta_t_list, bins=100, color='skyblue', edgecolor='black', log=True)
    plt.title("Histogram of Delta t (ms) [Log Scale]")
    plt.xlabel("Delta t (ms)")
    plt.ylabel("Log(Frequency)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.show()


# Print vessels with delta t above the threshold (1e6 = 16.7 min).
def find_vessels_with_large_deltas(df, threshold_ms=1e6):
    print(f"\n🔎 Vessels with delta t > {threshold_ms:,} ms:")

    outlier_vessels = []

    for mmsi, group in df.groupby('MMSI'):
        group = group.sort_values('# Timestamp')
        deltas = group['# Timestamp'].diff().dt.total_seconds() * 1000  # convert to ms
        large_deltas = deltas[deltas > threshold_ms]

        if not large_deltas.empty:
            outlier_vessels.append(mmsi)
            print(f" - MMSI {mmsi} has {len(large_deltas)} large gaps:")
            print(large_deltas.values[:5])  # print first few

    print(f"\n Total vessels with large gaps: {len(outlier_vessels)}")
    return outlier_vessels


def main():
    # Connection is probably not necessary here since it's done in Task 1
    collection = connect_to_mongodb()
    df = load_data_sample(collection)

    # delta calculation
    delta_t_list = calculate_delta_t(df)

    # plots
    plot_histogram(delta_t_list)
    plot_histogram_log(delta_t_list)
    # summaries
    analyze_deltas(delta_t_list)
    find_vessels_with_large_deltas(df)


if __name__ == "__main__":
    main()
