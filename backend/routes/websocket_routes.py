from typing import Dict
from fastapi import APIRouter, WebSocket
import json
import asyncio
from datetime import datetime

from llm_agent.agent_events import AgentEvent  # Corrected import path

router = APIRouter()

active_debug_sockets: Dict[int, WebSocket] = {}


from starlette.websockets import WebSocketDisconnect

async def emit_debug(chat_id: int, event: AgentEvent):
    websocket = active_debug_sockets.get(chat_id)
    if not websocket:
        return

    try:
        await websocket.send_text(event.model_dump_json())
    except (WebSocketDisconnect, RuntimeError):
        # Client disconnected  remove the stale socket and move on
        active_debug_sockets.pop(chat_id, None)

@router.websocket("/ws/debug/{chat_id}")
async def debug_ws(websocket: WebSocket, chat_id: int):
    await websocket.accept()
    active_debug_sockets[chat_id] = websocket
    print("Connected debug socket for:", chat_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Debug socket disconnected for: {chat_id}")
    finally:
        active_debug_sockets.pop(chat_id, None)
        
        

"""
Type	                    Purpose
----------------------------------------------------------
websocket_connection        Websocket connection established (optional content for debug)
iteration_start	            New agent loop iteration
system_prompt	            Final system prompt used
llm_request	                What was sent to LLM
llm_thinking	            Raw model reasoning (optional)
tool_call	                Tool being invoked
tool_processing             Intermediate tool processing logs (optional)
tool_result	                Tool output
final_answer	            Final response
error	                    Something failed
"""