import os

import click
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self) -> None:
        self.learner_profile = os.environ.get("LEARNER_PROFILE", "ages 9-12, kid-friendly with emojis")
        self.audio_enabled = os.environ.get("MEDIA_AUDIO_ENABLED", "true").lower() == "true"
        self.image_enabled = os.environ.get("MEDIA_IMAGE_ENABLED", "true").lower() == "true"
        self.concurrency = int(os.environ.get("MEDIA_CONCURRENCY", "3"))
        self.image_provider = os.environ.get("IMAGE_PROVIDER", "minimax")  # "minimax" or "gemini"
        self.enrich_provider = os.environ.get("ENRICH_PROVIDER", "minimax")  # "minimax" or "gemini"
        self.default_deck_name = os.environ.get("EXPORT_DECK_NAME", "Vocabulary")

    @property
    def minimax_api_key(self) -> str:
        return os.environ.get("MINIMAX_API_KEY", "")

    @property
    def google_api_key(self) -> str:
        return os.environ.get("GOOGLE_API_KEY", "")

    def require_minimax_key(self) -> None:
        if not self.minimax_api_key:
            raise click.ClickException(
                "MINIMAX_API_KEY is required but not set. Add it to your .env file or set the environment variable."
            )

    def require_google_key(self) -> None:
        if not self.google_api_key:
            raise click.ClickException(
                "GOOGLE_API_KEY is required but not set. Add it to your .env file or set the environment variable."
            )


def load_config() -> Config:
    return Config()
