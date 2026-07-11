---
phase: 1
title: "Redirect Context-Loss Fix"
status: superseded
priority: P0
dependencies: []
---

# Phase 1: Redirect Context-Loss Fix

> **SUPERSEDED (2026-07-11)** — a parallel plan, `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-01-modal-return-to-invoker.md`, covers this finding with a BETTER design: an independent `return_to` field (default `"redirect"` | `"stay"`) that never touches the `source == "call_cockpit"` branch at all — sidestepping the dead-code trap this file's revision below had to work around (that branch renders `onclick="s14OpenOutcome(...)"`, a function already deleted by the shipped disposition-strip-v2 migration; `test_disposition_strip_v2.py:294-306` forbids its reappearance). The 0933 file also covers `patch_task_edit` (M05 edit/"Dời hạn" flow), which this file explicitly left out of scope. 2 additional gaps found during this file's red-team review were ported forward as amendments to the 0933 file: the `s14StripOpenDetail`/`edit_activity`-mode call site's fix is a no-op there too (needs `handle_patch_activity` itself updated, not just the GET call site), and the worklist-header no-party M05 flow likely 404s pre-existing. Treat the 0933 file (with its amendments) as canonical/executable. This file's revision below is kept for its research/evidence trail only — do not implement from here.

## Overview

Finding #1 (report §II.1). `POST /customers/{pid}/tasks` (M05) and `POST /customers/{pid}/log-activity` (M08) both unconditionally return `HX-Redirect`, yanking staff out of S14 cockpit or S01 worklist back to S03 whenever those screens open M05/M08 as a side panel. Fix: redirect only when the modal was opened from S03 itself; when opened from cockpit or worklist, close the modal in place (empty swap, no redirect) and let the caller refresh only its own region.

Reuses mechanisms already in the codebase instead of inventing new ones:
- `modal_m16_promote_insight.html:46` already uses `hx-on::after-request="document.body.dispatchEvent(new Event('insightSaved'))"` to fire a body event after a modal save without navigating — same pattern for M05's `taskSaved` and M08's `activitySaved`.
- `worklist_fragment.html:19-23` / `worklist.html:34-38` already have `<div id="worklist-container" hx-get="/worklist/fragment" hx-trigger="claimSuccess from:body" ...>` (currently dead — `claimSuccess` is never emitted) → extend the `hx-trigger` list rather than adding a new container/route.

**Revised after red-team review (2026-07-11) — 2 corrections to the original design, see `## Red Team Review` in plan.md for full findings:**
- **M08's `source == "call_cockpit"` branch is NOT safe reusable dead code** (original plan's premise) — it's a leftover confirmation fragment from a design predating the shipped disposition-strip-v2 migration (`plans/260710-1338-activity-log-disposition-api`). It renders `onclick="s14OpenOutcome(...)"`, a function that migration deliberately deleted — `crm/src/tests/test_disposition_strip_v2.py:294-306` (`TestOldOutcomeBarFullyRemoved::test_old_identifiers_gone_from_template`) explicitly asserts `s14OpenOutcome(` is **absent** from the template. Making this branch reachable would ship a fragment whose only interactive element throws `ReferenceError`. **Fix: this branch must be changed to return empty content (`HTMLResponse(content="")`), same shape as the new `source == "worklist"` case, NOT left as-is.** The existing test `test_call_cockpit_source_returns_fragment_no_redirect` (`crm/src/tests/test_quick_outcome_cockpit_post.py:92-111`) currently asserts the old `s14-outcome__done`/`Hoàn tác` fragment is returned for this branch — that assertion must be rewritten to expect empty content instead, as part of this same change (not left green-but-wrong).
- **One naming decision**: use a single param name, `source`, for BOTH M05 and M08 (not `caller` for M05 + `source` for M08) — M08 already precedent-sets `source` (pre-existing, if currently unwired), so M05 adopts the same name rather than inventing a second one for the identical concept.

## Requirements

- M05/M08 opened from **S03 itself** (customer_360.html) → unchanged: `HX-Redirect` as today.
- M05/M08 opened from **S14 cockpit** (rail "Đặt lịch"/"Tạo task xác minh", idbar "Tạo task", M08 fallback **log** opens only — see file-list note on `s14StripOpenDetail`) → close modal in place (empty content, no redirect), cockpit page does not navigate.
- M05 opened from **S01 worklist header** ("+ Tạo task", no party_id) → close modal in place, worklist refetches itself via a new `taskSaved` event. **Descoped**: this specific call site is currently believed broken independent of this fix (see Risk Assessment) — implement the `source=worklist` wiring regardless, but do not block this phase on making the no-party POST itself succeed; that is a separate, pre-existing bug.
- M08 opened from **S01 worklist claimed-task row** (`contact_btn` macro, `_wl_row.html`) → close modal in place, worklist refetches itself via a new `activitySaved` event.
- S15 `task_detail.html:472`'s M08 call site is OUT OF SCOPE (report doesn't list it as broken) — leave its default (S03-style) redirect behavior untouched.
- `_wl_row.html:288` M05 "edit task" call site is OUT OF SCOPE (not cited by report finding #1) — leave untouched (falls through to default redirect branch, safe no-op).

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py` (GET `/modals/m05` ~line 39-48, POST `/customers/{party_id}/tasks` ~line 141-184)
- Modify: `crm/src/adapters/inbound/web/screens/modals/screen_modal_shared.py` (`redirect_to_customer` helper ~line 36-38 — leave as-is, just stop calling it unconditionally)
- Modify: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` (GET `/modals/m08` handler ~line 182-201 and its `_m08_ctx` closure ~line 85-97, POST `/customers/{party_id}/log-activity` ~line 221-390, specifically the `source == "call_cockpit"` branch ~line 375)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html` (create-task form ~line 41 — add hidden `source` field + `hx-on::after-request`)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` (form ~line 110 — add hidden `source` field + `hx-on::after-request`)
- Modify: `crm/src/adapters/inbound/web/templates/worklist.html` (header "+ Tạo task" ~line 26-28 → add `&source=worklist`; `hx-trigger` on worklist-container ~line 34-38)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` (`hx-trigger` on worklist-container ~line 19-23)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` (`contact_btn` macro, 4 call sites ~line 30/35/40/45 → add `&source=worklist`. **Also touched by Phase 5a** in the same 4 lines — this phase must land first, Phase 5a rebases its `channel=`→`hinh_thuc=` rename on top of this phase's output rather than editing independently.)
- Modify: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (M05 call sites ~line 262, 312-313, 619, 666 → add `&source=s14`; M08 **log-mode** fallback call sites ~line 256, 1075, 1081 → add `&source=call_cockpit`. **Do NOT touch line ~1088** (`s14StripOpenDetail`, `mode=edit_activity`) — that call site PATCHes `/api/activities/{activity_id}` via `handle_patch_activity`, a different route entirely that never reads `source`; appending the param there is inert. Verify current line numbers before editing, they may have drifted.)
- Modify: `crm/src/tests/test_quick_outcome_cockpit_post.py` (`test_call_cockpit_source_returns_fragment_no_redirect` ~line 92-111 — rewrite assertion to expect empty content, not the old `s14-outcome__done` fragment; `test_unknown_source_keeps_hx_redirect` ~line 152-166 — its docstring "Only the exact 'call_cockpit' marker skips the redirect" becomes inaccurate once `source=="worklist"` also skips it; update the docstring and add an explicit `source="worklist"` no-redirect test case alongside it)

## Implementation Steps

1. **M05 GET handler** (`screen_modal_task.py`): add `source: str = Query(default="")` to the `/modals/m05` GET signature; pass through to the `modal_m05_create_task.html` render context.
2. **M05 template**: add `<input type="hidden" name="source" value="{{ source }}">` inside the `hx-post="/customers/{{ party_id }}/tasks"` form (~line 41) — check first whether this form already has a hidden `source`/`source_ref` field for task-provenance purposes (per Phase 3's `create_task` source semantics); if so, this is a DIFFERENT field serving a different purpose (caller-context vs. task-provenance) and needs a distinct field name (e.g. `caller_source`) to avoid colliding with the existing one — verify at implementation time, do not assume no collision. Add `hx-on::after-request="if(event.detail.successful) document.body.dispatchEvent(new Event('taskSaved'))"` on the same `<form>` tag (unconditional dispatch is safe — `#worklist-container` only exists in the DOM on the worklist page, so the event is inert everywhere else).
3. **M05 POST handler** (`screen_modal_task.py:141-184`): add the new caller-context param (name per step 2's collision check) `: str = Form(default="")`. Replace the unconditional `return redirect_to_customer(party_id)` (line 184) with: `if <param>.strip() in ("s01", "s14"): return HTMLResponse(content="")` else keep existing `return redirect_to_customer(party_id)`.
4. **Cockpit M05 call sites** (`c360_call_cockpit_panel.html:262,312-313,619,666`): append `&source=s14` (or `&caller_source=s14` if step 2 found a naming collision) to each `hx-get`/`htmx.ajax` URL.
5. **Worklist header M05 call site** (`worklist.html:26-28`): append `&source=worklist` (or `&caller_source=worklist`).
6. **M08 GET handler** (`screen_customer_360_activity.py`, `_m08_ctx` closure + the `/modals/m08` route): add `source: str = Query(default="")` to the GET signature (currently only the POST accepts `source`), thread into `modal_log_activity.html` render context.
7. **M08 template** (`modal_log_activity.html:110` area): add `<input type="hidden" name="source" value="{{ source }}">` inside the form. Add `hx-on::after-request="if(event.detail.successful) document.body.dispatchEvent(new Event('activitySaved'))"` on the same `<form>` tag.
8. **M08 POST handler** (`screen_customer_360_activity.py:375` area): change the existing `if source.strip() == "call_cockpit":` branch's return from the old `s14-outcome__done`/`s14OpenOutcome` fragment to `return HTMLResponse(content="")` — **this is a behavior change to existing code, not a no-op reactivation** (see Overview correction). Add a new `elif source.strip() == "worklist": return HTMLResponse(content="")` branch immediately after it, before the default `HX-Redirect` fallback.
9. **Cockpit M08 log-mode fallback call sites** (`c360_call_cockpit_panel.html:256,1075,1081` — verify current numbers, NOT line ~1088): append `&source=call_cockpit` to each.
10. **Worklist `contact_btn` macro** (`_wl_row.html:30/35/40/45`): append `&source=worklist` to each of the 4 channel variants.
11. **Worklist-container triggers** (`worklist_fragment.html:19-23`, `worklist.html:34-38`): change `hx-trigger="claimSuccess from:body"` → `hx-trigger="taskSaved from:body, activitySaved from:body"` — do NOT add `claimSuccess` to this list (see Phase 7 #12: wiring `claimSuccess` here too was considered and rejected — the claim button already re-renders this exact container directly, so also listening for `claimSuccess` would double-fetch on every claim; drop the dead `claimSuccess` clause entirely rather than resurrect it).
12. **Descoped, not fixed by this phase**: the worklist header "no party" M05 flow (`hx-post="/customers//tasks"` when `party_id` is empty) is very likely a pre-existing 404 — `modal_m05_create_task.html`'s customer field renders `disabled` with no picker when `party_id` is empty, and FastAPI's default path-parameter matching does not match an empty segment. Wire `source=worklist` through this call site regardless (step 5) so the fix is in place IF/WHEN the routing bug is separately fixed, but do not attempt to fix the routing itself here — that's a distinct pre-existing bug (party-less task creation may need to target the separate `POST /tasks` route at `screen_tasks_board.py:131` instead), out of this UX-redirect-focused phase's scope. Flag it to the user as a known gap, do not silently claim it works.
13. Update the 2 existing tests per the file-list note above (`test_call_cockpit_source_returns_fragment_no_redirect` new assertion; `test_unknown_source_keeps_hx_redirect` docstring + new `source="worklist"` case).

## Success Criteria

- [ ] Cockpit "Đặt lịch"/"Tạo task" → task created, cockpit stays on S14, no navigation, call draft/timer/queue_ids untouched.
- [ ] Cockpit M08 log-mode fallback → activity saved, cockpit stays on S14, no `ReferenceError` in console (verifies the old dead fragment is truly gone, not just unreachable).
- [ ] Cockpit M08 edit-mode (`s14StripOpenDetail`) — unchanged behavior, regression-check only (explicitly not touched by this phase).
- [ ] Worklist claimed-task row 📞/💬/📘 quick-log (M08) → activity saved, stays on worklist, filter/scroll/band-expand state preserved (no full page reload).
- [ ] S03 M05/M08 (unchanged path, no `source` param) → still redirects to `/customers/{pid}` / `/customers/{pid}?tab=timeline` exactly as today.
- [ ] S15 M08 call site behavior unchanged (out of scope, regression-check only).
- [ ] Worklist header "+ Tạo task" — `source=worklist` wired through; task-creation success itself is EXPLICITLY NOT a pass/fail criterion of this phase (known pre-existing gap, see Implementation Step 12) — report actual behavior observed, don't assume.
- [ ] Existing tests covering M05/M08 redirect behavior still pass (with the 2 rewritten per step 13); new tests added for the `source=s14`/`source=worklist` no-redirect branches and for `taskSaved`/`activitySaved` triggering the worklist refetch.

## Risk Assessment

- **Risk**: forgetting a call site (e.g. a future new M05/M08 opener) silently falls through to the safe default (redirect to S03) — not a regression, just doesn't get the fix. Acceptable.
- **Risk**: `hx-on::after-request` firing unconditionally (even on the S03-redirect path) is harmless because `HX-Redirect` triggers full navigation before any in-page JS/event listener on the now-unloading page matters — verify this ordering holds in htmx during implementation (htmx processes `HX-Redirect` via `window.location`, which does not block synchronous `after-request` handlers from firing first, but the destination page won't have `#worklist-container` in scope so it's inert either way).
- **Risk (confirmed by red-team, not hypothetical)**: the worklist-header no-party M05 flow is very likely already broken (404) independent of this plan — do not let this phase's success criteria imply it's fixed. Surface the actual observed behavior to the user rather than silently passing/failing on it.
- **Rollback**: each modified file is an independent, additive change (new param + new branch; the one non-additive change — the `call_cockpit` branch's return value — is isolated to a single `elif`/return statement) — revertable file-by-file without touching the others.
