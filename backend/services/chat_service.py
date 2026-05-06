# Orchestrates SQL + ChromaDB operations: storing messages, summaries, prompt assembly

from datetime import datetime
import math
from typing import Dict, List, Tuple
from services import sql_service, chroma_service, ollama_service
from chromadb_client import embed_text

import numpy as np

import dotenv
dotenv.load_dotenv()
import os


def handle_new_message(chat_id, user, message):
    """
    Handles storing a new chat message in SQL and ChromaDB.
    """
    # 1. Save message in SQL
    msg_id, created_at = sql_service.insert_message(chat_id, user, message)

    # TEMP
    #print("Testing embedding generation for message:")
    #print(embed_text(message))  # Pre-cache embedding in Ollama server
 
    # 2. Prepare ChromaDB metadata
    metadata = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "user": user,
        "created_at": str(created_at),
    }

    #print("input message to message_summary is: " + str(message))
    
    # 3. Add message to ChromaDB
    doc_id = f"chat{chat_id}_msg{msg_id}"
    chroma_service.add_message_embedding(
        collection_name="messages",
        doc_id=doc_id,
        content=message,
        metadata=metadata,
    )

    # 4. Update context summary (rolling or finalize if needed)
    if os.getenv("username") == user:  # Only update context for user messages
        updated_summary = update_or_finalize_rolling_context_summary(chat_id, message, new_message_id=msg_id, current_user=user)[0]
        
        #print("Updated context summary is: \n" + str(updated_summary) + "\n\n")
        
    # 5. Decide if web search RAG is needed
    
    return {"message_id": msg_id}

def reset_current_topic_summary(chat_id, new_message, new_message_id):
    """
    Resets the current topic summary for a chat with one message.
    """
    first_summary = ollama_service.summarize_message_for_embedding(
        chat_id=chat_id,
        user=os.getenv("username"),
        message=new_message,
        )
    sql_service.set_current_context_summary(chat_id, first_summary)
    sql_service.set_starting_context_message_id(new_message_id, chat_id)
    return first_summary

def update_or_finalize_rolling_context_summary(chat_id, new_message, new_message_id, current_user, context_window_size=6):
    """
    Updates the rolling context summary for a chat based on the new message.
    """
    # 1. Retrieve current summary
    current_topic_summary = sql_service.get_current_context_summary(chat_id)
    if current_topic_summary is None: # Means the conversation is brand new
        first_summary = reset_current_topic_summary(chat_id, new_message, new_message_id)
        return first_summary, "initialized", {}
        
    # 2. Determine if to roll or finalize the context summary
    count_since_last_summary = sql_service.get_count_since_last_context_summary(chat_id)
    recent_messages = sql_service.get_last_x_messages(chat_id, count_since_last_summary)
    topic_start_message_id = recent_messages[0].get("message_id")
    
    should_finalize, debug_signals = detect_topic_drift(
        chat_id=chat_id, 
        current_topic_summary=current_topic_summary, 
        recent_messages=recent_messages,
        current_user_message=new_message,
        message_count_since_topic_start=count_since_last_summary,
        last_user_message_at=sql_service.get_message_timestamp(chat_id, message_id=new_message_id -1),
        now=sql_service.get_message_timestamp(chat_id, message_id=new_message_id)
    )
    print("Detected topic drift: " + str(should_finalize))

    # 4 Finalize current topic if needed
    if should_finalize and current_topic_summary:
        # Generate final topic summary (could be LLM-assisted)
        messages_to_finalize = recent_messages[:-1]  # Exclude the new message that started the new topic
        print("Finalizing topic with messages: \n" + str(messages_to_finalize))
        final_summary = ollama_service.summarize_messages_for_embedding(
            chat_id=chat_id,
            messages=messages_to_finalize
        )

        # Save finalized summary to ChromaDB
        now = datetime.now()
        doc_id = f"chat{chat_id}_summary_{now.strftime('%Y%m%d%H%M%S')}"
    
        chroma_service.add_message_embedding(
            collection_name="context_summaries",
            doc_id=doc_id,
            content=final_summary,
            metadata={
                "chat_id": chat_id,
                "ongoing": False,
                "start_message_id": topic_start_message_id,
                "end_message_id": messages_to_finalize[-1].get("message_id"), 
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        # Reset current topic summary in SQL
        newly_started_summary = reset_current_topic_summary(chat_id, new_message, new_message_id)
        

        return newly_started_summary, final_summary, "finalized", debug_signals

    else:
        # Incremental summary update
        updated_summary = ollama_service.update_topic_summary_incremental(
            current_summary=current_topic_summary,
            new_messages=recent_messages
        )

        # Update ongoing summary in SQL (do NOT embed in ChromaDB yet)
        sql_service.set_current_context_summary(
            chat_id=chat_id,
            new_summary=updated_summary,
        )

        return updated_summary, "updated", debug_signals
        

def detect_topic_drift(
    *,
    chat_id: int,
    current_topic_summary: str | None,
    recent_messages: List[Dict],
    current_user_message: str,
    message_count_since_topic_start: int,
    last_user_message_at: datetime | None,
    now: datetime,
) -> Tuple[bool, Dict]:
    """
    Determines if the current topic should be finalized.

    Returns:
        should_finalize (bool)
        debug_signals (dict)
    """
    # ----------------------
    # 1. Short-message guard
    # ----------------------
    def is_short_message(text: str, min_words: int = 4) -> bool:
        """
        Returns True if the message is shorter than `min_words`.
        """
        return len(text.split()) < min_words


    # ---------------------------------
    # 2. Discourse marker detection
    # ---------------------------------
    def detect_discourse_marker(recent_messages: List[Dict]) -> bool:
        """
        Detects if recent messages contain discourse cues indicating a potential topic shift.
        Returns True if any cue is found.
        """
        # List of common linguistic cues for topic shifts
        markers = [
            "now", "another question", "by the way", 
            "switching", "new topic", "can you also", "additionally",
            "actually", "on a different note"
        ]

        # Combine all recent messages into one lowercase string
        text = " ".join(m["message"].lower() for m in recent_messages)

        # Return True if any marker appears
        return any(marker in text for marker in markers)


    # ---------------------------------
    # 3. Intent classification
    # ---------------------------------
    def classify_intent(summary: str, recent_messages: List[Dict], chat_id: int) -> str:
        """
        Uses LLM to determine whether the user is continuing the current topic
        or starting a new topic.
        Returns either "CONTINUE" or "NEW_TASK".
        """

        last_human_msgs = sql_service.get_last_x_user_messages(chat_id, 2, os.getenv("username"))
        # Combine recent messages into a conversation snippet
        conversation_text = "\n".join(f"{m['user']}: {m['message']}" for m in last_human_msgs)

        prompt = f"""
    Current topic summary:
    {summary}

    Latest user messages:
    {conversation_text}

    Question:
    Has the user switched to a new topic/task, or are they continuing
    the same topic? Answer only with CONTINUE or NEW_TASK.
    """

        # Call your LLM service
        response = ollama_service.generate_ollama_response(
            prompt, 
            model=os.getenv("LLM_model"), 
            stream_setting=False)

        # Normalize the output
        result = response.strip().upper()
        print("LLM intent classification result: \n" + str(result))
        if result not in ["CONTINUE", "NEW_TASK"]:
            # fallback to conservative default
            result = "CONTINUE"

        return result
    
    # ---------------------------------
    
    debug = {}
    
    if not current_topic_summary:
        debug["reason"] = "no_active_topic"
        return False, debug

    if is_short_message(current_user_message):
        debug["reason"] = "short_message"
        return False, debug

    # 1. Intent check via LLM
    intent = classify_intent(current_topic_summary, recent_messages, chat_id)
    debug["intent"] = intent
    if intent == "NEW_TASK":
        debug["finalize_reason"] = "intent_change"
        return True, debug

    # 2. Time gap check
    time_gap_minutes = (now - last_user_message_at).total_seconds() / 60
    debug["time_gap_minutes"] = time_gap_minutes
    if time_gap_minutes > 60:
        debug["finalize_reason"] = "time_gap"
        return True, debug

    # 3. Topic saturation
    debug["message_count"] = message_count_since_topic_start
    if message_count_since_topic_start >= 50:  # configurable
        debug["finalize_reason"] = "topic_saturation"
        return True, debug

    # 4. Discourse marker (supporting info)
    debug["discourse_marker"] = detect_discourse_marker(recent_messages)
    # Not decisive, just logged

    # Default: do not finalize
    debug["finalize_reason"] = None
    return False, debug

def classify_intent(summary: str, recent_messages: list) -> str:
    """
    Determine if the user is continuing the current topic or starting a new one.

    Returns:
        "CONTINUE" or "NEW_TASK"
    """
    # Prepare recent conversation text
    context_text = "\n".join(f'{m["user"]}: {m["message"]}' for m in recent_messages)
    
    prompt = f"""
Current topic summary:
{summary}

Recent conversation:
{context_text}

Question:
Has the user switched to a new task or topic, or are they continuing the same topic?
Answer only with CONTINUE or NEW_TASK.
"""
    try:
        response = ollama_service.generate_ollama_response(prompt, model=os.getenv("fast_LLM_model"), stream_setting=False)
        result = response.strip().upper()
        if result not in ("CONTINUE", "NEW_TASK"):
            # fallback to safe default
            return "CONTINUE"
        return result
    except Exception as e:
        print(f"[classify_intent] LLM error: {e}")
        return "CONTINUE"