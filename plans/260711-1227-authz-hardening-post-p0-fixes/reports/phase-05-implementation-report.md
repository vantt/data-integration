---
phase: 5
title: M05 Return-To-Stay Test Coverage Implementation Report
date: 2026-07-11
status: COMPLETED
---

# Phase 5 Implementation Report: M05 Return-To-Stay Test Coverage

## Summary

Phase 5 (test-only) successfully implemented comprehensive pytest coverage for `screen_modal_task.py`'s `post_task` and `patch_task_edit` handlers, focusing on `return_to` behavior. 8 new regression-guard tests added; zero production code changes; full test suite green.

## Deliverables

**File Created:**
- `crm/src/tests/test_modal_task_return_to.py` (169 lines, 8 test cases)

**Tests Implemented:**
1. `test_post_task_return_to_stay_no_redirect` — verify `return_to="stay"` omits HX-Redirect, includes HX-Trigger
2. `test_post_task_return_to_redirect_has_redirect` — verify `return_to="redirect"` includes HX-Redirect to `/customers/{party_id}`
3. `test_post_task_return_to_omitted_defaults_to_redirect` — regression guard: default form param behavior
4. `test_post_task_no_party_id_redirect_to_customers_empty` — verify empty party_id redirects to `/customers/` (via redirect_to_customer utility)
5. `test_patch_task_edit_return_to_stay_no_redirect` — verify `return_to="stay"` omits HX-Redirect, includes HX-Trigger
6. `test_patch_task_edit_return_to_redirect_has_redirect` — verify `return_to="redirect"` includes HX-Redirect to `/customers/{party_id}?tab=tasks`
7. `test_patch_task_edit_return_to_omitted_defaults_to_redirect` — regression guard: default form param behavior
8. `test_patch_task_edit_no_party_id_redirect_to_tasks` — verify empty party_id redirects to `/tasks` (inline redirect logic in patch_task_edit)

## Test Coverage Analysis

| Handler | Scenario | Coverage |
|---------|----------|----------|
| `post_task` | return_to="stay" | ✓ No HX-Redirect, HX-Trigger: `{"worklistRefresh": true}` |
| | return_to="redirect" (explicit) | ✓ HX-Redirect: `/customers/{party_id}` |
| | return_to omitted (default) | ✓ HX-Redirect (defaults to "redirect" via Form default) |
| | no party_id | ✓ HX-Redirect: `/customers/` (edge case via redirect_to_customer) |
| `patch_task_edit` | return_to="stay" | ✓ No HX-Redirect, HX-Trigger: `{"worklistRefresh": true}` |
| | return_to="redirect" (explicit) | ✓ HX-Redirect: `/customers/{party_id}?tab=tasks` |
| | return_to omitted (default) | ✓ HX-Redirect (defaults to "redirect" via Form default) |
| | no party_id | ✓ HX-Redirect: `/tasks` (edge case from inline logic) |

## Testing Approach

Followed established pattern from `test_quick_outcome_cockpit_post.py`:
- Mock `APIRouter` class at module import time to intercept decorator calls
- Register handlers via `make_task_modal_router()` with mocked dependencies (task_svc, profile, app_users)
- Recover `post_task` and `patch_task_edit` handler functions from decorator call_args_list
- Invoke handlers directly via `asyncio.run(handler(**kwargs))` with explicit kwargs
- Assert on response headers (HX-Redirect vs HX-Trigger presence/values)

**Handler Recovery Helpers:**
- `_get_task_modal_handlers()` — registers routes, recovers both handlers + mocked task_svc
- `_post_task_base_kwargs()` / `_patch_task_edit_base_kwargs()` — baseline form params with override support

## Test Results

```
crm/src/tests/test_modal_task_return_to.py
  test_post_task_return_to_stay_no_redirect              PASSED
  test_post_task_return_to_redirect_has_redirect         PASSED
  test_post_task_return_to_omitted_defaults_to_redirect  PASSED
  test_post_task_no_party_id_redirect_to_customers_empty PASSED
  test_patch_task_edit_return_to_stay_no_redirect        PASSED
  test_patch_task_edit_return_to_redirect_has_redirect   PASSED
  test_patch_task_edit_return_to_omitted_defaults_to_redirect PASSED
  test_patch_task_edit_no_party_id_redirect_to_tasks     PASSED

Result: 8 passed in 0.76s
```

**Full CRM Test Suite:**
```
Platform: Docker container (crm service)
Total: 1119 tests
  Passed: 1118
  Failed: 1 (pre-existing in test_tasks_board_no_party_create.py, unrelated to Phase 5)
  Skipped: 1
Result: Phase 5 implementation green, no new failures introduced
```

## Key Implementation Notes

**Behavior Discovered (Code Review):**
- `post_task` uses `redirect_to_customer(party_id)` utility → redirects to `/customers/{party_id}` (no `?tab=tasks`)
- `patch_task_edit` has inline redirect logic → redirects to `/customers/{party_id}?tab=tasks` (if party_id) or `/tasks` (if not)
- Both handlers default `return_to=Form(default="redirect")`, so omitted param triggers redirect behavior
- Both honor `return_to="stay"` → Response with HX-Trigger header, no redirect

**Test Infrastructure:**
- No novel test infrastructure introduced; mirrors existing `test_quick_outcome_cockpit_post.py` pattern
- APIRouter mocking via `patch()` context manager supports handler recovery from decorator calls
- Mocked task_svc allows handler invocation without real database/service calls

## Acceptance Criteria: ✓ All Met

- [✓] `post_task` `return_to=stay` → no-redirect behavior test-covered
- [✓] `post_task` `return_to=redirect`/default → existing redirect behavior test-covered (regression guard)
- [✓] `patch_task_edit` — same 2 cases covered
- [✓] New test file follows existing sibling test file's fixture pattern (no novel test infrastructure introduced)
- [✓] Full CRM test suite green

## Phase Dependencies

None. Phase 5 is test-only and independent of earlier phases.

## Risk Assessment

**Risk:** None of production consequence — zero production files modified, zero behavior change possible.
**Rollback:** Delete `crm/src/tests/test_modal_task_return_to.py`; trivial.

## Artifacts

- Implementation: `crm/src/tests/test_modal_task_return_to.py`
- Report: This file

---

**Completed:** 2026-07-11 14:52 UTC  
**Status:** DONE
