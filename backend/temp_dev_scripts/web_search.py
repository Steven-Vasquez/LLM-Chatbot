"""
Live Web Search + RAG Pipeline (Free, No API)
DuckDuckGo HTML + MiniLM embeddings + URL-based citations

Run:
    pip install requests beautifulsoup4 sentence-transformers scikit-learn
    python web_search.py
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import textwrap
from typing import List, Dict
from dataclasses import dataclass
import json
from urllib.parse import urlparse

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os


# -----------------------------
# CONFIG
# -----------------------------
TEST_QUESTION = "Which Python 3.13 PEP removed the GIL, and what behavior did it change?"

MAX_SEARCH_RESULTS = 5
MAX_PAGES_TO_FETCH = 3

CHUNK_SIZE = 600
CHUNK_OVERLAP = 150
TOP_K_CHUNKS = 6
MAX_CHUNKS_PER_SOURCE = 2

REQUEST_TIMEOUT = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/143.0.0.0 Safari/537.36"
)

OLLAMA_MODEL = os.getenv("LLM_model", "gemma3:12b")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

HEADERS = {"User-Agent": USER_AGENT}


# -----------------------------
# DATA STRUCTURES
# -----------------------------
@dataclass
class WebDocument:
    title: str
    url: str
    content: str


@dataclass
class Chunk:
    text: str
    source_id: str
    url: str


# -----------------------------
# EMBEDDING MODEL (CACHED)
# -----------------------------
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def embed_texts(texts: List[str]) -> np.ndarray:
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True)


# -----------------------------
# STEP 1: DUCKDUCKGO SEARCH
# -----------------------------
def duckduckgo_search(query: str, max_results: int) -> List[str]:
    print(f"[1] Searching web via DuckDuckGo: {query}")

    url = "https://html.duckduckgo.com/html/"
    try:
        resp = requests.post(
            url,
            data={"q": query},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] DuckDuckGo search failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []

    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href and href.startswith("http"):
            links.append(href)
        if len(links) >= max_results:
            break

    print(f"[DEBUG] URLs found: {links}")
    return links


# -----------------------------
# STEP 2: FETCH PAGE CONTENT
# -----------------------------
def fetch_page_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# -----------------------------
# STEP 3: CHUNKING
# -----------------------------
def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + size]
        if len(chunk) >= 200:
            chunks.append(chunk)
        start += size - overlap
    return chunks


# -----------------------------
# STEP 4: EMBEDDING-BASED RANKING
# -----------------------------
def rank_chunks(question: str, chunks: List[Chunk], top_k: int) -> List[Chunk]:
    print("[3] Ranking chunks with MiniLM embeddings...")

    query_embedding = embed_texts([question])[0]
    chunk_embeddings = embed_texts([c.text for c in chunks])

    similarities = cosine_similarity([query_embedding], chunk_embeddings)[0]
    ranked_indices = np.argsort(similarities)[::-1]

    selected = []
    per_source_count = {}

    for idx in ranked_indices:
        chunk = chunks[idx]
        count = per_source_count.get(chunk.source_id, 0)
        if count < MAX_CHUNKS_PER_SOURCE:
            selected.append(chunk)
            per_source_count[chunk.source_id] = count + 1
        if len(selected) >= top_k:
            break

    return selected


# -----------------------------
# STEP 5: BUILD RAG CONTEXT
# -----------------------------
def build_rag_context(chunks: List[Chunk]) -> str:
    formatted = []
    for chunk in chunks:
        formatted.append(f"[{chunk.source_id}] {chunk.url}\n{chunk.text}")
    return "\n\n".join(formatted)


def build_sources_section(chunks: List[Chunk]) -> str:
    """
    Builds a sources section for the prompt listing each source ID and its URL.
    """
    seen = {}
    lines = []
    for chunk in chunks:
        if chunk.source_id not in seen:
            domain = urlparse(chunk.url).netloc
            lines.append(f"[{chunk.source_id}] {domain}  {chunk.url}")
            seen[chunk.source_id] = True
    return "\n".join(lines)


# -----------------------------
# STEP 6: FINAL PROMPT
# -----------------------------
def build_final_prompt(question: str, rag_context: str, sources_section: str) -> str:
    prompt = f"""
You are answering a question using ONLY the sources below.
Each source is labeled [S1], [S2], etc., and includes its URL.
Cite the sources in your answer by referring to these labels.
Do not invent sources.

=== SOURCES ===
{rag_context}

=== SOURCES LIST ===
{sources_section}

=== QUESTION ===
{question}

=== ANSWER ===
"""
    return textwrap.dedent(prompt)


# -----------------------------
# STEP 7: CALL OLLAMA
# -----------------------------
def generate_ollama_response(prompt: str) -> str:
    try:
        resp = requests.post(
            "http://10.1.3.19:11434/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt},
            stream=True
        )

        full_text = ""
        for line in resp.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                full_text += data.get("response", "")
            except Exception:
                continue

        return " ".join(full_text.split())

    except Exception as e:
        return f"[ERROR] Failed to call Ollama: {e}"


# -----------------------------
# MAIN
# -----------------------------
def main():
    urls = duckduckgo_search(TEST_QUESTION, MAX_SEARCH_RESULTS)
    urls = urls[:MAX_PAGES_TO_FETCH]

    documents = []
    for url in urls:
        print(f"[2] Fetching page: {url}")
        text = fetch_page_text(url)
        if text:
            documents.append(WebDocument(title=url, url=url, content=text))
        time.sleep(1)

    if not documents:
        print("\n=== FINAL ANSWER ===\nNo usable web content found.")
        return

    # Create chunks retaining source_id and URL
    all_chunks: List[Chunk] = []
    for i, doc in enumerate(documents):
        source_id = f"S{i+1}"
        for chunk_text_piece in chunk_text(doc.content, CHUNK_SIZE, CHUNK_OVERLAP):
            all_chunks.append(Chunk(text=chunk_text_piece, source_id=source_id, url=doc.url))

    # Rank chunks and select top-K
    ranked_chunks = rank_chunks(TEST_QUESTION, all_chunks, TOP_K_CHUNKS)

    # Build RAG context and sources list
    rag_context = build_rag_context(ranked_chunks)
    sources_section = build_sources_section(ranked_chunks)

    # Build final prompt
    final_prompt = build_final_prompt(TEST_QUESTION, rag_context, sources_section)

    print("\n=== FINAL RAG PROMPT ===\n")
    print(final_prompt)

    # Generate answer
    answer = generate_ollama_response(final_prompt)

    print("\n=== FINAL ANSWER ===\n")
    print(answer)


if __name__ == "__main__":
    main()
