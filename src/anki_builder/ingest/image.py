import json
import re
import time
from pathlib import Path

import click
import httpx
import PIL.Image
import pillow_heif
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from anki_builder.constants import MAX_RETRIES
from anki_builder.schema import Card

pillow_heif.register_heif_opener()

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
                contents=[  # type: ignore[arg-type]
                    "Extract ALL vocabulary items from this image as JSON. Do not skip any words — include every single vocabulary entry visible on the page.",  # noqa: E501
                    img,
                ],
                config=types.GenerateContentConfig(
                    system_instruction=_load_system_prompt(target_language, source_language),
                    max_output_tokens=65536,
                ),
            )
            break
        except (httpx.RemoteProtocolError, httpx.ConnectError, ConnectionError) as e:
            if attempt < MAX_RETRIES - 1:
                wait = 5 * (attempt + 1)
                click.echo(f"Connection error ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except ClientError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                match = re.search(r"retry in ([\d.]+)s", str(e))
                wait = float(match.group(1)) + 1 if match else 60
                click.echo(f"Rate limited, waiting {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise

    raw_text = response.text or ""
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    # Find the first [ or { to strip any leading non-JSON text
    first_bracket = len(raw_text)
    for ch in ("[", "{"):
        idx = raw_text.find(ch)
        if idx != -1 and idx < first_bracket:
            first_bracket = idx
    if first_bracket < len(raw_text):
        raw_text = raw_text[first_bracket:]

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to find the last matching ] or } to trim trailing text
        for end_ch in ("]", "}"):
            idx = raw_text.rfind(end_ch)
            if idx != -1:
                try:
                    data = json.loads(raw_text[: idx + 1])
                    break
                except json.JSONDecodeError:
                    continue
        else:
            raise click.ClickException(f"Failed to parse Gemini response as JSON: {raw_text[:200]}")
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
