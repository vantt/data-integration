# Phase 03 — "Hàng Đợi Chung" row redesign

**Status:** ✅ done — `wl_row()` extended with `is_unassigned`/`current_user_id` params;
`worklist_fragment.html`'s queue block now calls the macro instead of bare markup; row id
unified to `task-{{ t.task_id }}`. 4 tests in `TestUnassignedQueueRowRedesign`, all passing.

## Context

User explicitly called this out as messy ("bừa bãi"): `worklist_fragment.html:85-103` renders
unassigned-task queue rows with bare custom markup — just title + due date + a "Nhận" button.
No priority pill, no description, no contact info — visually inconsistent with the polished
task row rendered by `wl_row()` (used everywhere else: `_wl_row.html:172-304`), which has
priority badge, task_kind tag, description, contact-pref notes, last-contact strip, due date.

`_wl_row.html`'s task branch already renders a full-featured row but its `wl-row__aside`
(lines 255-302) assumes a task already has an assignee — CTAs are contact button,
reschedule/cancel (band 0 only), unclaim ("Trả việc" for claim-tasks), snooze. None of these
fit an unassigned row; the correct CTA here is "Nhận" (self-assign), matching
`worklist_fragment.html:93-101`'s existing `hx-patch="/tasks/{{ t.task_id }}/assign-me"`.

## Requirement

Extend `wl_row()` macro (`_wl_row.html:9`) with an optional parameter, e.g.
`is_unassigned=false`. When `row.kind == 'task'` and `is_unassigned` is true:
- Render the same `wl-row__main` block as today (priority pill, task_kind tag, title,
  description, contact-pref notes, due date) — reuse as-is, no duplication.
- Replace the entire `wl-row__aside` content with a single "Nhận" button:
  `hx-patch="/tasks/{{ t.task_id }}/assign-me" hx-target="#task-{{ t.task_id }}" hx-swap="delete"`
  (matches the existing endpoint contract in `screen_worklist.py:402-413` — 200 empty body on
  success, row deletes client-side).
- Skip last-contact strip and contact_btn (no assignee yet, and per current behavior these
  rows carry no `party_extras` contact context — verify against what
  `_load_worklist_data()` actually populates for `unassigned_tasks`; if `party_extras` is empty
  for these party_ids today, decide whether phase 02 should also enrich them, or leave the
  strip conditionally absent as it already is for missing data — do not add new enrichment
  calls unless genuinely needed).

Do not touch the row's `id="queue-task-{{ t.task_id }}"` vs `id="task-{{ t.task_id }}"`
mismatch silently — pick one convention (prefer `task-{{ t.task_id }}` to match the rest of
`_wl_row.html` so any shared CSS/JS selectors keep working) and update
`worklist_fragment.html`'s call site accordingly.

## Files to modify

- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` — add `is_unassigned` param
  and the aside-swap branch.
- `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` — replace the
  bare markup (lines 85-103) with `{{ wl_row(row_wrapped, party_extras, is_unassigned=true) }}`
  — note `unassigned_tasks` is a plain `list[Task]`, not `list[WorklistRow]`; either wrap each
  task in a minimal `WorklistRow`-like object before calling the macro, or adjust the macro to
  accept a bare `Task` when `is_unassigned=true` (check what `row.payload`/`row.band` accesses
  the macro needs and short-circuit those for this call path — prefer wrapping in a
  `WorklistRow(kind='task', band=-1, urgency=0, value=0, neglect_days=0, ref_id=task_id,
  payload=task)` for minimal macro changes over branching internals further).

## Tests

- `test_web_templating.py`: render the "Hàng Đợi Chung" block with a task fixture; assert the
  priority pill and title show, assert a "Nhận" button with the correct `hx-patch` URL is
  present, assert none of the assigned-only controls (Trả việc, Dời hạn, Hủy, snooze) render.

## Risks / rollback

- Low-medium: macro signature change is additive (`is_unassigned` defaults false, existing
  call sites in `_wl_bands.html` unaffected). Rollback = revert the two template files; no
  backend/data changes here.
