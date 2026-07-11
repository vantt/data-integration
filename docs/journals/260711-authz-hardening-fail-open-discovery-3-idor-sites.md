# Authorization Hardening: Fail-Open Guard + 3-Site IDOR Discovery + Subagent Recovery Pattern

**Date**: 2026-07-11 15:30  
**Severity**: High (real security bugs discovered and fixed; fail-open guard was shipping)  
**Component**: `crm/src/application/authorization_service.py`, `crm/src/adapters/inbound/web/screen_tasks_board.py`, `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_tasks.py`, `crm/src/application/task_service.py`  
**Status**: Resolved; phases 1–5 completed, all 1152 tests passing (1 skipped), landed in commit `f502e3ba`

## What Happened

Executed a 5-phase security-hardening plan (`plans/260711-1227-authz-hardening-post-p0-fixes/`) via `/ck:cook --auto` with phased and parallel subagent orchestration:

1. **Phase 1**: New `AuthorizationService` class (pure application layer, zero IO, single shared instance in `composition.py`).
2. **Phase 2**: Fixed unclaim ownership guard + audit trail wiring (discovered fail-open condition + NoteService mapping bug).
3. **Phase 3**: Found and fixed 3 separate IDOR vulnerabilities across two code paths (red-team review caught 2 beyond original scope).
4. **Phase 4**: Fixed no-party task creation 404 (`/customers//tasks` → `/tasks` endpoint routing).
5. **Phase 5**: Added regression tests for M05 `return_to` behavior.

**Process recovery:** Midway through execution, the harness process interrupted. Phase 2 (a sequential dependency for Phase 3) showed as "stopped" on the agent dashboard. Instead of restarting from scratch, I `SendMessage`'d the same agentId with context: it resumed from its saved transcript, re-read the partial diff on disk, and completed cleanly. Zero work lost, zero repeated effort. Worth capturing as a pattern for future session interruptions during long-running subagent orchestration.

## The Brutal Truth

This is frustrating in three layers:

1. **The fail-open guard almost shipped.** The original ownership check was written as `if actor_id and not is_owner(actor_id, ...)`, intended to prevent staff from unclaiming tasks they didn't own. But in this app's LAN-trust deployment mode (no CF Access intercept → `actor_id` is always empty string or None), the entire guard was silent-fail-open. Every unclaim succeeded regardless of who asked. This is not a theoretical vulnerability — real users could have unclaimed each other's work. The test suite passed because tests set `actor_id` explicitly (contrary to production reality); the bug only surfaced during red-team review when someone asked "what if actor_id is missing?"

2. **The audit trail had a silent wiring bug.** Phase 2 was supposed to write an audit note when unclaim succeeded. The code was wired to `NoteRepository` (raw data-layer) instead of `NoteService` (the application-layer API). This would have raised a `TypeError` at runtime (methods don't exist on the raw repo). But the exception would have been swallowed by the encompassing try/finally block, resulting in no error message and no audit trail being written. Silent data loss. Only discovered during code review when the reviewer checked the wiring.

3. **Red-team review found 2 MORE IDOR instances beyond the originally-scoped fix.** Phase 3 was intended to fix `resolve_actions_and_tasks()` — client-supplied action ids with no ownership check. The reviewer asked "are there other places we bulk-update items by client-supplied ids?" Found: (a) `execute_side_effects()`'s `complete_task_ids` loop 10 lines away in the same file (same vulnerability class), and (b) `screen_customer_360_tasks.py`'s `done`/`cancel`/`postpone` handlers (a live IDOR on task_id visible across the app with zero cross-party check). All 3 now verify ownership via `AuthorizationService.is_same_party()`, threaded explicitly through the full call chain. But the fact that 2 identical bugs were sitting 10 lines from the first fix, *and a third in a different file*, suggests the codebase had never been swept for this vulnerability class.

## Technical Details

### Phase 2: Fail-Open Guard

**Original (broken) code:**
```python
def unclaim_task(actor_id: UUID, task_id: UUID, reason: str) -> Task:
    task = task_repo.get(task_id)
    if actor_id and not is_owner(actor_id, task.party_id):
        raise Unauthorized("You do not own this task")
    # ... proceed with unclaim
```

**Problem:** In LAN-trust deployment, `actor_id` comes from the request context. When no authorization header is present (the default in LAN), `actor_id` is None or empty. The condition `if actor_id and ...` short-circuits to False, guard never fires, unclaim proceeds.

**Production consequence:** Any staff member could POST `/tasks/{id}/unclaim` and succeed, regardless of party assignment.

**Test consequence:** All tests explicitly set `actor_id` in the context, hiding the real production behavior. Green tests + red production.

**Fix (fail-closed):**
```python
if not actor_id or not is_owner(actor_id, task.party_id):
    raise Unauthorized("You do not own this task or no authorization context")
```

Now: if `actor_id` is missing, the guard fires. Explicit fail-closed.

### Phase 2: Audit Trail Wiring

**Original code:**
```python
def unclaim_task(actor_id: UUID, task_id: UUID, reason: str) -> Task:
    # ... guard check (now fixed)
    task = task_repo.get(task_id)
    task.status = TaskStatus.OPEN
    task.assignee_id = None
    try:
        task_repo.save(task)
        note_repo.create(Note(task_id=task_id, text=f"Unclaimed: {reason}"))  # BUG
    finally:
        return task
```

**Problem:** `note_repo.create()` is a low-level data method. The application expects `NoteService.create_activity_note()` (which does timestamps, user attribution, and audit enrichment). The mismatch would have caused a `TypeError` at runtime (NoteRepository has no such attribute), but the `finally` block would have swallowed it and returned the task as though the note was written. Silent audit loss.

**Fix:** Wire to the correct service layer:
```python
note_service.create_activity_note(
    task_id=task_id,
    text=f"Trả việc: {reason}",
    activity_type="task_unclaim"
)
```

### Phase 3: 3-Site IDOR Vulnerabilities

**Site 1: `resolve_actions_and_tasks()`**

```python
def resolve_actions_and_tasks(customer_id: UUID, action_ids: list[UUID], task_ids: list[UUID]):
    for aid in action_ids:
        action = action_repo.get(aid)
        action.status = DISMISSED  # BUG: no ownership check
        action_repo.save(action)
```

**Problem:** action_id comes from client request. No verification that the action belongs to the customer. Staff from Party A could dismiss actions for Party B.

**Fix:** Thread `party_id` from composition and check:
```python
for aid in action_ids:
    action = action_repo.get(aid)
    if not authz_service.is_same_party(party_id, action.party_id):
        raise Unauthorized(f"Action {aid} not in party {party_id}")
    action.status = DISMISSED
    action_repo.save(action)
```

**Site 2: `execute_side_effects()` in the same file**

```python
def execute_side_effects(customer_id: UUID, complete_task_ids: list[UUID]):
    for tid in complete_task_ids:
        task = task_repo.get(tid)
        task.status = COMPLETED  # BUG: no ownership check
        task_repo.save(task)
```

**Identical vulnerability**, same file, 10 lines from Site 1. Fixed with same pattern.

**Site 3: `screen_customer_360_tasks.py` handlers**

```python
@post("/done")
def mark_task_done(self, task_id: UUID):
    task = task_repo.get(task_id)
    task.status = DONE
    task_repo.save(task)
```

**Problem:** task_id is visible and guessable across the app. No cross-party check in the handler. Staff viewing customer A's 360 can POST to mark tasks from customer B as done.

**Fix:** Extract party_id from context and verify:
```python
@post("/done")
def mark_task_done(self, task_id: UUID):
    task = task_repo.get(task_id)
    if not self.authz_service.is_same_party(self.current_party_id, task.party_id):
        raise Unauthorized(f"Task {task_id} not in party {self.current_party_id}")
    task.status = DONE
    task_repo.save(task)
```

### Phase 4: No-Party Task Creation

Worklist header "+ Tạo task" button POST'd to `/customers//tasks` (empty party_id segment). Route didn't match any handler, returned 404. Routed to existing `/tasks` endpoint instead, extended to accept M05's full field set + `return_to` semantics.

### Phase 5: M05 Test Coverage

Added regression tests for `return_to=stay` behavior (had shipped with manual-verify checklist only, no automation).

## What We Tried

1. **Phase 1:** Designed `AuthorizationService` as a pure stateless class (zero IO, zero adapter deps). Tested in isolation. Wired as singleton in `composition.py` to avoid repeated instantiation and hidden dependencies. Pattern proven stable.

2. **Phase 2:** First iteration of unclaim guard was fail-open (the bug). Discovered during review when reviewer asked "what if actor_id is missing?" Re-read the LAN-trust architecture decision and flipped the guard logic. NoteRepository wiring traced through the service layer and corrected to use NoteService. Added 3 regression tests covering: (a) unclaim with reason audit, (b) unclaim by non-owner raises, (c) actor_id missing raises.

3. **Phase 3:** Implemented the scoped IDOR fix for `resolve_actions_and_tasks()`. Red-team review asked "are there other similar paths?" Swept the codebase for client-supplied id patterns. Found 2 more. Applied the same fix to all 3. Verified each fix in context by tracing the call chain from the HTTP handler through composition to the service call.

4. **Phase 4 & 5:** Phase 4 was straightforward routing. Phase 5 added test coverage for the M05 modal's `return_to` behavior (was modal-only, now testable via M05 creation endpoint).

5. **Subagent recovery:** When harness interrupted mid-Phase 2, I checked the agent's status (showed "stopped", no error). Instead of restarting the entire phase (which would have re-read files, re-run the work), I sent a message to the same agent ID with the context: "resume from your saved transcript." It picked up the partial work (file edits on disk were intact), re-read the diff, and finished the remaining steps. Clean pattern for future session interruptions.

## Root Cause Analysis

**Fail-Open Guard:**

1. **Deployment-mode blind spot.** The guard was written for internet-facing services (where authorization headers are always present). The CRM deployment is LAN-trust (no CF Access by design). Tests assume internet-facing semantics. Nobody connected the dots until red-team review explicitly asked "what is actor_id in real deployment?"

2. **Test/production parity failure.** Tests set `actor_id` explicitly, hiding the real behavior. The bug only appeared in mental modeling during review, not in test execution.

**Audit Trail Wiring:**

Repository/Service layer confusion. The original code used the raw data layer, not the application layer. No compile-time error (duck typing in Python). No test failure (no test exercised the `note_repo.create()` call). Only surfaced in code review when the reviewer traced the call path.

**3-Site IDOR:**

1. **Vulnerability class not recognized at implementation time.** The original IDOR fix was scoped to one method. The identical vulnerability class exists elsewhere in the codebase. Standard pattern: (a) find a vuln, (b) fix it in place, (c) never check if it's local or systemic. This time, red-team review did step (c).

2. **Composition didn't thread party_id explicitly.** Some handlers accepted `customer_id` and derived party_id from it; others didn't. Inconsistent patterns made it easy to miss the guard. Now, `party_id` is threaded explicitly from the composition root and passed to every authorization check.

**No-Party Task Creation:**

Route wildcard mismatch. Simple routing oversight; the worklist button assumed a `/customers/{party_id}/tasks` handler existed. Didn't. Fallback was clear once found.

## Lessons Learned

1. **LAN-trust deployments have different guard semantics than internet-facing.** A guard that says "if auth_context is present and check fails, deny" works when auth_context is always present. In LAN-trust, it's optional. Flip to fail-closed: "if auth_context is missing OR check fails, deny." Document this in the guard's docstring and in the deployment architecture.

2. **Authorization must be threaded explicitly from composition, not reconstructed ad-hoc.** If party_id is derived by the handler, it's easy to miss. If it's passed down from the single composition root, every caller has it. Explicit threading also makes the call chain visible (code review can trace it).

3. **Vulnerability classes are patterns, not one-offs.** Finding an IDOR in one method should trigger a sweep for "client-supplied ids used in data mutations without ownership checks" across the codebase. Red-team review did this; ship-it reviews typically don't. Proposal: add a vulnerability-class checklist to the code review template.

4. **Prose documentation (docstrings) and implementation must sync.** The Phase 2 fix was correct in concept, but the wiring was wrong. A docstring would have clarified "this should call NoteService.create_activity_note(), not NoteRepository.create()." Proposal: for outbound calls (especially cross-service), document the expected layer in the docstring.

5. **Subagent recovery via transcript is a viable pattern.** When a long-running orchestrated task is interrupted, don't assume work is lost. If the agent saved context (transcripts), you can resume from that context and let the agent re-orient against the partial state on disk. This is effective for multi-hour sessions with interruptions.

6. **Tests set up preconditions that hide production reality.** Tests that set `actor_id` explicitly hide the fact that it's often missing in production. Proposal: add a "deployment-mode correctness" test that verifies guards fire when called with production-realistic parameters (missing headers, minimal context).

## Next Steps

1. ✅ Phase 1: AuthorizationService foundation (pure, stateless, single instance).
2. ✅ Phase 2: Unclaim guard fail-closed fix + NoteService wiring + audit tests.
3. ✅ Phase 3: 3-site IDOR fixes + party_id threading through composition + 9 regression tests.
4. ✅ Phase 4: No-party task creation rerouting + extended endpoint.
5. ✅ Phase 5: M05 return_to regression tests.
6. ✅ Full suite: 1152 passed, 1 skipped, 0 failed (verified twice, independently).
7. ✅ All 5 phases marked completed in `plan.md`.
8. 🔴 **Known residuals (documented, not blocking):**
   - M05 reason-picker UI click-through not performed (server-side fully test-covered; manual browser test pending in QA).
   - Pre-existing dead-code bug: `GET /tasks/modal/create` references a template that doesn't exist on disk. Out of scope for this plan (flagged for future fix-list, not a security issue).

## Commits

- `f502e3ba`: All 5 phases + red-team fixes landed in single commit (phases orchestrated in sequence/parallel, merged at end).
- Breakout: Phase 1 foundation, Phase 2 fail-closed + NoteService wiring, Phase 2 audit tests, Phase 3 IDOR sweep (3 sites), Phase 4 routing, Phase 5 test coverage.

---

**Session notes:**
- Subagent recovery pattern: harness interrupted → agent showed "stopped" → SendMessage to same agentId with context → agent resumed from transcript + on-disk state → zero work lost.
- Red-team review discipline: "are there other similar patterns?" caught 2 IDOR instances that implementation missed. Added to code review checklist.
- LAN-trust deployment context was not present in Phase 1 spec; discovered during Phase 2 review. Updated architecture doc to clarify fail-closed semantics for LAN deployments.
- Full CRM test suite independently run 2x outside implementing agents — both runs: 1152 passed, 1 skipped, 0 failed. Confidence: high.
