PYTHON ?= python3
POETRY ?= poetry
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate

.PHONY: bootstrap
bootstrap:
	@test -d $(VENV) || ($(PYTHON) -m venv $(VENV))
	$(ACTIVATE) && pip install -U pip setuptools wheel
	$(ACTIVATE) && pip install -e .[dev]

.PHONY: run
run:
	@if [ ! -d $(VENV) ]; then echo "Virtualenv missing. Run 'make bootstrap' first."; exit 1; fi
	$(ACTIVATE) && uvicorn eco_api.main:app --reload --host 127.0.0.1 --port 8890

.PHONY: lint
lint:
	@if [ ! -d $(VENV) ]; then echo "Virtualenv missing. Run 'make bootstrap' first."; exit 1; fi
	$(ACTIVATE) && ruff check
	$(ACTIVATE) && mypy eco_api

.PHONY: test
test:
	@if [ ! -d $(VENV) ]; then echo "Virtualenv missing. Run 'make bootstrap' first."; exit 1; fi
	$(ACTIVATE) && pytest
