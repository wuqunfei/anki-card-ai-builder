import uuid

from pydantic import BaseModel, Field


class Card(BaseModel):
    # --- Metadata & Tracking ---
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit: str | None = None                    # Textbook unit (e.g., "Unité 1")
    reference: str | None = None               # Origin (e.g., "Page 162")
    status: str = "extracted"                  # Workflow state
    tags: list[str] = Field(default_factory=list)
    audio_file: str | None = None
    image_file: str | None = None
    source: str                                # How card was created ("cli", file path, etc.)

    # --- SOURCE (Native Language) ---
    source_word: str                           # Native language word
    source_language: str = "de"                # Native language ISO
    source_gender: str | None = None           # Grammatical Gender: e.g. German if noun ("m", "f", "n")
    source_example_sentence: str | None = None # Native language sentence with emojis

    # --- TARGET (Learning Language) ---
    target_word: str | None = None             # Learning language word
    target_language: str                       # Learning language ISO (no default)
    target_gender: str | None = None           # Target Grammatical Gender: e.g. French if noun ("m", "f")
    target_pronunciation: str | None = None    # IPA, Pinyin, or Romaji
    target_part_of_speech: str | None = None   # noun, verb, adjective, etc.
    target_example_sentence: str | None = None # Target sentence with emojis

    # Word breakdown as HTML with soft colored parts:
    # - Prefix (blue): <span style="color:#5b9bd5">...</span>
    # - Root (coral): <span style="color:#e07b7b">...</span>
    # - Suffix (green): <span style="color:#6dba6d">...</span>
    target_mnemonic: str | None = None
