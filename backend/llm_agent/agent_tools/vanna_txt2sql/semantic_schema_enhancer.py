# semantic_schema_enhancer.py

import json
import requests
import math
from vanna.core.enhancer import LlmContextEnhancer
from vanna.core.llm import LlmMessage
from vanna.core.user import User

# -----------------------------
# CONFIG
# -----------------------------
OLLAMA_URL = "http://10.1.3.19:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text:latest"

TOP_K_COLUMNS = 3  # used in scoring formula


# -----------------------------
# Load precomputed schema embeddings
# (or create them if not found)
# -----------------------------
from pathlib import Path
import subprocess
import sys

SCHEMA_FILE = Path(__file__).parent / "schema_embeddings.json"

# Utility function to ensure schema_embeddings.json exists, or create it if missing
def ensure_schema_file():
    if not SCHEMA_FILE.exists():
        print("schema_embeddings.json not found. Generating it...")
        subprocess.run(
            [sys.executable, "create_schema_embeddings.py"],
            check=True
        )
    else:
        print("Found existing schema_embeddings.json file. Continuing...")

# Ensure file exists BEFORE reading
ensure_schema_file()

with open(SCHEMA_FILE, "r") as f:
    SCHEMA_EMBEDDINGS = json.load(f)

# -----------------------------
# Embedding helper
# -----------------------------
def get_embedding(text: str):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": EMBED_MODEL,
            "prompt": text
        }
    )
    response.raise_for_status()
    return response.json()["embedding"]


# -----------------------------
# Cosine similarity
# -----------------------------
def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    return dot / (norm1 * norm2 + 1e-8)


# -----------------------------
# Semantic Schema Enhancer
# -----------------------------
class SemanticSchemaEnhancer(LlmContextEnhancer):
    def __init__(self, sql_runner, top_n: int = 5):
        self.sql_runner = sql_runner
        self.top_n = top_n
        self.schema_embeddings = SCHEMA_EMBEDDINGS

    async def enhance_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        user: User
    ) -> str:
        """
        Enhance the system prompt for an LLM agent by semantically selecting the most relevant database schema elements.

        This method uses the following approach:
        - Embeds the user query using a local embedding model (Ollama).
        - Computes cosine similarity between the user query embedding and precomputed table/column embeddings from the schema.
        - For each table, calculates a score that combines:
            * Table-level similarity
            * The maximum column-level similarity among the top-K most relevant columns
            * The average similarity of the top-K columns (weighted)
        - Ranks all tables by this score and selects the top-N most relevant tables.
        - For each selected table, includes its name and all column descriptions in the prompt.
        - Appends a static database relationship map for context.

        Debugging output is included to show the scoring and selection process for transparency and tuning.

        Args:
            system_prompt (str): The base system prompt to enhance.
            user_message (str): The user's query or message.
            user (User): The user object (for future use).

        Returns:
            str: The enhanced system prompt including relevant schema and relationships.
        """
        print("system prompt is:\n", system_prompt)
        # Generate embedding for user query
        user_embedding = get_embedding(user_message)

        scored_tables = []

        for table_name, table_data in self.schema_embeddings.items():

            # ---- Table-level similarity ----
            table_similarity = cosine_similarity(
                user_embedding,
                table_data["table_embedding"]
            )

            # ---- Column-level similarity ----
            column_similarities = []

            for col_name, col_data in table_data["columns"].items():
                sim = cosine_similarity(
                    user_embedding,
                    col_data["embedding"]
                )
                column_similarities.append((col_name, sim))

            # Sort columns by similarity descending
            column_similarities.sort(key=lambda x: x[1], reverse=True)

            # Top-K column logic (clean ranking)
            top_k = column_similarities[:TOP_K_COLUMNS]
            max_column_sim = top_k[0][1] if top_k else 0
            avg_top_k_sim = (
                sum(sim for _, sim in top_k) / len(top_k)
                if top_k else 0
            )

            # ---- Final scoring formula ----
            score = (
                table_similarity
                + max_column_sim
                + (0.5 * avg_top_k_sim)
            )

            scored_tables.append({
                "table_name": table_name,
                "score": score,
                "table_similarity": table_similarity,
                "column_similarities": column_similarities
            })

        # Sort tables by score descending
        scored_tables.sort(key=lambda x: x["score"], reverse=True)

        # Pick top N tables
        relevant_tables = scored_tables[:self.top_n]

        # DEBUG (comment out to disable)
        debug_table_scoring(relevant_tables, scored_tables)

        # ---- Build schema section ----
        schema_section = "\n\n## Relevant Database Schema\n\n"

        for table in relevant_tables:
            table_name = table["table_name"]
            schema_section += f"### {table_name}\n"

            for col_name, col_data in self.schema_embeddings[table_name]["columns"].items():
                schema_section += f"- {col_name}: {col_data['description']}\n"

            schema_section += "\n"

        # ---- Relationships (unchanged from yours) ----
        table_relationships = """
=== DATABASE RELATIONSHIP MAP ===

PRIMARY FILE LINEAGE
tbl_aces.aces_file_name = tbl_auto_app_listing.aces_file_name
tbl_pies.pies_file_name = tbl_auto_app_listing.pies_file_name
tbl_pies.pies_file_name = tbl_auto_part_listing.pies_file_name

PART IDENTITY (MOST IMPORTANT)
tbl_pies.part_sku = tbl_auto_app_listing.part1_part_sku
tbl_pies.part_sku = tbl_auto_part_listing.part1_part_sku

APPLICATION PART TERMINOLOGY
tbl_aces.part_type = tbl_pies.part_type
tbl_aces.part_type_aces_id = tbl_pies.part_terminology_id

COMPATIBILITY GROUPING
tbl_aces.ca_group_key = tbl_auto_app_listing.group_key
        """

        final_output = system_prompt + table_relationships + schema_section
        return final_output

    async def enhance_user_messages(
        self,
        messages: list[LlmMessage],
        user: User
    ) -> list[LlmMessage]:
        return messages


# -----------------------------
# DEBUG FUNCTION (Semantic)
# -----------------------------
def debug_table_scoring(top_tables, all_tables):
    print("\n=== SEMANTIC TABLE SCORING DEBUG ===")

    top_names = {t["table_name"] for t in top_tables}

    for table in all_tables:
        flag = "[TOP]" if table["table_name"] in top_names else "[SKIP]"

        print(
            f"{flag} {table['table_name']} | "
            f"Score: {round(table['score'], 4)} | "
            f"TableSim: {round(table['table_similarity'], 4)}"
        )

        # Show top 3 column similarities
        for col_name, sim in table["column_similarities"][:3]:
            print(f"    - {col_name}: {round(sim, 4)}")

        print()

    print("====================================\n")