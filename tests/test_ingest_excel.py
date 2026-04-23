import tempfile
import unittest
from pathlib import Path

import openpyxl

from anki_builder.ingest.excel import ingest_excel


class TestExcelIngestion(unittest.TestCase):
    def _create_xlsx(self, headers: list[str], rows: list[list], path: Path) -> Path:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        wb.save(path)
        return path

    def test_basic_ingestion(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["word", "translation"],
            [["dog", "Hund"], ["cat", "Katze"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(path, target_language="en")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "dog")
        self.assertEqual(cards[0].target_word, "Hund")
        self.assertEqual(cards[0].target_language, "en")
        self.assertEqual(cards[0].source, str(path))

    def test_fuzzy_header_matching(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["Wort", "Übersetzung"],
            [["Hund", "dog"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(path, target_language="en")
        self.assertEqual(cards[0].source_word, "Hund")
        self.assertEqual(cards[0].target_word, "dog")

    def test_custom_column_mapping(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["vocab", "meaning"],
            [["accomplish", "erreichen"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(
            path,
            target_language="en",
            column_map={"vocab": "source_word", "meaning": "target_word"},
        )
        self.assertEqual(cards[0].source_word, "accomplish")
        self.assertEqual(cards[0].target_word, "erreichen")

    def test_unmapped_columns_become_tags(self):
        tmpdir = tempfile.mkdtemp()
        path = self._create_xlsx(
            ["word", "translation", "level", "chapter"],
            [["dog", "Hund", "A1", "ch3"]],
            Path(tmpdir) / "vocab.xlsx",
        )
        cards = ingest_excel(path, target_language="en")
        self.assertIn("level:A1", cards[0].tags)
        self.assertIn("chapter:ch3", cards[0].tags)

    def test_csv_ingestion(self):
        tmpdir = tempfile.mkdtemp()
        csv_path = Path(tmpdir) / "vocab.csv"
        csv_path.write_text("word,translation\ndog,Hund\ncat,Katze\n")
        cards = ingest_excel(csv_path, target_language="en")
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].source_word, "dog")


if __name__ == "__main__":
    unittest.main()
