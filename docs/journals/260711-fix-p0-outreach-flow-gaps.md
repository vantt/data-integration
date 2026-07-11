# P0 CRM Outreach Flow: 4 Fixes Shipped; Orchestration Lesson on False Parallelism

**Date**: 2026-07-11 11:30  
**Severity**: Medium (P0 UX bugs; all fixed and verified before ship)  
**Component**: CRM cockpit/worklist modals + activity disposition + task assignment  
**Status**: Resolved; 1075 passed/1 skipped (12 new tests); code review 8/10 PASS

## What Happened

Ran `/ck:cook --auto --parallel` on 4 independent P0 fixes covering a tight worklist→call→log→callback loop (plan `260711-0933`). Shipped 718 lines added/152 removed across 14 files in 2 safe execution waves (not 1 parallel batch as the plan claimed).

**The 4 fixes:**

1. **M05/M08 modal `return_to=stay`** — Stop force-redirecting away from cockpit/worklist on save. Was unconditional `HX-Redirect`, breaking in-progress call state (cockpit timer reset, draft lost). Fix threads `return_to` param through GET query → form hidden field → POST response. Backward compatible (default `"redirect"` preserves old behavior).

2. **`execute_side_effects()` outcome-aware resolve** — When call outcome is `no_answer`/`busy`, snooze 2 days instead of dismiss (TTL 30d). The cockpit's own "+Nhắn Zalo" button was silently undoing this fix by completing the associated task; now the task snoozes too, closing the bypass.

3. **Auto-created callback/follow-up tasks missing `assignee_user_id`** — Tasks landed in shared queue instead of "của tôi" (claimed). Fix sets both `assignee_user_id` and `created_by` to the calling staff. Previously NULL; now functional.

4. **Call Cockpit JS broken for no-approach-script customers** — 6 functions (`s14TagMultiSave`, `s14ToggleReason`, etc.) + a stale-badge IIFE were gated inside `{% if script and ap %}` block, silently no-op'ing the "collect info" UI. Moved outside the gate. Also fixed unrelated `ReferenceError` where code referenced bare `S` instead of `window.S14_STRIP`.

## The Brutal Truth

The plan document itself claimed "4 điểm độc lập nhau (chạm file khác nhau)" (4 independent points touching different files). This was **false**. Actual file-touch mapping revealed:

- Phase 1 ↔ Phase 2 conflict: both touch `screen_customer_360_activity.py` (phase 2's amendment to `handle_resolve_async` + phase 1's `handle_patch_activity` changes)
- Phase 1 ↔ Phase 4 conflict: both touch `c360_call_cockpit_panel.html` (phase 1 adds URLs with `return_to=stay`, phase 4 reorganizes JS)
- Phase 2 ↔ Phase 3 conflict: both touch `activity_side_effects.py` (resolve vs. assignee)

Before spawning ANY agents, remapping revealed 3 real conflict pairs. Had to derive a safe 2-wave execution order: wave1={phase1, phase3} (no conflict), wave2={phase2, phase4} (blocks phase 1's amendment fix). A naive first pairing (wave1={phase1, phase2}) would have caused concurrent-edit collision.

**The frustration:** The plan's own parallelism claim was wrong, and this wasn't caught in initial review because the claim was stated as a given, not derived from actual code. A 5-minute grep of phase files BEFORE spawning agents would have caught it. Instead, I caught it mid-orchestration, had to halt and re-derive execution order.

## Technical Details

**Test progression:** 1063 passed/1 skipped → 1075 passed/1 skipped (12 new tests, 0 regressions).

**Code review score:** 8/10, PASS. 0 critical/high; 2 medium (not blocking):
1. `return_to=stay` branches in M05 create/edit lack pytest coverage (manual verification only).
2. Existing IDOR-shaped gap in `resolve_actions_and_tasks()` (no ownership check before dismiss by client-submitted ID) — documented, out of scope.

**Adversarial validation:** 5 key claims verified via code trace + grep + git log:
- resolve-async snooze gate only fires for `no_answer`/`busy` (confirmed in `activity_side_effects.py:202-210`)
- `source=manual` remains unchanged (not set by any phase; old dead code path left alone)
- `handle_patch_activity` PATCH response checks `return_to` only for edit-mode (confirmed; spec was initially vague)
- worklist header "+ Tạo task" pre-existing 404 (confirmed via git log --follow; not caused by phase 1)
- No cross-phase field collision (all 4 seams verified clean via diff review)

**Process bugs caught mid-session:**
1. Docs-manager subagent wrote report to malformed path (`plans/<dir>/plans/reports/...`). Caught and fixed manually.
2. Docs-manager's edit to `M08-log-activity-modal.md` fixed one stale claim (`resolve_action_ids` dismiss) but left sibling table row with same stale claim untouched. Caught by re-reading diff before commit.

## What We Tried

**Orchestration approach:** 
- Initial: trust plan's "4 independent" claim, spawn 4 agents in parallel.
- Caught conflict risk after first reading phase files: re-derived safe 2-wave order.
- Wave1 completed without issues; wave2 completed after wave1. Total wall-clock time longer than parallel, but zero conflict risk.

**Verification discipline:**
- Baseline test run before any code changes.
- Independent re-run by orchestrator (not just trusting agent self-reports).
- Code reviewer subagent ran standard review + adversarial validation (required for large diffs).
- All 3 checks converged on same numbers (no hidden failures).

## Root Cause Analysis

**False parallelism claim:** Plan author stated independence without verifying actual file-touch lists. The claim "4 phases touching different files" was not derived from grep; it was asserted as a given. Standard practice elsewhere in this codebase is to list file ownership per phase upfront, then compute conflict pairs. This plan skipped that step.

**Mid-session process errors:** 
1. Subagent paths — docs-manager inherited reporting template from a different project with different directory structure. First-pass template not validated against this project's naming rules.
2. Incomplete fixes — docs-manager's dbt yml edit was correct for one row but incomplete for a related row in the same table. Both rows had the same stale claim; partial fix left inconsistency.

## Lessons Learned

1. **Verify parallelism claims before agent spawning.** "Independent" is not a given; derive it by listing actual files per phase, then compute conflict matrix. 5 minutes of grep beats 30 minutes of conflict resolution.

2. **Re-run tests independently after parallel work.** Agents report their test results; don't trust aggregation. Orchestrator re-ran suite, caught no discrepancies, but the discipline matters.

3. **Plan amendments need the same rigor as original phases.** The 2 amendments (ported from red-team review of a different, broader plan) were correct technically, but they created new file conflicts that the plan's original structure didn't anticipate. Amendment risk matrix should be re-derived (conflict analysis, test impact, review scope).

4. **Don't trust subagent report templates across projects.** Directory structure varies. Validate paths against the current project's naming rules (docs/journals/, plans/reports/, etc.) before trusting a template from another session.

5. **Related rows in structured docs need consistent fixing.** When a table or nested structure has multiple instances of the same stale claim, fix all of them in one pass, or flag incompleteness explicitly. Partial fixes create subtle inconsistency that's hard to spot in diff review.

## Next Steps

1. ✅ Fixed all 4 P0 bugs; full suite passing.
2. ✅ Verified via independent test re-run + code review + adversarial validation.
3. ✅ Committed all 4 phases (each with its own commit).
4. ✅ Plan.md sync'd with actual file conflicts + execution waves + verification results.
5. Pending: Manual browser test on each of the 4 fixes (agent environment limitation; QA checklist provided in phase reports).

---

**Broader context:** This followed a red-team review (same session, different plan `260711-0838` covering 15 findings across 7 phases) that discovered better designs for 3 of the 4 P0 fixes. Reconciled rather than duplicated: ported still-applicable red-team findings (2 gaps) into this better plan as amendments. Avoided one dead-code-reactivation trap the first plan's design walked into (resurrecting `source=call_cockpit` code path).
