import json
import re


def parse_json_response(text: str) -> list[dict]:
    """Strip markdown code fences and parse a JSON array from an LLM response."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def extract_response_text(response) -> str:
    """Extract the first text block from an Anthropic-style API response."""
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""
