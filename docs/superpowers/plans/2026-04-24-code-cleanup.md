# Code Cleanup & Light Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix bugs, improve consistency, deduplicate logic, and improve error handling across the anki-builder codebase without changing `schema.py` or `ingest/prompt.md`.

**Architecture:** No structural changes. Extract shared constants into a new `constants.py` module, move duplicated status-update logic into `state.py`, and improve error messages throughout the CLI. All existing module boundaries remain the same.

**Tech Stack:** Python 3.12+, Click, Pydantic, gTTS, httpx, anthropic SDK, google-genai

---

### Task 1: Create shared constants module

**Files:**
- Create: `src/anki_builder/constants.py`

- [ ] **Step 1: Create the constants module**

```python
# src/anki_builder/constants.py
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"
MINIMAX_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
MINIMAX_IMAGE_MODEL = "image-01"
MAX_RETRIES = 3
```

- [ ] **Step 2: Verify the module imports correctly**

Run: `uv run python -c "from anki_builder.constants import MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_IMAGE_URL, MINIMAX_IMAGE_MODEL, MAX_RETRIES; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/anki_builder/constants.py
git commit -m "refactor: add shared constants module"
```

---

### Task 2: Update enrich modules to use shared constants

**Files:**
- Modify: `src/anki_builder/enrich/ai.py:16-17` (remove local constants, import from constants, fix typo)
- Modify: `src/anki_builder/enrich/vocabulary.py:6-7` (remove local constants, import from constants)

- [ ] **Step 1: Update `enrich/ai.py`**

Replace lines 16-17:
```python
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"
```

With:
```python
from anki_builder.constants import MINIMAX_BASE_URL, MINIMAX_MODEL
```

Also fix the typo on line 42 — change `"serval emojis"` to `"several emojis"`.

- [ ] **Step 2: Update `enrich/vocabulary.py`**

Replace lines 6-7:
```python
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"
```

With:
```python
from anki_builder.constants import MINIMAX_BASE_URL, MINIMAX_MODEL
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

Run: `uv run pytest tests/test_enrich_ai.py tests/test_vocabulary.py -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/anki_builder/enrich/ai.py src/anki_builder/enrich/vocabulary.py
git commit -m "refactor: use shared constants in enrich modules, fix typo"
```

---

### Task 3: Update media/image.py — constants, typo, print→click.echo

**Files:**
- Modify: `src/anki_builder/media/image.py`

- [ ] **Step 1: Update imports and remove local constants**

Replace lines 1-10:
```python
import asyncio
import base64
from pathlib import Path

import httpx

from anki_builder.schema import Card

MINIMAX_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
MINIMAX_IMAGE_MODEL = "image-01"
```

With:
```python
import asyncio
import base64
from pathlib import Path

import click
import httpx

from anki_builder.constants import MAX_RETRIES, MINIMAX_IMAGE_MODEL, MINIMAX_IMAGE_URL
from anki_builder.schema import Card
```

- [ ] **Step 2: Fix the "ZEdRO" typo in `_build_image_prompt`**

On line 17, change `"ZEdRO text"` to `"ZERO text"`.

- [ ] **Step 3: Use `MAX_RETRIES` constant in retry loop**

Replace line 45:
```python
    for attempt in range(3):
```

With:
```python
    for attempt in range(MAX_RETRIES):
```

Also replace line 59:
```python
        if attempt < 2:
```

With:
```python
        if attempt < MAX_RETRIES - 1:
```

- [ ] **Step 4: Replace `print()` with `click.echo()`**

Replace line 62:
```python
    print(f"Warning: image generation failed for '{card.source_word}', skipping.")
```

With:
```python
    click.echo(f"Warning: image generation failed for '{card.source_word}', skipping.")
```

- [ ] **Step 5: Run existing tests**

Run: `uv run pytest tests/ -v -k "image" --ignore=tests/input`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/anki_builder/media/image.py
git commit -m "refactor: use shared constants in media/image, fix typo, use click.echo"
```

---

### Task 4: Update ingest/image.py — API key param, print→click.echo, import constants

**Files:**
- Modify: `src/anki_builder/ingest/image.py`
- Modify: `tests/test_ingest_image.py`

- [ ] **Step 1: Update `ingest_image()` to accept API key as parameter**

In `src/anki_builder/ingest/image.py`, change the imports — add `click`, import `MAX_RETRIES` from constants, remove the local `MAX_RETRIES`:

Replace lines 1-16:
```python
import json
import re
import time
from pathlib import Path

import PIL.Image
import pillow_heif
from google import genai
from google.genai import types
from google.genai.errors import ClientError

pillow_heif.register_heif_opener()

from anki_builder.schema import Card

MAX_RETRIES = 3
```

With:
```python
import json
import re
import time
from pathlib import Path

import click
import PIL.Image
import pillow_heif
from google import genai
from google.genai import types
from google.genai.errors import ClientError

pillow_heif.register_heif_opener()

from anki_builder.constants import MAX_RETRIES
from anki_builder.schema import Card
```

- [ ] **Step 2: Change `ingest_image` signature and remove internal `os.environ` access**

Replace lines 25-28:
```python
def ingest_image(path: Path, target_language: str, source_language: str = "de") -> list[Card]:
    import os
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=google_api_key)
```

With:
```python
def ingest_image(path: Path, target_language: str, source_language: str = "de", google_api_key: str = "") -> list[Card]:
    client = genai.Client(api_key=google_api_key)
```

- [ ] **Step 3: Replace `print()` with `click.echo()`**

Replace line 47:
```python
                print(f"Rate limited, waiting {wait:.0f}s...")
```

With:
```python
                click.echo(f"Rate limited, waiting {wait:.0f}s...")
```

- [ ] **Step 4: Update tests for new signature**

In `tests/test_ingest_image.py`, update all calls to `ingest_image` to pass `google_api_key`:

Line 71 — change:
```python
        cards = ingest_image(Path("test.png"), target_language="fr", source_language="de")
```
To:
```python
        cards = ingest_image(Path("test.png"), target_language="fr", source_language="de", google_api_key="test-key")
```

Line 96 — change:
```python
        cards = ingest_image(Path("test.jpg"), target_language="fr")
```
To:
```python
        cards = ingest_image(Path("test.jpg"), target_language="fr", google_api_key="test-key")
```

Line 107 — change:
```python
        cards = ingest_image(Path("test.png"), target_language="zh", source_language="en")
```
To:
```python
        cards = ingest_image(Path("test.png"), target_language="zh", source_language="en", google_api_key="test-key")
```

Line 123 — change:
```python
            ingest_image(Path("test.png"), target_language="fr")
```
To:
```python
            ingest_image(Path("test.png"), target_language="fr", google_api_key="test-key")
```

For the `TestIngestImageReal` class (line 140-144), change:
```python
            cards = ingest_image(
                path=image_path,
                target_language=target_language,
                source_language="de",
            )
```
To:
```python
            cards = ingest_image(
                path=image_path,
                target_language=target_language,
                source_language="de",
                google_api_key=os.environ.get("GOOGLE_API_KEY", ""),
            )
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_ingest_image.py -v`
Expected: All unit tests pass (integration tests skipped if no API key).

- [ ] **Step 6: Commit**

```bash
git add src/anki_builder/ingest/image.py tests/test_ingest_image.py
git commit -m "refactor: pass google_api_key to ingest_image, use click.echo and shared constants"
```

---

### Task 5: Update ingest/pdf.py — ClickException instead of NotImplementedError

**Files:**
- Modify: `src/anki_builder/ingest/pdf.py:1,27-30`

- [ ] **Step 1: Add click import and replace the error**

Add `import click` at line 2 (after `from pathlib import Path`).

Replace lines 27-30:
```python
        raise NotImplementedError(
            "Image-based PDF ingestion is not yet available. "
            "Google Gemini OCR support is planned for a future release."
        )
```

With:
```python
        raise click.ClickException(
            "This PDF contains scanned images instead of selectable text. "
            "Image-based PDF ingestion is not yet supported."
        )
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_ingest_pdf.py -v`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/anki_builder/ingest/pdf.py
git commit -m "fix: raise ClickException for image-based PDFs instead of NotImplementedError"
```

---

### Task 6: Add API key validation to config.py

**Files:**
- Modify: `src/anki_builder/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Add validation methods and config error handling**

In `src/anki_builder/config.py`, add `import click` and `from pydantic import ValidationError` at the top.

Add two methods to the `Config` class after the `google_api_key` property:

```python
    def require_minimax_key(self) -> None:
        if not self.minimax_api_key:
            raise click.ClickException(
                "MINIMAX_API_KEY is required but not set. "
                "Add it to your .env file or set the environment variable."
            )

    def require_google_key(self) -> None:
        if not self.google_api_key:
            raise click.ClickException(
                "GOOGLE_API_KEY is required but not set. "
                "Add it to your .env file or set the environment variable."
            )
```

Update `load_config` to catch Pydantic validation errors:

Replace:
```python
def load_config(work_dir: Path) -> Config:
    config_path = work_dir / "config.yaml"
    if not config_path.exists():
        return Config()
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return Config(**data)
```

With:
```python
def load_config(work_dir: Path) -> Config:
    config_path = work_dir / "config.yaml"
    if not config_path.exists():
        return Config()
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    try:
        return Config(**data)
    except ValidationError as e:
        errors = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in e.errors())
        raise click.ClickException(f"Invalid config.yaml: {errors}")
```

- [ ] **Step 2: Run existing config tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/anki_builder/config.py
git commit -m "feat: add API key validation and config YAML error handling"
```

---

### Task 7: Extract finalize_card_status to state.py

**Files:**
- Modify: `src/anki_builder/state.py`

- [ ] **Step 1: Add `finalize_card_status` function**

Add this function at the end of `src/anki_builder/state.py`:

```python
def finalize_card_status(
    cards: list[Card], no_images: bool = False, no_audio: bool = False
) -> list[Card]:
    updated = []
    for card in cards:
        if card.status in ("extracted", "enriched") and card.audio_file and card.image_file:
            updated.append(card.model_copy(update={"status": "complete"}))
        elif card.status in ("extracted", "enriched") and (no_images or no_audio):
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)
    return updated
```

- [ ] **Step 2: Verify import works**

Run: `uv run python -c "from anki_builder.state import finalize_card_status; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/anki_builder/state.py
git commit -m "refactor: extract finalize_card_status to state module"
```

---

### Task 8: Update cli.py — all remaining changes

**Files:**
- Modify: `src/anki_builder/cli.py`

This task applies all remaining CLI changes: API key validation calls, column-map error handling, `finalize_card_status` usage, help text, `pass` removal, and passing `google_api_key` to `ingest_image`.

- [ ] **Step 1: Update imports**

Replace line 8:
```python
from anki_builder.state import StateManager
```

With:
```python
from anki_builder.state import StateManager, finalize_card_status
```

- [ ] **Step 2: Remove `pass` from `main()`**

Replace lines 46-48:
```python
def main():
    """anki-builder: Anki Card AI Builder — generate flashcards for language learning."""
    pass
```

With:
```python
def main():
    """anki-builder: Anki Card AI Builder — generate flashcards for language learning."""
```

- [ ] **Step 3: Add column-map error handling and API key validation in `ingest` command**

In the `ingest` function, replace lines 73-75:
```python
        col_map = None
        if column_map:
            col_map = dict(pair.split("=") for pair in column_map.split(","))
```

With:
```python
        col_map = None
        if column_map:
            try:
                col_map = dict(pair.split("=") for pair in column_map.split(","))
            except ValueError:
                raise click.ClickException(
                    "Invalid --column-map format. Expected key=value pairs separated by commas, "
                    'e.g. --column-map word=Wort,translation=Übersetzung'
                )
```

After `click.echo(f"Ingesting {input_path} as {input_type}...")` (line 77), add API key validation:

```python
        if input_type in ("image", "gdrive"):
            config.require_google_key()
        if input_type in ("pdf", "gdrive"):
            config.require_minimax_key()
```

- [ ] **Step 4: Pass `google_api_key` to `ingest_image` in `ingest` command**

Replace line 89:
```python
            cards = ingest_image(path, target_language, src_lang)
```

With:
```python
            cards = ingest_image(path, target_language, src_lang, config.google_api_key)
```

- [ ] **Step 5: Add API key validation in `enrich` command**

After `config = load_config(WORK_DIR)` in the `enrich` function (line 100), add:

```python
    config.require_minimax_key()
```

- [ ] **Step 6: Add API key validation in `media` command**

After `config = load_config(WORK_DIR)` in the `media` function (line 122), add:

```python
    if not no_images and config.media.image_enabled:
        config.require_minimax_key()
```

- [ ] **Step 7: Replace status update logic in `media` command with `finalize_card_status`**

Replace lines 140-148:
```python
    # Update status to complete for cards that have media
    updated = []
    for card in cards:
        if card.status in ("extracted", "enriched") and card.audio_file and card.image_file:
            updated.append(card.model_copy(update={"status": "complete"}))
        elif card.status in ("extracted", "enriched") and (no_images or no_audio):
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)

    state.save_cards(updated)
```

With:
```python
    updated = finalize_card_status(cards, no_images, no_audio)
    state.save_cards(updated)
```

- [ ] **Step 8: Add help text and API key validation in `run` command**

Replace lines 200-206:
```python
@click.option("--input", "input_path", default=None, type=str)
@click.option("--words", "words", default=None, type=str, help="Comma-separated words")
@click.option("--lang", "target_language", required=True)
@click.option("--deck", "deck_name", default=None)
@click.option("--no-images", is_flag=True)
@click.option("--no-audio", is_flag=True)
@click.option("--source-lang", "source_language", default=None)
```

With:
```python
@click.option("--input", "input_path", default=None, type=str, help="Input file path or Google Drive folder URL")
@click.option("--words", "words", default=None, type=str, help='Comma-separated words (e.g. "Glove,Squirrel,impossible")')
@click.option("--lang", "target_language", required=True, help="Target language code (en, fr, zh)")
@click.option("--deck", "deck_name", default=None, help="Deck name for export")
@click.option("--no-images", is_flag=True, help="Skip image generation")
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
@click.option("--source-lang", "source_language", default=None, help="Source language code (default: from config)")
```

- [ ] **Step 9: Add API key validation in `run` command**

After `src_lang = source_language or config.default_source_language` (line 217), before the ingest block, add validation:

```python
    config.require_minimax_key()
    if not words:
        input_type = _detect_input_type(input_path)
        if input_type in ("image", "gdrive"):
            config.require_google_key()
```

Note: Since `run` always calls `enrich`, `MINIMAX_API_KEY` is always required. We need to detect input type early for google key validation but still use it later. Restructure the run command's ingest section slightly:

Actually, looking at the existing code, `_detect_input_type` is already called inside the `else` block (line 224). To avoid calling it twice, add validation after `_detect_input_type` is called. Replace lines 219-236:

```python
    # Ingest
    if words:
        cards = _words_to_cards(words, target_language, src_lang)
        click.echo(f"Step 1/4: Ingesting {len(cards)} words from command line...")
    else:
        input_type = _detect_input_type(input_path)
        click.echo(f"Step 1/4: Ingesting {input_path}...")
        if input_type == "gdrive":
            cards = ingest_gdrive_folder(input_path, target_language, config.google_api_key, config.minimax_api_key, src_lang)
        elif input_type == "excel":
            path = Path(input_path)
            cards = ingest_excel(path, target_language, src_lang)
        elif input_type == "pdf":
            path = Path(input_path)
            cards = ingest_pdf(path, target_language, config.minimax_api_key, src_lang)
        elif input_type == "image":
            path = Path(input_path)
            cards = ingest_image(path, target_language, src_lang)
```

With:
```python
    # Validate API keys
    config.require_minimax_key()

    # Ingest
    if words:
        cards = _words_to_cards(words, target_language, src_lang)
        click.echo(f"Step 1/4: Ingesting {len(cards)} words from command line...")
    else:
        input_type = _detect_input_type(input_path)
        if input_type in ("image", "gdrive"):
            config.require_google_key()
        click.echo(f"Step 1/4: Ingesting {input_path}...")
        if input_type == "gdrive":
            cards = ingest_gdrive_folder(input_path, target_language, config.google_api_key, config.minimax_api_key, src_lang)
        elif input_type == "excel":
            path = Path(input_path)
            cards = ingest_excel(path, target_language, src_lang)
        elif input_type == "pdf":
            path = Path(input_path)
            cards = ingest_pdf(path, target_language, config.minimax_api_key, src_lang)
        elif input_type == "image":
            path = Path(input_path)
            cards = ingest_image(path, target_language, src_lang, config.google_api_key)
```

- [ ] **Step 10: Replace status update logic in `run` command with `finalize_card_status`**

Replace lines 257-263:
```python
    updated = []
    for card in enriched:
        if card.status == "enriched":
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)
    state.save_cards(updated)
```

With:
```python
    updated = finalize_card_status(enriched, no_images, no_audio)
    state.save_cards(updated)
```

- [ ] **Step 11: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 12: Commit**

```bash
git add src/anki_builder/cli.py
git commit -m "refactor: add API key validation, error handling, dedup status logic in CLI"
```

---

### Task 9: Remove dead code — export/merge.py

**Files:**
- Delete: `src/anki_builder/export/merge.py`
- Modify: `tests/test_merge.py:7` (remove unused import)

- [ ] **Step 1: Remove the unused import from test_merge.py**

In `tests/test_merge.py`, delete line 7:
```python
from anki_builder.export.merge import merge_and_export
```

- [ ] **Step 2: Delete export/merge.py**

```bash
rm src/anki_builder/export/merge.py
```

- [ ] **Step 3: Run tests to verify nothing broke**

Run: `uv run pytest tests/test_merge.py -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add -u src/anki_builder/export/merge.py tests/test_merge.py
git commit -m "refactor: remove unused merge_and_export function"
```

---

### Task 10: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Verify CLI help output**

Run: `uv run anki-builder --help`
Expected: Shows all commands.

Run: `uv run anki-builder run --help`
Expected: All options have help text.

- [ ] **Step 3: Verify API key validation works**

Run: `uv run anki-builder enrich`
Expected: Error message about MINIMAX_API_KEY not set (not a Python traceback).

- [ ] **Step 4: No commit needed — this is verification only**
