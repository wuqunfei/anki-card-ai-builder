# Gemini Enrichment Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google Gemini as an optional enrichment provider alongside MiniMax, selected via `ENRICH_PROVIDER` environment variable.

**Architecture:** Add a `_enrich_gemini` function using the `google-genai` SDK (already a dependency). Introduce a provider dispatch dict in `enrich/ai.py` (matching the pattern in `media/image.py`). Update `enrich_cards()` to accept a provider name and route to the correct backend. Wire up config and CLI call sites.

**Tech Stack:** Python, google-genai SDK, Anthropic SDK (existing), pytest

---

### File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/anki_builder/constants.py` | Modify | Add `GEMINI_ENRICH_MODEL` constant |
| `src/anki_builder/config.py` | Modify | Add `enrich_provider` config field |
| `src/anki_builder/enrich/ai.py` | Modify | Add Gemini provider function, provider dispatch |
| `src/anki_builder/cli.py` | Modify | Pass provider + correct API key to `enrich_cards` |
| `.env.example` | Modify | Add `ENRICH_PROVIDER` |
| `tests/test_enrich_ai.py` | Modify | Add tests for Gemini enrichment + provider dispatch |

---

### Task 1: Add constant and config

**Files:**
- Modify: `src/anki_builder/constants.py`
- Modify: `src/anki_builder/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Add Gemini enrichment model constant**

In `src/anki_builder/constants.py`, add after line 3:

```python
GEMINI_ENRICH_MODEL = "gemini-3-flash-preview"
```

- [ ] **Step 2: Add `enrich_provider` to Config**

In `src/anki_builder/config.py`, inside `Config.__init__`, add after line 15 (`self.image_provider = ...`):

```python
        self.enrich_provider = os.environ.get("ENRICH_PROVIDER", "minimax")  # "minimax" or "gemini"
```

- [ ] **Step 3: Update `.env.example`**

In `.env.example`, add after the `IMAGE_PROVIDER=gemini` line:

```
ENRICH_PROVIDER=minimax
```

- [ ] **Step 4: Commit**

```bash
git add src/anki_builder/constants.py src/anki_builder/config.py .env.example
git commit -m "feat: add ENRICH_PROVIDER config and Gemini model constant"
```

---

### Task 2: Write failing tests for Gemini enrichment

**Files:**
- Modify: `tests/test_enrich_ai.py`

- [ ] **Step 1: Write test for Gemini provider enrichment**

Add to `tests/test_enrich_ai.py` at the end of the `TestAIEnrichment` class (before the `if __name__` block):

```python
    @patch("anki_builder.enrich.ai.genai")
    def test_enrich_cards_gemini(self, mock_genai_module):
        mock_client = MagicMock()
        mock_genai_module.Client.return_value = mock_client

        enriched_data = json.dumps(
            [
                {
                    "source_word": "dog",
                    "target_word": "Hund",
                    "target_pronunciation": "/dɒɡ/",
                    "target_example_sentence": "The dog loves to play in the park! 🐕",
                    "source_example_sentence": "Der Hund spielt gern im Park! 🐕",
                    "target_mnemonic": '<span style="color:red">dog</span>',
                    "target_part_of_speech": "noun",
                }
            ]
        )

        mock_response = MagicMock()
        mock_response.text = enriched_data
        mock_client.models.generate_content.return_value = mock_response

        cards = [Card(source_word="dog", target_language="en")]
        result = enrich_cards(cards, api_key="test-google-key", provider="gemini")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_word, "Hund")
        self.assertEqual(result[0].target_pronunciation, "/dɒɡ/")
        self.assertIn("🐕", result[0].target_example_sentence)
        self.assertEqual(result[0].target_part_of_speech, "noun")
        self.assertEqual(result[0].status, "enriched")
```

- [ ] **Step 2: Update existing MiniMax test to use new signature**

In the existing `test_enrich_cards` method, change line 64 from:

```python
        result = enrich_cards(cards, minimax_api_key="test-key")
```

to:

```python
        result = enrich_cards(cards, api_key="test-key", provider="minimax")
```

- [ ] **Step 3: Write test for default provider (minimax)**

Add to the test class:

```python
    @patch("anki_builder.enrich.ai.anthropic")
    def test_enrich_cards_default_provider_is_minimax(self, mock_anthropic_module):
        mock_client = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        enriched_data = json.dumps(
            [{"source_word": "cat", "target_word": "Katze", "target_part_of_speech": "noun"}]
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=enriched_data)]
        mock_client.messages.create.return_value = mock_response

        cards = [Card(source_word="cat", target_language="en")]
        result = enrich_cards(cards, api_key="test-key")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_word, "Katze")
        mock_anthropic_module.Anthropic.assert_called_once()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/test_enrich_ai.py -v`
Expected: FAIL — `enrich_cards` does not accept `provider` or `api_key` kwargs yet.

- [ ] **Step 5: Commit failing tests**

```bash
git add tests/test_enrich_ai.py
git commit -m "test: add failing tests for Gemini enrichment provider"
```

---

### Task 3: Implement Gemini enrichment provider and dispatch

**Files:**
- Modify: `src/anki_builder/enrich/ai.py`

- [ ] **Step 1: Add Gemini import and provider functions**

At the top of `src/anki_builder/enrich/ai.py`, add to imports:

```python
from google import genai
from google.genai import types

from anki_builder.constants import GEMINI_ENRICH_MODEL, MINIMAX_BASE_URL, MINIMAX_MODEL
```

(Replace the existing `from anki_builder.constants import MINIMAX_BASE_URL, MINIMAX_MODEL` line.)

- [ ] **Step 2: Add `_enrich_minimax` function**

Add after `_parse_enrichment_response`, before `enrich_cards`:

```python
def _enrich_minimax(batch: list[Card], api_key: str) -> list[dict]:
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=MINIMAX_BASE_URL,
    )
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
    return _parse_enrichment_response(content)
```

- [ ] **Step 3: Add `_enrich_gemini` function**

Add right after `_enrich_minimax`:

```python
def _enrich_gemini(batch: list[Card], api_key: str) -> list[dict]:
    client = genai.Client(api_key=api_key)
    prompt = _build_enrichment_prompt(batch)
    response = client.models.generate_content(
        model=GEMINI_ENRICH_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=16384,
            temperature=0.3,
        ),
    )
    return _parse_enrichment_response(response.text or "")
```

- [ ] **Step 4: Add provider dispatch dict**

Add after `_enrich_gemini`:

```python
PROVIDERS = {
    "minimax": _enrich_minimax,
    "gemini": _enrich_gemini,
}
```

- [ ] **Step 5: Refactor `enrich_cards` to use provider dispatch**

Replace the entire `enrich_cards` function with:

```python
def enrich_cards(
    cards: list[Card],
    api_key: str,
    provider: str = "minimax",
) -> list[Card]:
    to_enrich = [c for c in cards if c.status == "extracted"]
    already_done = [c for c in cards if c.status != "extracted"]

    if not to_enrich:
        return cards

    enrich_fn = PROVIDERS.get(provider, _enrich_minimax)

    enriched: list[Card] = []
    for batch in _batch_cards(to_enrich):
        items = enrich_fn(batch, api_key)

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
                for field in [
                    "target_word",
                    "target_pronunciation",
                    "target_example_sentence",
                    "source_example_sentence",
                ]:
                    if getattr(card, field) is None and field in item:
                        update[field] = item[field]
                for field in [
                    "target_mnemonic",
                    "target_origin",
                    "target_cognates",
                    "target_memory_hook",
                    "target_part_of_speech",
                    "source_gender",
                    "target_gender",
                ]:
                    if field in item:
                        update[field] = item[field]
                enriched.append(card.model_copy(update=update))
            else:
                enriched.append(card)

    return already_done + enriched
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_enrich_ai.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/anki_builder/enrich/ai.py
git commit -m "feat: add Gemini enrichment provider with dispatch"
```

---

### Task 4: Update CLI call sites

**Files:**
- Modify: `src/anki_builder/cli.py`

- [ ] **Step 1: Update enrichment call in the `auto` command (line 183)**

Change:

```python
        enriched = enrich_cards(merged, config.minimax_api_key)
```

to:

```python
        enrich_key = config.google_api_key if config.enrich_provider == "gemini" else config.minimax_api_key
        enriched = enrich_cards(merged, api_key=enrich_key, provider=config.enrich_provider)
```

- [ ] **Step 2: Update enrichment call in the `enrich` command (line 328)**

Change:

```python
    enriched = enrich_cards(cards, config.minimax_api_key)
```

to:

```python
    enrich_key = config.google_api_key if config.enrich_provider == "gemini" else config.minimax_api_key
    enriched = enrich_cards(cards, api_key=enrich_key, provider=config.enrich_provider)
```

- [ ] **Step 3: Add key validation for enrichment provider**

In the `enrich` command, before calling `enrich_cards`, add:

```python
    if config.enrich_provider == "gemini":
        config.require_google_key()
    else:
        config.require_minimax_key()
```

And in the `auto` command, similarly before the enrichment step, add:

```python
    if config.enrich_provider == "gemini":
        config.require_google_key()
    else:
        config.require_minimax_key()
```

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/anki_builder/cli.py
git commit -m "feat: wire Gemini enrichment provider into CLI commands"
```

---

### Task 5: Update CLI tests for new signature

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Check and update mock patches in test_cli.py**

The mock `@patch("anki_builder.cli.enrich_cards")` should still work since we're patching the import. Verify no tests pass `minimax_api_key` as a positional arg. If any test calls `enrich_cards` directly with the old signature, update to use `api_key=` and `provider=` kwargs.

- [ ] **Step 2: Check and update test_integration.py**

Same check — the `@patch("anki_builder.cli.enrich_cards")` mock should still work. Verify tests pass.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: Run linting**

Run: `ruff check src/ tests/`
Expected: No errors.

- [ ] **Step 5: Commit (if changes needed)**

```bash
git add tests/
git commit -m "test: update CLI and integration tests for new enrich_cards signature"
```
