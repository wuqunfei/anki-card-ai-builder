import asyncio
import base64
from pathlib import Path

import httpx

from anki_builder.schema import Card

MINIMAX_API_URL = "https://api.minimax.io/v1/t2a_v2"
T2A_MODEL = "speech-02-hd"
DEFAULT_VOICE_ID = "Friendly_Person"


async def generate_audio_for_card(
    card: Card,
    media_dir: Path,
    api_key: str,
    client: httpx.AsyncClient,
) -> Card:
    audio_path = media_dir / f"{card.id}_audio.mp3"

    # Skip if already exists
    if card.audio_file and Path(card.audio_file).exists():
        return card

    if audio_path.exists():
        return card.model_copy(update={"audio_file": str(audio_path)})

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": T2A_MODEL,
        "text": card.word,
        "voice_setting": {"voice_id": DEFAULT_VOICE_ID},
        "audio_setting": {"format": "mp3", "sample_rate": 32000},
    }

    resp = await client.post(
        MINIMAX_API_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    status_code = data.get("base_resp", {}).get("status_code", -1)
    if status_code != 0:
        return card

    audio_b64 = data["data"]["audio"]
    # Fix padding if needed
    audio_b64 += "=" * (-len(audio_b64) % 4)
    audio_bytes = base64.b64decode(audio_b64)
    audio_path.write_bytes(audio_bytes)

    return card.model_copy(update={"audio_file": str(audio_path)})


async def generate_audio_batch(
    cards: list[Card],
    media_dir: Path,
    api_key: str,
    concurrency: int = 5,
) -> list[Card]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _limited(card: Card, client: httpx.AsyncClient) -> Card:
        async with semaphore:
            return await generate_audio_for_card(card, media_dir, api_key, client)

    async with httpx.AsyncClient() as client:
        tasks = [_limited(card, client) for card in cards]
        return await asyncio.gather(*tasks)
