# Typing Card Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-card "type in the answer" support so cards can optionally require the user to type the target word instead of just revealing it.

**Architecture:** Add a `typing` boolean field to the Card schema. At export time, populate a `Typing` field in the genanki model. Use two mutually exclusive templates (Basic and Type-in) controlled by Anki's `{{#Typing}}`/`{{^Typing}}` conditionals. CLI gets a `--typing` flag on `run` and `ingest`.

**Tech Stack:** Python, Pydantic, Click, genanki

---

### Task 1: Add `typing` field to Card schema

**Files:**
- Modify: `src/anki_builder/schema.py:36` (after `target_mnemonic`)
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_schema.py`:

```python
def test_typing_defaults_to_false(self):
    card = Card(source_word="test", source_language="de", target_language="en")
    self.assertFalse(card.typing)

def test_typing_can_be_set_true(self):
    card = Card(source_word="test", source_language="de", target_language="en", typing=True)
    self.assertTrue(card.typing)

def test_typing_roundtrip(self):
    card = Card(source_word="test", source_language="de", target_language="en", typing=True)
    data = card.model_dump()
    card2 = Card(**data)
    self.assertTrue(card2.typing)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_schema.py::TestCard::test_typing_defaults_to_false -v`
Expected: FAIL with "unexpected keyword argument" or similar

- [ ] **Step 3: Write minimal implementation**

In `src/anki_builder/schema.py`, add after line 36 (`target_mnemonic`):

```python
    # --- Card Type ---
    typing: bool = False                       # True = "type in the answer" card
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_schema.py -v`
Expected: All tests PASS (including new ones)

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/schema.py tests/test_schema.py
git commit -m "feat: add typing field to Card schema"
```

---

### Task 2: Add `--typing` CLI flag to `ingest` and `run` commands

**Files:**
- Modify: `src/anki_builder/cli.py:22-27` (`_words_to_cards` function)
- Modify: `src/anki_builder/cli.py:95-104` (`run` command options and signature)
- Modify: `src/anki_builder/cli.py:118-119` (`run` command word ingestion)
- Modify: `src/anki_builder/cli.py:140` (`run` command merge)
- Modify: `src/anki_builder/cli.py:191-196` (`ingest` command options and signature)
- Modify: `src/anki_builder/cli.py:206-208` (`ingest` command word ingestion)
- Modify: `src/anki_builder/cli.py:232` (`ingest` command merge)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_ingest_with_typing_flag(self):
    runner = CliRunner()
    with runner.isolated_filesystem():
        self._create_xlsx(Path("vocab.xlsx"))
        result = runner.invoke(main, [
            "ingest", "--input", "vocab.xlsx", "--lang-target", "en", "--typing"
        ])
        self.assertEqual(result.exit_code, 0, msg=result.output)
        import json
        cards_data = json.loads(Path("output/cards.json").read_text())
        self.assertTrue(all(c["typing"] for c in cards_data))

def test_ingest_without_typing_flag(self):
    runner = CliRunner()
    with runner.isolated_filesystem():
        self._create_xlsx(Path("vocab.xlsx"))
        result = runner.invoke(main, [
            "ingest", "--input", "vocab.xlsx", "--lang-target", "en"
        ])
        self.assertEqual(result.exit_code, 0, msg=result.output)
        import json
        cards_data = json.loads(Path("output/cards.json").read_text())
        self.assertFalse(any(c["typing"] for c in cards_data))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestCLI::test_ingest_with_typing_flag -v`
Expected: FAIL — `--typing` not recognized

- [ ] **Step 3: Write minimal implementation**

In `src/anki_builder/cli.py`:

**3a.** Update `_words_to_cards` (line 22) to accept `typing` parameter:

```python
def _words_to_cards(words_str: str, target_language: str, source_language: str, typing: bool = False) -> list[Card]:
    words = [w.strip() for w in words_str.split(",") if w.strip()]
    return [
        Card(source_word=w, target_language=target_language, source_language=source_language, typing=typing)
        for w in words
    ]
```

**3b.** Add `--typing` option to `ingest` command (after line 195, the `--lang-source` option):

```python
@click.option("--typing", is_flag=True, help="Create 'type in the answer' cards")
```

Update the `ingest` function signature to include `typing: bool`:

```python
def ingest(input_path: str | None, words: str | None, target_language: str, source_language: str, typing: bool):
```

In the `ingest` function body, after cards are created (from any source), set `typing` on all cards before merge. After the line that creates cards (whether from words or file), add:

```python
    if typing:
        cards = [c.model_copy(update={"typing": True}) for c in cards]
```

Add this right before `merged = state.merge_cards(cards)` (line 232).

**3c.** Add `--typing` option to `run` command (after line 102, the `--no-audio` option):

```python
@click.option("--typing", is_flag=True, help="Create 'type in the answer' cards")
```

Update the `run` function signature to include `typing: bool`:

```python
def run(input_path: str | None, words: str | None, target_language: str, source_language: str,
        deck_name: str | None, no_images: bool, no_audio: bool, typing: bool):
```

In the `run` function body, pass `typing` to `_words_to_cards`:

```python
        cards = _words_to_cards(words, target_language, source_language, typing)
```

And after file-based ingestion, set typing on all cards before merge (right before `merged = state.merge_cards(cards)` at line 140):

```python
    if typing:
        cards = [c.model_copy(update={"typing": True}) for c in cards]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/cli.py tests/test_cli.py
git commit -m "feat: add --typing CLI flag to run and ingest commands"
```

---

### Task 3: Update genanki model with Typing field and dual templates

**Files:**
- Modify: `src/anki_builder/export/apkg.py:8-51` (model definition)
- Test: `tests/test_export_apkg.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_export_apkg.py`:

```python
def test_export_typing_card(self):
    """Typing cards should export with the Typing field set to '1'."""
    tmpdir = tempfile.mkdtemp()
    output_path = Path(tmpdir) / "test.apkg"
    cards = [
        Card(
            id="card-typing",
            source_word="dog",
            target_language="en",
            target_word="Hund",
            target_pronunciation="/dɒɡ/",
            target_example_sentence="The dog plays! 🐕",
            source_example_sentence="Der Hund spielt! 🐕",
            target_mnemonic='<span style="color:red">dog</span>',
            target_part_of_speech="noun",
            status="enriched",
            typing=True,
        ),
    ]
    export_apkg(cards, output_path, deck_name="Typing Deck")
    self.assertTrue(output_path.exists())
    self.assertTrue(zipfile.is_zipfile(output_path))

def test_export_mixed_typing_and_basic(self):
    """A deck can contain both basic and typing cards."""
    tmpdir = tempfile.mkdtemp()
    output_path = Path(tmpdir) / "test.apkg"
    cards = [
        Card(
            id="card-basic",
            source_word="dog",
            target_language="en",
            target_word="Hund",
            status="enriched",
            typing=False,
        ),
        Card(
            id="card-typing",
            source_word="cat",
            target_language="en",
            target_word="Katze",
            status="enriched",
            typing=True,
        ),
    ]
    export_apkg(cards, output_path, deck_name="Mixed Deck")
    self.assertTrue(output_path.exists())
    self.assertTrue(zipfile.is_zipfile(output_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_export_apkg.py::TestApkgExport::test_export_typing_card -v`
Expected: FAIL — field count mismatch (model expects 11 fields, note provides 10)

- [ ] **Step 3: Write minimal implementation**

Replace the model and note-building code in `src/anki_builder/export/apkg.py`:

**3a.** Update MODEL_ID (line 8):

```python
MODEL_ID = int(hashlib.md5(b"anki-builder-model-v3").hexdigest()[:8], 16)
```

**3b.** Replace CARD_MODEL (lines 10-51) with:

```python
CARD_MODEL = genanki.Model(
    MODEL_ID,
    "Anki Builder Card",
    fields=[
        {"name": "SourceWord"},
        {"name": "TargetWord"},
        {"name": "TargetPronunciation"},
        {"name": "TargetExampleSentence"},
        {"name": "SourceExampleSentence"},
        {"name": "TargetMnemonic"},
        {"name": "TargetPartOfSpeech"},
        {"name": "Audio"},
        {"name": "Image"},
        {"name": "ExampleAudio"},
        {"name": "Typing"},
    ],
    templates=[
        {
            "name": "Basic",
            "qfmt": (
                '{{^Typing}}'
                '<div style="text-align:center; font-size:28px; font-weight:bold; margin:20px; color:#2c3e50;">'
                "{{TargetWord}}"
                "</div>"
                '<div style="text-align:center; font-size:16px; color:#7f8c8d; margin-bottom:8px;">'
                "{{TargetPronunciation}}"
                "</div>"
                '<div style="text-align:center; font-size:13px; color:#999; margin-bottom:12px;">'
                "{{TargetPartOfSpeech}}"
                "</div>"
                '<div style="text-align:center; margin:10px;">{{Image}}</div>'
                '<div style="text-align:center;">{{Audio}}</div>'
                '{{/Typing}}'
            ),
            "afmt": (
                '{{^Typing}}'
                '{{FrontSide}}<hr id="answer">'
                '<div style="text-align:center; font-size:22px; color:#333; margin:10px;">{{SourceWord}}</div>'
                '<div style="text-align:center; font-size:14px; margin:10px;">{{TargetMnemonic}}</div>'
                '<div style="text-align:center; font-size:16px; margin:10px; color:#2c3e50;">{{TargetExampleSentence}}</div>'
                '{{#ExampleAudio}}'
                '<div style="text-align:center; margin:6px 0 10px;">{{ExampleAudio}}</div>'
                '{{/ExampleAudio}}'
                '<div style="text-align:center; font-size:14px; color:#666;">{{SourceExampleSentence}}</div>'
                '{{/Typing}}'
            ),
        },
        {
            "name": "Type-in",
            "qfmt": (
                '{{#Typing}}'
                '<div style="text-align:center; font-size:28px; font-weight:bold; margin:20px; color:#2c3e50;">'
                "{{SourceWord}}"
                "</div>"
                '<div style="text-align:center; margin:10px;">{{Image}}</div>'
                '<div style="text-align:center;">{{Audio}}</div>'
                '<div style="text-align:center; margin:20px;">{{type:TargetWord}}</div>'
                '{{/Typing}}'
            ),
            "afmt": (
                '{{#Typing}}'
                '{{FrontSide}}<hr id="answer">'
                '<div style="text-align:center; margin:20px;">{{type:TargetWord}}</div>'
                '<div style="text-align:center; font-size:22px; color:#333; margin:10px;">{{TargetWord}}</div>'
                '<div style="text-align:center; font-size:16px; color:#7f8c8d; margin-bottom:8px;">'
                "{{TargetPronunciation}}"
                "</div>"
                '<div style="text-align:center; font-size:13px; color:#999; margin-bottom:12px;">'
                "{{TargetPartOfSpeech}}"
                "</div>"
                '<div style="text-align:center; font-size:14px; margin:10px;">{{TargetMnemonic}}</div>'
                '<div style="text-align:center; font-size:16px; margin:10px; color:#2c3e50;">{{TargetExampleSentence}}</div>'
                '{{#ExampleAudio}}'
                '<div style="text-align:center; margin:6px 0 10px;">{{ExampleAudio}}</div>'
                '{{/ExampleAudio}}'
                '<div style="text-align:center; font-size:14px; color:#666;">{{SourceExampleSentence}}</div>'
                '{{/Typing}}'
            ),
        },
    ],
)
```

**3c.** Update `_card_to_note` (line 93-108) to include the Typing field. Add `"1" if card.typing else ""` as the last field in the fields list:

```python
    note = genanki.Note(
        model=CARD_MODEL,
        fields=[
            source_display,
            target_display,
            card.target_pronunciation or "",
            card.target_example_sentence or "",
            card.source_example_sentence or "",
            card.target_mnemonic or "",
            card.target_part_of_speech or "",
            audio_field,
            image_field,
            example_audio_field,
            "1" if card.typing else "",
        ],
        guid=genanki.guid_for(card.id),
    )
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/test_export_apkg.py tests/test_schema.py tests/test_cli.py tests/test_state.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/export/apkg.py tests/test_export_apkg.py
git commit -m "feat: add dual templates for basic and type-in card types"
```

---

### Task 4: Preserve `typing` field in state merge

**Files:**
- Modify: `src/anki_builder/state.py:66-70` (merge field list)
- Test: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_state.py`:

```python
def test_merge_preserves_typing_field(self):
    existing = [
        Card(
            source_word="dog",
            target_language="en",
            target_word="Hund",
            status="enriched",
            typing=True,
        ),
    ]
    self.state.save_cards(existing)

    new_cards = [
        Card(source_word="dog", target_language="en"),
    ]
    merged = self.state.merge_cards(new_cards)
    self.assertTrue(merged[0].typing)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state.py::TestStateManager::test_merge_preserves_typing_field -v`
Expected: FAIL — `merged[0].typing` is `False` because `typing` is not in the merge field list

- [ ] **Step 3: Write minimal implementation**

In `src/anki_builder/state.py`, add `"typing"` to the merge field list at line 66-70. Update the list to:

```python
                for field in ["target_word", "target_pronunciation",
                              "target_example_sentence", "source_example_sentence",
                              "target_mnemonic", "target_part_of_speech",
                              "audio_file", "image_file",
                              "target_example_audio", "typing"]:
```

Note: The merge logic checks `if old_val is not None and new_val is None`. Since `typing` is a `bool` (never `None`), the existing card's `True` won't overwrite the new card's `False` with this check. We need to handle `typing` specially. After the field loop (after line 74), add:

```python
                if old.typing:
                    update_data["typing"] = old.typing
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_state.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/state.py tests/test_state.py
git commit -m "feat: preserve typing field during card merge"
```

---

### Task 5: Full integration test

**Files:**
- Test: `tests/test_export_apkg.py`

- [ ] **Step 1: Write the integration test**

Add to `tests/test_export_apkg.py`:

```python
def test_full_pipeline_mixed_deck(self):
    """End-to-end: mixed basic + typing cards in one deck, both export correctly."""
    tmpdir = tempfile.mkdtemp()
    output_path = Path(tmpdir) / "test.apkg"

    basic_card = Card(
        id="basic-1",
        source_word="dog",
        target_language="en",
        target_word="Hund",
        target_pronunciation="/dɒɡ/",
        target_example_sentence="The dog plays! 🐕",
        source_example_sentence="Der Hund spielt! 🐕",
        target_mnemonic='<span style="color:red">dog</span>',
        target_part_of_speech="noun",
        status="enriched",
        typing=False,
    )
    typing_card = Card(
        id="typing-1",
        source_word="cat",
        target_language="en",
        target_word="Katze",
        target_pronunciation="/kæt/",
        target_example_sentence="The cat sleeps! 🐱",
        source_example_sentence="Die Katze schläft! 🐱",
        target_mnemonic='<span style="color:red">cat</span>',
        target_part_of_speech="noun",
        status="enriched",
        typing=True,
    )

    export_apkg([basic_card, typing_card], output_path, deck_name="Mixed Deck")
    self.assertTrue(output_path.exists())
    self.assertTrue(zipfile.is_zipfile(output_path))

    # Verify the apkg contains an sqlite database with 2 notes
    with zipfile.ZipFile(output_path) as zf:
        self.assertIn("collection.anki2", zf.namelist())
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_export_apkg.py
git commit -m "test: add integration test for mixed basic/typing deck export"
```
