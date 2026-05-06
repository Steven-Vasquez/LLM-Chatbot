# /chromadb_client.py

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os
import requests

# --- Configuration ---
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

# --- Singleton Instances ---
_client = None
_model = None


def get_chroma_client():
    """
    Returns a singleton persistent ChromaDB client.
    """
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    return _client

def embed_text(text):
    """
    Embed a string or list of strings using Ollama embeddings.
    
    Returns:
      - list[float] for single string
      - list[list[float]] for list of strings
    """
    if isinstance(text, list):
        return [_embed_single(t) for t in text]
    else:
        return _embed_single(text)


def _embed_single(text: str) -> list[float]:
    payload = {
        "model": os.getenv("embedding_model", "nomic-embed-text:latest"),
        "prompt": text,
    }

    response = requests.post("http://10.1.3.19:11434/api/embeddings", json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()

    if "embedding" not in data:
        raise RuntimeError(f"Model embedding response missing 'embedding': {data}")

    return data["embedding"]


# def get_embedding_model():
#     """
#     Returns a singleton SentenceTransformer model instance.
#     """
#     global _model
#     if _model is None:
#         _model = SentenceTransformer("all-MiniLM-L6-v2")
#     return _model
#
#
# def embed_text(text):
#     """
#     Helper to embed text or list of texts.
#     """
#     model = get_embedding_model()
#     if isinstance(text, list):
#         return model.encode(text, convert_to_numpy=True).tolist()
#     else:
#         return model.encode([text], convert_to_numpy=True).tolist()[0]