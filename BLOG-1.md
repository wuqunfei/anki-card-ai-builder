# ankids: Building AI-Powered Anki Cards for My Daughter in a Weekend

> *126 commits. Three days. One real user: my daughter.*

---

## A Note Before We Begin

Every line of code in this project is, at its core, an act of care.

We live in an age that is extraordinarily good at capturing attention — headlines, notifications, feeds that refresh forever. It is very easy to spend a weekend consuming the world's problems without solving any of them. At some point I asked myself a simple question: *what if I put that time somewhere that actually matters?*

My daughter was struggling with French vocabulary. Not dramatically — she is fine, school is fine — but I could see the friction. New words that didn't stick. Flashcard apps that didn't match her textbook. That small, persistent friction that accumulates over months into a reluctance to try.

I didn't want to worry about whether an AI tool could handle this, or whether the `.apkg` format was too obscure, or whether it was worth building something no one else would ever use. I just wanted to build it. The decision to create something new — instead of waiting for a perfect plan, instead of over-thinking the tradeoffs — is the most underrated move in any maker's toolkit.

So I opened my laptop on a Friday evening and started coding.

By Sunday night, she had a deck of 80 personalized French vocabulary cards — complete with AI-generated cartoon illustrations, pronunciation audio, color-coded etymology breakdowns, and mnemonics tuned to her level. She opened Anki on her iPad, flipped through a few cards, and looked up with a grin.

*"Papa, this one has a funny picture."*

That was it. That was the whole return on investment. Every overnight commit, every refactored function, every dollar spent on API calls — worth it.

The technical story follows. But that's what it was really about.

---

## The Problem: School Vocabulary Is a Moving Target

My daughter started learning French at school this year. Like most kids, she struggles to remember new vocabulary — especially the words that don't map cleanly onto anything she already knows.

The obvious answer was Anki. Spaced repetition is one of the few learning strategies backed by decades of cognitive science research, and the Anki ecosystem is mature: desktop app, iPhone, Android, all synced. But when we browsed the [Anki shared deck library](https://ankiweb.net/shared/info/1104981491), we ran into a familiar problem: the decks available don't match her textbook. The cards skip the vocabulary her class is actually studying this week. The audio quality is inconsistent. There are no images. And the cards are designed for adults — no emojis, no fun, no memory hooks.

Making good flashcards by hand is genuinely tedious. For each word you need: a translation, IPA pronunciation, an example sentence, a counter-example, and ideally an image and audio clip. Add etymology and mnemonic cues and you're looking at 20–30 minutes per word. For a class with 40 new words per unit, that's not a Saturday afternoon — it's a part-time job.

The question I asked myself on a Friday evening: *what if I could just point a tool at her textbook pages and get a ready-to-import Anki deck with everything already filled in?*

---

## The Insight: Don't Rebuild the Wheel, Just Feed It Better

Every parent who has tried to build "a better Anki" ends up rebuilding Anki. There are graveyard repositories full of custom flashcard web apps, iPad quiz builders, and vocabulary trainers that died when the developer got a job offer. The Anki ecosystem already solved the hard problems: mobile sync, spaced repetition algorithms, offline support, shared decks. What it lacks is *personalized content generation*.

The key insight was to stay entirely within the `.apkg` format — Anki's portable deck package — and treat content generation as a pure upstream problem. `ankids` doesn't compete with Anki; it feeds it.

The opportunity opened up across three AI capabilities that have matured significantly this year:

1. **Vision models** can OCR a photo of a textbook page and extract structured vocabulary data — words, translations, example sentences — in one pass.
2. **Language models** can enrich that raw data with etymology, morpheme breakdowns, IPA pronunciation, cognates, and kid-friendly mnemonics at the batch level.
3. **Image and audio models** can generate a cartoon illustration and a TTS audio clip for every word in seconds.

None of these capabilities are novel individually. What `ankids` does is wire them into a coherent, resumable pipeline that outputs a standard `.apkg` file.

---

## System Design

### The 5-Step Pipeline

![ankids 5-step pipeline diagram](docs/diagrams/pipeline.svg)

Each step reads and writes a shared `cards.json` file inside an isolated workspace folder. This means every step is independently restartable — if image generation hits a rate limit at card 847 out of 1,000, you just re-run `ankids media` and it resumes from where it left off.

### Input Sources

The ingestion layer accepts six source types, dispatched by detecting the input path: `--words` (CSV), Excel/CSV files, PDFs, single image files, folders of images/PDFs, and Google Drive URLs. A single `_detect_input_type()` function inspects the path string and routes to the appropriate handler.

HEIC support (iPhone's native photo format) was a deliberate design choice. My daughter's textbook lives on an iPhone camera roll. The pipeline handles HEIC → Gemini Vision OCR → structured JSON in one step via `pillow-heif`.

### External Services

![External API services diagram](docs/diagrams/services.svg)


MiniMax serves dual duty as the enrichment LLM (accessed via the Anthropic SDK's `base_url` override — a neat trick for compatible providers) and as the primary image generator. Google Gemini handles OCR and acts as the image generation fallback. If either provider rate-limits, the pipeline falls back to the other automatically.

### Card Lifecycle

![Card lifecycle state diagram](docs/diagrams/card-lifecycle.svg)

### Workspace Layout

Each pipeline run creates an isolated, UUID-scoped directory:

```
workspace/
└── a1b2c3d4/
    ├── cards.json               ← single source of truth
    ├── media/
    │   ├── {uuid}_audio.mp3     ← word TTS
    │   ├── {uuid}_example_audio.mp3
    │   └── {uuid}_image.png     ← AI cartoon
    └── MyDeck.apkg              ← ready to import
```

This isolation means you can run multiple decks in parallel without collisions, and the workspace persists between sessions — critical when a batch of 1,000 image generations takes hours and you need to close your laptop.

---

## The Data Model: A Card Is More Than a Word

The `Card` Pydantic model is the core contract across every stage of the pipeline. Here's the full schema:

```python
class Card(BaseModel):
    # Metadata
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit: str | None = None          # e.g. "Unité 3"
    reference: str | None = None     # e.g. "Page 42"
    status: str = STATUS_EXTRACTED   # extracted → enriched → complete
    tags: list[str] = Field(default_factory=list)
    audio_file: str | None = None
    image_file: str | None = None

    # Source (native language)
    source_word: str
    source_language: str = "de"
    source_gender: str | None = None          # "m", "f", "n"
    source_example_sentence: str | None = None

    # Target (learning language)
    target_word: str | None = None
    target_language: str
    target_gender: str | None = None
    target_pronunciation: str | None = None   # IPA or Pinyin
    target_part_of_speech: str | None = None
    target_example_sentence: str | None = None
    target_example_audio: str | None = None
    target_synonyms: str | None = None
    target_antonyms: str | None = None

    # Etymology & Mnemonics
    target_mnemonic: str | None = None       # color-coded morpheme breakdown
    target_origin: str | None = None         # PIE → Latin → Old French chain
    target_cognates: str | None = None       # EN/DE/FR/Latin cognates
    target_memory_hook: str | None = None    # one-line hook referencing morphemes

    # Card type
    typing: bool = False                     # True = type-in-answer card
```

Card merging is keyed on `(source_word, target_language)`. Re-ingesting the same word list never overwrites existing enrichment or media — new words are added, existing cards are preserved. This is what makes iterative deck-building practical.

---

## The Etymology Engine: Making Words Stick

This is the feature I'm most proud of, and the one that took the most prompt engineering to get right.

The core insight: for Western European languages, a large fraction of vocabulary shares Latin or Greek roots. A child who understands that *in-* means "not" and *-croy-* comes from *credere* ("to believe") can decode *incroyable* even if they've never seen it before. That's not just memorization — it's linguistic intuition.

The enrichment prompt instructs the AI to produce four distinct etymology fields for every card, each rendered with carefully chosen color semantics:

| Field | Color scheme | Purpose |
|---|---|---|
| `target_mnemonic` | Blue prefix · Coral root · Green suffix | Morpheme breakdown |
| `target_origin` | Gold tones, warm gradient | PIE → Latin → Old French chain |
| `target_cognates` | Purple tones | EN / DE / FR / Latin cognate family |
| `target_memory_hook` | Morpheme colors | One-line hook using the breakdown |

Here's what the prompt generates for *incroyable* (French for "incredible"):

```
Mnemonic:    <span color="#5b9bd5">in-</span> + <span color="#e07b7b">croy</span> + <span color="#6dba6d">-able</span>

Origin:      <span color="#8B6914">PIE *krey-</span> →
             <span color="#B8860B">Latin credere</span> →
             <span color="#D4A854">Old French incroyable</span>

Cognates:    <span color="#8e7cc3">EN</span> incredible,
             <span color="#a78bfa">DE</span> unglaublich,
             <span color="#7c3aed">LA</span> incredibilis

Memory hook: <span color="#5b9bd5">in-</span> = not +
             <span color="#e07b7b">croy</span> = believe +
             <span color="#6dba6d">-able</span> = can be → "not believable!"
```

This HTML renders directly inside Anki's card template — no post-processing needed. The card template references each etymology field with `{{#TargetMnemonic}}...{{/TargetMnemonic}}` conditional blocks, so the etymology section is silently absent for truly atomic words where breakdown doesn't apply.

The gender coloring follows the same system: masculine nouns get a soft blue prefix (*m.*), feminine a coral red (*f.*), and neuter a neutral grey — consistent with the morpheme color palette so learners build the same visual association across all card layers.

---

## The Anki Card Template

The card template is pure HTML/CSS embedded in the `.apkg` via `genanki`. Here's the full card anatomy — front and back — with all the layers labeled:

![ankids card anatomy — front and back](docs/diagrams/card-anatomy.svg)

The front shows the target word in a large bold font with IPA pronunciation, part-of-speech, an AI-generated cartoon image, and a TTS audio button. The back reveals all four etymology layers — each field is conditionally rendered so atomic words (without useful breakdown) don't show empty sections.

A separate "Type-in" card variant flips the front to show the source word and asks the learner to type the target word before revealing the answer. The `typing: bool` flag on the `Card` model drives the template selection at export time.

---

## Building It: 126 Commits Over Three Days

Andrew Ng said it well in his [2024 talk on AI-assisted development](https://www.youtube.com/watch?v=RNJCfif1dPY): the bottleneck in software is no longer typing speed or even design — it's the speed at which you can iterate on ideas and validate them against reality. With AI agents as collaborators, the iteration loop collapses from days to hours.

Here's the actual commit activity for the sprint, with Monday's design-spec work and Thursday's first-feature work distributed proportionally across the three coding days:

![Weekend coding sprint commit chart](docs/diagrams/commit-chart.svg)

The Monday spike is the initial design phase: architecture documents, Pydantic schema drafts, and prompt specs written before a single line of runtime code existed. By Thursday evening the first real feature — image OCR via Gemini — was committed at **21:30**. By 03:19 on Friday morning, the refactoring pass that introduced shared constants, proper API key validation, and `ClickException` handling was done. Those 14 commits between midnight and 3am represent the kind of flow state that only happens when the implementation is validating itself in real time.

Saturday was the refinement sprint: docs, workspace isolation, the Gemini enrichment provider, incremental media saves. By Sunday morning the MVP was in the hands of my first user.

Total: **126 commits** across a working week, with the heaviest sustained work between **Thursday night and Saturday evening**. The longest coding session ran from **00:30 to 03:19** — five hours of pure refactoring energy while the rest of the house slept.

The experience of working with 10 concurrent AI agents on a codebase this size is genuinely different from solo development. The bottleneck shifts from *writing code* to *making decisions*. Every agent can produce working code in seconds; what takes time is deciding which design to accept, which edge case to prioritize, which abstraction level to commit to. Three days of that is exhausting in a way that three days of solo coding isn't — not physically, but cognitively. Your brain never rests.

---

## Before and After: Real Cards

Here's what the Anki shared deck community provides out of the box:

![Standard shared Anki card — plain text, no image, no audio, no etymology](docs/before.png)

A text-only card with a translation and nothing else. Functional, but forgettable.

Here's what `ankids` generates from the same vocabulary:

![AI-generated ankids card — cartoon image, color-coded etymology, IPA, example sentences](docs/after.png)

The same word, now with: an AI-generated cartoon illustration sized for the card, IPA pronunciation, grammatical gender colored by convention, color-coded morpheme breakdown, origin chain to Proto-Indo-European, cognates across four languages, a memory hook, and a bilingual example sentence with TTS audio on both the word and the sentence.

The visual difference is stark. More importantly, the cognitive load difference is real — a card that tells you *why* a word looks the way it does is orders of magnitude easier to retain than one that just restates the definition.

---

## Hard Lessons Learned

### 1. Local Image Models: Your MacBook Is Not a GPU Server

The project started with the ambition of running image generation locally. My Mac Mini (M4, 16 GB unified memory) is a capable machine for coding — it handled 10 parallel AI coding agents without breaking a sweat for days.

![Mac Mini M4 — great for coding, not for local image generation](docs/mac-mini.jpg)

For image generation, it's a different story. The current generation of open image models — Stable Diffusion XL, Flux, and Google's new Gemma 4 — all require more than 16 GB of VRAM to run at usable quality and speed. On 16 GB of unified memory shared with the OS, the models either refuse to load or produce results at a rate of one image every 3–4 minutes. For a deck of 1,000 words, that's days of runtime.

The pragmatic decision: use cloud APIs. The machine memory constraint is a genuine hardware problem, not a software one.

### 2. The $84 Image Generation Bill

The initial implementation used Google Gemini for image generation with aggressive async concurrency. Gemini's image model is exceptional quality — but it's not cheap at scale, and "scale" in this context means approximately 1,000 cards for a complete deck.

![Google Gemini API cost breakdown after generating ~1,000 card images](docs/google-gemini-cost.png)

A single weekend run cost **$84** in image generation API calls alone. The async pipeline was working exactly as designed — hitting the API at maximum concurrency — which turned out to be both technically impressive and financially alarming.

The fix was straightforward: switch the primary image provider to [MiniMax image-01](https://www.minimax.io), which offers comparable quality at a fraction of the cost. Gemini was demoted to fallback status, triggered only when MiniMax fails. The provider dispatch is a simple dictionary lookup:

```python
PROVIDERS = {
    "minimax": _generate_minimax,
    "gemini":  _generate_gemini,
}
```

The `IMAGE_PROVIDER` environment variable selects the primary; the fallback tries the other automatically. A rate-limit (`429`) from either provider halts the batch gracefully and saves progress — because the state file is written after every card, nothing is lost.

**Lesson:** Async image generation is fast and expensive. Set `MEDIA_CONCURRENCY=3` and monitor your spend before unleashing it on a 1,000-card deck.

### 3. Handschuhe and the Literal AI Imagination

The funniest failure mode: I asked the image model to illustrate the German word *Handschuhe* (gloves).

The model returned this:

![AI-generated illustration for 'Handschuhe' — a hand and a shoe, literally](docs/Handschuhe.png)

*Handschuhe* literally translates as "hand shoes" (*Hand* + *Schuhe*). The model, unfamiliar with the compound convention, illustrated a hand and a shoe. Side by side. Smiling.

The fix was to pass the *target language* to the image prompt and explicitly instruct the model to illustrate the concept, not decode the word:

```python
def _build_image_prompt(word: str, target_language: str) -> str:
    lang = _lang_full_name(target_language)  # "German" → full name
    return (
        f"A single cute, kid-friendly cartoon illustration representing "
        f"the {lang} word '{word}'. "
        f"Kid-friendly, colorful, clean background. "
        f"Pure illustration only — no text, letters, labels, "
        f"captions, or speech bubbles."
    )
```

Passing the language name in full ("German" rather than "de") dramatically reduced literal interpretations. The "no text" constraint was equally important — early versions produced images with the word itself overlaid in the illustration, which cluttered the card and created a circular hint.

### 4. The Hidden Cost of Continuous Refactoring

Here's the raw git ledger for the entire project:

| Metric | Count |
|---|---|
| Total commits | 126 |
| Lines of code added | 15,558 |
| Lines of code deleted | 9,760 |
| Net codebase size | 5,798 lines |
| Refactor / fix / clean commits | 42 out of 126 (33%) |

Those 9,760 deleted lines are not a mistake — they are the *cost of moving fast*. But they are a real cost, in both money and attention.

When you work with AI agents at high velocity, the instinct is to ship first, clean later. Agents are happy to generate large blobs of code — CLI handlers, test suites, config migrations — without first checking whether an existing module already covers the ground. The result is duplication that compounds. Two commits later you're unifying three slightly different prompt-building functions into one, or ripping out a YAML config system you wrote at 2am to replace it with a `.env` loader that's half the size.

A few of the most expensive cleanup commits illustrate the pattern:

- `"Clean the docs"` — **3,505 lines deleted**, 143 added. A documentation folder that grew organically during the sprint was purged to remove 20+ intermediate planning files.
- `"Create MVP in first day"` — **3,224 lines deleted**, 24 added. A complete rewrite of the initial prototype, removing code that had been superseded by a cleaner design.
- `"refactor: eliminate duplication across enrich, ingest, and CLI modules"` — 95 lines deleted, 230 added. The classic sign of premature copy-paste: three modules had independently evolved their own JSON parsing helpers.

The pattern is visible in the commit graph. Every burst of feature work — 9 commits between midnight and 3am on Friday — is followed the next morning by a refactoring pass that deletes 20–30% of what was just written. The code is clean by Saturday, but the cycle repeated.

**The structural fix** is to use a `review` skill or refactoring pass *before* adding more features, not after. In practice, asking an agent to audit for duplication before writing new code cuts the churn dramatically. Treating a "code review" prompt as a mandatory gate — not an optional afterthought — is the discipline that makes the difference between a clean MVP and a weekend project that's embarrassing to open-source.

**Lesson:** Deleted lines cost roughly the same as written lines. In a 3-day sprint with 10 agents, 9,760 deleted lines represents real API spend and real cognitive re-review. Planning even 10 minutes of "does this already exist?" before each new module pays for itself many times over.

### 5. The Cognitive Cost of AI-Accelerated Development

Three days of parallel AI-assisted development taught me something I wasn't expecting: the exhaustion is real, but it's not physical. When agents can generate working code in seconds, the bottleneck becomes *you* — your ability to evaluate, reject, redirect, and integrate in a continuous stream.

Every 10 minutes brings a new design question that would previously have taken a day of background thinking to resolve. Do you batch enrichment calls or process cards one at a time? Do you store media file paths as absolute or relative? Do you merge cards by word string or UUID? These decisions compound. Make a bad one and you're refactoring state management at 2am on Saturday while your daughter sleeps.

The pace is exhilarating. It is also, genuinely, exhausting. I finished the MVP on Sunday morning and slept for most of the afternoon. Andrew Ng is right that AI collapses the time-to-prototype — but the cognitive budget is still yours to spend.

---

## Get Started

Install and configure:

```bash
# Install with uv (Python 3.12+)
uv sync

# Copy and fill in your API keys
cp .env.example .env
```

The minimal `.env`:

```
MINIMAX_API_KEY=your_minimax_key
GOOGLE_API_KEY=your_google_key
LEARNER_PROFILE="ages 9-12, kid-friendly with emojis"
```

### One-command pipeline

```bash
# From a word list — creates a new workspace automatically
ankids run --words "chat,maison,incroyable,bonjour" --lang-target fr --lang-source de

# From iPhone photos of textbook pages (HEIC OCR)
ankids run --input ./input/french/ --lang-target fr --lang-source de --deck "Unité 3"

# From a PDF textbook
ankids run --input textbook.pdf --lang-target fr --lang-source de

# From an Excel vocabulary list
ankids run --input vocab.xlsx --lang-target fr --lang-source de
```

The `run` command prints the workspace path. Add `--output workspace/<uuid>` to resume:

```bash
# Add more words to an existing workspace (incremental)
ankids run --words "école,professeur" --lang-target fr --output workspace/a1b2c3d4
```

### Step-by-step pipeline

```bash
# 1. Extract words from a folder of textbook photos
ankids ingest --input ./input/french/ --lang-target fr --lang-source de
#   ↳ Created new workspace: workspace/a1b2c3d4

# 2. Enrich all cards with AI (etymology, IPA, examples)
ankids enrich --output workspace/a1b2c3d4

# 3. Generate TTS audio and cartoon images
ankids media --output workspace/a1b2c3d4

# 4. Review card quality before exporting
ankids review --output workspace/a1b2c3d4

# 5. Export to Anki
ankids export --output workspace/a1b2c3d4 --deck "French Unit 3"
#   ↳ Done! Created workspace/a1b2c3d4/French Unit 3.apkg
```

### Cost-control flags

```bash
# Text-only cards (no image API calls)
ankids run --words "chat,chien" --lang-target fr --no-images

# Cards with images but no audio
ankids run --words "chat,chien" --lang-target fr --no-audio

# Spelling practice: type-in-the-answer cards
ankids run --words "chat,chien" --lang-target fr --typing

# Low concurrency for cost control
IMAGE_PROVIDER=minimax MEDIA_CONCURRENCY=2 ankids media --output workspace/a1b2c3d4
```

### CLI reference

| Command | What it does | `--output` |
|---|---|---|
| `run` | Full pipeline: ingest + enrich + media | Optional (auto-creates) |
| `ingest` | Extract words from file, folder, or CLI | Optional (auto-creates) |
| `enrich` | Fill all card fields with AI | Required |
| `media` | Generate TTS audio and AI images | Required |
| `review` | Display all cards and media status | Required |
| `export` | Bundle into `.apkg` for Anki | Required |
| `clean` | Delete workspace and start fresh | Required |

---

## What's Next

The MVP is working and in the hands of one real user. A few directions I'm considering:

**More language support.** The enrichment pipeline is already language-agnostic — you just set `--lang-target`. Adding tested support for Spanish, Italian, and Mandarin is mostly a matter of testing gTTS coverage and adjusting the IPA/Pinyin prompt instructions.

**Better card templates.** The current HTML template is functional but minimal. A redesign with cleaner typography, better image scaling, and dark-mode support would make the cards noticeably more pleasant to study.

**Smarter image prompts.** The Handschuhe failure points to a general problem: compound words and idiomatic expressions need a concept-level summary rather than a literal word prompt. One approach is to use the enriched `target_mnemonic` or `target_memory_hook` as the image prompt input instead of the raw word.

**Deck diffing.** Right now, re-importing an updated `.apkg` into Anki requires manually handling duplicates. A proper diff-and-patch workflow — tracking cards by their stable UUID across exports — would make iterative deck updates seamless.

**A curriculum planner.** The ultimate version generates an entire semester's worth of decks from a syllabus PDF, pre-scheduled to align with the school timetable so cards arrive in Anki the week before they appear in class.

---

## Stack at a Glance

| Layer | Technology |
|---|---|
| CLI | Typer + Python 3.12 |
| Schema / validation | Pydantic v2 |
| Image OCR | Google Gemini 3 Flash (vision) |
| AI enrichment | MiniMax M2.5 (via Anthropic SDK) |
| Image generation | MiniMax image-01 (primary) / Gemini 3.1 Flash (fallback) |
| Audio | gTTS |
| Anki packaging | genanki |
| PDF extraction | PyMuPDF |
| HEIC support | pillow-heif |
| Async HTTP | httpx + asyncio |
| Linting / types | ruff + mypy |
| Package management | uv + hatchling |

---

*The project is open source. Pull requests are welcome — especially from parents who have already survived a weekend of AI-assisted engineering and lived to tell the story.*
