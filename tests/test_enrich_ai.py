import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.schema import Card
from anki_builder.enrich.ai import enrich_cards, _build_enrichment_prompt, _batch_cards


class TestAIEnrichment(unittest.TestCase):
    def test_build_enrichment_prompt(self):
        cards = [
            Card(word="dog", target_language="en", source="test"),
        ]
        prompt = _build_enrichment_prompt(cards, source_language="de")
        self.assertIn("dog", prompt)
        self.assertIn("kid-friendly", prompt.lower())
        self.assertIn("emoji", prompt.lower())
        self.assertIn("mnemonic", prompt.lower())
        self.assertIn("JSON", prompt)

    def test_batch_cards(self):
        cards = [Card(word=f"word{i}", target_language="en", source="test") for i in range(45)]
        batches = _batch_cards(cards, batch_size=20)
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0]), 20)
        self.assertEqual(len(batches[1]), 20)
        self.assertEqual(len(batches[2]), 5)

    def test_already_enriched_cards_skipped(self):
        cards = [
            Card(word="dog", target_language="en", source="test", status="enriched"),
            Card(word="cat", target_language="en", source="test", status="extracted"),
        ]
        to_enrich = [c for c in cards if c.status == "extracted"]
        self.assertEqual(len(to_enrich), 1)
        self.assertEqual(to_enrich[0].word, "cat")

    @patch("anki_builder.enrich.ai.anthropic")
    def test_enrich_cards(self, mock_anthropic_module):
        mock_client = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        enriched_data = json.dumps([{
            "word": "dog",
            "translation": "Hund",
            "pronunciation": "/dɒɡ/",
            "example_sentence": "The dog loves to play in the park! 🐕",
            "sentence_translation": "Der Hund spielt gern im Park! 🐕",
            "mnemonic": '<span style="color:red">dog</span>',
            "part_of_speech": "noun",
        }])

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=enriched_data)]
        mock_client.messages.create.return_value = mock_response

        cards = [Card(word="dog", target_language="en", source="test")]
        result = enrich_cards(cards, minimax_api_key="test-key", source_language="de")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].translation, "Hund")
        self.assertEqual(result[0].pronunciation, "/dɒɡ/")
        self.assertIn("🐕", result[0].example_sentence)
        self.assertIn("🐕", result[0].sentence_translation)
        self.assertIn("color:red", result[0].mnemonic)
        self.assertEqual(result[0].part_of_speech, "noun")
        self.assertEqual(result[0].status, "enriched")


if __name__ == "__main__":
    unittest.main()
