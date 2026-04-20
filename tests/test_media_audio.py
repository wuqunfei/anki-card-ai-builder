import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from anki_builder.schema import Card
from anki_builder.media.audio import generate_audio_for_card, generate_audio_batch


class TestAudioGeneration(unittest.TestCase):
    @patch("anki_builder.media.audio.httpx.AsyncClient")
    def test_generate_audio_for_card(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock create task response
        create_resp = MagicMock()
        create_resp.json.return_value = {"task_id": "task-123"}
        create_resp.raise_for_status = MagicMock()

        # Mock query status response (completed)
        status_resp = MagicMock()
        status_resp.json.return_value = {
            "status": "Success",
            "file_id": "file-456",
        }
        status_resp.raise_for_status = MagicMock()

        # Mock download response
        download_resp = MagicMock()
        download_resp.content = b"fake-mp3-data"
        download_resp.raise_for_status = MagicMock()

        mock_client.post.return_value = create_resp
        mock_client.get.side_effect = [status_resp, download_resp]

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")

        result = asyncio.run(
            generate_audio_for_card(card, media_dir, "test-key", mock_client)
        )
        self.assertIsNotNone(result.audio_file)
        self.assertIn("audio.mp3", result.audio_file)

    def test_skip_existing_audio(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        audio_path = media_dir / "fixed-id_audio.mp3"
        audio_path.write_bytes(b"existing-audio")
        card = card.model_copy(update={"audio_file": str(audio_path)})

        # Should skip — audio_file already set
        result = asyncio.run(
            generate_audio_for_card(card, media_dir, "test-key", AsyncMock())
        )
        self.assertEqual(result.audio_file, str(audio_path))


if __name__ == "__main__":
    unittest.main()
