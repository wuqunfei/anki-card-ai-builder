import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from anki_builder.ingest.image import ingest_image

TESTS_DIR = Path(__file__).parent
INPUT_DIR = TESTS_DIR / "input"
OUTPUT_DIR = TESTS_DIR / "output"


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

        cards = ingest_image(Path("test.png"), target_language="fr", source_language="de")

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "Apfel")
        self.assertEqual(cards[0].target_word, "pomme")
        self.assertEqual(cards[0].target_pronunciation, "/pɔm/")

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

        cards = ingest_image(Path("test.jpg"), target_language="fr")

        self.assertEqual(len(cards), 2)

    @patch("anki_builder.ingest.image.PIL.Image.open")
    @patch("anki_builder.ingest.image.genai.Client")
    def test_ingest_image_overrides_language(self, mock_client_cls, mock_pil_open):
        mock_client, _ = _mock_client()
        mock_client_cls.return_value = mock_client
        mock_pil_open.return_value = MagicMock()

        cards = ingest_image(Path("test.png"), target_language="zh", source_language="en")

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
            ingest_image(Path("test.png"), target_language="fr")


@unittest.skipUnless(os.environ.get("GOOGLE_API_KEY"), "GOOGLE_API_KEY not set")
class TestIngestImageReal(unittest.TestCase):
    """Integration tests that call the real Gemini API with test images."""

    def _run_folder(self, target_language: str):
        input_folder = INPUT_DIR / target_language
        output_folder = OUTPUT_DIR / target_language
        output_folder.mkdir(parents=True, exist_ok=True)

        image_files = sorted(input_folder.glob("*.heic"))
        self.assertTrue(len(image_files) > 0, f"No .heic files in {input_folder}")

        all_cards = []
        for image_path in image_files:
            cards = ingest_image(
                path=image_path,
                target_language=target_language,
                source_language="de",
            )
            self.assertIsInstance(cards, list)
            for card in cards:
                self.assertEqual(card.target_language, target_language)
                self.assertEqual(card.source_language, "de")
                self.assertTrue(card.source_word, "source_word should not be empty")

            all_cards.extend(cards)

        # Save results as JSON
        output_file = output_folder / "cards.json"
        cards_data = [card.model_dump() for card in all_cards]
        output_file.write_text(json.dumps(cards_data, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"\n{target_language}: extracted {len(all_cards)} cards from {len(image_files)} images -> {output_file}")
        return all_cards

    def test_ingest_english_images(self):
        cards = self._run_folder("english")
        self.assertGreater(len(cards), 0, "Should extract at least one card")

    def test_ingest_french_images(self):
        cards = self._run_folder("french")
        self.assertGreater(len(cards), 0, "Should extract at least one card")


if __name__ == "__main__":
    unittest.main()
