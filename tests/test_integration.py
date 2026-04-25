import json
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import openpyxl
from click.testing import CliRunner

from anki_builder.cli import main


class TestFullPipeline(unittest.TestCase):
    """Integration test: Excel → enrich → media → export, all with mocked APIs."""

    def _create_xlsx(self, path: Path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["word", "translation"])
        ws.append(["dog", "Hund"])
        ws.append(["cat", "Katze"])
        wb.save(path)

    @patch("anki_builder.cli.generate_image_batch")
    @patch("anki_builder.cli.generate_audio_batch")
    @patch("anki_builder.cli.enrich_cards")
    def test_full_run_command(self, mock_enrich, mock_audio, mock_image):
        def fake_enrich(cards, api_key):
            enriched = []
            for c in cards:
                enriched.append(
                    c.model_copy(
                        update={
                            "target_pronunciation": "/test/",
                            "target_example_sentence": "Test sentence! 🎉",
                            "source_example_sentence": "Testsatz! 🎉",
                            "target_mnemonic": '<span style="color:red">test</span>',
                            "target_part_of_speech": "noun",
                            "status": "enriched",
                        }
                    )
                )
            return enriched

        mock_enrich.side_effect = fake_enrich

        mock_audio.side_effect = lambda cards, media_dir: cards

        async def fake_image(cards, media_dir, api_key, concurrency):
            return cards

        mock_image.side_effect = fake_image

        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(
                main,
                ["run", "--input", "vocab.xlsx", "--lang-target", "en", "--deck", "TestDeck"],
                env={"MINIMAX_API_KEY": "test"},
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

            cards_data = json.loads(Path("output/cards.json").read_text())
            self.assertEqual(len(cards_data), 2)
            self.assertEqual(cards_data[0]["source_word"], "dog")
            self.assertEqual(cards_data[0]["target_part_of_speech"], "noun")
            self.assertIn("🎉", cards_data[0]["target_example_sentence"])

            result2 = runner.invoke(main, ["export", "--deck", "TestDeck"])
            self.assertEqual(result2.exit_code, 0, msg=result2.output)
            apkg_path = Path("output/TestDeck.apkg")
            self.assertTrue(apkg_path.exists())
            self.assertTrue(zipfile.is_zipfile(apkg_path))


if __name__ == "__main__":
    unittest.main()
