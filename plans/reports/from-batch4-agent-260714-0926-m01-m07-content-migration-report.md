# M01-M07 modals: samples/elements → typed content migration

Migrated 6 modal surfaces (M01, M02, M03, M04, M06, M07) from legacy `samples:`/`elements:` to typed `content:`, per ui-layout-authoring.md §8b + §2b. No contract (`crm-contract`) blocks touched.

## M01 — Merge Confirm Modal

- Regions migrated: `header`, `body`, `actions` (all 3 had samples).
- header: `h` + close `btn` (A-M01-001).
- body: 3 `text` lines (Party A / Party B / transfer counts), 1 `badge` (⚠ warning), 1 `text` (snapshot-undo note), 1 `checklist` for the confirm checkbox (left unchecked — matches "default: checkbox unchecked" in States; original sample showed it checked as an illustrative example, not the default state).
- actions: `Hủy` (A-M01-002), `Xác nhận Merge` primary (A-M01-003).
- All 3 actions mapped. No gaps.

## M02 — Create Party Modal

- Regions migrated: `header`, `body`, `actions`.
- header: `h` + close `btn` (A-M02-001).
- body: 4 label/`input` rows (Tên hiển thị, Số điện thoại, Email, Ghi chú nhanh) + 1 `text` warning line.
- actions: `Hủy` (A-M02-002), `Tạo khách` primary (A-M02-003).
- **Ambiguity**: `A-M02-004` (`phone_input`, trigger `blur`, normalizes phone to E.164) is a real interaction but not attached as `action:` on the `input` element — followed the established idiom from canonical M08 (select/input triggers stay documented in the contract only, not surfaced as a content `action:`, since `input`/`select` aren't in the actionable-type set and the renderer doesn't make them hoverable). Not a gap, just noting the pattern followed.

## M03 — Tag Management Modal

- Regions migrated: `header`, `body`, `actions`.
- header: `h` + close `btn` (A-M03-001).
- body: "Đang có:" label + 3 removable tag `btn`s sharing A-M03-003 (tag_remove_btn — correct per authoring rule: several elements may share one action), a search `input` + a `+ Tạo tag mới` `btn` (A-M03-007), and 4 "add tag" `btn`s sharing A-M03-004.
- actions: `Đóng` (A-M03-002), `Lưu` primary (A-M03-005).
- **Ambiguity**: the "+ Tạo tag mới" button (A-M03-007, `open_overlay` → M14) has no literal chip text in the old `samples:` line — it's implied by the search placeholder "Tìm hoặc tạo tag mới...". I added an explicit `+ Tạo tag mới` btn next to the search input to represent it, since the contract clearly defines the interaction and the placeholder text implies the affordance. Flagging this label as inferred, not sourced verbatim from the original sample line.
- `A-M03-006` (`tag_search_input`, trigger `input`, filters tag list) intentionally left without `action:` on the `input` element — same established idiom as M02.
- All actionable (`btn`) elements mapped; chip-audit confirms M03 has zero unmapped entries.

## M04 — Assign Owner Modal

- Regions migrated: `header`, `body`, `actions`.
- header: `h` + close `btn` (A-M04-001).
- body: current-owner `text`, a `select` for "Chọn NV mới", and a `checklist` standing in for the radio-button owner list (○ NV A / NV B / CSKH B / Manager C) — `checklist` is the closest existing primitive since there's no dedicated radio type; "NV A (hiện tại)" rendered as the checked item to convey current selection. No action attached to the radio-style list because per-option selection has no distinct action ID (only `selected_user_id` state feeds the Save guard).
- actions: `Hủy` (A-M04-002), `Lưu` primary (A-M04-003).
- No unmapped actionable elements; no contract gaps.

## M06 — Custom Fields Edit Modal

- Regions migrated: `header`, `body`, `actions`.
- header: `h` + close `btn` (A-M06-001).
- body: 3 sections (Sức khoẻ & Da liễu / Nguồn & Marketing / Nội bộ) rendered as `h` headings separated by `divider: true`, each with label + `chips`/`select`/`input` rows matching the field types implied by the sample (boolean toggle as display-only `chips`, select for dropdown fields, input for free text/date).
- actions: `Hủy` (A-M06-002), `Lưu` primary (A-M06-003).
- Note: this modal renders dynamically from `crm_custom_field_def` (see Render Rules) — the content block models one realistic instance, consistent with the existing samples-line approach; no schema change implied.

## M07 — Create / Edit Campaign Modal

- Regions migrated: `header`, `body`, `actions`.
- header: `h` + close `btn` (A-M07-001).
- body: 6 label/field rows (Tên chiến dịch, Mục tiêu, Kênh, Segment, Giao cho, Ngày bắt đầu) using `input`/`select` per field type, plus a `text` line for the segment-size preview ("→ 34 khách (3 bị loại consent)").
- actions: `Hủy` (A-M07-002), `Tạo & Kích hoạt` primary (A-M07-004).
- **Ambiguity**: `A-M07-003` (`segment_select`, trigger `change`, reloads target preview) intentionally left without `action:` on the `select` element — same established idiom as M02/M03 (change-triggered mutate actions on non-btn/tabs elements stay contract-only, matching canonical M08's `hinh_thuc_select`).

## Verify summary

```
node validate.mjs --root crm/docs/ui-spec        → 0 errors, 7 VR-ASCII-DRIFT/stale warnings (expected pre-build)
node build.mjs --root crm/docs/ui-spec           → ascii regenerated for all 6 files; chip-audit: 208 tokens, 190 mapped, 18 unmapped (all 18 in M09/M10/M11/M12/M13/M14 — none in scope)
node validate.mjs --root crm/docs/ui-spec        → 0 errors, 0 warnings
node verify-runtime.mjs --root crm/docs/ui-spec  → PASS, 0 runtime errors, 54 surfaces / 6 flows exercised
node screenshot.mjs --surface M01,M02,M03,M04,M06,M07 --width 1920 --height 2100 → 6/6 PNGs written to crm/docs/ui-spec/generated/screenshots/
```

Visual QA (read all 6 PNGs): proportions correct (single-column modal, 560px), sample content dominant over muted region labels, buttons/inputs/badges/chips/dividers render as distinct shapes, close (✕) button present and mapped on all 6 headers, Vietnamese diacritics clean (no tofu/mojibake), no horizontal overflow, Contract Inspector panel present and not cramping the grid.

## Acceptance checklist

- Every region that had a `samples:` line now has `content:`; `samples:`/`elements:` deleted in the same edit — done for all 6 files.
- validate 0/0 post-build — confirmed.
- verify-runtime PASS — confirmed.
- Chip-audit: zero unmapped actionable in M01/M02/M03/M04/M06/M07 — confirmed (unmapped list only contains M09-M14).
- 6 screenshots written — confirmed.
- Close (✕) button mapped to `close_overlay` on all 6 — confirmed (A-M01-001, A-M02-001, A-M03-001, A-M04-001, A-M06-001, A-M07-001 all have `action: close_overlay, target: return_to_invoker` in their contract blocks — contract blocks untouched, verified by re-reading each file's Interactions section pre-edit).

## Unresolved questions

1. M03's "+ Tạo tag mới" button label/placement is inferred from the search-input placeholder text, not from an explicit chip in the old `samples:` line — worth a human eyeball to confirm the label matches actual UI copy.
2. M04's radio-style NV picker modeled via `checklist` (no dedicated radio primitive exists in the schema) — acceptable approximation, flagging in case a future radio-group primitive is added to `layout-schema.mjs`.

Status: DONE
Summary: All 6 modals migrated to typed `content:`, validate 0/0, verify-runtime PASS, chip-audit clean for these surfaces, 6 screenshots written and visually reviewed.
Concerns/Blockers: none blocking; see 2 unresolved questions above (minor, non-blocking).
