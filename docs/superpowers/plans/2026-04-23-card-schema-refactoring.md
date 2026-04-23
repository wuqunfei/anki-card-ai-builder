# Card Schema Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename Card model fields for clarity, add new optional fields, remove `target_language` default, and auto-migrate existing data.

**Architecture:** Mechanical rename across the codebase following the field mapping in the spec. Migration logic added to `state.py` load path. Tests updated to use new field names and verify migration.

**Tech Stack:** Python 3.12+, Pydantic, genanki, Click, pytest

---

### Task 1: Update Card Schema

**Files:**
- Modify: `src/anki_builder/schema.py:1-22`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write failing test for new schema fields**

Update `tests/test_schema.py` to use new field names:

```python
import unittest
from anki_builder.schema import Card


class TestCard(unittest.TestCase):
    def test_create_full_card(self):
        card = Card(
            source_word="accomplish",
            source_language="de",
            target_language="en",
            source="vocab.xlsx",
        )
        self.assertEqual(card.source_word, "accomplish")
        self.assertEqual(card.source_language, "de")
        self.assertEqual(card.target_language, "en")
        self.assertEqual(card.status, "extracted")
        self.assertIsNotNone(card.id)
        self.assertIsNone(card.target_word)
        self.assertIsNone(card.target_pronunciation)
        self.assertIsNone(card.target_example_sentence)
        self.assertIsNone(card.source_example_sentence)
        self.assertIsNone(card.target_mnemonic)
        self.assertIsNone(card.target_part_of_speech)
        self.assertIsNone(card.unit)
        self.assertIsNone(card.reference)
        self.assertIsNone(card.source_gender)
        self.assertIsNone(card.target_gender)
        self.assertEqual(card.tags, [])

    def test_card_id_is_uuid(self):
        import uuid
        card = Card(source_word="test", source_language="de", target_language="en", source="test")
        uuid.UUID(card.id)  # Raises if not valid UUID

    def test_card_serialization_roundtrip(self):
        card = Card(
            source_word="Hund",
            source_language="de",
            target_language="en",
            target_word="dog",
            source="vocab.xlsx",
        )
        data = card.model_dump()
        card2 = Card(**data)
        self.assertEqual(card, card2)

    def test_new_optional_fields(self):
        card = Card(
            source_word="maison",
            source_language="de",
            target_language="fr",
            source="test",
            unit="Unité 1",
            reference="Page 162",
            source_gender="f",
            target_gender="f",
        )
        self.assertEqual(card.unit, "Unité 1")
        self.assertEqual(card.reference, "Page 162")
        self.assertEqual(card.source_gender, "f")
        self.assertEqual(card.target_gender, "f")

    def test_target_language_required(self):
        with self.assertRaises(Exception):
            Card(source_word="test", source="test")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schema.py -v`
Expected: FAIL — `Card` does not have `source_word` field yet.

- [ ] **Step 3: Update schema.py**

Replace `src/anki_builder/schema.py` with:

```python
import uuid

from pydantic import BaseModel, Field


class Card(BaseModel):
    # --- Metadata & Tracking ---
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit: str | None = None                    # Textbook unit (e.g., "Unité 1")
    reference: str | None = None               # Origin (e.g., "Page 162")
    status: str = "extracted"                  # Workflow state
    tags: list[str] = Field(default_factory=list)
    audio_file: str | None = None
    image_file: str | None = None
    source: str                                # How card was created ("cli", file path, etc.)

    # --- SOURCE (Native Language) ---
    source_word: str                           # Native language word
    source_language: str = "de"                # Native language ISO
    source_gender: str | None = None           # Gender if noun ("m", "f", "n")
    source_example_sentence: str | None = None # Native language sentence

    # --- TARGET (Learning Language) ---
    target_word: str | None = None             # Learning language word
    target_language: str                       # Learning language ISO (no default)
    target_gender: str | None = None           # Target gender if noun
    target_pronunciation: str | None = None    # IPA, Pinyin, or Romaji
    target_part_of_speech: str | None = None   # noun, verb, adjective, etc.
    target_example_sentence: str | None = None # Target sentence

    # Word breakdown as HTML with soft colored parts:
    # - Prefix (blue): <span style="color:#5b9bd5">...</span>
    # - Root (coral): <span style="color:#e07b7b">...</span>
    # - Suffix (green): <span style="color:#6dba6d">...</span>
    target_mnemonic: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_schema.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/schema.py tests/test_schema.py
git commit -m "feat: rename Card fields and add new optional fields"
```

---

### Task 2: Add Migration Logic to StateManager

**Files:**
- Modify: `src/anki_builder/state.py:1-60`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write failing test for migration**

Replace `tests/test_state.py` with:

```python
import json
import tempfile
import unittest
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.state import StateManager


class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state = StateManager(Path(self.tmpdir))

    def test_save_and_load_cards(self):
        cards = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
            Card(source_word="chat", target_language="fr", source="test.xlsx"),
        ]
        self.state.save_cards(cards)
        loaded = self.state.load_cards()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].source_word, "dog")
        self.assertEqual(loaded[1].source_word, "chat")

    def test_load_empty_returns_empty_list(self):
        loaded = self.state.load_cards()
        self.assertEqual(loaded, [])

    def test_merge_new_cards(self):
        existing = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
            Card(source_word="cat", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].id, existing[0].id)
        self.assertEqual(merged[1].source_word, "cat")

    def test_merge_preserves_enriched_fields(self):
        existing = [
            Card(
                source_word="dog",
                target_language="en",
                source="test.xlsx",
                target_word="Hund",
                status="enriched",
            ),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(merged[0].target_word, "Hund")
        self.assertEqual(merged[0].status, "enriched")

    def test_media_dir_created(self):
        media_dir = self.state.media_dir
        self.assertTrue(media_dir.exists())
        self.assertTrue(media_dir.is_dir())

    def test_migrate_old_field_names(self):
        """Loading cards.json with old field names auto-migrates them."""
        old_data = [
            {
                "id": "test-id",
                "word": "dog",
                "source_language": "de",
                "target_language": "en",
                "translation": "Hund",
                "pronunciation": "/dɒɡ/",
                "part_of_speech": "noun",
                "mnemonic": "<span>test</span>",
                "example_sentence": "The dog plays.",
                "sentence_translation": "Der Hund spielt.",
                "tags": [],
                "audio_file": None,
                "image_file": None,
                "source": "test.xlsx",
                "status": "enriched",
            }
        ]
        self.state.cards_file.write_text(json.dumps(old_data))
        loaded = self.state.load_cards()
        self.assertEqual(len(loaded), 1)
        card = loaded[0]
        self.assertEqual(card.source_word, "dog")
        self.assertEqual(card.target_word, "Hund")
        self.assertEqual(card.target_pronunciation, "/dɒɡ/")
        self.assertEqual(card.target_part_of_speech, "noun")
        self.assertEqual(card.target_mnemonic, "<span>test</span>")
        self.assertEqual(card.target_example_sentence, "The dog plays.")
        self.assertEqual(card.source_example_sentence, "Der Hund spielt.")

    def test_migration_writes_back(self):
        """After migration, cards.json uses new field names."""
        old_data = [
            {
                "id": "test-id",
                "word": "dog",
                "source_language": "de",
                "target_language": "en",
                "translation": "Hund",
                "source": "test.xlsx",
                "status": "extracted",
                "tags": [],
                "audio_file": None,
                "image_file": None,
                "pronunciation": None,
                "part_of_speech": None,
                "mnemonic": None,
                "example_sentence": None,
                "sentence_translation": None,
            }
        ]
        self.state.cards_file.write_text(json.dumps(old_data))
        self.state.load_cards()
        # Re-read raw JSON
        raw = json.loads(self.state.cards_file.read_text())
        self.assertIn("source_word", raw[0])
        self.assertNotIn("word", raw[0])
        self.assertIn("target_word", raw[0])
        self.assertNotIn("translation", raw[0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_state.py -v`
Expected: FAIL — `test_migrate_old_field_names` and `test_migration_writes_back` fail because migration logic doesn't exist yet. Other tests fail because they use old field names (but we already updated them).

- [ ] **Step 3: Update state.py with migration and new field names**

Replace `src/anki_builder/state.py` with:

```python
import json
from pathlib import Path

from anki_builder.schema import Card

FIELD_MIGRATION = {
    "word": "source_word",
    "translation": "target_word",
    "pronunciation": "target_pronunciation",
    "part_of_speech": "target_part_of_speech",
    "mnemonic": "target_mnemonic",
    "example_sentence": "target_example_sentence",
    "sentence_translation": "source_example_sentence",
}


def _migrate_card_data(item: dict) -> dict:
    """Rename old field names to new names if present."""
    for old_key, new_key in FIELD_MIGRATION.items():
        if old_key in item and new_key not in item:
            item[new_key] = item.pop(old_key)
    return item


class StateManager:
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cards_file = work_dir / "cards.json"
        self.media_dir = work_dir / "media"
        self.media_dir.mkdir(exist_ok=True)

    def load_cards(self) -> list[Card]:
        if not self.cards_file.exists():
            return []
        data = json.loads(self.cards_file.read_text())
        migrated = False
        for item in data:
            if any(old_key in item for old_key in FIELD_MIGRATION):
                _migrate_card_data(item)
                migrated = True
        cards = [Card(**item) for item in data]
        if migrated:
            self.save_cards(cards)
        return cards

    def save_cards(self, cards: list[Card]) -> None:
        data = [card.model_dump() for card in cards]
        self.cards_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def merge_cards(self, new_cards: list[Card], prune: bool = False) -> list[Card]:
        existing = self.load_cards()
        existing_map: dict[tuple[str, str], Card] = {
            (c.source_word, c.target_language): c for c in existing
        }

        merged: list[Card] = []
        seen_keys: set[tuple[str, str]] = set()
        for card in new_cards:
            key = (card.source_word, card.target_language)
            seen_keys.add(key)
            if key in existing_map:
                old = existing_map[key]
                update_data = {}
                for field in ["target_word", "target_pronunciation",
                              "target_example_sentence", "source_example_sentence",
                              "target_mnemonic", "target_part_of_speech",
                              "audio_file", "image_file"]:
                    old_val = getattr(old, field)
                    new_val = getattr(card, field)
                    if old_val is not None and new_val is None:
                        update_data[field] = old_val
                update_data["id"] = old.id
                if old.status != "extracted":
                    update_data["status"] = old.status
                merged.append(card.model_copy(update=update_data))
            else:
                merged.append(card)

        if not prune:
            for key, card in existing_map.items():
                if key not in seen_keys:
                    merged.append(card)

        return merged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_state.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/state.py tests/test_state.py
git commit -m "feat: add auto-migration for old Card field names in state manager"
```

---

### Task 3: Update Ingest Modules

**Files:**
- Modify: `src/anki_builder/ingest/excel.py:1-104`
- Modify: `src/anki_builder/ingest/pdf.py:39-48`
- Test: `tests/test_ingest_excel.py`
- Test: `tests/test_ingest_pdf.py`

- [ ] **Step 1: Write failing tests**

Replace `tests/test_ingest_excel.py` with:

```python
import tempfile
import unittest
from pathlib import Path

import openpyxl

from anki_builder.ingest.excel import ingest_excel


class TestExcelIngestion(unittest.TestCase):
    def _create_xlsx(self, headers: list[str], rows: list[list], path: Path) -> Path:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        wb.save(path)
        return path

    def test_basic_ingestion(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["word", "translation"],
            [["dog", "Hund"], ["cat", "Katze"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(path, target_language="en")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "dog")
        self.assertEqual(cards[0].target_word, "Hund")
        self.assertEqual(cards[0].target_language, "en")
        self.assertEqual(cards[0].source, str(path))

    def test_fuzzy_header_matching(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["Wort", "Übersetzung"],
            [["Hund", "dog"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(path, target_language="en")
        self.assertEqual(cards[0].source_word, "Hund")
        self.assertEqual(cards[0].target_word, "dog")

    def test_custom_column_mapping(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["vocab", "meaning"],
            [["accomplish", "erreichen"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(
            path,
            target_language="en",
            column_map={"vocab": "source_word", "meaning": "target_word"},
        )
        self.assertEqual(cards[0].source_word, "accomplish")
        self.assertEqual(cards[0].target_word, "erreichen")

    def test_unmapped_columns_become_tags(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["word", "translation", "level", "chapter"],
            [["dog", "Hund", "A1", "ch3"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(path, target_language="en")
        self.assertIn("level:A1", cards[0].tags)
        self.assertIn("chapter:ch3", cards[0].tags)

    def test_csv_ingestion(self):
        tmpdir = tempfile.mkdtemp()
        csv_path = Path(tmpdir) / "vocab.csv"
        csv_path.write_text("word,translation\ndog,Hund\ncat,Katze\n")
        cards = ingest_excel(csv_path, target_language="en")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "dog")


if __name__ == "__main__":
    unittest.main()
```

Replace `tests/test_ingest_pdf.py` with:

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from anki_builder.ingest.pdf import ingest_pdf, extract_text_from_pdf


class TestPdfTextExtraction(unittest.TestCase):
    def _create_pdf_with_text(self, text: str, path: Path) -> Path:
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(str(path))
        doc.close()
        return path

    def test_extract_text_from_digital_pdf(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_pdf_with_text(
            "dog - Hund\ncat - Katze\nbird - Vogel",
            Path(tmpdir) / "vocab.pdf",
        )
        text = extract_text_from_pdf(path)
        self.assertIn("dog", text)
        self.assertIn("Hund", text)

    @patch("anki_builder.ingest.pdf.extract_vocabulary_with_ai")
    def test_ingest_pdf_calls_ai_extraction(self, mock_ai):
        mock_ai.return_value = [
            {"source_word": "dog", "target_word": "Hund"},
            {"source_word": "cat", "target_word": "Katze"},
        ]
        tmpdir = tempfile.mkdtemp()
        path = self._create_pdf_with_text(
            "dog - Hund\ncat - Katze",
            Path(tmpdir) / "vocab.pdf",
        )
        cards = ingest_pdf(path, target_language="en", minimax_api_key="test-key")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "dog")
        mock_ai.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ingest_excel.py tests/test_ingest_pdf.py -v`
Expected: FAIL — old field names in source code.

- [ ] **Step 3: Update excel.py**

Replace `src/anki_builder/ingest/excel.py` with:

```python
import csv
from pathlib import Path

import openpyxl

from anki_builder.schema import Card

# Fuzzy header mapping: common header names → Card field names
HEADER_ALIASES: dict[str, str] = {
    "word": "source_word",
    "wort": "source_word",
    "vokabel": "source_word",
    "translation": "target_word",
    "übersetzung": "target_word",
    "uebersetzung": "target_word",
    "bedeutung": "target_word",
    "pronunciation": "target_pronunciation",
    "aussprache": "target_pronunciation",
    "example": "target_example_sentence",
    "beispiel": "target_example_sentence",
    "example_sentence": "target_example_sentence",
    "tags": "tags",
    "tag": "tags",
}

CARD_FIELDS = {
    "source_word", "target_word", "target_pronunciation",
    "target_example_sentence", "source_example_sentence",
    "target_mnemonic", "target_part_of_speech", "tags",
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

        if "source_word" not in card_data:
            continue

        card_data["tags"] = tags
        cards.append(Card(**card_data))

    return cards
```

- [ ] **Step 4: Update pdf.py**

In `src/anki_builder/ingest/pdf.py`, change lines 40-48 to use `source_word`:

```python
    cards = []
    for item in vocab_items:
        card_data = {
            "source_language": source_language,
            "target_language": target_language,
            "source": str(path),
            **item,
        }
        if "source_word" in card_data:
            cards.append(Card(**card_data))
    return cards
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_ingest_excel.py tests/test_ingest_pdf.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/anki_builder/ingest/excel.py src/anki_builder/ingest/pdf.py tests/test_ingest_excel.py tests/test_ingest_pdf.py
git commit -m "feat: update ingest modules to use new Card field names"
```

---

### Task 4: Update Enrichment Modules

**Files:**
- Modify: `src/anki_builder/enrich/ai.py:1-119`
- Modify: `src/anki_builder/enrich/vocabulary.py:10-19`
- Test: `tests/test_enrich_ai.py`
- Test: `tests/test_vocabulary.py`

- [ ] **Step 1: Write failing tests**

Replace `tests/test_enrich_ai.py` with:

```python
import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.schema import Card
from anki_builder.enrich.ai import enrich_cards, _build_enrichment_prompt, _batch_cards


class TestAIEnrichment(unittest.TestCase):
    def test_build_enrichment_prompt(self):
        cards = [
            Card(source_word="dog", target_language="en", source="test"),
        ]
        prompt = _build_enrichment_prompt(cards, source_language="de")
        self.assertIn("dog", prompt)
        self.assertIn("kid-friendly", prompt.lower())
        self.assertIn("emoji", prompt.lower())
        self.assertIn("target_mnemonic", prompt)
        self.assertIn("JSON", prompt)

    def test_batch_cards(self):
        cards = [Card(source_word=f"word{i}", target_language="en", source="test") for i in range(45)]
        batches = _batch_cards(cards, batch_size=20)
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0]), 20)
        self.assertEqual(len(batches[1]), 20)
        self.assertEqual(len(batches[2]), 5)

    def test_already_enriched_cards_skipped(self):
        cards = [
            Card(source_word="dog", target_language="en", source="test", status="enriched"),
            Card(source_word="cat", target_language="en", source="test", status="extracted"),
        ]
        to_enrich = [c for c in cards if c.status == "extracted"]
        self.assertEqual(len(to_enrich), 1)
        self.assertEqual(to_enrich[0].source_word, "cat")

    @patch("anki_builder.enrich.ai.anthropic")
    def test_enrich_cards(self, mock_anthropic_module):
        mock_client = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        enriched_data = json.dumps([{
            "source_word": "dog",
            "target_word": "Hund",
            "target_pronunciation": "/dɒɡ/",
            "target_example_sentence": "The dog loves to play in the park! 🐕",
            "source_example_sentence": "Der Hund spielt gern im Park! 🐕",
            "target_mnemonic": '<span style="color:red">dog</span>',
            "target_part_of_speech": "noun",
        }])

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=enriched_data)]
        mock_client.messages.create.return_value = mock_response

        cards = [Card(source_word="dog", target_language="en", source="test")]
        result = enrich_cards(cards, minimax_api_key="test-key", source_language="de")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_word, "Hund")
        self.assertEqual(result[0].target_pronunciation, "/dɒɡ/")
        self.assertIn("🐕", result[0].target_example_sentence)
        self.assertIn("🐕", result[0].source_example_sentence)
        self.assertIn("color:red", result[0].target_mnemonic)
        self.assertEqual(result[0].target_part_of_speech, "noun")
        self.assertEqual(result[0].status, "enriched")


if __name__ == "__main__":
    unittest.main()
```

Replace `tests/test_vocabulary.py` with:

```python
import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.enrich.vocabulary import (
    extract_vocabulary_with_ai,
    _build_text_prompt,
    _parse_vocabulary_response,
)


class TestVocabularyExtraction(unittest.TestCase):
    def test_build_text_prompt(self):
        prompt = _build_text_prompt(
            text="dog - Hund\ncat - Katze",
            target_language="en",
            source_language="de",
        )
        self.assertIn("dog", prompt)
        self.assertIn("en", prompt)
        self.assertIn("JSON", prompt)

    def test_parse_vocabulary_response(self):
        response_text = json.dumps([
            {"source_word": "dog", "target_word": "Hund"},
            {"source_word": "cat", "target_word": "Katze"},
        ])
        items = _parse_vocabulary_response(response_text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_word"], "dog")
        self.assertEqual(items[1]["target_word"], "Katze")

    def test_parse_response_with_markdown_code_block(self):
        response_text = '```json\n[{"source_word": "dog", "target_word": "Hund"}]\n```'
        items = _parse_vocabulary_response(response_text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_word"], "dog")

    @patch("anki_builder.enrich.vocabulary.anthropic.Anthropic")
    def test_extract_vocabulary_with_text(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_block = MagicMock()
        mock_block.text = json.dumps([{"source_word": "dog", "target_word": "Hund"}])
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        items = extract_vocabulary_with_ai(
            text="dog - Hund",
            target_language="en",
            source_language="de",
            minimax_api_key="test-key",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_word"], "dog")
        mock_client.messages.create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_enrich_ai.py tests/test_vocabulary.py -v`
Expected: FAIL — old field names in source code.

- [ ] **Step 3: Update enrich/ai.py**

Replace `src/anki_builder/enrich/ai.py` with:

```python
import json
import re

import anthropic

from anki_builder.schema import Card

MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"


def _batch_cards(cards: list[Card], batch_size: int = 20) -> list[list[Card]]:
    return [cards[i:i + batch_size] for i in range(0, len(cards), batch_size)]


def _build_enrichment_prompt(cards: list[Card], source_language: str) -> str:
    card_list = []
    for c in cards:
        entry = {"source_word": c.source_word, "target_language": c.target_language}
        if c.target_word:
            entry["target_word"] = c.target_word
        if c.target_pronunciation:
            entry["target_pronunciation"] = c.target_pronunciation
        if c.target_example_sentence:
            entry["target_example_sentence"] = c.target_example_sentence
        if c.source_example_sentence:
            entry["source_example_sentence"] = c.source_example_sentence
        card_list.append(entry)

    return (
        f"You are a friendly language tutor for German-speaking kids aged 9-12.\n\n"
        f"For each word below, fill in the missing fields. The source language is "
        f"'{source_language}'. Keep sentences simple, natural, and kid-friendly with "
        f"serval emojis sprinkled in.\n\n"
        f"For EVERY word, you MUST generate:\n"
        f"- `target_part_of_speech`: the grammatical category (noun, verb, adjective, etc.)\n"
        f"- `target_mnemonic`: word breakdown as HTML with soft colored parts:\n"
        f'  prefix in soft blue: <span style="color:#5b9bd5">un-</span>\n'
        f'  root in soft coral: <span style="color:#e07b7b">break</span>\n'
        f'  suffix in soft green: <span style="color:#6dba6d">-able</span>\n'
        f"  Join parts with \" + \". ONLY provide a mnemonic if the word has meaningful parts "
        f"(prefixes, suffixes, or compound structure). If it's a simple word with no useful "
        f"breakdown (e.g. \"glove\", \"cat\", \"dog\"), set target_mnemonic to null.\n\n"
        f"For fields that are already filled, keep the existing value.\n"
        f"For missing fields, generate:\n"
        f"- `target_word`: translate to {source_language}\n"
        f"- `target_pronunciation`: IPA for English/French, pinyin with tone marks for Chinese\n"
        f"- `target_example_sentence`: a kid-friendly sentence with emojis\n"
        f"- `source_example_sentence`: translation of the example to {source_language}, also kid-friendly with emojis\n\n"
        f"Return ONLY a JSON array with one object per word. Each object must have all fields: "
        f"source_word, target_word, target_pronunciation, target_example_sentence, "
        f"source_example_sentence, target_mnemonic, target_part_of_speech.\n\n"
        f"Words:\n{json.dumps(card_list, ensure_ascii=False)}"
    )


def _parse_enrichment_response(text: str) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def enrich_cards(
    cards: list[Card],
    minimax_api_key: str,
    source_language: str = "de",
) -> list[Card]:
    to_enrich = [c for c in cards if c.status == "extracted"]
    already_done = [c for c in cards if c.status != "extracted"]

    if not to_enrich:
        return cards

    client = anthropic.Anthropic(
        api_key=minimax_api_key,
        base_url=MINIMAX_BASE_URL,
    )

    enriched: list[Card] = []
    for batch in _batch_cards(to_enrich):
        prompt = _build_enrichment_prompt(batch, source_language)
        response = client.messages.create(
            model=MINIMAX_MODEL,
            max_tokens=16384,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
                break
        items = _parse_enrichment_response(content)

        item_map = {item["source_word"]: item for item in items if "source_word" in item}
        for card in batch:
            if card.source_word in item_map:
                item = item_map[card.source_word]
                update = {"status": "enriched"}
                for field in ["target_word", "target_pronunciation",
                              "target_example_sentence", "source_example_sentence"]:
                    if getattr(card, field) is None and field in item:
                        update[field] = item[field]
                for field in ["target_mnemonic", "target_part_of_speech"]:
                    if field in item:
                        update[field] = item[field]
                enriched.append(card.model_copy(update=update))
            else:
                enriched.append(card)

    return already_done + enriched
```

- [ ] **Step 4: Update enrich/vocabulary.py**

Replace the `_build_text_prompt` function in `src/anki_builder/enrich/vocabulary.py` (lines 10-19):

```python
def _build_text_prompt(text: str, target_language: str, source_language: str) -> str:
    return (
        f"Extract vocabulary words from the following text. The text is in "
        f"{target_language} (target language) and {source_language} (source language).\n\n"
        f"For each word, extract any available information: source_word, target_word, "
        f"target_pronunciation, target_example_sentence, target_part_of_speech.\n\n"
        f"Return ONLY a JSON array of objects. Each object should have the fields "
        f"that are present in the source. Do not generate content that isn't in "
        f"the source text — only extract what's there.\n\n"
        f"Text:\n{text}"
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_enrich_ai.py tests/test_vocabulary.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/anki_builder/enrich/ai.py src/anki_builder/enrich/vocabulary.py tests/test_enrich_ai.py tests/test_vocabulary.py
git commit -m "feat: update enrichment modules to use new Card field names"
```

---

### Task 5: Update Media Modules

**Files:**
- Modify: `src/anki_builder/media/audio.py:27`
- Modify: `src/anki_builder/media/image.py:38`
- Test: `tests/test_media_audio.py`

- [ ] **Step 1: Write failing test**

Replace `tests/test_media_audio.py` with:

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from anki_builder.schema import Card
from anki_builder.media.audio import generate_audio_for_card, generate_audio_batch


class TestAudioGeneration(unittest.TestCase):
    @patch("anki_builder.media.audio.gTTS")
    def test_generate_audio_for_card(self, mock_gtts_cls):
        mock_tts = MagicMock()
        mock_gtts_cls.return_value = mock_tts

        def fake_save(path):
            Path(path).write_bytes(b"fake-mp3")
        mock_tts.save.side_effect = fake_save

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(source_word="dog", target_language="en", source="test")
        result = generate_audio_for_card(card, media_dir)

        self.assertIsNotNone(result.audio_file)
        self.assertIn("audio.mp3", result.audio_file)
        self.assertTrue(Path(result.audio_file).exists())
        # TTS should speak the target word (learning language)
        mock_gtts_cls.assert_called_once_with(text="dog", lang="en")

    def test_skip_existing_audio(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", source_word="dog", target_language="en", source="test")
        audio_path = media_dir / "fixed-id_audio.mp3"
        audio_path.write_bytes(b"existing-audio")
        card = card.model_copy(update={"audio_file": str(audio_path)})

        result = generate_audio_for_card(card, media_dir)
        self.assertEqual(result.audio_file, str(audio_path))

    @patch("anki_builder.media.audio.gTTS")
    def test_generate_audio_batch(self, mock_gtts_cls):
        mock_tts = MagicMock()
        mock_gtts_cls.return_value = mock_tts

        def fake_save(path):
            Path(path).write_bytes(b"fake-mp3")
        mock_tts.save.side_effect = fake_save

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        cards = [
            Card(source_word="dog", target_language="en", source="test"),
            Card(source_word="cat", target_language="en", source="test"),
        ]
        results = generate_audio_batch(cards, media_dir)
        self.assertEqual(len(results), 2)
        self.assertIsNotNone(results[0].audio_file)
        self.assertIsNotNone(results[1].audio_file)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_audio.py -v`
Expected: FAIL — `Card` no longer has `word` field.

- [ ] **Step 3: Update audio.py**

In `src/anki_builder/media/audio.py`, change line 27 from `card.word` to `card.source_word`:

```python
    tts = gTTS(text=card.source_word, lang=lang)
```

- [ ] **Step 4: Update image.py**

In `src/anki_builder/media/image.py`, change line 38 from `card.word` to `card.source_word`:

```python
        "prompt": _build_image_prompt(card.source_word, card.target_language),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_media_audio.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/anki_builder/media/audio.py src/anki_builder/media/image.py tests/test_media_audio.py
git commit -m "feat: update media modules to use new Card field names"
```

---

### Task 6: Update Export Module

**Files:**
- Modify: `src/anki_builder/export/apkg.py:1-98`
- Test: `tests/test_export_apkg.py`

- [ ] **Step 1: Write failing test**

Replace `tests/test_export_apkg.py` with:

```python
import tempfile
import unittest
import zipfile
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.export.apkg import export_apkg


class TestApkgExport(unittest.TestCase):
    def _make_cards(self) -> list[Card]:
        return [
            Card(
                id="card-1",
                source_word="dog",
                target_language="en",
                source="test",
                target_word="Hund",
                target_pronunciation="/dɒɡ/",
                target_example_sentence="The dog plays in the park! 🐕",
                source_example_sentence="Der Hund spielt im Park! 🐕",
                target_mnemonic='<span style="color:red">dog</span>',
                target_part_of_speech="noun",
                status="enriched",
            ),
            Card(
                id="card-2",
                source_word="cat",
                target_language="en",
                source="test",
                target_word="Katze",
                target_pronunciation="/kæt/",
                target_example_sentence="The cat sleeps on the sofa! 🐱",
                source_example_sentence="Die Katze schläft auf dem Sofa! 🐱",
                target_mnemonic='<span style="color:red">cat</span>',
                target_part_of_speech="noun",
                status="enriched",
            ),
        ]

    def test_export_creates_apkg_file(self):
        tmpdir = tempfile.mkdtemp()
        output_path = Path(tmpdir) / "test.apkg"
        cards = self._make_cards()

        export_apkg(cards, output_path, deck_name="Test Deck")

        self.assertTrue(output_path.exists())
        self.assertTrue(zipfile.is_zipfile(output_path))

    def test_export_with_media(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        audio_path = media_dir / "card-1_audio.mp3"
        audio_path.write_bytes(b"fake-audio")

        cards = self._make_cards()
        cards[0] = cards[0].model_copy(update={"audio_file": str(audio_path)})

        output_path = Path(tmpdir) / "test.apkg"
        export_apkg(cards, output_path, deck_name="Test Deck")

        self.assertTrue(output_path.exists())
        with zipfile.ZipFile(output_path) as zf:
            names = zf.namelist()
            self.assertTrue(any("media" in str(n) or n.isdigit() for n in names))

    def test_export_empty_cards(self):
        tmpdir = tempfile.mkdtemp()
        output_path = Path(tmpdir) / "test.apkg"
        export_apkg([], output_path, deck_name="Empty Deck")
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_apkg.py -v`
Expected: FAIL — `Card` constructor uses old field names.

- [ ] **Step 3: Update apkg.py**

Replace `src/anki_builder/export/apkg.py` with:

```python
import hashlib
from pathlib import Path

import genanki

from anki_builder.schema import Card

MODEL_ID = int(hashlib.md5(b"anki-builder-model-v2").hexdigest()[:8], 16)

CARD_MODEL = genanki.Model(
    MODEL_ID,
    "Anki Builder Card",
    fields=[
        {"name": "SourceWord"},
        {"name": "TargetWord"},
        {"name": "TargetPronunciation"},
        {"name": "TargetExampleSentence"},
        {"name": "SourceExampleSentence"},
        {"name": "TargetMnemonic"},
        {"name": "TargetPartOfSpeech"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[{
        "name": "Card 1",
        "qfmt": (
            '<div style="text-align:center; font-size:24px; margin:20px;">'
            "{{SourceWord}}"
            "</div>"
            '<div style="text-align:center;">{{Image}}</div>'
            '<div style="text-align:center;">{{Audio}}</div>'
        ),
        "afmt": (
            '{{FrontSide}}<hr id="answer">'
            '<div style="text-align:center; font-size:20px; color:#333;">{{TargetWord}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{TargetPronunciation}}</div>'
            '<div style="text-align:center; font-size:14px; margin:10px;">{{TargetMnemonic}}</div>'
            '<div style="text-align:center; font-size:16px; margin:10px;">{{TargetExampleSentence}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{SourceExampleSentence}}</div>'
            '<div style="text-align:center; font-size:12px; color:#999;">{{TargetPartOfSpeech}}</div>'
        ),
    }],
)


def _card_to_note(card: Card) -> tuple[genanki.Note, list[str]]:
    media_files = []

    audio_field = ""
    if card.audio_file and Path(card.audio_file).exists():
        audio_filename = Path(card.audio_file).name
        audio_field = f"[sound:{audio_filename}]"
        media_files.append(card.audio_file)

    image_field = ""
    if card.image_file and Path(card.image_file).exists():
        image_filename = Path(card.image_file).name
        image_field = f'<img src="{image_filename}" style="max-width:350px;">'
        media_files.append(card.image_file)

    note = genanki.Note(
        model=CARD_MODEL,
        fields=[
            card.source_word,
            card.target_word or "",
            card.target_pronunciation or "",
            card.target_example_sentence or "",
            card.source_example_sentence or "",
            card.target_mnemonic or "",
            card.target_part_of_speech or "",
            audio_field,
            image_field,
        ],
        guid=genanki.guid_for(card.id),
    )
    return note, media_files


def export_apkg(
    cards: list[Card],
    output_path: Path,
    deck_name: str = "Vocabulary",
) -> None:
    deck_id = int(hashlib.md5(deck_name.encode()).hexdigest()[:8], 16)
    deck = genanki.Deck(deck_id, deck_name)

    all_media: list[str] = []
    for card in cards:
        note, media_files = _card_to_note(card)
        deck.add_note(note)
        all_media.extend(media_files)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    package = genanki.Package(deck)
    package.media_files = all_media
    package.write_to_file(str(output_path))
```

Note: `MODEL_ID` hash changed from `"anki-builder-model-v1"` to `"anki-builder-model-v2"` because the field structure changed. This ensures Anki treats this as a new model rather than conflicting with old exports.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_export_apkg.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/export/apkg.py tests/test_export_apkg.py
git commit -m "feat: update Anki export to use new Card field names and template"
```

---

### Task 7: Update CLI and Remaining Tests

**Files:**
- Modify: `src/anki_builder/cli.py:22-27, 168-174`
- Test: `tests/test_cli.py`
- Test: `tests/test_merge.py`
- Test: `tests/test_integration.py`
- Test: `tests/test_ingest_gdrive.py`

- [ ] **Step 1: Update cli.py**

In `src/anki_builder/cli.py`, change `_words_to_cards` (lines 22-27):

```python
def _words_to_cards(words_str: str, target_language: str, source_language: str) -> list[Card]:
    words = [w.strip() for w in words_str.split(",") if w.strip()]
    return [
        Card(source_word=w, target_language=target_language, source_language=source_language, source="cli")
        for w in words
    ]
```

And the review display (lines 167-175):

```python
    for i, card in enumerate(cards, 1):
        click.echo(f"[{i}] {card.source_word}")
        click.echo(f"    Target Word:    {card.target_word or '(missing)'}")
        click.echo(f"    Pronunciation:  {card.target_pronunciation or '(missing)'}")
        click.echo(f"    Example:        {card.target_example_sentence or '(missing)'}")
        click.echo(f"    Mnemonic:       {card.target_mnemonic or '(missing)'}")
        click.echo(f"    Audio:          {'✓' if card.audio_file else '✗'}")
        click.echo(f"    Image:          {'✓' if card.image_file else '✗'}")
        click.echo()
```

- [ ] **Step 2: Update test_cli.py**

Replace `tests/test_cli.py` with:

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import openpyxl
from click.testing import CliRunner

from anki_builder.cli import main


class TestCLI(unittest.TestCase):
    def _create_xlsx(self, path: Path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["word", "translation"])
        ws.append(["dog", "Hund"])
        ws.append(["cat", "Katze"])
        wb.save(path)

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("anki-builder", result.output.lower())

    def test_ingest_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(main, ["ingest", "--input", "vocab.xlsx", "--lang", "en"])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue(Path(".anki-builder/cards.json").exists())

    @patch("anki_builder.cli.enrich_cards")
    def test_enrich_command(self, mock_enrich):
        mock_enrich.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".anki-builder").mkdir()
            Path(".anki-builder/cards.json").write_text("[]")
            result = runner.invoke(
                main, ["enrich"],
                env={"MINIMAX_API_KEY": "test-key"},
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

    def test_export_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".anki-builder").mkdir()
            Path(".anki-builder/cards.json").write_text("[]")
            result = runner.invoke(main, ["export", "--deck", "Test"])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue(Path("output/Test.apkg").exists())


if __name__ == "__main__":
    unittest.main()
```

Note: `test_cli.py` tests are mostly unchanged — they use Excel files with old header names "word"/"translation" which map through `HEADER_ALIASES` to the new field names, so ingestion still works.

- [ ] **Step 3: Update test_merge.py**

Replace `tests/test_merge.py` with:

```python
import tempfile
import unittest
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.state import StateManager
from anki_builder.export.merge import merge_and_export


class TestMerge(unittest.TestCase):
    def test_merge_new_cards_into_existing_deck(self):
        tmpdir = tempfile.mkdtemp()
        state = StateManager(Path(tmpdir) / ".anki-builder")

        cards_v1 = [
            Card(id="id-1", source_word="dog", target_language="en", source="v1",
                 target_word="Hund", status="enriched"),
            Card(id="id-2", source_word="cat", target_language="en", source="v1",
                 target_word="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        new_cards = [
            Card(source_word="dog", target_language="en", source="v2"),
            Card(source_word="bird", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards)
        self.assertEqual(len(merged), 3)
        dog = next(c for c in merged if c.source_word == "dog")
        self.assertEqual(dog.id, "id-1")
        self.assertEqual(dog.target_word, "Hund")
        bird = next(c for c in merged if c.source_word == "bird")
        self.assertIsNone(bird.target_word)
        cat = next(c for c in merged if c.source_word == "cat")
        self.assertEqual(cat.target_word, "Katze")

    def test_merge_with_prune(self):
        tmpdir = tempfile.mkdtemp()
        state = StateManager(Path(tmpdir) / ".anki-builder")

        cards_v1 = [
            Card(id="id-1", source_word="dog", target_language="en", source="v1",
                 target_word="Hund", status="enriched"),
            Card(id="id-2", source_word="cat", target_language="en", source="v1",
                 target_word="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        new_cards = [
            Card(source_word="dog", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards, prune=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].source_word, "dog")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Update test_integration.py**

Replace `tests/test_integration.py` with:

```python
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import openpyxl
from click.testing import CliRunner

from anki_builder.cli import main


class TestFullPipeline(unittest.TestCase):
    """Integration test: Excel → enrich → media → export, all with mocked APIs."""

    def _create_xlsx(self, path: Path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["word", "translation"])
        ws.append(["dog", "Hund"])
        ws.append(["cat", "Katze"])
        wb.save(path)

    @patch("anki_builder.cli.generate_image_batch")
    @patch("anki_builder.cli.generate_audio_batch")
    @patch("anki_builder.cli.enrich_cards")
    def test_full_run_command(self, mock_enrich, mock_audio, mock_image):
        def fake_enrich(cards, api_key, src_lang):
            enriched = []
            for c in cards:
                enriched.append(c.model_copy(update={
                    "target_pronunciation": "/test/",
                    "target_example_sentence": "Test sentence! 🎉",
                    "source_example_sentence": "Testsatz! 🎉",
                    "target_mnemonic": '<span style="color:red">test</span>',
                    "target_part_of_speech": "noun",
                    "status": "enriched",
                }))
            return enriched
        mock_enrich.side_effect = fake_enrich

        mock_audio.side_effect = lambda cards, media_dir: cards
        async def fake_image(cards, media_dir, api_key, concurrency):
            return cards
        mock_image.side_effect = fake_image

        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(
                main,
                ["run", "--input", "vocab.xlsx", "--lang", "en", "--deck", "TestDeck"],
                env={"MINIMAX_API_KEY": "test"},
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

            cards_data = json.loads(Path(".anki-builder/cards.json").read_text())
            self.assertEqual(len(cards_data), 2)
            self.assertEqual(cards_data[0]["source_word"], "dog")
            self.assertEqual(cards_data[0]["target_part_of_speech"], "noun")
            self.assertIn("🎉", cards_data[0]["target_example_sentence"])

            result2 = runner.invoke(main, ["export", "--deck", "TestDeck"])
            self.assertEqual(result2.exit_code, 0, msg=result2.output)
            apkg_path = Path("output/TestDeck.apkg")
            self.assertTrue(apkg_path.exists())
            self.assertTrue(zipfile.is_zipfile(apkg_path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Update test_ingest_gdrive.py**

Replace `tests/test_ingest_gdrive.py` with:

```python
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.ingest.gdrive import extract_folder_id, ingest_gdrive_folder


class TestGDriveIngestion(unittest.TestCase):
    def test_extract_folder_id_from_url(self):
        url = "https://drive.google.com/drive/folders/1abc2def3ghi"
        self.assertEqual(extract_folder_id(url), "1abc2def3ghi")

    def test_extract_folder_id_from_raw_id(self):
        self.assertEqual(extract_folder_id("1abc2def3ghi"), "1abc2def3ghi")

    def test_extract_folder_id_with_query_params(self):
        url = "https://drive.google.com/drive/folders/1abc2def3ghi?usp=sharing"
        self.assertEqual(extract_folder_id(url), "1abc2def3ghi")

    @patch("anki_builder.ingest.gdrive.download_file")
    @patch("anki_builder.ingest.gdrive.list_files_in_folder")
    @patch("anki_builder.ingest.gdrive.ingest_excel")
    def test_ingest_gdrive_folder_with_excel(self, mock_ingest_excel, mock_list, mock_download):
        from anki_builder.schema import Card
        from pathlib import Path
        import tempfile

        mock_list.return_value = [
            {"id": "file1", "name": "vocab.xlsx", "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        ]
        mock_download.return_value = Path(tempfile.mktemp(suffix=".xlsx"))
        mock_ingest_excel.return_value = [
            Card(source_word="dog", target_language="en", source="gdrive"),
        ]

        cards = ingest_gdrive_folder(
            "https://drive.google.com/drive/folders/test123",
            target_language="en",
            google_api_key="test-key",
            minimax_api_key="test-key",
        )
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].source_word, "dog")
        mock_list.assert_called_once_with("test123", "test-key")

    @patch("anki_builder.ingest.gdrive.download_file")
    @patch("anki_builder.ingest.gdrive.list_files_in_folder")
    def test_skips_unsupported_files(self, mock_list, mock_download):
        mock_list.return_value = [
            {"id": "file1", "name": "readme.txt", "mimeType": "text/plain"},
            {"id": "file2", "name": "notes.docx", "mimeType": "application/vnd.openxmlformats"},
        ]

        cards = ingest_gdrive_folder(
            "test-folder-id",
            target_language="en",
            google_api_key="test-key",
            minimax_api_key="test-key",
        )
        self.assertEqual(len(cards), 0)
        mock_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/anki_builder/cli.py tests/test_cli.py tests/test_merge.py tests/test_integration.py tests/test_ingest_gdrive.py
git commit -m "feat: update CLI, merge, and remaining tests for new Card field names"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS with 0 failures.

- [ ] **Step 2: Verify no old field references remain**

Run: `grep -rn "\.word\b" src/anki_builder/ --include="*.py" | grep -v "source_word\|target_word\|password\|keyword"`

Run: `grep -rn "\.translation\b" src/anki_builder/ --include="*.py" | grep -v "sentence_translation\|source_example_sentence"`

Run: `grep -rn "\.pronunciation\b" src/anki_builder/ --include="*.py" | grep -v "target_pronunciation"`

Run: `grep -rn "\.mnemonic\b" src/anki_builder/ --include="*.py" | grep -v "target_mnemonic"`

Run: `grep -rn "\.part_of_speech\b" src/anki_builder/ --include="*.py" | grep -v "target_part_of_speech"`

Run: `grep -rn "\.example_sentence\b" src/anki_builder/ --include="*.py" | grep -v "target_example_sentence\|source_example_sentence"`

Expected: No matches for any of the above — all old field accesses have been renamed.

- [ ] **Step 3: Verify migration works end-to-end**

Create a temporary old-format `cards.json` and verify it loads correctly:

```bash
mkdir -p /tmp/test-migration/.anki-builder
cat > /tmp/test-migration/.anki-builder/cards.json << 'EOF'
[{"id":"test","word":"dog","source_language":"de","target_language":"en","translation":"Hund","pronunciation":"/dɒɡ/","part_of_speech":"noun","mnemonic":null,"example_sentence":"The dog plays.","sentence_translation":"Der Hund spielt.","tags":[],"audio_file":null,"image_file":null,"source":"test","status":"enriched"}]
EOF
cd /tmp/test-migration && python -c "
from pathlib import Path
from anki_builder.state import StateManager
state = StateManager(Path('.anki-builder'))
cards = state.load_cards()
assert cards[0].source_word == 'dog'
assert cards[0].target_word == 'Hund'
assert cards[0].target_pronunciation == '/dɒɡ/'
print('Migration OK')
"
```

Expected: Prints "Migration OK".
