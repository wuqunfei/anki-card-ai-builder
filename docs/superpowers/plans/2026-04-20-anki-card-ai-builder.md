# Anki Card AI Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that ingests vocabulary from Excel/PDF/images, enriches with AI, generates audio/images, and exports Anki `.apkg` packages.

**Architecture:** Stage-based pipeline with local state. Each stage (ingest → enrich → media → export) writes to `.anki-builder/` directory. Stages run independently and are resumable. MiniMax for text/audio/image AI, DeepSeek chat API for vision OCR.

**Tech Stack:** Python 3.12, uv, unittest, Click, Pydantic, openpyxl, pymupdf, genanki, anthropic SDK, httpx

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/anki_builder/__init__.py`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Initialize uv project**

```bash
uv init --lib --name anki-builder
```

- [ ] **Step 2: Replace pyproject.toml with correct config**

```toml
[project]
name = "anki-builder"
version = "0.1.0"
description = "AI-powered Anki flashcard generator for language learning"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1",
    "openpyxl>=3.1",
    "pymupdf>=1.24",
    "genanki>=0.13",
    "anthropic>=0.40",
    "httpx>=0.27",
    "pydantic>=2.9",
    "pyyaml>=6.0",
]

[project.scripts]
anki-builder = "anki_builder.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 3: Create .gitignore**

```
.venv/
__pycache__/
*.pyc
.anki-builder/
output/
.env
*.egg-info/
dist/
```

- [ ] **Step 4: Create .env.example**

```
MINIMAX_API_KEY=your-minimax-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
```

- [ ] **Step 5: Create package init**

```python
# src/anki_builder/__init__.py
```

(Empty file.)

- [ ] **Step 6: Install dependencies**

```bash
uv sync
```

- [ ] **Step 7: Verify installation**

```bash
uv run python -c "import anki_builder; print('OK')"
```

Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src/ .gitignore .env.example uv.lock
git commit -m "feat: scaffold project with uv and dependencies"
```

---

### Task 2: Card Schema & State Management

**Files:**
- Create: `src/anki_builder/schema.py`
- Create: `src/anki_builder/state.py`
- Create: `tests/test_schema.py`
- Create: `tests/test_state.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write failing test for Card schema**

```python
# tests/__init__.py
```

```python
# tests/test_schema.py
import unittest
from anki_builder.schema import Card


class TestCard(unittest.TestCase):
    def test_create_full_card(self):
        card = Card(
            word="accomplish",
            source_language="de",
            target_language="en",
            source="vocab.xlsx",
        )
        self.assertEqual(card.word, "accomplish")
        self.assertEqual(card.source_language, "de")
        self.assertEqual(card.target_language, "en")
        self.assertEqual(card.status, "extracted")
        self.assertIsNotNone(card.id)
        self.assertIsNone(card.translation)
        self.assertIsNone(card.pronunciation)
        self.assertIsNone(card.example_sentence)
        self.assertIsNone(card.sentence_translation)
        self.assertIsNone(card.mnemonic)
        self.assertIsNone(card.part_of_speech)
        self.assertEqual(card.tags, [])

    def test_card_id_is_uuid(self):
        import uuid
        card = Card(word="test", source_language="de", target_language="en", source="test")
        uuid.UUID(card.id)  # Raises if not valid UUID

    def test_card_serialization_roundtrip(self):
        card = Card(
            word="Hund",
            source_language="de",
            target_language="en",
            translation="dog",
            source="vocab.xlsx",
        )
        data = card.model_dump()
        card2 = Card(**data)
        self.assertEqual(card, card2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_schema.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'anki_builder.schema'`

- [ ] **Step 3: Implement Card schema**

```python
# src/anki_builder/schema.py
import uuid

from pydantic import BaseModel, Field


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    word: str
    source_language: str = "de"
    target_language: str = "en"
    translation: str | None = None
    pronunciation: str | None = None  # IPA for en/fr, pinyin for zh
    example_sentence: str | None = None
    sentence_translation: str | None = None
    mnemonic: str | None = None  # HTML rich text: prefix (blue) + root (red) + suffix (green)
    part_of_speech: str | None = None
    tags: list[str] = Field(default_factory=list)
    audio_file: str | None = None
    image_file: str | None = None
    source: str
    status: str = "extracted"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_schema.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Write failing test for state management**

```python
# tests/test_state.py
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
            Card(word="dog", target_language="en", source="test.xlsx"),
            Card(word="chat", target_language="fr", source="test.xlsx"),
        ]
        self.state.save_cards(cards)
        loaded = self.state.load_cards()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].word, "dog")
        self.assertEqual(loaded[1].word, "chat")

    def test_load_empty_returns_empty_list(self):
        loaded = self.state.load_cards()
        self.assertEqual(loaded, [])

    def test_merge_new_cards(self):
        existing = [
            Card(word="dog", target_language="en", source="test.xlsx"),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(word="dog", target_language="en", source="test.xlsx"),
            Card(word="cat", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(len(merged), 2)
        # Existing card keeps its ID
        self.assertEqual(merged[0].id, existing[0].id)
        # New card gets added
        self.assertEqual(merged[1].word, "cat")

    def test_merge_preserves_enriched_fields(self):
        existing = [
            Card(
                word="dog",
                target_language="en",
                source="test.xlsx",
                translation="Hund",
                status="enriched",
            ),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(word="dog", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(merged[0].translation, "Hund")
        self.assertEqual(merged[0].status, "enriched")

    def test_media_dir_created(self):
        media_dir = self.state.media_dir
        self.assertTrue(media_dir.exists())
        self.assertTrue(media_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_state.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'anki_builder.state'`

- [ ] **Step 7: Implement StateManager**

```python
# src/anki_builder/state.py
import json
from pathlib import Path

from anki_builder.schema import Card


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
        return [Card(**item) for item in data]

    def save_cards(self, cards: list[Card]) -> None:
        data = [card.model_dump() for card in cards]
        self.cards_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def merge_cards(self, new_cards: list[Card]) -> list[Card]:
        existing = self.load_cards()
        existing_map: dict[tuple[str, str], Card] = {
            (c.word, c.target_language): c for c in existing
        }

        merged: list[Card] = []
        for card in new_cards:
            key = (card.word, card.target_language)
            if key in existing_map:
                old = existing_map.pop(key)
                # Keep enriched fields from existing card
                update_data = {}
                for field in ["translation", "pronunciation", "example_sentence",
                              "sentence_translation", "mnemonic", "part_of_speech",
                              "audio_file", "image_file"]:
                    old_val = getattr(old, field)
                    new_val = getattr(card, field)
                    if old_val is not None and new_val is None:
                        update_data[field] = old_val
                # Preserve ID and status from existing
                update_data["id"] = old.id
                if old.status != "extracted":
                    update_data["status"] = old.status
                merged.append(card.model_copy(update=update_data))
            else:
                merged.append(card)

        return merged
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_schema.py tests/test_state.py -v
```

Expected: All 8 tests PASS

- [ ] **Step 9: Commit**

```bash
git add src/anki_builder/schema.py src/anki_builder/state.py tests/
git commit -m "feat: add Card schema and StateManager with merge support"
```

---

### Task 3: Configuration

**Files:**
- Create: `src/anki_builder/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test for config**

```python
# tests/test_config.py
import os
import tempfile
import unittest
from pathlib import Path

from anki_builder.config import Config, load_config


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        config = Config()
        self.assertEqual(config.default_source_language, "de")
        self.assertEqual(config.default_target_language, "en")
        self.assertTrue(config.media.audio_enabled)
        self.assertTrue(config.media.image_enabled)
        self.assertEqual(config.media.concurrency, 5)
        self.assertEqual(config.export.default_deck_name, "Vocabulary")

    def test_load_config_from_yaml(self):
        tmpdir = tempfile.mkdtemp()
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(
            "default_source_language: fr\n"
            "default_target_language: zh\n"
            "export:\n"
            "  default_deck_name: 'Chinese Words'\n"
        )
        config = load_config(Path(tmpdir))
        self.assertEqual(config.default_source_language, "fr")
        self.assertEqual(config.default_target_language, "zh")
        self.assertEqual(config.export.default_deck_name, "Chinese Words")

    def test_load_config_missing_file_returns_defaults(self):
        tmpdir = tempfile.mkdtemp()
        config = load_config(Path(tmpdir))
        self.assertEqual(config.default_source_language, "de")

    def test_api_keys_from_env(self):
        os.environ["MINIMAX_API_KEY"] = "test-minimax-key"
        os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"
        try:
            config = Config()
            self.assertEqual(config.minimax_api_key, "test-minimax-key")
            self.assertEqual(config.deepseek_api_key, "test-deepseek-key")
        finally:
            del os.environ["MINIMAX_API_KEY"]
            del os.environ["DEEPSEEK_API_KEY"]


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Config**

```python
# src/anki_builder/config.py
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class MediaConfig(BaseModel):
    audio_enabled: bool = True
    image_enabled: bool = True
    concurrency: int = 5


class ExportConfig(BaseModel):
    default_deck_name: str = "Vocabulary"
    output_dir: str = "./output"


class Config(BaseModel):
    default_source_language: str = "de"
    default_target_language: str = "en"
    learner_profile: str = "ages 9-12, kid-friendly with emojis"
    media: MediaConfig = Field(default_factory=MediaConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    @property
    def minimax_api_key(self) -> str:
        return os.environ.get("MINIMAX_API_KEY", "")

    @property
    def deepseek_api_key(self) -> str:
        return os.environ.get("DEEPSEEK_API_KEY", "")


def load_config(work_dir: Path) -> Config:
    config_path = work_dir / "config.yaml"
    if not config_path.exists():
        return Config()
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return Config(**data)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_config.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/config.py tests/test_config.py
git commit -m "feat: add Config with YAML loading and env var API keys"
```

---

### Task 4: Excel Ingestion

**Files:**
- Create: `src/anki_builder/ingest/__init__.py`
- Create: `src/anki_builder/ingest/excel.py`
- Create: `tests/test_ingest_excel.py`
- Create: `tests/fixtures/sample_vocab.xlsx` (generated in test setUp)

- [ ] **Step 1: Write failing test for Excel ingestion**

```python
# tests/test_ingest_excel.py
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
        self.assertEqual(cards[0].word, "dog")
        self.assertEqual(cards[0].translation, "Hund")
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
        self.assertEqual(cards[0].word, "Hund")
        self.assertEqual(cards[0].translation, "dog")

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
            column_map={"vocab": "word", "meaning": "translation"},
        )
        self.assertEqual(cards[0].word, "accomplish")
        self.assertEqual(cards[0].translation, "erreichen")

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
        self.assertEqual(cards[0].word, "dog")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_ingest_excel.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Excel ingestion**

```python
# src/anki_builder/ingest/__init__.py
```

```python
# src/anki_builder/ingest/excel.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_ingest_excel.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/ingest/ tests/test_ingest_excel.py
git commit -m "feat: add Excel/CSV ingestion with fuzzy header matching"
```

---

### Task 5: PDF Ingestion

**Files:**
- Create: `src/anki_builder/ingest/pdf.py`
- Create: `tests/test_ingest_pdf.py`

- [ ] **Step 1: Write failing test for PDF ingestion**

```python
# tests/test_ingest_pdf.py
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

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
            {"word": "dog", "translation": "Hund"},
            {"word": "cat", "translation": "Katze"},
        ]
        tmpdir = tempfile.mkdtemp()
        path = self._create_pdf_with_text(
            "dog - Hund\ncat - Katze",
            Path(tmpdir) / "vocab.pdf",
        )
        cards = ingest_pdf(path, target_language="en", deepseek_api_key="test-key")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].word, "dog")
        mock_ai.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_ingest_pdf.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement PDF ingestion**

```python
# src/anki_builder/ingest/pdf.py
import base64
from pathlib import Path

import httpx
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
        # Digital PDF — send extracted text to AI for structuring
        vocab_items = extract_vocabulary_with_ai(
            text=text,
            target_language=target_language,
            source_language=source_language,
            deepseek_api_key=deepseek_api_key,
        )
    else:
        # Scanned PDF — convert pages to images, send to DeepSeek vision
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_ingest_pdf.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/ingest/pdf.py tests/test_ingest_pdf.py
git commit -m "feat: add PDF ingestion with pymupdf and AI extraction"
```

---

### Task 6: Vocabulary Extraction with DeepSeek AI

**Files:**
- Create: `src/anki_builder/enrich/__init__.py`
- Create: `src/anki_builder/enrich/vocabulary.py`
- Create: `tests/test_vocabulary.py`

- [ ] **Step 1: Write failing test for vocabulary extraction**

```python
# tests/test_vocabulary.py
import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.enrich.vocabulary import (
    extract_vocabulary_with_ai,
    _build_text_prompt,
    _build_vision_prompt,
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

    def test_build_vision_prompt(self):
        prompt = _build_vision_prompt(
            target_language="en",
            source_language="de",
        )
        self.assertIn("vocabulary", prompt.lower())
        self.assertIn("JSON", prompt)

    def test_parse_vocabulary_response(self):
        response_text = json.dumps([
            {"word": "dog", "translation": "Hund"},
            {"word": "cat", "translation": "Katze"},
        ])
        items = _parse_vocabulary_response(response_text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["word"], "dog")
        self.assertEqual(items[1]["translation"], "Katze")

    def test_parse_response_with_markdown_code_block(self):
        response_text = '```json\n[{"word": "dog", "translation": "Hund"}]\n```'
        items = _parse_vocabulary_response(response_text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["word"], "dog")

    @patch("anki_builder.enrich.vocabulary.httpx.post")
    def test_extract_vocabulary_with_text(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps([
                        {"word": "dog", "translation": "Hund"},
                    ])
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        items = extract_vocabulary_with_ai(
            text="dog - Hund",
            target_language="en",
            source_language="de",
            deepseek_api_key="test-key",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["word"], "dog")
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_vocabulary.py -v
```

Expected: FAIL ��� `ModuleNotFoundError`

- [ ] **Step 3: Implement vocabulary extraction**

```python
# src/anki_builder/enrich/__init__.py
```

```python
# src/anki_builder/enrich/vocabulary.py
import base64
import json
import re

import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def _build_text_prompt(text: str, target_language: str, source_language: str) -> str:
    return (
        f"Extract vocabulary words from the following text. The text is in "
        f"{target_language} (target language) and {source_language} (source language).\n\n"
        f"For each word, extract any available information: word, translation, "
        f"pronunciation, example_sentence, part_of_speech.\n\n"
        f"Return ONLY a JSON array of objects. Each object should have the fields "
        f"that are present in the source. Do not generate content that isn't in "
        f"the source text — only extract what's there.\n\n"
        f"Text:\n{text}"
    )


def _build_vision_prompt(target_language: str, source_language: str) -> str:
    return (
        f"Extract vocabulary words from this image. The content is in "
        f"{target_language} (target language) and {source_language} (source language).\n\n"
        f"For each word, extract any available information: word, translation, "
        f"pronunciation, example_sentence, part_of_speech.\n\n"
        f"Return ONLY a JSON array of objects. Each object should have the fields "
        f"that are present in the source. Do not generate content that isn't in "
        f"the image — only extract what's visible."
    )


def _parse_vocabulary_response(text: str) -> list[dict]:
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def extract_vocabulary_with_ai(
    target_language: str,
    source_language: str,
    deepseek_api_key: str,
    text: str | None = None,
    image_bytes: bytes | None = None,
) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json",
    }

    if image_bytes is not None:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
                {
                    "type": "text",
                    "text": _build_vision_prompt(target_language, source_language),
                },
            ],
        }]
    elif text is not None:
        messages = [{
            "role": "user",
            "content": _build_text_prompt(text, target_language, source_language),
        }]
    else:
        return []

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.1,
    }

    response = httpx.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return _parse_vocabulary_response(content)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_vocabulary.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/enrich/ tests/test_vocabulary.py
git commit -m "feat: add DeepSeek-powered vocabulary extraction for text and images"
```

---

### Task 7: Image Ingestion (OCR via DeepSeek Vision)

**Files:**
- Create: `src/anki_builder/ingest/image.py`
- Create: `tests/test_ingest_image.py`

- [ ] **Step 1: Write failing test for image ingestion**

```python
# tests/test_ingest_image.py
import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.ingest.image import ingest_image


class TestImageIngestion(unittest.TestCase):
    @patch("anki_builder.ingest.image.extract_vocabulary_with_ai")
    def test_ingest_image(self, mock_ai):
        mock_ai.return_value = [
            {"word": "apple", "translation": "Apfel"},
            {"word": "banana", "translation": "Banane"},
        ]
        # Create a minimal PNG (1x1 pixel)
        import struct, zlib
        def make_tiny_png() -> bytes:
            raw = b"\x00\x00\x00\x00"
            compressed = zlib.compress(raw)
            def chunk(ctype, data):
                c = ctype + data
                return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return (
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", compressed)
                + chunk(b"IEND", b"")
            )

        import tempfile
        from pathlib import Path
        tmpdir = tempfile.mkdtemp()
        img_path = Path(tmpdir) / "page.png"
        img_path.write_bytes(make_tiny_png())

        cards = ingest_image(img_path, target_language="en", deepseek_api_key="test-key")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].word, "apple")
        self.assertEqual(cards[0].translation, "Apfel")
        self.assertEqual(cards[0].source, str(img_path))
        mock_ai.assert_called_once()
        # Verify image_bytes was passed
        call_kwargs = mock_ai.call_args[1]
        self.assertIsNotNone(call_kwargs.get("image_bytes"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_ingest_image.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement image ingestion**

```python
# src/anki_builder/ingest/image.py
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_ingest_image.py -v
```

Expected: 1 test PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/ingest/image.py tests/test_ingest_image.py
git commit -m "feat: add image ingestion via DeepSeek vision OCR"
```

---

### Task 8: AI Enrichment via MiniMax

**Files:**
- Create: `src/anki_builder/enrich/ai.py`
- Create: `tests/test_enrich_ai.py`

- [ ] **Step 1: Write failing test for AI enrichment**

```python
# tests/test_enrich_ai.py
import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.schema import Card
from anki_builder.enrich.ai import enrich_cards, _build_enrichment_prompt, _batch_cards


class TestAIEnrichment(unittest.TestCase):
    def test_build_enrichment_prompt(self):
        cards = [
            Card(word="dog", target_language="en", source="test"),
        ]
        prompt = _build_enrichment_prompt(cards, source_language="de")
        self.assertIn("dog", prompt)
        self.assertIn("kid-friendly", prompt.lower())
        self.assertIn("emoji", prompt.lower())
        self.assertIn("mnemonic", prompt.lower())
        self.assertIn("JSON", prompt)

    def test_batch_cards(self):
        cards = [Card(word=f"word{i}", target_language="en", source="test") for i in range(45)]
        batches = _batch_cards(cards, batch_size=20)
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0]), 20)
        self.assertEqual(len(batches[1]), 20)
        self.assertEqual(len(batches[2]), 5)

    def test_already_enriched_cards_skipped(self):
        cards = [
            Card(word="dog", target_language="en", source="test", status="enriched"),
            Card(word="cat", target_language="en", source="test", status="extracted"),
        ]
        to_enrich = [c for c in cards if c.status == "extracted"]
        self.assertEqual(len(to_enrich), 1)
        self.assertEqual(to_enrich[0].word, "cat")

    @patch("anki_builder.enrich.ai.anthropic")
    def test_enrich_cards(self, mock_anthropic_module):
        mock_client = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        enriched_data = json.dumps([{
            "word": "dog",
            "translation": "Hund",
            "pronunciation": "/dɒɡ/",
            "example_sentence": "The dog loves to play in the park! 🐕",
            "sentence_translation": "Der Hund spielt gern im Park! 🐕",
            "mnemonic": '<span style="color:red">dog</span>',
            "part_of_speech": "noun",
        }])

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=enriched_data)]
        mock_client.messages.create.return_value = mock_response

        cards = [Card(word="dog", target_language="en", source="test")]
        result = enrich_cards(cards, minimax_api_key="test-key", source_language="de")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].translation, "Hund")
        self.assertEqual(result[0].pronunciation, "/dɒɡ/")
        self.assertIn("🐕", result[0].example_sentence)
        self.assertIn("🐕", result[0].sentence_translation)
        self.assertIn("color:red", result[0].mnemonic)
        self.assertEqual(result[0].part_of_speech, "noun")
        self.assertEqual(result[0].status, "enriched")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_enrich_ai.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement AI enrichment**

```python
# src/anki_builder/enrich/ai.py
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
        entry = {"word": c.word, "target_language": c.target_language}
        if c.translation:
            entry["translation"] = c.translation
        if c.pronunciation:
            entry["pronunciation"] = c.pronunciation
        if c.example_sentence:
            entry["example_sentence"] = c.example_sentence
        if c.sentence_translation:
            entry["sentence_translation"] = c.sentence_translation
        card_list.append(entry)

    return (
        f"You are a friendly language tutor for German-speaking kids aged 9-12.\n\n"
        f"For each word below, fill in the missing fields. The source language is "
        f"'{source_language}'. Keep sentences simple, natural, and kid-friendly with "
        f"emoji sprinkled in.\n\n"
        f"For EVERY word, you MUST generate:\n"
        f"- `part_of_speech`: the grammatical category (noun, verb, adjective, etc.)\n"
        f"- `mnemonic`: word breakdown as HTML with colored parts:\n"
        f'  prefix in blue: <span style="color:blue">un-</span>\n'
        f'  root in red: <span style="color:red">break</span>\n'
        f'  suffix in green: <span style="color:green">-able</span>\n'
        f"  Join parts with \" + \". If a word has no prefix/suffix, just show the root in red.\n\n"
        f"For fields that are already filled, keep the existing value.\n"
        f"For missing fields, generate:\n"
        f"- `translation`: translate to {source_language}\n"
        f"- `pronunciation`: IPA for English/French, pinyin with tone marks for Chinese\n"
        f"- `example_sentence`: a kid-friendly sentence with emojis\n"
        f"- `sentence_translation`: translation of the example to {source_language}, also kid-friendly with emojis\n\n"
        f"Return ONLY a JSON array with one object per word. Each object must have all fields: "
        f"word, translation, pronunciation, example_sentence, sentence_translation, mnemonic, part_of_speech.\n\n"
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
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.content[0].text
        items = _parse_enrichment_response(content)

        # Match enriched items back to cards
        item_map = {item["word"]: item for item in items if "word" in item}
        for card in batch:
            if card.word in item_map:
                item = item_map[card.word]
                update = {"status": "enriched"}
                for field in ["translation", "pronunciation", "example_sentence",
                              "sentence_translation"]:
                    if getattr(card, field) is None and field in item:
                        update[field] = item[field]
                # Always overwrite these
                for field in ["mnemonic", "part_of_speech"]:
                    if field in item:
                        update[field] = item[field]
                enriched.append(card.model_copy(update=update))
            else:
                enriched.append(card)

    return already_done + enriched
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_enrich_ai.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/enrich/ai.py tests/test_enrich_ai.py
git commit -m "feat: add AI enrichment via MiniMax Anthropic-compatible API"
```

---

### Task 9: Audio Generation via MiniMax T2A

**Files:**
- Create: `src/anki_builder/media/__init__.py`
- Create: `src/anki_builder/media/audio.py`
- Create: `tests/test_media_audio.py`

- [ ] **Step 1: Write failing test for audio generation**

```python
# tests/test_media_audio.py
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from anki_builder.schema import Card
from anki_builder.media.audio import generate_audio_for_card, generate_audio_batch


class TestAudioGeneration(unittest.TestCase):
    @patch("anki_builder.media.audio.httpx.AsyncClient")
    def test_generate_audio_for_card(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock create task response
        create_resp = MagicMock()
        create_resp.json.return_value = {"task_id": "task-123"}
        create_resp.raise_for_status = MagicMock()

        # Mock query status response (completed)
        status_resp = MagicMock()
        status_resp.json.return_value = {
            "status": "Success",
            "file_id": "file-456",
        }
        status_resp.raise_for_status = MagicMock()

        # Mock download response
        download_resp = MagicMock()
        download_resp.content = b"fake-mp3-data"
        download_resp.raise_for_status = MagicMock()

        mock_client.post.return_value = create_resp
        mock_client.get.side_effect = [status_resp, download_resp]

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")

        result = asyncio.run(
            generate_audio_for_card(card, media_dir, "test-key", mock_client)
        )
        self.assertIsNotNone(result.audio_file)
        self.assertIn("audio.mp3", result.audio_file)

    def test_skip_existing_audio(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        audio_path = media_dir / "fixed-id_audio.mp3"
        audio_path.write_bytes(b"existing-audio")
        card = card.model_copy(update={"audio_file": str(audio_path)})

        # Should skip — audio_file already set
        result = asyncio.run(
            generate_audio_for_card(card, media_dir, "test-key", AsyncMock())
        )
        self.assertEqual(result.audio_file, str(audio_path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_media_audio.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement audio generation**

```python
# src/anki_builder/media/__init__.py
```

```python
# src/anki_builder/media/audio.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_media_audio.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/media/ tests/test_media_audio.py
git commit -m "feat: add async audio generation via MiniMax T2A API"
```

---

### Task 10: Image Generation via MiniMax

**Files:**
- Create: `src/anki_builder/media/image.py`
- Create: `tests/test_media_image.py`

- [ ] **Step 1: Write failing test for image generation**

```python
# tests/test_media_image.py
import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from anki_builder.schema import Card
from anki_builder.media.image import generate_image_for_card, generate_image_batch


class TestImageGeneration(unittest.TestCase):
    @patch("anki_builder.media.image.httpx.AsyncClient")
    def test_generate_image_for_card(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # Fake 1x1 PNG as base64
        fake_image = base64.b64encode(b"fake-png-data").decode()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {"image_base64": [fake_image]}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_resp

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")

        result = asyncio.run(
            generate_image_for_card(card, media_dir, "test-key", mock_client)
        )
        self.assertIsNotNone(result.image_file)
        self.assertIn("image.png", result.image_file)
        # Verify file was written
        self.assertTrue(Path(result.image_file).exists())

    def test_skip_existing_image(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        img_path = media_dir / "fixed-id_image.png"
        img_path.write_bytes(b"existing-image")
        card = card.model_copy(update={"image_file": str(img_path)})

        result = asyncio.run(
            generate_image_for_card(card, media_dir, "test-key", AsyncMock())
        )
        self.assertEqual(result.image_file, str(img_path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_media_image.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement image generation**

```python
# src/anki_builder/media/image.py
import asyncio
import base64
from pathlib import Path

import httpx

from anki_builder.schema import Card

MINIMAX_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
MINIMAX_IMAGE_MODEL = "image-01"


def _build_image_prompt(word: str, target_language: str) -> str:
    return (
        f"Simple, colorful illustration of '{word}' suitable for children aged 9-12. "
        f"Friendly cartoon style, no text in the image."
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
        "prompt": _build_image_prompt(card.word, card.target_language),
        "aspect_ratio": "1:1",
        "response_format": "base64",
    }

    resp = await client.post(
        MINIMAX_IMAGE_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    b64_data = resp.json()["data"]["image_base64"][0]
    image_bytes = base64.b64decode(b64_data)
    image_path.write_bytes(image_bytes)

    return card.model_copy(update={"image_file": str(image_path)})


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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_media_image.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/media/image.py tests/test_media_image.py
git commit -m "feat: add image generation via MiniMax image API"
```

---

### Task 11: Anki Export (.apkg)

**Files:**
- Create: `src/anki_builder/export/__init__.py`
- Create: `src/anki_builder/export/apkg.py`
- Create: `tests/test_export_apkg.py`

- [ ] **Step 1: Write failing test for .apkg export**

```python
# tests/test_export_apkg.py
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
                word="dog",
                target_language="en",
                source="test",
                translation="Hund",
                pronunciation="/dɒɡ/",
                example_sentence="The dog plays in the park! 🐕",
                sentence_translation="Der Hund spielt im Park! 🐕",
                mnemonic='<span style="color:red">dog</span>',
                part_of_speech="noun",
                status="enriched",
            ),
            Card(
                id="card-2",
                word="cat",
                target_language="en",
                source="test",
                translation="Katze",
                pronunciation="/kæt/",
                example_sentence="The cat sleeps on the sofa! ��",
                sentence_translation="Die Katze schläft auf dem Sofa! 🐱",
                mnemonic='<span style="color:red">cat</span>',
                part_of_speech="noun",
                status="enriched",
            ),
        ]

    def test_export_creates_apkg_file(self):
        tmpdir = tempfile.mkdtemp()
        output_path = Path(tmpdir) / "test.apkg"
        cards = self._make_cards()

        export_apkg(cards, output_path, deck_name="Test Deck")

        self.assertTrue(output_path.exists())
        # .apkg is a zip file
        self.assertTrue(zipfile.is_zipfile(output_path))

    def test_export_with_media(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        # Create fake audio file
        audio_path = media_dir / "card-1_audio.mp3"
        audio_path.write_bytes(b"fake-audio")

        cards = self._make_cards()
        cards[0] = cards[0].model_copy(update={"audio_file": str(audio_path)})

        output_path = Path(tmpdir) / "test.apkg"
        export_apkg(cards, output_path, deck_name="Test Deck")

        self.assertTrue(output_path.exists())
        # Verify media is inside the zip
        with zipfile.ZipFile(output_path) as zf:
            names = zf.namelist()
            # genanki stores media with numeric names
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

```bash
uv run python -m pytest tests/test_export_apkg.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement .apkg export**

```python
# src/anki_builder/export/__init__.py
```

```python
# src/anki_builder/export/apkg.py
import hashlib
from pathlib import Path

import genanki

from anki_builder.schema import Card

# Stable model ID derived from a hash so it's consistent across runs
MODEL_ID = int(hashlib.md5(b"anki-builder-model-v1").hexdigest()[:8], 16)

CARD_MODEL = genanki.Model(
    MODEL_ID,
    "Anki Builder Card",
    fields=[
        {"name": "Word"},
        {"name": "Translation"},
        {"name": "Pronunciation"},
        {"name": "ExampleSentence"},
        {"name": "SentenceTranslation"},
        {"name": "Mnemonic"},
        {"name": "PartOfSpeech"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[{
        "name": "Card 1",
        "qfmt": (
            '<div style="text-align:center; font-size:24px; margin:20px;">'
            "{{Word}}"
            "</div>"
            '<div style="text-align:center;">{{Image}}</div>'
            '<div style="text-align:center;">{{Audio}}</div>'
        ),
        "afmt": (
            '{{FrontSide}}<hr id="answer">'
            '<div style="text-align:center; font-size:20px; color:#333;">{{Translation}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{Pronunciation}}</div>'
            '<div style="text-align:center; font-size:14px; margin:10px;">{{Mnemonic}}</div>'
            '<div style="text-align:center; font-size:16px; margin:10px;">{{ExampleSentence}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{SentenceTranslation}}</div>'
            '<div style="text-align:center; font-size:12px; color:#999;">{{PartOfSpeech}}</div>'
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
            card.word,
            card.translation or "",
            card.pronunciation or "",
            card.example_sentence or "",
            card.sentence_translation or "",
            card.mnemonic or "",
            card.part_of_speech or "",
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_export_apkg.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/export/ tests/test_export_apkg.py
git commit -m "feat: add .apkg export with HTML card template and media embedding"
```

---

### Task 12: Merge/Update Support

**Files:**
- Create: `src/anki_builder/export/merge.py`
- Create: `tests/test_merge.py`

- [ ] **Step 1: Write failing test for merge**

```python
# tests/test_merge.py
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

        # First run: save 2 cards
        cards_v1 = [
            Card(id="id-1", word="dog", target_language="en", source="v1",
                 translation="Hund", status="enriched"),
            Card(id="id-2", word="cat", target_language="en", source="v1",
                 translation="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        # Second run: new extraction has dog + bird (cat removed, bird added)
        new_cards = [
            Card(word="dog", target_language="en", source="v2"),
            Card(word="bird", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards)
        self.assertEqual(len(merged), 2)
        # dog keeps old ID and enriched data
        dog = next(c for c in merged if c.word == "dog")
        self.assertEqual(dog.id, "id-1")
        self.assertEqual(dog.translation, "Hund")
        # bird is new
        bird = next(c for c in merged if c.word == "bird")
        self.assertIsNone(bird.translation)

    def test_merge_with_prune(self):
        tmpdir = tempfile.mkdtemp()
        state = StateManager(Path(tmpdir) / ".anki-builder")

        cards_v1 = [
            Card(id="id-1", word="dog", target_language="en", source="v1",
                 translation="Hund", status="enriched"),
            Card(id="id-2", word="cat", target_language="en", source="v1",
                 translation="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        new_cards = [
            Card(word="dog", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards, prune=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].word, "dog")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_merge.py -v
```

Expected: FAIL — `merge_and_export` import fails / `prune` parameter not supported

- [ ] **Step 3: Update StateManager.merge_cards to support prune**

Update `src/anki_builder/state.py` — add `prune` parameter to `merge_cards`:

```python
    def merge_cards(self, new_cards: list[Card], prune: bool = False) -> list[Card]:
        existing = self.load_cards()
        existing_map: dict[tuple[str, str], Card] = {
            (c.word, c.target_language): c for c in existing
        }

        merged: list[Card] = []
        seen_keys: set[tuple[str, str]] = set()
        for card in new_cards:
            key = (card.word, card.target_language)
            seen_keys.add(key)
            if key in existing_map:
                old = existing_map[key]
                update_data = {}
                for field in ["translation", "pronunciation", "example_sentence",
                              "sentence_translation", "mnemonic", "part_of_speech",
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

        # Keep cards not in new set (unless pruning)
        if not prune:
            for key, card in existing_map.items():
                if key not in seen_keys:
                    merged.append(card)

        return merged
```

- [ ] **Step 4: Create merge helper module**

```python
# src/anki_builder/export/merge.py
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.state import StateManager
from anki_builder.export.apkg import export_apkg


def merge_and_export(
    new_cards: list[Card],
    work_dir: Path,
    output_path: Path,
    deck_name: str = "Vocabulary",
    prune: bool = False,
) -> list[Card]:
    state = StateManager(work_dir)
    merged = state.merge_cards(new_cards, prune=prune)
    state.save_cards(merged)
    export_apkg(merged, output_path, deck_name)
    return merged
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_merge.py tests/test_state.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/anki_builder/state.py src/anki_builder/export/merge.py tests/test_merge.py
git commit -m "feat: add merge/update with prune support"
```

---

### Task 13: CLI Interface

**Files:**
- Create: `src/anki_builder/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for CLI**

```python
# tests/test_cli.py
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
            self.assertEqual(result.exit_code, 0)
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
            self.assertEqual(result.exit_code, 0)

    def test_export_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".anki-builder").mkdir()
            Path(".anki-builder/cards.json").write_text("[]")
            result = runner.invoke(main, ["export", "--deck", "Test"])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(Path("output/Test.apkg").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# src/anki_builder/cli.py
import asyncio
from pathlib import Path

import click

from anki_builder.config import load_config
from anki_builder.schema import Card
from anki_builder.state import StateManager
from anki_builder.ingest.excel import ingest_excel
from anki_builder.ingest.pdf import ingest_pdf
from anki_builder.ingest.image import ingest_image
from anki_builder.enrich.ai import enrich_cards
from anki_builder.media.audio import generate_audio_batch
from anki_builder.media.image import generate_image_batch
from anki_builder.export.apkg import export_apkg

WORK_DIR = Path(".anki-builder")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _detect_input_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".csv"):
        return "excel"
    elif suffix == ".pdf":
        return "pdf"
    elif suffix in IMAGE_EXTENSIONS:
        return "image"
    else:
        raise click.ClickException(f"Unsupported file type: {suffix}")


@click.group()
def main():
    """Anki Card AI Builder — generate flashcards for language learning."""
    pass


@main.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Input file path")
@click.option("--lang", "target_language", required=True, help="Target language code (en, fr, zh)")
@click.option("--source-lang", "source_language", default=None, help="Source language code (default: from config)")
@click.option("--column-map", type=str, default=None, help="Column mapping as key=value pairs, comma-separated")
def ingest(input_path: str, target_language: str, source_language: str | None, column_map: str | None):
    """Extract vocabulary from input files."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    src_lang = source_language or config.default_source_language
    path = Path(input_path)
    input_type = _detect_input_type(path)

    col_map = None
    if column_map:
        col_map = dict(pair.split("=") for pair in column_map.split(","))

    click.echo(f"Ingesting {path.name} as {input_type}...")

    if input_type == "excel":
        cards = ingest_excel(path, target_language, src_lang, col_map)
    elif input_type == "pdf":
        cards = ingest_pdf(path, target_language, config.deepseek_api_key, src_lang)
    elif input_type == "image":
        cards = ingest_image(path, target_language, config.deepseek_api_key, src_lang)

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    click.echo(f"Extracted {len(cards)} cards. Total: {len(merged)} cards.")


@main.command()
@click.option("--source-lang", "source_language", default=None, help="Source language override")
def enrich(source_language: str | None):
    """Fill missing card fields using AI."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    src_lang = source_language or config.default_source_language

    cards = state.load_cards()
    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    to_enrich = [c for c in cards if c.status == "extracted"]
    click.echo(f"Enriching {len(to_enrich)} of {len(cards)} cards...")

    enriched = enrich_cards(cards, config.minimax_api_key, src_lang)
    state.save_cards(enriched)
    click.echo(f"Enrichment complete.")


@main.command()
@click.option("--no-images", is_flag=True, help="Skip image generation")
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
def media(no_images: bool, no_audio: bool):
    """Generate audio and images for cards."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    if not no_audio and config.media.audio_enabled:
        click.echo(f"Generating audio for {len(cards)} cards...")
        cards = asyncio.run(generate_audio_batch(
            cards, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))

    if not no_images and config.media.image_enabled:
        click.echo(f"Generating images for {len(cards)} cards...")
        cards = asyncio.run(generate_image_batch(
            cards, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))

    # Update status to complete for cards that have both media
    updated = []
    for card in cards:
        if card.status == "enriched" and card.audio_file and card.image_file:
            updated.append(card.model_copy(update={"status": "complete"}))
        elif card.status == "enriched" and (no_images or no_audio):
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)

    state.save_cards(updated)
    click.echo("Media generation complete.")


@main.command()
@click.option("--deck", "deck_name", default=None, help="Deck name")
@click.option("--output", "output_path", default=None, help="Output .apkg file path")
@click.option("--prune", is_flag=True, help="Remove cards not in current source")
def export(deck_name: str | None, output_path: str | None, prune: bool):
    """Export cards to .apkg file."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    name = deck_name or config.export.default_deck_name
    out = Path(output_path) if output_path else Path(config.export.output_dir) / f"{name}.apkg"

    click.echo(f"Exporting {len(cards)} cards to {out}...")
    export_apkg(cards, out, name)
    click.echo(f"Done! Created {out}")


@main.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--lang", "target_language", required=True)
@click.option("--deck", "deck_name", default=None)
@click.option("--no-images", is_flag=True)
@click.option("--no-audio", is_flag=True)
@click.option("--source-lang", "source_language", default=None)
def run(input_path: str, target_language: str, deck_name: str | None,
        no_images: bool, no_audio: bool, source_language: str | None):
    """Run full pipeline: ingest → enrich → media → export."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    src_lang = source_language or config.default_source_language
    path = Path(input_path)
    input_type = _detect_input_type(path)

    # Ingest
    click.echo(f"Step 1/4: Ingesting {path.name}...")
    if input_type == "excel":
        cards = ingest_excel(path, target_language, src_lang)
    elif input_type == "pdf":
        cards = ingest_pdf(path, target_language, config.deepseek_api_key, src_lang)
    elif input_type == "image":
        cards = ingest_image(path, target_language, config.deepseek_api_key, src_lang)

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    click.echo(f"  Extracted {len(cards)} cards. Total: {len(merged)}.")

    # Enrich
    click.echo("Step 2/4: Enriching cards with AI...")
    enriched = enrich_cards(merged, config.minimax_api_key, src_lang)
    state.save_cards(enriched)
    click.echo("  Enrichment complete.")

    # Media
    click.echo("Step 3/4: Generating media...")
    if not no_audio and config.media.audio_enabled:
        enriched = asyncio.run(generate_audio_batch(
            enriched, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))
    if not no_images and config.media.image_enabled:
        enriched = asyncio.run(generate_image_batch(
            enriched, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))

    updated = []
    for card in enriched:
        if card.status == "enriched":
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)
    state.save_cards(updated)
    click.echo("  Media complete.")

    # Export
    name = deck_name or config.export.default_deck_name
    out = Path(config.export.output_dir) / f"{name}.apkg"
    click.echo(f"Step 4/4: Exporting to {out}...")
    export_apkg(updated, out, name)
    click.echo(f"Done! Created {out} with {len(updated)} cards.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/test_cli.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/cli.py tests/test_cli.py
git commit -m "feat: add Click CLI with ingest, enrich, media, export, and run commands"
```

---

### Task 14: Integration Test — Full Pipeline

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
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
        # Mock enrich: add missing fields
        def fake_enrich(cards, api_key, src_lang):
            enriched = []
            for c in cards:
                enriched.append(c.model_copy(update={
                    "pronunciation": "/test/",
                    "example_sentence": "Test sentence! 🎉",
                    "sentence_translation": "Testsatz! 🎉",
                    "mnemonic": '<span style="color:red">test</span>',
                    "part_of_speech": "noun",
                    "status": "enriched",
                }))
            return enriched
        mock_enrich.side_effect = fake_enrich

        # Mock media: just return cards unchanged
        async def fake_audio(cards, media_dir, api_key, concurrency):
            return cards
        async def fake_image(cards, media_dir, api_key, concurrency):
            return cards
        mock_audio.side_effect = lambda *a, **kw: fake_audio(*a, **kw)
        mock_image.side_effect = lambda *a, **kw: fake_image(*a, **kw)

        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(
                main,
                ["run", "--input", "vocab.xlsx", "--lang", "en", "--deck", "TestDeck"],
                env={"MINIMAX_API_KEY": "test", "DEEPSEEK_API_KEY": "test"},
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

            # Verify cards.json
            cards_data = json.loads(Path(".anki-builder/cards.json").read_text())
            self.assertEqual(len(cards_data), 2)
            self.assertEqual(cards_data[0]["word"], "dog")
            self.assertEqual(cards_data[0]["part_of_speech"], "noun")
            self.assertIn("🎉", cards_data[0]["example_sentence"])

            # Verify .apkg
            apkg_path = Path("output/TestDeck.apkg")
            self.assertTrue(apkg_path.exists())
            self.assertTrue(zipfile.is_zipfile(apkg_path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run integration test**

```bash
uv run python -m pytest tests/test_integration.py -v
```

Expected: 1 test PASS

- [ ] **Step 3: Run full test suite**

```bash
uv run python -m pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: add integration test for full pipeline"
```

---

### Task 15: Final Cleanup & Verification

**Files:**
- Verify: all files from project structure exist
- Verify: all tests pass

- [ ] **Step 1: Verify project structure**

```bash
find src/anki_builder -name "*.py" | sort
```

Expected output:
```
src/anki_builder/__init__.py
src/anki_builder/cli.py
src/anki_builder/config.py
src/anki_builder/enrich/__init__.py
src/anki_builder/enrich/ai.py
src/anki_builder/enrich/vocabulary.py
src/anki_builder/export/__init__.py
src/anki_builder/export/apkg.py
src/anki_builder/export/merge.py
src/anki_builder/ingest/__init__.py
src/anki_builder/ingest/excel.py
src/anki_builder/ingest/image.py
src/anki_builder/ingest/pdf.py
src/anki_builder/media/__init__.py
src/anki_builder/media/audio.py
src/anki_builder/media/image.py
src/anki_builder/schema.py
src/anki_builder/state.py
```

- [ ] **Step 2: Run full test suite**

```bash
uv run python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 3: Test CLI entry point**

```bash
uv run anki-builder --help
```

Expected: Shows help with ingest, enrich, media, export, run commands

- [ ] **Step 4: Commit any remaining changes**

```bash
git add -A
git status
git commit -m "chore: final cleanup and verification"
```
