# Plan — Task Detail (S15) + Call Cockpit (S14 v2) — Data & Backend

**Status:** ✅ Phases 1–5 DONE (backend + UI port) · committed on branch · follow-up S15 refinements applied (migration 0033) · Phase 6 deferred
**Branch:** `feature/task-detail-cockpit-backend`
**Verified:** Migration 0032 (task_kind) exists + entity/repo/templates complete; migration 0033 (activity_log.channel_type) exists; screen_task_detail.py ✓; screen_call_cockpit.py ✓; task_kind derivation & M05 modal wired; all CSS/templates (ds-s15.css, berich-theme.css, c360_call_cockpit_panel.html, task_detail.html, call_cockpit.html) in place; composition.py routes wired; test files all present (test_task_kind_migration.py, test_task_kind.py, test_task_detail_and_cockpit.py, test_outcome_bulk_resolve.py).
**Sequencing principle (user):** **DATA + BACKEND first**; UI arrives later from *Claude Design* → extracted via **skill `ui-port`** and bound to the backend context built here. Backend handlers expose the full **context dict contract**; templates are stubs until ui-port.

## Source of truth
- Contract: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`, `.../S15-task-detail.md`, modal `M05` (task_kind)
- Code-level HOW: `crm/docs/ui-spec/notes/S14-implementation-notes.md`
- Rationale/model + resolved decisions: `crm/docs/design/contact-execution-and-task-model-design.md`
- States: `crm/docs/ui-spec/30-states-and-errors.md` (S14, S15)

## Locked decisions feeding this plan
- `task_kind` = `contact|internal|generic` (+ optional nullable `channel`). Populated by **data migration/backfill**, **no render-time hardcode**.
- `/tasks/{task_id}` route for S15. Contact-task body = launcher into customer-grained cockpit `/customers/{id}/call` (NOT embedded).
- Cockpit customer-grained: reason rail merges open **contact-tasks** + warehouse actions, **PRIMARY + SECONDARY by ripeness**; outcome **bulk-resolves** many action_ids/task_ids and **syncs `task.status`**.
- M05: task_kind **auto-prefill + hide when confident**.
- Engagement rollup (`crm_identity_engagement`), frequency-cap, worklist group-by-customer = **DEFERRED** (Phase 6, not now).

## Phases
| # | Phase | Status | Deliverable |
|---|---|---|---|
| 1 | Data: `task_kind` column + backfill + entity/repo wiring | ✅ DONE | Migration **0032**, `Task.task_kind`+`channel`, repo (9 SELECT+INSERT/UPDATE/row-map); 0-null gate proven |
| 2 | task_kind derivation + M05 backend | ✅ DONE | `derive_task_kind()`, set on create/claim, M05 POST accepts+derives + `task_kind_confident` |
| 3 | S15 Task Detail backend (route + context + lifecycle) | ✅ DONE | `GET /tasks/{id}` context, `POST /tasks/{id}/status`, wired composition |
| 4 | Call Cockpit backend (S14 v2) + task-aware refinements | ✅ DONE | Panel enrich, `/customers/{id}/call`, inline collect `?inline=1`, `reason_rail`, outcome bulk-resolve + async-resolve |
| 5 | UI integration via `ui-port` | ✅ DONE | S14 (embedded+full-screen) + S15 (3 bodies, full-page wrapper) + M05 kind selector + `.tkind-tag` routing; token-only theming |
| 6 | DEFERRED: engagement rollup · frequency-cap · worklist-by-customer | ⏳ TODO | separate later plan |

### Follow-ups / open
- **Post-Phase-05 refinements** (commit bffcf9ec): migration 0033 added for `crm_activity_log.channel_type` (labels channel values for UI); S15 activity log UI enhancements.
- **Push + PR** not done (awaiting user).
- **[TEST] seed rows** in live `/data/crm.db` (`source_ref='seed-3body-*'`) — delete after QA: `DELETE FROM crm_task WHERE source_ref LIKE 'seed-3body-%'`.
- **Visual QA** by user in progress (3 body URLs above).
- Excluded from commits (separate concern): `.agents/skills/ui-spec/SKILL.md` change, loose `plans/reports/phase-05-*` reports (live in `plans/reports/`).
- Dev note: `crm` uses bind-mounts + `CRM_DEV_RELOAD=0` → `docker compose restart crm` to apply changes (not `--build`).

## Acceptance (whole plan)
- Migrations apply idempotently; existing tasks get correct `task_kind`; no reverse-etl break.
- `/tasks/{id}` renders (stub ok) with a complete context for all 3 kinds + claim list.
- Cockpit reason rail shows contact-tasks + actions split primary/secondary; outcome resolves multiple + flips task.status.
- Routing S07/P04/S01 → S15 works incl. generic (no-party) tasks.
- All touched-area tests green; no schema drift in `stg_crm__task`.

## Cross-cutting risks
- **Repo column drift**: `task_repository` uses explicit column lists in ~10 SELECTs + INSERT + row-map — miss one → mapping error. Grep-audit all.
- **Backfill = SQL-only, complete, no code bridge** (user hard rule): old rows fully classified IN the migration (0 NULLs). `task_kind` is coarser than `action_type` (all action types = outreach = contact), and the only `internal` signal (verify_account) is in `crm.db` — so NO `cache.wh_action_queue` join, NO Python enrichment. Validate on a copy of real `crm.db`.
- **Migration numbering** collision (verify highest in `crm/migrations/`).
- **Reverse-etl**: `transformation/models/staging/stg_crm__task.sql` explicit cols → safe; add `task_kind` there only if warehouse needs it.
- **Phase 5 blocked on external** Claude Design delivery.

## Reports
`plans/260702-1219-task-detail-cockpit-backend/reports/`
