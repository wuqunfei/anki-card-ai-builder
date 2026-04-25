import uuid

from pydantic import BaseModel, Field


class Card(BaseModel):
    # --- Metadata & Tracking ---
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit: str | None = None  # Textbook unit (e.g., "Unité 1")
    reference: str | None = None  # Origin (e.g., "Page 162")
    status: str = "extracted"  # Workflow state
    tags: list[str] = Field(default_factory=list)
    audio_file: str | None = None
    image_file: str | None = None
    # --- SOURCE (Native Language) ---
    source_word: str  # Native language word
    source_language: str = "de"  # Native language ISO
    source_gender: str | None = None  # Grammatical Gender: e.g. German if noun ("m", "f", "n")
    source_example_sentence: str | None = None  # Native language sentence with emojis

    # --- TARGET (Learning Language) ---
    target_word: str | None = None  # Learning language word
    target_language: str  # Learning language ISO (no default)
    target_gender: str | None = None  # Target Grammatical Gender: e.g. French if noun ("m", "f")
    target_pronunciation: str | None = None  # IPA, Pinyin, or Romaji
    target_part_of_speech: str | None = None  # noun, verb, adjective, etc.
    target_example_sentence: str | None = None  # Target sentence with emojis
    target_example_audio: str | None = None  # Path to example sentence audio
    target_synonyms: str | None = None  # Similar words (comma-separated)
    target_antonyms: str | None = None  # Opposite words (comma-separated)

    # --- Etymology & Mnemonics ---
    # Morpheme breakdown: Prefix (blue #5b9bd5) + Root (coral #e07b7b) + Suffix (green #6dba6d)
    target_mnemonic: str | None = None
    # Origin chain to PIE: warm gold tones per stage (#8B6914, #B8860B, #D4A854)
    target_origin: str | None = None
    # Cognates across EN/DE/FR/Latin: purple tones (#8e7cc3, #a78bfa)
    target_cognates: str | None = None
    # Memory hook: colored when referencing morphemes
    target_memory_hook: str | None = None

    # --- Card Type ---
    typing: bool = False  # True = "type in the answer" card
