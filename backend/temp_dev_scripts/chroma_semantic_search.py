import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from chromadb_client import embed_text, get_chroma_client

client = get_chroma_client()
collection = client.get_or_create_collection(name="messages")

query = "woody"
query_embedding = embed_text(query)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3,  # top 3 most similar
    #where={"chat_id": 1},  # optional filter
)
print("distances are:\n" + str(results["distances"]))
for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"[{meta['created_at']}] {meta['user']}: {doc}")