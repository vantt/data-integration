---
phase: 7
title: "Minor Cleanup"
status: pending
priority: P3
dependencies: []
---

# Phase 7: Minor Cleanup

> **Dependency note (2026-07-11)**: #12 depends on `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-01-modal-return-to-invoker.md` landing first (it reshapes the same `hx-trigger` attribute this finding cleans up) — not this directory's own Phase 1, which is superseded.

## Overview

5 cosmetic/dead-code findings (report §IV.11-15), each XS effort, independent of each other and of every earlier phase — safe to batch and do last.

### #11 — Dead progress bar

`worklist_fragment.html:52-68` renders "Đã xong 0/{{ total_count }}" — the `0` is a hardcoded server-side baseline with an explicit code comment acknowledging it never updates ("X = 0 as server-side baseline — no session tracking needed; refreshes reset it. The bar communicates scale, not precise done-count"). This is an intentional design note, not an accidental bug, but the report flags it as confusing since the label reads like a live counter. Options: (a) remove the "Đã xong X/Y" numeric label and keep only a scale indicator (e.g. just "Y việc"), (b) leave as-is given the existing comment defends the design. Confirm with user before changing — this one has an explicit prior design rationale in the code itself, unlike the others in this batch.

### #12 — Dead `claimSuccess` trigger — RESOLVED BY RED-TEAM REVIEW, decision made, not deferred

`worklist_fragment.html:19-23`/`worklist.html:34-38`'s `hx-trigger="claimSuccess from:body"` has zero emitters anywhere in `crm/src`.

**Original framing ("check for conflicts, decide at implementation time") was itself flagged by red-team as indecisive for a P3 phase — resolved now, not deferred.** Failure Mode Analyst traced the actual markup and confirmed the conflict is certain, not conditional: the claim button (`_wl_row.html`) already has `hx-target="#worklist-container" hx-swap="outerHTML"` and its handler (`screen_worklist.py:513-524`) directly returns a full re-render of that same container in one round trip. Wiring `claimSuccess` to also fire (option a) would make the freshly-swapped-in container — which carries the same `hx-trigger` attribute as part of its own markup — immediately issue a SECOND `GET /worklist/fragment` in response to the event its own response just triggered. Guaranteed double-fetch/flicker on every claim, not a maybe.

**Decision: option (b), remove `claimSuccess` from the trigger list.** This is already consistent with how both this plan's Phase 1 (superseded, see below) and the parallel `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-01-modal-return-to-invoker.md` handle it — 0933's phase 1 explicitly keeps `claimSuccess` present-but-unwired alongside its new `worklistRefresh` event ("tiện thể kích hoạt luôn trigger `claimSuccess`... không bắt buộc sửa nơi emit nó" — i.e. left dead intentionally, no new emitter added). This phase's job is just to clean up the leftover dead clause once 0933's phase 1 has landed and reshaped this same `hx-trigger` attribute — don't reintroduce it.

### #13 — Claim-task snooze has no visual feedback

`_wl_row.html:312-313`'s claim-task snooze button uses `hx-swap="none"` (row stays, no feedback) vs. the action-row snooze at `:149-150` which uses `hx-target="#aq-{id}" hx-swap="delete"` (row removed immediately). Fix: give the claim-task snooze row a stable `id` and switch to `hx-target="#<that id>" hx-swap="delete"` (or an `outerHTML` swap to a "snoozed until X" placeholder if silently vanishing is undesirable for a claimed task — worth a quick check since removing a CLAIMED task row silently might read as "did my snooze work" ambiguity; a brief inline confirmation state may fit better than outright deletion). Decide the exact swap target at implementation time by comparing to how the equivalent claimed-task due-date change already renders elsewhere (e.g. Phase 2's task snooze reuses `handle_snooze_task`, which already returns 204 today — this finding is purely about the row's client-side reaction to that response, not the backend).

### #14 — `aqCallNow` backslash bug — VERIFY ONLY, LIKELY ALREADY FIXED

Report cites a `'\modals\m08?...'` backslash string in a fallback branch. Verification pass (2026-07-11, this plan's research) found **zero matches** for any backslash-escaped `/modals/m08` string anywhere in the current repo — `aqCallNow` (`c360_insight_panel.html:156-159`) already uses correct forward-slash URLs: `htmx.ajax('GET', '/modals/m08?party_id=' + pid + '&mode=log&hinh_thuc=call', {...})`. Treat this as already resolved; do a final grep confirmation at implementation time (`grep -rn "\\\\modals\\\\m08"` or equivalent) before closing — do not "fix" code that isn't broken.

### #15 — Row-click duplicates "Xem 360" button

`_wl_row.html:59`'s row-click (`onclick="if(!event.target.closest('button,a,details,summary')) location.href='/customers/{{ a.party_id }}'"`) navigates to S03, identical destination to the explicit "Xem 360" button (`:164`). Report presents 2 options, no verdict given: (i) change row-click to open the cockpit instead (hot action for the row's primary intent), or (ii) accept the redundancy as intentional (common list-UI pattern — whole row as a bigger click target for the same action). **Ask the user which they prefer before implementing** — this is a UX call, not a bug, and the report explicitly left it open (§V "Đề xuất: row-click đổi thành mở cockpit... hoặc giữ nguyên nhưng chấp nhận redundancy có chủ đích").

## Requirements

- #11: confirm intent with user before changing (has an explicit prior design comment defending current behavior).
- #12: remove `claimSuccess` from the `hx-trigger` list (decided — see Overview, not conditional).
- #13: claimed-task snooze gives the same "row responded to my click" feedback quality as the action-row snooze (exact visual treatment — delete vs. placeholder — decided at implementation time).
- #14: verification only, no code change expected.
- #15: get an explicit user decision before touching row-click behavior (options i/ii above).

## Related Code Files

- `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` (#11 progress bar ~line 52-68, #12 hx-trigger ~line 19-23)
- `crm/src/adapters/inbound/web/templates/worklist.html` (#12 hx-trigger ~line 34-38)
- `crm/src/adapters/inbound/web/screen_worklist.py` (#12 claim handler ~line 514-524, if wiring the emitter)
- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` (#13 snooze button ~line 312-313, #15 row-click ~line 59)
- `crm/src/adapters/inbound/web/templates/fragments/c360_insight_panel.html` (#14 verification only, ~line 156-159)

## Implementation Steps

1. **#14 first** (fastest, likely a no-op): grep the repo for any remaining backslash-escaped modal URL; if none found (expected), mark this finding closed with a note in the implementation report — no code change.
2. **#15**: use `AskUserQuestion` (or equivalent explicit check-in) to get the user's choice between row-click→cockpit vs. keep-as-is-redundant before writing any code for this one.
3. **#11**: confirm with user whether to keep the existing "scale not precise count" design (code comment) or simplify the label — do not silently override a documented prior decision.
4. **#12**: after 0933's phase 1 has landed (it touches this same `hx-trigger` attribute), remove the leftover `claimSuccess from:body` clause — decided as option (b), no further conflict-check needed at implementation time (see Overview).
5. **#13**: give the snooze button a stable row id, switch `hx-swap="none"` to a target+swap that gives visible feedback (delete or placeholder per the Overview note), matching the action-row snooze's existing UX quality bar.

## Success Criteria

- [ ] #14 confirmed non-issue (or fixed, if grep surprisingly finds something) — documented either way.
- [ ] #15 implemented per explicit user choice, not assumed.
- [ ] #11 either left as-is with rationale reconfirmed, or changed per explicit user sign-off.
- [ ] #12 `claimSuccess` clause removed from `hx-trigger` — no dead clause left behind.
- [ ] #13 claimed-task snooze gives visible feedback (row updates/disappears with clear cause-effect), matching action-row snooze's UX quality.

## Risk Assessment

- **Risk**: #11/#15 are UX judgment calls the report explicitly left open — implementing without checking first would silently overrule the report's own "no verdict given" framing. Both steps above insert an explicit confirmation gate for this reason.
- **Risk (#12)**: none remaining — removal (not wiring) eliminates the double-fetch risk entirely rather than requiring runtime verification.
- **Rollback**: all 5 are independent single-file, low-blast-radius tweaks; revert individually with no cross-dependency.
