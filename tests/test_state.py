import json
import tempfile
import unittest
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.state import StateManager


class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state = StateManager(Path(self.tmpdir))

    def test_save_and_load_cards(self):
        cards = [
            Card(word="dog", target_language="en", source="test.xlsx"),
            Card(word="chat", target_language="fr", source="test.xlsx"),
        ]
        self.state.save_cards(cards)
        loaded = self.state.load_cards()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].word, "dog")
        self.assertEqual(loaded[1].word, "chat")

    def test_load_empty_returns_empty_list(self):
        loaded = self.state.load_cards()
        self.assertEqual(loaded, [])

    def test_merge_new_cards(self):
        existing = [
            Card(word="dog", target_language="en", source="test.xlsx"),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(word="dog", target_language="en", source="test.xlsx"),
            Card(word="cat", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(len(merged), 2)
        # Existing card keeps its ID
        self.assertEqual(merged[0].id, existing[0].id)
        # New card gets added
        self.assertEqual(merged[1].word, "cat")

    def test_merge_preserves_enriched_fields(self):
        existing = [
            Card(
                word="dog",
                target_language="en",
                source="test.xlsx",
                translation="Hund",
                status="enriched",
            ),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(word="dog", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(merged[0].translation, "Hund")
        self.assertEqual(merged[0].status, "enriched")

    def test_media_dir_created(self):
        media_dir = self.state.media_dir
        self.assertTrue(media_dir.exists())
        self.assertTrue(media_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
