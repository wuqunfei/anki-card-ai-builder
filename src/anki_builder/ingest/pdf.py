from pathlib import Path

import pymupdf

from anki_builder.schema import Card
from anki_builder.enrich.vocabulary import extract_vocabulary_with_ai


def extract_text_from_pdf(path: Path) -> str:
    doc = pymupdf.open(str(path))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def ingest_pdf(
    path: Path,
    target_language: str,
    minimax_api_key: str,
    source_language: str = "de",
) -> list[Card]:
    text = extract_text_from_pdf(path)

    if not text.strip():
        raise NotImplementedError(
            "Image-based PDF ingestion is not yet available. "
            "Google Gemini OCR support is planned for a future release."
        )

    vocab_items = extract_vocabulary_with_ai(
        text=text,
        target_language=target_language,
        source_language=source_language,
        minimax_api_key=minimax_api_key,
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
