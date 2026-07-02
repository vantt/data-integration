# Phase 03 — S15 Task Detail backend (route + context + lifecycle)

## Context
No task-detail surface today (S07 card → S03). Add `GET /tasks/{task_id}` + lifecycle endpoints. Templates = stub (ui-port later); deliverable = **context contract**. Reuse `task_service.transition_status`, O03 (postpone), M08 (log/done).

## Files
- NEW `crm/src/adapters/inbound/web/screens/screen_task_detail.py` (router factory) — wire in `composition.py`.
- Reuse: `task_repository` (get_by_id), profile/identities readers, `activities.list_activities` filtered by task_id, insight (claim actions).
- Routing links (template refs only, verified in Phase 5): S07 card, P04 row, S01 row → `/tasks/{id}`.

## Context contract (what the handler passes)
- `task` (Task incl. task_kind, provenance: source/source_ref, due, status, assignee).
- If `task.party_id`: `party` (Party360), `identities`, minimal snapshot (reuse cockpit snapshot helper).
- `provenance_action`: resolve `source_ref`→action rationale/value if `source in (action_queue*)` (via insight/action lookup); else None.
- `attempt_log`: activities WHERE task_id (contact attempts + status changes).
- `claim_actions`: if `source=action_queue_claim` → list of the customer's action items (reuse `insight.sorted_actions`) for the body list.
- `allowed_transitions`: from `TASK_ALLOWED_TRANSITIONS[task.status]`.
- `body_kind`: task.task_kind → selects template body (contact|internal|generic).

## Lifecycle endpoints
- `POST /tasks/{id}/status` (start→doing, cancel→cancelled, reopen) via `task_service.transition_status` (validate against TASK_ALLOWED_TRANSITIONS).
- Postpone → reuse existing O03 endpoint (`due_at` update). Edit → M05. Done → M08 log (mode=log, task_id) then set done (reuse existing outcome path).
- Contact body "Vào phiên gọi" = link `GET /customers/{party_id}/call?task_id={id}` (Phase 4 consumes task_id).

## Tests
- `GET /tasks/{id}` for each kind returns 200 + expected context keys (contact has claim_actions when claim; generic has no party).
- Status transitions respect allowed set (reject illegal).
- 404 on unknown task_id.

## Rollback
- New router; unregister in composition to disable. No schema change here.
