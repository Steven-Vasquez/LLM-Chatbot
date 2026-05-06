Also creates Vanna ChromaDB collection for storing agent memories

1. Ensure backend server.py is running on port 5000
2. Run Vanna agent with `python vanna_test.py` and access the Vanna agent testing UI at http://localhost:8000/
3. python -m http.server 8001, and access the chatbot app at http://localhost:8001/QA_Chatbot/components/chat.html

In the `venv/lib/python3.12/site-packages/vanna/tools/visualize_data.py` file, find the line:

df = pd.read_csv(io.StringIO(csv_content))

(line ~74) and replace it with:
###
df = pd.read_csv(
    io.StringIO(csv_content),
    dtype=str
)

# Convert real numeric columns back to numbers for plotting
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer') \
            .fillna(df[col])
###

To eliminate the issue of Vanna sometimes naively casting string values as ints and resulting in mixed types errors when platting with the VisualizeDataTool.