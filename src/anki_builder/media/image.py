import asyncio
import base64
from pathlib import Path

import httpx

from anki_builder.schema import Card

MINIMAX_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
MINIMAX_IMAGE_MODEL = "image-01"


def _build_image_prompt(word: str, target_language: str) -> str:
    return (
        f"A single cute, cartoon illustration of: {word}. "
        f"Kid-friendly, colorful, clean background. "
        f"The image must contain ZERO text, ZERO letters, ZERO words, ZERO labels, ZERO captions. "
        f"No speech bubbles. No writing of any kind. Only a drawing."
    )


async def generate_image_for_card(
    card: Card,
    media_dir: Path,
    api_key: str,
    client: httpx.AsyncClient,
) -> Card:
    image_path = media_dir / f"{card.id}_image.png"

    # Skip if already exists
    if card.image_file and Path(card.image_file).exists():
        return card

    if image_path.exists():
        return card.model_copy(update={"image_file": str(image_path)})

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": MINIMAX_IMAGE_MODEL,
        "prompt": _build_image_prompt(card.source_word, card.target_language),
        "aspect_ratio": "1:1",
        "response_format": "base64",
    }

    for attempt in range(3):
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
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)

    print(f"Warning: image generation failed for '{card.source_word}', skipping.")
    return card


async def generate_image_batch(
    cards: list[Card],
    media_dir: Path,
    api_key: str,
    concurrency: int = 5,
) -> list[Card]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _limited(card: Card, client: httpx.AsyncClient) -> Card:
        async with semaphore:
            return await generate_image_for_card(card, media_dir, api_key, client)

    async with httpx.AsyncClient() as client:
        tasks = [_limited(card, client) for card in cards]
        return await asyncio.gather(*tasks)
