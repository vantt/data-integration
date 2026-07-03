# Spec Gaps — Seven Controls Interactions Fix

**Date:** 2026-07-03  
**Branch:** feature/task-detail-cockpit-backend  

---

## Summary

Closed 6 spec files (covering 8 token-to-action mappings). Actions: 311 → 319 (+8). Mapped chips: 155 → 163 (+8). All verification gates passed clean.

---

## Changes Made

### 1. P02 — `Xem thêm →` (toolbar)

**File:** `crm/docs/ui-spec/panels/P02-order-history-panel.md`

Added `A-P02-003` (btn_load_more, click, mutate, effects: `[order_list.load_next_page, order_list.append_rows]`) and `"Xem thêm →": A-P02-003` to elements.

**Deviation:** The yaml crm-contract block was unclosed (no closing ` ``` ` fence). Inspection of the corpus revealed that crm-contract blocks in several other files (S07, S11, S14, S15, M13, M15) also lack closing fences — MarkdownIt treats EOF as block end. P02 was the only file I had to extend to EOF so I added a proper closing fence for cleanliness; this is harmless (MarkdownIt correctly terminates the block at ` ``` ` before EOF).

---

### 2. S07 — `Priority ▼`, `Status ▼`, `Party 🔍` (topbar)

**File:** `crm/docs/ui-spec/screens/S07-tasks-board.md`

Added:
- `A-S07-008`: filter_priority, change, mutate, `[board.reload_with_filters]`
- `A-S07-009`: filter_status, change, mutate, `[board.reload_with_filters]`
- `A-S07-010`: filter_party, change, mutate, `[board.reload_with_filters]`

And element mappings for all three.

**`Party 🔍` trigger decision:** The 🔍 emoji suggests a text search input. C02 uses `trigger: input` for its search_input, but C02 is a standalone component that emits events; it doesn't have direct `mutate` actions. Existing S07 filters (A-S07-005 filter_assignee, A-S07-006 filter_campaign) both use `trigger: change`. Using `change` for filter_party is consistent with the surface-local pattern. Deviation from C02's `input` trigger is justified by the filter-bar context (not a global search component).

---

### 3. S11 — `Kích hoạt` (topbar)

**File:** `crm/docs/ui-spec/screens/S11-campaign-detail-targets.md`

Added `A-S11-008` (btn_activate_campaign, click, guard: `campaign.status == 'draft'`, mutate, effects: `[campaign.status.set_active, topbar.activate_btn.hide, ui.toast.show]`).

**Confirmation pattern decision:** The task asked to check whether the corpus uses O01 confirm overlay for irreversible actions. Review of O01 purpose ("destructive nhỏ — xóa note, xóa custom field") and existing major-state-change interactions (A-S15-004 cancel task → direct mutate; A-S11-004 mark_skipped → direct mutate) shows **no pattern of O01 for activation/state-change actions** — O01 is reserved for delete confirmations. Used direct `mutate` with a guard. If a product-level decision is made to require confirmation for campaign activation (since it can't easily be reversed), a future change should add `open_overlay` → O01 here.

---

### 4. S15 — `← Quay lại` (header)

**File:** `crm/docs/ui-spec/screens/S15-task-detail.md`

Added `A-S15-011` (btn_back, click, navigate, target: S07).

**Back-target reasoning:** S15 Purpose states "P04 / S07 — hàng đợi / bảng, mở task → S15" and A-S07-002 (task_card click → navigate S15) is the explicit entry point. S07 is the primary back target. S15 can also be entered from P04 (Tasks Panel tab in S03) — in that case the browser history stack handles the contextual back correctly without a separate interaction. Noted in report only (no spec prose changed).

**Schema note:** The schema does not allow a `description` field on interactions. First attempt included a prose description field; removed after validation error.

---

### 5. M15 — `Hủy` (actions)

**File:** `crm/docs/ui-spec/modals/M15-edit-contact-core-info-modal.md`

Added `A-M15-008` (btn_cancel, click, close_overlay, target: return_to_invoker) and `"Hủy": A-M15-008` to elements.

**VR-MODAL-EXIT compliance:** M15 already satisfied VR-MODAL-EXIT-001 (close_overlay exists via A-M15-001) and VR-MODAL-EXIT-002 (return_to_invoker via A-M15-001). A-M15-008 is a second exit path; adding `target: return_to_invoker` is consistent with M13-002 (Hủy pattern) and maintains the rule.

---

### 6. M13 — `+ Thêm tùy chọn` (body)

**File:** `crm/docs/ui-spec/modals/M13-custom-field-def-modal.md`

Added `A-M13-005` (btn_add_option, click, mutate, effects: `[options_list.append_empty_row]`) and `"+ Thêm tùy chọn": A-M13-005` to elements.

---

## Verification Results

| Check | Result |
|---|---|
| `validate.mjs` — errors | 0 |
| `validate.mjs` — warnings | 0 |
| `build.mjs` | green (surfaces=54, actions=319, flows=6) |
| chip-audit mapped | **163** (was 155, +8) |
| chip-audit summary line | `Surfaces: 40 · Tokens: 286 · Mapped: 163 · Unmapped: 123` |
| Action count | **319** (was 311, +8) |
| `verify-runtime.mjs` | **PASS** — 0 errors |

---

## Unresolved Questions

1. **S11 `Kích hoạt` — confirmation UX:** No O01 confirm pattern exists for activation in this corpus, so direct mutate was used. If the product decision is that activating a campaign is high-stakes enough to require a "are you sure?" prompt, the action should be changed to `open_overlay` → O01 with appropriate confirm_type payload.

2. **S15 back-target contextual behaviour:** When S15 is entered from P04 (Tasks tab in S03), `btn_back` will navigate to S07 (hardcoded target). Browser history back() is the natural escape; the spec does not model per-entry-point routing. If a "return to S03 if entered from P04" requirement emerges, the target needs a dynamic/contextual navigation strategy (e.g., history.back() in the router, or a `source` query param).

3. **`Party 🔍` trigger vs `input`:** Used `change` to match the existing S07 filter pattern. If a debounced-on-keystroke UX is required (matching C02's `input` trigger), the trigger should be changed to `input` and the effects should include a debounce note.
