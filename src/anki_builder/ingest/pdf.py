import base64
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


def _pdf_pages_to_images(path: Path) -> list[bytes]:
    doc = pymupdf.open(str(path))
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def ingest_pdf(
    path: Path,
    target_language: str,
    deepseek_api_key: str,
    source_language: str = "de",
) -> list[Card]:
    text = extract_text_from_pdf(path)

    if text.strip():
        vocab_items = extract_vocabulary_with_ai(
            text=text,
            target_language=target_language,
            source_language=source_language,
            deepseek_api_key=deepseek_api_key,
        )
    else:
        images = _pdf_pages_to_images(path)
        vocab_items = []
        for img_bytes in images:
            items = extract_vocabulary_with_ai(
                image_bytes=img_bytes,
                target_language=target_language,
                source_language=source_language,
                deepseek_api_key=deepseek_api_key,
            )
            vocab_items.extend(items)

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
