# agent/tools.py

from typing import Callable, Dict, Any

# Import your actual implementations
from .agent_tools import web_search
from .agent_tools.vanna_txt2sql import proof_of_concept


TOOLS: Dict[str, Callable[..., Any]] = {
    "text_to_sql": proof_of_concept.vanna_text_to_sql,
    "web_search": web_search.web_search,
}



import asyncio

async def execute_tool(name: str, arguments: dict) -> str:
    """
    Executes a tool safely, supporting both sync and async tools.
    Always returns string.
    """
    if name not in TOOLS:
        return f"Error: Unknown tool '{name}'."
    try:
        tool_fn = TOOLS[name]
        if asyncio.iscoroutinefunction(tool_fn):
            result = await tool_fn(**arguments)
        else:
            result = tool_fn(**arguments)
        return str(result)
    except Exception as e:
        return f"Tool execution failed: {str(e)}"
