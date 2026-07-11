---
title: "Worklist-Claim-Gọi-Log Flow Fixes (UX Audit)"
description: "Fix 15 UX-audit findings across CRM S01 Worklist/S03 360/S14 Call Cockpit/S15 Task/M05/M08, in report priority order"
status: pending
priority: P1
branch: "main"
tags: [crm, ux, worklist, call-cockpit]
blockedBy: []
blocks: []
created: "2026-07-11T01:45:13.528Z"
createdBy: "ck:plan"
source: skill
---

# Worklist-Claim-Gọi-Log Flow Fixes (UX Audit)

## Overview

Nguồn: [ux-review-260711-0818-worklist-claim-call-log-flow-report.md](../reports/ux-review-260711-0818-worklist-claim-call-log-flow-report.md) — MỌI finding/quyết định trong plan này phải khớp report đó, không mở lại phân tích. Report đã chốt 3 câu hỏi chính sách với user (2026-07-11) — xem "User decisions" trong report và mục Policy Decisions bên dưới.

15 findings, sửa theo đúng thứ tự ưu tiên bảng VI của report — mapping 1:1 sang 7 phase:

| Phase | Findings | Tier | Status |
|---|---|---|---|
| 1 | #1 (HX-Redirect phá context) | P0 | **Superseded** — see `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-01-modal-return-to-invoker.md` |
| 2 | #2 (resolve bất kể outcome, đốt signal 30d) | P0 | **Superseded** — see `.../phase-02-outcome-aware-resolve.md` |
| 3 | #3 (callback/followup task không assignee) | P0 | **Superseded** — see `.../phase-03-callback-task-assignee.md` |
| 4 | #4 (JS gate script=None) | P0 | **Superseded** — see `.../phase-04-cockpit-js-unconditional.md` |
| 5 | #5-8 (kênh modal, closebar, claim feedback, cockpit link) | Medium | Active (this plan) |
| 6 | #9-10 (claim race auto-claim-on-call-start, dismiss-session bắt buộc log) | Medium (policy) | Active (this plan) |
| 7 | #11-15 (cosmetic/dead code) | Minor | Active (this plan) |

**Superseded (2026-07-11)**: a parallel plan (`plans/260711-0933-fix-p0-outreach-flow-gaps`, same source report, same 4 P0 findings) was found mid-review with materially better designs for phases 1/3/4 — it sidesteps the dead-code trap this plan's original phase 1 walked into, and avoids scope creep in phase 3 that this plan's red-team flagged. See `## Red Team Review` below for the full reconciliation. Phases 1-4 here are kept for their research/evidence trail; treat `260711-0933`'s phase files as canonical/executable for the 4 P0 fixes. Phases 5-7 remain this plan's active scope — the P0-only plan explicitly excludes them.

Verification pass (2026-07-11, Explore agent, post-report) đã re-check toàn bộ 15 file:line citation trên code hiện tại — một vài đường dẫn/số dòng đã trôi (~20 phút giữa report và giờ viết plan), ghi rõ trong từng phase. Đáng chú ý: **finding #14 (backslash `'\modals\m08?...'`) KHÔNG tồn tại trong code hiện tại** — search toàn repo ra 0 match; phase 7 sẽ verify lại thay vì sửa mù.

## Policy Decisions (chốt cùng user, báo cáo đã ghi — không hỏi lại)

1. **Finding 2** — outcome `no_answer`/`busy`: KHÔNG resolve action/task; **auto-snooze 1-3 ngày** thay vì dismiss TTL 30d. Các outcome khác (answered/purchased/refused/wrong_number) vẫn resolve như hiện tại.
2. **Finding 10** — "Hoàn tất ✓" dismiss-session: **bắt buộc kèm activity log** (không cho resolve hàng loạt mà không ghi nhận tiếp xúc).
3. **Finding 9** — claim-at-call-start: **auto-claim khi bấm "Gọi"** (T0→T1, tạo call draft trong `s14StripStartCall`). Mở cockpit chỉ để xem KHÔNG claim (giữ nguyên). Bỏ ngang dùng "Trả việc" có sẵn để nhả — không cần logic mới cho unclaim.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Redirect Context-Loss Fix](./phase-01-redirect-context-loss-fix.md) | Superseded |
| 2 | [Resolve-Outcome Gating](./phase-02-resolve-outcome-gating.md) | Superseded |
| 3 | [Callback-Followup Task Assignee](./phase-03-callback-followup-task-assignee.md) | Superseded |
| 4 | [Script-Gate JS Fix](./phase-04-script-gate-js-fix.md) | Superseded |
| 5 | [Medium Findings Batch](./phase-05-medium-findings-batch.md) | Pending |
| 6 | [Claim-Policy Findings](./phase-06-claim-policy-findings.md) | Pending |
| 7 | [Minor Cleanup](./phase-07-minor-cleanup.md) | Pending |

## Dependencies

- **`plans/260711-0933-fix-p0-outreach-flow-gaps` shipped 2026-07-11** (was blockedBy, now unblocked) — the 4 P0 fixes landed via `/ck:cook --auto --parallel`, full suite 1075 passed/1 skipped, code review 8/10 PASS, 0 critical/high. Phases 5-7 here can now proceed — their dependency notes (pointing at 0933's phase-01/phase-02) are satisfied.
- Touches files last modified by `plans/260710-1338-activity-log-disposition-api` (DONE 2026-07-11 — `activity_side_effects.py`, `c360_call_cockpit_panel.html`, `screen_customer_360_activity.py`) and `plans/260709-1122-worklist-queue-vs-mytasks-split` (DONE 2026-07-09 — `worklist_fragment.html`, `_wl_row.html`). Both fully shipped, no active phases remain.
- Phase 5a rebases its `_wl_row.html` `contact_btn` edits on top of `260711-0933`'s phase-01 amendment output (same 4 lines) rather than editing independently — land that phase first.
- Phase 6 depends on `260711-0933`'s phase-02 (+ its `/reason/resolve-async` amendment) for its "reuses the outcome-gated bulk-resolve" design in 6b.
- Phase 7's #12 depends on `260711-0933`'s phase-01 (reshapes the same `hx-trigger` attribute #12 cleans up).

## Red Team Review

### Session — 2026-07-11
**Findings:** 26 raw (4 reviewers) → 22 after dedup → 15 accepted, capped per methodology (7 Critical, 4 High, 4 Medium formally adjudicated; 4 additional cheap fixes folded in during application: stale test docstring, cross-phase file-collision doc note, dead TASK_SOURCE constants, false actor_id=None claim).
**Severity breakdown:** 7 Critical, 4 High, 4 Medium (formal top-15); reviewers: Security Adversary (Fact Checker), Failure Mode Analyst (Flow Tracer), Assumption Destroyer (Scope Auditor), Scope & Complexity Critic (Contract Verifier) — Full tier (7 phases).

| # | Finding | Severity | Disposition | Applied To |
|---|---|---|---|---|
| 1 | Worklist header no-party M05 flow likely 404s pre-existing (confirmed by 3/4 reviewers independently) | Critical | Accept | Descoped in `260711-0933`'s phase-01 amendment (this plan's own phase 1 is superseded) |
| 2 | Phase 1's reuse of M08's `source=="call_cockpit"` branch would ship a broken fragment (`s14OpenOutcome` already deleted by a shipped migration, regression test forbids it) | Critical | Accept | Design abandoned — `260711-0933`'s independent `return_to` field sidesteps the branch entirely; this plan's own phase 1 marked superseded |
| 3 | No ownership/party-match check before dismiss/complete in `execute_side_effects` step 7 (IDOR-shaped) | Critical | Accept | Documented as pre-existing, out-of-P0-scope gap in `260711-0933`'s plan.md; not fixed by either plan |
| 4 | Phase 6a's claim-at-call-start race not actually closed — TOCTOU + silent try/except swallow, zero feedback to losing staff | Critical | Accept | Phase 6, rewritten (claim-conflict surfaced via response field + cockpit warning) |
| 5 | Phase 6a adds a 2nd auto-claim call site without touching the existing finalize-time one | Critical | Accept | Phase 6, rewritten (documented as intentional safety-net no-op, comment added) |
| 6 | Phase 2's fix silently undone by the cockpit's own "+Nhắn Zalo" button → `/reason/resolve-async` → unconditional `_bulk_resolve`, shown specifically for the `no_answer` outcome the fix protects | Critical | Accept | Ported to `260711-0933`'s phase-02 as amendment |
| 7 | Phase 6b's "Hoàn tất ✓" repoint (as literally specified) discards per-checkbox selective resolve — every click would resolve ALL, not just checked | Critical | Accept | Phase 6, rewritten (dynamic `:checked` read required) |
| 8 | Phase 1's `s14StripOpenDetail`/edit_activity M08 call site doesn't route through the fixed branch — inert | High | Accept | Ported to `260711-0933`'s phase-01 as amendment (`handle_patch_activity` needs its own fix) |
| 9 | `handle_unclaim_customer` has no ownership check; Phase 6a increases exposure | High | Accept (light) | Phase 6, flagged explicitly in Risk Assessment, not fixed (scope-bounded) |
| 10 | `task_id` in `handle_create_call_session` is a spoofable client field, sole gate to skip auto-claim | High | Accept | Phase 6, rewritten (ownership verification added) |
| 11 | Phase 3's stated goal ("S15 provenance đúng") not achieved — `task_detail.html` missing from scope | High | Accept | Moot — `260711-0933`'s phase-03 deliberately keeps `source="manual"` unchanged, sidestepping the gap entirely; this plan's own phase 3 marked superseded |
| 12 | Phase 7 #12's "wire claimSuccess" is a guaranteed double-fetch, not a maybe | Medium/High | Accept | Phase 7, resolved definitively (remove, don't wire) |
| 13 | Phase 5c over-engineered relative to the bug (3-call-site param + inline JS for what's a 1-line attribute fix) | Medium | Accept | Phase 5, rewritten (minimal `open`-attribute fix first, highlight is optional layer) |
| 14 | Phase 5a's "phone/other variants presumably already send hinh_thuc=call" is factually wrong — all 4 send `channel=` | Medium | Accept | Phase 5, corrected (all 4 variants normalized) |
| 15 | Phase 1 uses 2 param names (`caller`/`source`) for 1 concept | Medium | Accept | Moot — superseded by `260711-0933`'s `return_to` design (single field) |

**Reviewer reports:** `reports/from-code-reviewer-to-planner-red-team-security-adversary-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-failure-mode-analyst-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-assumption-destroyer-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-scope-complexity-critic-plan-review-report.md`.

**Unplanned discovery during review**: a second, independently-authored plan (`plans/260711-0933-fix-p0-outreach-flow-gaps`) covering the same 4 P0 findings appeared mid-session. Reconciled rather than duplicated — see "Superseded" note above and each phase file's amendment. This is the primary reason several findings above resolved as "moot" (the better design in the other plan sidestepped the problem) rather than requiring a direct code-level fix in this plan.

### Whole-Plan Consistency Sweep
- Files reread: `plan.md`, `phase-01` through `phase-07` (this plan), plus `plans/260711-0933-fix-p0-outreach-flow-gaps/plan.md` and its `phase-01`/`phase-02`/`phase-03`/`phase-04` (cross-referenced, amended).
- Decision deltas checked: 15 (formal findings) + 4 (folded-in cheap fixes) + 1 (the supersession discovery itself).
- Reconciled stale references: phase 1-4 status (pending → superseded, 4 files), plan.md phase table + Dependencies section, phase 5/6/7 dependency notes (pointed at `260711-0933` phases instead of this plan's own superseded phase 1/2), phase 7 #12 (indecisive → decided), phase 5a/5c (corrected premises).
- Unresolved contradictions: **0**. Remaining known gaps are explicitly documented as out-of-scope/flagged-not-fixed (IDOR ownership check, `handle_unclaim_customer` ownership check) rather than left as silent contradictions.
