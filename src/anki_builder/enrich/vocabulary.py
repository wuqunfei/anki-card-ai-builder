import anthropic

from anki_builder.constants import MINIMAX_BASE_URL, MINIMAX_MODEL
from anki_builder.enrich import extract_response_text, parse_json_response

# Re-export for backward compatibility with tests
_parse_vocabulary_response = parse_json_response


def _build_text_prompt(text: str, target_language: str, source_language: str) -> str:
    return (
        f"Extract vocabulary words from the following text. The text is in "
        f"{target_language} (target language) and {source_language} (source language).\n\n"
        f"For each word, extract any available information: source_word, target_word, "
        f"target_pronunciation, target_example_sentence, target_part_of_speech.\n\n"
        f"Return ONLY a JSON array of objects. Each object should have the fields "
        f"that are present in the source. Do not generate content that isn't in "
        f"the source text — only extract what's there.\n\n"
        f"Text:\n{text}"
    )


def extract_vocabulary_with_ai(
    target_language: str,
    source_language: str,
    minimax_api_key: str = "",
    text: str | None = None,
) -> list[dict]:
    if not text:
        return []

    client = anthropic.Anthropic(api_key=minimax_api_key, base_url=MINIMAX_BASE_URL)
    response = client.messages.create(
        model=MINIMAX_MODEL,
        max_tokens=16384,
        messages=[
            {
                "role": "user",
                "content": _build_text_prompt(text, target_language, source_language),
            }
        ],
        temperature=0.1,
    )
    return parse_json_response(extract_response_text(response))
