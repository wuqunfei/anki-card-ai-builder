import os
import unittest

from anki_builder.config import Config, load_config


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        config = Config()
        self.assertEqual(config.learner_profile, "ages 9-12, kid-friendly with emojis")
        self.assertTrue(config.audio_enabled)
        self.assertTrue(config.image_enabled)
        self.assertEqual(config.concurrency, 5)
        self.assertEqual(config.default_deck_name, "Vocabulary")

    def test_config_from_env(self):
        env = {
            "LEARNER_PROFILE": "adults",
            "MEDIA_AUDIO_ENABLED": "false",
            "MEDIA_IMAGE_ENABLED": "false",
            "MEDIA_CONCURRENCY": "10",
            "EXPORT_DECK_NAME": "Chinese Words",
        }
        for k, v in env.items():
            os.environ[k] = v
        try:
            config = Config()
            self.assertEqual(config.learner_profile, "adults")
            self.assertFalse(config.audio_enabled)
            self.assertFalse(config.image_enabled)
            self.assertEqual(config.concurrency, 10)
            self.assertEqual(config.default_deck_name, "Chinese Words")
        finally:
            for k in env:
                del os.environ[k]

    def test_load_config_returns_config(self):
        config = load_config()
        self.assertIsInstance(config, Config)

    def test_api_keys_from_env(self):
        os.environ["MINIMAX_API_KEY"] = "test-minimax-key"
        try:
            config = Config()
            self.assertEqual(config.minimax_api_key, "test-minimax-key")
        finally:
            del os.environ["MINIMAX_API_KEY"]


if __name__ == "__main__":
    unittest.main()
