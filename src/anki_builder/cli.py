import asyncio
from pathlib import Path

import click

from anki_builder.config import load_config
from anki_builder.schema import Card
from anki_builder.state import StateManager
from anki_builder.ingest.excel import ingest_excel
from anki_builder.ingest.pdf import ingest_pdf
from anki_builder.ingest.image import ingest_image
from anki_builder.enrich.ai import enrich_cards
from anki_builder.media.audio import generate_audio_batch
from anki_builder.media.image import generate_image_batch
from anki_builder.export.apkg import export_apkg

WORK_DIR = Path(".anki-builder")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _detect_input_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".csv"):
        return "excel"
    elif suffix == ".pdf":
        return "pdf"
    elif suffix in IMAGE_EXTENSIONS:
        return "image"
    else:
        raise click.ClickException(f"Unsupported file type: {suffix}")


@click.group()
def main():
    """anki-builder: Anki Card AI Builder — generate flashcards for language learning."""
    pass


@main.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Input file path")
@click.option("--lang", "target_language", required=True, help="Target language code (en, fr, zh)")
@click.option("--source-lang", "source_language", default=None, help="Source language code (default: from config)")
@click.option("--column-map", type=str, default=None, help="Column mapping as key=value pairs, comma-separated")
def ingest(input_path: str, target_language: str, source_language: str | None, column_map: str | None):
    """Extract vocabulary from input files."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    src_lang = source_language or config.default_source_language
    path = Path(input_path)
    input_type = _detect_input_type(path)

    col_map = None
    if column_map:
        col_map = dict(pair.split("=") for pair in column_map.split(","))

    click.echo(f"Ingesting {path.name} as {input_type}...")

    if input_type == "excel":
        cards = ingest_excel(path, target_language, src_lang, col_map)
    elif input_type == "pdf":
        cards = ingest_pdf(path, target_language, config.deepseek_api_key, src_lang)
    elif input_type == "image":
        cards = ingest_image(path, target_language, config.deepseek_api_key, src_lang)

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    click.echo(f"Extracted {len(cards)} cards. Total: {len(merged)} cards.")


@main.command()
@click.option("--source-lang", "source_language", default=None, help="Source language override")
def enrich(source_language: str | None):
    """Fill missing card fields using AI."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    src_lang = source_language or config.default_source_language

    cards = state.load_cards()
    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    to_enrich = [c for c in cards if c.status == "extracted"]
    click.echo(f"Enriching {len(to_enrich)} of {len(cards)} cards...")

    enriched = enrich_cards(cards, config.minimax_api_key, src_lang)
    state.save_cards(enriched)
    click.echo(f"Enrichment complete.")


@main.command()
@click.option("--no-images", is_flag=True, help="Skip image generation")
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
def media(no_images: bool, no_audio: bool):
    """Generate audio and images for cards."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    if not cards:
        click.echo("No cards found. Run 'ingest' first.")
        return

    if not no_audio and config.media.audio_enabled:
        click.echo(f"Generating audio for {len(cards)} cards...")
        cards = asyncio.run(generate_audio_batch(
            cards, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))

    if not no_images and config.media.image_enabled:
        click.echo(f"Generating images for {len(cards)} cards...")
        cards = asyncio.run(generate_image_batch(
            cards, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))

    # Update status to complete for cards that have both media
    updated = []
    for card in cards:
        if card.status == "enriched" and card.audio_file and card.image_file:
            updated.append(card.model_copy(update={"status": "complete"}))
        elif card.status == "enriched" and (no_images or no_audio):
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)

    state.save_cards(updated)
    click.echo("Media generation complete.")


@main.command()
@click.option("--deck", "deck_name", default=None, help="Deck name")
@click.option("--output", "output_path", default=None, help="Output .apkg file path")
@click.option("--prune", is_flag=True, help="Remove cards not in current source")
def export(deck_name: str | None, output_path: str | None, prune: bool):
    """Export cards to .apkg file."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    cards = state.load_cards()

    name = deck_name or config.export.default_deck_name
    out = Path(output_path) if output_path else Path(config.export.output_dir) / f"{name}.apkg"

    click.echo(f"Exporting {len(cards)} cards to {out}...")
    export_apkg(cards, out, name)
    click.echo(f"Done! Created {out}")


@main.command()
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--lang", "target_language", required=True)
@click.option("--deck", "deck_name", default=None)
@click.option("--no-images", is_flag=True)
@click.option("--no-audio", is_flag=True)
@click.option("--source-lang", "source_language", default=None)
def run(input_path: str, target_language: str, deck_name: str | None,
        no_images: bool, no_audio: bool, source_language: str | None):
    """Run full pipeline: ingest → enrich → media → export."""
    config = load_config(WORK_DIR)
    state = StateManager(WORK_DIR)
    src_lang = source_language or config.default_source_language
    path = Path(input_path)
    input_type = _detect_input_type(path)

    # Ingest
    click.echo(f"Step 1/4: Ingesting {path.name}...")
    if input_type == "excel":
        cards = ingest_excel(path, target_language, src_lang)
    elif input_type == "pdf":
        cards = ingest_pdf(path, target_language, config.deepseek_api_key, src_lang)
    elif input_type == "image":
        cards = ingest_image(path, target_language, config.deepseek_api_key, src_lang)

    merged = state.merge_cards(cards)
    state.save_cards(merged)
    click.echo(f"  Extracted {len(cards)} cards. Total: {len(merged)}.")

    # Enrich
    click.echo("Step 2/4: Enriching cards with AI...")
    enriched = enrich_cards(merged, config.minimax_api_key, src_lang)
    state.save_cards(enriched)
    click.echo("  Enrichment complete.")

    # Media
    click.echo("Step 3/4: Generating media...")
    if not no_audio and config.media.audio_enabled:
        enriched = asyncio.run(generate_audio_batch(
            enriched, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))
    if not no_images and config.media.image_enabled:
        enriched = asyncio.run(generate_image_batch(
            enriched, state.media_dir, config.minimax_api_key, config.media.concurrency,
        ))

    updated = []
    for card in enriched:
        if card.status == "enriched":
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)
    state.save_cards(updated)
    click.echo("  Media complete.")

    # Export
    name = deck_name or config.export.default_deck_name
    out = Path(config.export.output_dir) / f"{name}.apkg"
    click.echo(f"Step 4/4: Exporting to {out}...")
    export_apkg(updated, out, name)
    click.echo(f"Done! Created {out} with {len(updated)} cards.")
