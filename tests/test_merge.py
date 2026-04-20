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

        # First run: save 2 cards
        cards_v1 = [
            Card(id="id-1", word="dog", target_language="en", source="v1",
                 translation="Hund", status="enriched"),
            Card(id="id-2", word="cat", target_language="en", source="v1",
                 translation="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        # Second run: new extraction has dog + bird (cat removed, bird added)
        new_cards = [
            Card(word="dog", target_language="en", source="v2"),
            Card(word="bird", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards)
        self.assertEqual(len(merged), 3)  # dog + bird + cat (kept by default)
        # dog keeps old ID and enriched data
        dog = next(c for c in merged if c.word == "dog")
        self.assertEqual(dog.id, "id-1")
        self.assertEqual(dog.translation, "Hund")
        # bird is new
        bird = next(c for c in merged if c.word == "bird")
        self.assertIsNone(bird.translation)
        # cat is kept from existing (not pruned by default)
        cat = next(c for c in merged if c.word == "cat")
        self.assertEqual(cat.translation, "Katze")

    def test_merge_with_prune(self):
        tmpdir = tempfile.mkdtemp()
        state = StateManager(Path(tmpdir) / ".anki-builder")

        cards_v1 = [
            Card(id="id-1", word="dog", target_language="en", source="v1",
                 translation="Hund", status="enriched"),
            Card(id="id-2", word="cat", target_language="en", source="v1",
                 translation="Katze", status="enriched"),
        ]
        state.save_cards(cards_v1)

        new_cards = [
            Card(word="dog", target_language="en", source="v2"),
        ]

        merged = state.merge_cards(new_cards, prune=True)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].word, "dog")


if __name__ == "__main__":
    unittest.main()
