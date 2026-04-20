from pathlib import Path

from gtts import gTTS

from anki_builder.schema import Card

# gTTS language codes
LANG_MAP = {
    "en": "en",
    "fr": "fr",
    "zh": "zh-CN",
    "de": "de",
}


def generate_audio_for_card(card: Card, media_dir: Path) -> Card:
    audio_path = media_dir / f"{card.id}_audio.mp3"

    # Skip if already exists
    if card.audio_file and Path(card.audio_file).exists():
        return card

    if audio_path.exists():
        return card.model_copy(update={"audio_file": str(audio_path)})

    lang = LANG_MAP.get(card.target_language, card.target_language)
    tts = gTTS(text=card.word, lang=lang)
    tts.save(str(audio_path))

    return card.model_copy(update={"audio_file": str(audio_path)})


def generate_audio_batch(cards: list[Card], media_dir: Path) -> list[Card]:
    return [generate_audio_for_card(card, media_dir) for card in cards]
