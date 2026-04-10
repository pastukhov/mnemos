const translations = {
  ru: {
    document_title: "Mnemos",
    hero: {
      eyebrow: "Личная память для человека и ИИ",
      lead: "Сохраняйте заметки, находите их по смыслу, превращайте сырые тексты в факты и просматривайте новые выводы перед тем, как они попадут в основную память.",
      primary_cta: "Добавить первую запись",
      secondary_cta: "Попробовать поиск",
    },
    status: {
      label: "Статус",
      loading: "Загрузка...",
      ready: "Готово",
      attention: "Нужно внимание",
      ok: "Готов",
      failed: "Ошибка",
      pending_candidates: "Кандидаты на проверку",
    },
    overview: {
      wiki_label: "Wiki",
      wiki_loading: "Загрузка...",
      wiki_summary: "Страниц wiki: {count}",
    },
    nav: {
      home: "Главная",
      search: "Поиск",
      add: "Добавить",
      import: "Импорт",
      review: "Проверка",
      help: "Справка",
    },
    actions: {
      refresh: "Обновить",
      search: "Искать",
      save_record: "Сохранить запись",
      preview: "Предпросмотр",
      import: "Импортировать",
      accept: "Принять",
      reject: "Отклонить",
    },
    labels: {
      domain: "Область",
      kind: "Тип записи",
      confidence: "Уверенность",
      metadata: "Метаданные",
    },
    domains: {
      self: "О себе",
      project: "О проекте",
      operational: "Об операционной работе",
      interaction: "О взаимодействии",
    },
    kinds: {
      all: "Все типы",
      note: "Заметка",
      note_plural: "Заметки",
      raw: "Исходная запись",
      raw_plural: "Исходные записи",
      fact: "Факт",
      fact_plural: "Факты",
      reflection: "Вывод",
      reflection_plural: "Выводы",
      decision: "Решение",
      task: "Задача",
      preview: "Предпросмотр",
      record: "Запись",
    },
    home: {
      quick_actions: {
        title: "Что можно сделать прямо сейчас",
        step_1: "Добавить заметку о себе, проекте или рабочем наблюдении.",
        step_2: "Найти старые записи по смыслу.",
        step_3: "Импортировать текст, Markdown, CSV или экспорт диалога.",
        step_4: "Проверить кандидатов, которые предложила система.",
      },
      memory_model: {
        title: "Как устроена память",
        note: {
          term: "Заметка",
          desc: "Сырой материал интервью: длинный ответ, цитата, рабочая заметка, черновик наблюдения.",
        },
        fact: {
          term: "Факт",
          desc: "Короткое проверяемое утверждение, которое выросло из заметки и подходит для review.",
        },
        reflection: {
          term: "Вывод",
          desc: "Более общий паттерн, который опирается на несколько фактов.",
        },
        candidate: {
          term: "Кандидат",
          desc: "Предложение системы с provenance, review session и подсказками о возможных дублях.",
        },
      },
      recent: {
        title: "Недавние записи",
        empty: "Пока здесь нет записей.",
      },
    },
    search: {
      title: "Поиск по памяти",
      query_label: "Что вы ищете?",
      query_placeholder: "Например: конфиги, мотивация, наблюдаемость",
      top_k_label: "Сколько показать",
      empty: "Ничего не найдено. Попробуйте другой запрос.",
    },
    add: {
      title: "Добавить запись",
      domain_label: "Область памяти",
      confidence_placeholder: "Например: 0.85",
      statement_label: "Текст записи",
      statement_placeholder: "Например: Я предпочитаю YAML для конфигураций.",
      success: "Запись сохранена. ID: {id}",
      failure: "Не удалось сохранить запись: {detail}",
    },
    import: {
      title: "Импорт текста или файла",
      lead: "Поддерживаются обычный текст, Markdown, CSV и базовый импорт диалогов ChatGPT.",
      drop_zone: "Перетащите файл сюда или выберите его вручную.",
      file_input_aria: "Выбрать файл",
      kind_label: "Как сохранить записи",
      kind_note: "Как заметки",
      kind_raw: "Как исходные записи",
      filename_label: "Имя файла",
      filename_placeholder: "Например: notes.md",
      content_label: "Содержимое",
      content_placeholder: "Вставьте текст сюда или загрузите файл.",
      preview_title: "Предпросмотр импорта",
      preview_empty: "Предпросмотр пуст. Добавьте текст или загрузите файл.",
      success: "Импорт завершён. Добавлено: {created}. Пропущено как дубликаты: {skipped}.",
      failure: "Импорт не выполнен: {detail}",
      no_new_items: "Импорт выполнен, но новых записей не создано.",
    },
    review: {
      title: "Кандидаты на проверку",
      lead: "Здесь кандидаты сгруппированы по review session. На карточке видно источник, режим записи и фрагмент исходного материала.",
      empty: "Сейчас нет кандидатов, ожидающих проверки.",
      no_session: "Без review session",
      session: "сессия",
      pending_short: "на проверке",
      source_note: "источник",
      evidence_ref: "ссылка",
      mode: "режим",
      reject_reason: "Отклонено через веб-интерфейс",
    },
    help: {
      what_is: {
        title: "Что такое Mnemos",
        p1: "Mnemos собирает заметки, позволяет искать их по смыслу и постепенно превращает исходные тексты в более удобные знания.",
        p2: "Если коротко: вы сохраняете записи, а система помогает их не потерять и сделать полезнее.",
      },
      flow: {
        title: "Как проходит путь памяти",
        step_1: "Сырые записи сохраняются как notes или raw.",
        step_2: "Из них извлекаются facts и reflections.",
        step_3: "Команда `mnemos wiki build` собирает wiki-страницы.",
        step_4: "Проверяйте кандидатов, если хотите принять новые знания вручную.",
      },
      next_steps: {
        title: "Куда идти дальше",
        step_1: "Начните с вкладки «Добавить», чтобы сохранить первую запись.",
        step_2: "Используйте вкладку «Импорт», если у вас уже есть заметки или экспорт диалога.",
        step_3: "Открывайте вкладку «Проверка», когда система предлагает новые кандидаты.",
        step_4: "Запускайте wiki build, когда хотите превратить факты в читаемую документацию.",
      },
    },
    common: {
      unknown_error: "неизвестная ошибка",
      memory: "память",
      confidence: "уверенность",
    },
  },
  en: {
    document_title: "Mnemos",
    hero: {
      eyebrow: "Personal memory for humans and AI",
      lead: "Save notes, find them semantically, turn raw text into facts, and review new conclusions before they enter long-term memory.",
      primary_cta: "Add your first record",
      secondary_cta: "Try search",
    },
    status: {
      label: "Status",
      loading: "Loading...",
      ready: "Ready",
      attention: "Needs attention",
      ok: "Ready",
      failed: "Failed",
      pending_candidates: "Pending candidates",
    },
    overview: {
      wiki_label: "Wiki",
      wiki_loading: "Loading...",
      wiki_summary: "Wiki pages: {count}",
    },
    nav: {
      home: "Home",
      search: "Search",
      add: "Add",
      import: "Import",
      review: "Review",
      help: "Help",
    },
    actions: {
      refresh: "Refresh",
      search: "Search",
      save_record: "Save record",
      preview: "Preview",
      import: "Import",
      accept: "Accept",
      reject: "Reject",
    },
    labels: {
      domain: "Domain",
      kind: "Record type",
      confidence: "Confidence",
      metadata: "Metadata",
    },
    domains: {
      self: "Self",
      project: "Project",
      operational: "Operations",
      interaction: "Interaction",
    },
    kinds: {
      all: "All types",
      note: "Note",
      note_plural: "Notes",
      raw: "Raw record",
      raw_plural: "Raw records",
      fact: "Fact",
      fact_plural: "Facts",
      reflection: "Reflection",
      reflection_plural: "Reflections",
      decision: "Decision",
      task: "Task",
      preview: "Preview",
      record: "Record",
    },
    home: {
      quick_actions: {
        title: "What you can do right now",
        step_1: "Add a note about yourself, your project, or a working observation.",
        step_2: "Find older records by meaning.",
        step_3: "Import text, Markdown, CSV, or a chat export.",
        step_4: "Review candidates proposed by the system.",
      },
      memory_model: {
        title: "How memory is structured",
        note: {
          term: "Note",
          desc: "Raw interview material: a long answer, quote, working note, or draft observation.",
        },
        fact: {
          term: "Fact",
          desc: "A short verifiable statement derived from a note and suitable for review.",
        },
        reflection: {
          term: "Reflection",
          desc: "A broader pattern derived from several facts.",
        },
        candidate: {
          term: "Candidate",
          desc: "A proposed item with provenance, review session info, and duplicate hints.",
        },
      },
      recent: {
        title: "Recent records",
        empty: "There are no records here yet.",
      },
    },
    search: {
      title: "Memory search",
      query_label: "What are you looking for?",
      query_placeholder: "For example: configs, motivation, observability",
      top_k_label: "How many to show",
      empty: "Nothing found. Try a different query.",
    },
    add: {
      title: "Add a record",
      domain_label: "Memory domain",
      confidence_placeholder: "For example: 0.85",
      statement_label: "Record text",
      statement_placeholder: "For example: I prefer YAML for configuration files.",
      success: "Record saved. ID: {id}",
      failure: "Could not save record: {detail}",
    },
    import: {
      title: "Import text or file",
      lead: "Plain text, Markdown, CSV, and basic ChatGPT transcript import are supported.",
      drop_zone: "Drop a file here or choose it manually.",
      file_input_aria: "Choose file",
      kind_label: "How to save records",
      kind_note: "As notes",
      kind_raw: "As raw records",
      filename_label: "File name",
      filename_placeholder: "For example: notes.md",
      content_label: "Content",
      content_placeholder: "Paste text here or upload a file.",
      preview_title: "Import preview",
      preview_empty: "Preview is empty. Add text or upload a file.",
      success: "Import completed. Added: {created}. Skipped as duplicates: {skipped}.",
      failure: "Import failed: {detail}",
      no_new_items: "Import completed, but no new records were created.",
    },
    review: {
      title: "Candidates for review",
      lead: "Candidates are grouped by review session. Each card shows its source, write mode, and source excerpt.",
      empty: "There are no candidates waiting for review right now.",
      no_session: "No review session",
      session: "session",
      pending_short: "pending",
      source_note: "source note",
      evidence_ref: "evidence ref",
      mode: "mode",
      reject_reason: "Rejected via the web interface",
    },
    help: {
      what_is: {
        title: "What Mnemos is",
        p1: "Mnemos collects notes, lets you search them semantically, and gradually turns source text into more useful knowledge.",
        p2: "In short: you save records, and the system helps you keep them and make them more useful.",
      },
      flow: {
        title: "How the memory flow works",
        step_1: "Raw records are stored as notes or raw items.",
        step_2: "Facts and reflections are extracted from them.",
        step_3: "The `mnemos wiki build` command assembles wiki pages.",
        step_4: "Candidates stay reviewable if you want to accept knowledge manually.",
      },
      next_steps: {
        title: "Where to go next",
        step_1: "Start with the Add tab to save your first record.",
        step_2: "Use the Import tab if you already have notes or a chat export.",
        step_3: "Open the Review tab when the system proposes new candidates.",
        step_4: "Run wiki build when you want facts turned into readable documentation.",
      },
    },
    common: {
      unknown_error: "unknown error",
      memory: "memory",
      confidence: "confidence",
    },
  },
};

const state = {
  currentLang: "ru",
  importPayload: null,
};

document.addEventListener("DOMContentLoaded", () => {
  state.currentLang = resolveInitialLanguage();
  bindNavigation();
  bindLanguageSwitcher();
  bindSearchForm();
  bindAddForm();
  bindImportForm();
  bindReviewActions();
  bindRecentActions();
  applyTranslations();
  setLanguage(state.currentLang, {persist: false});
});

function resolveInitialLanguage() {
  const urlLang = new URLSearchParams(window.location.search).get("lang");
  if (urlLang && translations[urlLang]) return urlLang;
  const htmlLang = document.documentElement.dataset.initialLang;
  if (htmlLang && translations[htmlLang]) return htmlLang;
  const stored = window.localStorage.getItem("mnemos-ui-lang");
  if (stored && translations[stored]) return stored;
  const browser = navigator.language?.toLowerCase().startsWith("ru") ? "ru" : "en";
  return browser;
}

function bindNavigation() {
  const navButtons = document.querySelectorAll("[data-nav-target]");
  navButtons.forEach((button) => {
    button.addEventListener("click", () => activatePanel(button.dataset.navTarget));
  });
}

function bindLanguageSwitcher() {
  document.querySelectorAll("[data-lang-switch]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.langSwitch));
  });
}

function setLanguage(lang, {persist = true} = {}) {
  if (!translations[lang]) return;
  state.currentLang = lang;
  document.documentElement.lang = lang;
  document.title = t("document_title");
  if (persist) {
    window.localStorage.setItem("mnemos-ui-lang", lang);
  }
  document.querySelectorAll("[data-lang-switch]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.langSwitch === lang);
  });
  applyTranslations();
  loadOverview();
  loadRecentItems();
  loadReviewQueue();
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    setTranslatedText(node, t(node.dataset.i18n));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
}

function setTranslatedText(node, text) {
  if (!node.children.length) {
    node.textContent = text;
    return;
  }

  const prefix = `${text} `;
  if (node.firstChild?.nodeType === Node.TEXT_NODE) {
    node.firstChild.textContent = prefix;
    return;
  }

  node.insertBefore(document.createTextNode(prefix), node.firstChild);
}

function activatePanel(name) {
  document.querySelectorAll(".nav__item").forEach((item) => {
    item.classList.toggle("is-active", item.dataset.navTarget === name);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.panel === name);
  });
}

async function loadOverview() {
  const response = await fetch("/ui/api/overview");
  const data = await response.json();
  document.getElementById("overview-status").textContent = data.status === "ready" ? t("status.ready") : t("status.attention");
  document.getElementById("overview-postgres").textContent = translateCheck(data.checks.postgres);
  document.getElementById("overview-qdrant").textContent = translateCheck(data.checks.qdrant);
  document.getElementById("overview-candidates").textContent = String(data.pending_candidates);
  const wikiPagesFeature = (data.features || []).find((feature) => feature.startsWith("wiki_pages:"));
  const wikiPagesCount = Number(wikiPagesFeature?.split(":")[1] || 0);
  document.getElementById("overview-wiki").textContent = formatMessage("overview.wiki_summary", {
    count: Number.isFinite(wikiPagesCount) ? wikiPagesCount : 0,
  });
}

function translateCheck(value) {
  return value === "ok" ? t("status.ok") : t("status.failed");
}

function bindRecentActions() {
  document.getElementById("refresh-recent").addEventListener("click", loadRecentItems);
  document.getElementById("recent-domain").addEventListener("change", loadRecentItems);
}

async function loadRecentItems() {
  const domain = document.getElementById("recent-domain").value;
  const response = await fetch(`/ui/api/items?domain=${encodeURIComponent(domain)}&limit=12`);
  const data = await response.json();
  renderItems(document.getElementById("recent-items"), data.items, t("home.recent.empty"));
}

function bindSearchForm() {
  const form = document.getElementById("search-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const kind = formData.get("kind");
    const payload = {
      query: formData.get("query"),
      domain: formData.get("domain"),
      top_k: Number(formData.get("top_k")),
    };
    if (kind) {
      payload.kinds = [kind];
    }
    const response = await fetch("/memory/query", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    renderItems(document.getElementById("search-results"), data.items, t("search.empty"));
  });
}

function bindAddForm() {
  const form = document.getElementById("add-form");
  const notice = document.getElementById("add-result");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const confidence = formData.get("confidence");
    const payload = {
      domain: formData.get("domain"),
      kind: formData.get("kind"),
      statement: formData.get("statement"),
    };
    if (confidence) {
      payload.confidence = Number(confidence);
    }
    const response = await fetch("/memory/items", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    notice.hidden = false;
    notice.textContent = response.ok
      ? formatMessage("add.success", {id: data.id})
      : formatMessage("add.failure", {detail: extractErrorDetail(data)});
    if (response.ok) {
      form.reset();
      loadRecentItems();
    }
  });
}

function bindImportForm() {
  const fileInput = document.getElementById("file-input");
  const dropZone = document.getElementById("drop-zone");
  const importForm = document.getElementById("import-form");
  const previewButton = document.getElementById("preview-import");

  fileInput.addEventListener("change", async () => {
    const [file] = fileInput.files;
    if (!file) return;
    document.getElementById("import-filename").value = file.name;
    document.getElementById("import-content").value = await file.text();
  });

  ["dragenter", "dragover"].forEach((type) => {
    dropZone.addEventListener(type, (event) => {
      event.preventDefault();
      dropZone.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((type) => {
    dropZone.addEventListener(type, (event) => {
      event.preventDefault();
      dropZone.classList.remove("is-dragging");
    });
  });
  dropZone.addEventListener("drop", async (event) => {
    const [file] = event.dataTransfer.files;
    if (!file) return;
    document.getElementById("import-filename").value = file.name;
    document.getElementById("import-content").value = await file.text();
  });

  previewButton.addEventListener("click", async () => {
    const payload = getImportPayload();
    state.importPayload = payload;
    const response = await fetch("/ui/api/import/preview", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    renderImportPreview(data);
  });

  importForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = getImportPayload();
    state.importPayload = payload;
    const response = await fetch("/ui/api/import/apply", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    const notice = document.getElementById("import-notice");
    notice.hidden = false;
    notice.textContent = response.ok
      ? formatMessage("import.success", {created: data.created, skipped: data.skipped})
      : formatMessage("import.failure", {detail: extractErrorDetail(data)});
    if (response.ok) {
      renderItems(document.getElementById("recent-items"), data.items, t("import.no_new_items"));
      loadRecentItems();
    }
  });
}

function getImportPayload() {
  return {
    filename: document.getElementById("import-filename").value || null,
    content: document.getElementById("import-content").value,
    domain: new FormData(document.getElementById("import-form")).get("domain"),
    kind: new FormData(document.getElementById("import-form")).get("kind"),
  };
}

function renderImportPreview(data) {
  const root = document.getElementById("import-preview");
  const items = data.items.map((item) => ({
    statement: item.statement,
    kind: "preview",
    domain: data.detected_format,
    metadata: item.metadata,
  }));
  renderItems(root, items, t("import.preview_empty"));
  if (data.warnings.length) {
    const warning = document.createElement("div");
    warning.className = "notice";
    warning.textContent = data.warnings.join(" ");
    root.prepend(warning);
  }
}

function bindReviewActions() {
  document.getElementById("refresh-review").addEventListener("click", loadReviewQueue);
}

async function loadReviewQueue() {
  const [sessionsResponse, response] = await Promise.all([
    fetch("/memory/review-sessions"),
    fetch("/memory/candidates?status=pending"),
  ]);
  const sessionsData = await sessionsResponse.json();
  const data = await response.json();
  const root = document.getElementById("review-list");
  root.innerHTML = "";
  if (!data.items.length) {
    root.innerHTML = `<div class="empty-state">${escapeHtml(t("review.empty"))}</div>`;
    return;
  }
  const sessions = new Map((sessionsData.items || []).map((item) => [item.review_session.id, item]));
  const grouped = new Map();
  data.items.forEach((candidate) => {
    const sessionId = candidate.review_session?.id || "ungrouped";
    if (!grouped.has(sessionId)) {
      grouped.set(sessionId, []);
    }
    grouped.get(sessionId).push(candidate);
  });

  grouped.forEach((candidates, sessionId) => {
    const session = sessions.get(sessionId);
    const wrapper = document.createElement("section");
    wrapper.className = "stack";
    const first = candidates[0];
    const title = first.review_session?.label || t("review.no_session");
    const header = document.createElement("article");
    header.className = "result-card";
    header.innerHTML = `
      <div class="result-card__meta">
        <span class="pill pill--accent">${escapeHtml(t("review.session"))}</span>
        <span class="pill">${escapeHtml(title)}</span>
        <span class="pill">${escapeHtml(sessionId)}</span>
        <span class="pill">${escapeHtml(t("review.pending_short"))} ${escapeHtml(session ? String(session.pending_count) : String(candidates.length))}</span>
      </div>
    `;
    wrapper.append(header);

    candidates.forEach((candidate) => {
      const card = document.createElement("article");
      card.className = "result-card";
      const provenance = [
        candidate.source_note_id ? `${t("review.source_note")} ${candidate.source_note_id}` : null,
        candidate.evidence_ref ? `${t("review.evidence_ref")} ${candidate.evidence_ref}` : null,
        candidate.write_mode ? `${t("review.mode")} ${candidate.write_mode}` : null,
      ].filter(Boolean);
      card.innerHTML = `
        <div class="result-card__meta">
          <span class="pill pill--accent">${escapeHtml(translateKind(candidate.kind))}</span>
          <span class="pill">${escapeHtml(translateDomain(candidate.domain))}</span>
          <span class="pill">${escapeHtml(t("common.confidence"))} ${escapeHtml(candidate.confidence ?? "—")}</span>
        </div>
        <p>${escapeHtml(candidate.statement)}</p>
        ${provenance.length ? `<p class="muted">${escapeHtml(provenance.join(" • "))}</p>` : ""}
        ${candidate.source_excerpt ? `<blockquote>${escapeHtml(candidate.source_excerpt)}</blockquote>` : ""}
        <div class="actions-inline">
          <button class="button button--primary" data-action="accept" data-id="${candidate.id}">${escapeHtml(t("actions.accept"))}</button>
          <button class="button button--ghost" data-action="reject" data-id="${candidate.id}">${escapeHtml(t("actions.reject"))}</button>
        </div>
      `;
      wrapper.append(card);
    });
    root.append(wrapper);
  });

  root.querySelectorAll("[data-action='accept']").forEach((button) => {
    button.addEventListener("click", () => acceptCandidate(button.dataset.id));
  });
  root.querySelectorAll("[data-action='reject']").forEach((button) => {
    button.addEventListener("click", () => rejectCandidate(button.dataset.id));
  });
}

async function acceptCandidate(id) {
  await fetch(`/memory/candidate/${id}/accept`, {method: "POST"});
  loadReviewQueue();
  loadOverview();
  loadRecentItems();
}

async function rejectCandidate(id) {
  await fetch(`/memory/candidate/${id}/reject`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({reason: t("review.reject_reason")}),
  });
  loadReviewQueue();
  loadOverview();
}

function renderItems(root, items, emptyText) {
  root.innerHTML = "";
  if (!items || !items.length) {
    root.innerHTML = `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
    return;
  }
  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "result-card";
    const metadata = item.metadata ? JSON.stringify(item.metadata) : "";
    card.innerHTML = `
      <div class="result-card__meta">
        <span class="pill pill--accent">${escapeHtml(translateKind(item.kind))}</span>
        <span class="pill">${escapeHtml(translateDomain(item.domain))}</span>
        ${item.confidence !== undefined && item.confidence !== null ? `<span class="pill">${escapeHtml(t("common.confidence"))} ${escapeHtml(item.confidence)}</span>` : ""}
      </div>
      <p>${escapeHtml(item.statement)}</p>
      ${metadata ? `<details><summary>${escapeHtml(t("labels.metadata"))}</summary><pre>${escapeHtml(metadata)}</pre></details>` : ""}
    `;
    root.append(card);
  });
}

function translateDomain(value) {
  return translations[state.currentLang].domains[value] || value || t("common.memory");
}

function translateKind(value) {
  return translations[state.currentLang].kinds[value] || value || t("kinds.record");
}

function extractErrorDetail(data) {
  if (!data) return t("common.unknown_error");
  if (typeof data.detail === "string") return data.detail;
  if (typeof data.detail?.message === "string") return data.detail.message;
  return t("common.unknown_error");
}

function formatMessage(key, values) {
  return Object.entries(values).reduce(
    (message, [name, value]) => message.replaceAll(`{${name}}`, String(value)),
    t(key),
  );
}

function t(key) {
  const source = translations[state.currentLang] || translations.ru;
  return key.split(".").reduce((value, part) => value?.[part], source) || key;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
