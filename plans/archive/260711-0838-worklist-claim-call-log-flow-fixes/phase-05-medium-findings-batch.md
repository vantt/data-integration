---
phase: 5
title: "Medium Findings Batch"
status: pending
priority: P2
dependencies: []
---

# Phase 5: Medium Findings Batch

> **Dependency note (2026-07-11)**: this phase's own Phase 1 is superseded by `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-01-modal-return-to-invoker.md` — depend on THAT phase landing first, not this directory's (superseded) phase-01. 5a also touches the same `_wl_row.html` `contact_btn` macro lines that 0933's phase-01 amendment touches (`&return_to=stay`) — land 0933's phase 1 first, then rebase 5a's `channel=`→`hinh_thuc=` rename on top rather than editing independently (same collision risk the Assumption Destroyer review flagged, now resolved by explicit sequencing).

## Overview

4 independent Medium findings (report §III.5-8), batched into one phase since each is small (XS-S effort) but touches different files. No dependency between the 4 sub-fixes themselves; ordered after 0933's Phase 1 lands only because #8 adds a link that benefits from the redirect fix already landing (not a hard blocker, just cleaner cockpit-entry story once done).

**Revised after red-team review (2026-07-11) — 2 corrections, see `## Red Team Review` in plan.md:**
- **5a's premise was factually wrong**: the plan originally assumed the phone/fallback `contact_btn` variants "presumably already send `hinh_thuc=call` or equivalent." Verified (Failure Mode Analyst, grep-checked): **all 4** variants — phone, zalo, facebook, no-identity-fallback — currently send `channel=`, none send `hinh_thuc=`. All 4 need normalizing, not just the 2 originally called out.
- **5c was over-engineered relative to the bug**: the actual bug (claimed task disappears into a collapsed section) is fixed by an unconditional `open` attribute on the "Đã Claim" `<details>` — matching the pattern "Chưa Claim" already uses. The original design (thread a new `highlight_task_id` param through a 3-call-site shared render function + inline `<script>` scroll-into-view) is now scoped as an explicitly optional enhancement layered on top, not required for the fix itself.

### 5a. Kênh không khớp modal (#5)

`_HT_TO_ACT_TYPE` (`screen_customer_360_activity.py:31-34`) defines the canonical channel keys: `"call"`, `"zalo"`, `"fb"`, `"email"`, `"visit"`, `"other"`. Two call sites currently send the WRONG values against this set:
- Worklist `_wl_row.html` `contact_btn` macro sends `channel=zalo`/`channel=facebook` — a param the GET `/modals/m08` handler never reads at all (confirmed: GET handler's `_m08_ctx` signature has no `channel`/`hinh_thuc` param today).
- Cockpit Zalo button (`c360_call_cockpit_panel.html:256`) sends `hinh_thuc=chat` — not a key in `_HT_TO_ACT_TYPE` (falls to `.get(hinh_thuc, "other")` default), and mismatched with `CONTACT_OUTCOMES_BY_CHANNEL_TYPE`'s `"zalo"` key (`domain/entities/activity.py:49-55`).

Fix: standardize on `hinh_thuc` as the one query-param name across every M08 call site (drop `channel=` from worklist), using the canonical values `"call"`/`"zalo"`/`"fb"` (not `"chat"`/`"facebook"`). Add `hinh_thuc: str = Query(default="call")` to the GET `/modals/m08` handler and thread it into the template context so the modal opens with the right channel/outcome-set pre-selected instead of always defaulting to "Cuộc gọi". **All 4** `contact_btn` variants (`_wl_row.html`, phone/zalo/facebook/no-identity-fallback) currently send `channel=` — grep-verified none send `hinh_thuc=` today, including the phone variant (it only "works" today by accident, since "call" happens to be the GET handler's unread default) — normalize all 4, not just zalo/facebook.

### 5b. S15 closebar input chết (#6)

`task_detail.html:470`'s "Ghi chú nhanh khi đóng task…" `<input>` has no `name`/`id`/JS wiring — text typed is discarded when "Ghi log & hoàn thành" opens M08. Fix: give it `id="s15-closebar-note"`, and wire the button that opens M08 (`hx-get="/modals/m08?...&task_id=..."` per `task_detail.html:472`) to append `&prefill_body=` with the input's (URL-encoded) current value — either via a small onclick JS reading the input before firing `htmx.ajax`, or by adding `hx-vals` referencing the input by id. `prefill_body` is already an accepted GET param on `/modals/m08` (confirmed in its signature) and already flows into the M08 form body field — no backend change needed, purely template/JS wiring.

### 5c. Claim feedback biến mất (#7)

`worklist_fragment.html:92`'s "Đã Claim" `<details class="wl-section">` has no `open` attribute (collapsed by default) vs. `:119`'s "Chưa Claim" which has `open`. A freshly-claimed task lands inside this collapsed section with zero visual feedback.

**Minimal required fix (do this first, ship it alone if scope needs to shrink)**: make "Đã Claim" `<details>` unconditionally `open`, same as "Chưa Claim" already is. One-line template change, no backend change, no new param — fully resolves "claim feedback biến mất" on its own (Scope & Complexity Critic finding: the original 3-call-site-param + inline-JS design below was more surface area than the bug needed).

**Optional enhancement, layer on top only if the minimal fix isn't enough** (per-row highlight + scroll-into-view for the SPECIFIC just-claimed row, not just "section is open"):
- Claim handler (`screen_worklist.py:473-524`, `_render_worklist_fragment` call at line 524) needs to thread a `highlight_task_id` (the newly-created/claimed task's id) into the fragment render context.
- Template: add a highlight class/`id` to the matching row when `t.task_id == highlight_task_id`.
- Simple scroll-into-view: append a small inline `<script>document.getElementById('claimed-row-' + <id>)?.scrollIntoView({block:'center'})</script>` at the end of the returned fragment (common htmx-swap pattern already implicitly compatible with this codebase's "full container outerHTML swap" style used elsewhere).
- If this optional layer is skipped, `_render_worklist_fragment`'s signature stays untouched — no new param, no non-claim-caller verification needed.

### 5d. Sau claim, đường vào cockpit dài ra (#8)

Claimed task rows currently only offer `contact_btn` (→ M08 quick-log) + title-link (→ S15) — no direct cockpit entry, vs. an unclaimed action row's 1-click `📞 Gọi` (→ `/customers/{pid}/call?queue_ids=...`). Fix: add a `📞` link on claimed task rows pointing to `/customers/{pid}/call?task_id={task_id}` (mirrors the existing S15 "Vào phiên gọi" → `S14?task_id=` pattern, i.e. `return_target`/pinned-task wiring in `screen_call_cockpit.py:181` already supports a `task_id` query param — reuse it, don't invent a new cockpit entry mode).

## Requirements

- 5a: worklist and cockpit Zalo/Facebook buttons open M08 pre-set to the correct channel tab/outcome-set; no behavior change for the existing call-channel default.
- 5b: text typed in the S15 closebar note survives into the M08 body field when "Ghi log & hoàn thành" is clicked; empty input → no change from today (empty `prefill_body`, already handled).
- 5c: claiming a task auto-expands "Đã Claim" and visually marks the new row (no full-page scroll-jump required, just enough to not "disappear").
- 5d: claimed task rows get a one-click cockpit entry identical in destination shape to S15's existing "Vào phiên gọi" link.

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` (GET `/modals/m08` handler + `_m08_ctx`, ~line 85-201)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` (`contact_btn` macro ~30-46: `channel=` → `hinh_thuc=`; claimed-row cockpit link addition per 5d)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (line 256: `hinh_thuc=chat` → `hinh_thuc=zalo`)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` (verify how the template currently selects its default channel tab/outcome-set — thread the new `hinh_thuc` context var into that selection)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/task_detail.html` (~line 470-473: closebar input `id` + prefill wiring)
- Modify: `crm/src/adapters/inbound/web/screen_worklist.py` (claim handler ~line 473-524: thread `highlight_task_id`)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` (Đã Claim `<details>` ~line 92: conditional `open` + highlight)
- Reference only: `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py:181` (`return_target`/`task_id` pinning, pattern to reuse for 5d)

## Implementation Steps

1. **5a**: add `hinh_thuc: str = Query(default="call")` to GET `/modals/m08`; read the current default-channel-selection logic in `modal_log_activity.html` (verify at implementation time exactly which template variable drives the initial tab/outcome-set — not fully traced during planning) and wire the new param into it. Change **all 4** `_wl_row.html` `contact_btn` variants (phone, zalo, facebook, no-identity-fallback) from `channel=...` to `hinh_thuc=call`/`hinh_thuc=zalo`/`hinh_thuc=fb`/`hinh_thuc=call` respectively — do not skip the phone/fallback variants, they currently send `channel=` too (verified, not "presumably fine"). Change cockpit line 256 from `hinh_thuc=chat` to `hinh_thuc=zalo`.
2. **5b**: add `id="s15-closebar-note"` (or `name`, whichever the wiring approach needs) to the input at `task_detail.html:470`. On the M08-opening button (`:472-473`), read the input's value and append it as `prefill_body` — either `hx-vals='js:{"prefill_body": document.getElementById("s15-closebar-note").value}'` or an `onclick` building the URL manually before `htmx.ajax`.
3. **5c minimal fix**: change `worklist_fragment.html:92`'s `<details class="wl-section">` to `<details class="wl-section" open>`, matching "Chưa Claim" — this alone resolves the finding. **5c optional enhancement** (only if pursuing per-row highlight): extend `_render_worklist_fragment(request, ...)` with an optional `highlight_task_id: Optional[str] = None` param; the claim handler passes the newly claimed task's id after `task_claim.claim_customer_actions(...)` returns it; add `id="claimed-row-{{ t.task_id }}"` and a highlight CSS class on the matching row when `t.task_id == highlight_task_id`.
4. **5d**: in the claimed-task-row branch of `_wl_row.html`, add a `📞` link `href="/customers/{{ t.party_id }}/call?task_id={{ t.task_id }}"` alongside the existing `contact_btn`/title-link.
5. Manual verify (UI change): claim a task from worklist → Đã Claim visible without expanding; click the new 📞 link → lands in cockpit with the task pinned (same as S15's existing "Vào phiên gọi"); worklist Zalo/Facebook/phone buttons open M08 on the right tab; S15 closebar note text survives into M08.

## Success Criteria

- [ ] 5a: worklist/cockpit Zalo and Facebook buttons open M08 with the correct channel pre-selected, verified against `_HT_TO_ACT_TYPE`/`CONTACT_OUTCOMES_BY_CHANNEL_TYPE` canonical keys.
- [ ] 5b: typed closebar note text appears in the M08 body field on open.
- [ ] 5c: newly claimed task visible without manually expanding Đã Claim.
- [ ] 5d: claimed task row → cockpit in 1 click, task pinned exactly as S15's existing link does.
- [ ] No regression to unclaimed action rows or S03's own M08/cockpit entry points.

## Risk Assessment

- **Risk (5a)**: `modal_log_activity.html`'s exact channel-selection mechanism wasn't traced to the line during planning — implementer must read it first; if it turns out to be driven by `activity.channel_type` (edit mode only) with no equivalent for "new log" mode, a small template addition (not just a context var) may be needed.
- **Risk (5c)**: only applies if the optional highlight enhancement is pursued — `_render_worklist_fragment` may be called from many non-claim endpoints (snooze, dismiss, etc.), adding an optional param is additive/safe as long as every other caller keeps passing `None`/omits it. The minimal `open`-attribute fix carries no such risk.
- **Rollback**: 4 independent sub-fixes across different files; each revertable without affecting the other 3.
