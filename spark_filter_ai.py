from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = SparkSession.builder \
    .appName("Filter AI articles (cs.AI)") \
    .getOrCreate()

input_path = "hdfs://master:9000/dataset/arxiv-metadata-oai-snapshot.json"
output_path = "hdfs://master:9000/dataset/arxiv_ai_filtered.json"

# Read dataset and filter by category
df = spark.read.json(input_path)
df_filtered = df.filter(col("categories").contains("cs.AI"))

# Save filtered articles
df_filtered.write.mode("overwrite").json(output_path)

count = df_filtered.count()
print(f"Found and saved {count} AI articles to {output_path}")

spark.stop()
