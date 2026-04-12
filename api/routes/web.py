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
def web_app(lang: str | None = Query(default=None, pattern="^(ru|en)$")) -> HTMLResponse:
  return HTMLResponse(build_shell(initial_lang=lang))


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
  wiki_pages_total = sum(1 for page in memory_service.list_wiki_pages() if page.invalidated_at is None)
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
      f"wiki_pages:{wiki_pages_total}",
    ],
  )


@router.get("/ui/api/items", response_model=WebListItemsResponse, include_in_schema=False)
def web_list_items(
  domain: str = Query(default="self"),
  kind: str | None = Query(default=None),
  status: str | None = Query(default="accepted"),
  limit: int = Query(default=24, ge=1, le=100),
  memory_service: MemoryService = Depends(get_checked_memory_service),
) -> WebListItemsResponse:
  if domain not in ALLOWED_DOMAINS:
    raise HTTPException(status_code=422, detail="unsupported domain")
  items = memory_service.list_items_by_domain(domain, status=status)
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


def build_shell(*, initial_lang: str | None = None) -> str:
  lang_attr = initial_lang or ""
  return f"""<!doctype html>
<html lang="ru" data-initial-lang="{lang_attr}">
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
        <p class="eyebrow" data-i18n="hero.eyebrow">Личная память для человека и ИИ</p>
        <h1>Mnemos</h1>
        <p class="hero__lead" data-i18n="hero.lead">
          Сохраняйте заметки, находите их по смыслу, превращайте сырые тексты в факты
          и просматривайте новые выводы перед тем, как они попадут в основную память.
        </p>
        <div class="hero__actions">
          <button class="button button--primary" data-nav-target="add" data-i18n="hero.primary_cta">Добавить первую запись</button>
          <button class="button button--ghost" data-nav-target="search" data-i18n="hero.secondary_cta">Попробовать поиск</button>
        </div>
      </div>
      <aside class="status-card" id="status-card">
        <div class="language-switch" role="group" aria-label="Language switcher">
          <button class="language-switch__button is-active" type="button" data-lang-switch="ru">RU</button>
          <button class="language-switch__button" type="button" data-lang-switch="en">EN</button>
        </div>
        <div class="status-card__row">
          <span data-i18n="status.label">Статус</span>
          <strong id="overview-status" data-i18n="status.loading">Загрузка...</strong>
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
          <span data-i18n="status.pending_candidates">Кандидаты на проверку</span>
          <strong id="overview-candidates">0</strong>
        </div>
        <div class="status-card__row">
          <span data-i18n="overview.wiki_label">Wiki</span>
          <strong id="overview-wiki" data-i18n="overview.wiki_loading">Загрузка...</strong>
        </div>
      </aside>
    </header>

    <nav class="nav">
      <button class="nav__item is-active" data-nav-target="home" data-i18n="nav.home">Главная</button>
      <button class="nav__item" data-nav-target="search" data-i18n="nav.search">Поиск</button>
      <button class="nav__item" data-nav-target="wiki" data-i18n="nav.wiki">Вики</button>
      <button class="nav__item" data-nav-target="add" data-i18n="nav.add">Добавить</button>
      <button class="nav__item" data-nav-target="import" data-i18n="nav.import">Импорт</button>
      <button class="nav__item" data-nav-target="review" data-i18n="nav.review">Проверка</button>
      <button class="nav__item" data-nav-target="help" data-i18n="nav.help">Справка</button>
    </nav>

    <main class="layout">
      <section class="panel is-active" data-panel="home">
        <div class="grid grid--two">
          <article class="card">
            <h2 data-i18n="home.quick_actions.title">Что можно сделать прямо сейчас</h2>
            <ol class="steps">
              <li data-i18n="home.quick_actions.step_1">Добавить заметку о себе, проекте или рабочем наблюдении.</li>
              <li data-i18n="home.quick_actions.step_2">Найти старые записи по смыслу.</li>
              <li data-i18n="home.quick_actions.step_3">Импортировать текст, Markdown, CSV или экспорт диалога.</li>
              <li data-i18n="home.quick_actions.step_4">Проверить кандидатов, которые предложила система.</li>
            </ol>
          </article>
          <article class="card">
            <h2 data-i18n="home.memory_model.title">Как устроена память</h2>
            <dl class="glossary">
              <div><dt data-i18n="home.memory_model.note.term">Заметка</dt><dd data-i18n="home.memory_model.note.desc">Сырой материал интервью: длинный ответ, цитата, рабочая заметка, черновик наблюдения.</dd></div>
              <div><dt data-i18n="home.memory_model.fact.term">Факт</dt><dd data-i18n="home.memory_model.fact.desc">Короткое проверяемое утверждение, которое выросло из заметки и подходит для review.</dd></div>
              <div><dt data-i18n="home.memory_model.reflection.term">Вывод</dt><dd data-i18n="home.memory_model.reflection.desc">Более общий паттерн, который опирается на несколько фактов.</dd></div>
              <div><dt data-i18n="home.memory_model.candidate.term">Кандидат</dt><dd data-i18n="home.memory_model.candidate.desc">Предложение системы с provenance, review session и подсказками о возможных дублях.</dd></div>
            </dl>
          </article>
        </div>
        <article class="card">
          <h2 data-i18n="home.recent.title">Недавние записи</h2>
          <div class="toolbar">
            <label data-i18n="labels.domain">Область
              <select id="recent-domain">
                <option value="self" data-i18n="domains.self">О себе</option>
                <option value="project" data-i18n="domains.project">О проекте</option>
                <option value="operational" data-i18n="domains.operational">Об операционной работе</option>
                <option value="interaction" data-i18n="domains.interaction">О взаимодействии</option>
              </select>
            </label>
            <button class="button button--ghost" id="refresh-recent" data-i18n="actions.refresh">Обновить</button>
          </div>
          <div id="recent-items" class="result-list"></div>
        </article>
      </section>

      <section class="panel" data-panel="search">
        <article class="card">
          <h2 data-i18n="search.title">Поиск по памяти</h2>
          <form id="search-form" class="stack">
            <label data-i18n="search.query_label">Что вы ищете?
              <input type="text" name="query" placeholder="Например: конфиги, мотивация, наблюдаемость" data-i18n-placeholder="search.query_placeholder" required>
            </label>
            <div class="grid grid--three">
              <label data-i18n="labels.domain">Область
                <select name="domain">
                  <option value="self" data-i18n="domains.self">О себе</option>
                  <option value="project" data-i18n="domains.project">О проекте</option>
                  <option value="operational" data-i18n="domains.operational">Об операционной работе</option>
                  <option value="interaction" data-i18n="domains.interaction">О взаимодействии</option>
                </select>
              </label>
              <label data-i18n="labels.kind">Тип записи
                <select name="kind">
                  <option value="" data-i18n="kinds.all">Все типы</option>
                  <option value="note" data-i18n="kinds.note_plural">Заметки</option>
                  <option value="raw" data-i18n="kinds.raw_plural">Исходные записи</option>
                  <option value="fact" data-i18n="kinds.fact_plural">Факты</option>
                  <option value="reflection" data-i18n="kinds.reflection_plural">Выводы</option>
                </select>
              </label>
              <label data-i18n="search.top_k_label">Сколько показать
                <input type="number" name="top_k" min="1" max="20" value="5">
              </label>
            </div>
            <button class="button button--primary" type="submit" data-i18n="actions.search">Искать</button>
          </form>
        </article>
        <div id="search-results" class="result-list"></div>
      </section>

      <section class="panel" data-panel="wiki">
        <div class="grid wiki-layout">
          <article class="card">
            <div class="toolbar">
              <h2 data-i18n="wiki.title">Wiki</h2>
              <button class="button button--ghost" id="refresh-wiki" data-i18n="actions.refresh">Обновить</button>
            </div>
            <div id="wiki-pages" class="result-list"></div>
          </article>
          <article class="card wiki-detail">
            <div class="toolbar">
              <div>
                <h2 id="wiki-page-title" data-i18n="wiki.title">Wiki</h2>
                <p id="wiki-page-meta" class="muted"></p>
              </div>
              <button class="button button--primary" id="wiki-regenerate" data-i18n="wiki.regenerate" hidden>Обновить страницу</button>
            </div>
            <pre id="wiki-page-content" class="wiki-detail__content" data-i18n="wiki.empty">Пока нет wiki-страниц. Они появятся после накопления фактов и генерации.</pre>
          </article>
        </div>
      </section>

      <section class="panel" data-panel="add">
        <article class="card">
          <h2 data-i18n="add.title">Добавить запись</h2>
          <form id="add-form" class="stack">
            <div class="grid grid--three">
              <label data-i18n="add.domain_label">Область памяти
                <select name="domain">
                  <option value="self" data-i18n="domains.self">О себе</option>
                  <option value="project" data-i18n="domains.project">О проекте</option>
                  <option value="operational" data-i18n="domains.operational">Об операционной работе</option>
                  <option value="interaction" data-i18n="domains.interaction">О взаимодействии</option>
                </select>
              </label>
              <label data-i18n="labels.kind">Тип записи
                <select name="kind">
                  <option value="note" data-i18n="kinds.note">Заметка</option>
                  <option value="raw" data-i18n="kinds.raw">Исходная запись</option>
                  <option value="decision" data-i18n="kinds.decision">Решение</option>
                  <option value="task" data-i18n="kinds.task">Задача</option>
                </select>
              </label>
              <label data-i18n="labels.confidence">Уверенность
                <input type="number" name="confidence" min="0" max="1" step="0.01" placeholder="Например: 0.85" data-i18n-placeholder="add.confidence_placeholder">
              </label>
            </div>
            <label data-i18n="add.statement_label">Текст записи
              <textarea name="statement" rows="6" placeholder="Например: Я предпочитаю YAML для конфигураций." data-i18n-placeholder="add.statement_placeholder" required></textarea>
            </label>
            <button class="button button--primary" type="submit" data-i18n="actions.save_record">Сохранить запись</button>
          </form>
          <div id="add-result" class="notice" hidden></div>
        </article>
      </section>

      <section class="panel" data-panel="import">
        <article class="card">
          <h2 data-i18n="import.title">Импорт текста или файла</h2>
          <p class="muted" data-i18n="import.lead">Поддерживаются обычный текст, Markdown, CSV и базовый импорт диалогов ChatGPT.</p>
          <div id="drop-zone" class="drop-zone">
            <p data-i18n="import.drop_zone">Перетащите файл сюда или выберите его вручную.</p>
            <input id="file-input" type="file" aria-label="Выбрать файл" data-i18n-aria-label="import.file_input_aria">
          </div>
          <form id="import-form" class="stack">
            <div class="grid grid--two">
              <label data-i18n="add.domain_label">Область памяти
                <select name="domain">
                  <option value="self" data-i18n="domains.self">О себе</option>
                  <option value="project" data-i18n="domains.project">О проекте</option>
                  <option value="operational" data-i18n="domains.operational">Об операционной работе</option>
                  <option value="interaction" data-i18n="domains.interaction">О взаимодействии</option>
                </select>
              </label>
              <label data-i18n="import.kind_label">Как сохранить записи
                <select name="kind">
                  <option value="note" data-i18n="import.kind_note">Как заметки</option>
                  <option value="raw" data-i18n="import.kind_raw">Как исходные записи</option>
                </select>
              </label>
            </div>
            <label data-i18n="import.filename_label">Имя файла
              <input type="text" name="filename" id="import-filename" placeholder="Например: notes.md" data-i18n-placeholder="import.filename_placeholder">
            </label>
            <label data-i18n="import.content_label">Содержимое
              <textarea name="content" id="import-content" rows="10" placeholder="Вставьте текст сюда или загрузите файл." data-i18n-placeholder="import.content_placeholder" required></textarea>
            </label>
            <div class="toolbar">
              <button class="button button--ghost" type="button" id="preview-import" data-i18n="actions.preview">Предпросмотр</button>
              <button class="button button--primary" type="submit" data-i18n="actions.import">Импортировать</button>
            </div>
          </form>
          <div id="import-notice" class="notice" hidden></div>
        </article>
        <article class="card">
          <h2 data-i18n="import.preview_title">Предпросмотр импорта</h2>
          <div id="import-preview" class="result-list"></div>
        </article>
      </section>

      <section class="panel" data-panel="review">
        <article class="card">
          <div class="toolbar">
            <h2 data-i18n="review.title">Кандидаты на проверку</h2>
            <button class="button button--ghost" id="refresh-review" data-i18n="actions.refresh">Обновить</button>
          </div>
          <p class="muted" data-i18n="review.lead">Здесь кандидаты сгруппированы по review session. На карточке видно источник, режим записи и фрагмент исходного материала.</p>
          <div id="review-list" class="result-list"></div>
        </article>
      </section>

      <section class="panel" data-panel="help">
        <div class="grid grid--three">
          <article class="card">
            <h2 data-i18n="help.what_is.title">Что такое Mnemos</h2>
            <p data-i18n="help.what_is.p1">Mnemos собирает заметки, позволяет искать их по смыслу и постепенно превращает исходные тексты в более удобные знания.</p>
            <p data-i18n="help.what_is.p2">Если коротко: вы сохраняете записи, а система помогает их не потерять и сделать полезнее.</p>
          </article>
          <article class="card">
            <h2 data-i18n="help.flow.title">Как проходит путь памяти</h2>
            <ul class="plain-list">
              <li data-i18n="help.flow.step_1">Сырые записи сохраняются как notes или raw.</li>
              <li data-i18n="help.flow.step_2">Из них извлекаются facts и reflections.</li>
              <li data-i18n="help.flow.step_3">Команда `mnemos wiki build` собирает wiki-страницы.</li>
              <li data-i18n="help.flow.step_4">Проверяйте кандидатов, если хотите принять новые знания вручную.</li>
            </ul>
          </article>
          <article class="card">
            <h2 data-i18n="help.next_steps.title">Куда идти дальше</h2>
            <ul class="plain-list">
              <li data-i18n="help.next_steps.step_1">Начните с вкладки «Добавить», чтобы сохранить первую запись.</li>
              <li data-i18n="help.next_steps.step_2">Используйте вкладку «Импорт», если у вас уже есть заметки или экспорт диалога.</li>
              <li data-i18n="help.next_steps.step_3">Открывайте вкладку «Проверка», когда система предлагает новые кандидаты.</li>
              <li data-i18n="help.next_steps.step_4">Запускайте wiki build, когда хотите превратить факты в читаемую документацию.</li>
            </ul>
          </article>
        </div>
      </section>
    </main>
  </body>
</html>"""
