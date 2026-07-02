# Plan — Task Detail (S15) + Call Cockpit (S14 v2) — Data & Backend

**Status:** DRAFT · not started
**Branch:** feature branch off `main` (create before coding)
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
| # | Phase | Depends | Deliverable |
|---|---|---|---|
| 1 | Data: `task_kind` column + backfill + entity/repo wiring | — | Migration 00NN, `Task.task_kind`, repo reads/writes, export verified |
| 2 | task_kind derivation + M05 backend | 1 | `derive_task_kind()`, set on create/claim, M05 POST accepts+derives |
| 3 | S15 Task Detail backend (route + context + lifecycle) | 1,2 | `GET /tasks/{id}` context contract, lifecycle endpoints, routing links |
| 4 | Call Cockpit backend (S14 v2) + task-aware refinements | 1,2 | Panel enrich, `/customers/{id}/call`, inline collect, reason-rail merge, outcome bulk-resolve |
| 5 | UI integration via `ui-port` (after Claude Design delivers) | 3,4 | S14 v2 + S15 + M05 templates extracted, bound, verified vs spec |
| 6 | DEFERRED: engagement rollup · frequency-cap · worklist-by-customer | 4 | separate later plan |

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
