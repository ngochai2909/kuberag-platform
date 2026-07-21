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
	uv run ruff check apps/rag-api/src apps/rag-api/tests

format:
	uv run ruff format apps/rag-api/src apps/rag-api/tests

format-check:
	uv run ruff format --check apps/rag-api/src apps/rag-api/tests

typecheck:
	uv run mypy apps/rag-api/src apps/rag-api/tests

check: lint format-check typecheck test

lock:
	uv lock

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name .coverage -delete
