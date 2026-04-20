import asyncio
from pathlib import Path

import httpx

from anki_builder.schema import Card

MINIMAX_API_BASE = "https://api.minimax.io/v1"
T2A_MODEL = "speech-2.8-hd"


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

    # Step 1: Create T2A task
    payload = {
        "model": T2A_MODEL,
        "text": card.word,
        "voice_id": "English_expressive_narrator",
    }
    resp = await client.post(
        f"{MINIMAX_API_BASE}/t2a_async_v2",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["task_id"]

    # Step 2: Poll until complete
    for _ in range(60):  # Max ~5 minutes
        resp = await client.get(
            f"{MINIMAX_API_BASE}/query/t2a_async_query_v2",
            params={"task_id": task_id},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "Success":
            file_id = data["file_id"]
            break
        elif data.get("status") == "Failed":
            return card
        await asyncio.sleep(5)
    else:
        return card  # Timeout

    # Step 3: Download audio
    resp = await client.get(
        f"{MINIMAX_API_BASE}/files/retrieve_content",
        params={"file_id": file_id},
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    audio_path.write_bytes(resp.content)

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
