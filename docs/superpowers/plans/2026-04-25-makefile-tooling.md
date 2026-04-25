# Makefile + Python Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ruff (formatter + linter), Mypy (type checker), and a Makefile with dev workflow targets.

**Architecture:** Add ruff and mypy as dev dependencies in `pyproject.toml`, configure both tools in the same file, create a `Makefile` with targets for install/fmt/lint/typecheck/test/check, and update README contributing section.

**Tech Stack:** Ruff, Mypy, Make, uv

**Spec:** `docs/superpowers/specs/2026-04-25-makefile-tooling-design.md`

---

### Task 1: Add dev dependencies and tool config to pyproject.toml

**Files:**
- Modify: `pyproject.toml:28-31` (dev dependencies and add new sections)

- [ ] **Step 1: Add ruff and mypy to dev dependencies**

In `pyproject.toml`, replace the `[dependency-groups]` section and add tool config at the end:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "ruff>=0.11",
    "mypy>=1.15",
]

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.mypy]
python_version = "3.12"
warn_unused_ignores = true
ignore_missing_imports = true
```

- [ ] **Step 2: Install the new dependencies**

Run: `uv sync`
Expected: ruff and mypy are installed without errors.

- [ ] **Step 3: Verify tools are available**

Run: `uv run ruff --version && uv run mypy --version`
Expected: Both print version numbers (ruff 0.11.x, mypy 1.15.x or similar).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add ruff and mypy as dev dependencies"
```

---

### Task 2: Run formatters and fix existing code

**Files:**
- Modify: any files in `src/` and `tests/` that ruff or mypy flag

- [ ] **Step 1: Run ruff format to auto-format all code**

Run: `uv run ruff format src/ tests/`
Expected: Shows which files were reformatted (if any).

- [ ] **Step 2: Run ruff lint check**

Run: `uv run ruff check src/ tests/`
Expected: Either clean or shows fixable issues.

- [ ] **Step 3: Auto-fix any lint issues**

Run: `uv run ruff check src/ tests/ --fix`
Expected: Fixes applied. Re-run `uv run ruff check src/ tests/` — should be clean.

- [ ] **Step 4: Run mypy**

Run: `uv run mypy src/`
Expected: May show type errors. Note them — fix only obvious/simple ones. Complex type errors can be addressed later.

- [ ] **Step 5: Commit formatting and lint fixes**

```bash
git add -A
git commit -m "style: apply ruff formatting and lint fixes"
```

---

### Task 3: Create the Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create the Makefile**

Create `Makefile` with this exact content:

```makefile
.PHONY: install fmt lint typecheck test check

install:
	uv sync

fmt:
	uv run ruff format src/ tests/

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/

test:
	uv run pytest

check: lint typecheck test
```

**Important:** Makefile rules require real tab characters for indentation, not spaces.

- [ ] **Step 2: Verify all targets work**

Run each target:

Run: `make install`
Expected: Dependencies install successfully.

Run: `make fmt`
Expected: Shows formatting results (likely "X files left unchanged").

Run: `make lint`
Expected: Clean — no lint errors.

Run: `make typecheck`
Expected: Mypy runs (may have some warnings, should not crash).

Run: `make test`
Expected: Tests run and pass.

Run: `make check`
Expected: Runs lint, typecheck, and test in sequence.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: add Makefile with dev workflow targets"
```

---

### Task 4: Update README contributing section

**Files:**
- Modify: `README.md:252-260` (Contributing section)

- [ ] **Step 1: Update the Contributing section**

Replace the Contributing section in `README.md` with:

````markdown
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
````

- [ ] **Step 2: Verify the file looks correct**

Run: `grep -A 12 "## Contributing" README.md`
Expected: Shows the updated contributing section with make commands.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update contributing section with make commands"
```
