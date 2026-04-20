import base64
import json
import re

import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


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


def _build_vision_prompt(target_language: str, source_language: str) -> str:
    return (
        f"Extract vocabulary words from this image. The content is in "
        f"{target_language} (target language) and {source_language} (source language).\n\n"
        f"For each word, extract any available information: word, translation, "
        f"pronunciation, example_sentence, part_of_speech.\n\n"
        f"Return ONLY a JSON array of objects. Each object should have the fields "
        f"that are present in the source. Do not generate content that isn't in "
        f"the image — only extract what's visible."
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
    deepseek_api_key: str,
    text: str | None = None,
    image_bytes: bytes | None = None,
) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json",
    }

    if image_bytes is not None:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
                {
                    "type": "text",
                    "text": _build_vision_prompt(target_language, source_language),
                },
            ],
        }]
    elif text is not None:
        messages = [{
            "role": "user",
            "content": _build_text_prompt(text, target_language, source_language),
        }]
    else:
        return []

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.1,
    }

    response = httpx.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_vocabulary_response(content)
