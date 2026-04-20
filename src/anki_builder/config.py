import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()
from pydantic import BaseModel, Field


class MediaConfig(BaseModel):
    audio_enabled: bool = True
    image_enabled: bool = True
    concurrency: int = 5


class ExportConfig(BaseModel):
    default_deck_name: str = "Vocabulary"
    output_dir: str = "./output"


class Config(BaseModel):
    default_source_language: str = "de"
    default_target_language: str = "en"
    learner_profile: str = "ages 9-12, kid-friendly with emojis"
    media: MediaConfig = Field(default_factory=MediaConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    @property
    def minimax_api_key(self) -> str:
        return os.environ.get("MINIMAX_API_KEY", "")

    @property
    def deepseek_api_key(self) -> str:
        return os.environ.get("DEEPSEEK_API_KEY", "")

    @property
    def google_api_key(self) -> str:
        return os.environ.get("GOOGLE_API_KEY", "")


def load_config(work_dir: Path) -> Config:
    config_path = work_dir / "config.yaml"
    if not config_path.exists():
        return Config()
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return Config(**data)
