from pathlib import Path

from anki_builder.schema import Card
from anki_builder.enrich.vocabulary import extract_vocabulary_with_ai


def ingest_image(
    path: Path,
    target_language: str,
    deepseek_api_key: str,
    source_language: str = "de",
) -> list[Card]:
    image_bytes = path.read_bytes()

    vocab_items = extract_vocabulary_with_ai(
        image_bytes=image_bytes,
        target_language=target_language,
        source_language=source_language,
        deepseek_api_key=deepseek_api_key,
    )

    cards = []
    for item in vocab_items:
        card_data = {
            "source_language": source_language,
            "target_language": target_language,
            "source": str(path),
            **item,
        }
        if "word" in card_data:
            cards.append(Card(**card_data))
    return cards
