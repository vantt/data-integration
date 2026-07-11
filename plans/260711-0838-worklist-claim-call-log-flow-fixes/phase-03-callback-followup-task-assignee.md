---
phase: 3
title: "Callback-Followup Task Assignee"
status: superseded
priority: P0
dependencies: []
---

# Phase 3: Callback-Followup Task Assignee

> **SUPERSEDED (2026-07-11)** — a parallel plan, `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-03-callback-task-assignee.md`, covers this finding with a SIMPLER design: adds `assignee_user_id`/`created_by` only, deliberately keeps `source="manual"` unchanged (explicit YAGNI call, avoids this file's `TASK_SOURCE_CALLBACK`/`TASK_SOURCE_FOLLOWUP` rename entirely). This sidesteps 2 red-team findings against this file's original design (S15 provenance label not actually fixed since `task_detail.html` wasn't touched; new source constants dead-on-arrival since nothing validates `VALID_TASK_SOURCES`) by simply not attempting the source-rename part of the fix. Treat the 0933 file as canonical/executable. This file is kept for its research/evidence trail only.

## Overview

Finding #3 (report §II.3). `execute_side_effects` steps 4 and 5 (`activity_side_effects.py:129-154`) create "Gọi lại"/"Theo dõi" tasks via `task_svc.create_task({...})` without `assignee_user_id` or `created_by`, and with `source: "manual"`. The task falls into the unassigned "Hàng Đợi Chung" queue instead of the calling staff's own list — the UI promises "tạo task nhắc" but nobody is actually reminded; anyone can wrongly claim it, or nobody claims it at all.

Fix: pass `assignee_user_id=actor_id` (+ `created_by=actor_id`) — `actor_id` is already a parameter of `execute_side_effects` (the staff finalizing the activity), no new plumbing needed. Also change `source` from `"manual"` to distinct `"callback"`/`"followup"` values so S15/task provenance can distinguish these from real manually-typed tasks (report's fix note: "source callback/followup thay vì manual để S15 provenance đúng").

## Requirements

- Callback task (step 4, triggered by `contact_outcome == "callback"` + `callback_at` + `create_callback_task` flag) → `assignee_user_id=actor_id`, `created_by=actor_id`, `source="callback"`.
- Follow-up task (step 5, triggered by `schedule_followup_at`) → same shape, `source="followup"`.
- `create_task()` (`task_service.py:96-138`) already accepts both `assignee_user_id` and `created_by` as dict keys (lines 130, 132) — no service-layer change needed, only the caller's dict.
- New `TASK_SOURCE_CALLBACK`/`TASK_SOURCE_FOLLOWUP` constants must be added to `domain/entities/task.py` (currently only `TASK_SOURCE_MANUAL`/`TASK_SOURCE_ACTION_QUEUE`/`TASK_SOURCE_ACTION_QUEUE_CLAIM`/`TASK_SOURCE_CAMPAIGN` exist) and included in `VALID_TASK_SOURCES`.
- `derive_task_kind()` (`application/task_kind.py`) is not source-aware for these new values beyond its existing fallback (`_INTERNAL_SOURCES` doesn't include them, `TASK_SOURCE_ACTION_QUEUE*` branch doesn't match them) → falls through to the final `return TASK_KIND_CONTACT, False` — same result as today's `"manual"` case, confirmed safe, no change needed there.

## Related Code Files

- Modify: `crm/src/domain/entities/task.py` (add `TASK_SOURCE_CALLBACK = "callback"`, `TASK_SOURCE_FOLLOWUP = "followup"`, extend `VALID_TASK_SOURCES`)
- Modify: `crm/src/application/activity_side_effects.py` (steps 4 and 5, lines 129-154)
- Reference only: `crm/src/application/task_service.py:96-138` (`create_task` signature — confirms `assignee_user_id`/`created_by` are already accepted dict keys), `crm/src/application/task_kind.py` (confirms no source-specific branch needed for the new values)

## Implementation Steps

1. `domain/entities/task.py`: add the two new `TASK_SOURCE_*` constants next to the existing ones; append both to `VALID_TASK_SOURCES`.
2. `activity_side_effects.py` step 4 (callback task): add `"assignee_user_id": actor_id, "created_by": actor_id` to the dict, change `"source": "manual"` → `"source": "callback"`.
3. `activity_side_effects.py` step 5 (follow-up task): same three changes, `"source": "followup"`.
4. Check whether `VALID_TASK_SOURCES` is enforced anywhere on write (validation raising on unknown source) — if `TaskService.create_task` or the repository validates against this list, the two new constants must land before the side-effect change or task creation will start failing; if it's advisory-only (used elsewhere, e.g. filters/badges), order doesn't matter but do both in the same commit regardless.
5. Check `badge_catalog.py`/worklist templates for any `source`-keyed label/icon lookup (similar to `_ACTION_TYPE_SHORT_LABEL` in `task_service.py`) that might need a VN label for `"callback"`/`"followup"` sources so the task doesn't render as a raw/unknown source string in S07/S15 — out of scope for the report's finding but a likely regression if such a lookup exists and defaults to showing the raw enum value.

## Success Criteria

- [ ] Finalize a call with outcome `callback` + `callback_at` + "tạo task nhắc" checked → resulting task has `assignee_user_id == actor_id`, appears in the calling staff's own worklist/task list, not in "Hàng Đợi Chung".
- [ ] Same for `schedule_followup_at` → follow-up task.
- [ ] `source` field on both is `"callback"`/`"followup"` respectively, distinct from `"manual"`.
- [ ] Existing tests referencing these two task-creation code paths updated for the new `source` value and new assignee assertion; no regression in `derive_task_kind` output (still `contact`/not-confident, same as before).

## Risk Assessment

- **Risk**: any existing test/UI code hardcodes `source == "manual"` as a filter for these auto-generated reminder tasks (e.g. a "manual tasks only" view) — would now miss callback/follow-up tasks. Search for `TASK_SOURCE_MANUAL` usages across templates/screens during implementation to catch this before it ships.
- **Risk**: if `actor_id` is `None` (side effects invoked without an authenticated actor — shouldn't happen in practice since both call sites require a logged-in user, but `execute_side_effects`'s signature allows `Optional[str]`) — `assignee_user_id=None` degrades to today's unassigned behavior, not a regression, just a no-op safety fallback.
- **Rollback**: single-file (plus one small domain-entity addition) change; revert the two dict literals and the source constants.
