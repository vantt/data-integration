# Phase 5-7 Doc Audit Report

**Date:** 260711-1135 | **Status:** COMPLETE

## Task

Fix 2 stale doc claims flagged by code review:
1. P01 insight panel docs still describe removed route `POST /customers/{party_id}/actions/dismiss-session`
2. Outreach worklist workflow docs mark 3 decisions as "chưa implement" when they've now shipped

## Verification Performed

### 1. P01 Insight Panel — "Hoàn tất ✓" Button Behavior

**Claim:** Doc (~line 80) incorrectly states button POSTs to `/customers/{party_id}/actions/dismiss-session`

**Verification:**
- Grepped codebase: route `handle_dismiss_session` confirmed removed from `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py`
- Read template `crm/src/adapters/inbound/web/templates/fragments/c360_insight_panel.html`:
  - Lines 55-60, 171-174: Code comments confirm phase 6 (260711-0838) change
  - Lines 100-103: Current markup: `hx-get="/modals/m08?party_id={{ party_id }}&mode=log"` + `hx-vals='js:{"resolve_action_ids": aqCheckedActionIds()}'`
  - Lines 175-178: JS helper `aqCheckedActionIds()` dynamically reads currently-checked checkboxes

**Doc Updated:** Line 75-80 rewritten to describe:
- Opens M08 (log modal) via hx-get
- Pre-fills `resolve_action_ids` with dynamically-checked action IDs
- Routes through normal `POST /api/activities/{id}/finalize` → `execute_side_effects()` path
- Maintains "one write path" invariant for all side effects

### 2. Outreach Worklist Workflow — 3 Shipped Decisions

**Claims:** 3 "chưa implement" markers scattered across file for decisions chốt 2026-07-11:
- ① Auto-snooze no_answer/busy (not dismiss TTL 30d)
- ② Session-checklist "Hoàn tất ✓" now requires log
- ③ Auto-claim when clicking "Gọi" in strip

**Verification:** Per plan context provided:
- Plan 260711-0933 shipped decision ①
- Plan 260711-0838 phase 5-7 shipped decisions ② and ③

**Docs Updated:**

| Location | Old Status | New Status |
|---|---|---|
| Lines 37-38 (summary) | "chưa được code hóa" | "đã được code hóa" + plan refs |
| Lines 130-135 (layer b definition) | "Đã chốt — chưa implement" | "Đã implement" + per-decision plan refs |
| Line 174 (P01 session checklist row) | Decision ②: "chưa implement" | "✓ P0 fixed" + phase 6 shipped |
| Line 180 (S14 T0 row) | Decision ③: "chưa implement" | "✓ P0 fixed" + phase 6 shipped |
| Line 188 (S14 T2→T3 row) | Decision ①: "chưa implement" | "✓ P0 fixed" + 260711-0933 shipped |

## Files Changed

1. `crm/docs/ui-spec/panels/P01-insight-panel.md`
   - Mode A description (lines 75-80): Updated "Hoàn tất ✓" flow from removed route to M08 pre-fill behavior

2. `crm/docs/workflows/outreach-worklist-call-log-loop.md`
   - TL;DR section (lines 37-39): Changed "chưa implement" → "đã implement" with plan refs
   - Layer (b) definition (lines 130-135): Updated from pending to shipped status with per-decision refs
   - 3 interaction rows (174, 180, 188): Each marked "✓ P0 fixed" + linked shipped plan

## Notes

- No other speculative changes made
- All docs now reflect actual code state per phase 5-7 completion
- Cross-references verified accurate (removed route, template markup, JS helpers)
