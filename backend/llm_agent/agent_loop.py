# agent/loop.py

from copy import deepcopy
from typing import List, Dict, Callable, Awaitable, Optional
import asyncio

from .schema import get_response_schema_description
from .validator import parse_agent_response
from .tools import execute_tool
from .agent_events import (
    AgentEvent, 
    WebsocketConnectionEvent, 
    IterationStartEvent,
    SystemPromptEvent,
    LLMRequestEvent,
    LLMThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
    FinalAnswerEvent,
    ErrorEvent
)

import sys
from pathlib import Path
import pprint
pp = pprint.PrettyPrinter(indent=2)

sys.path.append(str(Path(__file__).resolve().parents[1]))
#print("Current sys.path:", sys.path)
from services import ollama_service

MAX_ITERATIONS = 25


async def run_agent_loop(
    call_llm: Callable[[List[Dict]], Dict],
    base_messages: List[Dict],
    enabled_tools: List[str] = None,
    max_iterations: int = MAX_ITERATIONS,
    verbose: bool = True,
    debug_emit: Optional[Callable[[AgentEvent], Awaitable[None]]] = None
) -> str:
    """
    Async agent loop for LLM chatbot agent.
    Handles tool calls and LLM responses using async/await.
    """
    if debug_emit:
        await debug_emit(WebsocketConnectionEvent(content="DEBUG CONNECTED"))

    enabled_tools = enabled_tools or []
    messages = deepcopy(base_messages)
    messages.append({
        "role": "system",
        "content": get_response_schema_description(enabled_tools).strip()
    })

    for iteration in range(max_iterations):
        iter_num = iteration + 1

        # Emit IterationStartEvent
        if debug_emit:
            await debug_emit(IterationStartEvent(iteration=iter_num))

        if verbose:
            print(f"\n========== ITERATION {iter_num} ==========")
            print("Current Messages:")
            for m in messages:
                print(f"{m['role'].upper()}: {m['content'][:200]}")

        # Await LLM call if it's async
        if asyncio.iscoroutinefunction(call_llm):
            llm_msg = await call_llm(messages)
        else:
            llm_msg = call_llm(messages)

        # Emit LLMRequestEvent
        if debug_emit:
            await debug_emit(LLMRequestEvent(iteration=iter_num, messages=deepcopy(messages)))

        if not isinstance(llm_msg, dict):
            if debug_emit:
                await debug_emit(ErrorEvent(message="LLM returned invalid response format."))
            return "Error: LLM returned invalid response format."
        
        if verbose:
            print(f"TYPE OF LLM RESPONSE: {type(llm_msg)}")
            print(f"LLM RESPONSE RAW: {llm_msg}")
            print("\nLLM RAW RESPONSE:")
            pp.pprint(llm_msg)

        content = llm_msg.get("content", "")

        if verbose:
            print("\nLLM CONTENT:")
            print(content)
            if debug_emit:
                await debug_emit(LLMThinkingEvent(iteration=iter_num, content=content))

        parsed = parse_agent_response(content)

        # ---------- Malformed JSON ----------
        if parsed is None:
            if debug_emit:
                await debug_emit(ErrorEvent(message="Malformed JSON. Asking model to fix response."))
            if verbose:
                print("!!! Malformed JSON. Asking model to fix response.")

            messages.append({
                "role": "assistant",
                "content": content
            })
            messages.append({
                "role": "system",
                "content": "Your previous response was invalid. Respond ONLY with valid JSON following the required schema."
            })
            continue

        # ---------- Tool Call ----------
        if parsed["type"] == "tool_call":
            tool_name = parsed["tool"]
            arguments = parsed["arguments"]

            if debug_emit:
                await debug_emit(ToolCallEvent(iteration=iter_num, tool=tool_name, args=arguments))
            if verbose:
                print(f"- Tool Call Requested: {tool_name}")
                print(f"Arguments: {arguments}")

            tool_args = {**arguments, "debug_emit": debug_emit}
            # Await tool execution if async
            if asyncio.iscoroutinefunction(execute_tool):
                tool_result = await execute_tool(tool_name, tool_args)
            else:
                tool_result = execute_tool(tool_name, tool_args)

            if debug_emit:
                await debug_emit(ToolResultEvent(iteration=iter_num, tool=tool_name, result=tool_result))
            if verbose:
                print("- Tool Result:")
                print(tool_result)

            messages.append({
                "role": "assistant",
                "content": content
            })
            messages.append({
                "role": "system",  # was "tool"
                "content": f"Tool '{tool_name}' returned:\n{tool_result}"
            })
            continue

        # ---------- Final ----------
        if parsed["type"] == "final":
            if debug_emit:
                await debug_emit(FinalAnswerEvent(content=parsed["content"]))
            if verbose:
                print("Final Answer Reached.")
            return parsed["content"]

    if debug_emit:
        await debug_emit(ErrorEvent(message="Agent stopped after max iterations"))
    return "(Agent stopped after max iterations)"


def main():
    question_to_ask  = "What kinds of car parts do we sell according to our database? what other companies sell similar parts, do search to find out."
    base_messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": question_to_ask
        }
    ]

    print("Running agent loop test...\n")

    final_answer = asyncio.run(run_agent_loop(
        call_llm=ollama_service.call_llm,
        base_messages=base_messages
    ))

    print("\nFinal Answer:")
    print(final_answer)


if __name__ == "__main__":
    main()