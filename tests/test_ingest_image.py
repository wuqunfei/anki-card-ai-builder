import unittest
from pathlib import Path
import tempfile

from anki_builder.ingest.image import ingest_image


class TestImageIngestion(unittest.TestCase):
    def test_ingest_image_raises_not_implemented(self):
        img_path = Path(tempfile.mktemp(suffix=".png"))
        img_path.write_bytes(b"fake image data")

        with self.assertRaises(NotImplementedError):
            ingest_image(img_path, target_language="en", minimax_api_key="test-key")


if __name__ == "__main__":
    unittest.main()
