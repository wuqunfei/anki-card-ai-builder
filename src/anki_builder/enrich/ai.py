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
        entry = {"word": c.word, "target_language": c.target_language}
        if c.translation:
            entry["translation"] = c.translation
        if c.pronunciation:
            entry["pronunciation"] = c.pronunciation
        if c.example_sentence:
            entry["example_sentence"] = c.example_sentence
        if c.sentence_translation:
            entry["sentence_translation"] = c.sentence_translation
        card_list.append(entry)

    return (
        f"You are a friendly language tutor for German-speaking kids aged 9-12.\n\n"
        f"For each word below, fill in the missing fields. The source language is "
        f"'{source_language}'. Keep sentences simple, natural, and kid-friendly with "
        f"serval emojis sprinkled in.\n\n"
        f"For EVERY word, you MUST generate:\n"
        f"- `part_of_speech`: the grammatical category (noun, verb, adjective, etc.)\n"
        f"- `mnemonic`: word breakdown as HTML with soft colored parts:\n"
        f'  prefix in soft blue: <span style="color:#5b9bd5">un-</span>\n'
        f'  root in soft coral: <span style="color:#e07b7b">break</span>\n'
        f'  suffix in soft green: <span style="color:#6dba6d">-able</span>\n'
        f"  Join parts with \" + \". ONLY provide a mnemonic if the word has meaningful parts "
        f"(prefixes, suffixes, or compound structure). If it's a simple word with no useful "
        f"breakdown (e.g. \"glove\", \"cat\", \"dog\"), set mnemonic to null.\n\n"
        f"For fields that are already filled, keep the existing value.\n"
        f"For missing fields, generate:\n"
        f"- `translation`: translate to {source_language}\n"
        f"- `pronunciation`: IPA for English/French, pinyin with tone marks for Chinese\n"
        f"- `example_sentence`: a kid-friendly sentence with emojis\n"
        f"- `sentence_translation`: translation of the example to {source_language}, also kid-friendly with emojis\n\n"
        f"Return ONLY a JSON array with one object per word. Each object must have all fields: "
        f"word, translation, pronunciation, example_sentence, sentence_translation, mnemonic, part_of_speech.\n\n"
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
        # Find the text block (skip ThinkingBlock if present)
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
                break
        items = _parse_enrichment_response(content)

        # Match enriched items back to cards
        item_map = {item["word"]: item for item in items if "word" in item}
        for card in batch:
            if card.word in item_map:
                item = item_map[card.word]
                update = {"status": "enriched"}
                for field in ["translation", "pronunciation", "example_sentence",
                              "sentence_translation"]:
                    if getattr(card, field) is None and field in item:
                        update[field] = item[field]
                # Always overwrite these
                for field in ["mnemonic", "part_of_speech"]:
                    if field in item:
                        update[field] = item[field]
                enriched.append(card.model_copy(update=update))
            else:
                enriched.append(card)

    return already_done + enriched
