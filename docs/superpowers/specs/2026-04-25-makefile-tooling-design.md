# Makefile + Python Tooling — Design Spec

## Overview

Add a Makefile with dev workflow targets and configure Ruff (formatter + linter) and Mypy (type checker) as dev dependencies. All tools managed via uv and configured in `pyproject.toml`.

## Files

### Create: `Makefile`

Dev workflow targets:

| Target | Command | Description |
|--------|---------|-------------|
| `install` | `uv sync` | Install all dependencies including dev |
| `fmt` | `uv run ruff format src/ tests/` | Format code with Ruff |
| `lint` | `uv run ruff check src/ tests/` | Lint code with Ruff (no auto-fix) |
| `typecheck` | `uv run mypy src/` | Type check with Mypy |
| `test` | `uv run pytest` | Run tests |
| `check` | `lint` + `typecheck` + `test` | Run all checks in sequence |

### Modify: `pyproject.toml`

**Dev dependencies** — add to `[dependency-groups] dev`:
- `ruff>=0.11`
- `mypy>=1.15`

**Ruff config** — `[tool.ruff]` section:
- `target-version = "py312"`
- `line-length = 120`
- `[tool.ruff.lint]` select = `["E", "F", "I"]` (pycodestyle errors, pyflakes, isort)

**Mypy config** — `[tool.mypy]` section:
- `python_version = "3.12"`
- `warn_unused_ignores = true`
- `ignore_missing_imports = true` (many deps like genanki, gtts lack type stubs)

### Modify: `README.md`

Update the Contributing section to use `make` commands:

```markdown
## Contributing

```bash
# Install dev dependencies
make install

# Format code
make fmt

# Run all checks (lint + typecheck + test)
make check
```

Issues and pull requests are welcome.
```
