import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import openpyxl
from click.testing import CliRunner

from anki_builder.cli import main


class TestCLI(unittest.TestCase):
    def _create_xlsx(self, path: Path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["word", "translation"])
        ws.append(["dog", "Hund"])
        ws.append(["cat", "Katze"])
        wb.save(path)

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("anki-builder", result.output.lower())

    def test_ingest_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(main, ["ingest", "--input", "vocab.xlsx", "--lang", "en"])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue(Path(".anki-builder/cards.json").exists())

    @patch("anki_builder.cli.enrich_cards")
    def test_enrich_command(self, mock_enrich):
        mock_enrich.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".anki-builder").mkdir()
            Path(".anki-builder/cards.json").write_text("[]")
            result = runner.invoke(
                main, ["enrich"],
                env={"MINIMAX_API_KEY": "test-key"},
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

    def test_export_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".anki-builder").mkdir()
            Path(".anki-builder/cards.json").write_text("[]")
            result = runner.invoke(main, ["export", "--deck", "Test"])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue(Path("output/Test.apkg").exists())


if __name__ == "__main__":
    unittest.main()
