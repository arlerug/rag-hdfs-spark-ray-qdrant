from pyspark.sql import SparkSession
import json
import re

spark = SparkSession.builder \
    .appName("Spark preprocessing") \
    .getOrCreate()

sc = spark.sparkContext

input_path = "hdfs://master:9000/dataset/arxiv_ai_filtered.json"
output_path = "hdfs://master:9000/dataset/processed_dataset.json"

def clean_text(text):
    return re.sub(r"\s+", " ", text.strip()) if text else ""

def simple_sentence_split(text):
    text = clean_text(text)
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 20]

def process_line(line):
    try:
        obj = json.loads(line)
        abstract = clean_text(obj.get("abstract", ""))
        title = clean_text(obj.get("title", ""))
        authors = clean_text(obj.get("authors", ""))
        categories = clean_text(obj.get("categories", ""))
        paper_id = obj.get("id", "")
        year = obj.get("update_date", "").split("-")[0] if obj.get("update_date") else "unknown"

        sentences = simple_sentence_split(abstract)
        if len(sentences) < 2:
            return []

        return [json.dumps({
            "id": paper_id,
            "title": title,
            "authors": authors,
            "year": year,
            "chunk": " ".join(sentences[i:i+2])
        }) for i in range(0, len(sentences), 2)]
    except Exception:
        return []

# Run the preprocessing job
data = sc.textFile(input_path)
processed_chunks = data.flatMap(process_line)
processed_chunks.saveAsTextFile(output_path)

print("Spark preprocessing completed.")
