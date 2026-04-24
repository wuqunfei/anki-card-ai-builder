# Anki Card AI Builder

AI-powered Anki flashcard generator for language learning. Extracts vocabulary from various sources, enriches cards with AI (translations, pronunciations, example sentences, mnemonics, synonyms/antonyms), generates audio and images, and exports to `.apkg` for Anki.

## Features

- **Multiple input sources**: Excel/CSV, PDF, images (OCR via Google Gemini), Google Drive folders, or direct word input
- **AI enrichment**: Translations, IPA/Pinyin/Romaji pronunciation, grammatical gender, part of speech, example sentences, mnemonic word breakdowns, synonyms, and antonyms — powered by [MiniMax M2.5](https://www.minimax.io/)
- **Media generation**: Text-to-speech audio (gTTS) and AI-generated cartoon images (MiniMax image-01)
- **Anki export**: `.apkg` files with HTML card templates and embedded media
- **Incremental workflow**: Cards are merged across runs, so you can add words over time
- **HEIC/HEIF support**: Accepts iPhone photos directly for OCR ingestion

## Setup

Requires Python 3.12+.

```bash
# Install with uv
uv sync

# Copy and fill in your API keys
cp .env.example .env
```

### API Keys

| Key | Required for |
|-----|-------------|
| `MINIMAX_API_KEY` | AI enrichment (MiniMax M2.5) + image generation (MiniMax image-01) |
| `GOOGLE_API_KEY` | Image OCR (Google Gemini) + Google Drive folder ingestion |

## Usage

### Quick start with words

```bash
# Add words directly from command line
anki-builder run --words "Glove,Squirrel,impossible" --lang en

# Review your cards
anki-builder review

# Export to Anki
anki-builder export --deck "My-Vocabulary"
```

### From files

```bash
# From Excel/CSV
anki-builder run --input vocab.csv --lang en

# From PDF
anki-builder run --input textbook.pdf --lang en

# From image (OCR via Gemini — supports PNG, JPG, HEIC, WebP, etc.)
anki-builder run --input photo.png --lang en

# From Google Drive folder
anki-builder run --input "https://drive.google.com/drive/folders/..." --lang en
```

### Step-by-step pipeline

You can also run each step individually:

```bash
# 1. Ingest words
anki-builder ingest --words "Glove,Squirrel" --lang en
# or: anki-builder ingest --input vocab.xlsx --lang en

# 2. Enrich with AI
anki-builder enrich

# 3. Generate audio and images
anki-builder media

# 4. Review cards
anki-builder review

# 5. Export
anki-builder export --deck "German Vocabulary"
```

### Options

```bash
# Skip image or audio generation
anki-builder run --words "cat,dog" --lang en --no-images
anki-builder run --words "cat,dog" --lang en --no-audio

# Set source language (default: de/German)
anki-builder run --words "Hund,Katze" --lang en --source-lang de

# Custom deck name
anki-builder run --input vocab.xlsx --lang en --deck "Unit 5 Words"
```

## Project Structure

```
src/anki_builder/
├── cli.py              # Click CLI with commands: run, ingest, enrich, media, review, export
├── config.py           # YAML config + env var loading (Pydantic)
├── schema.py           # Card data model (Pydantic)
├── state.py            # JSON state persistence + card merging
├── ingest/
│   ├── excel.py        # Excel/CSV ingestion (openpyxl)
│   ├── pdf.py          # PDF text extraction (PyMuPDF)
│   ├── image.py        # Image OCR (Google Gemini)
│   └── gdrive.py       # Google Drive folder ingestion
├── enrich/
│   ├── ai.py           # AI enrichment (MiniMax M2.5 via Anthropic SDK)
│   └── vocabulary.py   # Vocabulary helpers
├── media/
│   ├── audio.py        # TTS audio generation (gTTS)
│   └── image.py        # AI image generation (MiniMax image-01)
└── export/
    ├── apkg.py         # Anki .apkg export (genanki)
    └── merge.py        # Card merge logic
```

## Configuration

Create `.anki-builder/config.yaml` to customize defaults:

```yaml
default_source_language: de
default_target_language: en
learner_profile: "ages 9-12, kid-friendly with emojis"
media:
  audio_enabled: true
  image_enabled: true
  concurrency: 5
export:
  default_deck_name: Vocabulary
  output_dir: ./output
```

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest
```
