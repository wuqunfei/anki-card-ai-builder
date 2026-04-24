import json
import re
import unicodedata

import anthropic

from anki_builder.constants import MINIMAX_BASE_URL, MINIMAX_MODEL
from anki_builder.schema import Card

def _normalize(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, strip accents and punctuation."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) not in ("Mn", "Po", "Ps", "Pe"))
    return text.strip()


def _batch_cards(cards: list[Card], batch_size: int = 20) -> list[list[Card]]:
    return [cards[i:i + batch_size] for i in range(0, len(cards), batch_size)]


def _build_enrichment_prompt(cards: list[Card]) -> str:
    card_list = []
    for c in cards:
        entry = {
            "source_word": c.source_word,
            "source_language": c.source_language,
            "target_language": c.target_language,
        }
        if c.target_word:
            entry["target_word"] = c.target_word
        if c.target_pronunciation:
            entry["target_pronunciation"] = c.target_pronunciation
        if c.target_example_sentence:
            entry["target_example_sentence"] = c.target_example_sentence
        if c.source_example_sentence:
            entry["source_example_sentence"] = c.source_example_sentence
        card_list.append(entry)

    return (
        f"You are a friendly language tutor for kids aged 9-12.\n\n"
        f"For each word below, fill in the missing fields. Each word has its own "
        f"source_language and target_language — use them to determine translation direction. "
        f"Keep sentences simple, natural, and kid-friendly with "
        f"several emojis sprinkled in.\n\n"
        f"For EVERY word, you MUST generate:\n"
        f"- `target_part_of_speech`: the grammatical category (noun, verb, adjective, etc.)\n"
        f"- `source_gender`: grammatical gender of the source word if it's a noun (\"m\", \"f\", \"n\"), otherwise null\n"
        f"- `target_gender`: grammatical gender of the target word if it's a noun (\"m\", \"f\", \"n\"), otherwise null\n"
        f"- `target_mnemonic`: word breakdown as HTML with soft colored parts:\n"
        f'  prefix in soft blue: <span style="color:#5b9bd5">un-</span>\n'
        f'  root in soft coral: <span style="color:#e07b7b">break</span>\n'
        f'  suffix in soft green: <span style="color:#6dba6d">-able</span>\n'
        f"  Join parts with \" + \". ONLY provide a mnemonic if the word has meaningful parts "
        f"(prefixes, suffixes, or compound structure). If it's a simple word with no useful "
        f"breakdown (e.g. \"glove\", \"cat\", \"dog\"), set target_mnemonic to null.\n\n"
        f"For fields that are already filled, keep the existing value.\n"
        f"For missing fields, generate:\n"
        f"- `target_word`: translate source_word into the source_language\n"
        f"- `target_pronunciation`: IPA for English/French, pinyin with tone marks for Chinese\n"
        f"- `target_example_sentence`: a kid-friendly sentence in the TARGET language (the language of target_word) with emojis\n"
        f"- `source_example_sentence`: translation of that sentence into source_language, also kid-friendly with emojis\n\n"
        f"Return ONLY a JSON array with one object per word. Each object must have all fields: "
        f"source_word, target_word, target_pronunciation, target_example_sentence, "
        f"source_example_sentence, target_mnemonic, target_part_of_speech, source_gender, target_gender.\n\n"
        f"Words:\n{json.dumps(card_list, ensure_ascii=False)}"
    )


def _parse_enrichment_response(text: str) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def enrich_cards(
    cards: list[Card],
    minimax_api_key: str,
) -> list[Card]:
    to_enrich = [c for c in cards if c.status == "extracted"]
    already_done = [c for c in cards if c.status != "extracted"]

    if not to_enrich:
        return cards

    client = anthropic.Anthropic(
        api_key=minimax_api_key,
        base_url=MINIMAX_BASE_URL,
    )

    enriched: list[Card] = []
    for batch in _batch_cards(to_enrich):
        prompt = _build_enrichment_prompt(batch)
        response = client.messages.create(
            model=MINIMAX_MODEL,
            max_tokens=16384,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
                break
        items = _parse_enrichment_response(content)

        # Build lookup maps: exact match first, then normalized fallback
        item_map = {item["source_word"]: item for item in items if "source_word" in item}
        norm_map = {_normalize(item["source_word"]): item for item in items if "source_word" in item}

        for i, card in enumerate(batch):
            item = item_map.get(card.source_word) or norm_map.get(_normalize(card.source_word))
            # Positional fallback if word count matches
            if item is None and len(items) == len(batch) and i < len(items):
                item = items[i]

            if item is not None:
                update = {"status": "enriched"}
                for field in ["target_word", "target_pronunciation",
                              "target_example_sentence", "source_example_sentence"]:
                    if getattr(card, field) is None and field in item:
                        update[field] = item[field]
                for field in ["target_mnemonic", "target_part_of_speech",
                              "source_gender", "target_gender"]:
                    if field in item:
                        update[field] = item[field]
                enriched.append(card.model_copy(update=update))
            else:
                enriched.append(card)

    return already_done + enriched
