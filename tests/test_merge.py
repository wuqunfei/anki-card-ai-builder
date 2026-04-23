import tempfile
import unittest
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.state import StateManager
from anki_builder.export.merge import merge_and_export


class TestMerge(unittest.TestCase):
    def test_merge_new_cards_into_existing_deck(self):
        tmpdir = tempfile.mkdtemp()
        state = StateManager(Path(tmpdir) / ".anki-builder")

        cards_v1 = [
            Card(id="id-1", source_word="dog", target_language="en", source="v1",
                 target_word="Hund", status="enriched"),
            Card(id="id-2", source_word="cat", target_language="en", source="v1",
                 target_word="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        new_cards = [
            Card(source_word="dog", target_language="en", source="v2"),
            Card(source_word="bird", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards)
        self.assertEqual(len(merged), 3)
        dog = next(c for c in merged if c.source_word == "dog")
        self.assertEqual(dog.id, "id-1")
        self.assertEqual(dog.target_word, "Hund")
        bird = next(c for c in merged if c.source_word == "bird")
        self.assertIsNone(bird.target_word)
        cat = next(c for c in merged if c.source_word == "cat")
        self.assertEqual(cat.target_word, "Katze")

    def test_merge_with_prune(self):
        tmpdir = tempfile.mkdtemp()
        state = StateManager(Path(tmpdir) / ".anki-builder")

        cards_v1 = [
            Card(id="id-1", source_word="dog", target_language="en", source="v1",
                 target_word="Hund", status="enriched"),
            Card(id="id-2", source_word="cat", target_language="en", source="v1",
                 target_word="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        new_cards = [
            Card(source_word="dog", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards, prune=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].source_word, "dog")


if __name__ == "__main__":
    unittest.main()
