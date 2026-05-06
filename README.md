# LLM Chatbot Platform

A context-aware AI chatbot platform built for isolated chat instances, dynamic memory management, and autonomous agentic functionality. Designed as both a learning project and a foundation for a customer service chatbot, the system supports real-time conversation, long-term topic memory, and extensible agent tools for database querying and live web search.

---

## Features

- Real-time messaging between user and chatbot
- Isolated chat instances supporting multiple simultaneous conversations
- Dynamic memory pipeline with incremental topic summaries and topic drift detection
- LLM agent loop enabling autonomous, multi-step tool usage
- **Vanna Text-to-SQL tool** — semantic schema retrieval + natural language to SQL against a live MSSQL database
- **Web Search tool** — live RAG pipeline using DuckDuckGo, chunk ranking, and cited LLM responses
- Context-aware prompt building combining summaries, memory, and recent chat history
- Persistent storage via MSSQL and ChromaDB vector embeddings

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, JavaScript, CSS |
| Backend | Python, Flask, FastAPI |
| Structured Database | MSSQL (via SQLAlchemy + ODBC) |
| Vector Database | ChromaDB |
| LLM | Ollama (local) — Qwen3:30b, Gemma3:12b, ... |
| Embeddings | Ollama — nomic-embed-text |
| Text-to-SQL | Vanna AI |
| Web Scraping | requests, BeautifulSoup, ddgs |

---

## Project Structure

```
/
├── .env.example
├── requirements.txt
│
├── backend/
│   ├── server.py                   # FastAPI entry point
│   ├── server_runner.py
│   ├── chromadb_client.py
│   ├── sql_connection.py
│   │
│   ├── llm_agent/                  # Agent loop, tools, and validation
│   │   └── agent_tools/
│   │       ├── web_search.py       # Web search + RAG pipeline
│   │       └── vanna_txt2sql/      # Text-to-SQL via Vanna
│   │
│   ├── routes/                     # API route handlers
│   └── services/                   # Business logic layer
│
├── components/
│   └── chat.html                   # Chatbot frontend
│
├── css/
│   └── style.css
│
├── js/
│   └── chat.js
│
├── diagrams/                       # Architecture and flow diagrams
├── notes/                          # Dev notes and prompt drafts
└── sql_queries_quick_access/       # Utility SQL scripts
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Ollama running locally with the following models pulled:
  - `qwen3:30b`
  - `gemma3:12b`
  - `nomic-embed-text:latest`
- MSSQL database accessible via ODBC Driver 18
- ChromaDB (installed via pip)

### Installation

```bash
git clone <repo-url>
cd <repo-folder>
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Generate Schema Embeddings

This only needs to be run once, or whenever `column_semantics.py` is updated.

```bash
python create_schema_embeddings.py
```

This reads column descriptions from `column_semantics.py`, generates embeddings via Ollama, and saves them to `schema_embeddings.json`. To customize to your database for the Text2SQL tool using Vanna, update TABLE_SEMANTICS in `create_schema_embeddings.py` and the populate the entire `column_semantics.py` file using your database column descriptors.

### Running the App

**1. Start the main backend server (Flask) on port 5000:**
```bash
python server.py
```

**2. Start the Vanna agent server on port 8000:**
```bash
python vanna_server.py
```

**3. Serve the frontend on port 8001:**
```bash
python -m http.server 8001
```

Access the chatbot at: [http://localhost:8001/QA_Chatbot/components/chat.html](http://localhost:8001/QA_Chatbot/components/chat.html)

You can also access the Vanna agent testing UI directly at: [http://localhost:8000/](http://localhost:8000/)

---

## Tools

### Vanna (Text-to-SQL)

Converts natural language questions into SQL queries against a live MSSQL database. Uses a `SemanticSchemaEnhancer` to embed the user query and retrieve only the most relevant tables and columns via cosine similarity, keeping prompts lean and accurate. A SQLAlchemy engine event listener enforces SQL safety guards before any query reaches the database.

### Web Search

A full RAG pipeline for live web questions. Searches DuckDuckGo, fetches and cleans the top pages, chunks the content, ranks chunks by embedding similarity to the query, and passes the top results to a local LLM for a cited answer.

---

## Known Issues and Fixes

### Vanna VisualizeDataTool — Mixed Type Error

When using the `VisualizeDataTool`, Vanna may naively cast string values as integers, causing mixed type errors during plotting.

In `venv/lib/python3.12/site-packages/vanna/tools/visualize_data.py`, locate the following line (~line 74):

```python
df = pd.read_csv(io.StringIO(csv_content))
```

Replace it with:

```python
df = pd.read_csv(
    io.StringIO(csv_content),
    dtype=str
)

# Convert real numeric columns back to numbers for plotting
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer') \
            .fillna(df[col])
```

---

## Configuration Notes

- Database connection strings and Ollama host URLs are currently hardcoded in `vanna_server.py` and `web_search.py`. Move these to a `.env` file for any shared or production deployment.
- SQL guardrails in `vanna_server.py` are intentionally conservative. Once expected query patterns are known, refine the guard logic accordingly.
- The Vanna agent tool registry has `VisualizeDataTool` and memory tools commented out. Uncomment and register them as needed for your use case.

---

## Purpose

This project was built as a learning exercise and a proof of concept for a customer service chatbot. The goal was a modular base that can be extended with custom agent tools depending on the types of customer inquiries expected.
