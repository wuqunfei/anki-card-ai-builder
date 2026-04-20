import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from anki_builder.schema import Card
from anki_builder.media.image_local import generate_image_for_card, generate_image_batch


class TestLocalImageGeneration(unittest.TestCase):
    @patch("anki_builder.media.image_local._get_pipeline")
    def test_generate_image_for_card(self, mock_get_pipe):
        mock_pipe = MagicMock()
        mock_get_pipe.return_value = mock_pipe

        # Create a real tiny image as output
        fake_image = Image.new("RGB", (64, 64), color="red")
        mock_pipe.return_value.images = [fake_image]

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")
        result = generate_image_for_card(card, media_dir)

        self.assertIsNotNone(result.image_file)
        self.assertIn("image.png", result.image_file)
        self.assertTrue(Path(result.image_file).exists())

    def test_skip_existing_image(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        img_path = media_dir / "fixed-id_image.png"
        img_path.write_bytes(b"existing")
        card = card.model_copy(update={"image_file": str(img_path)})

        result = generate_image_for_card(card, media_dir)
        self.assertEqual(result.image_file, str(img_path))


if __name__ == "__main__":
    unittest.main()
