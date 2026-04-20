import hashlib
from pathlib import Path

import genanki

from anki_builder.schema import Card

# Stable model ID derived from a hash so it's consistent across runs
MODEL_ID = int(hashlib.md5(b"anki-builder-model-v1").hexdigest()[:8], 16)

CARD_MODEL = genanki.Model(
    MODEL_ID,
    "Anki Builder Card",
    fields=[
        {"name": "Word"},
        {"name": "Translation"},
        {"name": "Pronunciation"},
        {"name": "ExampleSentence"},
        {"name": "SentenceTranslation"},
        {"name": "Mnemonic"},
        {"name": "PartOfSpeech"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[{
        "name": "Card 1",
        "qfmt": (
            '<div style="text-align:center; font-size:24px; margin:20px;">'
            "{{Word}}"
            "</div>"
            '<div style="text-align:center;">{{Image}}</div>'
            '<div style="text-align:center;">{{Audio}}</div>'
        ),
        "afmt": (
            '{{FrontSide}}<hr id="answer">'
            '<div style="text-align:center; font-size:20px; color:#333;">{{Translation}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{Pronunciation}}</div>'
            '<div style="text-align:center; font-size:14px; margin:10px;">{{Mnemonic}}</div>'
            '<div style="text-align:center; font-size:16px; margin:10px;">{{ExampleSentence}}</div>'
            '<div style="text-align:center; font-size:14px; color:#666;">{{SentenceTranslation}}</div>'
            '<div style="text-align:center; font-size:12px; color:#999;">{{PartOfSpeech}}</div>'
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
            card.word,
            card.translation or "",
            card.pronunciation or "",
            card.example_sentence or "",
            card.sentence_translation or "",
            card.mnemonic or "",
            card.part_of_speech or "",
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
