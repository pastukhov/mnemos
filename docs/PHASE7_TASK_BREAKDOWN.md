# Phase 7 Documentation Task Breakdown

## Purpose

This document decomposes
[`docs/PHASE7_LLM_WIKI_DOCUMENTATION.md`](./PHASE7_LLM_WIKI_DOCUMENTATION.md)
into small implementation tasks that can be executed independently.

Each task is designed to be:

- small enough for one focused PR;
- concrete enough to estimate and verify;
- scoped to one feature area or a small file group.

## Execution Order

1. Complete `P0` tasks for wiki documentation coverage.
1. Complete `P1` reference pages and navigation.
1. Complete `P2` UI documentation surfaces and doc cleanup.
1. Complete `P3` optional but valuable additions.

## Task Template

Each task below includes:

- `Priority`: execution priority
- `Scope`: what is in and out
- `Files`: expected files to touch
- `Definition of done`: how to decide the task is complete

---

## P0 Tasks

### TASK-01: Create the Russian wiki page

- `Priority`: P0
- `Scope`: create the main Russian landing page for the wiki feature
- `Files`: `wiki.md`
- `DoD`: `wiki.md` exists with valid Jekyll frontmatter
- `DoD`: page explains what LLM Wiki is
- `DoD`: page explains the `raw -> facts -> reflections -> wiki` flow
- `DoD`: page includes `mnemos wiki build`
- `DoD`: page mentions `wiki_schema.yaml`
- `DoD`: page includes a compact output example

### TASK-02: Create the English wiki page

- `Priority`: P0
- `Scope`: mirror the Russian wiki page in English
- `Files`: `en/wiki.md`
- `DoD`: `en/wiki.md` exists with valid frontmatter
- `DoD`: content structure matches `wiki.md`
- `DoD`: English terminology is consistent with existing `en/*.md` pages

### TASK-03: Add wiki to the user guide

- `Priority`: P0
- `Scope`: update the guide so wiki appears in the product narrative
- `Files`: `guide.md`, `en/guide.md`
- `DoD`: wiki generation is added to the capabilities section
- `DoD`: lifecycle includes the `wiki build` step
- `DoD`: a practical example flow is added
- `DoD`: English page mirrors the Russian changes

### TASK-04: Add wiki to the About page

- `Priority`: P0
- `Scope`: explain wiki as part of how Mnemos turns memory into useful output
- `Files`: `about.md`, `en/about.md`
- `DoD`: About page mentions wiki generation in the solution narrative
- `DoD`: About page lists wiki pages as a supported output format
- `DoD`: English page mirrors the Russian changes

### TASK-05: Add wiki to FAQ

- `Priority`: P0
- `Scope`: answer the three core wiki questions in FAQ
- `Files`: `faq.md`, `en/faq.md`
- `DoD`: FAQ includes “What is Wiki in Mnemos?”
- `DoD`: FAQ includes where wiki pages are stored
- `DoD`: FAQ includes whether an LLM is required for wiki
- `DoD`: English page mirrors the Russian changes

### TASK-06: Add wiki to README files

- `Priority`: P0
- `Scope`: expose wiki in top-level repository docs
- `Files`: `README.md`, `README_ru.md`
- `DoD`: `wiki build` appears in features
- `DoD`: `mnemos wiki build` appears in setup, quick start, or usage
- `DoD`: wording distinguishes user flow from developer flow where needed

### TASK-07: Add wiki to the landing pages

- `Priority`: P0
- `Scope`: surface wiki on the main site entry pages
- `Files`: `index.md`, `en/index.md`
- `DoD`: main flow mentions wiki as a later-stage output
- `DoD`: value proposition mentions readable documentation from memory
- `DoD`: English page mirrors the Russian changes

---

## P1 Tasks

### TASK-08: Create CLI reference pages

- `Priority`: P1
- `Scope`: create dedicated CLI reference pages instead of relying on README
- `Files`: `cli.md`, `en/cli.md`
- `DoD`: both pages exist with frontmatter
- `DoD`: each page documents `ingest`, `extract`, `reflect`, `candidates`,
  `wiki`, and `mcp-server`
- `DoD`: each command has syntax, flags, and at least one example
- `DoD`: docs match actual CLI behavior in `cli.py`

### TASK-09: Create configuration reference pages

- `Priority`: P1
- `Scope`: document runtime configuration in one dedicated place
- `Files`: `config.md`, `en/config.md`, `.env.example`, `core/config.py`
- `DoD`: both pages exist with frontmatter
- `DoD`: variables are grouped by subsystem
- `DoD`: wiki-specific settings are documented explicitly
- `DoD`: `mock` mode versus real LLM mode is explained
- `DoD`: documented variables match `core/config.py` and `.env.example`

### TASK-10: Update site navigation for new pages

- `Priority`: P1
- `Scope`: make new docs discoverable from the site shell
- `Files`: `_layouts/default.html`
- `DoD`: nav includes `Wiki`, `CLI`, `Config`, and `Backup`
- `DoD`: links work for both Russian and English pages
- `DoD`: language switching still works on the new pages

---

## P2 Tasks

### TASK-11: Add wiki summary to the web overview

- `Priority`: P2
- `Scope`: expose wiki status in the web UI overview panel
- `Files`: `api/routes/web.py`, `api/static/app.js`
- `DoD`: overview shows a dedicated wiki block or summary row
- `DoD`: UI exposes at least status and one useful wiki metric
- `DoD`: copy exists in both Russian and English translations
- `DoD`: no existing overview interactions regress

### TASK-12: Expand Help with onboarding and wiki flow

- `Priority`: P2
- `Scope`: improve the built-in Help tab for first-time users
- `Files`: `api/routes/web.py`, `api/static/app.js`
- `DoD`: Help explains what to do after first launch
- `DoD`: Help explains the memory flow including wiki
- `DoD`: copy is available in both Russian and English
- `DoD`: Help content remains readable in the current layout

### TASK-13: Fix install guide inconsistencies

- `Priority`: P2
- `Scope`: align installation messaging across docs
- `Files`: `install.md`, `README.md`, `README_ru.md`
- `DoD`: platform requirements are internally consistent
- `DoD`: developer setup and end-user setup are clearly separated
- `DoD`: no contradictory first-step instructions remain

### TASK-14: Remove About/FAQ duplication

- `Priority`: P2
- `Scope`: keep FAQ content in one place and reduce duplication
- `Files`: `about.md`, `en/about.md`, `faq.md`, `en/faq.md`
- `DoD`: repeated FAQ-style sections are removed from About
- `DoD`: About links to FAQ instead of duplicating it
- `DoD`: English pages stay aligned with Russian pages

### TASK-15: Run an RU/EN synchronization pass

- `Priority`: P2
- `Scope`: perform a final consistency pass across all changed docs
- `Files`:
- `Files`: `wiki.md`, `en/wiki.md`
- `Files`: `guide.md`, `en/guide.md`
- `Files`: `about.md`, `en/about.md`
- `Files`: `faq.md`, `en/faq.md`
- `Files`: `index.md`, `en/index.md`
- `Files`: `cli.md`, `en/cli.md`
- `Files`: `config.md`, `en/config.md`
- `DoD`: every Russian change has an English equivalent where expected
- `DoD`: section ordering is aligned
- `DoD`: terminology is internally consistent

---

## P3 Tasks

### TASK-16: Move backup/restore docs into the site

- `Priority`: P3
- `Scope`: adapt existing backup docs to the Jekyll site format
- `Files`: `backup.md`, `en/backup.md`, `docs/backup-restore-ru.md`
- `DoD`: site-facing backup pages exist in Russian and English
- `DoD`: pages have proper frontmatter and navigation placement
- `DoD`: content is adapted to site style instead of pasted raw

### TASK-17: Add an architecture diagram to About

- `Priority`: P3
- `Scope`: replace part of the explanatory text with one visual model
- `Files`: `about.md`, `en/about.md`
- `DoD`: About contains a diagram for
  `raw -> facts -> reflections -> wiki`
- `DoD`: diagram also shows PostgreSQL, Qdrant, LLM, and MCP
- `DoD`: diagram renders correctly in the site, or a readable ASCII fallback
  is used

---

## Suggested PR Slices

If this work is implemented through PRs, a practical split is:

1. PR-01: `TASK-01` and `TASK-02`
1. PR-02: `TASK-03`, `TASK-04`, `TASK-05`
1. PR-03: `TASK-06` and `TASK-07`
1. PR-04: `TASK-08`
1. PR-05: `TASK-09`
1. PR-06: `TASK-10`
1. PR-07: `TASK-11` and `TASK-12`
1. PR-08: `TASK-13`, `TASK-14`, `TASK-15`
1. PR-09: `TASK-16` and `TASK-17`

## Verification Checklist

After all tasks are complete, verify:

- `mdl` passes for all changed Markdown files
- new site pages build and render correctly
- RU and EN navigation both work
- web UI still loads and overview/help render correctly
- documentation matches current CLI and configuration behavior
