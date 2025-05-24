import ray
import json
from tqdm import tqdm
import socket
from sentence_transformers import SentenceTransformer

# Initialize Ray
ray.init(address="auto")

# Load the model once and place it in the Ray object store
model = SentenceTransformer("all-MiniLM-L6-v2")
model_ref = ray.put(model)

# Remote task for embedding computation
@ray.remote(num_cpus=2)
def compute_embeddings_batch(batch, model_ref):
    model = model_ref
    results = []

    for entry in batch:
        try:
            text = entry.get("chunk", "").strip()
            if not text:
                continue
            embedding = model.encode(text).tolist()
            results.append({
                "id": entry.get("id", ""),
                "title": entry.get("title", ""),
                "authors": entry.get("authors", ""),
                "year": entry.get("year", ""),
                "chunk": text,
                "embedding": embedding
            })
        except Exception as e:
            print(f"Error on node {socket.gethostname()}: {e}")
            continue
    return results

INPUT_PATH = "processed_dataset.json"
OUTPUT_PATH = "embedded_chunks.json"

# Read input file
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    entries = [json.loads(line) for line in f if line.strip()]

# Create batches
BATCH_SIZE = 64
batches = [entries[i:i+BATCH_SIZE] for i in range(0, len(entries), BATCH_SIZE)]

print(f"Starting embedding of {len(entries)} chunks in {len(batches)} batches of {BATCH_SIZE}...")

futures = [compute_embeddings_batch.remote(batch, model_ref) for batch in batches]
all_chunks = []

for future in tqdm(futures, desc="Embedding batches", unit="batch"):
    result = ray.get(future)
    all_chunks.extend(result)

# Write output file
with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
    for chunk in all_chunks:
        out.write(json.dumps(chunk) + "\n")

print(f"Completed {len(all_chunks)} embeddings and saved to {OUTPUT_PATH}")
