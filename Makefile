.PHONY: help install dev db-up db-migrate db-down api test lint clean test-data

# Default target
help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  dev        Install dev dependencies"
	@echo "  db-up      Start Postgres via Docker Compose"
	@echo "  db-down    Stop Postgres"
	@echo "  db-migrate Run Alembic migrations (upgrade head)"
	@echo "  api        Start Uvicorn server (reload)"
	@echo "  test       Run pytest"
	@echo "  lint       Run ruff check and black --check"
	@echo "  format     Run ruff check --fix and black"
	@echo "  clean      Remove __pycache__ and .pytest_cache"
	@echo "  test-data  Create test project/story/scene and export IDs"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

db-up:
	docker compose up -d

db-down:
	docker compose down

db-migrate:
	alembic upgrade head

api:
	uvicorn app.main:app --reload

test:
	pytest -q

lint:
	ruff check .
	black --check .

format:
	ruff check --fix .
	black .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

test-data:
	python scripts/create_test_data.py
