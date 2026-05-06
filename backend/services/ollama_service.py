import requests
import json
from services import sql_service

from dotenv import load_dotenv
import os

load_dotenv()

def generate_ollama_response(prompt: str, model: str = os.getenv("LLM_model"), stream_setting=True) -> str:
    """
    Sends a prompt to an Ollama server and returns the full text response.
    Handles multi-line JSON streaming automatically.
    """
    url = "http://10.1.3.19:11434/api/generate"
    response = requests.post(url, 
                             json={"model": model, "prompt": prompt},
                             stream=stream_setting)

    full_text = ""

    # The response body contains multiple JSON lines
    for line in response.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if "response" in data:
                full_text += data["response"]
        except json.JSONDecodeError:
            # Skip malformed or incomplete lines
            continue

    full_text = " ".join(full_text.split())  # flatten newlines & collapse spaces
    return full_text

import requests
import os

OLLAMA_CHAT_URL = "http://10.1.3.19:11434/api/chat"

# Simple wrapper to call Ollama /api/chat for agent responses
def call_llm(messages, model=os.getenv("very_smart_model")):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]
    except requests.exceptions.HTTPError as e:
        # Log more info about the server response
        print("HTTPError:", e)
        print("Response content:", response.text)
        raise
    except Exception as e:
        print("Unexpected error calling Ollama:", e)
        raise

def summarize_messages_for_embedding(
    chat_id: int,
    messages: list,  # list of dicts: {"user":..., "message":...}
):
    """
    Generate a concise, embedding-friendly summary for a set of messages.
    Maintains key factual details (e.g., entities like car parts) and overall meaning.
    """

    conversation_text = "\n".join(f"{m['user']}: {m['message']}" for m in messages)

    prompt = f"""
You are preparing text for vector embedding storage.

Write a concise, 1-2 sentence factual summary (max 30 words) 
describing the main ideas of the following conversation.
Focus on preserving **critical factual details** (e.g., entities, specific items being discussed)
and the overall meaning or intent.
Avoid filler or tone, and produce a single coherent summary.

Conversation:
{conversation_text}

Respond only with the summary text:
"""

    #print("Rolling context summary prompt:\n", prompt)
    summary = generate_ollama_response(
        prompt.strip(),
        model=os.getenv("fast_summarization_LLM_model"),
        stream_setting=False
    )

    # Clean output
    if summary:
        summary = summary.strip().strip('"').replace("\n", " ")

    return summary or ""

def update_topic_summary_incremental(
    current_summary: str,
    new_messages: list,  # only messages since last summary update
):
    """
    Incrementally updates an existing topic summary with new information.
    Preserves existing facts unless explicitly changed.
    """

    new_text = "\n".join(f"{m['user']}: {m['message']}" for m in new_messages)

    prompt = f"""
You are maintaining a concise topic summary.

CURRENT SUMMARY:
{current_summary}

NEW MESSAGES:
{new_text}

Update the summary to include any NEW factual information, decisions,
constraints, or direction changes introduced by the new messages.

Rules:
- Preserve existing facts unless contradicted
- Do NOT rewrite unrelated parts
- Keep the summary concise (1-2 sentences, max 30 words)
- Focus on entities, decisions, and technical details
- Output ONLY the updated summary text
"""

    updated_summary = generate_ollama_response(
        prompt.strip(),
        model=os.getenv("fast_summarization_LLM_model"),
        stream_setting=False
    )

    if updated_summary:
        updated_summary = updated_summary.strip().strip('"').replace("\n", " ")

    return updated_summary or current_summary

def update_topic_summary_incremental(
    current_summary: str,
    new_messages: list,  # only messages since last summary update
):
    """
    Incrementally updates an existing topic summary with new information.
    Preserves existing facts unless explicitly changed.
    """

    new_text = "\n".join(f"{m['user']}: {m['message']}" for m in new_messages)

    prompt = f"""
You are maintaining a concise topic summary.

CURRENT SUMMARY:
{current_summary}

NEW MESSAGES:
{new_text}

Update the summary to include any NEW factual information, decisions,
constraints, or direction changes introduced by the new messages.

Rules:
- Preserve existing facts unless contradicted
- Do NOT rewrite unrelated parts
- Keep the summary concise (12 sentences, max 30 words)
- Focus on entities, decisions, and technical details
- Output ONLY the updated summary text
"""

    updated_summary = generate_ollama_response(
        prompt.strip(),
        model=os.getenv("fast_summarization_LLM_model"),
        stream_setting=False
    )

    if updated_summary:
        updated_summary = updated_summary.strip().strip('"').replace("\n", " ")

    return updated_summary or current_summary

def summarize_message_for_embedding(
    chat_id: int,
    user: str,
    message: str,
):
    """
    Generate a concise, embedding-friendly summary of a chat message using Ollama.
    """

    prompt = f"""
    You are preparing text for vector embedding storage.

    Write a concise, one sentence (10-20 words) factual summary describing the main idea or intent of the message.
    Avoid filler or tone, focus on meaning only.

    Message ({user}): "{message}"

    Respond only with the summary text:
    """

    #print("The summary request prompt is:\n" + str(prompt))
    # Chose mistral-nemo:12b as it follows strict format and is concise
    summary = generate_ollama_response(prompt.strip(), model=os.getenv("fast_summarization_LLM_model"), stream_setting=False)
    # --- 5. Clean output ---
    if summary:
        summary = summary.strip().strip('"').replace("\n", " ")

    return summary or ""

def summarize_recent_context(
    chat_id: int,
    user: str,
    message: str,
    context_window: int = 4,
):
    """
    Generate a concise, embedding-friendly summary of a chat message using Ollama.
    Adapts between intent-based and content-based summarization.
    """

    # --- 1. Fetch recent context ---
    history = sql_service.get_last_x_messages(chat_id, context_window)
    history.pop() # Remove the last message (the "message" is already included in prompt)
    #print("history is: " + str(history))
    
    recent_context = "\n".join([
        f"{m['user']}: {m['message']}" for m in history
    ])

    # --- 2. Classify the message ---
    word_count = len(message.split())
    short_or_ambiguous = word_count < 6 or message.strip().endswith("?")
    long_or_contentful = word_count > 25  # heuristic for "story" or detailed answer

    # --- 3. Build adaptive prompt ---
    if short_or_ambiguous:
        # infer meaning from context
        prompt = f"""
        You are preparing text for vector embedding storage.

        Given the chat context, infer the intended meaning of the latest message even if it's short or vague.
        Write one neutral, factual sentence (<=15 words) summarizing its intent or meaning.

        Context:
        {recent_context}

        Latest message ({user}): "{message}"

        Respond only with the summary text:
        """
    elif long_or_contentful:
        # summarize the *content*, not just intent
        prompt = f"""
            You are preparing text for vector embedding storage.

            The following message is long or detailed (like a story, explanation, or response). 
            Summarize its *core content* or main ideas clearly and concisely, within 1-2 short sentences (=30 words). 
            Avoid emotional tone or filler.

            Message:
            {message}

            Respond only with the summary text:
            """
    else:
        # default: single concise summary of meaning
        prompt = f"""
        You are preparing text for vector embedding storage.

        Write a concise, one sentence (10-20 words) factual summary describing the main idea or intent of the message.
        Avoid filler or tone, focus on meaning only.

        Message: "{message}"

        Respond only with the summary text:
        """

    # --- 4. Generate summary ---
    # Chose mistral-nemo:12b as it follows strict format and is concise
    summary = generate_ollama_response(prompt.strip(), model=os.getenv("fast_summarization_LLM_model"), stream_setting=False)
    print("The generated summary is: " + str(summary))
    # --- 5. Clean output ---
    if summary:
        summary = summary.strip().strip('"').replace("\n", " ")

    return summary or ""
