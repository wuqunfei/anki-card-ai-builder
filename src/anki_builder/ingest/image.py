import json
import re
import time
from pathlib import Path

import click
import PIL.Image
import pillow_heif
from google import genai
from google.genai import types
from google.genai.errors import ClientError

pillow_heif.register_heif_opener()

from anki_builder.constants import MAX_RETRIES
from anki_builder.schema import Card

PROMPT_PATH = Path(__file__).parent / "prompt.md"


def _load_system_prompt(target_language: str, source_language: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(target_language=target_language, source_language=source_language)


def ingest_image(path: Path, target_language: str, source_language: str = "de", google_api_key: str = "") -> list[Card]:
    client = genai.Client(api_key=google_api_key)

    img = PIL.Image.open(path)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=["Extract ALL vocabulary items from this image as JSON. Do not skip any words — include every single vocabulary entry visible on the page.", img],
                config=types.GenerateContentConfig(
                    system_instruction=_load_system_prompt(target_language, source_language),
                    max_output_tokens=65536,
                ),
            )
            break
        except ClientError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                match = re.search(r"retry in ([\d.]+)s", str(e))
                wait = float(match.group(1)) + 1 if match else 60
                click.echo(f"Rate limited, waiting {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise

    raw_text = response.text
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()

    data = json.loads(raw_text)
    card_list = data["cards"] if isinstance(data, dict) and "cards" in data else data
    cards = []
    for card_data in card_list:
        card_data.pop("id", None)
        card_data.pop("status", None)
        card_data.pop("audio_file", None)
        card_data.pop("image_file", None)
        card_data["source_language"] = source_language
        card_data["target_language"] = target_language
        # Gemini prompt already requests all enrichment fields;
        # mark as enriched if the key fields are present
        if card_data.get("target_word"):
            card_data["status"] = "enriched"
        cards.append(Card(**card_data))
    return cards
