import os
import time
import pandas as pd
import multiprocessing as mp
from tqdm import tqdm
import numpy as np

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon1 - lon2)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def process_vessel(vessel_data, k_std, distance_threshold):
    vessel_data = vessel_data.sort_values(by='# Timestamp')
    vessel_data['distance'] = calculate_distance(vessel_data['Latitude'], vessel_data['Longitude'],
                                        vessel_data['Latitude'].shift(), vessel_data['Longitude'].shift())

    mean_sog = vessel_data['SOG'].mean()
    std_sog = vessel_data['SOG'].std()
    upper_bound = mean_sog + k_std * std_sog
    lower_bound = max(0, mean_sog - k_std * std_sog)

    vessel_data['anomaly_speed'] = (vessel_data['SOG'] > upper_bound) | (vessel_data['SOG'] < lower_bound)
    vessel_data['anomaly_location'] = vessel_data['distance'] > distance_threshold
    return vessel_data


def conflicting_positions(chunk):
    chunk['lat_approx'] = chunk['Latitude'].round(6)
    chunk['lon_approx'] = chunk['Longitude'].round(6)

    chunk['conflicting_locations'] = chunk.groupby(['lat_approx', 'lon_approx'])['MMSI'].transform('nunique')
    chunk['anomaly_conflict'] = chunk['conflicting_locations'] > 1

    return chunk


def data_prep(df):
    df_cleaned = df.dropna(subset=['# Timestamp', 'MMSI'])
    df_cleaned = df_cleaned[df_cleaned['Type of position fixing device'] == "GPS"]
    df_cleaned = df_cleaned.drop_duplicates()
    df_cleaned = df_cleaned[df_cleaned['Latitude'] != 91.0]

    return df_cleaned

def process_chunk(chunk, idx, k_std, distance_threshold):
    #pid = os.getpid()
    #print(f"[Worker {pid}] Processing chunk {idx} of size {len(chunk)}", flush=True)

    chunk = data_prep(chunk)
    chunk = chunk.sort_values(by=['MMSI', '# Timestamp'])
    chunk = chunk.groupby('MMSI').apply(process_vessel, k_std, distance_threshold).reset_index(drop=True)
    chunk = conflicting_positions(chunk)
    chunk['anomaly'] = chunk['anomaly_location'] | chunk['anomaly_speed'] | chunk['anomaly_conflict']

    #print(f"[Worker {pid}] Finished chunk {idx}", flush=True)

    return chunk[chunk['anomaly']]

def process_large_file(file_path , chunk_size, cpu_count, k_std, distance_threshold):

    pool = mp.Pool(cpu_count)
    processed_chunks = []

    total_rows = sum(1 for row in open(file_path)) - 1
    total_chunks = total_rows // chunk_size + 1

    with tqdm(total=total_chunks, unit='chunk', desc='Processing test chunks') as pbar:
        for i, chunk in enumerate(pd.read_csv(file_path, chunksize=chunk_size)):
            processed_chunk = pool.apply_async(process_chunk, (chunk, i, k_std, distance_threshold))
            processed_chunks.append(processed_chunk)
            pbar.update(1)

    pool.close()
    pool.join()

    results = [f.get() for f in processed_chunks]
    final_df = pd.concat(results, ignore_index=True)

    return final_df
