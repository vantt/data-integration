# CRM i18n — JSON Locale (VI/EN)

**Branch:** main  
**Date:** 2026-06-18  
**Goal:** Add Vietnamese/English bilingual support via JSON locale files, cookie-based language switch.

## Scope summary

| Source | Items |
|--------|-------|
| HTML templates (39 files) | ~250 string literals |
| `badge_catalog.py` | 72 BadgeDef hint strings |
| `format_helpers.py` | ~12 strings (time units, verdict labels) |
| `screen_*.py` (6 files) | ~20 error/flash messages |

## Architecture decision

- Language stored in `lang` cookie (`vi` default, `en` alternative)
- `ContextVar`-based `t()` function — set in middleware, available everywhere without per-handler changes
- `templates.env.globals["t"] = t` — single injection point in `composition.py`
- JSON locale: flat dot-notation keys, domain-namespaced (not surface-namespaced)
- `badge_catalog.py` `hint` field → becomes i18n key, templates call `t(bdg_tip(...))`

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Infrastructure](phase-01-infrastructure.md) | Todo |
| 2 | [Locale files](phase-02-locale-files.md) | Todo |
| 3 | [badge_catalog migration](phase-03-badge-catalog.md) | Todo |
| 4 | [format_helpers migration](phase-04-format-helpers.md) | Todo |
| 5 | [Template migration](phase-05-templates.md) | Todo |
| 6 | [Python screen files migration](phase-06-python-screens.md) | Todo |

> **Status:** Not started (updated 2026-06-24: untouched by 260623 audit work; owner-sequenced backlog item)

## Key files to create/modify

**Create:**
- `crm/src/adapters/inbound/web/i18n.py`
- `crm/src/adapters/inbound/web/locales/vi.json`
- `crm/src/adapters/inbound/web/locales/en.json`

**Modify:**
- `crm/src/composition.py` — wire middleware + inject `t` global
- `crm/src/adapters/inbound/web/badge_catalog.py` — hint → key
- `crm/src/adapters/inbound/web/format_helpers.py` — locale-aware functions
- 39 HTML template files
- 6 screen Python files
