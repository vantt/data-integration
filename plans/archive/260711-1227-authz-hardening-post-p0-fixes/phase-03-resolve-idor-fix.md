---
phase: 3
title: "Resolve IDOR Fix"
status: completed
priority: P1
dependencies: [1]
---

# Phase 3: Resolve IDOR Fix

## Overview

`resolve_actions_and_tasks()` (`activity_side_effects.py:44-51`, extracted from `execute_side_effects` step 7 during the prior session's phase 6) dismisses actions / completes tasks by client-supplied `action_id`/`task_id` lists with zero check that those ids belong to the `party_id` of the activity currently being finalized. Any staff can submit foreign ids (via the hidden form field or `resolve-async` route) and dismiss/complete another customer's or another staff's items.

**Scope broadened after red-team review (2026-07-11) — the original design fixed the named function but missed 2 structurally identical gaps found during review, both now folded into this phase (per user decision to fix rather than track separately, since the tool needed — `AuthorizationService.is_same_party()` — already exists once Phase 1 lands):**

1. **Sibling unguarded path in the SAME file**: `execute_side_effects()` step 6 ("Complete linked task(s)", ~line 230-236) iterates `complete_task_ids` and calls `task_svc.transition_status(tid, "done")` directly — no party check, same vulnerability class as the originally-scoped `resolve_actions_and_tasks()`, 10 lines away in the same function. `complete_task_ids` is client-controlled via `POST /api/activities/{activity_id}/finalize`'s Form param and `POST /customers/{party_id}/log-activity`'s `task_id`/`complete_task` params.
2. **A second, entirely separate live instance of the same IDOR class**: `PATCH /customers/{party_id}/tasks/{task_id}/{done,cancel,postpone}` (`screen_customer_360_tasks.py:59-108`) takes `party_id` as a URL path segment but calls `task_svc.transition_status(task_id, ...)`/`get_task(task_id)`/`update_task(task_id, ...)` using only `task_id` — never cross-checked against the task's actual party. `task_id` values are visible across the app (worklist rows, task board), so exploiting this requires no more than viewing another customer's page first.

## Requirements

- Every `action_id` in `resolve_action_ids` is resolved to its true `party_id` server-side; mismatch vs. the activity's own `party_id` → skip that id (log a warning), do NOT dismiss/snooze it.
- Every `task_id` in `resolve_task_ids` is resolved the same way via `task_svc.get_task(task_id).party_id`.
- **Same check applied to `complete_task_ids` (step 6) — not just `resolve_task_ids` (step 7).** Both loops in `execute_side_effects()` that call `transition_status()` on a client-supplied id must be guarded, not just the one the original scope named.
- **`screen_customer_360_tasks.py`'s 3 handlers (`done`/`cancel`/`postpone`) verify the fetched task's `party_id` matches the URL's `party_id` before mutating** — skip/404 on mismatch (this is a different call shape than the bulk-resolve functions: single id, already fetched via `get_task`, so the check is a direct `is_same_party` call, not a resolve-then-compare).
- Preserve the existing per-item try/except isolation (one bad/mismatched id must not abort processing of the rest) for the bulk-resolve paths.
- No behavior change for the common case (ids that DO belong to the right party) — this is purely an added guard, not a redesign.

## Architecture

`ActionStatePort` (`domain/ports/action_state_port.py:7-20`) currently exposes `dismiss()`/`snooze()`/`reopen()` but not party resolution. `SQLiteActionStateRepository` already has a private `_resolve_party_and_action_type()` (`action_state_repository.py:81-118`) doing exactly this lookup for `dismiss()`'s own internal (party_id, action_type) TTL-dismissal write — expose it as a new port method rather than duplicating the cache-join logic.

`resolve_actions_and_tasks()` gains a required `party_id: str` parameter (the activity's own party_id — already available at every call site, since `execute_side_effects`/`_bulk_resolve`/`handle_resolve_async` all already have it in scope) and does the resolve+compare before each dismiss/snooze/transition call. **`execute_side_effects()`'s step 6 (`complete_task_ids`) gets the identical guard inline** (it doesn't go through `resolve_actions_and_tasks()`, so the check is added directly in that loop, using the same `authz.is_same_party(task_svc.get_task(tid).party_id, party_id)` pattern).

**Uses `AuthorizationService` from Phase 1** for the comparison itself (`authz.is_same_party(resolved_party, party_id)`) rather than a raw `==` — this is the 2nd consumer that justifies centralizing the decision logic in Phase 1 instead of writing 2 near-identical inline comparisons across 2 unrelated modules (`task_service.py` here, `activity_side_effects.py` there). `resolve_actions_and_tasks()` takes `authz: AuthorizationService` as a new required parameter (same "required, not Optional" reasoning as Phase 2 — no silent-skip failure mode for a security check).

**Full DI threading, no inline fallback (per Phase 1's revised design)**: `authz` is threaded as an explicit parameter through the ENTIRE call chain from `composition.py` to `resolve_actions_and_tasks()` — both chains: (a) `execute_side_effects(..., authz=authz)` → `resolve_actions_and_tasks(..., authz=authz)`, and (b) `register_activity_routes(..., authz=authz)` → `handle_resolve_async` → `bulk_resolve(..., authz=authz)` → `resolve_actions_and_tasks(..., authz=authz)`. Every function in both chains gains an `authz` parameter — this is more files touched than "just the 2 endpoints," but it's what "one shared instance, no ad-hoc re-construction" actually requires, and each individual change is a mechanical 1-parameter addition.

**`screen_customer_360_tasks.py`'s 3 handlers** are a different shape — single `task_id`, already fetched via `task_svc.get_task(task_id)` before the mutation — so the fix there is direct: `task = task_svc.get_task(task_id); if not authz.is_same_party(task.party_id if task else None, party_id): return <404 or 403>` before calling `transition_status`/`update_task`. This needs `authz` threaded into whatever router-factory function registers these 3 routes too.

## Related Code Files

- Modify: `crm/src/domain/ports/action_state_port.py` (add `resolve_party_id(action_id: str) -> Optional[str]` to the Protocol)
- Modify: `crm/src/adapters/outbound/sqlite/action_state_repository.py` (implement `resolve_party_id` as a thin wrapper: `return self._resolve_party_and_action_type(action_id)[0] if resolved else None` — reuse the existing private method verbatim, do not duplicate the cache-join SQL)
- Modify: `crm/src/application/activity_side_effects.py` (`resolve_actions_and_tasks`, ~line 44-90 — add `party_id`+`authz` params, add resolve+verify step before each dismiss/snooze/transition; **also `execute_side_effects()` step 6, ~line 230-236 — add the identical guard to the `complete_task_ids` loop**, and add `authz` param to `execute_side_effects()`'s own signature to thread it to both step 6 and its call into `resolve_actions_and_tasks` at ~line 246)
- Modify: `crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py` (`bulk_resolve`/`_bulk_resolve` — thread `party_id`+`authz` through to `resolve_actions_and_tasks`; this function already receives `party_id` from its own caller, `handle_resolve_async`, per prior session's phase 2 amendment work)
- Modify: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` (`register_activity_routes` factory signature — add `authz: AuthorizationService` param; thread into every call to `execute_side_effects`/`bulk_resolve` inside this file's handlers — `party_id` is already a path param on every relevant route, purely additive)
- **NEW — 2nd IDOR site**: Modify `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_tasks.py` (3 handlers at ~line 59-108 — `done`/`cancel`/`postpone` — add the `is_same_party` guard before each mutation; add `authz` to this file's router-factory signature)
- **NEW — test files broken by `resolve_actions_and_tasks`/`bulk_resolve`'s new required params:**
  - `crm/src/tests/test_outcome_bulk_resolve.py` — ~19-20 direct calls to `_bulk_resolve`/`bulk_resolve`, ALL need `party_id=`/`authz=` added (verify exact count/lines via `grep -n "_bulk_resolve(\|bulk_resolve(" crm/src/tests/test_outcome_bulk_resolve.py` at implementation time — red-team review counted 19 across lines 82-220, re-check for drift)
  - `crm/src/tests/test_activity_disposition_api_routes.py` — verify whether any test here calls `resolve_actions_and_tasks`/`execute_side_effects` directly with a bare `MagicMock()` for `action_state` that would need `authz` added too
- Reference: `crm/src/application/authorization_service.py` (Phase 1 — `is_same_party()` method consumed here)

## Implementation Steps

1. Add `resolve_party_id(action_id: str) -> Optional[str]` to `ActionStatePort` protocol.
2. Implement in `SQLiteActionStateRepository`: call the existing `_resolve_party_and_action_type(action_id)` and return just the party_id half (or `None` if the private method returns `None`). Do not rewrite the SQL — this is a pure wrapper.
3. In `activity_side_effects.py`, add `party_id: str` and `authz: AuthorizationService` (both required, import from Phase 1's `authorization_service.py`) as new params to `resolve_actions_and_tasks()`. Before each `action_state.dismiss(aid, ...)`/`action_state.snooze(aid, ...)` call, resolve `resolved_party = action_state.resolve_party_id(aid)` and skip (log warning, continue loop) unless `authz.is_same_party(resolved_party, party_id)` is `True` (this also fails closed on `resolved_party is None`, matching `is_same_party`'s own defined behavior from Phase 1). Before each `task_svc.transition_status(tid, ...)` call, do the equivalent check via `task_svc.get_task(tid)`.
4. Add `authz: AuthorizationService` to `execute_side_effects()`'s own signature. Pass it to `resolve_actions_and_tasks()` at the step 7 call site (~line 246), AND add the identical guard directly inside step 6's `complete_task_ids` loop (~line 230-236) — resolve each `tid` via `task_svc.get_task(tid)`, skip (log warning) unless `authz.is_same_party(task.party_id if task else None, party_id)`.
5. Thread `authz` through the FULL call chain from `composition.py` to both consumers — no inline construction anywhere:
   - `register_activity_routes(..., authz: AuthorizationService)` — new param on the factory in `screen_customer_360_activity.py`; every handler in this file that calls `execute_side_effects`/`bulk_resolve` passes `authz` through.
   - `outcome_resolve_helpers.bulk_resolve(..., party_id, authz)` — accepts and forwards both to `resolve_actions_and_tasks`.
   - Wherever `register_activity_routes` is invoked from `composition.py`, pass the SAME shared `AuthorizationService` instance Phase 1/Phase 2 already wired (reuse, don't re-instantiate).
6. **2nd IDOR site**: in `screen_customer_360_tasks.py`, add `authz: AuthorizationService` to this file's router-factory signature. In each of the 3 handlers (`done`/`cancel`/`postpone`, ~line 59-108): after `task = task_svc.get_task(task_id)`, before the mutation, check `authz.is_same_party(task.party_id if task else None, party_id)` — on failure, return **403** (user decision during validation, 2026-07-11: explicit rejection is clearer UX than 404 here — verify this file's existing error-response pattern for consistency in body/headers, but the status code itself is decided).
7. Grep for any OTHER caller of `resolve_actions_and_tasks`/`bulk_resolve`/`execute_side_effects` (both production AND test files) to confirm the file list above is exhaustive — red-team review found `test_outcome_bulk_resolve.py` (~19-20 calls) and flagged `test_activity_disposition_api_routes.py` as needing verification; re-run this grep fresh rather than trusting the review's counts blindly (line numbers may have drifted).
8. Update all test call sites found in step 7 — add `party_id=`/`authz=` to each. For `test_outcome_bulk_resolve.py`'s ~19-20 calls, this is mechanical (same 2 kwargs added to each) but must cover all of them, not a sample.
9. Add tests: mismatched `action_id` (belongs to a different party) → `action_state.dismiss`/`snooze` NOT called for that id, other valid ids in the same batch still processed correctly (per-item isolation preserved). Same for mismatched `task_id` in `resolve_task_ids`. **Same for mismatched `task_id` in `complete_task_ids`** (step 6's new guard — this needs its own test, it's a different code path than step 7's). Unresolvable id (not found at all) → also skipped, not treated as automatically valid. **New: `screen_customer_360_tasks.py`'s 3 handlers with a `task_id` belonging to a different party → rejected, verified for all 3 (`done`/`cancel`/`postpone`), not just one.**

## Success Criteria

- [x] Mismatched `action_id` (real id, wrong party) is skipped, not dismissed/snoozed — verified by test.
- [x] Mismatched `task_id` in `resolve_task_ids` is skipped, not transitioned — verified by test.
- [x] **Mismatched `task_id` in `complete_task_ids` (step 6) is skipped, not transitioned — verified by a SEPARATE test from the `resolve_task_ids` one, since it's a different code path.**
- [x] **`screen_customer_360_tasks.py`'s `done`/`cancel`/`postpone` all reject a cross-party `task_id` — 3 tests, not 1.**
- [x] Valid ids in the same batch as an invalid one are still processed correctly (isolation preserved).
- [x] Unresolvable/unknown id fails closed (skipped), not open.
- [x] No behavior change for the all-valid-ids common case — full existing bulk-resolve test suite still green, **including the previously-broken calls in `test_outcome_bulk_resolve.py` (40 call sites across 6 files, re-grepped fresh), now updated and passing.**
- [x] Both call paths (`execute_side_effects` step 7 AND `/reason/resolve-async`) are covered — this is the same 2-path gap the prior session's outcome-gating fix had to close (report shown for the "+Nhắn Zalo" bypass), don't repeat that mistake by fixing only one path.
- [x] `authz` is a single shared instance across all consumers (Phase 1, 2, 3) — no ad-hoc `AuthorizationService()` construction anywhere outside `composition.py`, verified by grep at the end of this phase (code-reviewer independently re-verified).

## Risk Assessment

- **Risk**: `resolve_party_id`'s underlying cache-join (`_resolve_party_and_action_type`) may fail to resolve legitimately-valid ids if the warehouse cache is stale/the action already rotated out of `wh_action_queue` between when it was surfaced to the client and when the resolve request arrives — this would turn a previously-working case into a skipped/silently-ignored one. Check the existing `dismiss()` path's tolerance for this same edge case (it already depends on the same private method for its own TTL-dismissal write, so this risk is not NEW, just now also gates dismiss/snooze itself rather than only the secondary TTL bookkeeping) — if `dismiss()` already handles a `None` resolution gracefully (best-effort per its own docstring: "silently skipped... not raised"), matching that same graceful-degradation posture here (skip, log, don't hard-fail the whole batch) is consistent, but confirm this doesn't newly break a previously-working flow for currently-active actions.
- **Risk (was Critical, now in scope)**: the original design fixed `resolve_actions_and_tasks()` but left `complete_task_ids` (same file, 10 lines away) and `screen_customer_360_tasks.py` (different file, same vulnerability class) unguarded — found by red-team review, not the original scope. Both are now explicitly in this phase's Requirements/Implementation Steps/Success Criteria — do not let a future "cleanup" pass accidentally drop either while implementing.
- **Risk (was Critical, now in scope)**: `test_outcome_bulk_resolve.py`'s ~19-20 direct calls to `bulk_resolve`/`_bulk_resolve` were not in the original file list and would have broken on this phase's signature change. Now explicit in Related Code Files/Implementation Steps — verify the count is still accurate at implementation time (code may have shifted since the review).
- **Rollback**: additive port method + required params threaded through 2 call chains + the new 2nd-site guard — more files than originally scoped, but each change (port method, 2 threaded params per function, 1 guard per handler) is independently revertable.
