from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import text

from api.deps import get_checked_governance_service, get_checked_memory_service
from api.schemas import (
  ImportApplyResponse,
  ImportPreviewRequest,
  ImportPreviewResponse,
  MemoryItemResponse,
  WebDomainSummary,
  WebListItemsResponse,
  WebOverviewResponse,
)
from core.config import ALLOWED_DOMAINS
from services.memory_governance_service import MemoryGovernanceService
from services.memory_service import MemoryService
from services.user_import_service import UserImportService

router = APIRouter(tags=["web"])
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def web_app() -> HTMLResponse:
  return HTMLResponse(build_shell())


@router.get("/ui/static/{asset_name}", include_in_schema=False)
def web_static(asset_name: str) -> FileResponse:
  if asset_name not in {"app.css", "app.js"}:
    raise HTTPException(status_code=404, detail="asset not found")
  asset_path = STATIC_DIR / asset_name
  if not asset_path.exists():
    raise HTTPException(status_code=404, detail="asset not found")
  media_type = "text/css" if asset_name.endswith(".css") else "application/javascript"
  return FileResponse(asset_path, media_type=media_type)


@router.get("/ui/api/overview", response_model=WebOverviewResponse, include_in_schema=False)
def web_overview(
  request: Request,
  governance_service: MemoryGovernanceService = Depends(get_checked_governance_service),
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> WebOverviewResponse:
  postgres_status = "ok"
  qdrant_status = "ok"
  try:
    with request.app.state.session_factory() as session:
      session.execute(text("SELECT 1"))
  except Exception:  # pragma: no cover - mirrors readiness behavior
    postgres_status = "failed"

  try:
    request.app.state.qdrant.ping()
  except Exception:  # pragma: no cover - mirrors readiness behavior
    qdrant_status = "failed"

  domains = [
    WebDomainSummary(domain=domain, items_total=len(memory_service.list_items_by_domain(domain)))
    for domain in ALLOWED_DOMAINS
  ]
  pending_candidates = len(governance_service.list_candidates(status="pending"))
  overall = "ready" if postgres_status == "ok" and qdrant_status == "ok" else "degraded"
  return WebOverviewResponse(
    status=overall,
    checks={"postgres": postgres_status, "qdrant": qdrant_status},
    domains=domains,
    pending_candidates=pending_candidates,
    features=[
      "поиск по смыслу",
      "ручное добавление записей",
      "импорт текста и файлов",
      "review кандидатов",
    ],
  )


@router.get("/ui/api/items", response_model=WebListItemsResponse, include_in_schema=False)
def web_list_items(
  domain: str = Query(default="self"),
  kind: str | None = Query(default=None),
  limit: int = Query(default=24, ge=1, le=100),
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> WebListItemsResponse:
  if domain not in ALLOWED_DOMAINS:
    raise HTTPException(status_code=422, detail="unsupported domain")
  items = memory_service.list_items_by_domain(domain)
  if kind is not None:
    items = [item for item in items if item.kind == kind]
  items = list(reversed(items))[:limit]
  return WebListItemsResponse(items=[MemoryItemResponse.model_validate(item) for item in items])


@router.post("/ui/api/import/preview", response_model=ImportPreviewResponse, include_in_schema=False)
def web_import_preview(
  payload: ImportPreviewRequest,
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> ImportPreviewResponse:
  preview = UserImportService(memory_service).preview(
    content=payload.content,
    filename=payload.filename,
    domain=payload.domain,
    kind=payload.kind,
  )
  return ImportPreviewResponse(
    detected_format=preview.detected_format,
    items=preview.items,
    warnings=preview.warnings,
    truncated=preview.truncated,
  )


@router.post("/ui/api/import/apply", response_model=ImportApplyResponse, include_in_schema=False)
def web_import_apply(
  payload: ImportPreviewRequest,
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> ImportApplyResponse:
  applied = UserImportService(memory_service).apply(
    content=payload.content,
    filename=payload.filename,
    domain=payload.domain,
    kind=payload.kind,
  )
  return ImportApplyResponse(
    detected_format=applied.detected_format,
    created=applied.created,
    skipped=applied.skipped,
    items=[MemoryItemResponse.model_validate(item) for item in applied.items],
  )


def build_shell() -> str:
  return """<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Mnemos</title>
    <link rel="stylesheet" href="/ui/static/app.css">
    <script defer src="/ui/static/app.js"></script>
  </head>
  <body>
    <div class="backdrop"></div>
    <header class="hero">
      <div class="hero__content">
        <p class="eyebrow">Личная память для человека и ИИ</p>
        <h1>Mnemos</h1>
        <p class="hero__lead">
          Сохраняйте заметки, находите их по смыслу, превращайте сырые тексты в факты
          и просматривайте новые выводы перед тем, как они попадут в основную память.
        </p>
        <div class="hero__actions">
          <button class="button button--primary" data-nav-target="add">Добавить первую запись</button>
          <button class="button button--ghost" data-nav-target="search">Попробовать поиск</button>
        </div>
      </div>
      <aside class="status-card" id="status-card">
        <div class="status-card__row">
          <span>Статус</span>
          <strong id="overview-status">Загрузка...</strong>
        </div>
        <div class="status-card__row">
          <span>PostgreSQL</span>
          <strong id="overview-postgres">...</strong>
        </div>
        <div class="status-card__row">
          <span>Qdrant</span>
          <strong id="overview-qdrant">...</strong>
        </div>
        <div class="status-card__row">
          <span>Кандидаты на проверку</span>
          <strong id="overview-candidates">0</strong>
        </div>
      </aside>
    </header>

    <nav class="nav">
      <button class="nav__item is-active" data-nav-target="home">Главная</button>
      <button class="nav__item" data-nav-target="search">Поиск</button>
      <button class="nav__item" data-nav-target="add">Добавить</button>
      <button class="nav__item" data-nav-target="import">Импорт</button>
      <button class="nav__item" data-nav-target="review">Проверка</button>
      <button class="nav__item" data-nav-target="help">Справка</button>
    </nav>

    <main class="layout">
      <section class="panel is-active" data-panel="home">
        <div class="grid grid--two">
          <article class="card">
            <h2>Что можно сделать прямо сейчас</h2>
            <ol class="steps">
              <li>Добавить заметку о себе, проекте или рабочем наблюдении.</li>
              <li>Найти старые записи по смыслу.</li>
              <li>Импортировать текст, Markdown, CSV или экспорт диалога.</li>
              <li>Проверить кандидатов, которые предложила система.</li>
            </ol>
          </article>
          <article class="card">
            <h2>Как устроена память</h2>
            <dl class="glossary">
              <div><dt>Заметка</dt><dd>Исходный текст, который вы сохранили.</dd></div>
              <div><dt>Факт</dt><dd>Короткое подтверждаемое утверждение, извлечённое из текста.</dd></div>
              <div><dt>Вывод</dt><dd>Более общий паттерн, который опирается на несколько фактов.</dd></div>
              <div><dt>Кандидат</dt><dd>Предложение системы, которое ещё не принято в основную память.</dd></div>
            </dl>
          </article>
        </div>
        <article class="card">
          <h2>Недавние записи</h2>
          <div class="toolbar">
            <label>Область
              <select id="recent-domain">
                <option value="self">О себе</option>
                <option value="project">О проекте</option>
                <option value="operational">Об операционной работе</option>
                <option value="interaction">О взаимодействии</option>
              </select>
            </label>
            <button class="button button--ghost" id="refresh-recent">Обновить</button>
          </div>
          <div id="recent-items" class="result-list"></div>
        </article>
      </section>

      <section class="panel" data-panel="search">
        <article class="card">
          <h2>Поиск по памяти</h2>
          <form id="search-form" class="stack">
            <label>Что вы ищете?
              <input type="text" name="query" placeholder="Например: конфиги, мотивация, наблюдаемость" required>
            </label>
            <div class="grid grid--three">
              <label>Область
                <select name="domain">
                  <option value="self">О себе</option>
                  <option value="project">О проекте</option>
                  <option value="operational">Об операционной работе</option>
                  <option value="interaction">О взаимодействии</option>
                </select>
              </label>
              <label>Тип записи
                <select name="kind">
                  <option value="">Все типы</option>
                  <option value="note">Заметки</option>
                  <option value="raw">Исходные записи</option>
                  <option value="fact">Факты</option>
                  <option value="reflection">Выводы</option>
                </select>
              </label>
              <label>Сколько показать
                <input type="number" name="top_k" min="1" max="20" value="5">
              </label>
            </div>
            <button class="button button--primary" type="submit">Искать</button>
          </form>
        </article>
        <div id="search-results" class="result-list"></div>
      </section>

      <section class="panel" data-panel="add">
        <article class="card">
          <h2>Добавить запись</h2>
          <form id="add-form" class="stack">
            <div class="grid grid--three">
              <label>Область памяти
                <select name="domain">
                  <option value="self">О себе</option>
                  <option value="project">О проекте</option>
                  <option value="operational">Об операционной работе</option>
                  <option value="interaction">О взаимодействии</option>
                </select>
              </label>
              <label>Тип записи
                <select name="kind">
                  <option value="note">Заметка</option>
                  <option value="raw">Исходная запись</option>
                  <option value="decision">Решение</option>
                  <option value="task">Задача</option>
                </select>
              </label>
              <label>Уверенность
                <input type="number" name="confidence" min="0" max="1" step="0.01" placeholder="Например: 0.85">
              </label>
            </div>
            <label>Текст записи
              <textarea name="statement" rows="6" placeholder="Например: Я предпочитаю YAML для конфигураций." required></textarea>
            </label>
            <button class="button button--primary" type="submit">Сохранить запись</button>
          </form>
          <div id="add-result" class="notice" hidden></div>
        </article>
      </section>

      <section class="panel" data-panel="import">
        <article class="card">
          <h2>Импорт текста или файла</h2>
          <p class="muted">Поддерживаются обычный текст, Markdown, CSV и базовый импорт диалогов ChatGPT.</p>
          <div id="drop-zone" class="drop-zone">
            <p>Перетащите файл сюда или выберите его вручную.</p>
            <input id="file-input" type="file" aria-label="Выбрать файл">
          </div>
          <form id="import-form" class="stack">
            <div class="grid grid--two">
              <label>Область памяти
                <select name="domain">
                  <option value="self">О себе</option>
                  <option value="project">О проекте</option>
                  <option value="operational">Об операционной работе</option>
                  <option value="interaction">О взаимодействии</option>
                </select>
              </label>
              <label>Как сохранить записи
                <select name="kind">
                  <option value="note">Как заметки</option>
                  <option value="raw">Как исходные записи</option>
                </select>
              </label>
            </div>
            <label>Имя файла
              <input type="text" name="filename" id="import-filename" placeholder="Например: notes.md">
            </label>
            <label>Содержимое
              <textarea name="content" id="import-content" rows="10" placeholder="Вставьте текст сюда или загрузите файл." required></textarea>
            </label>
            <div class="toolbar">
              <button class="button button--ghost" type="button" id="preview-import">Предпросмотр</button>
              <button class="button button--primary" type="submit">Импортировать</button>
            </div>
          </form>
          <div id="import-notice" class="notice" hidden></div>
        </article>
        <article class="card">
          <h2>Предпросмотр импорта</h2>
          <div id="import-preview" class="result-list"></div>
        </article>
      </section>

      <section class="panel" data-panel="review">
        <article class="card">
          <div class="toolbar">
            <h2>Кандидаты на проверку</h2>
            <button class="button button--ghost" id="refresh-review">Обновить</button>
          </div>
          <p class="muted">Здесь можно принять или отклонить новые записи, которые предложила система или агент.</p>
          <div id="review-list" class="result-list"></div>
        </article>
      </section>

      <section class="panel" data-panel="help">
        <div class="grid grid--two">
          <article class="card">
            <h2>Что такое Mnemos</h2>
            <p>Mnemos собирает заметки, позволяет искать их по смыслу и постепенно превращает исходные тексты в более удобные знания.</p>
            <p>Если коротко: вы сохраняете записи, а система помогает их не потерять и сделать полезнее.</p>
          </article>
          <article class="card">
            <h2>Куда идти дальше</h2>
            <ul class="plain-list">
              <li>Начните с вкладки «Добавить», чтобы сохранить первую запись.</li>
              <li>Используйте вкладку «Импорт», если у вас уже есть заметки или экспорт диалога.</li>
              <li>Открывайте вкладку «Проверка», когда система предлагает новые кандидаты.</li>
            </ul>
          </article>
        </div>
      </section>
    </main>
  </body>
</html>"""
