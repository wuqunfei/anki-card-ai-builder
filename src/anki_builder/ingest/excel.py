import csv
from pathlib import Path

import openpyxl

from anki_builder.schema import Card

# Fuzzy header mapping: common header names → Card field names
HEADER_ALIASES: dict[str, str] = {
    "word": "word",
    "wort": "word",
    "vokabel": "word",
    "translation": "translation",
    "übersetzung": "translation",
    "uebersetzung": "translation",
    "bedeutung": "translation",
    "pronunciation": "pronunciation",
    "aussprache": "pronunciation",
    "example": "example_sentence",
    "beispiel": "example_sentence",
    "example_sentence": "example_sentence",
    "tags": "tags",
    "tag": "tags",
}

CARD_FIELDS = {
    "word", "translation", "pronunciation", "example_sentence",
    "sentence_translation", "mnemonic", "part_of_speech", "tags",
}


def _resolve_header(header: str, column_map: dict[str, str] | None) -> str | None:
    if column_map and header in column_map:
        return column_map[header]
    return HEADER_ALIASES.get(header.lower().strip())


def _read_xlsx(path: Path) -> tuple[list[str], list[list]]:
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return [], []
    headers = [str(h) if h else "" for h in rows[0]]
    data = [list(row) for row in rows[1:]]
    return headers, data


def _read_csv(path: Path) -> tuple[list[str], list[list]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def ingest_excel(
    path: Path,
    target_language: str,
    source_language: str = "de",
    column_map: dict[str, str] | None = None,
) -> list[Card]:
    if path.suffix == ".csv":
        headers, data = _read_csv(path)
    else:
        headers, data = _read_xlsx(path)

    # Map headers to card fields
    field_map: dict[int, str] = {}
    unmapped_cols: dict[int, str] = {}
    for i, header in enumerate(headers):
        field = _resolve_header(header, column_map)
        if field and field in CARD_FIELDS:
            field_map[i] = field
        elif header.strip():
            unmapped_cols[i] = header.strip()

    cards: list[Card] = []
    for row in data:
        card_data: dict = {
            "source_language": source_language,
            "target_language": target_language,
            "source": str(path),
        }
        tags: list[str] = []

        for i, value in enumerate(row):
            if value is None or str(value).strip() == "":
                continue
            value_str = str(value).strip()
            if i in field_map:
                card_data[field_map[i]] = value_str
            elif i in unmapped_cols:
                tags.append(f"{unmapped_cols[i]}:{value_str}")

        if "word" not in card_data:
            continue

        card_data["tags"] = tags
        cards.append(Card(**card_data))

    return cards
