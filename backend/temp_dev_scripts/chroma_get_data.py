import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from chromadb_client import get_chroma_client
from tabulate import tabulate
from collections import defaultdict

client = get_chroma_client()
collection = client.get_or_create_collection(name="messages")



# Get all stored messages (with embeddings)
results = collection.get()

# Handle missing embeddings
embeddings = results.get("embeddings")
if embeddings is None:
    embeddings = [None] * len(results["documents"])

# Group by chat_id and include embeddings
grouped = defaultdict(list)
for doc, meta, emb in zip(results["documents"], results["metadatas"], embeddings):
    grouped[meta.get("chat_id")].append((meta, doc, emb))

print("\n?? Messages by Chat (with Embeddings):\n" + "=" * 60)

for chat_id, items in grouped.items():
    print(f"\n Chat {chat_id}\n" + "-" * 60)
    # Sort by created_at if available
    items = sorted(items, key=lambda x: x[0].get("created_at", ""))
    for meta, doc, emb in items:
        print(f"[{meta.get('created_at')}] {meta.get('message_id')}: {meta.get('user')}: {doc}\n  Embedding: {emb}")
        
        
        
        


context_summary_collection = client.get_or_create_collection(name="context_summaries")
results = context_summary_collection.get()

# Handle missing embeddings
embeddings = results.get("embeddings")
if embeddings is None:
    embeddings = [None] * len(results["documents"])

print("\nContext Summaries (with Embeddings):\n" + "=" * 60)
table = []
for doc, meta, emb in zip(results["documents"], results["metadatas"], embeddings):
    table.append([
        meta.get("chat_id"),
        meta.get("ongoing"),
        meta.get("start_message_id"),
        meta.get("end_message_id"),
        doc,
        str(emb) if emb is not None else "None"
    ])
print(tabulate(table, headers=["Chat ID", "Ongoing", "start msg ID", "end msg ID", "Summary", "Embedding"]))


