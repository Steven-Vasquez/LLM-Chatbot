# Assembles the LLM prompt

from services import sql_service, chroma_service

default_system_prompt = f"""You are Ollama, a friendly, helpful, and creative AI assistant. 
- Provide concise, informative, and polite responses.
- Use knowledge from previous conversation summaries when relevant.
- Ask clarifying questions if needed.
- Avoid repeating information unnecessarily
"""
    

def build_prompt(
    chat_id: int, 
    system_prompt: str = default_system_prompt,
    recent_message_count: int = 5,
    retrieved_context_count: int = 10
    ):    
    
    recent_messages = sql_service.get_last_x_messages(chat_id, recent_message_count)
    
    raw_recent_messages_list = [msg["message"].strip() for msg in recent_messages]
    retrieved_context_blurbs = chroma_service.retrieve_top_x_context_embeddings(chat_id, retrieved_context_count, raw_recent_messages_to_exclude=raw_recent_messages_list)
    formatted_context_blurbs = "\n\n".join(f"{b['type'].upper()}: {b['message']}" for b in retrieved_context_blurbs)
    
    latest_user_input = recent_messages[-1]['message'] if recent_messages else ""
    
    conversation_text = "\n\n".join(f"{m['user']}: {m['message']}" for m in recent_messages[:-1])

    current_topic_summary = sql_service.get_current_context_summary(chat_id)
    
    prompt_outline = f"""
=== SYSTEM INSTRUCTIONS ===
{system_prompt}

=== CURRENT TOPIC (LIVE) ===
{current_topic_summary}
    
=== MEMORY / PAST CONVERSATION SUMMARIES ===
{formatted_context_blurbs}

=== RECENT MESSAGES ===
{conversation_text}
    
=== USER INPUT ===
{latest_user_input}

AI RESPONSE:
"""
    
    print("=== FULL PROMPT ===")
    print(prompt_outline)
    return prompt_outline




# Agent-style message builder for structured messages with roles, which can be used with more advanced prompting techniques and tools that utilize message history more effectively. This is the format expected by many agent frameworks and can be adapted to include tool calls, function calls, or other structured interactions in the future.
def build_messages(
    chat_id: int,
    system_prompt: str = default_system_prompt,
    recent_message_count: int = 5,
    retrieved_context_count: int = 10
):

    recent_messages = sql_service.get_last_x_messages(
        chat_id,
        recent_message_count
    )

    raw_recent_messages_list = [
        msg["message"].strip() for msg in recent_messages
    ]

    retrieved_context_blurbs = chroma_service.retrieve_top_x_context_embeddings(
        chat_id,
        retrieved_context_count,
        raw_recent_messages_to_exclude=raw_recent_messages_list
    )

    current_topic_summary = sql_service.get_current_context_summary(chat_id)

    messages = []

    # 1?? System persona
    messages.append({
        "role": "system",
        "content": system_prompt.strip()
    })

    # 2?? Current topic
    if current_topic_summary:
        messages.append({
            "role": "system",
            "content": f"Current topic (live):\n{current_topic_summary}"
        })

    # 3?? Retrieved memory
    if retrieved_context_blurbs:
        formatted_context = "\n\n".join(
            f"{b['type'].upper()}: {b['message']}"
            for b in retrieved_context_blurbs
        )

        messages.append({
            "role": "system",
            "content": f"Relevant past conversation memory:\n{formatted_context}"
        })

    # 4?? Recent conversation (properly structured)
    for m in recent_messages:
        role = "assistant" if m["user"] == "Ollama" else "user"

        messages.append({
            "role": role,
            "content": m["message"].strip()
        })

    return messages
