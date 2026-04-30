# Anki Card AI Builder

Turn any vocabulary source into rich, multimedia Anki flashcards — powered by AI.

## Why We Need It

Creating good Anki flashcards for language learning takes a lot of manual work. You need translations, pronunciations, example sentences, and ideally images and audio on every card. Adding etymology, mnemonics, and memory hooks makes cards far more effective — but doing all that by hand is painfully slow.

Anki Card AI Builder automates the entire process. Give it a word list, spreadsheet, PDF, or even a photo — and it generates complete, media-rich flashcards ready to import into Anki.

- **AI enrichment** — translations, IPA/Pinyin/Romaji pronunciation, example sentences, synonyms, antonyms, and mnemonics
- **Color-coded etymology** — morpheme breakdown (prefix / root / suffix), origin chains to Proto-Indo-European roots, cross-language cognates (EN/DE/FR/Latin), and memory hooks
- **Multimedia** — text-to-speech audio and AI-generated cartoon images on every card
- **Flexible inputs** — word lists, Excel/CSV, PDF, image OCR (including iPhone HEIC photos), folders, and Google Drive
- **Personalization** — configurable learner profile (e.g. `"ages 9-12, kid-friendly with emojis"`) tailors card content, examples, and tone to the learner
- **One command** — from input to `.apkg` file, ready to import into Anki

## How It Works

```mermaid
flowchart LR
    A["1. Ingest<br/>Extract words from<br/>files, images, or CLI"] --> B["2. Enrich<br/>AI fills translations,<br/>pronunciation, examples"]
    B --> C["3. Media<br/>Generate audio (TTS)<br/>and cartoon images"]
    C --> D["4. Export<br/>Package into<br/>.apkg file"]
    D --> E["Import into<br/>Anki app"]
```

| Step | What happens | Output |
|------|-------------|--------|
| **Ingest** | Extracts vocabulary from your input (words, Excel, PDF, image OCR, Google Drive) | `cards.json` with raw word list |
| **Enrich** | AI adds translations, IPA pronunciation, etymology, mnemonics, example sentences | `cards.json` with full card data |
| **Media** | Generates TTS audio for words and example sentences, plus cartoon images | `media/*.mp3` and `media/*.png` |
| **Export** | Bundles cards + media into an Anki-compatible package | `.apkg` file ready to import |

The `run` command executes steps 1–3 automatically. Then use `export` to create the `.apkg` file and import it into Anki.

## Core Features

### Input Sources

- **Word list** — comma-separated via `--words "cat,dog,run"`
- **Excel/CSV** — `.xlsx` and `.csv` with fuzzy header mapping
- **PDF** — text-based PDFs (via PyMuPDF + MiniMax)
- **Image OCR** — `.png`, `.jpg`, `.heic`, `.heif`, `.webp`, `.bmp`, `.tiff` (via Google Gemini)
- **Folder** — processes all supported images and PDFs in a directory
- **Google Drive** — downloads and processes all files from a Drive folder URL

### AI Enrichment

- Translations, IPA/Pinyin/Romaji pronunciation, grammatical gender, part of speech
- Example sentences with translations
- Synonyms and antonyms

### Etymology & Mnemonics

- Color-coded morpheme breakdown — prefix (blue), root (coral), suffix (green)
- Origin chain tracing to Proto-Indo-European roots
- Cross-language cognates across EN/DE/FR/Latin
- Memory hooks that reference morpheme meanings

### Media Generation

- Text-to-speech audio for words and example sentences (gTTS)
- AI-generated cartoon images (MiniMax image-01 or Google Gemini)

### Personalization

- Configurable learner profile via `LEARNER_PROFILE` environment variable
- Example: `"ages 9-12, kid-friendly with emojis"` produces age-appropriate examples and tone

### Export & Card Types

| Type | Flag | Front | Back |
|------|------|-------|------|
| **Basic** | (default) | Target word + pronunciation + image + audio | Source word + mnemonic + etymology + example sentences |
| **Type-in** | `--typing` | Source word + image + audio + text input | Checks typed answer + shows full card details |

- `.apkg` export with HTML card templates and embedded media
- Workspace isolation — each run gets its own `workspace/<uuid>` folder
- Incremental merging — re-running with the same workspace adds new words and preserves existing data

### Supported Languages

| Language | Code | TTS | Tested |
|----------|------|-----|--------|
| English | `en` | gTTS | Yes |
| French | `fr` | gTTS | Yes |
| German | `de` | gTTS | Yes |
| Chinese | `zh` | gTTS (zh-CN) | No |
| Japanese | `ja` | — | No |
| Korean | `ko` | — | No |
| Spanish | `es` | — | No |
| Italian | `it` | — | No |
| Portuguese | `pt` | — | No |
| Russian | `ru` | — | No |
| Arabic | `ar` | — | No |

## What You Got before

<p align="center">
  <img src="docs/before.png" alt="Old Card" width="400">
</p>



## What You Get After

<p align="center">
  <img src="docs/after.png" alt="New Card" width="400">
</p>

An example card in Anki showing: AI-generated cartoon image, IPA pronunciation, color-coded morpheme breakdown (con- + centr + -ate), origin chain, cognates across languages, memory hook, and an example sentence with translation.

## Get Started

### Prerequisites

- Python 3.12+
- [Anki desktop app](https://apps.ankiweb.net/) or [AnkiMobile](https://apps.apple.com/app/ankimobile-flashcards/id373493387) / [AnkiDroid](https://play.google.com/store/apps/details?id=com.ichi2.anki) for importing `.apkg` files

### Installation

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
| `GOOGLE_API_KEY` | Image OCR (Google Gemini) + Google Drive folder ingestion + Gemini image generation |

### Language Flags

- **`--lang-target`** (required): The language you are **learning**. Appears on the front of the card.
- **`--lang-source`** (optional, default: `de`): Your **native language**. Shown on the back for reference.

Example: if you speak German and are learning English: `--lang-target en --lang-source de`

### Usage

#### Full pipeline (recommended)

```bash
# From word list — creates a new workspace automatically
ankids run --words "Glove,Squirrel,impossible" --lang-target en

# From Excel/CSV
ankids run --input vocab.xlsx --lang-target en

# From PDF
ankids run --input textbook.pdf --lang-target en

# From image (OCR — supports PNG, JPG, HEIC, WebP, etc.)
ankids run --input photo.heic --lang-target en

# From a folder of images/PDFs
ankids run --input ./my-scans/ --lang-target en

# From Google Drive folder
ankids run --input "https://drive.google.com/drive/folders/..." --lang-target en
```

The `run` command prints the workspace path. Use `--output` to continue in an existing workspace:

```bash
# Add more words to an existing workspace
ankids run --words "more,words" --lang-target en --output workspace/a1b2c3d4
```

#### Step-by-step pipeline

Run each step individually, passing the workspace folder with `--output`:

```bash
# 1. Ingest words (creates workspace/a1b2c3d4/)
ankids ingest --words "Glove,Squirrel" --lang-target en

# 2. Enrich with AI
ankids enrich --output workspace/a1b2c3d4

# 3. Generate audio and images
ankids media --output workspace/a1b2c3d4

# 4. Review cards
ankids review --output workspace/a1b2c3d4

# 5. Export to .apkg
ankids export --output workspace/a1b2c3d4 --deck "English Vocabulary"
```

#### Options

```bash
# Skip image or audio generation
ankids run --words "cat,dog" --lang-target en --no-images
ankids run --words "cat,dog" --lang-target en --no-audio

# Create "type the answer" cards (spelling practice)
ankids run --words "cat,dog" --lang-target en --typing

# Custom deck name
ankids run --input vocab.xlsx --lang-target en --deck "Unit 5 Words"

# Custom .apkg output path
ankids export --output workspace/a1b2c3d4 --deck "Test" --apkg ./my-deck.apkg

# Clean up a workspace
ankids clean --output workspace/a1b2c3d4
```

### CLI Reference

| Command | Description | `--output` |
|---------|-------------|------------|
| `run` | Full pipeline: ingest + enrich + media + review | Optional (auto-creates) |
| `ingest` | Extract vocabulary from input | Optional (auto-creates) |
| `enrich` | Fill missing fields with AI | Required |
| `media` | Generate TTS audio and AI images | Required |
| `review` | Show cards and media status | Required |
| `export` | Export to `.apkg` file | Required |
| `clean` | Delete a workspace folder | Required |

### Configuration

Environment variables (via `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIMAX_API_KEY` | — | Required for AI enrichment and MiniMax image generation |
| `GOOGLE_API_KEY` | — | Required for OCR, Google Drive, and Gemini image generation |
| `LEARNER_PROFILE` | `"ages 9-12, kid-friendly with emojis"` | Learner context for AI enrichment |
| `MEDIA_AUDIO_ENABLED` | `true` | Enable/disable audio generation |
| `MEDIA_IMAGE_ENABLED` | `true` | Enable/disable image generation |
| `MEDIA_CONCURRENCY` | `3` | Max concurrent image generation requests |
| `IMAGE_PROVIDER` | `minimax` | Image provider: `minimax` or `gemini` |
| `EXPORT_DECK_NAME` | `Vocabulary` | Default deck name for export |

## Current Status & Roadmap

### Status

Working MVP — usable but still evolving.

- **Tested languages:** English, French, German
- **Stable input sources:** word list, Excel/CSV, PDF, image OCR

### Roadmap

- [ ] More language support (extensible to any language)
- [ ] Better card templates and styling
- [ ] Additional input format testing
- [ ] Google Drive integration testing

## Contributing

```bash
# Install dev dependencies
make install

# Format code
make fmt

# Run all checks (lint + typecheck + test)
make check
```

Issues and pull requests are welcome.

## License

MIT
