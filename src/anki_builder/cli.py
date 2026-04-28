import asyncio
import uuid
from pathlib import Path
from typing import Optional

import typer

from anki_builder.config import Config, load_config
from anki_builder.constants import IMAGE_EXTENSIONS, STATUS_EXTRACTED
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


def _words_to_cards(words_str: str, target_language: str, source_language: str, typing: bool = False) -> list[Card]:
    words = [w.strip() for w in words_str.split(",") if w.strip()]
    return [
        Card(source_word=w, target_language=target_language, source_language=source_language, typing=typing)
        for w in words
    ]


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


def main():
    app()
