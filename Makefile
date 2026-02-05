.PHONY: help install install-back install-front dev dev-install dev-back dev-arize dev-front db-up db-migrate db-down api ui kill test lint clean test-data

# Default target
VENV := venv
PYTHON := $(shell if [ -d $(VENV) ]; then echo $(VENV)/bin/python; else echo python3; fi)
PIP := $(shell if [ -d $(VENV) ]; then echo $(VENV)/bin/pip; else echo python3 -m pip; fi)

help:
	@echo "Available commands:"
	@echo "  install    Install backend + frontend dependencies"
	@echo "  install-back Install backend dependencies"
	@echo "  install-front Install frontend dependencies"
	@echo "  dev        Show dev commands"
	@echo "  dev-install Install dev dependencies"
	@echo "  dev-back   Run backend only"
	@echo "  dev-arize  Run backend with Arize Phoenix (requires Docker)"
	@echo "  dev-front  Run frontend only"
	@echo "  db-up      Start Postgres via Docker Compose"
	@echo "  db-down    Stop Postgres"
	@echo "  db-migrate Run Alembic migrations (upgrade head)"
	@echo "  api        Start Uvicorn server (reload)"
	@echo "  ui         Start Next.js dev server"
	@echo "  test       Run pytest"
	@echo "  lint       Run ruff check and black --check"
	@echo "  format     Run ruff check --fix and black"
	@echo "  clean      Remove __pycache__ and .pytest_cache"
	@echo "  test-data  Create test project/story/scene and export IDs"

install: install-back install-front

install-back:
	$(PIP) install -e .

install-front:
	@if [ ! -d frontend/node_modules ]; then \
		echo "Installing frontend dependencies..."; \
		npm --prefix frontend install; \
	else \
		echo "Frontend dependencies already installed."; \
	fi

dev-install:
	$(PIP) install -e ".[dev]"

db-up:
	docker compose up -d

db-down:
	docker compose down

db-migrate:
	$(PYTHON) -m alembic upgrade head

api:
	$(PYTHON) -m uvicorn app.main:app --reload

ui:
	npm --prefix frontend run dev

dev:
	@echo "Use one of:"
	@echo "  make dev-back   # backend only"
	@echo "  make dev-arize  # backend with phoenix"
	@echo "  make dev-front  # frontend only"

dev-back:
	@echo "Starting backend..."
	$(PYTHON) -m uvicorn app.main:app --reload

dev-arize:
	docker compose up -d phoenix
	@echo "Starting backend with Phoenix OTEL endpoint..."
	PHOENIX_OTEL_ENDPOINT=http://localhost:6006/v1/traces $(PYTHON) -m uvicorn app.main:app --reload

dev-front: ui

kill:
	@echo "Stopping backend (uvicorn) and frontend (next dev)..."
	@pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	@pkill -f "npm --prefix frontend run dev" 2>/dev/null || true
	@pkill -f "node .*next" 2>/dev/null || true
	@echo "Done."

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m black .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

test-data:
	$(PYTHON) scripts/create_test_data.py
