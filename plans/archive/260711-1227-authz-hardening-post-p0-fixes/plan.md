---
title: "Authz Hardening + Post-P0 Fixes"
description: "Fix 2 IDOR-shaped authz gaps (unclaim ownership, resolve-actions ownership), 1 pre-existing 404, 1 test-coverage gap — all deferred/documented during the prior P0/UX-fix session"
status: completed
priority: P1
branch: "main"
tags: [crm, security, authz, worklist]
blockedBy: []
blocks: []
created: "2026-07-11T05:32:13.281Z"
createdBy: "ck:plan"
source: skill
---

# Authz Hardening + Post-P0 Fixes

## Overview

4 items deferred during the prior session's 2 shipped plans (`plans/260711-0933-fix-p0-outreach-flow-gaps`, `plans/260711-0838-worklist-claim-call-log-flow-fixes`, both merged to `main`: commits `33578bad`, `200916a2`). Both IDOR-shaped gaps below were explicitly identified and documented as "authz hardening, out of scope" at the time — this plan closes them, plus 2 smaller loose ends.

1. **Unclaim ownership + audit trail** ("Trả việc"): any staff can currently unclaim ANY customer's claim, not just their own. Discussed with user — decided NOT to block the action outright (would deadlock genuinely-mismatched leads), but require an ownership check (assignee-only, no admin override — no role/permission system exists yet to build one on) PLUS a mandatory reason + audit note (matches industry practice for claim/drop queues: visibility over hard gating).
2. **`resolve_actions_and_tasks()` IDOR + 2 sibling gaps found during red-team review**: dismiss/complete actions by client-supplied `action_id`/`task_id` with no check they belong to the `party_id` of the activity being finalized. Fix: resolve each id's true `party_id` server-side, skip (log + continue) any mismatch. **Scope broadened (2026-07-11)**: red-team review found the identical vulnerability class unfixed in 2 more places — `execute_side_effects()`'s `complete_task_ids` loop (same file, 10 lines from the original fix) and `screen_customer_360_tasks.py`'s `done`/`cancel`/`postpone` handlers (a second, independent live IDOR instance). User decided to fold both into Phase 3 rather than track separately, since the fix tool (`AuthorizationService.is_same_party()`) already exists once Phase 1 lands.
3. **Worklist header "+ Tạo task" 404**: confirmed real (TestClient-verified in the prior session), pre-existing, not introduced by prior work. Root cause: `POST /customers/{party_id}/tasks` doesn't route-match an empty `party_id` segment. Fix: route the no-party case to the existing `POST /tasks` (party-less task route), extended to accept the fields M05 sends and to honor `return_to` like its sibling route.
4. **M05 `return_to=stay` test coverage**: `post_task`/`patch_task_edit` (screen_modal_task.py) ship with only a manual-verify checklist — no pytest regression guard. Add tests matching the established handler-recovery pattern already used in `test_quick_outcome_cockpit_post.py`.

**Research**: `research/researcher-01-unclaim-ownership-audit-trail.md`, `research/researcher-02-no-party-task-route-test-structure.md`.

**Scope Challenge (2026-07-11)**: HOLD SCOPE — user pre-specified exact scope with file:line citations and decided policy directions; no expansion/reduction warranted (later legitimately broadened by red-team findings, see below — that's new evidence, not scope creep).

**Mid-plan design decision (2026-07-11)**: user asked to consider centralizing authorization logic into a proper hexagonal service (prep for future RBAC) rather than 2 inline `==` comparisons scattered across `task_service.py` and `activity_side_effects.py`. Decided: NOT a full RBAC build (would be speculative — no permission-check infra exists, `AppUser.role` is explicitly "auth deferred" per existing code), but a small, properly-designed `AuthorizationService` (new Phase 1) that findings #1 and #2 both consume — clean typed interface (`is_owner`, `is_same_party`), deliberately ad-hoc/minimal internals for v1. This inserted a new Phase 1, shifting the original 4 phases to 2-5.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Authorization Service Foundation](./phase-01-authorization-service-foundation.md) | Completed |
| 2 | [Unclaim Ownership and Audit Trail](./phase-02-unclaim-ownership-and-audit-trail.md) | Completed |
| 3 | [Resolve IDOR Fix](./phase-03-resolve-idor-fix.md) | Completed |
| 4 | [No-Party Task Creation Fix](./phase-04-no-party-task-creation-fix.md) | Completed |
| 5 | [M05 Return-To-Stay Test Coverage](./phase-05-m05-return-to-stay-test-coverage.md) | Completed |

## Dependencies

- No cross-plan `blockedBy`/`blocks` — both prior-session plans are DONE, no active phases remain.
- Phase 2 and Phase 3 both `dependencies: [1]` — both consume `AuthorizationService` from Phase 1. Phase 1 must land first.
- Phase 4 and Phase 5 have no dependencies — no file overlap with 1/2/3, safe to implement/cook in parallel with each other or with the 1→{2,3} chain.
- **Correction (post-red-team, was wrong)**: Phase 2 and Phase 3 are NOT file-overlap-free — both now touch `composition.py` (Phase 2 wires `authz`+`notes` into `TaskService`; Phase 3 wires `authz` into `register_activity_routes`/`screen_customer_360_tasks.py`'s factory). Do NOT cook 2 and 3 in true concurrent parallel — sequence them (either order works, both depend only on 1) to avoid 2 agents editing `composition.py` at the same time.
- Phases 1, 2, 3 touch security-sensitive authorization logic — red-team review completed 2026-07-11, see below. Do not cook until its findings are applied (they are, as of this plan's current state).

## Red Team Review

### Session — 2026-07-11
**Findings:** 12 accepted (6 Critical, 2 High, 4 Medium) — all 4 reviewers independently found the same fail-open bug, making it the single most important catch of this review. Reviewers: Security Adversary (Fact Checker), Failure Mode Analyst (Flow Tracer), Assumption Destroyer (Scope Auditor), Scope & Complexity Critic (Contract Verifier) — Full tier (5 phases, security-sensitive).

| # | Finding | Severity | Reviewer(s) | Disposition |
|---|---|---|---|---|
| 1 | Ownership check `if actor_id and not is_owner(...)` is fail-OPEN — under this app's real deployment (LAN-trust, no CF Access, `current_user=None`), `actor_id` is always empty, so the check never fires; the fix as originally specified didn't fix anything | Critical | **All 4 reviewers independently** | Accept — Phase 2 rewritten: `if not actor_id or not is_owner(...)`, plus explicit 401 at route layer |
| 2 | `TaskService.__init__`'s required `authz` param breaks 8-10 existing test constructions across 5 files; also illegal Python (non-default after default) unless reordered | Critical | Scope Critic, Security, FMA | Accept — Phase 2: keyword-only signature, all 8 test files added to scope |
| 3 | `resolve_actions_and_tasks()`/`bulk_resolve()`'s new required params break ~19-20 calls in `test_outcome_bulk_resolve.py` | Critical | Scope Critic, Security, Assumption Destroyer, FMA | Accept — Phase 3: test file added to scope |
| 4 | `notes_repo` wiring calls the wrong layer (raw `NoteRepository.add_note(note)` vs. `NoteService`-shaped kwargs in the pseudocode) — `TypeError` silently swallowed, audit note never written, defeating the entire policy rationale | Critical | Security, Assumption Destroyer, FMA | Accept — Phase 2: wire `NoteService`, not the raw repo |
| 5 | Sibling unguarded code path: `complete_task_ids` (execute_side_effects step 6, 10 lines from the Phase 3 fix, same file) has the identical IDOR shape, untouched | Critical | Security Adversary | Accept — folded into Phase 3 |
| 6 | A second, entirely separate live IDOR instance: `PATCH /customers/{party_id}/tasks/{task_id}/{done,cancel,postpone}` never checks the task's real party_id against the URL's | Critical | Security Adversary | Accept, user confirmed — folded into Phase 3 |
| 7 | `AuthorizationService`'s "wired once, single source of truth" claim didn't hold — 2 non-class consumers had no clean path to the composition-wired instance, real outcome would have been inline construction at 2+ sites | High | Security, Assumption Destroyer, Scope Critic | Accept — Phase 1/3 revised: full explicit-parameter threading through both call chains, no inline-construction fallback |
| 8 | Plan simultaneously claimed the abstraction was clean AND admitted (in its own Risk Assessment) it didn't fit one of its 2 consumers | High | Scope Critic | Accept — same fix as #7 |
| 9 | Stale `TaskClaimWriter` Protocol (`screen_worklist.py:75-77`) still declares old `bool` return type | Medium | Security, Assumption Destroyer, Scope Critic | Accept — added to Phase 2 |
| 10 | Phase 2 handler control-flow underspecified — risk of "forbidden" result falling through to a 200 render if the try/except isn't restructured carefully | Medium | Scope Critic | Accept — Phase 2 now specifies exact control flow |
| 11 | Phase 4 defended against a phantom consumer — `/tasks/modal/create`'s target template doesn't exist on disk (already-dead code) | Medium | Scope Critic, FMA | Accept (light) — Phase 4 drops the defensive framing, flags the dead-template bug separately (not fixed, out of scope) |
| 12 | `VALID_UNCLAIM_REASONS` as (code, label) pairs contradicts the flat-code-list convention every other `VALID_*` constant in this codebase uses | Medium | Assumption Destroyer | Accept — Phase 2: flat code list, labels moved to template layer |

**Reviewer reports:** `reports/from-code-reviewer-to-planner-red-team-security-adversary-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-failure-mode-analyst-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-assumption-destroyer-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-scope-complexity-critic-plan-review-report.md`.

**User decisions during adjudication**: apply all 12 findings (not a subset); fold finding #6 (2nd IDOR site) into Phase 3 rather than tracking separately, since `AuthorizationService` already makes it cheap to fix once Phase 1 lands.

### Whole-Plan Consistency Sweep
- Files reread: `plan.md`, `phase-01` through `phase-05` (all 5), after applying the 12 findings.
- Decision deltas checked: 12 (formal findings), all traced to their specific phase edits.
- Reconciled stale references: Phase 1's "fallback to inline construction" language (removed, replaced with full-threading commitment); Phase 2's fail-open guard, notes wiring, reasons-constant shape, missing test files, stale Protocol; Phase 3's scope (complete_task_ids + 2nd IDOR site added), test file additions, full DI threading; Phase 4's phantom-consumer risk framing; Dependencies section's now-incorrect "no file overlap between 2 and 3" claim (composition.py is now shared — corrected to require sequencing, not true parallel).
- Unresolved contradictions: **0**.

## Validation Log

### Session — 2026-07-11
Guard per `validate-workflow.md`: `## Red Team Review` section already present with verification evidence (4 reviewers, Fact Checker/Flow Tracer/Scope Auditor/Contract Verifier roles) — skipped the separate Step 2.5 verification pass, went straight to the interview.

3 questions asked (within the configured 3-8 range), all targeting genuine post-red-team decision points not yet settled by the review itself:

1. **DI threading scope for Phase 3** — after red-team review flagged the original "fallback to inline construction" design as inconsistent, Phase 3 was revised to thread `AuthorizationService` explicitly through the full call chain (including the newly-added 2nd IDOR site in `screen_customer_360_tasks.py`), touching more files than a locally-inline fix would. Asked whether to keep full threading or allow inline construction just at the new site to reduce blast radius.
   - **Decision: keep full threading.** Matches the user's original "properly centralized" requirement from the mid-plan design discussion — an inline exception at the newest site would reintroduce exactly the inconsistency the red-team review flagged.
2. **Phase 2/Phase 3 `composition.py` conflict** — red-team review found both phases now edit `composition.py` (Phase 2 wires `authz`+`notes` into `TaskService`; Phase 3 wires `authz` into `register_activity_routes`/`screen_customer_360_tasks.py`'s factory), so the plan's original "no file overlap, safe to parallelize" claim was wrong. Asked how to handle at cook time.
   - **Decision: cook sequentially, Phase 2 then Phase 3** (order arbitrary, both only depend on Phase 1) — simplest, avoids any merge risk on a security-sensitive shared file. Already reflected in the plan's Dependencies section.
3. **2nd IDOR site status code** — Phase 3's newly-added fix for `screen_customer_360_tasks.py`'s `done`/`cancel`/`postpone` handlers needed a decided response code for the cross-party rejection case. Plan had proposed 404 (IDOR-safe, doesn't confirm the resource exists elsewhere) as the recommended default.
   - **Decision: 403**, not the recommended 404 — user prioritized explicit-rejection clarity over resource-existence non-disclosure for this internal, LAN-trust CRM (not a public-internet-facing API where resource-enumeration hardening carries more weight). Propagated to Phase 3's Implementation Step 6.

### Whole-Plan Consistency Sweep (post-validation)
- Files reread: `plan.md`, `phase-03-resolve-idor-fix.md` (only file touched by validation decisions — decisions 1 and 2 confirmed existing plan language unchanged, decision 3 required one edit).
- Decision deltas checked: 3 (this validation session's answers).
- Reconciled stale references: Phase 3 Implementation Step 6's status code (404 proposal → 403 decided, with rationale noting this was a validation-session decision, not carried over from red-team).
- Unresolved contradictions: **0**.

**Recommendation**: plan is implementation-ready (red-team + validation both complete, 0 open contradictions). Per user instruction (2026-07-11), holding here — not proceeding to `/ck:cook` this turn.

## Implementation Log

### Session — 2026-07-11 (`/ck:cook --auto`)
All 5 phases implemented via parallel/sequential subagents per Dependencies (1 → {2 then 3} sequential on shared `composition.py`; 4 and 5 independent, ran concurrently with the chain).

- Phase 1: `AuthorizationService` (`is_owner`/`is_same_party`) created, wired once in `composition.py`. 7/7 unit tests.
- Phase 2: fail-closed unclaim guard + `NoteService`-backed audit trail; 9 test call sites across 5 files updated; 14 new dedicated tests (incl. DB-verified audit note + dedicated unauthenticated-actor test).
- Phase 3: `resolve_actions_and_tasks` + `execute_side_effects` step 6 (`complete_task_ids`) + `screen_customer_360_tasks.py`'s 3 handlers (2nd IDOR site) all guarded via full `authz` DI threading from `composition.py`; 40 test call sites across 6 files updated/added.
- Phase 4: worklist header "+ Tạo task" 404 fixed, routes to `/tasks` with full field forwarding + `return_to` handling; 7 new tests. Flagged (not fixed, out of scope): `GET /tasks/modal/create`'s target template doesn't exist on disk — pre-existing dead code, separate decision needed.
- Phase 5: 8 new regression tests for M05 `post_task`/`patch_task_edit` `return_to=stay` behavior.

**Verification**: full CRM suite independently re-run twice outside the implementing agents (once by controller, once by code-reviewer) — **1152 passed, 1 skipped, 0 failed** both times. Mandatory `code-reviewer` pass: 0 blocking findings; explicitly re-verified in landed code (not trusted from reports) that the fail-closed guard, `NoteService` wiring, both `execute_side_effects` guards, the 2nd IDOR site, and single-shared-instance `authz` threading are all genuinely correct, not just claimed.

**Known residual (informational, not blocking)**: Phase 2's manual UI click-through of the reason-picker `<select>` not performed (server-side behavior fully test-covered).

Reports: `reports/phase-01-implementation-report.md` through `reports/phase-05-implementation-report.md`, `reports/code-reviewer-full-diff-review-report.md`.

### Follow-up session — 2026-07-11 (closing the 2 residuals)

Both items flagged as residual/out-of-scope above are now closed:

1. **Manual UI click-through of the unclaim reason-picker (Phase 2's residual)**: verified live via browser against the running `crm` container (customer `6d08c918-cb56-4743-845f-8c304ec3b064`, a genuinely claimed party). Confirmed: (a) the "Trả việc" button is disabled until a reason is selected, enables correctly on selection (JS gating works); (b) clicking it fires `PATCH /customers/{party_id}/unclaim`; (c) this dev environment has no CF Access token (`current_user` is always `None` locally, same as production's LAN-trust bypass path when unauthenticated), so the click genuinely exercised the exact unauthenticated-rejection scenario the original fail-open bug missed — server logged **401 Unauthorized**, and the claim's `status`/`assignee_user_id` were confirmed unchanged in the DB afterward. The "rightful owner succeeds" path remains pytest-only (DB-verified in `test_unclaim_ownership_and_audit_trail.py`) — this local environment has no way to authenticate as a real user without a genuine CF Access token, so that path cannot be re-proven via live browser here.

2. **Dead-code bug fixed** (`GET /tasks/modal/create` → `fragments/modal_create_task.html`, which didn't exist on disk, flagged not-fixed during Phase 4): rather than author a new near-duplicate template, S07 Tasks Board's "+ Tạo task" button (both the header and empty-state variants in `tasks_board.html`) now opens the existing, already-working M05 modal (`GET /modals/m05`, already globally wired via `make_party_modals_router` in `composition.py`) — reuse over duplication (YAGNI/DRY). Changes: `tasks_board.html`'s 2 buttons retargeted to `hx-get="/modals/m05"` / `hx-target="#modal-root"`, its `<div id="modal">` renamed to `<div id="modal-root">` (the id M05's own template hardcodes for its close/scrim JS and form swap target — confirmed no other element on this page depended on the old `#modal` id), and the dead `handle_modal_create_task` route + its stale template reference removed from `screen_tasks_board.py`. Verified live: clicked "+ Tạo task" on `/tasks` → M05 modal opened (no-party display "— (không gắn)") → submitted → task created in DB with `party_id=None`, `task_kind='generic'` → modal closed cleanly. Test-verify task row deleted after confirming. Full suite re-run after both changes: **1152 passed, 1 skipped, 0 failed**.

Files touched this session (beyond the 5 phases): `crm/src/adapters/inbound/web/screen_tasks_board.py`, `crm/src/adapters/inbound/web/templates/tasks_board.html`, `crm/src/tests/test_tasks_board_no_party_create.py` (docstring correction only, route list was stale).

**Plan status: fully closed.** All 5 phases + both previously-flagged residuals complete, verified (pytest + live browser + DB), zero known open items.
