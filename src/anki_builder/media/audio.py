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
        tts = gTTS(text=card.target_example_sentence, lang=lang)
        tts.save(str(example_audio_path))
        update["target_example_audio"] = str(example_audio_path)

    if update:
        return card.model_copy(update=update)
    return card


def generate_audio_batch(cards: list[Card], media_dir: Path) -> list[Card]:
    return [generate_audio_for_card(card, media_dir) for card in cards]
