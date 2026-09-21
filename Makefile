# Every routine action in this repo has a target here. If you add a workflow,
# add it here too, so humans and agents run the same commands.
.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help setup lint fmt test check run migrate clean

help:  ## Show this help
	@grep -hE '^[a-z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:  ## Install runtime and dev dependencies from uv.lock
	uv sync --group dev

lint:  ## Static checks, no files changed
	uv run ruff check .

fmt:  ## Apply safe lint fixes and format the files you touched
	uv run ruff check . --fix
	uv run ruff format .

# Note: the formatter has not been run across the whole repo yet, so `make fmt`
# produces a large diff. Pre-commit formats only the files in a commit, which is
# the intended adoption path.

test:  ## Offline tests: no Ollama, no database, no network
	uv run pytest

check: lint test  ## What CI runs

run:  ## Run the flow against the watchlist in src/main.py (needs Ollama)
	uv run python -m src.main

migrate:  ## Create the persistence tables (needs ALGO_TRADING_DATABASE_URL)
	psql "$$ALGO_TRADING_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/001_swing_sentry_tables.sql

clean:  ## Remove caches and build leftovers
	rm -rf .pytest_cache .ruff_cache src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
