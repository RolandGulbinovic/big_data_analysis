from functions import process_large_file
import time

if __name__ == "__main__":
    start_time = time.time()
    file_path = "data.csv"
    chunk_size = 50000
    cpu_count = 11
    result = process_large_file(file_path , chunk_size, cpu_count,
    k_std = 5, distance_threshold = 2)

    result.to_csv('output.csv', index=False)
    end_time = time.time()
    execution_time = end_time - start_time

    print(result.shape)
    print(f"Execution time: {execution_time:.2f} seconds")
