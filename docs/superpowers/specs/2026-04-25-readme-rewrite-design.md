# README.md Rewrite — Design Spec

## Overview

Rewrite the README.md as a structured reference document with clean, scannable sections. The goal is to make the project easy to understand for language learners who want rich, multimedia Anki flashcards without the manual effort.

## Target Audience

Language learners who find manual Anki card creation tedious — especially when they want audio, images, mnemonics, and etymology on every card.

## Section Structure

### 1. Why We Need It

- **Title:** `Anki Card AI Builder`
- **Tagline:** One-line summary of what the tool does
- **Problem statement:** 3-4 sentences explaining that creating rich Anki flashcards (audio, images, pronunciation, mnemonics, etymology) by hand is tedious and time-consuming. This tool automates the entire process in one command.
- **Key differentiators (bullet list):**
  - AI enrichment: translations, IPA/Pinyin, example sentences, mnemonics
  - Color-coded etymology: morpheme breakdown (prefix/root/suffix), origin chains to PIE, cross-language cognates (EN/DE/FR/Latin), memory hooks
  - Multimedia: TTS audio + AI-generated cartoon images
  - Flexible inputs: words, Excel, PDF, image OCR, Google Drive
  - Personalization: configurable learner profile (e.g. `"ages 9-12, kid-friendly with emojis"`) tailors card content to the learner
  - One command from input to `.apkg`

### 2. How It Works

- **Mermaid flowchart:** `Ingest -> Enrich -> Media -> Export` (keep existing diagram style)
- **Summary table** with columns: Step | What happens | Output
  - **Ingest:** Extract vocabulary from input sources -> `cards.json` with raw word list
  - **Enrich:** AI adds translations, pronunciation, etymology, mnemonics, example sentences -> enriched `cards.json`
  - **Media:** Generate TTS audio + AI cartoon images -> `media/*.mp3` and `media/*.png`
  - **Export:** Bundle cards + media into Anki package -> `.apkg` file
- **One-liner:** `run` executes steps 1-3 automatically; then use `export` to create the `.apkg`

### 3. Core Features (grouped by category)

**Input Sources**
- Word list, Excel/CSV, PDF, Image OCR (including HEIC/HEIF iPhone photos), folder of files, Google Drive

**AI Enrichment**
- Translations, IPA/Pinyin/Romaji pronunciation, grammatical gender, part of speech
- Example sentences with translations
- Synonyms & antonyms

**Etymology & Mnemonics**
- Color-coded morpheme breakdown (prefix/root/suffix)
- Origin chain tracing to Proto-Indo-European roots
- Cross-language cognates (EN/DE/FR/Latin)
- Memory hooks referencing morphemes

**Media Generation**
- TTS audio for words and example sentences (gTTS)
- AI-generated cartoon images (MiniMax image-01 or Google Gemini)

**Personalization**
- Configurable learner profile (e.g. `"ages 9-12, kid-friendly with emojis"`)

**Export & Workflow**
- Two card types: Basic (show word, reveal answer) and Type-in (type the answer for spelling practice) — use `--typing` flag
- `.apkg` export with HTML templates and embedded media
- Workspace isolation (parallel runs, incremental merging)
- Supported languages table (EN, FR, DE tested; ZH, JA, KO, ES, IT, PT, RU, AR listed)

### 4. Screenshot / Example Card

- Heading: "What You Get" or "Example Card"
- Image: `examples/Screenshot-Anki-MacApp.png`
- Caption highlighting: AI-generated cartoon image, IPA pronunciation, color-coded morpheme breakdown, origin chain, cognates, memory hook, example sentence with translation

### 5. Get Started

**Prerequisites**
- Python 3.12+
- Anki desktop/mobile app (for importing `.apkg`)

**Installation**
- `uv sync`
- Copy `.env.example` to `.env` and fill in API keys

**API Keys table**
| Key | Required for |
|-----|-------------|
| `MINIMAX_API_KEY` | AI enrichment (MiniMax M2.5) + image generation (MiniMax image-01) |
| `GOOGLE_API_KEY` | Image OCR (Google Gemini) + Google Drive + Gemini image generation |

**Language flags**
- `--lang-target` (required): the language you are learning (front of card)
- `--lang-source` (optional, default: `de`): your native language (back of card)

**Usage — full pipeline examples**
- From word list: `anki-builder run --words "Glove,Squirrel,impossible" --lang-target en`
- From Excel/CSV: `anki-builder run --input vocab.xlsx --lang-target en`
- From PDF: `anki-builder run --input textbook.pdf --lang-target en`
- From image (OCR): `anki-builder run --input photo.heic --lang-target en`
- From folder: `anki-builder run --input ./my-scans/ --lang-target en`
- From Google Drive: `anki-builder run --input "https://drive.google.com/drive/folders/..." --lang-target en`

**Continuing in an existing workspace**
- Use `--output workspace/<uuid>` to add more words to an existing workspace

**Step-by-step pipeline**
- `anki-builder ingest` -> `enrich` -> `media` -> `review` -> `export`
- Each step uses `--output` to point to the workspace

**Options**
- `--no-images` / `--no-audio`: skip media generation
- `--typing`: create Type-in cards (spelling practice)
- `--deck "Name"`: custom deck name
- `--apkg ./path.apkg`: custom output path

**CLI reference table**
| Command | Description |
|---------|-------------|
| `run` | Full pipeline: ingest + enrich + media + review |
| `ingest` | Extract vocabulary from input |
| `enrich` | Fill missing fields with AI |
| `media` | Generate TTS audio and AI images |
| `review` | Show cards and media status |
| `export` | Export to `.apkg` file |
| `clean` | Delete a workspace folder |

**Configuration table**
- All environment variables with defaults (MINIMAX_API_KEY, GOOGLE_API_KEY, LEARNER_PROFILE, MEDIA_AUDIO_ENABLED, MEDIA_IMAGE_ENABLED, MEDIA_CONCURRENCY, IMAGE_PROVIDER, EXPORT_DECK_NAME)

### 6. Current Status & Roadmap

**Current Status**
- Working MVP — usable but still evolving
- Tested languages: English, French, German
- Stable input sources: word list, Excel/CSV, PDF, image OCR

**Roadmap**
- More language support (any language as needed)
- Better card templates and styling
- More input formats (need testing)
- Google Drive integration (need testing)

### 7. Contributing & License

**Contributing**
- Dev setup: `uv sync --group dev`
- Run tests: `uv run pytest`
- Brief invitation: issues and PRs welcome

**License**
- MIT
