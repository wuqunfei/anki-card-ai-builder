import json
from pathlib import Path

from anki_builder.schema import Card

FIELD_MIGRATION = {
    "word": "source_word",
    "translation": "target_word",
    "pronunciation": "target_pronunciation",
    "part_of_speech": "target_part_of_speech",
    "mnemonic": "target_mnemonic",
    "example_sentence": "target_example_sentence",
    "sentence_translation": "source_example_sentence",
}


def _migrate_card_data(item: dict) -> dict:
    """Rename old field names to new names if present."""
    for old_key, new_key in FIELD_MIGRATION.items():
        if old_key in item and new_key not in item:
            item[new_key] = item.pop(old_key)
    return item


class StateManager:
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.cards_file = work_dir / "cards.json"
        self.media_dir = work_dir / "media"
        self.media_dir.mkdir(exist_ok=True)

    def load_cards(self) -> list[Card]:
        if not self.cards_file.exists():
            return []
        data = json.loads(self.cards_file.read_text())
        migrated = False
        for item in data:
            item.pop("source", None)
            if any(old_key in item for old_key in FIELD_MIGRATION):
                _migrate_card_data(item)
                migrated = True
        cards = [Card(**item) for item in data]
        if migrated:
            self.save_cards(cards)
        return cards

    def save_cards(self, cards: list[Card]) -> None:
        data = [card.model_dump() for card in cards]
        self.cards_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def merge_cards(self, new_cards: list[Card], prune: bool = False) -> list[Card]:
        existing = self.load_cards()
        existing_map: dict[tuple[str, str], Card] = {(c.source_word, c.target_language): c for c in existing}

        merged: list[Card] = []
        seen_keys: set[tuple[str, str]] = set()
        for card in new_cards:
            key = (card.source_word, card.target_language)
            seen_keys.add(key)
            if key in existing_map:
                old = existing_map[key]
                update_data = {}
                for field in [
                    "target_word",
                    "target_pronunciation",
                    "target_example_sentence",
                    "source_example_sentence",
                    "target_mnemonic",
                    "target_origin",
                    "target_cognates",
                    "target_memory_hook",
                    "target_part_of_speech",
                    "audio_file",
                    "image_file",
                    "target_example_audio",
                ]:
                    old_val = getattr(old, field)
                    new_val = getattr(card, field)
                    if old_val is not None and new_val is None:
                        update_data[field] = old_val
                if old.typing:
                    update_data["typing"] = old.typing
                update_data["id"] = old.id
                if old.status != "extracted":
                    update_data["status"] = old.status
                merged.append(card.model_copy(update=update_data))
            else:
                merged.append(card)

        if not prune:
            for key, card in existing_map.items():
                if key not in seen_keys:
                    merged.append(card)

        return merged


def finalize_card_status(cards: list[Card], no_images: bool = False, no_audio: bool = False) -> list[Card]:
    updated = []
    for card in cards:
        if card.status in ("extracted", "enriched") and card.audio_file and card.image_file:
            updated.append(card.model_copy(update={"status": "complete"}))
        elif card.status in ("extracted", "enriched") and (no_images or no_audio):
            updated.append(card.model_copy(update={"status": "complete"}))
        else:
            updated.append(card)
    return updated
