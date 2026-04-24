import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.schema import Card
from anki_builder.enrich.ai import enrich_cards, _build_enrichment_prompt, _batch_cards


class TestAIEnrichment(unittest.TestCase):
    def test_build_enrichment_prompt(self):
        cards = [
            Card(source_word="dog", target_language="en"),
        ]
        prompt = _build_enrichment_prompt(cards)
        self.assertIn("dog", prompt)
        self.assertIn("source_language", prompt)
        self.assertIn("target_language", prompt)
        self.assertIn("kid-friendly", prompt.lower())
        self.assertIn("emoji", prompt.lower())
        self.assertIn("target_mnemonic", prompt)
        self.assertIn("JSON", prompt)

    def test_batch_cards(self):
        cards = [Card(source_word=f"word{i}", target_language="en") for i in range(45)]
        batches = _batch_cards(cards, batch_size=20)
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0]), 20)
        self.assertEqual(len(batches[1]), 20)
        self.assertEqual(len(batches[2]), 5)

    def test_already_enriched_cards_skipped(self):
        cards = [
            Card(source_word="dog", target_language="en", status="enriched"),
            Card(source_word="cat", target_language="en", status="extracted"),
        ]
        to_enrich = [c for c in cards if c.status == "extracted"]
        self.assertEqual(len(to_enrich), 1)
        self.assertEqual(to_enrich[0].source_word, "cat")

    @patch("anki_builder.enrich.ai.anthropic")
    def test_enrich_cards(self, mock_anthropic_module):
        mock_client = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        enriched_data = json.dumps([{
            "source_word": "dog",
            "target_word": "Hund",
            "target_pronunciation": "/dɒɡ/",
            "target_example_sentence": "The dog loves to play in the park! 🐕",
            "source_example_sentence": "Der Hund spielt gern im Park! 🐕",
            "target_mnemonic": '<span style="color:red">dog</span>',
            "target_part_of_speech": "noun",
        }])

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=enriched_data)]
        mock_client.messages.create.return_value = mock_response

        cards = [Card(source_word="dog", target_language="en")]
        result = enrich_cards(cards, minimax_api_key="test-key")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_word, "Hund")
        self.assertEqual(result[0].target_pronunciation, "/dɒɡ/")
        self.assertIn("🐕", result[0].target_example_sentence)
        self.assertIn("🐕", result[0].source_example_sentence)
        self.assertIn("color:red", result[0].target_mnemonic)
        self.assertEqual(result[0].target_part_of_speech, "noun")
        self.assertEqual(result[0].status, "enriched")


if __name__ == "__main__":
    unittest.main()
