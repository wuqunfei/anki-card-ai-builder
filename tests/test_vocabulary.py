import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.enrich.vocabulary import (
    extract_vocabulary_with_ai,
    _build_text_prompt,
    _parse_vocabulary_response,
)


class TestVocabularyExtraction(unittest.TestCase):
    def test_build_text_prompt(self):
        prompt = _build_text_prompt(
            text="dog - Hund\ncat - Katze",
            target_language="en",
            source_language="de",
        )
        self.assertIn("dog", prompt)
        self.assertIn("en", prompt)
        self.assertIn("JSON", prompt)

    def test_parse_vocabulary_response(self):
        response_text = json.dumps([
            {"word": "dog", "translation": "Hund"},
            {"word": "cat", "translation": "Katze"},
        ])
        items = _parse_vocabulary_response(response_text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["word"], "dog")
        self.assertEqual(items[1]["translation"], "Katze")

    def test_parse_response_with_markdown_code_block(self):
        response_text = '```json\n[{"word": "dog", "translation": "Hund"}]\n```'
        items = _parse_vocabulary_response(response_text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["word"], "dog")

    @patch("anki_builder.enrich.vocabulary.anthropic.Anthropic")
    def test_extract_vocabulary_with_text(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_block = MagicMock()
        mock_block.text = json.dumps([{"word": "dog", "translation": "Hund"}])
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        items = extract_vocabulary_with_ai(
            text="dog - Hund",
            target_language="en",
            source_language="de",
            minimax_api_key="test-key",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["word"], "dog")
        mock_client.messages.create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
