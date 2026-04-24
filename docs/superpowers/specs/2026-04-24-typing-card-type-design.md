# Typing Card Type Feature

## Summary

Add support for Anki's "Basic (type in the answer)" card type alongside the existing Basic card type. When enabled, the card front shows the source/native word and the user must type the target/learning word. Anki compares the typed answer character-by-character against the correct answer.

## Requirements

- New `--typing` CLI flag on `run` and `ingest` commands (default: `false`)
- Per-card `typing` field stored in the schema, allowing mixed Basic and typing cards in one deck
- When `typing=false` (default): card behaves as current Basic type
- When `typing=true`: card front shows source word + image + audio + type input box; user types target word

## Schema Changes

### Card model (`schema.py`)

Add field:

```python
typing: bool = False
```

- Persists in `cards.json`
- Defaults to `False` for backward compatibility with existing cards
- Preserved during state merge

## CLI Changes

### `run` command

Add `--typing` flag (default: `false`). Passed through to ingest step, sets `typing=True` on all cards in that batch.

### `ingest` command

Add `--typing` flag (default: `false`). Sets `typing=True` on all newly ingested cards.

## Export Changes (`apkg.py`)

### Model field list

Add `"Typing"` field to the genanki model fields:

```python
["SourceWord", "TargetWord", "TargetPronunciation", "TargetExampleSentence",
 "SourceExampleSentence", "TargetMnemonic", "TargetPartOfSpeech",
 "Audio", "Image", "ExampleAudio", "Typing"]
```

### Model ID

Update hash seed from `"anki-builder-model-v2"` to `"anki-builder-model-v3"` since the field list changes.

### Typing field population

When building a genanki note, set the `Typing` field to `"1"` if `card.typing=True`, otherwise `""`.

### Template 1 — Basic (existing, wrapped in conditional)

**Front (`qfmt`):** Wrapped in `{{^Typing}}...{{/Typing}}` so it only renders when `Typing` is empty.

Content unchanged from current:
- TargetWord (large, bold)
- TargetPronunciation
- TargetPartOfSpeech
- Image
- Audio

**Back (`afmt`):** Wrapped in `{{^Typing}}...{{/Typing}}`.

Content unchanged from current:
- FrontSide + hr
- SourceWord
- TargetMnemonic
- TargetExampleSentence
- ExampleAudio (conditional)
- SourceExampleSentence

### Template 2 — Type-in-the-answer (new)

**Front (`qfmt`):** Wrapped in `{{#Typing}}...{{/Typing}}` so it only renders when `Typing` is non-empty.

Content:
- SourceWord (large, bold, centered)
- Image
- Audio
- `{{type:TargetWord}}` — renders the text input box

**Back (`afmt`):** Wrapped in `{{#Typing}}...{{/Typing}}`.

Content:
- `{{FrontSide}}` + `<hr id="answer">`
- `{{type:TargetWord}}` — renders the character-by-character comparison
- TargetPronunciation
- TargetPartOfSpeech
- TargetMnemonic
- TargetExampleSentence
- ExampleAudio (conditional)
- SourceExampleSentence

## State Merge

The `typing` field is preserved on existing cards during merge. New cards inherit the `--typing` CLI flag value. No special merge logic needed beyond Pydantic's default handling.

## No Impact Areas

- **Enrichment:** No changes — `typing` is irrelevant to AI enrichment
- **Media generation:** No changes — audio and images are generated regardless
- **Review:** No changes — card display in terminal review is unaffected

## Backward Compatibility

- Existing `cards.json` files without the `typing` field will default to `False` via Pydantic
- Existing decks re-exported will get the new model ID (v3), which Anki handles as a model update
