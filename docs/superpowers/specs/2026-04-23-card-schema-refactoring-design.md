# Card Schema Refactoring

## Summary

Rename Card model fields for clarity, add new optional fields, remove the default for `target_language`, and auto-migrate existing `cards.json` data on load. No behavior changes.

## Field Mapping

| Old Field | New Field | Change Type |
|---|---|---|
| `word` | `source_word` | Rename |
| `translation` | `target_word` | Rename |
| `pronunciation` | `target_pronunciation` | Rename |
| `part_of_speech` | `target_part_of_speech` | Rename |
| `mnemonic` | `target_mnemonic` | Rename |
| `example_sentence` | `target_example_sentence` | Rename |
| `sentence_translation` | `source_example_sentence` | Rename |
| `id` | `id` | Unchanged |
| `source_language` | `source_language` | Unchanged, keep default `"de"` |
| `target_language` | `target_language` | Remove default, now required |
| `source` | `source` | Unchanged |
| `tags` | `tags` | Unchanged |
| `audio_file` | `audio_file` | Unchanged |
| `image_file` | `image_file` | Unchanged |
| `status` | `status` | Unchanged |
| — | `unit` | New, optional |
| — | `reference` | New, optional |
| — | `source_gender` | New, optional |
| — | `target_gender` | New, optional |

## New Schema

```python
class Card(BaseModel):
    # --- Metadata & Tracking ---
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit: str | None = None                    # Textbook unit (e.g., "Unite 1")
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
    target_language: str                       # Learning language ISO (no default, required)
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

## Migration

Auto-migration runs in `state.py` when loading `cards.json`. On load, each card dict is checked for old field names and renamed:

```python
FIELD_MIGRATION = {
    "word": "source_word",
    "translation": "target_word",
    "pronunciation": "target_pronunciation",
    "part_of_speech": "target_part_of_speech",
    "mnemonic": "target_mnemonic",
    "example_sentence": "target_example_sentence",
    "sentence_translation": "source_example_sentence",
}
```

If any old key is found, rename it. New optional fields (`unit`, `reference`, `source_gender`, `target_gender`) default to `None`. For `target_language`, if missing in old data, default to `"en"` during migration only (since old schema defaulted to `"en"`).

The migrated data is written back to `cards.json` after loading so subsequent loads don't re-migrate.

## Affected Files

### Source (10 files)

1. **`schema.py`** — Field definitions (the core change)
2. **`state.py`** — Dedup key (`word` → `source_word`), merge logic field names, migration logic
3. **`cli.py`** — Card creation (`word=` → `source_word=`), display output
4. **`ingest/excel.py`** — Header mapping keys, `CARD_FIELDS` set, validation
5. **`ingest/pdf.py`** — Vocabulary extraction field validation
6. **`enrich/ai.py`** — Enrichment prompt JSON, response parsing, field preservation
7. **`enrich/vocabulary.py`** — Extraction prompt field names
8. **`media/audio.py`** — TTS text source (`card.word` → `card.source_word` or `card.target_word`)
9. **`media/image.py`** — Image generation prompt
10. **`export/apkg.py`** — Anki note fields, HTML card template

### Tests (15 files)

All test files that construct `Card` objects or assert on field names need updating to use the new names.

## Audio TTS Consideration

Currently `media/audio.py` uses `card.word` for TTS. The TTS should speak the **target language word** (the word being learned), so this should become `card.target_word`.

## Anki Template

The HTML template in `export/apkg.py` uses field names like `{{Word}}`, `{{Translation}}`, etc. These are Anki-internal template variables and should be updated to match the new naming for consistency:

| Old Template Var | New Template Var |
|---|---|
| `{{Word}}` | `{{SourceWord}}` |
| `{{Translation}}` | `{{TargetWord}}` |
| `{{Pronunciation}}` | `{{TargetPronunciation}}` |
| `{{ExampleSentence}}` | `{{TargetExampleSentence}}` |
| `{{SentenceTranslation}}` | `{{SourceExampleSentence}}` |
| `{{Mnemonic}}` | `{{TargetMnemonic}}` |
| `{{PartOfSpeech}}` | `{{TargetPartOfSpeech}}` |

Note: This will make existing Anki decks incompatible with newly exported ones. Since this is a build tool (not a sync tool), this is acceptable — users re-export.

## Out of Scope

- No behavior changes to enrichment, media generation, or export logic
- No new CLI commands or flags
- No changes to config.yaml structure
