# Code Cleanup & Light Refactor — Design Spec

**Date:** 2026-04-24
**Scope:** Full cleanup of `src/anki_builder/` — bugs, consistency, deduplication, config improvements
**Off-limits:** `schema.py`, `ingest/prompt.md`

---

## 1. Bug Fixes & Error Handling

### 1.1 API Key Validation

Add validation methods to `Config`:

- `require_minimax_key()` — raises `click.ClickException` if `MINIMAX_API_KEY` is empty/unset
- `require_google_key()` — raises `click.ClickException` if `GOOGLE_API_KEY` is empty/unset

Call sites:
- `ingest` command: call `require_google_key()` when input type is `image` or `gdrive`; call `require_minimax_key()` when input type is `pdf` or `gdrive`
- `enrich` command: call `require_minimax_key()`
- `media` command: call `require_minimax_key()` if images enabled
- `run` command: same rules based on input type and media flags

### 1.2 Stale Media File Paths

In `media/audio.py` and `media/image.py`, change the skip-if-exists check:

**Before:** If `card.audio_file` is set (regardless of whether the file exists), skip generation.
**After:** If `card.audio_file` is set AND the file exists on disk, skip. Otherwise, regenerate.

Same logic for `card.image_file`.

### 1.3 Column-Map Parsing

In `cli.py`, wrap the `--column-map` parsing:

```python
try:
    col_map = dict(pair.split("=") for pair in column_map.split(","))
except ValueError:
    raise click.ClickException(
        "Invalid --column-map format. Expected key=value pairs separated by commas, "
        "e.g. --column-map word=Wort,translation=Übersetzung"
    )
```

### 1.4 PDF NotImplementedError

In `ingest/pdf.py`, replace the bare `NotImplementedError` with a `click.ClickException`:

```python
raise click.ClickException(
    "This PDF contains scanned images instead of selectable text. "
    "Image-based PDF ingestion is not yet supported."
)
```

---

## 2. Consistency Fixes

### 2.1 Replace `print()` with `click.echo()`

Files affected:
- `ingest/image.py` — all `print()` calls become `click.echo()`
- `media/image.py` — all `print()` calls become `click.echo()`

### 2.2 Shared Constants Module

Create `src/anki_builder/constants.py`:

```python
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"
MINIMAX_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
MINIMAX_IMAGE_MODEL = "image-01"
MAX_RETRIES = 3
```

Update imports:
- `enrich/ai.py` — remove local `MINIMAX_BASE_URL`, `MINIMAX_MODEL`; import from `constants`
- `enrich/vocabulary.py` — remove local constants; import from `constants`
- `media/image.py` — remove local `MINIMAX_IMAGE_URL`, `MINIMAX_IMAGE_MODEL`; import from `constants`
- `ingest/image.py` — remove local `MAX_RETRIES`; import from `constants`

### 2.3 Fix Typos

- `enrich/ai.py`: "serval emojis" → "several emojis"
- `media/image.py`: "ZEdRO text" → "ZERO text" in image prompt

### 2.4 Consistent API Key Access for Image Ingestion

Change `ingest_image()` signature to accept the API key as a parameter:

**Before:** `ingest_image(path, target_language, source_language)` — fetches key from `os.environ` internally
**After:** `ingest_image(path, target_language, source_language, google_api_key)` — receives key from caller

Update call sites in `cli.py` to pass `config.google_api_key`.

### 2.5 Remove Unnecessary `pass`

In `cli.py`, remove the `pass` statement from the `main()` click group function.

---

## 3. Deduplication & Light Refactoring

### 3.1 Extract Status Update Logic

Add to `state.py`:

```python
def finalize_card_status(cards: list[Card], no_images: bool = False, no_audio: bool = False) -> list[Card]:
```

Logic: for each card, if status is `"extracted"` or `"enriched"`, mark as `"complete"` if:
- Both `audio_file` and `image_file` are set, OR
- The missing media type was explicitly skipped (`no_images` / `no_audio`)

Replace the duplicated logic in `cli.py`'s `media` and `run` commands with calls to this function.

### 3.2 Consistent Retry Constants

Replace hardcoded `3` in `media/image.py` retry loop with `MAX_RETRIES` from `constants.py`. Keep sync (`time.sleep`) and async (`asyncio.sleep`) implementations separate, but both use exponential backoff: `2 ** attempt` seconds.

### 3.3 Remove Dead Code

`export/merge.py` contains `merge_and_export()` which is never called from production code. Delete the file. The `export/__init__.py` remains (empty package marker). Also remove the unused import of `merge_and_export` from `tests/test_merge.py` (the test only uses `StateManager.merge_cards()`).

### 3.4 Add Missing CLI Help Text

On the `run` command, add `help=` to:
- `--input`: `"Input file path or Google Drive folder URL"`
- `--words`: `"Comma-separated words (e.g. \"Glove,Squirrel,impossible\")"`
- `--source-lang`: `"Source language code (default: from config)"`
- `--deck`: `"Deck name for export"`

---

## 4. Configuration Improvements

### 4.1 Config YAML Error Handling

In `config.py`'s `load_config()`, catch `pydantic.ValidationError` and raise `click.ClickException` with a user-friendly message listing the invalid fields.

---

## 5. Test Updates

No new test files. Update existing tests where function signatures change:

- `test_ingest_image.py` — update calls to `ingest_image()` to pass `google_api_key` parameter
- `test_integration.py` — update if it calls `ingest_image()` directly
- Any test importing constants from `enrich/ai.py` or `media/image.py` — update imports to `constants`

---

## 6. Files Changed Summary

| File | Action |
|------|--------|
| `constants.py` (new) | Shared constants |
| `config.py` | Add key validation, config error handling |
| `cli.py` | API key checks, column-map error handling, status logic extraction, help text, remove `pass` |
| `state.py` | Add `finalize_card_status()` |
| `enrich/ai.py` | Import constants, fix typo |
| `enrich/vocabulary.py` | Import constants |
| `ingest/image.py` | Accept API key param, `print()` → `click.echo()`, import `MAX_RETRIES` |
| `ingest/pdf.py` | `NotImplementedError` → `ClickException` |
| `media/audio.py` | Fix stale file path check |
| `media/image.py` | Fix stale file path check, `print()` → `click.echo()`, import constants |
| `export/merge.py` | Delete (dead code) |
| `tests/test_ingest_image.py` | Update for new `ingest_image()` signature |
| `tests/test_merge.py` | Remove unused `merge_and_export` import |

**Not changed:** `schema.py`, `ingest/prompt.md`
