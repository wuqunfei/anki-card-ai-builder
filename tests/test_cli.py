import unittest
from pathlib import Path
from unittest.mock import patch

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
            result = runner.invoke(
                main, ["ingest", "--input", "vocab.xlsx", "--lang-target", "en", "--output", "myout"]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue(Path("myout/cards.json").exists())

    def test_ingest_creates_workspace_uuid_folder(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("workspace").mkdir()
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(main, ["ingest", "--input", "vocab.xlsx", "--lang-target", "en"])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            # Should have created a folder under workspace/
            workspace_dirs = list(Path("workspace").iterdir())
            self.assertEqual(len(workspace_dirs), 1)
            self.assertTrue((workspace_dirs[0] / "cards.json").exists())

    @patch("anki_builder.cli.enrich_cards")
    def test_enrich_command(self, mock_enrich):
        mock_enrich.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("myout").mkdir()
            Path("myout/cards.json").write_text("[]")
            result = runner.invoke(
                main,
                ["enrich", "--output", "myout"],
                env={"MINIMAX_API_KEY": "test-key"},
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

    def test_export_command(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("myout").mkdir()
            Path("myout/cards.json").write_text("[]")
            result = runner.invoke(main, ["export", "--output", "myout", "--deck", "Test"])
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertTrue(Path("myout/Test.apkg").exists())

    def test_ingest_with_typing_flag(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(
                main, ["ingest", "--input", "vocab.xlsx", "--lang-target", "en", "--typing", "--output", "myout"]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            import json

            cards_data = json.loads(Path("myout/cards.json").read_text())
            self.assertTrue(all(c["typing"] for c in cards_data))

    def test_ingest_without_typing_flag(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            self._create_xlsx(Path("vocab.xlsx"))
            result = runner.invoke(
                main, ["ingest", "--input", "vocab.xlsx", "--lang-target", "en", "--output", "myout"]
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            import json

            cards_data = json.loads(Path("myout/cards.json").read_text())
            self.assertFalse(any(c["typing"] for c in cards_data))


if __name__ == "__main__":
    unittest.main()
