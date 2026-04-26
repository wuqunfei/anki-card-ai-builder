import re
from pathlib import Path

from gtts import gTTS

from anki_builder.schema import Card

# Match emoji characters (Unicode emoji ranges)
_EMOJI_RE = re.compile(
    "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff\U00002702-\U000027b0\U0000fe00-\U0000fe0f"
    "\U0001f900-\U0001f9ff\U0001fa00-\U0001fa6f\U0001fa70-\U0001faff"
    "\U00002600-\U000026ff\U0000200d\U00002b50\U00002b55\U000023e9-\U000023f3"
    "\U0000231a-\U0000231b\U000025aa-\U000025ab\U000025b6\U000025c0"
    "\U000025fb-\U000025fe\U00003030\U0000303d\U00003297\U00003299]+",
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
    import click

    result = []
    for card in cards:
        try:
            result.append(generate_audio_for_card(card, media_dir))
        except Exception as e:
            click.echo(f"  Warning: audio failed for '{card.source_word}': {e}")
            result.append(card)
    return result
