import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from anki_builder.ingest.image import ingest_image


SAMPLE_GEMINI_RESPONSE = json.dumps({
    "cards": [
        {
            "id": "ignored-id",
            "unit": "Unité 1",
            "reference": "Page 12",
            "status": "extracted",
            "tags": ["food"],
            "audio_file": None,
            "image_file": None,
            "source_word": "Apfel",
            "source_language": "de",
            "source_gender": "m",
            "source_example_sentence": "Ich esse einen Apfel 🍎",
            "target_word": "pomme",
            "target_language": "fr",
            "target_gender": "f",
            "target_pronunciation": "/pɔm/",
            "target_part_of_speech": "noun",
            "target_example_sentence": "Je mange une pomme 🍎",
            "target_synonyms": None,
            "target_antonyms": None,
            "target_mnemonic": None,
        },
        {
            "source_word": "Katze",
            "target_word": "chat",
            "target_language": "fr",
            "source_language": "de",
            "unit": "Unité 1",
            "reference": "Page 12",
            "tags": ["animals"],
            "target_pronunciation": "/ʃa/",
            "target_part_of_speech": "noun",
            "target_example_sentence": "Le chat dort 🐱",
        },
    ]
})


def _mock_client():
    """Create a mock genai.Client with models.generate_content."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = SAMPLE_GEMINI_RESPONSE
    mock_client.models.generate_content.return_value = mock_response
    return mock_client, mock_response


class TestIngestImage(unittest.TestCase):
    @patch("anki_builder.ingest.image.PIL.Image.open")
    @patch("anki_builder.ingest.image.genai.Client")
    def test_ingest_image_returns_cards(self, mock_client_cls, mock_pil_open):
        mock_client, _ = _mock_client()
        mock_client_cls.return_value = mock_client
        mock_pil_open.return_value = MagicMock()

        cards = ingest_image(
            Path("test.png"),
            target_language="fr",
            minimax_api_key="test-key",
            source_language="de",
        )

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "Apfel")
        self.assertEqual(cards[0].target_word, "pomme")
        self.assertEqual(cards[0].target_pronunciation, "/pɔm/")
        self.assertEqual(cards[0].source, "test.png")
        self.assertEqual(cards[0].source_language, "de")
        self.assertEqual(cards[0].target_language, "fr")
        # id should be auto-generated, not the one from Gemini
        self.assertNotEqual(cards[0].id, "ignored-id")

        self.assertEqual(cards[1].source_word, "Katze")
        self.assertEqual(cards[1].target_word, "chat")

        mock_client_cls.assert_called_once()

    @patch("anki_builder.ingest.image.PIL.Image.open")
    @patch("anki_builder.ingest.image.genai.Client")
    def test_ingest_image_handles_code_fence(self, mock_client_cls, mock_pil_open):
        mock_client, mock_response = _mock_client()
        mock_response.text = f"```json\n{SAMPLE_GEMINI_RESPONSE}\n```"
        mock_client_cls.return_value = mock_client
        mock_pil_open.return_value = MagicMock()

        cards = ingest_image(
            Path("test.jpg"),
            target_language="fr",
            minimax_api_key="test-key",
        )

        self.assertEqual(len(cards), 2)

    @patch("anki_builder.ingest.image.PIL.Image.open")
    @patch("anki_builder.ingest.image.genai.Client")
    def test_ingest_image_overrides_language(self, mock_client_cls, mock_pil_open):
        mock_client, _ = _mock_client()
        mock_client_cls.return_value = mock_client
        mock_pil_open.return_value = MagicMock()

        cards = ingest_image(
            Path("test.png"),
            target_language="zh",
            minimax_api_key="test-key",
            source_language="en",
        )

        # Language params override whatever Gemini returned
        for card in cards:
            self.assertEqual(card.target_language, "zh")
            self.assertEqual(card.source_language, "en")

    @patch("anki_builder.ingest.image.PIL.Image.open")
    @patch("anki_builder.ingest.image.genai.Client")
    def test_ingest_image_invalid_json_raises(self, mock_client_cls, mock_pil_open):
        mock_client, mock_response = _mock_client()
        mock_response.text = "not valid json"
        mock_client_cls.return_value = mock_client
        mock_pil_open.return_value = MagicMock()

        with self.assertRaises(json.JSONDecodeError):
            ingest_image(
                Path("test.png"),
                target_language="fr",
                minimax_api_key="test-key",
            )


if __name__ == "__main__":
    unittest.main()
