import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Distance, VectorParams

QDRANT_HOST = "192.168.100.10"
QDRANT_PORT = 6333
COLLECTION_NAME = "arxiv"
FILE_PATH = "/home/diabd/embedded_chunks.json"
BATCH_SIZE = 100

points = []

# Load data from JSONL file
with open(FILE_PATH, "r") as f:
    for line in f:
        obj = json.loads(line)
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=obj["embedding"],
            payload={
                "id": obj["id"],
                "title": obj["title"],
                "authors": obj["authors"],
                "year": obj["year"],
                "chunk": obj["chunk"]
            }
        ))

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Create collection if it does not exist
if COLLECTION_NAME not in [c.name for c in client.get_collections().collections]:
    vector_size = len(points[0].vector)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        shard_number=2,  # one shard per node
        replication_factor=1,
        write_consistency_factor=1
    )

# Upload data in batches
for i in range(0, len(points), BATCH_SIZE):
    batch = points[i:i + BATCH_SIZE]
    client.upsert(collection_name=COLLECTION_NAME, points=batch)
    print(f"Batch uploaded: {i} - {i + len(batch) - 1}")

print(f"\nUpload completed: {len(points)} points inserted into Qdrant ({COLLECTION_NAME})")
