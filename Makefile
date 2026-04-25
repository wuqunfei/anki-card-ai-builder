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
