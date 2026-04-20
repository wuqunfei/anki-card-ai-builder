from pathlib import Path

from anki_builder.schema import Card
from anki_builder.state import StateManager
from anki_builder.export.apkg import export_apkg


def merge_and_export(
    new_cards: list[Card],
    work_dir: Path,
    output_path: Path,
    deck_name: str = "Vocabulary",
    prune: bool = False,
) -> list[Card]:
    state = StateManager(work_dir)
    merged = state.merge_cards(new_cards, prune=prune)
    state.save_cards(merged)
    export_apkg(merged, output_path, deck_name)
    return merged
