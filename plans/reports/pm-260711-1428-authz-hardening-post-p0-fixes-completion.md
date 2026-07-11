# PM Sync Report — Authz Hardening + Post-P0 Fixes

**Plan**: `plans/260711-1227-authz-hardening-post-p0-fixes/` | **Status**: pending → **completed** | **Date**: 2026-07-11

## Phase Completion

| Phase | Name | Status | Tests Added | Notes |
|---|---|---|---|---|
| 1 | Authorization Service Foundation | Completed | 7 | `is_owner`/`is_same_party`, zero-IO, wired once in composition.py |
| 2 | Unclaim Ownership + Audit Trail | Completed | 14 | fail-closed guard verified NOT fail-open; audit note DB-verified |
| 3 | Resolve IDOR Fix | Completed | ~15 new + 40 sites updated | 3 distinct IDOR gaps closed (resolve_actions_and_tasks, execute_side_effects step 6, screen_customer_360_tasks.py) |
| 4 | No-Party Task Creation Fix | Completed | 7 | worklist header 404 fixed; dead-template bug flagged separately |
| 5 | M05 Return-To-Stay Test Coverage | Completed | 8 | test-only, zero production changes |

## Verification

- Full CRM suite: **1152 passed, 1 skipped, 0 failed** — independently re-run by controller + by code-reviewer (not just trusted from implementing agents' self-reports).
- Mandatory code-reviewer pass: **0 blocking findings**. All 12 prior red-team findings re-verified as genuinely fixed in landed code (esp. the fail-open→fail-closed guard correction, `NoteService` vs raw-repo wiring, single-shared-`authz`-instance discipline).
- 2 informational-only residuals, both accurately self-disclosed, neither blocking: Phase 2's manual UI click-through not performed (server-side fully test-covered); Phase 4's pre-existing dead `GET /tasks/modal/create` template (out of scope, flagged for separate decision).

## Session Note

Mid-execution, the harness session was interrupted/resumed once (Phase 2's background agent showed `status: stopped` with no completion notification). Resumed it via `SendMessage` from its saved transcript rather than restarting — it re-oriented against its own partial diff, finished cleanly, full suite green. No work was lost.

## Docs Impact

No `./docs` updates triggered — this is an internal security-hardening change (authz logic, IDOR fixes, a 404 fix, test coverage) with no new user-facing API surface, no schema change, no config/env var change, no architecture shift warranting `docs/system-architecture.md` or similar updates.

## Unresolved Questions

1. Dead-template bug (`GET /tasks/modal/create` → missing `fragments/modal_create_task.html`) — flagged by Phase 4, needs a user decision on fix vs. leave as pre-existing dead code (out of this plan's scope either way).
2. Manual UI click-through of Phase 2's new "Trả việc" reason-picker `<select>` — recommend a quick visual pass before considering this plan fully shipped, since it's the one path not exercised outside pytest.
