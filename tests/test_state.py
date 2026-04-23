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
            Card(source_word="dog", target_language="en", source="test.xlsx"),
            Card(source_word="chat", target_language="fr", source="test.xlsx"),
        ]
        self.state.save_cards(cards)
        loaded = self.state.load_cards()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].source_word, "dog")
        self.assertEqual(loaded[1].source_word, "chat")

    def test_load_empty_returns_empty_list(self):
        loaded = self.state.load_cards()
        self.assertEqual(loaded, [])

    def test_merge_new_cards(self):
        existing = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
            Card(source_word="cat", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].id, existing[0].id)
        self.assertEqual(merged[1].source_word, "cat")

    def test_merge_preserves_enriched_fields(self):
        existing = [
            Card(
                source_word="dog",
                target_language="en",
                source="test.xlsx",
                target_word="Hund",
                status="enriched",
            ),
        ]
        self.state.save_cards(existing)

        new_cards = [
            Card(source_word="dog", target_language="en", source="test.xlsx"),
        ]
        merged = self.state.merge_cards(new_cards)
        self.assertEqual(merged[0].target_word, "Hund")
        self.assertEqual(merged[0].status, "enriched")

    def test_media_dir_created(self):
        media_dir = self.state.media_dir
        self.assertTrue(media_dir.exists())
        self.assertTrue(media_dir.is_dir())

    def test_migrate_old_field_names(self):
        """Loading cards.json with old field names auto-migrates them."""
        old_data = [
            {
                "id": "test-id",
                "word": "dog",
                "source_language": "de",
                "target_language": "en",
                "translation": "Hund",
                "pronunciation": "/dɒɡ/",
                "part_of_speech": "noun",
                "mnemonic": "<span>test</span>",
                "example_sentence": "The dog plays.",
                "sentence_translation": "Der Hund spielt.",
                "tags": [],
                "audio_file": None,
                "image_file": None,
                "source": "test.xlsx",
                "status": "enriched",
            }
        ]
        self.state.cards_file.write_text(json.dumps(old_data))
        loaded = self.state.load_cards()
        self.assertEqual(len(loaded), 1)
        card = loaded[0]
        self.assertEqual(card.source_word, "dog")
        self.assertEqual(card.target_word, "Hund")
        self.assertEqual(card.target_pronunciation, "/dɒɡ/")
        self.assertEqual(card.target_part_of_speech, "noun")
        self.assertEqual(card.target_mnemonic, "<span>test</span>")
        self.assertEqual(card.target_example_sentence, "The dog plays.")
        self.assertEqual(card.source_example_sentence, "Der Hund spielt.")

    def test_migration_writes_back(self):
        """After migration, cards.json uses new field names."""
        old_data = [
            {
                "id": "test-id",
                "word": "dog",
                "source_language": "de",
                "target_language": "en",
                "translation": "Hund",
                "source": "test.xlsx",
                "status": "extracted",
                "tags": [],
                "audio_file": None,
                "image_file": None,
                "pronunciation": None,
                "part_of_speech": None,
                "mnemonic": None,
                "example_sentence": None,
                "sentence_translation": None,
            }
        ]
        self.state.cards_file.write_text(json.dumps(old_data))
        self.state.load_cards()
        raw = json.loads(self.state.cards_file.read_text())
        self.assertIn("source_word", raw[0])
        self.assertNotIn("word", raw[0])
        self.assertIn("target_word", raw[0])
        self.assertNotIn("translation", raw[0])


if __name__ == "__main__":
    unittest.main()
