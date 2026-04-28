# CLI Migration: Click to Typer

## Goal

Migrate the CLI framework from Click to Typer for better UX: auto-completion, better help output, type-safe arguments via Python type hints. Rename the command from `anki-builder` to `ankids`.

## Approach

Direct 1:1 translation of Click decorators to Typer equivalents. No structural changes to the codebase (single `cli.py` file). No Rich output additions. Business logic remains untouched.

## Dependency Changes

- Remove: `click>=8.1`
- Add: `typer>=0.15`
- Entry point rename: `anki-builder` -> `ankids`

```toml
[project.scripts]
ankids = "anki_builder.cli:main"
```

## Command Migration Pattern

All 7 commands (`run`, `ingest`, `enrich`, `media`, `review`, `export`, `clean`) follow the same translation pattern.

### Click -> Typer Mapping

| Click | Typer |
|-------|-------|
| `@cli.command()` | `@app.command()` |
| `@click.option("--x", required=True)` | `x: str = typer.Option(..., help="...")` |
| `@click.option("--x", default=val)` | `x: str = typer.Option(val, help="...")` |
| `@click.option("--x", is_flag=True)` | `x: bool = typer.Option(False, help="...")` |
| `click.echo(msg)` | `print(msg)` |
| `click.confirm(msg)` | `typer.confirm(msg)` |
| `click.style(...)` | Keep as `print()` for now |
| Custom `OrderedGroup` | Remove (Typer preserves definition order) |

### App Initialization

```python
import typer

app = typer.Typer(help="Ankids - AI-powered Anki card builder")

def main():
    app()
```

### Example Command Translation

Before:
```python
@cli.command()
@click.option("--input", type=str, help="Input file or folder")
@click.option("--lang-target", required=True, help="Target language")
@click.option("--typing", is_flag=True, help="Type-in cards")
def ingest(input, lang_target, typing, ...):
    ...
```

After:
```python
@app.command()
def ingest(
    input: Optional[str] = typer.Option(None, help="Input file or folder"),
    lang_target: str = typer.Option(..., help="Target language"),
    typing: bool = typer.Option(False, help="Type-in cards"),
):
    ...
```

## Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Replace `click>=8.1` with `typer>=0.15`, rename entry point to `ankids` |
| `src/anki_builder/cli.py` | Replace Click decorators with Typer equivalents, remove `OrderedGroup`, keep all business logic |
| `tests/test_cli.py` | Rewrite using `typer.testing.CliRunner` against the Typer `app` |

## Test Migration

Replace Click's `CliRunner` with Typer's:

```python
from typer.testing import CliRunner
from anki_builder.cli import app

runner = CliRunner()
result = runner.invoke(app, ["ingest", "--lang-target", "en"])
```

## What Stays the Same

- All 7 commands and their option names
- All business logic (ingest, enrich, media, review, export, clean modules)
- Output style (print statements)
- Entry point module location (`anki_builder.cli:main`)

## What Changes for Users

- Command name: `anki-builder` -> `ankids`
- Better auto-generated `--help` formatting
- Shell auto-completion via `ankids --install-completion`
