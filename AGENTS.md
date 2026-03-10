# Repository Guidelines

## Project Structure & Module Organization

- `api/`: FastAPI app, routes, schemas, dependency wiring.
- `services/`: orchestration for memory, retrieval, and governance flows.
- `db/`: SQLAlchemy models, repositories, sessions, and Alembic migrations in `migrations/`.
- `pipelines/`: batch logic for ingestion, fact extraction, reflection, and governance.
- `mcp_server/`: FastMCP server, REST client, and MCP tools.
- `tests/`: pytest suite for API, ingestion, MCP, reflections, and candidates.
- `docker/`, `scripts/`, `Makefile`: local runtime, bootstrap, and operator commands.
- `docs/`: phase specs and design notes. Keep raw user data out of Git;
  `data/raw/` is ignored.

## Build, Test, and Development Commands

- `make venv`: create `.venv` and install the project in editable mode
  with dev tools.
- `make up`: start PostgreSQL, Qdrant, and the API with Docker Compose.
- `make migrate`: apply Alembic migrations locally.
- `make test`: run `pytest -q`.
- `make smoke`: hit live health, create, and query endpoints against a running stack.
- `.venv/bin/pre-commit run --all-files`: run repo hooks (`ruff`, `mdl`, `pytest`).
- `.venv/bin/mnemos reflect build --domain self`: run the reflection pipeline locally.
- `.venv/bin/mnemos candidates list --status pending`: inspect governance candidates.

## Coding Style & Naming Conventions

- Use 2-space indentation in Python and Markdown-friendly wrapping in docs.
- Prefer short, explicit modules and repository/service names in `lower_snake_case`.
- Keep new file names descriptive, for example `validate_candidate.py`.
- Use `ruff` for Python linting and `mdl` for Markdown linting.
- Do not commit generated artifacts such as `*.egg-info`, `.venv/`, or local datasets.

## Testing Guidelines

- Tests use `pytest`; add new coverage under `tests/` as `test_<feature>.py`.
- Prefer focused API and service tests over broad integration-only coverage.
- Run `make test` before pushing; run `pre-commit` before opening a PR.
- If you add migrations, verify with `.venv/bin/python -m alembic upgrade head`.

## Commit & Pull Request Guidelines

- Follow Conventional Commits, for example `feat: implement phase 6 memory governance`.
- Work on short-lived branches and merge into `main` through PRs.
- PRs should include a short summary, verification commands, and any
  operational impact.
- Keep PRs scoped; do not mix unrelated refactors with feature work.

## Security & Configuration Tips

- Copy `.env.example` to `.env` for local work; Compose overrides
  container-only hosts.
- Never commit secrets, local questionnaire files, or contents of `data/raw/`.
- MCP tools should create candidates via governance endpoints, not write
  accepted memory directly.
