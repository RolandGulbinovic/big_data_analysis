## TASK/ASSIGNMENT 4

### Files:
Everything is done in the `main.py` script.

### `main.py`


#### 1
- Downloads the dataset from http://web.ais.dk/aisdata/aisdk-2024-05-04.zip
- Unzips the downloaded dataset

#### 2
- Then I start a Spark session using `SparkSession.builder.appName("AIS_Longest_Route").getOrCreate()`
- Data is read into a PySpark Dataframe
- Some data processing is done like - making sure data types are correct and there are no NA values in the needed columns

#### 3
- A simple haversine distance calculation function is defined
- It gets wrapped inside a Pandas User-Defined Function for Pyspark. This ensures that the function is applied efficiently across our PySpark dataframe
- We apply this function to calculate the distance travelled in each row for each MMSI

#### 4
- Aggregation is done to compute the total distances travelled for each MMSI and with sorting the one with the highest MMSI gets extracted.

#### 5
- The Vessel MMSI and the total distance travelled is outputed using `.show()`
