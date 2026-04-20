import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from anki_builder.schema import Card
from anki_builder.media.audio import generate_audio_for_card, generate_audio_batch


class TestAudioGeneration(unittest.TestCase):
    def test_generate_audio_for_card(self):
        mock_client = AsyncMock()

        fake_audio_b64 = base64.b64encode(b"fake-mp3-data").decode()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "base_resp": {"status_code": 0},
            "data": {"audio": fake_audio_b64},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_resp

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")

        result = asyncio.run(
            generate_audio_for_card(card, media_dir, "test-key", mock_client)
        )
        self.assertIsNotNone(result.audio_file)
        self.assertIn("audio.mp3", result.audio_file)
        self.assertTrue(Path(result.audio_file).exists())

    def test_skip_existing_audio(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        audio_path = media_dir / "fixed-id_audio.mp3"
        audio_path.write_bytes(b"existing-audio")
        card = card.model_copy(update={"audio_file": str(audio_path)})

        result = asyncio.run(
            generate_audio_for_card(card, media_dir, "test-key", AsyncMock())
        )
        self.assertEqual(result.audio_file, str(audio_path))


if __name__ == "__main__":
    unittest.main()
