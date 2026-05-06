#!/usr/bin/env python3
"""
Safely delete all entries (collections and documents) in your ChromaDB database.
Use with caution  this cannot be undone.
"""

import os

import chromadb
from chromadb.config import Settings

# --- Configuration ---
CHROMA_DB_DIR = "/var/www/html/QA_Chatbot/chroma_db"

def clear_chromadb():
    print(f"??  WARNING: This will permanently delete all data in: {CHROMA_DB_DIR}")
    confirm = input("Type 'DELETE ALL' to confirm: ").strip()
    if confirm != "DELETE ALL":
        print("Cancelled - no data deleted.")
        return

    # Connect to ChromaDB (persistent client)
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    # List all collections
    collections = client.list_collections()
    if not collections:
        print("No collections found, database already empty.")
        return

    print(f"Found {len(collections)} collections:")
    for c in collections:
        print(f" - {c.name}")

    # Delete each collection
    for c in collections:
        '''
        if c.name == "vanna_memory":
            print(f"Skipping deletion of collection: {c.name}")
            continue
        '''
        client.delete_collection(c.name)
        print(f"Deleted collection: {c.name}")

    print("All ChromaDB data deleted successfully.")

if __name__ == "__main__":
    clear_chromadb()
