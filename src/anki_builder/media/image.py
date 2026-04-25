import asyncio
import base64
from pathlib import Path

import click
import httpx

from anki_builder.constants import MAX_RETRIES, MINIMAX_IMAGE_MODEL, MINIMAX_IMAGE_URL
from anki_builder.schema import Card

LANG_NAMES = {
    "en": "English",
    "fr": "French",
    "zh": "Chinese",
    "de": "German",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
}


def _lang_full_name(code: str) -> str:
    return LANG_NAMES.get(code, code)


def _build_image_prompt(word: str, target_language: str) -> str:
    lang = _lang_full_name(target_language)
    return (
        f"A single cute, kid-friendly cartoon illustration representing the {lang} word '{word}'. "
        f"Kid-friendly, colorful, clean background. "
        f"Pure illustration only — no text, letters, labels, captions, or speech bubbles."
    )


def _skip_if_exists(card: Card, image_path: Path) -> Card | None:
    """Return updated card if image already exists, None otherwise."""
    if card.image_file and Path(card.image_file).exists():
        return card
    if image_path.exists():
        return card.model_copy(update={"image_file": str(image_path)})
    return None


# --- MiniMax provider ---


async def _generate_minimax(
    card: Card,
    media_dir: Path,
    api_key: str,
    client: httpx.AsyncClient,
) -> Card:
    image_path = media_dir / f"{card.id}_image.png"

    existing = _skip_if_exists(card, image_path)
    if existing:
        return existing

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": MINIMAX_IMAGE_MODEL,
        "prompt": _build_image_prompt(card.source_word, card.target_language),
        "aspect_ratio": "1:1",
        "response_format": "base64",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.post(
                MINIMAX_IMAGE_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            image_list = (data.get("data") or {}).get("image_base64")
            if image_list:
                image_bytes = base64.b64decode(image_list[0])
                image_path.write_bytes(image_bytes)
                return card.model_copy(update={"image_file": str(image_path)})
            click.echo(f"  [{card.source_word}] attempt {attempt + 1}/{MAX_RETRIES}: empty response — {data}")
        except httpx.TimeoutException:
            click.echo(f"  [{card.source_word}] attempt {attempt + 1}/{MAX_RETRIES}: timeout (120s)")
        except httpx.HTTPStatusError as e:
            click.echo(
                f"  [{card.source_word}] attempt {attempt + 1}/{MAX_RETRIES}: HTTP {e.response.status_code} — {e.response.text[:200]}"  # noqa: E501
            )
        except Exception as e:
            click.echo(f"  [{card.source_word}] attempt {attempt + 1}/{MAX_RETRIES}: {type(e).__name__}: {e}")
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(3)

    click.echo(f"Warning: image generation failed for '{card.source_word}', skipping.")
    return card


# --- Google Gemini provider ---


async def _generate_gemini(
    card: Card,
    media_dir: Path,
    api_key: str,
    _client: httpx.AsyncClient,
) -> Card:
    image_path = media_dir / f"{card.id}_image.png"

    existing = _skip_if_exists(card, image_path)
    if existing:
        return existing

    from google import genai
    from google.genai import types

    gemini_client = genai.Client(api_key=api_key)
    prompt = _build_image_prompt(card.source_word, card.target_language)

    for attempt in range(MAX_RETRIES):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.1-flash-image-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        image_size="1K",
                    ),
                    response_modalities=["IMAGE"],
                ),
            )
            if response.parts:
                for part in response.parts:
                    if part.inline_data and part.inline_data.data:
                        image_path.write_bytes(part.inline_data.data)
                        return card.model_copy(update={"image_file": str(image_path)})
            click.echo(f"  [{card.source_word}] attempt {attempt + 1}/{MAX_RETRIES}: no image in response")
        except Exception as e:
            click.echo(f"  [{card.source_word}] attempt {attempt + 1}/{MAX_RETRIES}: {type(e).__name__}: {e}")
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(3)

    click.echo(f"Warning: image generation failed for '{card.source_word}', skipping.")
    return card


# --- Provider dispatch ---

PROVIDERS = {
    "minimax": _generate_minimax,
    "gemini": _generate_gemini,
}


async def generate_image_for_card(
    card: Card,
    media_dir: Path,
    api_key: str,
    client: httpx.AsyncClient,
    provider: str = "minimax",
    fallback_api_key: str = "",
) -> Card:
    fn = PROVIDERS.get(provider, _generate_minimax)
    result = await fn(card, media_dir, api_key, client)

    # If primary failed, try fallback provider
    if not result.image_file and fallback_api_key:
        fallback = "gemini" if provider == "minimax" else "minimax"
        click.echo(f"  [{card.source_word}] falling back to {fallback}...")
        fallback_fn = PROVIDERS[fallback]
        result = await fallback_fn(card, media_dir, fallback_api_key, client)

    return result


async def generate_image_batch(
    cards: list[Card],
    media_dir: Path,
    api_key: str,
    concurrency: int = 3,
    provider: str = "minimax",
    fallback_api_key: str = "",
) -> list[Card]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _limited(card: Card, client: httpx.AsyncClient) -> Card:
        async with semaphore:
            return await generate_image_for_card(card, media_dir, api_key, client, provider, fallback_api_key)

    async with httpx.AsyncClient() as client:
        tasks = [_limited(card, client) for card in cards]
        return await asyncio.gather(*tasks)
