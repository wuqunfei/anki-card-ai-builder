from pathlib import Path

from anki_builder.schema import Card


def ingest_image(
    path: Path,
    target_language: str,
    minimax_api_key: str,
    source_language: str = "de",
) -> list[Card]:
    raise NotImplementedError(
        "Image OCR ingestion is not yet available. "
        "Google Gemini OCR support is planned for a future release."
    )
