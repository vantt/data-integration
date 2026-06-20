# Phase 4 — Admin UI Screens: List / Create / Edit

## Context Links
- UI pattern to follow: `crm/src/adapters/inbound/web/screen_hug_mint.py` + `screen_hug_mint_html.py` (Pattern A: self-contained HTML, split _html helper)
- Composition wiring: `crm/src/composition.py` lines 355–366 (hug station mounting block)
- Repository (Phase 1): `crm/src/hug/campaign_repository.py`
- Push (Phase 2): `crm/src/hug/campaign_push.py`
- Validator (Phase 3): `crm/src/hug/targeting_catalog.py` — `TARGETING_CATALOG`, `validate_targeting`
- Dark-card CSS: `screen_hug_mint_html.py:_COMMON_CSS` — reuse verbatim

## Overview
- **Priority:** P1
- **Status:** pending (blocked on Phases 1, 2, 3)
- **Goal:** Three screens mounted at `/hug/campaigns` (list), `/hug/campaign/new` (create), `/hug/campaign/{id}/edit` (edit). Pattern A: self-contained HTML rendered server-side in Python, no Jinja2/AppShell dependency, split `_html` helper for testability.

## Key Insights
- Pattern A (screen_hug_mint style) is the explicit recommendation for C2. No HTMX, no AppShell template engine. All HTML is produced by `_html.py` helper functions that return strings.
- The rule-builder must use dropdowns only — no raw JSON editing for list/scalar attrs. `recency_days` gets two number inputs (gte, lte). The form serialises to the targeting JSON shape on submit (server-side assembly, not client JS).
- Destination type drives a conditional input: `zalo_oa` shows a Zalo deep-link field; `cf_pages` shows a CF Pages URL; `url` shows a generic URL field. All three map to `destination_url`.
- On save: validate targeting → upsert_campaign → push_campaign → return success page or error. Push failure is non-fatal (show warning, campaign saved locally).
- Priority field: pre-filled with `suggest_next_priority()` result; show "⚠️ trùng priority" warning inline if the entered value already exists in crm_hug_campaign (JS-free: check on submit).
- `campaign_id`: auto-generated (`slug(name) + "-" + 6-char random`) on create; read-only on edit.

## Requirements

### Functional
- `GET /hug/campaigns` → HTML list of all campaigns (all statuses), sorted priority ASC. Each row: name, priority, status badge, targeting summary, destination, actions (Edit, Pause/Activate, Archive).
- `GET /hug/campaign/new` → blank create form.
- `POST /hug/campaign/new` → validate + upsert + push → redirect to `/hug/campaigns` with success flash, or re-render form with errors.
- `GET /hug/campaign/{id}/edit` → edit form pre-filled from crm_hug_campaign.
- `POST /hug/campaign/{id}/edit` → validate + upsert + push → redirect or re-render errors.
- `POST /hug/campaign/{id}/status` → toggle active↔paused or set archived (form param `action=pause|activate|archive`). Push updated row.
- Duplicate priority warning on submit (not a hard block — display warning but allow save).

### Non-Functional
- `screen_hug_campaign.py` ≤ 200 lines (router only — HTML in `_html.py`).
- `screen_hug_campaign_html.py` ≤ 200 lines; split to `_html_form.py` / `_html_list.py` if needed.
- No external CSS/JS dependencies beyond what's already in `_COMMON_CSS`.
- FastAPI-free `_html.py` helpers — independently testable.

## Architecture

```
crm/src/adapters/inbound/web/
  screen_hug_campaign.py       ← FastAPI router (GET/POST handlers) — NEW
  screen_hug_campaign_html.py  ← Pure HTML helpers: _render_list, _render_form, _render_status_update — NEW

crm/src/composition.py         ← MODIFY: import + mount make_hug_campaign_router(conn)
```

**URL map:**
```
GET  /hug/campaigns                → list
GET  /hug/campaign/new             → blank form
POST /hug/campaign/new             → create
GET  /hug/campaign/{id}/edit       → edit form
POST /hug/campaign/{id}/edit       → update
POST /hug/campaign/{id}/status     → pause / activate / archive
```

**Data flow (create/edit save):**
```
POST form
  → parse form fields into targeting dict (server-side assembly)
  → validate_targeting(targeting)   [Phase 3]
  → campaign_repository.upsert_campaign(conn, row)   [Phase 1]
  → campaign_push.push_campaign(row)   [Phase 2]
  → redirect /hug/campaigns  (or re-render with errors)
```

## Related Code Files

**Create:**
- `crm/src/adapters/inbound/web/screen_hug_campaign.py`
- `crm/src/adapters/inbound/web/screen_hug_campaign_html.py`

**Modify:**
- `crm/src/composition.py` — add import `from adapters.inbound.web.screen_hug_campaign import make_hug_campaign_router` inside the hug station try-block (lines 355–366); add `app.include_router(make_hug_campaign_router(conn))`.

**Read-only references:**
- `crm/src/adapters/inbound/web/screen_hug_mint_html.py` — `_COMMON_CSS`, structural pattern
- `crm/src/hug/op_types.py` — `OP_LABELS` for op_type dropdown
- `crm/src/hug/targeting_catalog.py` (Phase 3) — `TARGETING_CATALOG` for attr dropdowns

## Implementation Steps

1. **`screen_hug_campaign_html.py`** — pure string-returning functions:
   - `_render_list(campaigns: list[dict], flash: str | None) → str` — table of campaigns, status badge colour (`active`=green, `paused`=amber, `archived`=grey), targeting summary (truncate to 60 chars), Edit + status action buttons (POST forms, no JS required).
   - `_render_form(campaign: dict | None, errors: list[str], catalog: dict, suggested_priority: int) → str` — form with: name field, campaign_id (read-only on edit, auto-slug hint on new), rule-builder rows (see below), destination_type select + destination_url, offer_ref, schedule_start/end, quota_total, priority, status select.
   - Rule-builder rendering: for each key in targeting dict, render a rule row: attr dropdown (from catalog keys), operator/value input appropriate to type (list = multi-select checkboxes rendered as pill toggles; range = two number inputs labelled gte/lte). "Add rule" is a second form submit that appends a blank row (server-round-trip, no JS needed — or a static "add another" fieldset that's always visible).
   - `_render_status_update_result(campaign_id, new_status, push_ok) → str` — minimal confirmation snippet (redirects after 1s via `<meta http-equiv=refresh>`).

2. **`screen_hug_campaign.py`** — FastAPI router:
   - `make_hug_campaign_router(conn: sqlite3.Connection) → APIRouter`
   - All routes are `async def` returning `HTMLResponse`.
   - Form parsing: each rule row is submitted as repeated fields `attr_N`, `op_N`, `val_N`. Router assembles the targeting dict: list attrs → value list, range attrs → `{gte: ..., lte: ...}` objects. Strip empty rules.
   - On validation errors: re-render form with error list at top (same pattern as `screen_hug_mint.py:_render_form(error=...)`).
   - Push result appended to flash: "Đã lưu. Đẩy D1: ✓" or "Đã lưu. Đẩy D1: ✗ (kiểm tra log)".

3. **`composition.py` modification** — inside the existing hug try-block:
   ```python
   from adapters.inbound.web.screen_hug_campaign import make_hug_campaign_router
   # ...
   app.include_router(make_hug_campaign_router(conn))
   log.info("hug campaign admin mounted at /hug/campaigns")
   ```
   Note: `conn` here is the crm.db connection (not hug_conn). The campaign data lives in crm.db.

## Todo

- [ ] Write `screen_hug_campaign_html.py` — list + form + status helpers
- [ ] Write `screen_hug_campaign.py` — router with all 6 routes
- [ ] Modify `composition.py` — import + mount (3 lines)
- [ ] Unit tests `crm/tests/hug/test_hug_campaign_html.py` — test `_render_list` and `_render_form` return valid HTML strings with expected content (no HTTP server needed)
- [ ] Manual smoke test: create a campaign, verify it appears in list, edit it, verify push log line

## Success Criteria

- `GET /hug/campaigns` returns 200 HTML with campaign rows.
- `POST /hug/campaign/new` with valid data redirects to `/hug/campaigns`; crm.db row created; push log shows HTTP 200 (or skipped if Worker URL unset).
- `POST /hug/campaign/new` with invalid targeting returns 200 with error message (no row created).
- `POST /hug/campaign/{id}/status` toggles status and pushes.
- `_html.py` functions are callable without FastAPI import in tests.
- `screen_hug_campaign.py` line count ≤ 200.
- `screen_hug_campaign_html.py` line count ≤ 200 (split if needed).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Rule-builder form serialisation is complex without JS | Medium | Medium | Keep it simple: fixed set of rule rows (max 6, one per attr), each always visible with blank default. No dynamic add/remove in v1 (YAGNI). |
| `conn` in composition.py is crm.db conn, not hug_conn — easy to confuse | Medium | High | Clearly comment the distinction in composition.py addition; hug_campaign lives in crm.db (migration 0024) |
| `campaign_id` slug collision on create | Low | Low | Append 6-char random suffix; repository raises IntegrityError only on exact match → catch + show error "ID đã tồn tại, thử tên khác" |
| Line count creep — HTML strings are verbose | High | Low | Split into `_html_list.py` + `_html_form.py` if either exceeds 150 lines |

## Security Considerations
- All form inputs HTML-escaped via `html.escape()` before rendering (mirror `screen_hug_mint.py` pattern).
- `campaign_id` from URL path: validate alphanumeric + hyphen/underscore only before DB query to prevent path traversal (parameterised query already safe, but validate early).
- No authentication layer in v1 (CRM is internal LAN only). Document this — if external access is added later, protect `/hug/campaign/*` routes.

## Next Steps
- Phase 5 adds preview + overlap warning (two new endpoints on the same router or separate module).
- Phase 6 adds history/rollback link on the edit form.
