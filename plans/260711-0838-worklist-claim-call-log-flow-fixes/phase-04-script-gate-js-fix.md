---
phase: 4
title: "Script-Gate JS Fix"
status: superseded
priority: P0
dependencies: []
---

# Phase 4: Script-Gate JS Fix

> **SUPERSEDED (2026-07-11)** — a parallel plan, `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-04-cockpit-js-unconditional.md`, covers this finding with a MORE thorough design: same 6-function relocation this file specifies, PLUS the stale-badge freshness IIFE (`#s14-trust-freshness`, also unconditionally rendered but missed here), PLUS an independent real bug found while reading the same code — `s14TagMultiSave` references a bare `S` variable (`S.draftId`) that throws `ReferenceError: S is not defined` unconditionally (not just when script-gated), since `S` only exists in the disposition-strip's own closure; fix is `window.S14_STRIP.draftId`. Treat the 0933 file as canonical/executable — it has exact current-line-number verified implementation steps. This file is kept for its research/evidence trail only.

## Overview

Finding #4 (report §II.4), ties to scenario ST-CALL-NO-SCRIPT. In `c360_call_cockpit_panel.html`, the Jinja block `{% if script and ap %}` (line 1342, closes ~1556/1559) wraps the `<script>` definitions of `s14ToggleReason`, `s14SetResolveId`, `s14CollectEnable`, `s14CollectSave`, `s14TagChipToggle`, `s14TagMultiSave` — but the HTML that calls these (rail primary/secondary "đã nói" checkboxes ~lines 574-687, collect-row list "Thu thập còn thiếu" ~lines 737-793) renders unconditionally, gated only on `rail_primary`/`collect_rows` being non-empty, not on `script`/`ap`. For a customer with no approach-script assigned, these onclick handlers reference undefined functions — silent JS failure, and the collect/reason UI (one of the flow's core "thu thập thông tin" goals) is dead on arrival.

Report's own fix note: "tách các hàm này ra block unconditional (như strip JS đã làm đúng)" — `s14StripSave` (line 1211) and `s14StripStartCall` (line 1059) already live in an earlier, unconditional `<script>` region (before the `{% if script and ap %}` block starts at 1342) — this is the pattern to match.

Functions that genuinely depend on script content (`s14SwitchChannel`, `s14CopyOpening`, `s14ToggleTP`, `s14ToggleObj`, `s14FilterObj`, `s14ClearObjSearch` — all about the approach-script rail's own talking-points/objections UI, which has nothing to render when `script` is `None`) correctly stay gated — do not move these.

## Requirements

- `s14ToggleReason`, `s14SetResolveId`, `s14CollectEnable`, `s14CollectSave`, `s14TagChipToggle`, `s14TagMultiSave` must be defined regardless of whether `script`/`ap` are truthy.
- No behavior change for customers WITH a script — these functions must still work identically after relocation.
- Script-specific functions (`s14SwitchChannel`, `s14CopyOpening`, `s14ToggleTP`, `s14ToggleObj`, `s14FilterObj`, `s14ClearObjSearch`) stay inside `{% if script and ap %}` — untouched.

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (relocate 6 function definitions from inside `{% if script and ap %}` (~line 1342-1556) to the unconditional script region above it, near `s14StripSave`/`s14StripStartCall`, ~line 1059-1211)

## Implementation Steps

1. Read the full current content of the 6 functions at their current locations (`s14ToggleReason` ~1438, `s14SetResolveId` ~1448, `s14CollectEnable` ~1462, `s14CollectSave` ~1469, `s14TagChipToggle` ~1501, `s14TagMultiSave` ~1515 — verify exact current line numbers first, they may have drifted since the verification pass).
2. Check each function body for any reference to script-only template variables (e.g. `ap.xxx`, `script.xxx` rendered inline via Jinja into the JS, not just DOM lookups) — if a function's body has Jinja-interpolated script data baked in, it cannot simply move; it would need those references converted to safe DOM/data-attribute reads first. Verify this during implementation before cutting/pasting.
3. Move the 6 function definitions verbatim to the unconditional script block (immediately after `s14StripSave`, before the `{% if script and ap %}` line), preserving their original order relative to each other.
4. Leave everything else inside `{% if script and ap %}` untouched.
5. Manually verify (per project's UI-change requirement) against a customer with `script=None`: rail "đã nói" checkboxes and "Thu thập còn thiếu" (zalo/email/sinh nhật/loại da/health…) rows now actually write when clicked, no `ReferenceError`/`undefined` in browser console.
6. Manually verify a customer WITH a script still behaves identically (regression check).

## Success Criteria

- [ ] No-script customer: clicking rail "đã nói" checkboxes and collect-row save buttons produces a real PATCH/POST (visible in network tab), no JS console error.
- [ ] Scripted customer: unchanged behavior, all script-rail features (switch channel, copy opening, toggle talking points/objections) still work.
- [ ] Existing S14 template/JS tests still pass; add a template-render test asserting the 6 function definitions appear in the rendered output when `script=None` (was previously absent).

## Risk Assessment

- **Risk**: if any of the 6 functions closes over a Jinja-rendered script-specific variable (not just DOM element ids), moving it outside the `{% if %}` could break because that variable is undefined when `script` is `None`. Mitigate via step 2's explicit check before moving — if found, the function needs a null-safe default for that variable rather than a pure cut/paste.
- **Rollback**: single-file template change, straightforward to move the 6 blocks back if a regression surfaces.
