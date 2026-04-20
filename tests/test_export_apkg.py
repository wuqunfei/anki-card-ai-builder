import tempfile
import unittest
import zipfile
from pathlib import Path

from anki_builder.schema import Card
from anki_builder.export.apkg import export_apkg


class TestApkgExport(unittest.TestCase):
    def _make_cards(self) -> list[Card]:
        return [
            Card(
                id="card-1",
                word="dog",
                target_language="en",
                source="test",
                translation="Hund",
                pronunciation="/dɒɡ/",
                example_sentence="The dog plays in the park! 🐕",
                sentence_translation="Der Hund spielt im Park! 🐕",
                mnemonic='<span style="color:red">dog</span>',
                part_of_speech="noun",
                status="enriched",
            ),
            Card(
                id="card-2",
                word="cat",
                target_language="en",
                source="test",
                translation="Katze",
                pronunciation="/kæt/",
                example_sentence="The cat sleeps on the sofa! 🐱",
                sentence_translation="Die Katze schläft auf dem Sofa! 🐱",
                mnemonic='<span style="color:red">cat</span>',
                part_of_speech="noun",
                status="enriched",
            ),
        ]

    def test_export_creates_apkg_file(self):
        tmpdir = tempfile.mkdtemp()
        output_path = Path(tmpdir) / "test.apkg"
        cards = self._make_cards()

        export_apkg(cards, output_path, deck_name="Test Deck")

        self.assertTrue(output_path.exists())
        # .apkg is a zip file
        self.assertTrue(zipfile.is_zipfile(output_path))

    def test_export_with_media(self):
        tmpdir = tempfile.mkdtemp()
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()

        # Create fake audio file
        audio_path = media_dir / "card-1_audio.mp3"
        audio_path.write_bytes(b"fake-audio")

        cards = self._make_cards()
        cards[0] = cards[0].model_copy(update={"audio_file": str(audio_path)})

        output_path = Path(tmpdir) / "test.apkg"
        export_apkg(cards, output_path, deck_name="Test Deck")

        self.assertTrue(output_path.exists())
        # Verify media is inside the zip
        with zipfile.ZipFile(output_path) as zf:
            names = zf.namelist()
            # genanki stores media with numeric names
            self.assertTrue(any("media" in str(n) or n.isdigit() for n in names))

    def test_export_empty_cards(self):
        tmpdir = tempfile.mkdtemp()
        output_path = Path(tmpdir) / "test.apkg"
        export_apkg([], output_path, deck_name="Empty Deck")
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
