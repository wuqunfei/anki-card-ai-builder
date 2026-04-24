import asyncio
from pathlib import Path

import click

from anki_builder.config import load_config
from anki_builder.schema import Card
from anki_builder.state import StateManager, finalize_card_status
from anki_builder.ingest.excel import ingest_excel
from anki_builder.ingest.pdf import ingest_pdf
from anki_builder.ingest.image import ingest_image
from anki_builder.ingest.gdrive import ingest_gdrive_folder, GDRIVE_URL_PATTERN
from anki_builder.enrich.ai import enrich_cards
from anki_builder.media.audio import generate_audio_batch
from anki_builder.media.image import generate_image_batch
from anki_builder.export.apkg import export_apkg

WORK_DIR = Path("output")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".heic", ".heif"}


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
        raise click.ClickException(f"Unsupported file type: {suffix}")


def _ingest_folder(
    folder: Path,
    target_language: str,
    source_language: str,
    google_api_key: str,
    minimax_api_key: str,
) -> list[Card]:
    supported = IMAGE_EXTENSIONS | {".pdf"}
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in supported)
    if not files:
        raise click.ClickException(f"No supported files found in {folder}")

    all_cards: list[Card] = []
    for f in files:
        suffix = f.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            click.echo(f"  Processing image: {f.name}")
            cards = ingest_image(f, target_language, source_language, google_api_key)
        elif suffix == ".pdf":
            click.echo(f"  Processing PDF: {f.name}")
            cards = ingest_pdf(f, target_language, minimax_api_key, source_language)
        else:
            continue
        all_cards.extend(cards)
    return all_cards


class OrderedGroup(click.Group):
    def list_commands(self, ctx):
        return list(self.commands)

    def format_commands(self, ctx, formatter):
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.commands[subcommand]
            help_text = cmd.get_short_help_str(limit=300)
            commands.append((subcommand, help_text))

        if commands:
            with formatter.section("Commands"):
                formatter.write_dl(commands)


@click.group(cls=OrderedGroup, context_settings={"max_content_width": 200})
def main():
    """anki-builder: Anki Card AI Builder — generate flashcards for language learning."""


@main.command()
@click.option("--input", "input_path", default=None, type=str, help="Input file, folder, or Google Drive URL")
@click.option("--words", "words", default=None, type=str, help='Comma-separated words (e.g. "Glove,Squirrel,impossible")')
@click.option("--lang-target", "target_language", required=True, help="Target language code (en, fr, zh)")
@click.option("--lang-source", "source_language", default="de", help="Source language code (default: de)")
@click.option("--deck", "deck_name", default=None, help="Deck name for export")
@click.option("--no-images", is_flag=True, help="Skip image generation")
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
@click.option("--typing", is_flag=True, help="Create 'type in the answer' cards")
def run(input_path: str | None, words: str | None, target_language: str, source_language: str,
        deck_name: str | None, no_images: bool, no_audio: bool, typing: bool):
    """Run full pipeline: ingest, enrich, media, review (export separately)."""
    if not input_path and not words:
        raise click.ClickException("Provide either --input or --words.")
    if input_path and words:
        raise click.ClickException("Use either --input or --words, not both.")

    config = load_config()
    state = StateManager(WORK_DIR)

    # Validate API keys
    config.require_minimax_key()

    # Ingest
    if words:
        cards = _words_to_cards(words, target_language, source_language, typing)
        click.echo(f"Step 1/4: Ingesting {len(cards)} words from command line...")
    else:
        input_type = _detect_input_type(input_path)
        if input_type in ("image", "folder", "gdrive"):
            config.require_google_key()
        click.echo(f"Step 1/4: Ingesting {input_path}...")
        if input_type == "gdrive":
            cards = ingest_gdrive_folder(input_path, target_language, config.google_api_key, config.minimax_api_key, source_language)
        elif input_type == "excel":
            path = Path(input_path)
            cards = ingest_excel(path, target_language, source_language)
        elif input_type == "pdf":
            path = Path(input_path)
            cards = ingest_pdf(path, target_language, config.minimax_api_key, source_language)
        elif input_type == "image":
            path = Path(input_path)
            cards = ingest_image(path, target_language, source_language, config.google_api_key)
        elif input_type == "folder":
            cards = _ingest_folder(Path(input_path), target_language, source_language, config.google_api_key, config.minimax_api_key)

    if typing:
        cards = [c.model_copy(update={"typing": True}) for c in cards]

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    click.echo(f"  Extracted {len(cards)} cards. Total: {len(merged)}.")

    # Enrich
    to_enrich = [c for c in merged if c.status == "extracted"]
    if to_enrich:
        click.echo(f"Step 2/4: Enriching {len(to_enrich)} of {len(merged)} cards with AI...")
        enriched = enrich_cards(merged, config.minimax_api_key)
        state.save_cards(enriched)
        click.echo("  Enrichment complete.")
    else:
        enriched = merged
        click.echo(f"Step 2/4: All {len(merged)} cards already enriched, skipping.")

    # Media
    need_audio = [c for c in enriched if not c.audio_file]
    need_image = [c for c in enriched if not c.image_file]

    if (need_audio or need_image) and not (no_audio and no_images):
        click.echo("Step 3/4: Generating media...")
        if not no_audio and config.audio_enabled and need_audio:
            click.echo(f"  Generating audio for {len(need_audio)} cards ({len(enriched) - len(need_audio)} already done)...")
            enriched = generate_audio_batch(enriched, state.media_dir)
        elif not no_audio and config.audio_enabled:
            click.echo(f"  Audio: all {len(enriched)} cards already have audio, skipping.")

        if not no_images and config.image_enabled and need_image:
            click.echo(f"  Generating images for {len(need_image)} cards ({len(enriched) - len(need_image)} already done)...")
            enriched = asyncio.run(generate_image_batch(
                enriched, state.media_dir, config.minimax_api_key, config.concurrency,
            ))
        elif not no_images and config.image_enabled:
            click.echo(f"  Images: all {len(enriched)} cards already have images, skipping.")

        click.echo("  Media complete.")
    else:
        click.echo(f"Step 3/4: All {len(enriched)} cards already have media, skipping.")

    updated = finalize_card_status(enriched, no_images, no_audio)
    state.save_cards(updated)

    # Review prompt
    click.echo(f"\nStep 4/4: Review your cards and media.")
    click.echo(f"  Media folder: {state.media_dir.resolve()}")
    click.echo(f"  Cards: {len(updated)}")
    click.echo(f"\nRun 'anki-builder review' to see card details.")
    name = deck_name or config.default_deck_name
    click.echo(f"When ready, run: anki-builder export --deck \"{name}\"")


@main.command()
@click.option("--input", "input_path", default=None, type=str, help="Input file, folder, or Google Drive URL")
@click.option("--words", "words", default=None, type=str, help="Comma-separated words (e.g. \"Glove,Squirrel,impossible\")")
@click.option("--lang-target", "target_language", required=True, help="Target language code (en, fr, zh)")
@click.option("--lang-source", "source_language", default="de", help="Source language code (default: de)")
@click.option("--typing", is_flag=True, help="Create 'type in the answer' cards")
def ingest(input_path: str | None, words: str | None, target_language: str, source_language: str, typing: bool):
    """Step 1: Extract vocabulary from a file, folder, URL, or word list."""
    if not input_path and not words:
        raise click.ClickException("Provide either --input or --words.")
    if input_path and words:
        raise click.ClickException("Use either --input or --words, not both.")

    config = load_config()
    state = StateManager(WORK_DIR)

    if words:
        cards = _words_to_cards(words, target_language, source_language)
        click.echo(f"Ingesting {len(cards)} words from command line...")
    else:
        input_type = _detect_input_type(input_path)

        click.echo(f"Ingesting {input_path} as {input_type}...")
        if input_type in ("image", "folder", "gdrive"):
            config.require_google_key()
        if input_type in ("pdf", "gdrive"):
            config.require_minimax_key()

        if input_type == "gdrive":
            cards = ingest_gdrive_folder(input_path, target_language, config.google_api_key, config.minimax_api_key, source_language)
        elif input_type == "excel":
            path = Path(input_path)
            cards = ingest_excel(path, target_language, source_language)
        elif input_type == "pdf":
            path = Path(input_path)
            cards = ingest_pdf(path, target_language, config.minimax_api_key, source_language)
        elif input_type == "image":
            path = Path(input_path)
            cards = ingest_image(path, target_language, source_language, config.google_api_key)
        elif input_type == "folder":
            cards = _ingest_folder(Path(input_path), target_language, source_language, config.google_api_key, config.minimax_api_key)

    if typing:
        cards = [c.model_copy(update={"typing": True}) for c in cards]

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    click.echo(f"Extracted {len(cards)} cards. Total: {len(merged)} cards.")


@main.command()
def enrich():
    """Step 2: Fill missing card fields (translation, pronunciation, examples) using AI."""
    config = load_config()
    config.require_minimax_key()
    state = StateManager(WORK_DIR)

    cards = state.load_cards()
    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    to_enrich = [c for c in cards if c.status == "extracted"]
    if not to_enrich:
        click.echo(f"All {len(cards)} cards already enriched, nothing to do.")
        return

    click.echo(f"Enriching {len(to_enrich)} of {len(cards)} cards ({len(cards) - len(to_enrich)} already done)...")
    enriched = enrich_cards(cards, config.minimax_api_key)
    state.save_cards(enriched)
    click.echo(f"Enrichment complete.")


@main.command()
@click.option("--no-images", is_flag=True, help="Skip image generation")
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
def media(no_images: bool, no_audio: bool):
    """Step 3: Generate TTS audio and AI images for cards."""
    config = load_config()
    if not no_images and config.image_enabled:
        config.require_minimax_key()
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    need_audio = [c for c in cards if not c.audio_file]
    need_image = [c for c in cards if not c.image_file]

    if not no_audio and config.audio_enabled:
        if need_audio:
            click.echo(f"Generating audio for {len(need_audio)} cards ({len(cards) - len(need_audio)} already done)...")
            cards = generate_audio_batch(cards, state.media_dir)
        else:
            click.echo(f"Audio: all {len(cards)} cards already have audio, skipping.")

    if not no_images and config.image_enabled:
        if need_image:
            click.echo(f"Generating images for {len(need_image)} cards ({len(cards) - len(need_image)} already done)...")
            cards = asyncio.run(generate_image_batch(
                cards, state.media_dir, config.minimax_api_key, config.concurrency,
            ))
        else:
            click.echo(f"Images: all {len(cards)} cards already have images, skipping.")

    updated = finalize_card_status(cards, no_images, no_audio)
    state.save_cards(updated)
    click.echo("Media generation complete.")


@main.command()
def review():
    """Step 4: Show all cards and media status for review before export."""
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    click.echo(f"\n{len(cards)} cards ready for review.\n")
    click.echo(f"Media folder: {state.media_dir.resolve()}\n")

    for i, card in enumerate(cards, 1):
        click.echo(f"[{i}] {card.source_word}")
        click.echo(f"    Target Word:    {card.target_word or '(missing)'}")
        click.echo(f"    Pronunciation:  {card.target_pronunciation or '(missing)'}")
        click.echo(f"    Example:        {card.target_example_sentence or '(missing)'}")
        click.echo(f"    Mnemonic:       {card.target_mnemonic or '(missing)'}")
        click.echo(f"    Audio:          {'✓' if card.audio_file else '✗'}")
        click.echo(f"    Image:          {'✓' if card.image_file else '✗'}")
        click.echo()

    click.echo(f"Review images and audio in: {state.media_dir.resolve()}")
    click.echo("When ready, run: anki-builder export --deck \"Your Deck Name\"")


@main.command()
@click.option("--deck", "deck_name", default=None, help="Deck name (default: Vocabulary)")
@click.option("--output", "output_path", default=None, help="Output .apkg file path")
@click.option("--prune", is_flag=True, help="Remove cards not in current source")
def export(deck_name: str | None, output_path: str | None, prune: bool):
    """Step 5: Export cards with media to an Anki .apkg file."""
    config = load_config()
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    name = deck_name or config.default_deck_name
    out = Path(output_path) if output_path else WORK_DIR / f"{name}.apkg"

    click.echo(f"Exporting {len(cards)} cards to {out}...")
    export_apkg(cards, out, name)
    click.echo(f"Done! Created {out}")


@main.command()
@click.confirmation_option(prompt="This will delete all cards, media, and exported files in output/. Continue?")
def clean():
    """Remove the output/ folder (cards, media, .apkg) to start fresh."""
    import shutil

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
        click.echo(f"Removed {WORK_DIR}/")
    else:
        click.echo("Nothing to clean.")


