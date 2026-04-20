import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from anki_builder.schema import Card
from anki_builder.media.audio import generate_audio_for_card, generate_audio_batch


class TestAudioGeneration(unittest.TestCase):
    @patch("anki_builder.media.audio.gTTS")
    def test_generate_audio_for_card(self, mock_gtts_cls):
        mock_tts = MagicMock()
        mock_gtts_cls.return_value = mock_tts

        def fake_save(path):
            Path(path).write_bytes(b"fake-mp3")
        mock_tts.save.side_effect = fake_save

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(word="dog", target_language="en", source="test")
        result = generate_audio_for_card(card, media_dir)

        self.assertIsNotNone(result.audio_file)
        self.assertIn("audio.mp3", result.audio_file)
        self.assertTrue(Path(result.audio_file).exists())
        mock_gtts_cls.assert_called_once_with(text="dog", lang="en")

    def test_skip_existing_audio(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        card = Card(id="fixed-id", word="dog", target_language="en", source="test")
        audio_path = media_dir / "fixed-id_audio.mp3"
        audio_path.write_bytes(b"existing-audio")
        card = card.model_copy(update={"audio_file": str(audio_path)})

        result = generate_audio_for_card(card, media_dir)
        self.assertEqual(result.audio_file, str(audio_path))

    @patch("anki_builder.media.audio.gTTS")
    def test_generate_audio_batch(self, mock_gtts_cls):
        mock_tts = MagicMock()
        mock_gtts_cls.return_value = mock_tts

        def fake_save(path):
            Path(path).write_bytes(b"fake-mp3")
        mock_tts.save.side_effect = fake_save

        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        cards = [
            Card(word="dog", target_language="en", source="test"),
            Card(word="cat", target_language="en", source="test"),
        ]
        results = generate_audio_batch(cards, media_dir)
        self.assertEqual(len(results), 2)
        self.assertIsNotNone(results[0].audio_file)
        self.assertIsNotNone(results[1].audio_file)


if __name__ == "__main__":
    unittest.main()
