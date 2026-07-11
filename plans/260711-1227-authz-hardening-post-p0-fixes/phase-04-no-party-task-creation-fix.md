---
phase: 4
title: "No-Party Task Creation Fix"
status: completed
priority: P2
dependencies: []
---

# Phase 4: No-Party Task Creation Fix

## Overview

Worklist header "+ Tạo task" button (`worklist.html:26`, `hx-get="/modals/m05?return_to=stay"`, no `party_id`) opens M05 in create mode with no customer attached (by design — M05's "Khách hàng" field is a read-only display, "— (không gắn)" when empty, confirmed no picker UI exists). The form then posts to `hx-post="/customers/{{ party_id }}/tasks"` (`modal_m05_create_task.html:43`) — with empty `party_id` this becomes `POST /customers//tasks`, which does not route-match (confirmed via TestClient in a prior session: real 404, not a hypothetical).

**Chosen fix (Option A from research, not B/C)**: route the no-party case to the existing `POST /tasks` (`screen_tasks_board.py:131-163`, already exists for party-less task creation, used elsewhere e.g. S07 Tasks Board). This is the correct semantic fit (this button's whole purpose is a party-less task), not just the simplest option — Option B (add a customer-picker) would be new UI scope for a header button that has no "current row" context to prefill from; Option C (hybrid) is more machinery than the problem needs.

`/tasks` currently accepts only 5 of the ~10 fields M05's create-mode form sends (missing `priority`, `task_kind`, `source`, `source_ref`, `return_to`) and always hard-redirects to `/tasks` regardless of `return_to` — both gaps need closing so this doesn't regress the "stay in place" fix already shipped for the with-party case.

**Correction after red-team review (2026-07-11)**: the original design repeatedly framed "S07 Tasks Board's own existing `/tasks` caller" as a live regression risk requiring careful additive-only changes and explicit manual verification. 2 independent reviewers traced this and found it doesn't currently exist as a reachable caller — zero templates `hx-post` to `/tasks` today, and S07's own "+ Tạo task" button opens `GET /tasks/modal/create`, whose handler renders `fragments/modal_create_task.html`, **a template file that does not exist on disk** (confirmed via Glob — only `modal_m05_create_task.html` exists). That GET route already fails before ever reaching a form that could POST to `/tasks`. This doesn't change the fix itself (still additive/safe either way), but the plan should stop treating this as a live regression surface — and the missing-template bug is worth a one-line flag (not a fix — separate scope, user's hold-scope decision stands) so it isn't lost.

## Requirements

- M05 create-mode form posts to `/tasks` when `party_id` is empty, `/customers/{party_id}/tasks` when present (unchanged for the with-party case).
- `/tasks` accepts and forwards `priority`, `task_kind`, `source`, `source_ref` (optional, matching `TaskService.create_task()`'s existing `.get()`-with-defaults reads — no service-layer change needed, only the route handler needs to accept and forward them).
- `/tasks` honors `return_to` the same way `/customers/{party_id}/tasks` does (`stay` → `HX-Trigger` no redirect; default → existing redirect behavior).
- Existing callers of `/tasks` that don't send the new optional fields see zero behavior change (purely additive).

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/screen_tasks_board.py` (`handle_create_task`, ~line 131-163 — add optional Form params + `return_to` handling)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html` (~line 43 — conditional `hx-post` target based on `party_id` presence)
- Reference only: `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py:190-192` (the sibling `return_to` handling pattern to mirror exactly, from `post_task`)

## Implementation Steps

1. `screen_tasks_board.py`'s `handle_create_task`: add `priority: str = Form(default="P3")` (or whatever default `TaskService.create_task()` itself falls back to — verify, task_service.py:122 uses `task_data.get("priority", 0)`; align the Form default with that), `task_kind: str = Form(default="")`, `source: str = Form(default="")`, `source_ref: str = Form(default="")`, `return_to: str = Form(default="redirect")`. Forward all of them into the `task_data` dict passed to `task_creator.create_task(task_data)` (only include non-empty ones, matching how `post_task` in `screen_modal_task.py` builds its own dict — check that pattern before writing this one, keep them consistent).
2. Replace the handler's hardcoded final response:
   ```python
   return Response(status_code=200, headers={"HX-Trigger": '{"closeModal":true}', "HX-Redirect": "/tasks"})
   ```
   with `return_to`-aware logic mirroring `screen_modal_task.py:190-192` exactly: `if return_to == "stay": return HTMLResponse("", 200, headers={"HX-Trigger": '{"worklistRefresh": true, "closeModal": true}'})` (combine both signals — `closeModal` for the modal-based worklist flow, `worklistRefresh` for the worklist container to refetch) `else:` keep the existing hardcoded `HX-Redirect: /tasks` (preserves current behavior for any caller not sending `return_to`).
3. `modal_m05_create_task.html`: change the create-mode form's `hx-post="/customers/{{ party_id }}/tasks"` to `hx-post="{% if party_id %}/customers/{{ party_id }}/tasks{% else %}/tasks{% endif %}"`.
4. Confirm via grep (`hx-post="/tasks"` across templates, and `hx-get="/tasks/modal/create"`) that no template currently posts to `/tasks` — expected result: zero matches except the one this phase is about to add. If this grep surprisingly finds a live caller not accounted for above, treat that as new information requiring a scope check, not something to silently work around.
5. Separately, note (do not fix — out of this phase's scope) that `GET /tasks/modal/create`'s target template `fragments/modal_create_task.html` doesn't exist — flag this in the implementation report as a pre-existing bug for the user to decide on later, don't silently leave it undiscovered again.
6. Manual verify: worklist header "+ Tạo task" → fill title, submit → task created, no 404, stays on worklist (per `return_to=stay` already sent by the button).

## Success Criteria

- [x] Worklist header "+ Tạo task" (no customer) → task created successfully, no 404 — verified with a test asserting 200/204, not the previous 404.
- [x] `return_to=stay` on `/tasks` → no `HX-Redirect` header, worklist stays in place.
- [x] `return_to` omitted/default → unchanged `HX-Redirect: /tasks` behavior (regression-safe for existing callers).
- [x] Party-attached M05 create (unchanged path) → still posts to `/customers/{party_id}/tasks`, unaffected.
- [x] `priority`/`task_kind`/`source`/`source_ref` correctly forwarded when M05 sends them (task_kind derivation etc. still works via `TaskService.create_task()`'s existing logic, unchanged).

## Risk Assessment

- **Risk (downgraded after red-team review)**: combining `closeModal` + `worklistRefresh` into one `HX-Trigger` payload for `/tasks`'s `stay` branch was originally flagged as a risk against "S07 Tasks Board's own page" — 2 reviewers traced this and confirmed that caller path doesn't currently exist (see Overview correction). Low residual risk remains only if some other yet-undiscovered template listens for `worklistRefresh` outside the worklist page — step 4's grep covers this.
- **Risk**: `TaskService.create_task()`'s `task_kind` derivation (`derive_task_kind()`) behaves differently when `party_id` is empty (`Rule 1: no customer party → generic, confident=True` per `task_kind.py:49-51`) — confirm this is the INTENDED task_kind for party-less worklist-header creates (likely yes, "generic" matches "no customer" semantics), not a regression from the M05-with-party path's usual "contact" kind.
- **Rollback**: purely additive Form params + one template conditional — revertable file-by-file, zero schema/migration involvement.
