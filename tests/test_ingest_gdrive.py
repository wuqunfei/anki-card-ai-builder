import unittest
from unittest.mock import patch, MagicMock

from anki_builder.ingest.gdrive import extract_folder_id, ingest_gdrive_folder


class TestGDriveIngestion(unittest.TestCase):
    def test_extract_folder_id_from_url(self):
        url = "https://drive.google.com/drive/folders/1abc2def3ghi"
        self.assertEqual(extract_folder_id(url), "1abc2def3ghi")

    def test_extract_folder_id_from_raw_id(self):
        self.assertEqual(extract_folder_id("1abc2def3ghi"), "1abc2def3ghi")

    def test_extract_folder_id_with_query_params(self):
        url = "https://drive.google.com/drive/folders/1abc2def3ghi?usp=sharing"
        self.assertEqual(extract_folder_id(url), "1abc2def3ghi")

    @patch("anki_builder.ingest.gdrive.download_file")
    @patch("anki_builder.ingest.gdrive.list_files_in_folder")
    @patch("anki_builder.ingest.gdrive.ingest_excel")
    def test_ingest_gdrive_folder_with_excel(self, mock_ingest_excel, mock_list, mock_download):
        from anki_builder.schema import Card
        from pathlib import Path
        import tempfile

        mock_list.return_value = [
            {"id": "file1", "name": "vocab.xlsx", "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        ]
        mock_download.return_value = Path(tempfile.mktemp(suffix=".xlsx"))
        mock_ingest_excel.return_value = [
            Card(source_word="dog", target_language="en", source="gdrive"),
        ]

        cards = ingest_gdrive_folder(
            "https://drive.google.com/drive/folders/test123",
            target_language="en",
            google_api_key="test-key",
            minimax_api_key="test-key",
        )
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].source_word, "dog")
        mock_list.assert_called_once_with("test123", "test-key")

    @patch("anki_builder.ingest.gdrive.download_file")
    @patch("anki_builder.ingest.gdrive.list_files_in_folder")
    def test_skips_unsupported_files(self, mock_list, mock_download):
        mock_list.return_value = [
            {"id": "file1", "name": "readme.txt", "mimeType": "text/plain"},
            {"id": "file2", "name": "notes.docx", "mimeType": "application/vnd.openxmlformats"},
        ]

        cards = ingest_gdrive_folder(
            "test-folder-id",
            target_language="en",
            google_api_key="test-key",
            minimax_api_key="test-key",
        )
        self.assertEqual(len(cards), 0)
        mock_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
