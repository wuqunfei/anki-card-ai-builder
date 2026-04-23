import json
from pathlib import Path

import PIL.Image
from google import genai
from google.genai import types

from anki_builder.schema import Card

PROMPT_PATH = Path(__file__).parent / "prompt.md"


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def ingest_image(path: Path, target_language: str, source_language: str = "de") -> list[Card]:
    import os
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=google_api_key)

    img = PIL.Image.open(path)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=["Extract vocabulary as JSON.", img],
        config=types.GenerateContentConfig(
            system_instruction=_load_system_prompt(),
        ),
    )

    raw_text = response.text
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()

    data = json.loads(raw_text)
    cards = []
    for card_data in data["cards"]:
        card_data.pop("id", None)
        card_data.pop("status", None)
        card_data.pop("audio_file", None)
        card_data.pop("image_file", None)
        card_data["source"] = str(path)
        card_data["source_language"] = source_language
        card_data["target_language"] = target_language
        cards.append(Card(**card_data))
    return cards
