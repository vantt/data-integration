# Phase 03 Implementation Report — Resolve IDOR Fix

## Executed Phase
- Phase: phase-03-resolve-idor-fix
- Plan: D:\Vantt\app\data-integration\plans\260711-1227-authz-hardening-post-p0-fixes
- Status: completed

## Files Modified

Production:
- `crm/src/domain/ports/action_state_port.py` — added `resolve_party_id(action_id) -> Optional[str]` to Protocol.
- `crm/src/adapters/outbound/sqlite/action_state_repository.py` — implemented `resolve_party_id` as thin wrapper over existing `_resolve_party_and_action_type`.
- `crm/src/application/activity_side_effects.py` — `resolve_actions_and_tasks()` gained required `party_id`/`authz` kwargs + resolve-then-compare guard before every dismiss/snooze/transition; `execute_side_effects()` gained required `authz` kwarg, threaded to step 7's call, and step 6's `complete_task_ids` loop got the identical inline guard.
- `crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py` — `bulk_resolve()` gained required `party_id`/`authz` kwargs, forwarded to `resolve_actions_and_tasks`.
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` — `register_activity_routes()` gained required `authz` param; `_run_side_effects` closure and `handle_resolve_async`'s `_bulk_resolve` call both thread it through.
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_tasks.py` — `register_task_routes()` gained required `authz` param; `done`/`cancel`/`postpone` handlers each resolve the task first, then `authz.is_same_party(task.party_id, party_id)` gate — reject with **403** on mismatch (before mutating).
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py` — `make_customer_360_router()` gained required `authz` param, threaded into both `register_activity_routes`/`register_task_routes` calls.
- `crm/src/composition.py` — `make_customer_360_router(...)` call now passes `authz=services["authz"]` (same shared instance Phase 1/2 wired).

Tests (new/updated):
- `crm/src/tests/test_outcome_bulk_resolve.py` — all ~20 `_bulk_resolve` calls updated with `party_id=`/`authz=`; added `TestBulkResolveIdorGuard` (5 tests: mismatched action_id, mismatched task_id, unresolvable action_id, unresolvable task_id, mismatch on snooze path).
- `crm/src/tests/test_activity_disposition_api_routes.py` — `_register()` helper defaults `authz` to a forced-True stand-in (covers all `_register`-based tests incl. resolve-async/M08-repoint paths without touching each test body); 7 direct `execute_side_effects` calls updated; added `TestSideEffectsIdorGuard` (4 tests: step 6 mismatch, step 6 unresolvable, step 7 action mismatch, step 7 task mismatch — using a REAL `AuthorizationService`).
- `crm/src/tests/test_bulk_resolve_endpoint.py`, `test_claim_context_snooze_r14.py`, `test_m08_quick_note_prefill.py`, `test_quick_outcome_cockpit_post.py` — `authz` threaded into each `register_activity_routes` call site (forced-True stand-in; these tests aren't about the IDOR guard itself).
- `crm/src/tests/test_customer_360_tasks_party_guard.py` (new) — 9 tests covering all 3 `screen_customer_360_tasks.py` handlers: cross-party rejection (403) + own-task regression check for each, plus an unresolvable-task-id fail-closed test.
- `crm/src/tests/test_action_dismissal_ttl.py` — added `TestResolvePartyId` (3 tests against the real DB-backed cache-join: resolves correctly, unknown action_id → None, unlinked party → None).

## Tasks Completed
- [x] `resolve_party_id` port method + repo implementation (thin wrapper, no duplicated SQL)
- [x] `resolve_actions_and_tasks()` IDOR guard (dismiss + snooze + task transition, step 7)
- [x] `execute_side_effects()` step 6 (`complete_task_ids`) identical guard — separate loop, separately tested
- [x] `screen_customer_360_tasks.py` 2nd IDOR site — `done`/`cancel`/`postpone` all guarded, 403 on mismatch
- [x] Full DI threading — composition.py → make_customer_360_router → register_activity_routes/register_task_routes → execute_side_effects/bulk_resolve → resolve_actions_and_tasks, single shared `authz` instance throughout
- [x] All broken test call sites found via fresh grep and updated (40 call sites across 6 test files)
- [x] New tests: mismatch isolation, unresolvable fail-closed, all 3 task-route handlers, step 6 vs step 7 as separate code paths

## Tests Status
- Type check: N/A (no dedicated typecheck script in this repo's CRM subproject; relies on pytest + runtime import checks)
- Unit/integration tests: **pass** — `1152 passed, 1 skipped` (full `crm/src/tests/` suite in the `crm` container)
- Runtime smoke check: `docker compose restart crm` → clean startup, `/healthz` 200, `/customers/1` route resolves without a 500 (confirms no missing-kwarg wiring bug in the real app, not just mocked tests)

## Grep Verification (Success Criteria)
`AuthorizationService()` construction outside `composition.py`: **none in production code** (`crm/src/adapters`, `crm/src/application` clean); all other matches are in `crm/src/tests/*` (legitimate — Phase 1/2 established the same pattern of real instances in pure-logic tests).

## Issues Encountered
- None blocking. One design call made during test-fixing: for the ~30 pre-existing tests not specifically exercising the IDOR guard, used a `MagicMock(spec=AuthorizationService, is_same_party=True)` stand-in rather than reconfiguring every mock's `resolve_party_id`/`get_task` return value — mechanical, minimal-diff, and the guard's actual resolve-then-compare logic is separately covered by dedicated tests using a REAL `AuthorizationService`.

## Next Steps
None outstanding for this phase. Phase depends only on Phase 1 (done, merged). No downstream phase blocked by this work per the plan's dependency graph shown to me.

## Unresolved Questions
None.
