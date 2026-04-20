# Anki Card AI Builder — Design Spec

## Overview

A Python CLI tool that generates Anki flashcards for language learning. It ingests vocabulary from multiple sources (Excel, PDF, images), enriches missing fields with AI, generates audio and images, and exports `.apkg` packages compatible with any Anki client.

**Default learner profile:** German native speaker learning English, French, and Chinese. Configurable per deck.

**Target audience for card content:** Kids aged 9-12 — simple natural sentences with emojis.

## Architecture: Stage-Based Pipeline with Local State

Each stage writes intermediate results to a local `.anki-builder/` directory. Stages can be re-run independently without redoing prior work.

```
input/vocab.xlsx
  → .anki-builder/cards.json        (extracted + enriched cards)
  → .anki-builder/media/             (audio + images)
  → output/my-deck.apkg
```

### API Providers

| Task                              | Provider              |
|-----------------------------------|-----------------------|
| PDF text extraction               | pymupdf (local, free) |
| OCR (images, scanned PDFs)        | DeepSeek vision       |
| AI enrichment (translations, etc.)| MiniMax text          |
| Audio generation                  | MiniMax T2A async     |
| Image generation                  | MiniMax image         |

## Project Structure

```
anki-card-ai-builder/
├── src/anki_builder/
│   ├── __init__.py
│   ├── cli.py              # Click-based CLI entry point
│   ├── config.py            # Language configs, API keys, defaults
│   ├── schema.py            # Card schema definition
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── excel.py         # Excel/CSV ingestion (openpyxl)
│   │   ├── pdf.py           # PDF text extraction (pymupdf)
│   │   └── image.py         # Image OCR (DeepSeek vision)
│   ├── enrich/
│   │   ├── __init__.py
│   │   ├── ai.py            # AI enrichment via MiniMax text API
│   │   └── vocabulary.py    # Word extraction from raw text
│   ├── media/
│   │   ├── __init__.py
│   │   ├── audio.py         # TTS via MiniMax T2A async API
│   │   └── image.py         # Image generation via MiniMax image API
│   ├── export/
│   │   ├── __init__.py
│   │   ├── apkg.py          # .apkg export (genanki)
│   │   └── merge.py         # Merge/update existing decks
│   └── state.py             # cards.json read/write + diffing
├── tests/
├── pyproject.toml
└── .anki-builder/           # Working directory (created per project)
    ├── config.yaml
    ├── cards.json
    └── media/
```

## Card Schema

```python
@dataclass
class Card:
    id: str                  # UUID, stable across updates
    word: str
    target_language: str     # "en", "fr", "zh"
    native_language: str     # "de" (default)
    translation: str | None
    pronunciation: str | None  # IPA for en/fr, pinyin for zh
    example_sentence: str | None  # Kid-friendly with emojis
    sentence_translation: str | None
    part_of_speech: str | None
    tags: list[str]
    audio_file: str | None   # Path in media/
    image_file: str | None   # Path in media/
    source: str              # Where this card came from
    status: str              # "extracted", "enriched", "complete"
```

## Ingestion

Three input handlers, all producing `list[Card]` with partial fields.

### Excel ingestion
- Reads `.xlsx` / `.csv` using `openpyxl` / `csv`
- Auto-maps columns by header name (fuzzy matching: "Wort" -> `word`, "Ubersetzung" -> `translation`)
- User can specify column mapping via CLI flags
- Unmapped columns get added as tags

### PDF ingestion
- Uses `pymupdf` to extract selectable text
- If text extraction yields no content (scanned PDF), falls back to sending pages as images to DeepSeek vision API for OCR
- Extracted raw text goes through vocabulary extraction

### Image ingestion
- Sends image to DeepSeek vision API for OCR
- Extracted text goes through vocabulary extraction
- Supports photos of textbook pages, whiteboards, word lists

### Vocabulary extraction (shared by PDF and image)
- Sends raw text + target language + learner level to MiniMax text API
- AI identifies individual words/phrases worth learning
- Each word becomes a partial card with `word` and `source` filled in

## AI Enrichment

Takes partial cards and fills missing fields using MiniMax text generation API.

### Behavior
- Batches cards (up to ~20 per API call)
- Sends structured prompt with card schema, target language, native language, and learner profile
- Returns structured JSON

### Field generation rules
| Field                  | Rule                                          |
|------------------------|-----------------------------------------------|
| `translation`          | Generate only if missing from source          |
| `pronunciation`        | Generate only if missing from source          |
| `example_sentence`     | Generate only if missing from source          |
| `sentence_translation` | Generate only if missing from source          |
| `part_of_speech`       | Always generate (AI classifies for consistency)|

### Prompt strategy
- System prompt: "You are a friendly language tutor for German-speaking kids aged 9-12"
- Includes examples of good output (emoji usage, sentence complexity)
- Requests structured JSON output
- Language-specific instructions (e.g., Chinese: always include pinyin with tone marks)

### Cost control
- Only enriches fields that are actually missing
- Caches results in `cards.json` — re-runs skip already-enriched cards
- Card `status` tracks progress: `extracted` -> `enriched` -> `complete`

## Media Generation

### Audio (TTS)
- MiniMax T2A (Text-to-Audio) async API
- Generates one audio file per card: pronunciation of `word` in target language
- Saves to `.anki-builder/media/{card_id}_audio.mp3`
- Skips if audio file already exists (resumable)

### Image generation
- MiniMax image generation API
- Prompt: "Simple, colorful illustration of [word] suitable for children aged 9-12. Friendly cartoon style, no text."
- Saves to `.anki-builder/media/{card_id}_image.png`
- Skips if image already exists
- Can be disabled via CLI flag (`--no-images`)

### Parallelism
- Uses `asyncio` for concurrent API requests
- Configurable concurrency limit (default: 5)

## Export & Merge

### Fresh export
- Uses `genanki` library to build `.apkg` files
- Card template with HTML/CSS styling:
  - **Front:** word + audio play button + image
  - **Back:** translation, pronunciation, example sentence (with emojis), sentence translation, part of speech
- Embeds all media files into the `.apkg` package
- Output path configurable, defaults to `output/<deck-name>.apkg`

### Merge/update
- Each card has a stable UUID — used as `genanki` note GUID
- On re-run:
  1. Loads existing `cards.json`
  2. Diffs against new extraction (match by `word` + `target_language`)
  3. New words -> new cards
  4. Existing words with changes -> update fields, preserve `id`
  5. Words removed from source -> kept by default (`--prune` flag to remove)
- Anki's import overwrites matching note GUIDs automatically

## CLI Interface

```
anki-builder ingest --input vocab.xlsx --lang en    # Extract cards
anki-builder enrich                                  # Fill missing fields via AI
anki-builder media                                   # Generate audio + images
anki-builder export --deck "English B2"              # Build .apkg
anki-builder run --input vocab.xlsx --lang en        # All steps in one go
```

## Configuration

Stored in `.anki-builder/config.yaml`:

```yaml
native_language: de
default_target_language: en
learner_profile: "ages 9-12, kid-friendly with emojis"

api_keys:
  minimax: ${MINIMAX_API_KEY}      # env var reference
  deepseek: ${DEEPSEEK_API_KEY}

media:
  audio_enabled: true
  image_enabled: true
  concurrency: 5

export:
  default_deck_name: "Vocabulary"
  output_dir: ./output
```

API keys loaded from environment variables, never stored in the config file directly.

## Key Dependencies

- `click` — CLI framework
- `openpyxl` — Excel reading
- `pymupdf` — PDF text extraction
- `genanki` — Anki package generation
- `httpx` — Async HTTP client for API calls
- `pydantic` — Data validation for card schema
- `pyyaml` — Config file parsing
