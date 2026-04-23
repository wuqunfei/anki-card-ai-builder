import json
import re

import anthropic

from anki_builder.schema import Card

MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"


def _batch_cards(cards: list[Card], batch_size: int = 20) -> list[list[Card]]:
    return [cards[i:i + batch_size] for i in range(0, len(cards), batch_size)]


def _build_enrichment_prompt(cards: list[Card], source_language: str) -> str:
    card_list = []
    for c in cards:
        entry = {"source_word": c.source_word, "target_language": c.target_language}
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
        f"You are a friendly language tutor for German-speaking kids aged 9-12.\n\n"
        f"For each word below, fill in the missing fields. The source language is "
        f"'{source_language}'. Keep sentences simple, natural, and kid-friendly with "
        f"serval emojis sprinkled in.\n\n"
        f"For EVERY word, you MUST generate:\n"
        f"- `target_part_of_speech`: the grammatical category (noun, verb, adjective, etc.)\n"
        f"- `target_mnemonic`: word breakdown as HTML with soft colored parts:\n"
        f'  prefix in soft blue: <span style="color:#5b9bd5">un-</span>\n'
        f'  root in soft coral: <span style="color:#e07b7b">break</span>\n'
        f'  suffix in soft green: <span style="color:#6dba6d">-able</span>\n'
        f"  Join parts with \" + \". ONLY provide a mnemonic if the word has meaningful parts "
        f"(prefixes, suffixes, or compound structure). If it's a simple word with no useful "
        f"breakdown (e.g. \"glove\", \"cat\", \"dog\"), set target_mnemonic to null.\n\n"
        f"For fields that are already filled, keep the existing value.\n"
        f"For missing fields, generate:\n"
        f"- `target_word`: translate to {source_language}\n"
        f"- `target_pronunciation`: IPA for English/French, pinyin with tone marks for Chinese\n"
        f"- `target_example_sentence`: a kid-friendly sentence with emojis\n"
        f"- `source_example_sentence`: translation of the example to {source_language}, also kid-friendly with emojis\n\n"
        f"Return ONLY a JSON array with one object per word. Each object must have all fields: "
        f"source_word, target_word, target_pronunciation, target_example_sentence, "
        f"source_example_sentence, target_mnemonic, target_part_of_speech.\n\n"
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
    source_language: str = "de",
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
        prompt = _build_enrichment_prompt(batch, source_language)
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

        item_map = {item["source_word"]: item for item in items if "source_word" in item}
        for card in batch:
            if card.source_word in item_map:
                item = item_map[card.source_word]
                update = {"status": "enriched"}
                for field in ["target_word", "target_pronunciation",
                              "target_example_sentence", "source_example_sentence"]:
                    if getattr(card, field) is None and field in item:
                        update[field] = item[field]
                for field in ["target_mnemonic", "target_part_of_speech"]:
                    if field in item:
                        update[field] = item[field]
                enriched.append(card.model_copy(update=update))
            else:
                enriched.append(card)

    return already_done + enriched
