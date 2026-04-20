import unittest
from anki_builder.schema import Card


class TestCard(unittest.TestCase):
    def test_create_full_card(self):
        card = Card(
            word="accomplish",
            source_language="de",
            target_language="en",
            source="vocab.xlsx",
        )
        self.assertEqual(card.word, "accomplish")
        self.assertEqual(card.source_language, "de")
        self.assertEqual(card.target_language, "en")
        self.assertEqual(card.status, "extracted")
        self.assertIsNotNone(card.id)
        self.assertIsNone(card.translation)
        self.assertIsNone(card.pronunciation)
        self.assertIsNone(card.example_sentence)
        self.assertIsNone(card.sentence_translation)
        self.assertIsNone(card.mnemonic)
        self.assertIsNone(card.part_of_speech)
        self.assertEqual(card.tags, [])

    def test_card_id_is_uuid(self):
        import uuid
        card = Card(word="test", source_language="de", target_language="en", source="test")
        uuid.UUID(card.id)  # Raises if not valid UUID

    def test_card_serialization_roundtrip(self):
        card = Card(
            word="Hund",
            source_language="de",
            target_language="en",
            translation="dog",
            source="vocab.xlsx",
        )
        data = card.model_dump()
        card2 = Card(**data)
        self.assertEqual(card, card2)


if __name__ == "__main__":
    unittest.main()
