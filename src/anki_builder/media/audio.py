import re
from pathlib import Path

from gtts import gTTS

from anki_builder.schema import Card

# Match emoji characters (Unicode emoji ranges)
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F"
    "\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF\U0000200D\U00002B50\U00002B55\U000023E9-\U000023F3"
    "\U0000231A-\U0000231B\U000025AA-\U000025AB\U000025B6\U000025C0"
    "\U000025FB-\U000025FE\U00003030\U0000303D\U00003297\U00003299]+",
)


def _strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub("", text).strip()

# gTTS language codes
LANG_MAP = {
    "en": "en",
    "fr": "fr",
    "zh": "zh-CN",
    "de": "de",
}


def generate_audio_for_card(card: Card, media_dir: Path) -> Card:
    lang = LANG_MAP.get(card.target_language, card.target_language)
    update = {}

    # Word audio
    audio_path = media_dir / f"{card.id}_audio.mp3"
    if card.audio_file and Path(card.audio_file).exists():
        pass
    elif audio_path.exists():
        update["audio_file"] = str(audio_path)
    else:
        tts = gTTS(text=card.target_word or card.source_word, lang=lang)
        tts.save(str(audio_path))
        update["audio_file"] = str(audio_path)

    # Example sentence audio
    example_audio_path = media_dir / f"{card.id}_example_audio.mp3"
    if card.target_example_audio and Path(card.target_example_audio).exists():
        pass
    elif example_audio_path.exists():
        update["target_example_audio"] = str(example_audio_path)
    elif card.target_example_sentence:
        tts = gTTS(text=_strip_emojis(card.target_example_sentence), lang=lang)
        tts.save(str(example_audio_path))
        update["target_example_audio"] = str(example_audio_path)

    if update:
        return card.model_copy(update=update)
    return card


def generate_audio_batch(cards: list[Card], media_dir: Path) -> list[Card]:
    return [generate_audio_for_card(card, media_dir) for card in cards]
