VENV ?= .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest
COMPOSE = docker compose -f docker/docker-compose.yml --env-file .env

.PHONY: venv up down logs migrate test seed collections smoke ingest-all ingest-questionnaire ingest-notes extract-facts reflect-build install-hooks validate-commit governance

venv:
	python3 -m venv $(VENV)
	$(PIP) install -e '.[dev]'

install-hooks:
	./scripts/install_git_hooks.sh

validate-commit:
	./scripts/validate_conventional_commit.sh "$(MSG)"

governance: install-hooks
	./scripts/enforce_github_branch_protection.sh

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f mnemos

migrate:
	$(PYTHON) -m alembic upgrade head

test:
	$(PYTEST) -q

smoke:
	@live=$$(curl -s http://localhost:8000/health/live); \
	echo "$$live"; \
	ready=$$(curl -s http://localhost:8000/health/ready); \
	echo "$$ready"; \
	item=$$(curl -s -X POST http://localhost:8000/memory/items -H 'Content-Type: application/json' -d '{"domain":"self","kind":"note","statement":"Smoke test memory item for automated systems.","confidence":0.91,"metadata":{"source":"make_smoke"}}'); \
	echo "$$item"; \
	echo "$$item" > /tmp/mnemos-smoke-item.json; \
	item_id=$$($(PYTHON) -c "import json; print(json.load(open('/tmp/mnemos-smoke-item.json'))['id'])"); \
	curl -s http://localhost:8000/memory/item/$$item_id; echo; \
	curl -s -X POST http://localhost:8000/memory/query -H 'Content-Type: application/json' -d '{"query":"automated systems","domain":"self","top_k":3,"kinds":["note","fact","reflection"]}'; echo

seed:
	$(PYTHON) scripts/seed_memory.py

collections:
	$(PYTHON) scripts/create_qdrant_collections.py

ingest-all:
	$(VENV)/bin/mnemos ingest all

ingest-questionnaire:
	$(VENV)/bin/mnemos ingest questionnaire data/raw/questionnaire.md

ingest-notes:
	$(VENV)/bin/mnemos ingest notes data/raw/notes.jsonl

extract-facts:
	$(VENV)/bin/mnemos extract facts --domain self

reflect-build:
	$(VENV)/bin/mnemos reflect build --domain self
