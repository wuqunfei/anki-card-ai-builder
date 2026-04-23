import os
import tempfile
import unittest
from pathlib import Path

from anki_builder.config import Config, load_config


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        config = Config()
        self.assertEqual(config.default_source_language, "de")
        self.assertEqual(config.default_target_language, "en")
        self.assertTrue(config.media.audio_enabled)
        self.assertTrue(config.media.image_enabled)
        self.assertEqual(config.media.concurrency, 5)
        self.assertEqual(config.export.default_deck_name, "Vocabulary")

    def test_load_config_from_yaml(self):
        tmpdir = tempfile.mkdtemp()
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(
            "default_source_language: fr\n"
            "default_target_language: zh\n"
            "export:\n"
            "  default_deck_name: 'Chinese Words'\n"
        )
        config = load_config(Path(tmpdir))
        self.assertEqual(config.default_source_language, "fr")
        self.assertEqual(config.default_target_language, "zh")
        self.assertEqual(config.export.default_deck_name, "Chinese Words")

    def test_load_config_missing_file_returns_defaults(self):
        tmpdir = tempfile.mkdtemp()
        config = load_config(Path(tmpdir))
        self.assertEqual(config.default_source_language, "de")

    def test_api_keys_from_env(self):
        os.environ["MINIMAX_API_KEY"] = "test-minimax-key"
        try:
            config = Config()
            self.assertEqual(config.minimax_api_key, "test-minimax-key")
        finally:
            del os.environ["MINIMAX_API_KEY"]


if __name__ == "__main__":
    unittest.main()
