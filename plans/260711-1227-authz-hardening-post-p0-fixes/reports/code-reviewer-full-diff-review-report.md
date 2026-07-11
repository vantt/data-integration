# Code Review — Authz Hardening + Post-P0 Fixes (full uncommitted diff)

Reviewed against `plan.md` + all 5 phase files + all 5 implementation reports, verified against the actual `git diff` (27 files, +647/-70) from `D:\Vantt\app\data-integration`. Full CRM suite executed live in the `crm` container: **1152 passed, 1 skipped, 0 failed**.

## Overall Assessment

This is a well-executed hardening pass. All 12 red-team findings from the plan's own review round are genuinely fixed in the landed code, not just claimed — I re-derived each one from the diff rather than trusting the phase reports. The most safety-critical claim (fail-closed unclaim guard) checks out exactly as specified. No blocking issues found. A few minor/informational notes below.

## Critical Issues

None found. Specifically, the one claim this review was told to scrutinize hardest — the fail-open bug — is **correctly fixed**:

`crm/src/application/task_service.py::unclaim_customer_actions`:
```python
if not actor_id or not self._authz.is_owner(existing.assignee_user_id, actor_id):
    return "forbidden"
```
This is the fail-closed shape (`not actor_id or ...`), not the fail-open shape (`actor_id and not ...`) that the red-team review caught in an earlier revision. Verified in the actual landed file, not the phase spec. Belt-and-suspenders 401 also present at both route layers (`screen_worklist.py`, `screen_customer_360_panels.py`) before the service is ever called.

## High Priority

None.

## Medium Priority

None blocking. Two informational notes:

1. **Manual UI click-through not performed (Phase 2)** — accurately self-disclosed in `phase-02-implementation-report.md`'s Concerns/Blockers ("manual UI click-through of the new reason-picker not performed"). All server-side behavior (401/422/403/200, audit-note persistence) is test-covered with real DB assertions, so this is a UI-polish residual risk (disabled-until-selected `<select>`/button wiring in `_wl_row.html`/`c360_insight_panel.html`), not an authz gap. Recommend a quick click-through before this reaches users, as the report itself suggests. Not more severe than described.
2. **Pre-existing missing-template bug flagged, not fixed (Phase 4)** — `GET /tasks/modal/create` renders `fragments/modal_create_task.html`, confirmed absent from disk (only `modal_m05_create_task.html` exists). S07 Tasks Board's own "+ Tạo task" buttons hit this dead route today. Correctly out of this phase's scope per the plan's explicit hold-scope decision; correctly flagged (not silently rediscovered) in the implementation report. Pre-existing, not introduced by this diff.

## Low Priority

- `.claude/settings.local.json` gained one unrelated Bash permission-pattern entry (`xargs -I{} sh -c '...grep...'`). Harmless local tooling config, unrelated to this plan's scope — flagging only for scope-drift hygiene, not a defect.
- `crm/docs/ui-spec/panels/P01-insight-panel.md` shows as modified in `git status` but produces an empty `git diff` (line-ending/whitespace noise only, likely a pre-existing CRLF/LF normalization artifact unrelated to this session's edits). No content change — not a concern.

## Verification Against Explicit Review Checks

**(a) Success Criteria spot-check** — read the actual code (not just reports) for all 5 phases' checklists. All criteria met:
- Phase 1: `AuthorizationService` matches the Architecture section verbatim, zero adapter imports (only `__future__`/`typing`), wired once in `composition.py`.
- Phase 2: fail-closed guard verified above; `NoteService.add_note(...)` called with correct kwargs signature (verified against `note_service.py:30-56`); `TaskClaimWriter` Protocol updated to `-> str`; all 9 broken `TaskService(...)` test call sites fixed (grep-verified count of 9, matching the phase-02 report's own re-grep correction from the stale "8").
- Phase 3: both `execute_side_effects()` step 6 (`complete_task_ids`) and step 7 (`resolve_actions_and_tasks`) independently guarded and independently tested; `screen_customer_360_tasks.py`'s 3 handlers (`done`/`cancel`/`postpone`) all resolve-then-check before mutating, all return 403 on mismatch, all covered by dedicated tests including an unresolvable-id fail-closed case.
- Phase 4: `parse_priority("P3") == 0` confirmed (`PRIO_STR_TO_INT = {"P1": 2, "P2": 1, "P3": 0, "P4": 0}`), so the default-priority regression claim holds. `return_to`-aware response mirrors the M05 pattern.
- Phase 5: 8 new tests for `post_task`/`patch_task_edit` `return_to` behavior, asserting actual header values (not just presence).

**(b) No regressions at touchpoints:**
- Unclaim guard shape: confirmed fail-closed (see Critical Issues above).
- Audit note write goes through `NoteService.add_note(party_id, body, author_user_id=..., note_type="unclaim_reason", visibility="team")` — the real service, not `NoteRepository` — confirmed in both the production code and a dedicated test that queries `crm_note` directly (`test_ok_persists_audit_note_with_correct_fields`).
- `resolve_actions_and_tasks` step 7 AND `execute_side_effects` step 6 both guard against cross-party ids — confirmed in `activity_side_effects.py` diff, each with its own dedicated skip/isolation/fail-closed tests (`TestSideEffectsIdorGuard`, `TestBulkResolveIdorGuard`).
- `screen_customer_360_tasks.py`'s 3 handlers (done/cancel/postpone) all reject cross-party `task_id` with 403 before mutating — confirmed by reading the file directly; `get_task` is called and checked in every handler before `transition_status`/`update_task`.

**(c) No breaking changes to public contracts:**
- `TaskService.__init__` uses `*, authz, notes, db=None, party_repo=None` — genuinely keyword-only, confirmed by reading the signature. Every production and test call site passes both by keyword.
- `resolve_actions_and_tasks`/`bulk_resolve`'s new required params (`party_id`, `authz`) are threaded consistently through the entire call chain (`composition.py` → `make_customer_360_router` → `register_activity_routes`/`register_task_routes` → `execute_side_effects`/`bulk_resolve` → `resolve_actions_and_tasks`) — grep-verified exhaustive call-site coverage for `resolve_actions_and_tasks(`/`execute_side_effects(`/`bulk_resolve(`/`_bulk_resolve(` (5 files, all accounted for) and for `make_customer_360_router(`/`register_activity_routes(`/`register_task_routes(` (all production call sites pass `authz`; the 3 extra files in the grep hit were docstring mentions only, not calls). No silent-default reintroduction of the vulnerability found anywhere.

**(d) Follows existing patterns:**
- `AuthorizationService` is pure logic — confirmed zero adapter/IO imports (`__future__`, `typing.Optional` only).
- Grep for `AuthorizationService(` across `crm/src` confirms construction occurs in exactly one production file (`composition.py:323`); every other match is in a test file, which the plan explicitly designated as acceptable (real instances in pure-logic tests, or `MagicMock(spec=AuthorizationService)` stand-ins for tests not exercising the guard itself). No stray production bypass found.

**(e) No new lint/type/build tooling gaps:**
- Confirmed no `pyproject.toml`/`mypy.ini`/`.flake8`/`setup.cfg` exists anywhere under `crm/` — the reports' claim of "no dedicated typecheck step beyond pytest" is accurate, not assumed.

**(f) Test quality:**
- Audit-note test queries `crm_note` via a real SQLite connection and asserts `party_id`/`author_user_id`/`note_type`/`visibility`/body content — not an HTTP-status-only tautology.
- Unauthenticated-unclaim test (`test_forbidden_when_actor_id_is_empty`) is a dedicated test distinct from the ownership-mismatch test, covering both `""` and `None` — exactly the fail-open regression case, verified to assert on claim-state-unchanged AND note-absence, not just the return value.
- Cross-party IDOR tests (both bulk-resolve and the 2nd IDOR site) assert on mock `.assert_called_once_with(...)`/`.assert_not_called()` for the underlying mutation call — genuine behavioral proof, not shallow status-code checks. Per-item isolation (valid id in the same batch as an invalid one) is explicitly tested for both dismiss and snooze paths.
- Ran the full suite live (not trusting reports): `1152 passed, 1 skipped, 0 failed`, matching Phase 3's report (the highest-numbered, most current full-suite count). The transient failure mentioned in the Phase 1/4/5 reports (`test_tasks_board_no_party_create.py`, `AttributeError: 'Form' object has no attribute 'strip'`) is **not present** in the current tree — re-ran that file in isolation (7/7 passed) and the full suite (0 failures); this was correctly self-diagnosed by the agents as a mid-session concurrent-edit artifact, not a landed defect.

## Residual Risks (as characterized in the plan's own Risk Assessment sections)

- Phase 2: manual UI click-through not performed — accurately characterized as a UI-polish gap, not an authz gap (server-side behavior fully test-covered). Not silently more severe.
- Phase 3: `resolve_party_id`'s cache-join dependency on warehouse cache freshness (a previously-valid action rotating out of `wh_action_queue` before the resolve request arrives) — inherited from `dismiss()`'s existing tolerance, not a new failure mode. Not independently re-verified in this review (would require live warehouse-cache staleness reproduction), but correctly scoped as a known, pre-existing, non-worsened risk in the plan.
- Phase 4: missing `modal_create_task.html` template — pre-existing dead code, correctly flagged not fixed, correctly out of scope.

## Recommended Actions

1. None blocking. Optional: perform the Phase 2 manual UI click-through (disabled-until-reason-selected button behavior) before this reaches end users — purely a UI-polish verification, not a security gap.
2. Optional: decide on the flagged dead `GET /tasks/modal/create` route (separate ticket, not part of this plan's scope).

## Metrics

- Files changed: 27 (+647/-70), plus 5 new test files and 1 new production file (`authorization_service.py`).
- Full CRM suite: 1152 passed, 1 skipped, 0 failed (live run, not trusted from reports).
- New dedicated security tests: 14 (Phase 2 unclaim) + 9 (Phase 3 2nd IDOR site) + 5 (Phase 3 bulk-resolve IDOR) + 4 (Phase 3 side-effects IDOR) + 3 (Phase 3 resolve_party_id repo) = 35 new tests directly proving the fixed vulnerabilities, plus 8 (Phase 5) + 7 (Phase 4) regression/coverage tests.
- Lint/type config in `crm/`: none exists (confirmed, not assumed).

## Unresolved Questions

None.
