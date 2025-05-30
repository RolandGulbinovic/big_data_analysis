import os
import requests
import zipfile
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lag, sum as _sum
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType, TimestampType
from math import radians, sin, cos, sqrt, atan2
import pandas as pd
from pyspark.sql.functions import pandas_udf, PandasUDFType
from pyspark.sql.functions import to_timestamp


# Set variables
url = "http://web.ais.dk/aisdata/aisdk-2024-05-04.zip"
zip_path = "aisdk-2024-05-04.zip"

#Download the ZIP file
print(f"Downloading dataset from {url}")
response = requests.get(url)
with open(zip_path, "wb") as f:
    f.write(response.content)
print("Download complete.")

print(f"Extracting dataset from {zip_path}")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(".")
print(f"Extraction complete")

spark = SparkSession.builder.appName("AIS_Longest_Route").getOrCreate()

print("Reading dataset")
df = spark.read.csv("aisdk-2024-05-04.csv", header=True, inferSchema=True)

# First we make sure the data types are correct. this is done using cast()
df = df.withColumn("latitude", col("latitude").cast(DoubleType())) \
       .withColumn("longitude", col("longitude").cast(DoubleType()))

# Pyspark has some requirements regarding the timestamp format, so for this we
# do some additional formating
df = df.withColumn("# Timestamp", to_timestamp(col("# Timestamp"), "dd/MM/yyyy HH:mm:ss"))

df = df.select("MMSI", "# Timestamp", "latitude", "longitude").dropna()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

# Here we wrap our haversine function in a pandas UDF. This will make sure that Python
# partitions data efficiently in Pyspark
@pandas_udf("double", PandasUDFType.SCALAR)
def haversine_udf(lat1, lon1, lat2, lon2):
    return pd.Series([
        haversine(a, b, c, d) for a, b, c, d in zip(lat1, lon1, lat2, lon2)
    ])

# We use window do partition our data by MMSI
windowSpec = Window.partitionBy("MMSI").orderBy("# Timestamp")

# We create ne columns that contain the previous lattitude and longitude
df = df.withColumn("prev_lat", lag("latitude").over(windowSpec)) \
       .withColumn("prev_lon", lag("longitude").over(windowSpec))

df = df.filter(col("prev_lat").isNotNull())

# Then we calculate the distance using haversine_udf()
df = df.withColumn("distance_km", haversine_udf(
    col("prev_lat"), col("prev_lon"),
    col("latitude"), col("longitude")
))

# We aggregate the distances by MMSI
distance_df = df.groupBy("MMSI").agg(
    _sum("distance_km").alias("total_distance_km")
)

# By ordering all of these we can select the one MMSI that has the highest total distance
# We use .show() to print out the result.
longest_route = distance_df.orderBy(col("total_distance_km").desc()).limit(1)
longest_route.show()