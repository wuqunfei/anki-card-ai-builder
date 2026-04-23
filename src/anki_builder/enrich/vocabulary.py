import json
import re

import anthropic

MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"


def _build_text_prompt(text: str, target_language: str, source_language: str) -> str:
    return (
        f"Extract vocabulary words from the following text. The text is in "
        f"{target_language} (target language) and {source_language} (source language).\n\n"
        f"For each word, extract any available information: word, translation, "
        f"pronunciation, example_sentence, part_of_speech.\n\n"
        f"Return ONLY a JSON array of objects. Each object should have the fields "
        f"that are present in the source. Do not generate content that isn't in "
        f"the source text — only extract what's there.\n\n"
        f"Text:\n{text}"
    )


def _parse_vocabulary_response(text: str) -> list[dict]:
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def extract_vocabulary_with_ai(
    target_language: str,
    source_language: str,
    minimax_api_key: str = "",
    text: str | None = None,
) -> list[dict]:
    if not text:
        return []

    client = anthropic.Anthropic(api_key=minimax_api_key, base_url=MINIMAX_BASE_URL)
    response = client.messages.create(
        model=MINIMAX_MODEL,
        max_tokens=16384,
        messages=[{
            "role": "user",
            "content": _build_text_prompt(text, target_language, source_language),
        }],
        temperature=0.1,
    )
    content = ""
    for block in response.content:
        if hasattr(block, "text"):
            content = block.text
            break
    return _parse_vocabulary_response(content)
