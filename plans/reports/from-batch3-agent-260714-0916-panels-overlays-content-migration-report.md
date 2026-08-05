# Panels + Overlays `samples:`/`elements:` → `content:` migration

8 surfaces migrated per `ui-layout-authoring.md` §8b + §2b. All edits confined to the listed files' `yaml ui-layout` fences; `crm-contract` blocks untouched.

## P02 — Order History Panel

- Regions migrated: `toolbar`, `order_list`.
- `toolbar`: `h` title + `badge` cache freshness + `btn "Xem thêm →"` → A-P02-003.
- `order_list`: `table` (cols Mã đơn/Ngày/Giá trị/Trạng thái, rows: 4) — collection, per-idiom no per-row buttons.
- Contract gap: **A-P02-002** (`btn_log_activity_with_order`, region: toolbar, payload references `$order.order_code`) has no visual chip in old samples or new content. Region says `toolbar` but the payload implies per-order context — looks like a region-field inconsistency in the contract (should probably be `order_list`, or the button belongs to a per-row context not representable in `content:`). Left unmapped by design; not invented. Flag for follow-up, contract not edited.
- A-P02-001 (`order_row` click → tooltip) exempt: per-item row interaction, not representable per established idiom.

## P03 — Activity Timeline Panel

- Regions migrated: `toolbar`, `timeline`.
- `toolbar`: `h` + `btn "+ Ghi log"` → A-P03-001 + `select "Filter type"` (display-only by type, A-P03-002 stays in Interactions tab only).
- `timeline`: `list` (item = original sample line, rows: 4).
- A-P03-003 (`activity_chat_link`, per-item link inside chat-type timeline entries) exempt: per-item interaction, not representable.

## P04 — Tasks Panel

- Regions migrated: `toolbar`, `task_list`.
- `toolbar`: `h "Tasks"` + `btn "+ Tạo task"` (primary) → A-P04-001 + `select "Filter: open/all"`.
- `task_list`: `list` (item template, rows: 4) + representative action `row` below (pattern from canonical P01 rep_insights_block): Ghi log→A-P04-002, Xong nhanh→A-P04-003, Sửa→A-P04-004, Tạm hoãn→A-P04-005, Huỷ task→A-P04-006.
- Ambiguity resolved: original samples showed a `[···]` context-menu trigger fanning out to 3 actions (menu_edit/menu_postpone/menu_cancel). No single action ID exists for "open menu" itself, so instead of a dangling unmapped `btn`, the 3 reachable actions are surfaced directly as buttons (same idiom P01 uses for its per-item edit/invalidate buttons) — all 3 now mapped, none invented.
- A-P04-008 (`task_row` click → navigate S15) exempt: per-item row click, not representable.
- A-P04-007 (filter_status) via `select`, display-only by type — expected.

## P05 — Notes Panel

- Regions migrated: `toolbar`, `pinned_section`, `notes_list`.
- `toolbar`: `tabs` (Tất cả/★ Ưu tiên/⚠ Cảnh báo/📞 Liên lạc/Campaign, active="Tất cả") → single whole-bar action A-P05-004 (contract mapped all 5 labels to the same action, so whole-bar `action:` matches, not per-tab `actions:`) + `btn "+ Thêm ghi chú"` (primary) → A-P05-001.
- `pinned_section`: `list` (rows: 1) — display-only; contract scopes edit/delete/promote actions to `notes_list` only, so no action row added here (kept faithful to contract's region field).
- `notes_list`: `list` (rows: 3) + representative action row: ✎ Sửa→A-P05-002, ✗ Xóa→A-P05-003, ★ Đúc kết→A-P05-005.

## P06 — Conversations Panel

- Regions migrated: `toolbar`, `conv_list`.
- `toolbar`: `h` + `select "Filter: status"` (A-P06-002 stays Interactions-only, display-only by type).
- `conv_list`: `list` (rows: 3) + representative `row` with `btn "Xem →"` → A-P06-001 (per-item click on view button, surfaced representatively per P01 idiom).

## O01 — Confirm / Toast Overlay

- Regions migrated: `content`, `actions`.
- `content`: `text` (confirm message).
- `actions`: `btn "Hủy"` → A-O01-002, `btn "Xóa"` (primary) → A-O01-003.
- A-O01-001 (`overlay_backdrop` click → close) exempt: no visible affordance (backdrop click), same pattern as O03's scrim.

## O02 — Quick Customer Preview Overlay

- Regions migrated: `content`, `actions`.
- `content`: `h` name + `btn "✕"` → A-O02-002; `chips` (phone/GOLD/active); `text` (last purchase + affinity); `badge` (action-queue count) + `chips` (queue item codes).
- `actions`: `btn "Mở hồ sơ đầy đủ →"` (primary) → A-O02-003.
- A-O02-001 (`overlay_backdrop` click → close) exempt: same backdrop pattern as O01/O03.

## O03 — Postpone Task Overlay

- Regions migrated: `body`, `actions`.
- `body`: `text "Hoãn đến:"` + `input "27/06/2026"` + `input "14:30"` (matches prose: `<input type=date>` / `<input type=time>`).
- `actions`: `btn "Huỷ"` → A-O03-001, `btn "Xác nhận"` (primary) → A-O03-003.
- A-O03-002 (`scrim` click → close) exempt: no visible affordance.

## Verify summary

```
validate (pre-build):  0 errors, 8× VR-ASCII-DRIFT (expected, pre-build) + 1 stale-wireframe warn
build:                 8/40 surfaces' ASCII regenerated; chip-audit 225 tokens / 189 mapped / 36 unmapped (none in our 8 surfaces)
validate (post-build): 0 errors, 0 warnings
verify-runtime:        PASS — 54 surfaces exercised, 0 runtime errors
screenshot:             8/8 PNGs written to crm/docs/ui-spec/generated/screenshots/{P02,P03,P04,P05,P06,O01,O02,O03}.png
```

Vision spot-check (P02, P04, P05, O02 read directly): proportions correct, Vietnamese diacritics clean, tabs/table/list/chips render distinctly, no raw contract text leaking into the grid, no overflow.

Chip-audit confirmed via `generated/chip-audit.md`: none of P02/P03/P04/P05/P06/O01/O02/O03 appear under "## Unmapped Chips" — zero unmapped actionable across all 8.

## Ambiguities / contract gaps (no contract edits made)

1. **P02 A-P02-002** (`btn_log_activity_with_order`) — region says `toolbar`, payload references `$order.order_code` (implies per-row context). Left unrepresented in content rather than guessing placement.
2. **P04 `[···]` context-menu trigger** — no single action ID for "open menu"; resolved by surfacing its 3 destination actions (Sửa/Tạm hoãn/Huỷ task) directly as buttons instead of a dangling unmapped trigger. Flagging the reasoning, not a blocking issue.

Everything else was an unambiguous 1:1 samples-chip → contract-action carry-over, or a per-item/backdrop interaction correctly left out per the established idioms in §2b.

Status: DONE
Summary: All 8 panels/overlays migrated samples/elements → content; validate 0/0, verify-runtime PASS, 8 screenshots written, zero unmapped actionable in chip-audit for these surfaces.
Concerns/Blockers: none blocking — 2 minor contract-gap/ambiguity notes above for a human to review (P02 A-P02-002 region mismatch; P04 context-menu trigger has no dedicated action ID).
