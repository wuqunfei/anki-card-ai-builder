# Architecture

## System Overview

Anki Card AI Builder is a CLI pipeline that transforms vocabulary inputs into Anki flashcard decks. It follows a linear 5-step pipeline where each step reads/writes to a shared `cards.json` state file within an isolated workspace folder.

## Data Flow

```mermaid
flowchart TD
    subgraph Inputs
        W[Words CLI]
        E[Excel/CSV]
        P[PDF]
        I[Image OCR]
        F[Folder]
        G[Google Drive]
    end

    subgraph "Step 1: Ingest"
        W --> IN[Ingest Layer]
        E --> IN
        P --> IN
        I --> IN
        F --> IN
        G --> IN
    end

    IN -->|cards.json| SM[State Manager]

    subgraph "Step 2: Enrich"
        SM --> EN[AI Enrichment]
        EN -->|enriched cards| SM
    end

    subgraph "Step 3: Media"
        SM --> AU[Audio Generation]
        SM --> IM[Image Generation]
        AU -->|*_audio.mp3| SM
        IM -->|*_image.png| SM
    end

    subgraph "Step 4: Review"
        SM --> RV[Review Display]
    end

    subgraph "Step 5: Export"
        SM --> EX[APKG Builder]
        EX --> APKG[Vocabulary.apkg]
    end
```

## Component Architecture

```mermaid
flowchart LR
    subgraph CLI["cli.py"]
        run
        ingest
        enrich
        media
        review
        export
        clean
    end

    subgraph State["State Layer"]
        SM[StateManager]
        CJ[(cards.json)]
        MD[(media/)]
    end

    subgraph Ingest["Ingest Services"]
        excel["excel.py<br/>openpyxl"]
        pdf["pdf.py<br/>PyMuPDF + MiniMax"]
        image["image.py<br/>Google Gemini"]
        gdrive["gdrive.py<br/>Google Drive API"]
    end

    subgraph Enrich["Enrich Services"]
        ai["ai.py<br/>MiniMax M2.5"]
        vocab["vocabulary.py<br/>helpers"]
    end

    subgraph Media["Media Services"]
        audio["audio.py<br/>gTTS"]
        img["image.py<br/>MiniMax / Gemini"]
    end

    subgraph Export["Export Services"]
        apkg["apkg.py<br/>genanki"]
    end

    CLI --> SM
    SM --> CJ
    SM --> MD
    ingest --> Ingest
    enrich --> Enrich
    media --> Media
    export --> Export
```

## External Services

```mermaid
flowchart TD
    AB[Anki Builder]

    AB -->|"PDF extraction<br/>AI enrichment<br/>Image generation"| MM[MiniMax API]
    AB -->|"Image OCR<br/>Drive file listing<br/>Image generation"| GG[Google API]
    AB -->|"Text-to-speech"| GTTS[gTTS]

    subgraph "MiniMax API"
        MM1["MiniMax M2.5<br/>(enrichment + PDF)"]
        MM2["image-01<br/>(image generation)"]
    end

    subgraph "Google API"
        GG1["Gemini 3 Flash<br/>(OCR + image gen)"]
        GG2["Drive API v3<br/>(folder listing)"]
    end

    MM --> MM1
    MM --> MM2
    GG --> GG1
    GG --> GG2
```

## Card Lifecycle

```mermaid
stateDiagram-v2
    [*] --> extracted : Ingest
    extracted --> enriched : Enrich (AI fills fields)
    enriched --> complete : Media (audio + images)
    complete --> exported : Export (.apkg)
    extracted --> complete : Media (with --no-images/--no-audio)
```

## Workspace Layout

Each pipeline run creates an isolated workspace:

```
workspace/
└── a1b2c3d4/                    # 8-char UUID folder
    ├── cards.json               # Shared state: list of Card objects
    ├── media/
    │   ├── {id}_audio.mp3       # Word TTS audio
    │   ├── {id}_example_audio.mp3  # Example sentence TTS
    │   └── {id}_image.png       # AI-generated illustration
    └── {DeckName}.apkg          # Final Anki export
```

## Key Design Decisions

- **State file as single source of truth**: All steps read/write `cards.json`. This enables incremental runs — re-running a step skips cards that already have the relevant data.
- **Intermediate saves**: Media generation saves `cards.json` after audio and after images separately, so progress is preserved if the process is interrupted.
- **Card merging by key**: Cards are keyed by `(source_word, target_language)`. Re-ingesting the same words preserves existing enrichment and media.
- **Provider fallback**: Image generation tries the primary provider first, then falls back to the secondary if it fails.
- **Workspace isolation**: Each run gets its own UUID folder under `workspace/`, avoiding collisions between parallel runs or different source materials.

## Project Structure

```
src/anki_builder/
├── cli.py              # Typer CLI — run, ingest, enrich, media, review, export, clean
├── config.py           # Environment config loading
├── schema.py           # Card data model (Pydantic)
├── state.py            # JSON state persistence + card merging
├── constants.py        # API endpoint constants
├── ingest/
│   ├── excel.py        # Excel/CSV ingestion (openpyxl)
│   ├── pdf.py          # PDF text extraction (PyMuPDF) + MiniMax vocabulary extraction
│   ├── image.py        # Image OCR (Google Gemini)
│   └── gdrive.py       # Google Drive folder ingestion
├── enrich/
│   ├── ai.py           # AI enrichment (MiniMax M2.5 via Anthropic SDK)
│   └── vocabulary.py   # Vocabulary prompt helpers
├── media/
│   ├── audio.py        # TTS audio generation (gTTS)
│   └── image.py        # AI image generation (MiniMax image-01 / Google Gemini)
└── export/
    └── apkg.py         # Anki .apkg export (genanki)
```
