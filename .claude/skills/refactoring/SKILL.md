---
name: refactoring
description: >
  Use when the user shares Python code and asks to clean it up, improve it,
  make it more readable, refactor it, or apply clean code principles.
  Also trigger when code is pasted with implicit improvement intent
  ("this is messy", "can you improve this?") or when asking about naming,
  function design, type hints, docstrings, or Pythonic idioms.
---

# Python Refactoring Skill

Transform working but messy Python into clean, idiomatic code — then explain what changed and why so the user learns.

## Guiding Principles

- **DRY** — Every piece of knowledge has a single, unambiguous representation. Eliminate duplication through abstraction, but don't abstract prematurely.
- **KISS** — Prefer the simplest solution that works. Avoid unnecessary complexity.
- **SoC** — Separate distinct concerns into distinct sections. Don't over-modularize.
- **Zen of Python** — Explicit > implicit. Simple > complex. Readability counts. (`import this`)

## Naming

| Rule | Bad | Good |
|------|-----|------|
| Descriptive nouns for variables | `d = 5` | `elapsed_days = 5` |
| Pronounceable names | `genyyyymmdd` | `generation_date` |
| No ambiguous abbreviations | `fna`, `cre_tmstp` | `first_name`, `creation_timestamp` |
| Consistent vocabulary | `client_name` / `customer_age` | `client_name` / `client_age` |
| Booleans as questions | `valid` | `is_valid`, `has_permission` |
| Verbs for functions | `data()` | `fetch_data()`, `parse_config()` |
| No synonyms for same concept | `get_name()` / `fetch_age()` | `get_name()` / `get_age()` |
| Nouns for classes | `DoStuff` | `PaymentProcessor` |
| Constants in UPPER_SNAKE_CASE | `return randint(0, 36)` | `POCKET_COUNT = 36` |
| No redundant context | `person.person_name` | `person.name` |

## Function Design

- **Single responsibility** — If you describe it with "and", split it.
- **Short and focused** — Roughly 20 lines max; readable without scrolling.
- **Minimize arguments** — Ideally 1-2; group 3+ into a dataclass or config object.
- **Guard clauses** — Return/raise early to avoid deep nesting.
- **No flags** — A boolean parameter means the function does two things. Split it:
  ```python
  # Bad
  def transform(text, uppercase):
      if uppercase:
          return text.upper()
      return text.lower()

  # Good
  def uppercase(text): return text.upper()
  def lowercase(text): return text.lower()
  ```
- **No side effects** — Don't modify global state or do unrelated I/O beyond the function's stated purpose.

## Pythonic Idioms

- **Comprehensions** over loop-append: `[x*2 for x in items]`
- **`enumerate()`** over `range(len())` for indexed iteration
- **`zip()`** for parallel iteration
- **Context managers** (`with`) for files, locks, connections — guarantees cleanup
- **Tuple unpacking**: `first, *rest = items`; `a, b = b, a`
- **f-strings** over `.format()` or `%`
- **`dict.get(key, default)`** for safe access with fallback
- **`any()` / `all()`** over manual boolean-accumulator loops
- **`dataclasses.dataclass`** for data-holding classes — eliminates boilerplate `__init__`
- **Generators** (`yield`) for lazy sequences that don't need to live in memory
- **Decorators** for cross-cutting concerns (auth, logging, caching) — applies SoC
- **Specific exception types** — bare `except:` swallows bugs silently

## Type Hints & Docstrings

- Annotate all function parameters and return types
- Use `str | None` (3.10+) or `Optional[str]` for older targets
- Use `list[str]`, `dict[str, int]` — not raw `list`/`dict`
- Google-style docstrings for non-trivial functions and public APIs:
  ```python
  def process_order(order_id: int, discount: float = 0.0) -> dict:
      """Process a customer order and return the result.

      Args:
          order_id: The unique identifier for the order.
          discount: Fractional discount to apply (0.0-1.0).

      Returns:
          A dict with keys 'total', 'status', and 'items'.

      Raises:
          ValueError: If order_id is negative or discount is out of range.
      """
  ```

## Comments

- **Don't comment bad code — rewrite it.** If code needs a comment to explain *what* it does, the code itself is unclear.
- **Clean code rarely needs comments.** Use them for *why*, not *what*.
- **No noise comments** — Don't restate what the code obviously does.
- **No commented-out code** — Delete it; version control has history.

## SOLID (for classes)

| Principle | Rule |
|-----------|------|
| **Single Responsibility** | A class has one reason to change |
| **Open-Closed** | Open for extension, closed for modification |
| **Liskov Substitution** | Subclasses must be usable wherever the parent is expected |
| **Interface Segregation** | Don't force clients to implement unused methods |
| **Dependency Inversion** | Depend on abstractions, not concretions |

## Workflow

1. **Read** the code end-to-end before touching anything.
2. **Identify** the most impactful issues across all dimensions above.
3. **Refactor** — preserve behavior exactly. Refactoring is not the time to add features.
4. **Present** the result:

   ### Refactored Code
   ```python
   # ... improved code
   ```

   ### What Changed & Why
   Group changes by theme (naming, functions, idioms, types). For each change, explain *why* it's better — not just what you did.

## Watch Out

- **Don't break behavior.** If unsure what code does, ask first.
- **Don't over-engineer.** Match solution complexity to problem complexity.
- **Preserve style preferences** (quotes, spacing) unless they violate PEP 8.
- **Flag suspicious code** in a "Heads up" note — don't silently "fix" possible bugs.
- **Design or critical issues** — Flag and confirm with the user before changing; continue cosmetic refactoring but fix affected unit tests.
- **If it's already clean**, say so. Don't manufacture fake improvements.