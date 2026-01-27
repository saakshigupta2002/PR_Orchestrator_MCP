PYTHON ?= python
PIP ?= pip

.PHONY: help install test lint typecheck format precommit run

help:
	@echo "Available targets:"
	@echo "  install     - Install the project and development dependencies"
	@echo "  test        - Run the unit and integration tests"
	@echo "  lint        - Run ruff for linting and formatting checks"
	@echo "  format      - Format the codebase using ruff"
	@echo "  typecheck   - Run mypy for static type checking"
	@echo "  precommit   - Run all pre-commit hooks"
	@echo "  run         - Start the MCP server over stdio"

install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

test:
	$(PYTHON) -m pytest -q

lint:
	@echo "Running ruff lint..."
	$(PYTHON) -m ruff check src/pr_orchestrator tests

format:
	@echo "Running ruff format..."
	$(PYTHON) -m ruff format src/pr_orchestrator tests

typecheck:
	$(PYTHON) -m mypy src/pr_orchestrator

precommit:
	$(PYTHON) -m pre_commit run --all-files

run:
	$(PYTHON) -m pr_orchestrator.server