# Parallel `/ck:cook` Session: Multi-Round CRM Validation Bugs + DBT Schema Wiring Mismatch + Subagent Recovery

**Date**: 2026-07-11 14:30  
**Severity**: High (both tracks blocked by bugs; caught and fixed in same session)  
**Component**: `crm/src/application/activity_service.py`, `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`, `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.sql`  
**Status**: Resolved; all 1052 tests passing, 1 skip (documented)

## What Happened

Ran `/ck:cook --auto --parallel` on remaining phases of two independent plans with disjoint file ownership:

1. **`plans/260710-1338-activity-log-disposition-api/`** (Phase 3): Replaced static `outcome_bar` with a 4-state T0–T3 disposition-strip state machine, wiring directly to the draft/PATCH/finalize API from Phase 2 via `fetch()`.
2. **`plans/260709-1638-crm-outreach-effort-report/`** (Phases 2–3): New dbt intermediate model (`int_crm_outreach_effort_events`) to measure outreach effort by action_type, plus weekly mart (`mart_crm_outreach_effort_by_action_weekly`).

Both tracks were spawned as parallel background subagents. **Midway through the session, the harness process restarted and both agents showed as "stopped."** Resumed both successfully via `SendMessage` using their saved transcripts — no work lost, no repeated effort.

## The Brutal Truth

The frustration here is multi-layered:

1. **Subagent recovery worked but was not expected.** I assumed "stopped" meant data loss or need to restart from scratch. Instead, the framework's transcript persistence meant we could resume both agents mid-work and they picked up exactly where they left off, re-reading context from the chat history. This is good design, but it's not obvious until you see it fail and recover.

2. **The CRM track was 100% green on tests throughout development, but the disposition strip's core "refused" outcome path was completely broken end-to-end in production.** Pytest passed because no test exercised the actual two-call sequence: PATCH outcome first (before reason is known), then PATCH reason second. The validation check fired on call #1 and silently failed. The error was then swallowed by a `fetch().catch()` block that only caught network errors, not HTTP status codes. A user clicking "Từ chối" on the real UI would see no error, no state change, no indication that something broke. This is the exact kind of silent failure that kills trust in a UI.

3. **The second CRM review (independent re-verification, not the same agent) found that our fix to round #1 had created a new security hole:** the M08 "edit an already-finalized activity" path has no future `finalize_activity` call to enforce validation. After the fix, you could PATCH a final activity to `refused` without a reason and it would be accepted. Pytest was still green because the tests that touched M08 all submit both fields together in one form POST, never testing the PATCH-alone path. We caught it in review, not in automation.

4. **The DBT track was less dramatic but equally illustrative of subtle wiring errors:** the spec said "staff_user_id should come from crm_task.assignee_user_id," but the implementation wired it from the linked activity's staff_user_id instead. For most tasks, the most-recent activity has no staff recorded (NULL), so the column was ~all NULL across 37 rows despite being the "key dimension" for the entire mart. A second independent review caught this because they traced the data lineage backward from the mart to the source, found the NULL pattern, and asked "is this right?" It wasn't. The fix was 1 line. The .yml doc for the model even said the right thing while the SQL did the wrong thing — a classic case of prose + code drift.

5. **Plan status sync (final gate before shipping) surfaced 2 "ownership gaps" that no phase in either plan actually owns:**
   - `zalo_connected_count` column was never added to `mart_staff_performance_weekly` despite UI + export both being ready. The dashboard that depends on it will go live missing this KPI.
   - `crm_party_tag.source_activity_id` write-path has been ready since Phase 1, but no CRM form actually wires it. The column will stay NULL forever until someone (not assigned in either plan) makes that UI connection.

## Technical Details

### CRM Disposition Strip: Round 1 Bug

**Error sequence:**
- User clicks outcome pill "🚫 Từ chối" (refused)
- JS calls `patchDraft()` → `PATCH /api/activities/{id}` with `{ contact_outcome: 'refused' }`
- Server's `patch_activity` method checks `if next_outcome in REASON_REQUIRED_OUTCOMES and not next_reason: raise ValueError`
- Raises 422 immediately (reason is still None on draft)
- PATCH reason call never executes (client-side error)
- `fetch().catch()` only catches network errors, not 4xx responses → error silently swallowed
- User sees: nothing. Activity unchanged. Workflow stuck.

**Root:** Validation intended for `finalize_activity` (the actual commit point) was incorrectly placed in `patch_activity`, which is called on intermediate steps. With the new state machine, outcome and reason are picked in separate PATCH calls.

**Root of the root:** Early test suite all passed because `test_outcome_reason_enum.py`, `test_bulk_resolve_endpoint.py`, etc. never tested the real two-step PATCH sequence. M08 form always POSTs both fields together, so the workaround path wasn't covered by tests.

### CRM Disposition Strip: Round 2 Bug (Fix Regression)

The fix for Round 1 was to relocate both checks to `finalize_activity`. But during independent re-verification, the reviewer asked: "What about M08 `edit_activity` mode on a row that's already FINAL?"

**Error sequence (after Round 1 fix):**
- User edits a completed activity in M08 modal
- Calls `patch_activity(is_edit_mode=True)` with `contact_outcome='refused'`, `outcome_reason=None`
- Since row is final, `finalize_activity` is never called (no future commit point)
- The check that now lives only in `finalize_activity` never runs
- Server accepts the invalid state silently
- Data corrupted undetected

**Root:** Relocating validation only to the "future commit point" works for the strip's draft workflow, but breaks the M08 edit-final workflow which has no such future point.

**Fix (Round 2):** Created two helper functions `_reason_required_violation()` and `_irritation_body_violation()`, called by both `patch_activity` (only when `activity.status == FINAL`) and `finalize_activity`. Draft PATCH calls skip these checks (guard passes), final-activity PATCH calls enforce them. DRY + safe.

### DBT Outreach Effort: Schema Wiring Mismatch

**Error sequence:**
- Phase 2 spec: "staff_user_id should equal crm_task.assignee_user_id (the person who claimed the task)"
- Phase 2 implementation: `SELECT ... st.staff_user_id FROM stg_crm__task st JOIN stg_crm__activity_log al ON ...`
- But which `staff_user_id`? Turned out the code joined activity, not task: `al.staff_user_id`
- Activity's staff is typically NULL (activity log doesn't track who called by default)
- Result: 37 rows, ~37 NULLs for the key dimension
- `.yml` doc correctly stated "should be crm_task.assignee_user_id", but the SQL did the opposite

**Root:** Review traced the NULL pattern backwards to the source. Spec + code drift went unnoticed by both implementation and initial test runs because dbt tests don't validate against business semantics — they only check `not_null(task_id)` and `unique_combination_of_columns(task_id, action_type)`, both of which passed even with staff_user_id NULL.

## What We Tried

### Fixing CRM Round 1 (refused-outcome PATCH)
- **First attempt:** Move the check from `patch_activity` to `finalize_activity` only. This worked for the strip's 2-step flow (PATCH outcome, PATCH reason, finalize) but broke M08's edit-on-final-activity case (patch without finalize). Tests for the strip passed. Tests for M08 also passed (they submit both fields together). The edge case only surfaced in review.

- **Second attempt (Round 2):** Extract check logic into helpers, call them conditionally:
  - `patch_activity`: check only if `activity.status == FINAL` (edit-mode on completed)
  - `finalize_activity`: always check (draft becoming final)
  - Result: Draft workflow skips early validation (correct), final edit enforces validation (correct).

### Fixing DBT Schema Wiring
- Traced the query backward from mart to source
- Found the NULL pattern in the 37 rows
- Checked the .yml to see what was intended
- Compared intended vs. actual join
- Changed from `al.staff_user_id` to `st.assignee_user_id`
- Re-ran `dbt test` and `dbt run` — all pass, no more NULLs for the 37 rows where data exists

## Root Cause Analysis

**CRM Round 1 & 2 (Multi-Round Validation Bug):**

1. **Semantic mismatch between API design and validation placement:** The draft/PATCH/finalize contract (from Phase 2) was designed to allow intermediate steps without full validation. The validation logic was written for a different workflow (single-submit-to-finalize). Nobody caught this until real UI interaction testing.

2. **Test coverage gap:** The test suite verified individual methods (`test_patch_activity`, `test_finalize_activity`) but not the *sequence* (PATCH twice, then finalize) that the UI actually performs. Pytest's per-file isolation made this invisible.

3. **Silent error swallowing in client code:** `fetch().catch()` in JS is a trap. Network errors get caught; HTTP 4xx doesn't. We caught it on the second bug (added `r.ok` check), but the pattern existed in the codebase elsewhere.

4. **Round 2 discovery:** The edge case (edit final activity) is a different path from the happy path (draft strip) and only appeared in review because the reviewer asked "what about the other caller?" — not a failure of the original implementation, but a failure of review checklist coverage (should have asked: "what are ALL callers of patch_activity and finalize_activity?").

**DBT Schema Wiring:**

1. **Prose + code drift:** The .yml schema doc clearly stated the intended source (`crm_task.assignee_user_id`), but the SQL used a different source. Both existed in the same PR; they just didn't sync.

2. **Test-driven development assumption:** Tests verified the model had the right grain and keys. They didn't test "is this dimension semantically correct?" — that's a business-logic question, not an automated-check question. Required human review of the data lineage.

3. **NULL mass-production:** Wiring a dimension to an always-NULL column doesn't *fail* in SQL; it quietly produces 100% NULLs. No error, no warning, perfect data shape, entirely useless. Caught only because the reviewer said "37 rows, 37 NULLs, is that right?" and traced backward.

## Lessons Learned

1. **State-machine APIs require sequence testing, not just unit testing.** The draft/PATCH/finalize contract is a sequence. Write tests that exercise `[PATCH outcome] → [PATCH reason] → [finalize]`, not just individual methods. This sequence-level test would have caught Round 1 immediately.

2. **Caller analysis is a review checklist item.** When moving or refactoring validation, enumerate all callers and verify each one's behavior. For `patch_activity`, we had 3 callers: (a) strip's 2-step PATCH, (b) M08's 1-step PATCH+finalize, (c) bulk quick-outcomes PATCH. The review should have explicitly asked: "Does the fix work for all 3?"

3. **HTTP error handling in JS: always check `r.ok`.** `fetch().catch()` is for network failures. `r.ok` is for application-level failures (4xx, 5xx). We learned this twice (once per bug discovery) and now have a pattern in the codebase. Could have been a linter rule.

4. **Data lineage review beats correctness tests.** Dbt's `not_null()` test would have failed if staff_user_id was expected to have values and didn't. But the test was written as "ensure this column exists and is part of the unique key" — not "ensure this dimension is semantically meaningful." A manual trace of 3 rows backward from mart → intermediate → staging → export → source table would have caught the wiring bug immediately.

5. **Prose documentation can diverge from code silently.** The .yml schema said one thing, the SQL did another. No linter caught the drift. In code review, docs go by fast. Proposal: add a check to dbt-parse that reports when a model doc describes a join that doesn't exist in the SQL, or describes a column source that contradicts the query.

6. **Subagent recovery is real.** When two background agents stopped mid-session, I expected data loss. The framework's transcript persistence meant they resumed cleanly. This is not just convenient; it's a lesson in how to architect multi-agent coordination — save context, allow resumption, don't require re-setup.

## Next Steps

1. ✅ Fixed CRM Round 1 (relocate validation to finalize) + Round 2 (re-add check for FINAL edits via helpers).
2. ✅ Fixed DBT staff_user_id wiring (task.assignee_user_id instead of activity.staff_user_id).
3. ✅ Full test suite 1052 passed / 1 skipped / 0 failed (1031 baseline + 21 new tests across both tracks).
4. ✅ Container restart + healthz OK.
5. 🔴 **Open gaps flagged in plan sync (noop for this session, blockers for next phase):**
   - `zalo_connected_count` column needs addition to `mart_staff_performance_weekly` — UI/export ready, no phase owned this. Needed for Sprint Gọi Ra KPI dashboard.
   - `crm_party_tag.source_activity_id` write-path ready (Phase 1 migration 0044), but no CRM form wires it — column will be NULL in production. Phase-01 report flagged "Handoff wiring" as pending, still not claimed by anyone. 2 UI paths proposed in report; neither is scoped here.
6. ✅ Both plans sync'd back to plan.md with final status + unresolved questions listed.

## Commits

- `260710-1338` Phase 3: `c360_call_cockpit_panel.html`, `activity_service.py` (find_open_draft), `screen_call_cockpit.py`, disposition-strip v2 template + CSS + spec S14 update, 1046 tests.
- `260710-1338` Phase 3 Round 1 Fix: Relocate reason/body-required validation to finalize_activity, add `r.ok` check in patchDraft(), 3 new regression tests.
- `260710-1338` Phase 3 Round 2 Fix: Add back validation for FINAL-activity PATCH via helper functions, 3 new audit tests.
- `260709-1638` Phase 2: `int_crm_outreach_effort_events.sql` + `.yml`, JSON explode logic, customer bridge, channel field selection.
- `260709-1638` Phase 2 Fix: Correct staff_user_id from `al.staff_user_id` to `st.assignee_user_id`.
- `260709-1638` Phase 3: `mart_crm_outreach_effort_by_action_weekly.sql` + `.yml`, simplified now that staff_user_id is correctly sourced.

All committed, ready for review + deploy decision.

---

**Session notes:**
- No manual test on browser (agent environment limitation) — manual test script provided in phase-03 report for QA.
- Subagent recovery via SendMessage saved significant rework; both agents resumed context cleanly.
- Final verification: Serving views bootstrap pending (separate task); blueprints deployment follows once serving confirmed.
