# Phase 04 — Call Cockpit backend (S14 v2) + task-aware refinements

## Context
Implements the S14 v2 backend from `crm/docs/ui-spec/notes/S14-implementation-notes.md` PLUS the customer-grained/task-aware refinements. Templates via ui-port (Phase 5); here = handlers + context + endpoints. Invariant: HTMX targets sub-regions only; never re-render `#s14-panel-root`.

## Files
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` — enrich `call_cockpit` context; add reason-rail merge.
- NEW route `GET /customers/{party_id}/call` (full-screen shell embedding the cockpit fragment) — new handler / thin module; accepts optional `task_id`.
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py` — add `?inline=1` branch to `post_contact` + `post_core` → return `_s14_collect_row` fragment (NEW stub partial) instead of redirect.
- NEW helper: reason-rail assembly + ripeness sort.

## Steps
1. **Context enrich** (from notes §1): pass `party, identities, insight, warning_notes, resolved_action_ids, geo_region, script, meta`. Snapshot cache-first; fallback `dim_metrics` only if `insight is None`.
2. **Reason rail merge** (new): combine `insight.sorted_actions` + **open/doing contact-tasks** (`task_repository` query: party, task_kind=contact, status in open/doing). Compute ripeness → split **PRIMARY (1)** + **SECONDARY[]**. Include `task_id`/`action_id` provenance per item for outcome resolution.
3. **Outcome bulk-resolve**: extend outcome logging so one outcome resolves the selected action_ids (existing dismiss/claim path) AND flips `task.status` for task-backed rail items (reuse `task_service.transition_status`). Keep single source of truth.
4. **Task-context entry**: `/customers/{id}/call?task_id=` → pin that task's reason as PRIMARY + set return target to `/tasks/{id}`. Chrome "Khách kế →" ↔ "Quay lại task" (template flag).
5. **Inline collect** (notes §4): `inline=1` returns one-row fragment; targets only its row.
6. **Async-resolve** (A-S14-026): rail item marked resolve-by-Zalo → log async contact + resolve item without a call.

## Tests
- call_cockpit context includes rail with primary+secondary; contact-tasks present.
- Outcome with N selected → N resolved + task.status flipped for task items.
- `/customers/{id}/call` renders (stub) with + without `task_id`.
- Inline collect POST returns row fragment (not full panel); panel not re-rendered.

## Rollback
- Additive route + context keys; feature-flag the rail merge if needed. No schema change.
