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
#url = "https://example.com/AIS_Data_2024-05-04.zip"
zip_path = "aisdk-2024-05-04.zip"

# Download the ZIP file
# response = requests.get(url)
# with open(zip_path, "wb") as f:
#     f.write(response.content)
# print("Download complete.")

# with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#     zip_ref.extractall(".")
# print(f"Extracted")

spark = SparkSession.builder.appName("AIS_Longest_Route").getOrCreate()

df = spark.read.csv("aisdk-2024-05-04.csv", header=True, inferSchema=True)

df = df.withColumn("latitude", col("latitude").cast(DoubleType())) \
       .withColumn("longitude", col("longitude").cast(DoubleType()))

df = df.withColumn("# Timestamp", to_timestamp(col("# Timestamp"), "dd/MM/yyyy HH:mm:ss"))

df = df.select("MMSI", "# Timestamp", "latitude", "longitude").dropna()


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

@pandas_udf("double", PandasUDFType.SCALAR)
def haversine_udf(lat1, lon1, lat2, lon2):
    return pd.Series([
        haversine(a, b, c, d) for a, b, c, d in zip(lat1, lon1, lat2, lon2)
    ])

# 5. Calculate segment distances
windowSpec = Window.partitionBy("MMSI").orderBy("# Timestamp")

df = df.withColumn("prev_lat", lag("latitude").over(windowSpec)) \
       .withColumn("prev_lon", lag("longitude").over(windowSpec))

df = df.filter(col("prev_lat").isNotNull())

df = df.withColumn("segment_distance_km", haversine_udf(
    col("prev_lat"), col("prev_lon"),
    col("latitude"), col("longitude")
))

# 6. Aggregate distances per MMSI
distance_df = df.groupBy("MMSI").agg(
    _sum("segment_distance_km").alias("total_distance_km")
)

# 7. Get the vessel with the longest distance
longest_route = distance_df.orderBy(col("total_distance_km").desc()).limit(1)
longest_route.show()