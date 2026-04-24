import hashlib
from pathlib import Path

import genanki

from anki_builder.schema import Card

BASIC_MODEL_ID = int(hashlib.md5(b"anki-builder-basic-v6").hexdigest()[:8], 16)
TYPING_MODEL_ID = int(hashlib.md5(b"anki-builder-typing-v6").hexdigest()[:8], 16)

_SHARED_FIELDS = [
    {"name": "SourceWord"},
    {"name": "TargetWord"},
    {"name": "TargetPronunciation"},
    {"name": "TargetExampleSentence"},
    {"name": "SourceExampleSentence"},
    {"name": "TargetMnemonic"},
    {"name": "TargetOrigin"},
    {"name": "TargetCognates"},
    {"name": "TargetMemoryHook"},
    {"name": "TargetPartOfSpeech"},
    {"name": "Audio"},
    {"name": "Image"},
    {"name": "ExampleAudio"},
    {"name": "TargetWordPlain"},
]

BASIC_MODEL = genanki.Model(
    BASIC_MODEL_ID,
    "Anki Builder Basic",
    fields=_SHARED_FIELDS,
    templates=[{
        "name": "Basic",
        "qfmt": (
            '<div style="text-align:center; font-size:28px; font-weight:bold; margin:20px; color:#2c3e50;">'
            "{{TargetWord}}"
            "</div>"
            '<div style="text-align:center; font-size:16px; color:#7f8c8d; margin-bottom:8px;">'
            "{{TargetPronunciation}}"
            "</div>"
            '<div style="text-align:center; font-size:13px; color:#999; margin-bottom:12px;">'
            "{{TargetPartOfSpeech}}"
            "</div>"
            '<div style="text-align:center; margin:10px;">{{Image}}</div>'
            '<div style="text-align:center;">{{Audio}}</div>'
        ),
        "afmt": (
            '{{FrontSide}}<hr id="answer">'
            '<div style="text-align:center; font-size:22px; color:#333; margin:10px;">{{SourceWord}}</div>'
            '{{#TargetMnemonic}}<div style="text-align:center; font-size:14px; margin:4px 0;">{{TargetMnemonic}}</div>{{/TargetMnemonic}}'
            '{{#TargetMemoryHook}}<div style="text-align:center; font-size:13px; margin:3px 0;">{{TargetMemoryHook}}</div>{{/TargetMemoryHook}}'
            '{{#TargetCognates}}<div style="text-align:center; font-size:12px; margin:3px 0;">{{TargetCognates}}</div>{{/TargetCognates}}'
            '<div style="text-align:center; font-size:16px; margin:10px; color:#4a90d9;">{{TargetExampleSentence}}</div>'
            '{{#ExampleAudio}}'
            '<div style="text-align:center; margin:6px 0 10px;">{{ExampleAudio}}</div>'
            '{{/ExampleAudio}}'
            '<div style="text-align:center; font-size:14px; color:#7ea87e;">{{SourceExampleSentence}}</div>'
        ),
    }],
)

TYPING_MODEL = genanki.Model(
    TYPING_MODEL_ID,
    "Anki Builder Type-in",
    fields=_SHARED_FIELDS,
    templates=[{
        "name": "Type-in",
        "qfmt": (
            '<div style="text-align:center; font-size:26px; font-weight:bold; margin:10px 0 6px; color:#2c3e50;">'
            "{{SourceWord}}"
            "</div>"
            '<div style="text-align:center; margin:6px 0;">{{Image}}</div>'
            '<div style="text-align:center; margin:4px 0;">{{Audio}}</div>'
            '<div style="text-align:center; margin:10px 0;">{{type:TargetWordPlain}}</div>'
        ),
        "afmt": (
            '{{FrontSide}}<hr id="answer" style="margin:6px 0;">'
            '<div style="text-align:center; font-size:20px; color:#333; margin:6px 0 2px;">{{TargetWord}}</div>'
            '<div style="text-align:center; margin-bottom:6px;">'
            '<span style="font-size:14px; color:#7f8c8d;">{{TargetPronunciation}}</span>'
            ' <span style="font-size:12px; color:#999;">{{TargetPartOfSpeech}}</span>'
            '</div>'
            '{{#TargetMnemonic}}<div style="text-align:center; font-size:14px; margin:4px 0;">{{TargetMnemonic}}</div>{{/TargetMnemonic}}'
            '{{#TargetMemoryHook}}<div style="text-align:center; font-size:13px; margin:3px 0;">{{TargetMemoryHook}}</div>{{/TargetMemoryHook}}'
            '{{#TargetCognates}}<div style="text-align:center; font-size:12px; margin:3px 0;">{{TargetCognates}}</div>{{/TargetCognates}}'
            '<div style="text-align:center; font-size:14px; margin:4px 0; color:#4a90d9;">{{TargetExampleSentence}}</div>'
            '<div style="text-align:center; font-size:13px; color:#7ea87e;">{{SourceExampleSentence}}</div>'
            '{{#ExampleAudio}}'
            '<div style="text-align:center; margin:2px 0;">{{ExampleAudio}}</div>'
            '{{/ExampleAudio}}'
        ),
    }],
)


GENDER_STYLE = {
    "m": ("m.", "#5b9bd5"),  # soft blue
    "f": ("f.", "#e07b7b"),  # soft red
    "n": ("n.", "#555"),     # soft black
}


def _format_word_with_gender(word: str, gender: str | None) -> str:
    """Format word with colored gender prefix: 'f. chien'."""
    if gender and gender in GENDER_STYLE:
        abbrev, color = GENDER_STYLE[gender]
        return f'<span style="color:{color}; font-size:0.7em;">{abbrev}</span> {word}'
    return word


def _card_to_note(card: Card) -> tuple[genanki.Note, list[str]]:
    media_files = []

    audio_field = ""
    if card.audio_file and Path(card.audio_file).exists():
        audio_filename = Path(card.audio_file).name
        audio_field = f"[sound:{audio_filename}]"
        media_files.append(card.audio_file)

    image_field = ""
    if card.image_file and Path(card.image_file).exists():
        image_filename = Path(card.image_file).name
        image_field = f'<img src="{image_filename}" style="max-width:250px;">'
        media_files.append(card.image_file)

    example_audio_field = ""
    if card.target_example_audio and Path(card.target_example_audio).exists():
        example_audio_filename = Path(card.target_example_audio).name
        example_audio_field = f"[sound:{example_audio_filename}]"
        media_files.append(card.target_example_audio)

    source_display = _format_word_with_gender(card.source_word, card.source_gender)
    target_display = _format_word_with_gender(card.target_word or "", card.target_gender)
    target_plain = card.target_word or ""

    model = TYPING_MODEL if card.typing else BASIC_MODEL

    note = genanki.Note(
        model=model,
        fields=[
            source_display,
            target_display,
            card.target_pronunciation or "",
            card.target_example_sentence or "",
            card.source_example_sentence or "",
            card.target_mnemonic or "",
            card.target_origin or "",
            card.target_cognates or "",
            card.target_memory_hook or "",
            card.target_part_of_speech or "",
            audio_field,
            image_field,
            example_audio_field,
            target_plain,
        ],
        guid=genanki.guid_for(card.id),
    )
    return note, media_files


def export_apkg(
    cards: list[Card],
    output_path: Path,
    deck_name: str = "Vocabulary",
) -> None:
    deck_id = int(hashlib.md5(deck_name.encode()).hexdigest()[:8], 16)
    deck = genanki.Deck(deck_id, deck_name)

    all_media: list[str] = []
    for card in cards:
        note, media_files = _card_to_note(card)
        deck.add_note(note)
        all_media.extend(media_files)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    package = genanki.Package(deck)
    package.media_files = all_media
    package.write_to_file(str(output_path))
