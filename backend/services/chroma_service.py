# ChromaDB helper functions (add/query embeddings)

#query_similar_messages(chat_id, query_embedding, k)

#query_similar_summaries(chat_id, query_embedding, k, exclude_ongoing=True)

#delete_chat_embeddings(chat_id)
# /services/chroma_service.py
import time
import numpy as np
from chromadb_client import get_chroma_client, embed_text
from services import chat_service, sql_service
import requests
import dotenv
import os
dotenv.load_dotenv()

from services import sql_service, ollama_service
import chromadb_client


client = get_chroma_client()

def add_message_embedding(collection_name, doc_id, content, metadata):
    """
    Adds an embedded message to a ChromaDB collection.
    """
    collection = client.get_or_create_collection(name=collection_name)
    embedding = embed_text(content)
    collection.add(
        ids=[doc_id],
        documents=[content],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def delete_chat_data(chat_id, collection_name="messages"):
    """
    Deletes all messages associated with a chat_id from the collection.
    """
    collection = client.get_or_create_collection(name=collection_name)
    collection.delete(where={"chat_id": chat_id})


def get_ongoing_topic_summary(chat_id: int):
    """
    Retrieves the ongoing topic summary for a given chat_id from ChromaDB.
    """
    collection = client.get_or_create_collection(name="context_summaries")
    results = collection.query(
        where={"chat_id": chat_id, "ongoing":True},
        n_results=1,
    )
    # ChromaDB returns results as a dict
    # If no results, return None
    if not results or len(results["documents"]) == 0:
        return None
    
    # Grab the first (and should be only) ongoing summary
    ongoing_summary = results["documents"][0][0]  # Chroma returns list of lists
    metadata = results["metadatas"][0][0]         # metadata dict
    
    retrieved_chat_id = metadata.get("chat_id")
    ongoing_boolean = metadata.get("ongoing")
    start_msg_id = metadata.get("start_message_id")
    end_msg_id = metadata.get("end_message_id")

    return {
        "summary": ongoing_summary,
        "chat_id": retrieved_chat_id,
        "ongoing": ongoing_boolean,
        "start_message_id": start_msg_id,
        "end_message_id": end_msg_id,
    }

def build_memory_query(chat_id: int) -> str:
    """
    Builds a query string for embedding-based memory retrieval.
    """
    user_name = os.getenv("username", "Human")

    last_msgs = sql_service.get_last_x_user_messages(chat_id, 1, user_name)
    if not last_msgs:
        return []

    last_user_message = last_msgs[0]["message"]

    current_summary = sql_service.get_current_context_summary(chat_id)
    if current_summary:
        current_summary = current_summary.strip()[:500]  # light safety cap

        memory_query = f"""
<topic>
{current_summary}
</topic>

<query>
{last_user_message}
</query>
""".strip()
    else:
        memory_query = last_user_message.strip()

    return memory_query

def cosine_similarity(vec1, vec2):
    """
    Compute cosine similarity between two vectors.
    Returns a float in [-1, 1], where 1 means identical direction.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


def retrieve_top_x_context_embeddings(chat_id: int, 
                                      x: int, 
                                      raw_recent_messages_to_exclude: list,
                                      collection_names=["messages", "context_summaries"]):
    """
    Retrieves the top X relevant context embeddings from 'messages' and 'context_summaries'
    collections for a given chat_id using semantic similarity (cosine) and recency weighting.
    """
    # 1 Build the memory query
    memory_query_text = build_memory_query(chat_id)
    if not memory_query_text:
        return []

    # 2 Embed the query
    query_embedding = chromadb_client.embed_text(memory_query_text)
    if query_embedding is None:
        return []

    # 3 Get collections
    message_collection = client.get_or_create_collection(name="messages")
    summary_collection = client.get_or_create_collection(name="context_summaries")

    # 4 Retrieve top candidates (over-retrieve to filter later)
    top_k_messages = message_collection.query(
        query_embeddings=[query_embedding],
        n_results=x * 2,
        include=["documents", "metadatas"],
        where={"chat_id": chat_id}
    )

    top_k_summaries = summary_collection.query(
        query_embeddings=[query_embedding],
        n_results=x * 2,
        include=["documents", "metadatas"],
        where={"chat_id": chat_id}
    )

    # 5 Combine results
    combined = []
    user_name = os.getenv("username", "Human")
    #last_msgs = sql_service.get_last_x_user_messages(chat_id, 1, user_name)
    #last_user_message = last_msgs[0]["message"] if last_msgs else ""

    # Process messages
    for doc, meta in zip(top_k_messages["documents"][0], top_k_messages["metadatas"][0]):
        if doc.strip() in raw_recent_messages_to_exclude:
            continue

        # Embed the retrieved message and compute cosine similarity
        item_embedding = chromadb_client.embed_text(doc)
        score = cosine_similarity(query_embedding, item_embedding)

        combined.append({
            "type": "message",
            "id": meta.get("id"),
            "content": doc,
            "timestamp": meta.get("timestamp", 0),
            "score": score
        })

    # Process summaries
    for doc, meta in zip(top_k_summaries["documents"][0], top_k_summaries["metadatas"][0]):
        content = doc or meta.get("summary", "")
        item_embedding = chromadb_client.embed_text(content)
        score = cosine_similarity(query_embedding, item_embedding)

        combined.append({
            "type": "summary",
            "id": meta.get("id"),
            "content": content,
            "timestamp": meta.get("timestamp", 0),
            "score": score
        })

    # 6 Apply recency weighting
    now_ts = time.time()
    for item in combined:
        age_days = (now_ts - item["timestamp"]) / (60 * 60 * 24)
        recency_boost = np.exp(-age_days / 30)
        item["final_score"] = item["score"] * (1 + 0.5 * recency_boost)

    # 7 Sort by final_score descending
    combined_sorted = sorted(combined, key=lambda i: i["final_score"], reverse=True)

    # 8 Return top X results
    sorted_results = combined_sorted[:x]
    results_list = [{"message": item["content"], "type": item["type"], "cosine_similarity": item["final_score"]} for item in sorted_results]

    return results_list