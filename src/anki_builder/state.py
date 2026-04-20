import json
from pathlib import Path

from anki_builder.schema import Card


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
        return [Card(**item) for item in data]

    def save_cards(self, cards: list[Card]) -> None:
        data = [card.model_dump() for card in cards]
        self.cards_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def merge_cards(self, new_cards: list[Card], prune: bool = False) -> list[Card]:
        existing = self.load_cards()
        existing_map: dict[tuple[str, str], Card] = {
            (c.word, c.target_language): c for c in existing
        }

        merged: list[Card] = []
        seen_keys: set[tuple[str, str]] = set()
        for card in new_cards:
            key = (card.word, card.target_language)
            seen_keys.add(key)
            if key in existing_map:
                old = existing_map[key]
                update_data = {}
                for field in ["translation", "pronunciation", "example_sentence",
                              "sentence_translation", "mnemonic", "part_of_speech",
                              "audio_file", "image_file"]:
                    old_val = getattr(old, field)
                    new_val = getattr(card, field)
                    if old_val is not None and new_val is None:
                        update_data[field] = old_val
                update_data["id"] = old.id
                if old.status != "extracted":
                    update_data["status"] = old.status
                merged.append(card.model_copy(update=update_data))
            else:
                merged.append(card)

        # Keep cards not in new set (unless pruning)
        if not prune:
            for key, card in existing_map.items():
                if key not in seen_keys:
                    merged.append(card)

        return merged
