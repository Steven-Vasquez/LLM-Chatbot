# agent/validator.py

import json
import re


def _extract_json(text: str) -> str | None:
    """
    Extract first JSON object from text.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


def parse_agent_response(content: str):
    """
    Safely parse and validate agent JSON response.
    Returns parsed dict or None.
    """

    if not content:
        return None

    # First attempt direct parse
    try:
        data = json.loads(content)
    except Exception:
        # Try extracting JSON block
        extracted = _extract_json(content)
        if not extracted:
            return None

        try:
            data = json.loads(extracted)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    response_type = data.get("type")

    if response_type == "tool_call":
        if (
            isinstance(data.get("tool"), str)
            and isinstance(data.get("arguments"), dict)
        ):
            return data

    if response_type == "final":
        if isinstance(data.get("content"), str):
            return data

    return None
