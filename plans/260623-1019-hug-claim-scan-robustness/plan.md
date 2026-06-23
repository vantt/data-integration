---
title: "Hug claim/scan robustness — token normalization + dynamic claim fields + edge-promotion seam"
description: "Worker /h/:token normalizes typed codes; claim station gains a config-driven multi-field form, per-field live validation, AJAX bind, session idempotency, and a one-time edge-promotion seam that makes adding new edge-matchable bind fields config-only forever after."
status: pending
priority: P1
effort: 12h
branch: main
tags: [hug, claim-station, worker, token-normalization, dynamic-fields, edge-promotion, ux]
created: 2026-06-23
---

# Hug Claim/Scan Robustness (Revised)

## Problem

1. **Worker silent fallback:** `index.ts:18-20` passes raw path segment to `handleHugScan` → D1 query `WHERE t.token = ?` (`hug-handler.ts:229`). No normalization. Staff typing printed codes → 302 to fallback URL silently.
2. **Claim station: hard-coded fields.** Currently binds only `order_code` + `is_gift`. Adding a new field requires touching router, repository, DB schema, and frontend — no config-driven extensibility.
3. **No per-field live validation.** Feedback only after full-page POST re-render.
4. **No session idempotency.** Token already bound to the same order in a different page-load session → ambiguous behavior.
5. **Edge targeting: dynamic fields not promoted.** Any new bind attribute that needs campaign-matching at the edge currently requires a D1 migration + Worker deploy per field.

## Architecture Overview — Dynamic Claim Fields

```
CLAIM_FIELDS config (claim_fields.py)
  [{key, label, type, input, required, validate, prefill, edge}, ...]
         │
         ├─ Backend: generic check-field?key=&value=&session=
         │           dispatches to VALIDATORS[field.validate]
         │
         ├─ Backend: POST /hug/claim/bind {session_id, fields:{...}}
         │           re-validates all required fields server-side
         │           writes promoted cols + bind_attributes JSON
         │
         ├─ Frontend: config-driven render from JSON-serialised CLAIM_FIELDS
         │            per-field live check → AJAX bind → zero-tap happy path
         │
         └─ Edge seam (Phase 4 — one-time):
              edge:true subset → attributes JSON in D1 push payload
              D1 hug_token gets generic `attributes TEXT` column
              ScanContext merges fixed cols + parsed attributes
              matchesTargeting already does ctx[key] lookup → works with zero further Worker change
              targeting_catalog.py gets entry per new edge attr
```

**Config-only guarantee (after Phase 4):** adding a new edge-matchable bind field = one dict in `claim_fields.py` + one `targeting_catalog.py` entry. No D1 migration, no Worker deploy.

## Phase Summary

| # | Name | Effort | Risk | Status | Deployable alone |
|---|------|--------|------|--------|-----------------|
| 1 | Worker `/h/:token` normalization | 2h | Low | pending | Yes — `wrangler deploy` |
| 2 | Dynamic claim-field foundation | 4h | Medium | pending | Yes — crm restart |
| 3 | Claim station frontend | 3h | Medium | pending | Yes — crm restart |
| 4 | Edge-promotion seam | 3h | Low-Medium | pending | Yes — coordinated deploy (D1 migration then wrangler deploy then crm restart) |

**Dependencies:** Phase 2 → Phase 3 (frontend depends on backend endpoints). Phase 4 is independent of 2/3 but logically sequenced after 2 (needs `bind_attributes` column + d1_push attribute subset to exist before push reaches D1).

Phase 1 is fully independent of all others.

## Key Files (verified with file:line)

| File | Role |
|------|------|
| `webhook_receiver/cloudflareD1/src/index.ts:18-20` | Route capture — raw token |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts:217-275` | `handleHugScan` — D1 lookup :229, ScanContext build :232-243 |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts:79-90` | `ScanContext` interface (currently 10 fixed fields) |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts:148-189` | `matchesTargeting` — already uses `ctx[key]` pattern :163 |
| `webhook_receiver/cloudflareD1/src/hug-handler.ts:334-408` | `HugTokenRow` interface + `handleHugTokenUpsert` — upsert SQL :374-386 |
| `webhook_receiver/cloudflareD1/schema_hug.sql:13-25` | D1 `hug_token` schema (no `attributes` column yet) |
| `crm/src/hug/db.py:22-46` | Local `hug_token` schema — idempotent `executescript` pattern |
| `crm/src/hug/repository.py:65-68` | `get_token` |
| `crm/src/hug/repository.py:91-134` | `bind_token` — current signature + idempotency |
| `crm/src/hug/d1_push.py:32-55` | `_row_to_payload` — fields pushed to edge |
| `crm/src/hug/config.py` | Env readers — pattern for new `sapo_api_url`/`sapo_api_key` |
| `crm/src/hug/targeting_catalog.py:27-68` | `TARGETING_CATALOG` — add entry per new edge attr |
| `crm/src/adapters/inbound/web/screen_hug_claim.py:37-100` | `make_hug_claim_router` — existing endpoints |
| `crm/src/adapters/inbound/web/screen_hug_claim.py:211-257` | Client JS block to be replaced |

## Deploy / Rollout

- **Phase 1:** `wrangler deploy` from `webhook_receiver/cloudflareD1/`. No D1 schema change. Instant rollback: redeploy prior commit.
- **Phases 2–3:** crm Python source is volume-mounted (`docker-compose.yml:187`). `CRM_DEV_RELOAD=1` (`docker-compose.yml:174`) → uvicorn hot-reloads on save. **Exception:** new SQLite columns (`bind_session_id`, `bind_attributes`) require `docker compose restart crm` (one-time) to re-run `db.connect()` → `executescript(_SCHEMA)`. Both columns nullable → no data loss on rollback.
- **Phase 4 (coordinated deploy, order matters):**
  1. Apply D1 migration: `wrangler d1 execute fgcare-webhook-db --remote --file=schema_hug.sql` (adds nullable `attributes TEXT` — no data loss, all existing rows get NULL).
  2. `wrangler deploy` (Worker reads the new column from D1, merges into ScanContext).
  3. `docker compose restart crm` (d1_push starts sending `attributes` JSON in upsert payload).
  Rollback: revert steps in reverse order. Worker reads `attributes` only when non-null; if column absent, returns undefined → no ScanContext key injected. Worker deploy can be reverted without the D1 column being dropped.

## Sapo API strategy (Phase 2 investigation confirmed from Phase 3 original plan)

`ingestion/src/sapo/client.py` uses headless Playwright cookie auth — not portable to crm container. Decision (carried forward): thin proxy in claim router using Sapo REST API key (`SAPO_API_URL`, `SAPO_API_KEY`). Sapo validator in `VALIDATORS` registry (`claim_fields.py`). Must be soft-fail: Sapo down → `{ok: null}` → amber → allow proceed.

## Cross-plan Reference

Phase 4 `targeting_catalog.py` entries for new edge-promoted bind fields are coordinated with `plans/260623-0852-hug-campaign-matching-and-preview/` (catalog expansion). Do not duplicate catalog entries — each field gets exactly one entry.

## Unresolved Questions

1. Does `fwg.mysapogo.com` support `Authorization: Bearer <key>` REST API auth, or only cookie sessions? If key auth unavailable, `sapo_order` validator always soft-fails → amber → no hard block (acceptable degradation).
2. Phase 4: should `order_code` (currently a promoted column in D1 `hug_token`) also be replicated in `attributes` JSON for symmetry, or kept as a dedicated column only? Recommendation: dedicated column only (it was always there; no need to duplicate). Confirm before Phase 4 implementation.
3. Stale-bind UX (from original Phase 2 Q): staff scans token A, abandons, then scans token B. Token A remains bound; if staff reloads and re-scans A, new session blocks. Leave as-is (no "release token" affordance) unless raised by ops.
