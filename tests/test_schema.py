import unittest
from anki_builder.schema import Card


class TestCard(unittest.TestCase):
    def test_create_full_card(self):
        card = Card(
            source_word="accomplish",
            source_language="de",
            target_language="en",
        )
        self.assertEqual(card.source_word, "accomplish")
        self.assertEqual(card.source_language, "de")
        self.assertEqual(card.target_language, "en")
        self.assertEqual(card.status, "extracted")
        self.assertIsNotNone(card.id)
        self.assertIsNone(card.target_word)
        self.assertIsNone(card.target_pronunciation)
        self.assertIsNone(card.target_example_sentence)
        self.assertIsNone(card.source_example_sentence)
        self.assertIsNone(card.target_mnemonic)
        self.assertIsNone(card.target_part_of_speech)
        self.assertIsNone(card.unit)
        self.assertIsNone(card.reference)
        self.assertIsNone(card.source_gender)
        self.assertIsNone(card.target_gender)
        self.assertEqual(card.tags, [])

    def test_card_id_is_uuid(self):
        import uuid
        card = Card(source_word="test", source_language="de", target_language="en")
        uuid.UUID(card.id)

    def test_card_serialization_roundtrip(self):
        card = Card(
            source_word="Hund",
            source_language="de",
            target_language="en",
            target_word="dog",
        )
        data = card.model_dump()
        card2 = Card(**data)
        self.assertEqual(card, card2)

    def test_new_optional_fields(self):
        card = Card(
            source_word="maison",
            source_language="de",
            target_language="fr",
            unit="Unité 1",
            reference="Page 162",
            source_gender="f",
            target_gender="f",
        )
        self.assertEqual(card.unit, "Unité 1")
        self.assertEqual(card.reference, "Page 162")
        self.assertEqual(card.source_gender, "f")
        self.assertEqual(card.target_gender, "f")

    def test_target_language_required(self):
        with self.assertRaises(Exception):
            Card(source_word="test")

    def test_typing_defaults_to_false(self):
        card = Card(source_word="test", source_language="de", target_language="en")
        self.assertFalse(card.typing)

    def test_typing_can_be_set_true(self):
        card = Card(source_word="test", source_language="de", target_language="en", typing=True)
        self.assertTrue(card.typing)

    def test_typing_roundtrip(self):
        card = Card(source_word="test", source_language="de", target_language="en", typing=True)
        data = card.model_dump()
        card2 = Card(**data)
        self.assertTrue(card2.typing)


if __name__ == "__main__":
    unittest.main()
