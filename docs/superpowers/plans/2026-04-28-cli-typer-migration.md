# CLI Typer Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the CLI from Click to Typer and rename the entry point from `anki-builder` to `ankids`.

**Architecture:** Direct 1:1 translation of Click decorators to Typer type-annotated function parameters. All business logic remains untouched. Only the CLI layer and tests change.

**Tech Stack:** Python 3.12, Typer >=0.15, pytest

---

### Task 1: Update dependencies in pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace click with typer and rename entry point**

In `pyproject.toml`, make these changes:

1. Replace `"click>=8.1"` with `"typer>=0.15"` in the dependencies list.
2. Change `anki-builder = "anki_builder.cli:main"` to `ankids = "anki_builder.cli:main"` in `[project.scripts]`.

The full modified sections:

```toml
dependencies = [
    "typer>=0.15",
    "openpyxl>=3.1",
    "pymupdf>=1.24",
    "genanki>=0.13",
    "anthropic>=0.40",
    "httpx>=0.27",
    "pydantic>=2.9",
    "gtts>=2.5.4",
    "python-dotenv>=1.2.2",
    "pillow-heif>=1.3.0",
    "google-genai>=1.0.0",
    "pillow>=12.2.0",
]

[project.scripts]
ankids = "anki_builder.cli:main"
```

- [ ] **Step 2: Reinstall the package**

Run: `pip install -e .`
Expected: Installs typer, `ankids` command becomes available.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: replace click with typer, rename entry point to ankids"
```

---

### Task 2: Migrate cli.py — imports, app setup, and helper functions

**Files:**
- Modify: `src/anki_builder/cli.py`

- [ ] **Step 1: Replace imports and app initialization**

Replace the top of `cli.py` (lines 1-20 and 131-149) with:

```python
import asyncio
import uuid
from pathlib import Path
from typing import Optional

import typer

from anki_builder.config import Config, load_config
from anki_builder.constants import IMAGE_EXTENSIONS, STATUS_ENRICHED, STATUS_EXTRACTED
from anki_builder.enrich.ai import enrich_cards
from anki_builder.export.apkg import export_apkg
from anki_builder.ingest.excel import ingest_excel
from anki_builder.ingest.gdrive import GDRIVE_URL_PATTERN, ingest_gdrive_folder
from anki_builder.ingest.image import ingest_image
from anki_builder.ingest.pdf import ingest_pdf
from anki_builder.media.audio import generate_audio_batch
from anki_builder.media.image import generate_image_batch
from anki_builder.schema import Card
from anki_builder.state import StateManager, finalize_card_status

WORKSPACE_DIR = Path("workspace")

app = typer.Typer(help="ankids: AI-powered Anki card builder for language learning.")
```

- [ ] **Step 2: Update helper functions to remove click references**

Replace `click.echo` with `print` and `click.ClickException` with `typer.Exit` (raising with a printed message) in the helper functions.

`_resolve_work_dir`:
```python
def _resolve_work_dir(output: str | None) -> Path:
    """Resolve the output folder. If given, use it; otherwise create a new UUID folder under workspace/."""
    if output:
        return Path(output)
    folder_id = uuid.uuid4().hex[:8]
    work_dir = WORKSPACE_DIR / folder_id
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created new workspace: {work_dir}")
    print(f"Use --output {work_dir} to continue with this workspace.")
    return work_dir
```

`_detect_input_type`:
```python
def _detect_input_type(path_or_url: str) -> str:
    if GDRIVE_URL_PATTERN.search(path_or_url):
        return "gdrive"
    path = Path(path_or_url)
    if path.is_dir():
        return "folder"
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".csv"):
        return "excel"
    elif suffix == ".pdf":
        return "pdf"
    elif suffix in IMAGE_EXTENSIONS:
        return "image"
    else:
        print(f"Error: Unsupported file type: {suffix}")
        raise typer.Exit(code=1)
```

`_ingest_source`:
```python
def _ingest_source(
    input_path: str,
    input_type: str,
    target_language: str,
    source_language: str,
    config: Config,
    state: StateManager | None = None,
    typing: bool = False,
) -> list[Card]:
    """Dispatch ingestion to the appropriate handler based on input type."""
    if input_type == "gdrive":
        return ingest_gdrive_folder(
            input_path, target_language, config.google_api_key, config.minimax_api_key, source_language
        )
    elif input_type == "excel":
        return ingest_excel(Path(input_path), target_language, source_language)
    elif input_type == "pdf":
        return ingest_pdf(Path(input_path), target_language, config.minimax_api_key, source_language)
    elif input_type == "image":
        return ingest_image(Path(input_path), target_language, source_language, config.google_api_key)
    elif input_type == "folder":
        return _ingest_folder(
            Path(input_path), target_language, source_language, config.google_api_key, config.minimax_api_key,
            state=state, typing=typing,
        )
    print(f"Error: Unknown input type: {input_type}")
    raise typer.Exit(code=1)
```

`_ingest_folder`:
```python
def _ingest_folder(
    folder: Path,
    target_language: str,
    source_language: str,
    google_api_key: str,
    minimax_api_key: str,
    state: StateManager | None = None,
    typing: bool = False,
) -> list[Card]:
    supported = IMAGE_EXTENSIONS | {".pdf"}
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in supported)
    if not files:
        print(f"Error: No supported files found in {folder}")
        raise typer.Exit(code=1)

    all_cards: list[Card] = []
    for i, f in enumerate(files, 1):
        suffix = f.suffix.lower()
        try:
            if suffix in IMAGE_EXTENSIONS:
                print(f"  [{i}/{len(files)}] Processing image: {f.name}")
                cards = ingest_image(f, target_language, source_language, google_api_key)
            elif suffix == ".pdf":
                print(f"  [{i}/{len(files)}] Processing PDF: {f.name}")
                cards = ingest_pdf(f, target_language, minimax_api_key, source_language)
            else:
                continue
        except Exception as e:
            print(f"  Warning: failed to process {f.name}: {e}")
            continue

        if typing:
            cards = [c.model_copy(update={"typing": True}) for c in cards]
        all_cards.extend(cards)

        # Save incrementally after each file
        if state:
            merged = state.merge_cards(all_cards)
            state.save_cards(merged)
            print(f"  Saved {len(merged)} cards so far.")

    return all_cards
```

- [ ] **Step 3: Remove the OrderedGroup class**

Delete the entire `OrderedGroup` class (lines 131-144) and the `@click.group(...)` / `def main():` block (lines 147-149). The `app` Typer instance and `main` function replace them:

```python
def main():
    app()
```

Place `def main():` at the very end of the file (after all commands).

- [ ] **Step 4: Verify the file compiles**

Run: `python -c "from anki_builder.cli import app; print('OK')"`
Expected: `OK` (may fail until commands are migrated in Task 3, but imports should work)

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/cli.py
git commit -m "refactor: migrate cli.py imports, helpers, and app setup to typer"
```

---

### Task 3: Migrate all 7 commands to Typer

**Files:**
- Modify: `src/anki_builder/cli.py`

- [ ] **Step 1: Migrate the `run` command**

Replace the Click-decorated `run` function with:

```python
@app.command()
def run(
    input_path: Optional[str] = typer.Option(None, "--input", help="Input file, folder, or Google Drive URL"),
    words: Optional[str] = typer.Option(None, help='Comma-separated words (e.g. "Glove,Squirrel,impossible")'),
    target_language: str = typer.Option(..., "--lang-target", help="Target language code (en, fr, zh)"),
    source_language: str = typer.Option("de", "--lang-source", help="Source language code (default: de)"),
    deck_name: Optional[str] = typer.Option(None, "--deck", help="Deck name for export"),
    no_images: bool = typer.Option(False, help="Skip image generation"),
    no_audio: bool = typer.Option(False, help="Skip audio generation"),
    typing: bool = typer.Option(False, help="Create 'type in the answer' cards"),
    output_dir: Optional[str] = typer.Option(None, "--output", help="Output folder (default: new workspace/<uuid>)"),
):
    """Run full pipeline: ingest, enrich, media, review (export separately)."""
    if not input_path and not words:
        print("Error: Provide either --input or --words.")
        raise typer.Exit(code=1)
    if input_path and words:
        print("Error: Use either --input or --words, not both.")
        raise typer.Exit(code=1)

    config = load_config()
    work_dir = _resolve_work_dir(output_dir)
    state = StateManager(work_dir)

    # Validate API keys
    config.require_minimax_key()

    # Ingest
    input_type = None
    if words:
        cards = _words_to_cards(words, target_language, source_language, typing)
        print(f"Step 1/4: Ingesting {len(cards)} words from command line...")
    else:
        assert input_path is not None
        input_type = _detect_input_type(input_path)
        if input_type in ("image", "folder", "gdrive"):
            config.require_google_key()
        print(f"Step 1/4: Ingesting {input_path}...")
        cards = _ingest_source(input_path, input_type, target_language, source_language, config, state, typing)

    if typing and input_type != "folder":
        cards = [c.model_copy(update={"typing": True}) for c in cards]

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    print(f"  Extracted {len(cards)} cards. Total: {len(merged)}.")

    # Enrich
    to_enrich = [c for c in merged if c.status == STATUS_EXTRACTED]
    if to_enrich:
        print(f"Step 2/4: Enriching {len(to_enrich)} of {len(merged)} cards with AI...")
        if config.enrich_provider == "gemini":
            config.require_google_key()
        else:
            config.require_minimax_key()
        enrich_key = config.google_api_key if config.enrich_provider == "gemini" else config.minimax_api_key
        enriched = enrich_cards(merged, api_key=enrich_key, provider=config.enrich_provider)
        state.save_cards(enriched)
        print("  Enrichment complete.")
    else:
        enriched = merged
        print(f"Step 2/4: All {len(merged)} cards already enriched, skipping.")

    # Media
    need_audio = [c for c in enriched if not c.audio_file]
    need_image = [c for c in enriched if not c.image_file]

    if (need_audio or need_image) and not (no_audio and no_images):
        print("Step 3/4: Generating media...")
        if not no_audio and config.audio_enabled and need_audio:
            print(
                f"  Generating audio for {len(need_audio)} cards ({len(enriched) - len(need_audio)} already done)..."
            )
            enriched = generate_audio_batch(enriched, state.media_dir)
            state.save_cards(enriched)
        elif not no_audio and config.audio_enabled:
            print(f"  Audio: all {len(enriched)} cards already have audio, skipping.")

        if not no_images and config.image_enabled and need_image:
            image_api_key = config.google_api_key if config.image_provider == "gemini" else config.minimax_api_key
            fallback_key = config.minimax_api_key if config.image_provider == "gemini" else config.google_api_key
            print(
                f"  Generating images for {len(need_image)} cards"
                f" ({len(enriched) - len(need_image)} already done)"
                f" [{config.image_provider}]..."
            )
            enriched = asyncio.run(
                generate_image_batch(
                    enriched,
                    state.media_dir,
                    image_api_key,
                    config.concurrency,
                    config.image_provider,
                    fallback_key,
                )
            )
            state.save_cards(enriched)
        elif not no_images and config.image_enabled:
            print(f"  Images: all {len(enriched)} cards already have images, skipping.")

        print("  Media complete.")
    else:
        print(f"Step 3/4: All {len(enriched)} cards already have media, skipping.")

    updated = finalize_card_status(enriched, no_images, no_audio)
    state.save_cards(updated)

    # Review prompt
    print("\nStep 4/4: Review your cards and media.")
    print(f"  Media folder: {state.media_dir.resolve()}")
    print(f"  Cards: {len(updated)}")
    print("\nRun 'ankids review' to see card details.")
    name = deck_name or config.default_deck_name
    print(f'When ready, run: ankids export --output "{work_dir}" --deck "{name}"')
```

- [ ] **Step 2: Migrate the `ingest` command**

```python
@app.command()
def ingest(
    input_path: Optional[str] = typer.Option(None, "--input", help="Input file, folder, or Google Drive URL"),
    words: Optional[str] = typer.Option(None, help='Comma-separated words (e.g. "Glove,Squirrel,impossible")'),
    target_language: str = typer.Option(..., "--lang-target", help="Target language code (en, fr, zh)"),
    source_language: str = typer.Option("de", "--lang-source", help="Source language code (default: de)"),
    typing: bool = typer.Option(False, help="Create 'type in the answer' cards"),
    output_dir: Optional[str] = typer.Option(None, "--output", help="Output folder (default: new workspace/<uuid>)"),
):
    """Step 1: Extract vocabulary from a file, folder, URL, or word list."""
    if not input_path and not words:
        print("Error: Provide either --input or --words.")
        raise typer.Exit(code=1)
    if input_path and words:
        print("Error: Use either --input or --words, not both.")
        raise typer.Exit(code=1)

    config = load_config()
    work_dir = _resolve_work_dir(output_dir)
    state = StateManager(work_dir)

    input_type = None
    if words:
        cards = _words_to_cards(words, target_language, source_language, typing)
        print(f"Ingesting {len(cards)} words from command line...")
    else:
        assert input_path is not None
        input_type = _detect_input_type(input_path)

        print(f"Ingesting {input_path} as {input_type}...")
        if input_type in ("image", "folder", "gdrive"):
            config.require_google_key()
        if input_type in ("pdf", "gdrive"):
            config.require_minimax_key()

        cards = _ingest_source(input_path, input_type, target_language, source_language, config, state, typing)

    if typing and input_type != "folder":
        cards = [c.model_copy(update={"typing": True}) for c in cards]

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    print(f"Extracted {len(cards)} cards. Total: {len(merged)} cards.")
```

- [ ] **Step 3: Migrate the `enrich` command**

```python
@app.command()
def enrich(
    output_dir: str = typer.Option(..., "--output", help="Output folder (e.g. workspace/<uuid>)"),
):
    """Step 2: Fill missing card fields (translation, pronunciation, examples) using AI."""
    config = load_config()
    state = StateManager(Path(output_dir))

    cards = state.load_cards()
    if not cards:
        print("No cards found. Run 'ingest' first.")
        return

    to_enrich = [c for c in cards if c.status == STATUS_EXTRACTED]
    if not to_enrich:
        print(f"All {len(cards)} cards already enriched, nothing to do.")
        return

    print(f"Enriching {len(to_enrich)} of {len(cards)} cards ({len(cards) - len(to_enrich)} already done)...")
    if config.enrich_provider == "gemini":
        config.require_google_key()
    else:
        config.require_minimax_key()
    enrich_key = config.google_api_key if config.enrich_provider == "gemini" else config.minimax_api_key
    enriched = enrich_cards(cards, api_key=enrich_key, provider=config.enrich_provider)
    state.save_cards(enriched)
    print("Enrichment complete.")
```

- [ ] **Step 4: Migrate the `media` command**

```python
@app.command()
def media(
    no_images: bool = typer.Option(False, help="Skip image generation"),
    no_audio: bool = typer.Option(False, help="Skip audio generation"),
    output_dir: str = typer.Option(..., "--output", help="Output folder (e.g. workspace/<uuid>)"),
):
    """Step 3: Generate TTS audio and AI images for cards."""
    config = load_config()
    if not no_images and config.image_enabled:
        config.require_minimax_key()
    state = StateManager(Path(output_dir))
    cards = state.load_cards()

    if not cards:
        print("No cards found. Run 'ingest' first.")
        return

    need_audio = [c for c in cards if not c.audio_file]
    need_image = [c for c in cards if not c.image_file]

    if not no_audio and config.audio_enabled:
        if need_audio:
            print(f"Generating audio for {len(need_audio)} cards ({len(cards) - len(need_audio)} already done)...")
            cards = generate_audio_batch(cards, state.media_dir)
            state.save_cards(cards)
        else:
            print(f"Audio: all {len(cards)} cards already have audio, skipping.")

    if not no_images and config.image_enabled:
        if need_image:
            image_api_key = config.google_api_key if config.image_provider == "gemini" else config.minimax_api_key
            fallback_key = config.minimax_api_key if config.image_provider == "gemini" else config.google_api_key
            print(
                f"Generating images for {len(need_image)} cards"
                f" ({len(cards) - len(need_image)} already done)"
                f" [{config.image_provider}]..."
            )
            cards = asyncio.run(
                generate_image_batch(
                    cards,
                    state.media_dir,
                    image_api_key,
                    config.concurrency,
                    config.image_provider,
                    fallback_key,
                )
            )
            state.save_cards(cards)
        else:
            print(f"Images: all {len(cards)} cards already have images, skipping.")

    updated = finalize_card_status(cards, no_images, no_audio)
    state.save_cards(updated)
    print("Media generation complete.")
```

- [ ] **Step 5: Migrate the `review` command**

```python
@app.command()
def review(
    output_dir: str = typer.Option(..., "--output", help="Output folder (e.g. workspace/<uuid>)"),
):
    """Step 4: Show all cards and media status for review before export."""
    state = StateManager(Path(output_dir))
    cards = state.load_cards()

    if not cards:
        print("No cards found. Run 'ingest' first.")
        return

    print(f"\n{len(cards)} cards ready for review.\n")
    print(f"Media folder: {state.media_dir.resolve()}\n")

    for i, card in enumerate(cards, 1):
        print(f"[{i}] {card.source_word}")
        print(f"    Target Word:    {card.target_word or '(missing)'}")
        print(f"    Pronunciation:  {card.target_pronunciation or '(missing)'}")
        print(f"    Example:        {card.target_example_sentence or '(missing)'}")
        print(f"    Mnemonic:       {card.target_mnemonic or '(missing)'}")
        print(f"    Audio:          {'OK' if card.audio_file else 'MISSING'}")
        print(f"    Image:          {'OK' if card.image_file else 'MISSING'}")
        print()

    print(f"Review images and audio in: {state.media_dir.resolve()}")
    print('When ready, run: ankids export --deck "Your Deck Name"')
```

- [ ] **Step 6: Migrate the `export` command**

```python
@app.command()
def export(
    deck_name: Optional[str] = typer.Option(None, "--deck", help="Deck name (default: Vocabulary)"),
    output_dir: str = typer.Option(..., "--output", help="Output folder (e.g. workspace/<uuid>)"),
    apkg_path: Optional[str] = typer.Option(None, "--apkg", help="Custom .apkg file path"),
    prune: bool = typer.Option(False, help="Remove cards not in current source"),
):
    """Step 5: Export cards with media to an Anki .apkg file."""
    config = load_config()
    work_dir = Path(output_dir)
    state = StateManager(work_dir)
    cards = state.load_cards()

    name = deck_name or config.default_deck_name
    out = Path(apkg_path) if apkg_path else work_dir / f"{name}.apkg"

    print(f"Exporting {len(cards)} cards to {out}...")
    export_apkg(cards, out, name)
    print(f"Done! Created {out}")
```

- [ ] **Step 7: Migrate the `clean` command**

Note: Click's `@click.confirmation_option` becomes `typer.confirm()` called inside the function body.

```python
@app.command()
def clean(
    output_dir: str = typer.Option(..., "--output", help="Output folder to clean (e.g. workspace/<uuid>)"),
):
    """Remove an output folder (cards, media, .apkg) to start fresh."""
    import shutil

    work_dir = Path(output_dir)
    typer.confirm("This will delete all cards, media, and exported files in this folder. Continue?", abort=True)
    if work_dir.exists():
        shutil.rmtree(work_dir)
        print(f"Removed {work_dir}/")
    else:
        print("Nothing to clean.")
```

- [ ] **Step 8: Add the main() function at the end of the file**

At the very end of `cli.py`, add:

```python
def main():
    app()
```

- [ ] **Step 9: Verify the CLI loads**

Run: `python -c "from anki_builder.cli import app, main; print('OK')"`
Expected: `OK`

Run: `ankids --help`
Expected: Shows help with all 7 commands listed.

- [ ] **Step 10: Commit**

```bash
git add src/anki_builder/cli.py
git commit -m "refactor: migrate all 7 CLI commands from click to typer"
```

---

### Task 4: Rewrite tests using Typer's CliRunner

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Rewrite tests**

Replace the entire `tests/test_cli.py` with:

```python
import json
from pathlib import Path
from unittest.mock import patch

import openpyxl
from typer.testing import CliRunner

from anki_builder.cli import app

runner = CliRunner()


def _create_xlsx(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["word", "translation"])
    ws.append(["dog", "Hund"])
    ws.append(["cat", "Katze"])
    wb.save(path)


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ankids" in result.output.lower()


def test_ingest_command(tmp_path):
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    out = tmp_path / "myout"
    result = runner.invoke(app, ["ingest", "--input", str(xlsx), "--lang-target", "en", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "cards.json").exists()


def test_ingest_creates_workspace_uuid_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    result = runner.invoke(app, ["ingest", "--input", str(xlsx), "--lang-target", "en"])
    assert result.exit_code == 0, result.output
    workspace_dirs = list((tmp_path / "workspace").iterdir())
    assert len(workspace_dirs) == 1
    assert (workspace_dirs[0] / "cards.json").exists()


@patch("anki_builder.cli.enrich_cards")
def test_enrich_command(mock_enrich, tmp_path):
    mock_enrich.return_value = []
    out = tmp_path / "myout"
    out.mkdir()
    (out / "cards.json").write_text("[]")
    result = runner.invoke(
        app,
        ["enrich", "--output", str(out)],
        env={"MINIMAX_API_KEY": "test-key"},
    )
    assert result.exit_code == 0, result.output


def test_export_command(tmp_path):
    out = tmp_path / "myout"
    out.mkdir()
    (out / "cards.json").write_text("[]")
    result = runner.invoke(app, ["export", "--output", str(out), "--deck", "Test"])
    assert result.exit_code == 0, result.output
    assert (out / "Test.apkg").exists()


def test_ingest_with_typing_flag(tmp_path):
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    out = tmp_path / "myout"
    result = runner.invoke(
        app, ["ingest", "--input", str(xlsx), "--lang-target", "en", "--typing", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    cards_data = json.loads((out / "cards.json").read_text())
    assert all(c["typing"] for c in cards_data)


def test_ingest_without_typing_flag(tmp_path):
    xlsx = tmp_path / "vocab.xlsx"
    _create_xlsx(xlsx)
    out = tmp_path / "myout"
    result = runner.invoke(
        app, ["ingest", "--input", str(xlsx), "--lang-target", "en", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    cards_data = json.loads((out / "cards.json").read_text())
    assert not any(c["typing"] for c in cards_data)
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_cli.py -v`
Expected: All 7 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: rewrite CLI tests using typer.testing.CliRunner"
```

---

### Task 5: Final verification and cleanup

**Files:**
- Verify: `src/anki_builder/cli.py`, `tests/test_cli.py`, `pyproject.toml`

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run linter**

Run: `ruff check src/anki_builder/cli.py tests/test_cli.py`
Expected: No errors. If there are, fix them.

- [ ] **Step 3: Verify CLI help output**

Run: `ankids --help`
Expected: Shows all 7 commands with descriptions.

Run: `ankids ingest --help`
Expected: Shows all options for the ingest command.

- [ ] **Step 4: Verify no remaining click references**

Run: `grep -r "import click\|from click\|click\." src/anki_builder/cli.py`
Expected: No matches.

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final cleanup for click-to-typer migration"
```
