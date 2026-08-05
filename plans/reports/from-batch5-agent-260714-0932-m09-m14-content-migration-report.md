# M09-M14 content: migration report

Task: migrate final 6 modal surfaces (M09-M14) from legacy `samples:`/`elements:` to typed `content:`, per ui-layout-authoring.md §8b + §2b.

## Per-surface summary

### M09 — Assign Conversation Modal
- Regions migrated: header, body, actions (all 3; no floating/variants).
- Radio-style assignee picker ("○ CSKH A · ● CSKH B (hiện tại) · ○ CSKH C") modeled as `checklist` — direct precedent from M04-assign-owner-modal.md (identical shape: current-value text + label/select row + checklist of options).
- Actions mapped: A-M09-001 (✕ close, header), A-M09-002 (Hủy, actions), A-M09-003 (Gán, actions, primary, guard `selected_user_id != null`).
- No contract gaps.

### M10 — Close Conversation Modal
- Regions migrated: header, body, actions.
- Body: `text` label + `input` (outcome notes placeholder) + single-item `checklist` for the "Ghi vào activity timeline" checkbox (checked by default per States section).
- Actions mapped: A-M10-001 (✕), A-M10-002 (Hủy), A-M10-003 (Đóng hội thoại, primary).
- No contract gaps.

### M11 — Link Party to Conversation Modal
- Regions migrated: header, body, actions.
- Search box → `input` (no `action:`, matching M03-tag-management-modal.md precedent where `tag_search_input`/A-M03-006 exists in the contract but the `input` type stays unmapped since input isn't an actionable type — search-as-you-type contract remains visible via region hover).
- Two sample result rows → `list: { item, rows: 2 }`. Per-row click (A-M11-004 `party_result_row`) intentionally NOT attached to the list per the established idiom (collections are display-only skeletons; item-level contract stays in region hover / Interactions tab).
- "+ Tạo khách mới" → `btn` action A-M11-006 (open_overlay → M02).
- Actions mapped: A-M11-001 (✕), A-M11-002 (Hủy), A-M11-005 (Gắn khách đã chọn, primary, guard), A-M11-006 (+ Tạo khách mới).
- Unmapped-by-design (not a gap): A-M11-003 (search_input, trigger=input) and A-M11-004 (party_result_row, trigger=click on list rows) — both covered by input/list being non-actionable types per §2b; contract remains inspectable via region hover.

### M12 — Record Conversion Modal
- Regions migrated: header, body, actions.
- Order-code field → `row: [text, input]`; computed-revenue line → `text`; manual-entry toggle → single-item `checklist` (checked in the sample, matching the "Đơn chưa có" example already shown checked in the old samples line); manual revenue field → `row: [text, input]`.
- Actions mapped: A-M12-001 (✕), A-M12-002 (Hủy), A-M12-004 (Ghi nhận, primary, guard).
- Unmapped-by-design: A-M12-003 (order_code_input, trigger=blur) — `input` type is non-actionable per registry; same pattern as M08's `hinh_thuc_select`/`content_input` fields that carry no `action:` even though a contract interaction exists on that element.

### M13 — Custom Field Definition Modal
- Regions migrated: header, body, actions.
- Full form: `checklist` for entity_type radio (Khách hàng/Đơn hàng), `input` rows for field_name/display_label/section/sort_order, `select` for data_type, `checklist` for required radio (Có/Không), `btn` for "+ Thêm tùy chọn" (A-M13-005).
- Actions mapped: A-M13-001 (✕), A-M13-002 (Hủy), A-M13-004 (Lưu, primary, guard), A-M13-005 (+ Thêm tùy chọn).
- Unmapped-by-design: A-M13-003 (data_type_select, trigger=change) — `select` isn't an actionable type; no precedent in the corpus (grepped) for attaching `action:` to `select`, so left unmapped like M08's `hinh_thuc_select`. Contract remains visible via region hover.

### M14 — Create Tag Modal
- Regions migrated: header, body, actions.
- Form: `row: [text, input]` for name/label, `row: [text, select]` for category, `checklist` for the optional color radio (Xanh/Đỏ/Vàng).
- Actions mapped: A-M14-001 (✕), A-M14-002 (Hủy), A-M14-003 (Tạo tag, primary, guard).
- No contract gaps.

## Ambiguities encountered

- **Select vs. checklist for radio pickers**: several bodies show a dropdown-looking field alongside a separate `○/●` radio list of the *same* choice set (e.g. M09's "Gán cho [CSKH B ▼]" plus the CSKH A/B/C radio list below it). Followed the M04 precedent literally: kept both the `select` (current value display) and the `checklist` (full option enumeration) as separate lines rather than collapsing them — this duplicates the option set visually but matches the only established precedent in the corpus (M04) exactly, so did not deviate.
- **Whether `select`/`input` should carry `action:`**: several contract interactions target select/input elements (data_type_select change, order_code_input blur, search_input input). Per `layout-schema.mjs` `CONTENT_TYPES`, only `btn`/`tabs` are marked `actionable: true`; other types can technically carry `action:` (validator doesn't forbid it) but no surface in the corpus does this. Left these unmapped, consistent with M03/M08 precedent, and documented as "unmapped-by-design" above rather than a gap — the underlying contract interaction still exists and is inspectable via region hover, nothing was lost.

## Contract gaps

None. All 6 surfaces' `crm-contract` blocks already covered every real button; no missing interactions, no invented action IDs.

## Verify summary

```
validate.mjs (pre-build):  0 errors, 7 warnings (VR-ASCII-DRIFT ×6 + stale wireframe — expected pre-build)
build.mjs:                 ascii regenerated 6/40 surfaces; chip-audit 190 tokens · 190 mapped · 0 unmapped
validate.mjs (post-build): 0 errors, 0 warnings
verify-runtime.mjs:        PASS — 54 surfaces exercised, 6 flows, 0 errors
screenshot.mjs:            6/6 written (M09-M14, 1920x2100) — visually reviewed, all clean:
                            Vietnamese diacritics render correctly, no mojibake, no chip overflow,
                            primary/secondary buttons visually distinct, ✕ mapped in every header,
                            checklists render with correct checked/unchecked state.
```

`grep -rl "^samples:" crm/docs/ui-spec/screens crm/docs/ui-spec/modals crm/docs/ui-spec/panels crm/docs/ui-spec/overlays` → **no matches** (exit 1). The `samples:`/`elements:` → `content:` migration is complete corpus-wide.

Final corpus totals (generated/chip-audit.md): **Surfaces: 40 · Tokens: 190 · Mapped: 190 · Unmapped: 0** — all chips mapped, no gaps found anywhere in the corpus.

Close (✕) control confirmed mapped to `close_overlay` / `return_to_invoker` in all 6 modals.

Status: DONE
Summary: All 6 modals (M09-M14) migrated to typed `content:`; validate 0/0, verify-runtime PASS, 6/6 screenshots clean, corpus-wide `samples:` grep returns nothing, chip-audit final totals 190/190 mapped/0 unmapped.
Concerns/Blockers: none — two documented ambiguities above (select-vs-checklist duplication in M09, select/input non-actionable-by-registry) were resolved by following the nearest established precedent (M04, M03/M08) rather than guessing.
