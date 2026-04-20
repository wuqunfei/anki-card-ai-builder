import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from anki_builder.schema import Card
from anki_builder.media.image import generate_image_for_card, generate_image_batch


class TestImageGeneration(unittest.TestCase):
    @patch("anki_builder.media.image.httpx.AsyncClient")
    def test_generate_image_for_card(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # Fake 1x1 PNG as base64
        fake_image = base64.b64encode(b"fake-png-data").decode()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {"image_base64": [fake_image]}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_resp

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")

        result = asyncio.run(
            generate_image_for_card(card, media_dir, "test-key", mock_client)
        )
        self.assertIsNotNone(result.image_file)
        self.assertIn("image.png", result.image_file)
        # Verify file was written
        self.assertTrue(Path(result.image_file).exists())

    def test_skip_existing_image(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        img_path = media_dir / "fixed-id_image.png"
        img_path.write_bytes(b"existing-image")
        card = card.model_copy(update={"image_file": str(img_path)})

        result = asyncio.run(
            generate_image_for_card(card, media_dir, "test-key", AsyncMock())
        )
        self.assertEqual(result.image_file, str(img_path))


if __name__ == "__main__":
    unittest.main()
