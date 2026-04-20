import uuid

from pydantic import BaseModel, Field


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    word: str
    source_language: str = "de"
    target_language: str = "en"
    translation: str | None = None
    pronunciation: str | None = None  # IPA for en/fr, pinyin for zh
    example_sentence: str | None = None
    sentence_translation: str | None = None
    mnemonic: str | None = None  # HTML rich text: prefix (blue) + root (red) + suffix (green)
    part_of_speech: str | None = None
    tags: list[str] = Field(default_factory=list)
    audio_file: str | None = None
    image_file: str | None = None
    source: str
    status: str = "extracted"
