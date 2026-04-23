# Anki Card AI Builder

AI-powered Anki flashcard generator for language learning. Extracts vocabulary from various sources, enriches cards with AI (translations, pronunciations, example sentences, mnemonics), generates audio and images, and exports to `.apkg` for Anki.

## Features

- **Multiple input sources**: Excel/CSV, PDF, images (OCR), Google Drive folders, or direct word input
- **AI enrichment**: Translations, IPA pronunciation, kid-friendly example sentences, mnemonic word breakdowns
- **Media generation**: Text-to-speech audio (gTTS) and AI-generated images (MiniMax)
- **Anki export**: `.apkg` files with HTML card templates and embedded media
- **Incremental workflow**: Cards are merged across runs, so you can add words over time

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
| `MINIMAX_API_KEY` | AI enrichment + image generation |
| `GOOGLE_API_KEY` | Google Drive folder ingestion |

OCR is handled locally by [PaddleOCR-VL-1.5](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5) — no API key needed.

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

# From image (OCR)
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
