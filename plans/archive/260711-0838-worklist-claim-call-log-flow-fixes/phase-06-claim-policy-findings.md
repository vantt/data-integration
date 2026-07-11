---
phase: 6
title: "Claim-Policy Findings"
status: pending
priority: P2
dependencies: []
---

# Phase 6: Claim-Policy Findings

> **Dependency note (2026-07-11)**: originally depended on this directory's Phase 2, now superseded — depend instead on `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-02-outcome-aware-resolve.md` (and its amendment) landing first, since 6b's option (b) reuses that phase's outcome-gated bulk-resolve.

## Overview

2 findings, both policy-decided by the user in the report (§"User decisions" #2-3).

**Revised after red-team review (2026-07-11) — 5 corrections, see `## Red Team Review` in plan.md for full findings. This phase now requires materially more than the original 2-line/1-template-attribute design:**

### 6a. Claim-at-call-start (#9)

Today, opening the cockpit does NOT claim (deliberate, unchanged); auto-claim only happens after finalize, via `execute_side_effects` step 2 (`auto_claim_from_contact`, `activity_side_effects.py:104-108`), gated on `auto_claim and actor_id and task_svc is not None`. Since 2 staff can both open the cockpit and press "Gọi" on the same unclaimed customer before either finalizes, there's a race window.

**User decision**: auto-claim when "Gọi" is pressed (T0→T1, i.e. when the call draft is created), not merely on cockpit open. The exact hook point already exists and is idempotent: `POST /api/parties/{party_id}/call-sessions` (`screen_customer_360_activity.py:490-531`, `handle_create_call_session`) — this is what `s14StripStartCall` (`c360_call_cockpit_panel.html:1059`) calls. It already has `actor_id` and an optional `task_id` (present when entering via S15's "Vào phiên gọi", meaning the task is already claimed/pinned — skip auto-claim in that case, matching the existing `auto_claim` gate's "no task_id already driving this contact" semantics).

`TaskService.auto_claim_from_contact(party_id, customer_name, assignee_id)` (`task_service.py:309-334`) is exactly the right primitive — idempotent via `get_customer_claim(party_id)` early-return, safe to call on every "Gọi" press (repeat presses for the same staff+party are a no-op).

"Mở cockpit chỉ để xem KHÔNG claim" stays true — nothing changes about cockpit-open itself, only the call-session-creation POST gains a claim side effect. "Bỏ ngang → dùng Trả việc" — no new unclaim logic needed, the existing unclaim endpoint (`screen_worklist.py`, `unclaim_customer_actions`) already covers it.

**Correction — race isn't actually closed as originally designed (Failure Mode Analyst, Critical)**: `auto_claim_from_contact`'s check-then-insert (`get_customer_claim` → early-return-or-insert, `task_service.py:317-319`) is NOT wrapped in a transaction/lock. A true race between 2 staff pressing "Gọi" within the same instant hits the DB-level unique index (`uidx_task_source_ref`, migration `0037`) on the losing insert — the original design's "wrap in try/except, a claim failure must not block the call draft" means the losing staff's request succeeds anyway with **zero feedback** that someone else already claimed the customer. **Fix**: `handle_create_call_session`'s response must surface the actual claim outcome — after calling `auto_claim_from_contact`, check if the returned task's `assignee_user_id` differs from `actor_id` (meaning someone else got there first); if so, include that in the JSON response (e.g. `{"claimed_by_other": "<display name>"}`), and have the cockpit JS show a visible "Đã được X nhận" warning at T1 instead of silently proceeding as if nothing happened.

**Correction — duplicate auto-claim path (Scope & Complexity Critic, Critical)**: this adds a SECOND call to `auto_claim_from_contact` without touching the existing finalize-time one (`execute_side_effects` step 2, `activity_side_effects.py:104-108`) — every call now potentially triggers the idempotent claim logic twice (call-start + finalize), which is harmless in practice (idempotent, second call always early-returns) but is architecturally redundant against this plan's own "một đường ghi duy nhất" principle. **Fix (documentation only, no code change needed)**: add an explicit code comment at `activity_side_effects.py`'s step 2 noting it is now a safety-net no-op for the common path (claim already happened at call-start via `handle_create_call_session`) and is kept for callers that reach `execute_side_effects` without having gone through call-session creation first (e.g. standalone M08 log with no prior "Gọi" press).

**Correction — pre-existing unclaim ownership gap, flagged not fixed (Security Adversary, High)**: `handle_unclaim_customer` (`screen_worklist.py:526-538`) has no ownership check — any staff can `PATCH .../unclaim` on ANY claimed customer, not just their own. This is a pre-existing gap, not introduced by this plan, but claiming earlier (6a) means claimed-but-uncontacted customers exist for longer, so this gap matters more often after this phase ships. **Not fixing this here** (separate authz-hardening scope, would expand this phase considerably) — but flag it explicitly to the user as a known increased-exposure risk, don't ship silently.

**Correction — `task_id` is a spoofable client field used as the sole skip-gate (Security Adversary, High)**: `handle_create_call_session` accepts `task_id: str = Form(default="")` directly from the client with no verification it exists or belongs to `party_id`/`actor_id`. Any non-empty value skips auto-claim entirely — trivially defeats the whole point of 6a (a client sending garbage `task_id=x` reintroduces the exact 2-staff race this phase exists to close, silently, no error). **Fix**: before skipping auto-claim on a non-empty `task_id`, look it up (`task_svc.get_task(task_id)`) and confirm it exists, `party_id` matches, and `assignee_user_id == actor_id` — only skip auto-claim when all 3 hold; otherwise proceed with `auto_claim_from_contact` as if `task_id` were empty.

### 6b. Dismiss-session bắt buộc log (#10)

`POST /customers/{party_id}/actions/dismiss-session` (`screen_customer_360_panels.py:296-306`, wired from the P01 "Hoàn tất ✓" button in `c360_insight_panel.html:97-99` — verify exact line, drifted from original ~55 citation) calls `action_state.dismiss(aid, user_id=None)` directly for every id in the batch — no activity/note write, no outcome captured, bypassing the flow's own "một đường ghi duy nhất" invariant that every other resolve path goes through `execute_side_effects`.

**User decision**: this action must require a log (no bare resolve-without-contact). Given `execute_side_effects` is the established single write path, the cleanest fix is to route dismiss-session THROUGH it rather than calling `action_state.dismiss` directly. Option (b) — repoint "Hoàn tất ✓" to open M08 with `resolve_action_ids` pre-filled — is the chosen approach.

**Correction — option (b) as originally specified breaks selective per-checkbox resolve (Failure Mode Analyst, Critical)**: `c360_insight_panel.html`'s current checkboxes (`<input type="checkbox" name="action_ids" value="{{ act.action_id }}">`, unchecked by default) let a rep resolve a SUBSET of the session's unresolved actions (e.g. tick 2 of 5, click "Hoàn tất (2) ✓" → only those 2 submit via native form `getlist`). If "Hoàn tất ✓" is repointed to a static server-rendered `resolve_action_ids={all ids}` GET link as originally specified, the checkboxes become cosmetic — EVERY click resolves ALL unresolved actions regardless of what's checked, silently expanding blast radius. **Fix**: the button's URL/request must be built dynamically from the currently-`:checked` inputs (client-side, analogous to how `s14StripSave()` reads its hidden fields at click time), not baked into a static server-rendered id list — e.g. `hx-vals='js:{"resolve_action_ids": Array.from(document.querySelectorAll(\'input[name=action_ids]:checked\')).map(el=>el.value).join(",")}'` on an `hx-get` to `/modals/m08?party_id={party_id}`.

## Requirements

- 6a: pressing "Gọi" (any cockpit entry that creates/adopts a call-session draft, i.e. `handle_create_call_session`) claims the customer via `auto_claim_from_contact`, UNLESS a `task_id` is already present AND verified to belong to `party_id`/`actor_id` (see correction above — presence alone is not enough). Cockpit-open alone (no call-session POST) still does not claim. Claim-conflict outcome (someone else already claimed) is surfaced back to the requesting staff, not silently swallowed.
- 6b: "Hoàn tất ✓" must not silently resolve actions without an activity/note being recorded for that session, AND must preserve the existing per-checkbox selection semantics (resolve only what's checked, not everything).

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` (`handle_create_call_session`, ~line 490-531 — add auto-claim call + `task_id` ownership verification + claim-conflict response field)
- Modify: `crm/src/application/activity_side_effects.py` (step 2, ~line 104-108 — add explanatory comment only, no logic change)
- Reference only: `crm/src/application/task_service.py:309-334` (`auto_claim_from_contact`), `crm/src/adapters/inbound/web/screen_worklist.py:526-538` (`handle_unclaim_customer` — reference for the flagged-not-fixed ownership gap)
- Modify: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` (`handle_dismiss_session`, ~line 296-306)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/c360_insight_panel.html` (verify current line for "Hoàn tất ✓" button, drifted from ~55 — repoint to M08 with dynamic `:checked` read)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (cockpit JS — show claim-conflict warning at T1 if `handle_create_call_session` response indicates `claimed_by_other`)

## Implementation Steps

1. **6a**: in `handle_create_call_session`, before deciding whether to skip auto-claim, if `task_id.strip()` is non-empty, look it up via `task_svc.get_task(task_id)` and verify `party_id` match + `assignee_user_id == actor_id` — treat as "already claimed and pinned" (skip auto-claim) ONLY if all checks pass; otherwise treat `task_id` as absent for auto-claim purposes.
2. After successfully creating/adopting the draft, when auto-claim is not skipped, call `task_svc.auto_claim_from_contact(party_id, <display name — reuse `execute_side_effects._display_name()`'s pattern via `profile.get_party_360`>, actor_id)`. Wrap in try/except-log — a claim failure must not block the call draft itself. Compare the returned task's `assignee_user_id` to `actor_id`; if they differ, include `"claimed_by_other": <display name or id>` in the JSON response.
3. Cockpit JS (wherever `s14StripStartCall`'s response is handled, `c360_call_cockpit_panel.html`): if the response includes `claimed_by_other`, show a visible warning at T1 (banner or toast — reuse existing warning-style UI if one exists in this template, else minimal inline text).
4. Add the explanatory comment to `activity_side_effects.py` step 2 per the "duplicate auto-claim path" correction above.
5. Document (in this phase's implementation report, not in code) the flagged-not-fixed `handle_unclaim_customer` ownership gap — do not silently ship without mentioning it.
6. **6b**: change the "Hoàn tất ✓" button to `hx-get="/modals/m08?party_id={party_id}"` with `hx-vals` dynamically reading `:checked` `action_ids` inputs at click time (see correction above for the exact JS shape) — building on Phase 2's/0933's gated bulk-resolve (reuses `resolve_action_ids` mechanism, no new backend endpoint). Remove or deprecate `handle_dismiss_session` once confirmed nothing else calls it (grep for `dismiss-session` — 0 test coverage confirmed by Scope & Complexity Critic review, so removal is caller-safe but untested; add a regression test for the new M08-repoint path since none exists for either old or new behavior).
7. Manual verify (UI change): press "Gọi" on an unclaimed customer → task appears in caller's Đã Claim immediately. Simulate a claim conflict (2 sessions/tabs, same customer) → second one sees the warning. Press "Hoàn tất ✓" with only 2 of 5 checkboxes ticked → M08 opens with only those 2 ids pre-filled, not all 5.

## Success Criteria

- [ ] Pressing "Gọi" on an unclaimed customer claims them immediately (task visible in Đã Claim without finalizing).
- [ ] Pressing "Gọi" with a spoofed/unrelated `task_id` does NOT skip auto-claim (verified ownership check works).
- [ ] Pressing "Gọi" when a genuinely-owned `task_id` is present (S15 entry) does skip auto-claim (no regression).
- [ ] A genuine claim race (2 staff, same instant) surfaces a visible warning to the losing staff — not silent.
- [ ] Opening the cockpit WITHOUT pressing "Gọi" still does not claim (regression check on the existing deliberate decision).
- [ ] "Hoàn tất ✓" resolves ONLY the checked actions, not the full unresolved set — verified with a partial-selection test case.
- [ ] "Hoàn tất ✓" no longer silently dismisses without a recorded activity — verified end-to-end that the batch resolve now flows through `execute_side_effects` (and therefore also gets the outcome-gating from 0933's phase 2).
- [ ] `handle_dismiss_session` route either removed (if confirmed dead after the template change) or left as a documented fallback — decide explicitly, don't leave stale dead code silently.
- [ ] `handle_unclaim_customer`'s ownership gap is documented in the implementation report as a known, not-fixed-here risk.

## Risk Assessment

- **Risk (6a)**: claiming earlier (at call-start instead of post-finalize) changes when a task first appears in "Đã Claim" — could surprise staff used to today's timing. Acceptable per explicit user decision; call out in the manual-verify pass so the user can confirm the felt experience matches intent.
- **Risk (6a, confirmed real by red-team)**: without the ownership-check and claim-conflict-surfacing corrections above, this phase's core anti-race purpose does not actually hold under concurrent load — these are not optional polish, they're required for the fix to do what it claims.
- **Risk (6a, flagged not fixed)**: `handle_unclaim_customer` has no ownership check; this phase increases how often that gap is exercised. Explicitly out of scope here (would expand into general authz hardening) — must be surfaced to the user, not silently left as an undocumented side effect of this phase.
- **Risk (6b)**: repointing "Hoàn tất ✓" to open M08 changes a 1-click bulk action into a modal flow — more friction by design (that's the point: no log-free resolve). The dynamic `:checked`-read fix adds client-side complexity the original static-link design didn't have — confirm the M08 view reads sensibly for a partial-selection batch (may have been designed for single-action use — verify at implementation time, adjust modal copy/labeling if it reads oddly for a batch).
- **Rollback**: 6a's ownership-check and conflict-surfacing are additive to the single new call site (revert = delete the call + response field + JS warning). 6b changes a template attribute + optionally removes a route (revert = restore `hx-post` + keep the route).
