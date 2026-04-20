import json
import unittest
from unittest.mock import patch, MagicMock

from anki_builder.ingest.image import ingest_image


class TestImageIngestion(unittest.TestCase):
    @patch("anki_builder.ingest.image.extract_vocabulary_with_ai")
    def test_ingest_image(self, mock_ai):
        mock_ai.return_value = [
            {"word": "apple", "translation": "Apfel"},
            {"word": "banana", "translation": "Banane"},
        ]
        # Create a minimal PNG (1x1 pixel)
        import struct, zlib
        def make_tiny_png() -> bytes:
            raw = b"\x00\x00\x00\x00"
            compressed = zlib.compress(raw)
            def chunk(ctype, data):
                c = ctype + data
                return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return (
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", compressed)
                + chunk(b"IEND", b"")
            )

        import tempfile
        from pathlib import Path
        tmpdir = tempfile.mkdtemp()
        img_path = Path(tmpdir) / "page.png"
        img_path.write_bytes(make_tiny_png())

        cards = ingest_image(img_path, target_language="en", deepseek_api_key="test-key")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].word, "apple")
        self.assertEqual(cards[0].translation, "Apfel")
        self.assertEqual(cards[0].source, str(img_path))
        mock_ai.assert_called_once()
        # Verify image_bytes was passed
        call_kwargs = mock_ai.call_args[1]
        self.assertIsNotNone(call_kwargs.get("image_bytes"))


if __name__ == "__main__":
    unittest.main()
