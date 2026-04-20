import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pymupdf

from anki_builder.ingest.pdf import ingest_pdf, extract_text_from_pdf


class TestPdfTextExtraction(unittest.TestCase):
    def _create_pdf_with_text(self, text: str, path: Path) -> Path:
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), text)
        doc.save(str(path))
        doc.close()
        return path

    def test_extract_text_from_digital_pdf(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_pdf_with_text(
            "dog - Hund\ncat - Katze\nbird - Vogel",
            Path(tmpdir) / "vocab.pdf",
        )
        text = extract_text_from_pdf(path)
        self.assertIn("dog", text)
        self.assertIn("Hund", text)

    @patch("anki_builder.ingest.pdf.extract_vocabulary_with_ai")
    def test_ingest_pdf_calls_ai_extraction(self, mock_ai):
        mock_ai.return_value = [
            {"word": "dog", "translation": "Hund"},
            {"word": "cat", "translation": "Katze"},
        ]
        tmpdir = tempfile.mkdtemp()
        path = self._create_pdf_with_text(
            "dog - Hund\ncat - Katze",
            Path(tmpdir) / "vocab.pdf",
        )
        cards = ingest_pdf(path, target_language="en", deepseek_api_key="test-key")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].word, "dog")
        mock_ai.assert_called_once()


if __name__ == "__main__":
    unittest.main()
