
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from services import chat_service, sql_service
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/chat", tags=["chat"])

class CreateChatRequest(BaseModel):
    user: str

class PostMessageRequest(BaseModel):
    chat_id: int
    user: str
    message: str

@router.get("/test-sql")
async def test_sql_connection():
    version = sql_service.test_connection()
    if not version:
        raise HTTPException(status_code=500, detail="Failed to connect to SQL Server")
    return {"message": "Connected successfully!", "sql_version": version}

@router.post("/create-chat")
async def create_chat(request: CreateChatRequest):
    if not request.user:
        raise HTTPException(status_code=400, detail="Missing user")
    chat_id = sql_service.create_chat(request.user)
    return {"chat_id": chat_id}

@router.post("/post-message")
async def post_message(request: PostMessageRequest):
    result = chat_service.handle_new_message(request.chat_id, request.user, request.message)
    return result

@router.get("/get-chat-history/{chat_id}", response_class=PlainTextResponse)
async def get_chat_history(chat_id: int):
    try:
        rows = sql_service.get_messages(chat_id)
        if not rows:
            return PlainTextResponse("No messages found.", status_code=200)
        chat_history = "\n".join(f"{row[0]}: {row[1]}" for row in rows)
        return PlainTextResponse(chat_history, status_code=200)
    except Exception as e:
        print("Error in get_chat_history:", e)
        return PlainTextResponse(f"Error: {str(e)}", status_code=500)

@router.get("/get-active-chats")
async def get_active_chats_route():
    rows = sql_service.get_active_chats()
    if rows is None:
        raise HTTPException(status_code=500, detail="Database error occurred while fetching chats")
    if not rows:
        return []
    chats = []
    for chat_id, user, last_updated in rows:
        if isinstance(last_updated, datetime):
            last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
        chats.append({
            "chat_id": chat_id,
            "user": user,
            "last_updated": last_updated
        })
    return chats

@router.get("/get-chat-messages")
async def get_chat_messages(chat_id: Optional[int] = Query(None)):
    if chat_id is None:
        raise HTTPException(status_code=400, detail="Missing chat_id")
    try:
        rows = sql_service.get_messages(chat_id)
        messages = []
        for row in rows:
            user, message, created_at = row
            if isinstance(created_at, datetime):
                created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append({
                "user": user,
                "message": message,
                "created_at": created_at
            })
        return messages
    except Exception as e:
        print("SQL error in /api/chat/get-chat-messages:", e)
        raise HTTPException(status_code=500, detail=str(e))