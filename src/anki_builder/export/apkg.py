import hashlib
from pathlib import Path

import genanki

from anki_builder.schema import Card

MODEL_ID = int(hashlib.md5(b"anki-builder-model-v2").hexdigest()[:8], 16)

CARD_MODEL = genanki.Model(
    MODEL_ID,
    "Anki Builder Card",
    fields=[
        {"name": "SourceWord"},
        {"name": "TargetWord"},
        {"name": "TargetPronunciation"},
        {"name": "TargetExampleSentence"},
        {"name": "SourceExampleSentence"},
        {"name": "TargetMnemonic"},
        {"name": "TargetPartOfSpeech"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[{
        "name": "Card 1",
        "qfmt": (
            '<div style="text-align:center; font-size:24px; margin:20px;">'
            "{{SourceWord}}"
            "</div>"
            '<div style="text-align:center;">{{Image}}</div>'
            '<div style="text-align:center;">{{Audio}}</div>'
        ),
        "afmt": (
            '{{FrontSide}}<hr id="answer">'
            '<div style="text-align:center; font-size:20px; color:#333;">{{TargetWord}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{TargetPronunciation}}</div>'
            '<div style="text-align:center; font-size:14px; margin:10px;">{{TargetMnemonic}}</div>'
            '<div style="text-align:center; font-size:16px; margin:10px;">{{TargetExampleSentence}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{SourceExampleSentence}}</div>'
            '<div style="text-align:center; font-size:12px; color:#999;">{{TargetPartOfSpeech}}</div>'
        ),
    }],
)


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
        image_field = f'<img src="{image_filename}" style="max-width:350px;">'
        media_files.append(card.image_file)

    note = genanki.Note(
        model=CARD_MODEL,
        fields=[
            card.source_word,
            card.target_word or "",
            card.target_pronunciation or "",
            card.target_example_sentence or "",
            card.source_example_sentence or "",
            card.target_mnemonic or "",
            card.target_part_of_speech or "",
            audio_field,
            image_field,
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
