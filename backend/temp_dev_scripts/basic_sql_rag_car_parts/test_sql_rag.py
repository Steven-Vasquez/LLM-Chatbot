import sys
import requests
import dotenv
dotenv.load_dotenv()
import os

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


from sql_connection import get_db_connection
from services.ollama_service import generate_ollama_response

conn = get_db_connection()
if not conn:
    raise Exception("Failed to connect to SQL Server")
cursor = conn.cursor()


# ============ SYSTEM PROMPT ============

SYSTEM_PROMPT = """
You are a SQL generator for a car parts compatibility database.

ONLY output valid T-SQL. No explanations. No markdown.

Database schema:

TABLE vehicles (
    id INT,
    make NVARCHAR,
    model NVARCHAR,
    year INT,
    trim NVARCHAR,
    engine NVARCHAR
)

TABLE parts (
    id INT,
    part_number NVARCHAR,
    name NVARCHAR,
    category NVARCHAR
)

TABLE part_fitment (
    id INT,
    part_id INT,
    make NVARCHAR,
    model NVARCHAR,
    year_start INT,
    year_end INT,
    trim NVARCHAR,
    engine NVARCHAR,
    notes NVARCHAR
)

Rules you MUST follow:
- JOIN parts to part_fitment on parts.id = part_fitment.part_id
- A vehicle fits when:
    year BETWEEN year_start AND year_end
    AND make/model/trim/engine match
- If user asks "does it fit", return rows proving fitment
- If user asks "what fits", return matching parts
"""

# ============ SQL EXECUTOR ============

def run_sql(sql):
    try:
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, rows, None
    except Exception as e:
        return None, None, str(e)


# ============ SQL-RAG PIPELINE ============

def sql_rag(question):
    print("\n?? Question:", question)

    # Step 1  Generate SQL
    prompt = SYSTEM_PROMPT + f"\nUser question:\n{question}\n"
    sql = generate_ollama_response(prompt, "deepseek-r1:32b")


    print("LLM output before extraction:\n", sql)
    start = sql.rfind("SELECT")
    #backtick_indices = [i for i, c in enumerate(sql) if c == '`']
    #end = backtick_indices[-3]  # third-to-last backtick
    sql = sql[start:].strip()
    if not sql.endswith(";"):
        sql += ";"
    print("\n?? Generated SQL:\n", sql)

    # Step 2  Execute SQL
    cols, rows, err = run_sql(sql)

    if err:
        print("\n? SQL Error:", err)
        return

    print(f"\n?? Rows returned: {len(rows)}")

    # Step 3  Explain result
    explanation_prompt = f"""
The SQL query returned these results.

Columns: {cols}
Rows: {rows}

Explain the answer to the user question in plain English:

{question}
"""

    explanation = generate_ollama_response(explanation_prompt)

    print("\n?? Explanation:\n", explanation)


# ============ INTERACTIVE TEST LOOP ============

def main():
    print("\n=== SQL RAG Car Parts Compatibility Test ===")
    print("Type a question, or 'exit'\n")

    sample_questions = [
        "Will part P0010 fit a 2017 Ford Focus Touring 1.8L?", # yes
        "Will part P0042 fit a 2018 Honda Civic EX 2.0L?", # no
        "Which brake rotors fit a 2018 Toyota Corolla Touring 1.8L?", # Brake Rotor 3
        "Does P0010 fit any Toyota from 2016?",
        "Which parts fit both a 2016 and 2020 Civic EX 2.0L?",
        "Why doesn't P0033 fit my 2018 Honda Civic EX 2.0L?"
    ]

    print("Sample questions:")
    for q in sample_questions:
        print("-", q)
    print("\n")

    while True:
        q = input("Ask> ")
        if q.lower() in ["exit", "quit"]:
            sys.exit(0)
        sql_rag(q)


if __name__ == "__main__":
    main()
