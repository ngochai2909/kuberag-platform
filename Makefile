.PHONY: setup run test test-cov lint format format-check typecheck check lock clean

setup:
	uv sync --group dev

run:
	uv run uvicorn app.main:app --reload --host $${APP_HOST:-0.0.0.0} --port $${APP_PORT:-8000}

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

typecheck:
	uv run mypy src tests

check: lint format-check typecheck test

lock:
	uv lock

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name .coverage -delete
