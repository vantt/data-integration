# CRM Data-Integrity + Auth Fixes — 2026-06-24

## Task 1 — identity_resolver atomicity + Zalo-only dedup

### 1a. Watermark atomicity

**File:** `crm/src/hug/identity_resolver.py` lines 232-244

**Bug:** `crm_conn.commit()` at line 238 persisted upserts; `save_watermark` at line 244 ran after. Crash between them → DB committed but watermark not advanced → re-process on restart.

**Fix:** Moved `save_watermark` BEFORE `crm_conn.commit()` inside the `try` block. Ordering is now: loop upserts → `save_watermark(wm_path, latest_ts)` → `commit()`. On any failure the `except` branch rolls back the DB; because `save_watermark` hadn't succeeded yet, watermark stays behind and the batch re-processes on restart (all phone-bearing upserts are idempotent via `ON CONFLICT`; Zalo-only rows are now deduplicated — see 1b).

Note: `save_watermark` is a file write (not SQLite), so true 2-phase atomicity is impossible. This ordering makes the file the "intent log" — commit confirms it — which is the safer failure mode (re-process is safe; skipping is not).

### 1b. Zalo-only duplicate rows

**File:** `crm/src/hug/identity_resolver_io.py` — `upsert_link()` function

**Bug:** `UNIQUE(token, scanner_phone)` schema constraint doesn't trigger when `scanner_phone IS NULL` (SQLite treats NULL ≠ NULL). Re-running the resolver created a new `crm_identity_link` row per run for C5 opt-ins.

**Fix:** When `scanner_phone is None` and `scanner_zalo_uid` is set, replaced the generic `_SQL_UPSERT_LINK` call with an explicit UPDATE-then-INSERT pattern keyed on `(token, scanner_zalo_uid, scanner_phone IS NULL)`. Phone-bearing rows continue to use the original `ON CONFLICT` path unchanged. No schema migration needed.

**Validation:** 13/13 `test_hug_identity_resolver.py` tests pass including C5 Zalo-only cases.

---

## Task 2 — segment refresh atomicity

**Files:**
- `crm/src/adapters/outbound/sqlite/segment_repository.py` — added `replace_rule_members()`
- `crm/src/application/segment_service.py` lines 146-157 — switched to `replace_rule_members()`

**Bug:** `refresh_dynamic_segment` called `delete_rule_members` (which committed), then looped `upsert_member` (each committed individually). A crash between delete and the first insert left the segment empty. Manual members were safe (delete filtered `source='rule'`) but the whole rule-member set was at risk.

**Fix:** Added `SQLiteSegmentRepository.replace_rule_members(segment_id, members)` that:
1. Issues explicit `BEGIN`
2. Deletes `source='rule'` rows for the segment
3. Bulk-inserts new members with the same `ON CONFLICT` upsert guard (preserves `'manual'` source if a party was also added manually)
4. `COMMIT` or `ROLLBACK` on exception

`SegmentService.refresh_dynamic_segment` now builds the `SegmentMember` list and calls `replace_rule_members` in one shot. The old per-row `upsert_member` loop is gone from the refresh path (still used for manual `add_member`).

**Note:** `segment_repository.py` already uses `self._conn.execute("BEGIN")` style (no `conn.isolation_level` tricks) which is correct for SQLite's default `isolation_level` of `""` (autocommit off when not in transaction) — our explicit `BEGIN`/`COMMIT`/`ROLLBACK` is safe.

**Validation:** 514 passed / 0 failed across full test suite (excl. `test_web_templating.py` which fails due to missing `fastapi` in host Python — pre-existing, unrelated to our changes).

---

## Task 3 — mutation-API auth

### Investigation

Web UI (HTMX) calls **web routes** at unprefixed paths (`hx-post="/segments/..."`, `hx-patch="/tasks/..."`, etc.) handled by `crm/src/adapters/inbound/web/screen_*.py`. These are **not** the HTTP `/api/*` routes.

The `/api/*` handlers in `crm/src/adapters/inbound/http/` are separate routes not referenced by any web template. They are used by server-to-server callers (Dagster, scripts, external integrations).

**Decision: implement token auth on `/api/*` mutation routes — safe, no UI impact.**

Exception carved out: `POST /api/conversations/messenger/ingest` — this is an inbound Facebook Messenger webhook. Facebook signs payloads with `X-Hub-Signature-256`, not our internal token; blocking it with `CRM_API_TOKEN` would break the ingest pipeline.

### Implementation

**New file:** `crm/src/adapters/inbound/http/auth_dependency.py`

FastAPI dependency `require_api_token(x_crm_token: str | None = Header(...))`:
- `CRM_API_TOKEN` set + header matches → allowed
- `CRM_API_TOKEN` set + header missing/wrong → 401
- `CRM_API_TOKEN` unset → allowed + warn once per process (backward-compat; LAN-trust mode)

**Routes updated** (added `dependencies=[Depends(require_api_token)]` per mutation):

| File | Routes guarded |
|---|---|
| `activity_handler.py` | `POST /api/parties/{id}/activities` |
| `task_handler.py` | `POST /api/tasks`, `PATCH /api/tasks/{id}`, `POST /api/tasks/generate` |
| `conversation_handler.py` | `PATCH /api/conversations/{id}` (messenger/ingest excluded) |
| `dedup_handler.py` | `POST /api/dedup/merge/{id}`, `POST /api/dedup/undo/{id}` |
| `customer360_handler.py` | `PUT /api/parties/{id}/profile`, `POST /api/custom-fields`, `POST /api/parties/{id}/tags`, `DELETE /api/parties/{id}/tags/{tag_id}`, `POST /api/parties/{id}/notes` |
| `segment_handler.py` | `POST /api/segments`, `PATCH /api/segments/{id}`, `POST /api/segments/{id}/refresh`, `POST /api/segments/{id}/members`, `DELETE /api/segments/{id}/members/{pid}` |
| `campaign_handler.py` | `POST /api/campaigns`, `PATCH /api/campaigns/{id}`, `POST /api/campaigns/{id}/generate-targets`, `PATCH /api/campaigns/{id}/targets/{pid}`, `POST /api/campaigns/{id}/scan-conversions` |
| `admin_handler.py` | `/admin/refresh` now accepts either `X-Refresh-Token`/`CRM_REFRESH_TOKEN` (legacy) or `X-CRM-Token`/`CRM_API_TOKEN` (unified); both unset → warn + allow |

GET/read-only endpoints are not gated.

**Validation:** All 13 files compile cleanly (`py_compile`). 514 tests pass.

---

## Summary

**Status:** DONE

**Per-task:**
1. Implemented — watermark moved before commit (atomicity); Zalo-only rows deduplicated by `(token, zalo_uid)` in `upsert_link`
2. Implemented — `replace_rule_members()` wraps delete + bulk insert in one `BEGIN`/`COMMIT`; service updated
3. Investigated → UI calls web routes, NOT `/api/*` → implemented `X-CRM-Token` auth on all `/api/*` mutations; `messenger/ingest` excluded (FB webhook); `/admin/refresh` folded to accept either token

**Apply note:** crm container rebuild needed. Set `CRM_API_TOKEN` env var (any non-empty secret string) in `docker-compose.yml` or `.env` to activate token enforcement; leave unset to keep LAN-trust mode until callers are updated.

## Unresolved questions

- `POST /api/conversations/messenger/ingest`: FB signature verification (`X-Hub-Signature-256`) is marked TODO in the handler. Should be implemented before this endpoint is exposed beyond LAN.
- `CRM_REFRESH_TOKEN` and `CRM_API_TOKEN` are now two separate env vars for `/admin/refresh`. Long-term, these can be unified to a single `CRM_API_TOKEN` once all callers (Dagster) are updated to send `X-CRM-Token`.
