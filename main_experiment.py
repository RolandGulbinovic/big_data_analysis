from functions import process_large_file, generate_speed_plot, speedup_analysis
import csv
import time

if __name__ == "__main__":
    file_path = 'data.csv'

    chunk_sizes = [10000, 50000, 100000]
    cpu_counts = [1, 2, 4, 8, 11]

    results = []

    for cs in chunk_sizes:
        for cpus in cpu_counts:
            print('Processing chunk size: {} cpus: {}'.format(cs, cpus))
            start_time = time.time()

            result = process_large_file(
                file_path,
                cs,
                cpus,
                k_std=5,
                distance_threshold=2
            )

            end_time = time.time()
            exec_time = end_time - start_time

            print(f"chunk_size={cs}, cpu_count={cpus}, execution_time={exec_time:.2f}s")

            results.append({
                'chunk_size': cs,
                'cpu_count': cpus,
                'execution_time': exec_time
            })

    with open('configurations.csv', 'w', newline='') as f:
        fieldnames = ['chunk_size', 'cpu_count', 'execution_time']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


    generate_speed_plot("configurations.csv")
    speedup_analysis("configurations.csv")