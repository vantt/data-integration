# Phase 2 Implementation Report — Unclaim Ownership and Audit Trail

## Executed Phase
- Phase: phase-02-unclaim-ownership-and-audit-trail
- Plan: D:\Vantt\app\data-integration\plans\260711-1227-authz-hardening-post-p0-fixes
- Status: completed

## Files Modified

- `crm/src/domain/entities/task.py` (+24 lines) — added `VALID_UNCLAIM_REASONS` (flat code-string list, matching `activity.py`'s `VALID_OUTCOME_REASONS` shape) and `UNCLAIM_REASON_LABELS` (VN label lookup, consumed only by `TaskService` for the audit-note body — templates hardcode their own VN option labels, matching this codebase's existing reason-picker convention in `c360_call_cockpit_panel.html`).
- `crm/src/application/task_service.py` (+~49/-4 lines) — `__init__` now takes `authz: AuthorizationService` and `notes: NoteService` as **keyword-only required** params (`*, authz, notes, db=None, party_repo=None`); `unclaim_customer_actions(party_id, actor_id=None, reason=None) -> str` returns `"ok" | "not_found" | "forbidden"`, fail-closed guard `if not actor_id or not self._authz.is_owner(...): return "forbidden"`, audit note written via `self._notes.add_note(...)` (NoteService, not raw repo) wrapped in try/except-log.
- `crm/src/composition.py` (+20/-6 lines) — `TaskService(...)` now wired with `authz=authz_svc` (the SAME `AuthorizationService()` instance also exposed as `services["authz"]` — single shared instance, no duplication) and `notes=note_svc` (the already-constructed `NoteService`, not `sqlite_repos["note"]`).
- `crm/src/adapters/inbound/web/screen_worklist.py` (+~35/-6 lines) — `TaskClaimWriter` Protocol's `unclaim_customer_actions` signature updated to `-> str` with `actor_id`/`reason` params; `handle_unclaim_customer` adds `reason: str = Form(default="")`, explicit `401` on empty `uid` (before any other logic), `422` on invalid/missing reason, narrow try/except around the service call only, explicit `result == "forbidden"` → `403` branching outside the try/except.
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` (+~20/-6 lines) — `handle_c360_unclaim_customer` same shape (401/422/403), reusing this file's existing `getattr(getattr(request.state, "current_user", None), "user_id", "")` pattern.
- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` — "Trả việc" button replaced with an inline `<select id="unclaim-reason-{{ t.task_id }}">` (VN-labeled options, hardcoded per existing convention) + button, disabled until a reason is chosen (`onchange="this.nextElementSibling.disabled = !this.value"`), `hx-vals` reads the select value.
- `crm/src/adapters/inbound/web/templates/fragments/c360_insight_panel.html` — same inline reason-picker pattern (`id="c360-unclaim-reason-{{ party_id }}"`, single instance per panel so no per-row id needed).
- 9 test call sites (phase file said "8 across 5 files"; re-grepped per its own instruction and found 9 — same 5 files, `test_task_claim_action_types_snapshot.py` has 4 sites not the phase file's original count) — all updated with `authz=AuthorizationService()` (real, cheap/stateless) + `notes=MagicMock()` (stub; none of these files exercise the unclaim/audit path):
  - `crm/src/tests/test_task_service_title_fallback.py:33`
  - `crm/src/tests/test_task_kind.py:155,231` (renumbered after edits: ~156,241)
  - `crm/src/tests/test_task_claim_action_types_snapshot.py:49,67,80,113` — added a shared `_make_svc()` helper to avoid repeating the boilerplate 4×
  - `crm/src/tests/test_claim_context_snooze_r14.py:71`
  - `crm/src/tests/test_activity_disposition_api_routes.py:134`
- **New**: `crm/src/tests/test_unclaim_ownership_and_audit_trail.py` (14 tests) — dedicated coverage for this phase's success criteria (see below).

## Tasks Completed

- [x] `VALID_UNCLAIM_REASONS` flat code list + `UNCLAIM_REASON_LABELS` VN lookup added to `task.py`.
- [x] `TaskService.__init__` — `authz`/`notes` keyword-only required params (chosen over the positional-with-defaults alternative per the phase file's explicit recommendation — forces every call site to pass by name, catching mistakes immediately).
- [x] `unclaim_customer_actions` — fail-closed guard verbatim as specified (`if not actor_id or not self._authz.is_owner(...)`), audit note via `NoteService.add_note` (real port, not raw repo), try/except-log around the note write only (never blocks the unclaim itself).
- [x] `composition.py` — single shared `AuthorizationService()` instance (`authz_svc`) reused for both `services["authz"]` and `TaskService(authz=authz_svc, ...)`; `notes=note_svc` is the same `NoteService` instance as `services["note"]`.
- [x] Both route handlers (worklist S01 + C360) — 401 unauthenticated (checked first), 422 invalid/missing reason, narrow try/except around the service call, explicit `"forbidden"` → 403 mapping outside the try/except.
- [x] `TaskClaimWriter` Protocol updated to `-> str` with the real params.
- [x] All 9 (see note above) test call sites updated, passing.
- [x] Both templates updated with an inline reason-picker gating the unclaim button.
- [x] Full CRM suite green.

## Tests Status

- Type check: N/A (this codebase has no dedicated typecheck step beyond pytest/runtime; `create_app()` import-and-build smoke-checked manually, passed).
- Unit tests: **pass** — `crm/src/tests/test_unclaim_ownership_and_audit_trail.py`: 14/14 passed. Covers:
  - `test_not_found_when_no_claim_exists`
  - `test_forbidden_when_actor_is_not_the_assignee` (criterion a — 2 different non-empty actor_ids, claim state + note-absence verified)
  - `test_forbidden_when_actor_id_is_empty` (criterion b — **dedicated** test, both `""` and `None`, distinct from the above; this is the exact fail-open regression case)
  - `test_ok_persists_audit_note_with_correct_fields` (criterion c — queries `crm_note` directly via `db.conn`, asserts `party_id`/`author_user_id`/`note_type`/`visibility`/body text)
  - `test_ok_with_invalid_reason_still_unclaims_but_writes_no_note`
  - `TestWorklistUnclaimRoute` (5 tests: 401, 422×2, 403, 200) — route-layer HTTP mapping via `TestClient` + a test-only `_InjectUserMiddleware` standing in for `CFAccessMiddleware`
  - `TestC360UnclaimRoute` (4 tests: 401, 422, 403, 200) — same shape for the C360 handler, confirms no duplicated authorization logic (both routes just map `TaskService`'s string result)
- Integration/full suite: **1133 passed, 1 skipped, 0 failed** (was 1119 passed/1 skipped before this phase's new test file; +14 new, 0 regressions).

## Issues Encountered

- Session was interrupted mid-run once (process restart); all file edits had already landed on disk and were verified intact via `git diff --stat` before continuing — no rework needed.
- Phase file's Related Code Files section said "8" broken test call sites across 5 files; re-grepping per its own instruction ("verify this list is still exhaustive... re-check for drift") found 9 sites in the same 5 files (`test_task_claim_action_types_snapshot.py` has 4, not fewer). Used the grep-verified count, not the stale "8".
- No conflicts with Phase 1 (`authorization_service.py`, `composition.py`'s `authz` key) or Phase 4 (`screen_tasks_board.py`, `screen_modal_shared.py`, `modal_m05_create_task.html`) — neither touched by this phase's edits; `composition.py`'s Phase-1-authored `"authz": AuthorizationService()` line was refactored into a named `authz_svc` variable reused by both the `TaskService(...)` wiring and the `"authz"` dict key (same single instance, not duplicated).

## Next Steps

- None blocking. Manual UI verification (step 11 in the phase file — unclaim button disabled-until-reason-selected, 403/401 behavior visible in the actual worklist/C360 screens) was not performed since this was a backend-focused test pass; recommend a quick click-through before considering this fully done end-to-end, though all server-side behavior is now test-covered.

## Unresolved Questions

- None.

Status: DONE
Summary: TaskService.unclaim_customer_actions now enforces a fail-closed ownership guard + writes an audit note via NoteService; both route handlers (worklist + C360) map 401/422/403 correctly; 9 test call sites fixed + 14 new dedicated tests added; full suite green (1133 passed, 1 skipped, 0 failed).
Concerns/Blockers: None — manual UI click-through of the new reason-picker (step 11 in the phase file) not performed, recommend a quick pass before shipping to users.
