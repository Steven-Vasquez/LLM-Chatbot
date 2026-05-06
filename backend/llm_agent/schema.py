# agent/schema.py

TOOL_CALL = "tool_call"
FINAL = "final"

def build_tool_instructions(enabled_tools: list[str]) -> str:
    tool_docs = []

    if "web_search_tool" in enabled_tools:
        tool_docs.append("""
web_search(query: string)
Use for:
- Current events
- Information you do not have access to
- Information not in your training data
- Anything requiring real time or historical event data
Do NOT use for internal database queries.
""")

    if "database_tool" in enabled_tools:
        tool_docs.append("""
text_to_sql(query: string)
Use for:
- Product inventory
- Internal database queries
Do NOT use for web searches.
""")

    return "\n".join(tool_docs)

def get_response_schema_description(enabled_tools: list) -> str:
    """
    Returns the response schema description string, including only the tools present in enabled_tools.
    """
    tool_instructions = build_tool_instructions(enabled_tools)

    return f"""You are operating in TOOL MODE.

You may use the following tools:
{tool_instructions}

When you want to use a tool, respond ONLY with a JSON object in the following format:

{{
  "type": "tool_call",
  "tool": "tool_name",
  "arguments": {{ "query": "..." }}
}}

If a tool is required, respond ONLY in this JSON format:

{{
  "type": "tool_call",
  "tool": "tool_name",
  "arguments": {{ "query": "..." }}
}}

If no tool is required, respond ONLY in:

{{
  "type": "final",
  "content": "..."
}}

Rules:
- Output MUST be valid JSON.
- Do NOT use markdown.
- Do NOT include explanations outside JSON.
- Do NOT include trailing commas.
"""