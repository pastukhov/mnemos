# Repository Guidelines

## Project Structure & Module Organization

- `api/`: FastAPI app, routes, schemas, dependency wiring.
- `core/`: Settings, logging, metrics, schema constants.
- `services/`: orchestration for memory, retrieval, and governance flows.
- `db/`: SQLAlchemy models, repositories, sessions, and Alembic migrations in `migrations/`.
- `vector/`: Qdrant wrapper and indexing helpers.
- `embeddings/`: Mock and OpenAI-compatible embedding providers.
- `pipelines/`: batch logic for ingestion (`ingest/`), fact extraction
  (`extract/`), reflection (`reflect/`), governance (`governance/`), and
  wiki generation (`wiki/`).
- `mcp_server/`: FastMCP server, REST client, and MCP tools.
- `tests/`: pytest suite for API, ingestion, MCP, reflections, and candidates.
- `docker/`, `scripts/`, `Makefile`: local runtime, bootstrap, and operator commands.
- `docs/`: phase specs and design notes. Keep raw user data out of Git;
  `data/raw/` is ignored.

## Build, Test, and Development Commands

- `make venv`: create `.venv` and install the project in editable mode
  with dev tools.
- `make up`: start PostgreSQL, Qdrant, and the API with Docker Compose.
- `docker compose -f docker-compose.local-mock.yml -f docker-compose.yml up`:
  run with mock OpenAI API (no API key needed).
- `make migrate`: apply Alembic migrations locally (`alembic.ini` points to `migrations/`).
- `make test`: run `pytest -q`.
- `make smoke`: hit live health, create, and query endpoints against a running stack.
- `make install-hooks`: install pre-commit hook (ruff, mdl, pytest) AND
  commit-msg hook (Conventional Commits format).
- `make seed`: seed demo memory items (requires `make collections` first).
- `make collections`: create Qdrant collections before seeding.
- `.venv/bin/mnemos ingest all`: ingest questionnaire and notes sources.
- `.venv/bin/mnemos extract facts --domain self`: run fact extraction pipeline.
- `.venv/bin/mnemos reflect build --domain self`: run reflection pipeline.
- `.venv/bin/mnemos candidates list --status pending`: inspect governance candidates.
- `.venv/bin/mnemos mcp-server`: start MCP server with stdio transport.

## Local Quality Gates

Pre-commit hooks: `ruff` (Python lint), `mdl` (Markdown lint), `pytest -q` (tests).
Commit-msg hook: validates Conventional Commits format (e.g., `feat:`, `fix:`, `docs:`).

**Important**: CI only runs `pytest -q`. Ruff and mdl are NOT enforced in CI.
Always run `.venv/bin/pre-commit run --all-files` locally before opening a PR.

## Coding Style & Naming Conventions

- Use 2-space indentation in Python; wrap Markdown at ~88 chars.
- Modules and repository/service names in `lower_snake_case`.
- New file names should be descriptive (e.g., `validate_candidate.py`).
- Use `ruff` for Python linting and `mdl` for Markdown linting.
- Do not commit generated artifacts (`*.egg-info`, `.venv/`, local
  datasets, `data/raw/` contents).

## Testing Guidelines

- Tests use `pytest`; add coverage under `tests/` as `test_<feature>.py`.
- Prefer focused API and service tests over broad integration-only coverage.
- Run `make test` before pushing; run `pre-commit` before opening a PR.
- After adding migrations, verify with `.venv/bin/python -m alembic upgrade head`.

## Versioning & Release

- `scripts/next_version.py` computes the next version on main branch push.
- Version workflow auto-tags `main` and triggers Docker image build.
- Docker image uses `docker/Dockerfile` and publishes to GHCR.
- Release workflow builds and pushes on git tags matching `v*`.

## Commit & Pull Request Guidelines

- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Work on short-lived branches; merge into `main` through PRs.
- Keep PRs scoped; do not mix unrelated refactors with feature work.
- PRs should include a short summary, verification commands, and operational impact.

## Security & Configuration

- Copy `.env.example` to `.env` for local work; Compose overrides
  container-only hosts.
- Never commit secrets, local questionnaire files, or contents of `data/raw/`.
- MCP tools must create candidates via governance endpoints, never write
  accepted memory directly.
- Settings are loaded from `.env` via `pydantic_settings` (`core/config.py`).
