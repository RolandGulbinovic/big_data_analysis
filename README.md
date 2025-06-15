# Individual Task

## Analysis of Bike Trip Distance and Duration by Day of the Week

The goal of this task is to use parallelisation to read, process and output results about Bike Trip for a whole year.

This project performs analysis of bike trip data using Python. It focuses on **distance and duration trends** by day of the week, cleans and transforms raw GPS ride data, and uses **clustering and geospatial visualization**.

---
### 0. Folder Structure
- `rent_bike.py` - the main script to run
- `functions.py` - file with all the functions
- `data/` - needs to contain the 12 input data files - IMPORTANT
- `output/` - all output plots

---

### 1. Read and Clean Data

- Loads all monthly CSVs from the `data/` folder in parallel
- Drops rows with invalid/missing GPS coordinates
- Removes outliers based on:
  - Duration (<1 or >240 minutes)
  - Distance (<0.1 km or >50 km)
- Calculates:
  - Trip duration in minutes
  - Haversine distance in km
  - Average speed (km/h)
  - extracts day of the week

This deletes about ~470 000 rows:

- Rows removed due to invalid GPS coordinates: 4771
- Rows removed due to outliers: 455994

---

### 2. Trip Statistics and Analysis

- We compute:
  - Average trip duration, distance, and speed by weekday
  - Most popular starting stations
  - Slowest station-to-station routes (long duration per km)
  - Most frequently used routes

- Visualizations:
  - Print out results
  - Bar plots for duration, distance, and trip count by day

![bar1](output/avg_duration_by_day.png)
![bar2](output/avg_distance_by_day.png)
![bar3](output/trip_count_by_day.png)

---

### 3. Geospatial Clustering

- Applies **KMeans clustering** on trip start coordinates for each day
- Visualizes clusters with:
  - `GeoPandas` for geometry
  - `Contextily` for map tiles
- Cluster centers are shown with black `×` markers

<p align="center">
  <img src="output/volume_cluster_Monday.png" alt="Monday" width="33%"/>
  <img src="output/volume_cluster_Thursday.png" alt="Thursday" width="33%"/>
  <img src="output/volume_cluster_Saturday.png" alt="Saturday" width="33%"/>
</p>

---

### 4. Performance Monitoring

- Logs memory usage with `psutil`

![Clusters for Friday](output/ram_usage.png)


## Results



