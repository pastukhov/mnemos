const state = {
  importPayload: null,
};

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindSearchForm();
  bindAddForm();
  bindImportForm();
  bindReviewActions();
  bindRecentActions();
  loadOverview();
  loadRecentItems();
  loadReviewQueue();
});

function bindNavigation() {
  const navButtons = document.querySelectorAll("[data-nav-target]");
  navButtons.forEach((button) => {
    button.addEventListener("click", () => activatePanel(button.dataset.navTarget));
  });
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
  document.getElementById("overview-status").textContent = data.status === "ready" ? "Готово" : "Нужно внимание";
  document.getElementById("overview-postgres").textContent = translateCheck(data.checks.postgres);
  document.getElementById("overview-qdrant").textContent = translateCheck(data.checks.qdrant);
  document.getElementById("overview-candidates").textContent = String(data.pending_candidates);
}

function translateCheck(value) {
  return value === "ok" ? "Готов" : "Ошибка";
}

function bindRecentActions() {
  document.getElementById("refresh-recent").addEventListener("click", loadRecentItems);
  document.getElementById("recent-domain").addEventListener("change", loadRecentItems);
}

async function loadRecentItems() {
  const domain = document.getElementById("recent-domain").value;
  const response = await fetch(`/ui/api/items?domain=${encodeURIComponent(domain)}&limit=12`);
  const data = await response.json();
  renderItems(document.getElementById("recent-items"), data.items, "Пока здесь нет записей.");
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
    renderItems(document.getElementById("search-results"), data.items, "Ничего не найдено. Попробуйте другой запрос.");
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
      ? `Запись сохранена. ID: ${data.id}`
      : `Не удалось сохранить запись: ${data.detail || "неизвестная ошибка"}`;
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
      ? `Импорт завершён. Добавлено: ${data.created}. Пропущено как дубликаты: ${data.skipped}.`
      : `Импорт не выполнен: ${data.detail || "неизвестная ошибка"}`;
    if (response.ok) {
      renderItems(document.getElementById("recent-items"), data.items, "Импорт выполнен, но новых записей не создано.");
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
  renderItems(root, items, "Предпросмотр пуст. Добавьте текст или загрузите файл.");
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
    root.innerHTML = '<div class="empty-state">Сейчас нет кандидатов, ожидающих проверки.</div>';
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
    const title = first.review_session?.label || "Без review session";
    const header = document.createElement("article");
    header.className = "result-card";
    header.innerHTML = `
      <div class="result-card__meta">
        <span class="pill pill--accent">session</span>
        <span class="pill">${escapeHtml(title)}</span>
        <span class="pill">${escapeHtml(sessionId)}</span>
        <span class="pill">pending ${session ? session.pending_count : candidates.length}</span>
      </div>
    `;
    wrapper.append(header);

    candidates.forEach((candidate) => {
      const card = document.createElement("article");
      card.className = "result-card";
      const provenance = [
        candidate.source_note_id ? `source_note ${candidate.source_note_id}` : null,
        candidate.evidence_ref ? `evidence_ref ${candidate.evidence_ref}` : null,
        candidate.write_mode ? `mode ${candidate.write_mode}` : null,
      ].filter(Boolean);
      card.innerHTML = `
        <div class="result-card__meta">
          <span class="pill pill--accent">${candidate.kind}</span>
          <span class="pill">${candidate.domain}</span>
          <span class="pill">confidence ${candidate.confidence ?? "—"}</span>
        </div>
        <p>${escapeHtml(candidate.statement)}</p>
        ${provenance.length ? `<p class="muted">${escapeHtml(provenance.join(" • "))}</p>` : ""}
        ${candidate.source_excerpt ? `<blockquote>${escapeHtml(candidate.source_excerpt)}</blockquote>` : ""}
        <div class="actions-inline">
          <button class="button button--primary" data-action="accept" data-id="${candidate.id}">Принять</button>
          <button class="button button--ghost" data-action="reject" data-id="${candidate.id}">Отклонить</button>
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
    body: JSON.stringify({reason: "Отклонено через веб-интерфейс"}),
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
        <span class="pill pill--accent">${escapeHtml(item.kind || "запись")}</span>
        <span class="pill">${escapeHtml(item.domain || "память")}</span>
        ${item.confidence !== undefined && item.confidence !== null ? `<span class="pill">confidence ${item.confidence}</span>` : ""}
      </div>
      <p>${escapeHtml(item.statement)}</p>
      ${metadata ? `<details><summary>Метаданные</summary><pre>${escapeHtml(metadata)}</pre></details>` : ""}
    `;
    root.append(card);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
