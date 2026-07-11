---
phase: 5
title: "M05 Return-To-Stay Test Coverage"
status: completed
priority: P3
dependencies: []
---

# Phase 5: M05 Return-To-Stay Test Coverage

## Overview

`screen_modal_task.py`'s `post_task`/`patch_task_edit` handlers shipped `return_to=stay` support in a prior session (`plans/260711-0933-fix-p0-outreach-flow-gaps`) with only a manual-verify checklist — no pytest regression guard exists for M05 specifically (confirmed by research: `crm/src/tests/` has zero tests for these 2 handlers; the closest existing coverage, `test_quick_outcome_cockpit_post.py`, tests M08's `handle_log_activity`, not M05). Add tests matching the established handler-recovery pattern already used in that file.

## Requirements

- `post_task` (M05 create): `return_to="stay"` → no `HX-Redirect` header, gets `HX-Trigger` instead. `return_to` omitted/default → unchanged existing redirect behavior (regression guard for the with-party and no-party-post-Phase-4 cases).
- `patch_task_edit` (M05 edit): same 2 cases.
- Tests follow the exact fixture/invocation pattern already established in `test_quick_outcome_cockpit_post.py` (`_get_*_handler()` router-mock recovery + `asyncio.run(handler(**kwargs))` + assert on response headers) so this test file reads consistently with its sibling.

## Related Code Files

- Create or extend: `crm/src/tests/test_modal_task_return_to.py` (new file — no existing dedicated test file for `screen_modal_task.py`, per research; a fresh file matching the naming convention of sibling test files is cleaner than overloading `test_quick_outcome_cockpit_post.py`, which is scoped to M08)
- Reference only: `crm/src/tests/test_quick_outcome_cockpit_post.py:28-49,121-140` (the exact handler-recovery + invocation pattern to mirror); `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py:141-192` (`post_task`, `patch_task_edit`, and the `make_task_modal_router` factory signature — confirm exact current param names before writing test kwargs, this file has shifted since the cited research)

## Implementation Steps

1. Write a `_get_task_modal_handlers()` helper mirroring `test_quick_outcome_cockpit_post.py`'s `_get_log_activity_handler()` shape: register `make_task_modal_router` on a `MagicMock()` router with mocked `profile`/`task_svc`/`app_users` dependencies, recover both the `post_task` and `patch_task_edit` handlers from the router mock's `post`/`patch` decorator call args.
2. Test `post_task` with `return_to="stay"` → assert response has no `HX-Redirect` header, has `HX-Trigger` (matching whatever exact trigger name Phase 1 of the prior session's plan actually shipped — verify current code, do not assume the value from memory).
3. Test `post_task` with `return_to="redirect"` (or omitted) → assert `HX-Redirect` present, value matches existing logic (`/customers/{party_id}?tab=tasks` or `/tasks` depending on `party_id`).
4. Same 2 test cases for `patch_task_edit`.
5. Run new tests + full suite to confirm green, no interaction with Phase 1-4's changes (this phase touches test files only, zero production code).

## Success Criteria

- [x] `post_task` `return_to=stay` → no-redirect behavior test-covered.
- [x] `post_task` `return_to=redirect`/default → existing redirect behavior test-covered (regression guard).
- [x] `patch_task_edit` — same 2 cases covered.
- [x] New test file follows existing sibling test file's fixture pattern (no novel test infrastructure introduced).
- [x] Full CRM test suite green.

## Risk Assessment

- **Risk**: none of production consequence — this phase is test-only, zero production files touched, zero behavior change possible.
- **Rollback**: delete the new test file; trivial.

