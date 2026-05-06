import os
import dotenv
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List
import traceback

from services import ollama_service, prompt_builder
from llm_agent.agent_loop import run_agent_loop

dotenv.load_dotenv()

router = APIRouter(prefix="/api", tags=["ollama"])

class OllamaPromptRequest(BaseModel):
    message: str

@router.post("/send-ollama-prompt")
async def ai_reply(request: OllamaPromptRequest):
    user_msg = request.message
    if not user_msg:
        raise HTTPException(status_code=400, detail="Missing 'message' in request")
    prompt = f"{os.getenv('username')}: {user_msg}\n{os.getenv('chatbot_name')}:"
    try:
        reply = ollama_service.generate_ollama_response(prompt, model=os.getenv("LLM_model"), stream_setting=True)
        return {"reply": reply}
    except Exception as e:
        print("Error in /send-ollama-prompt:", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/build-prompt/{chat_id}')
async def build_prompt_route(chat_id: int):
    try:
        prompt = prompt_builder.build_prompt(chat_id)
        print("Built prompt:\n", prompt)
        #print("Built messages:\n", prompt_builder.build_messages(chat_id))
        return {"prompt": prompt}
    except Exception as e:
        print("Error in /build-prompt:", e)
        raise HTTPException(status_code=500, detail=str(e))



class AgentRequest(BaseModel):
    mode: str
    tools: List[str]
    
@router.post('/run-agent/{chat_id}')
async def run_agent_route(chat_id: int, request: AgentRequest):
    import asyncio
    from .websocket_routes import emit_debug
    
    async def debug_callback(event: dict):
        await emit_debug(chat_id, event)
        #await asyncio.sleep(0)  # Small sleep to prevent overwhelming the websocket
        
    try:
        built_messages = prompt_builder.build_messages(chat_id)

        print("Received mode:", request.mode)
        print("Received tools:", request.tools)

        final_answer = await run_agent_loop(
            call_llm=ollama_service.call_llm,
            base_messages=built_messages,
            enabled_tools=request.tools,
            debug_emit=debug_callback
        )
        return {"final_answer": final_answer}
    except Exception as e:
        print("Error in /run-agent:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

"""
# For testing the route
@ollama_bp.route('/ai', methods=['POST'])
def ai_reply():
    print("Received request for AI reply")
    data = request.get_json(force=True)
    msg = data.get('message', '')
    print("Message:", msg)
    return jsonify({"reply": f"Echo: {msg}"})
"""