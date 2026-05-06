# create_schema_embeddings.py

import json
import requests
from column_semantics import COLUMN_SEMANTICS


OLLAMA_URL = "http://10.1.3.19:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text:latest"

# Optional table-level semantics
TABLE_SEMANTICS = {
    "tbl_aces": "Vehicle fitment data from ACES files",
    "tbl_auto_app_listing": "Product listings mapped to vehicles and SKUs",
    "tbl_auto_part_listing": "Part listings mapped to vehicles and SKUs",
    "tbl_pies": "Product information and marketplace attributes",
    # Add more if needed
}


def get_embedding(text: str):
    """
    Call Ollama to generate embedding for given text.
    """
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": EMBED_MODEL,
            "prompt": text
        }
    )

    response.raise_for_status()
    return response.json()["embedding"]


def build_table_combined_text(table_name: str, columns: dict):
    """
    Combine table semantic + all column descriptions
    into one large descriptive text block.
    """
    parts = []

    if table_name in TABLE_SEMANTICS:
        parts.append(f"Table purpose: {TABLE_SEMANTICS[table_name]}")

    for col_name, desc in columns.items():
        parts.append(f"{col_name}: {desc}")

    return "\n".join(parts)


def main():
    schema_embeddings = {}

    print("Generating schema embeddings...\n")

    for table_name, columns in COLUMN_SEMANTICS.items():
        print(f"Processing table: {table_name}")

        table_entry = {
            "table_embedding": None,
            "columns": {}
        }

        # ---- Column embeddings ----
        for col_name, description in columns.items():
            print(f"  Embedding column: {col_name}")
            embedding = get_embedding(description)

            table_entry["columns"][col_name] = {
                "description": description,
                "embedding": embedding
            }

        # ---- Table-level embedding (combined text) ----
        combined_text = build_table_combined_text(table_name, columns)
        print(f"  Embedding combined table text...")
        table_entry["table_embedding"] = get_embedding(combined_text)

        schema_embeddings[table_name] = table_entry

        print(f"Finished table: {table_name}\n")

    # ---- Save to JSON ----
    with open("schema_embeddings.json", "w") as f:
        json.dump(schema_embeddings, f)

    print("Schema embeddings saved to schema_embeddings.json")


if __name__ == "__main__":
    main()
