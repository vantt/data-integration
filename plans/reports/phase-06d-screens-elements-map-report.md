# Phase 06d — Screens Elements Map Report

**Date:** 2026-07-03  
**Files owned:** S01–S13, S15 (14 files; S14 was canonical reference)  
**Validator result:** `✓ validation passed` — 0 VR-ELEMENT-REF warnings in owned files

---

## Per-File Summary

| File | Tokens found | Mapped | Skipped |
|------|-------------|--------|---------|
| S01 | 17 | 7 | 10 |
| S02 | 8 | 7 | 1 |
| S03 | 13 | 6 | 7 |
| S04 | 4 | 4 | 0 |
| S05 | 3 | 3 | 0 |
| S06 | 8 | 6 | 2 |
| S07 | 8 | 4 | 4 |
| S08 | 2 | 2 | 0 |
| S09 | 7 | 5 | 2 |
| S10 | 2 | 2 | 0 |
| S11 | 4 | 3 | 1 |
| S12 | 2 | 2 | 0 |
| S13 | 3 | 2 | 1 |
| S15 | 16 | 8 | 8 |
| **Total** | **101** | **61** | **40** |

---

## Per-File Details

### S01 — Worklist Dashboard
7 tokens found / 7 mapped / 10 skipped

Mapped:
- `Làm mới ↺` → A-S01-020
- `+ Tạo task` → A-S01-004
- `✅ Ẩn đã liên hệ` → A-S01-013
- `📋 Có kịch bản` → A-S01-010
- `Dời hạn` → A-S01-019
- `Dọn` → A-S01-018
- `📞 Gọi` → A-S01-007

Skipped:
- `≡` — sidebar toggle; no interaction ID
- `↕` (×3) — same chip text appears in 3 filter positions (Ưu tiên/Loại/Sản phẩm); per-surface ambiguity
- KPI strip chips (` Task mở: N `, ` Hành động AQ: N `, ` Giá trị: Ntr `, ` Khẩn: N `) — display-only metric boxes
- `💰 Giá trị cao` — ambiguous between A-S01-015 (filter_min_value) and A-S01-022 (filter_value_group)
- `P1` — display priority badge
- `Mở hồ sơ >` — no dedicated button interaction (A-S01-001 is the whole row click)

### S02 — Customer List & Search
8 tokens found / 7 mapped / 1 skipped

Mapped:
- `Value Group ▼` → A-S02-003
- `Status ▼` → A-S02-004
- `Owner ▼` → A-S02-005
- `Tag ▼` → A-S02-006
- `+ Tạo mới` → A-S02-002
- `< Trước` → A-S02-008
- `Sau >` → A-S02-007

Skipped:
- `🔍 SĐT / Tên / Email...` — C02 global search component; handled via LSN events, no direct element interaction ID

### S03 — Customer 360 Detail
13 tokens found / 6 mapped / 7 skipped

Mapped:
- `← Quay lại` → A-S03-001
- `Gán NV ▼` → A-S03-002
- `+ Tag` → A-S03-003
- `Ghi log` → A-S03-011
- `Tạo task` → A-S03-012
- `+` → A-S03-013 (sidebar.contact add contact)

Skipped:
- `Value & Behavior | Ghi chú | Đơn | Timeline | Tasks | Chat | Gọi` — entire tab bar as single chip maps to 7 interactions; one-chip-to-one-action rule
- `GOLD`, `active` — display badges
- `✎` — appears in both sidebar.core_info (→ A-S03-015) and sidebar.tags (→ A-S03-017); same chip text, different regions, different targets; per-surface ambiguity rule
- `VIP`, `repeat` — display tag chips

### S04 — Dedup Review
4 tokens / 4 mapped / 0 skipped

Mapped:
- `Filter: match_rule ▼` → A-S04-007
- `Merge A←B` → A-S04-002
- `Reject` → A-S04-003
- `Bỏ qua` → A-S04-004

### S05 — Inbox
3 tokens / 3 mapped / 0 skipped

Mapped:
- `All ▼` → A-S05-003 (filter_assignee; "All" is default state, contrast with "Gán cho tôi")
- `Open | Pending | Closed` → A-S05-002 (filter_status segmented button)
- `Gán cho tôi` → A-S05-004

### S06 — Conversation Detail
8 tokens / 6 mapped / 2 skipped

Mapped:
- `← Inbox` → A-S06-001
- `Đổi NV` → A-S06-004
- `Đóng hội thoại` → A-S06-002
- `Ghi note` → A-S06-003
- `Mở hồ sơ đầy` → A-S06-006
- `Chưa link khách → 🔍 Tìm khách` → A-S06-005

Skipped:
- `Khách`, `NV` — message-sender display labels inside message_thread, not interactive chips

### S07 — Tasks Board
8 tokens / 4 mapped / 4 skipped

Mapped:
- `+ Tạo task` → A-S07-001
- `Assignee ▼` → A-S07-005
- `Campaign ▼` → A-S07-006
- `List|Board` → A-S07-007

Skipped:
- `Priority ▼` — no filter_priority interaction defined in S07 contract
- `Party 🔍` — no filter_party interaction defined in S07 contract
- `Status ▼` — no filter_status interaction defined in S07 contract (only filter_assignee + filter_campaign + toggle_view)
- `AUTO` — display badge (auto-generated task label)

### S08 — Segments List
2 tokens / 2 mapped / 0 skipped

Mapped:
- `+ Tạo segment` → A-S08-001
- `Search tên...` → A-S08-004

### S09 — Segment Builder
7 tokens / 5 mapped / 2 skipped

Mapped:
- `← Segments` → A-S09-001
- `+ Thêm điều kiện` → A-S09-002
- `Preview danh sách` → A-S09-005
- `Hủy` → A-S09-007
- `Lưu & Materialize` → A-S09-006

Skipped:
- `___________` — segment name text input placeholder, no button interaction
- `Lưu` (topbar) — abbreviated save; only A-S09-006 (btn_save_materialize) exists, which matches "Lưu & Materialize" in actions_bar more precisely; no dedicated "Lưu-only" interaction

### S10 — Campaigns List
2 tokens / 2 mapped / 0 skipped

Mapped:
- `+ Tạo chiến dịch` → A-S10-001
- `Filter status ▼` → A-S10-003

### S11 — Campaign Detail / Targets
4 tokens / 3 mapped / 1 skipped

Mapped:
- `← Chiến dịch` → A-S11-001
- `Sửa` → A-S11-007
- `Filter: status ▼` → A-S11-005

Skipped:
- `Kích hoạt` — no activate-campaign interaction defined in S11 contract

### S12 — Ads Tracking
2 tokens / 2 mapped / 0 skipped

Mapped:
- `Date range ▼` → A-S12-002
- `Ad platform ▼` → A-S12-003

### S13 — Settings
3 tokens / 2 mapped / 1 skipped (but `Edit` appears twice for same interaction)

Mapped:
- `+ Thêm` → A-S13-004
- `Edit` → A-S13-005 (appears twice in same region, same action; one mapping covers both)

Skipped:
- nav items (`Custom Fields`, `Tags`, `Người dùng`) appear outside brackets in the sample

### S15 — Task Detail
16 tokens / 8 mapped / 8 skipped

Mapped:
- `Nguyễn Văn A ↗ 360` → A-S15-007 (header navigate 360)
- `▷ Bắt đầu` → A-S15-001
- `✎ Sửa` → A-S15-002
- `⏳ Hoãn` → A-S15-003
- `✕ Huỷ` → A-S15-004
- `▶ Vào phiên gọi` → A-S15-006
- `Xem 360 >` → A-S15-007 (body_internal; different chip text, same target as header chip)
- `✓ Ghi log & hoàn thành` → A-S15-005

Skipped:
- `← Quay lại` — no btn_back interaction defined in S15 contract
- `P1`, `Quá hạn 2 ngày`, `status chip` — display badges
- `GOLD` — display badge (appears in body_contact and body_internal)
- `ghi chú nhanh…` — text input placeholder
- `https://drive.google.com/…` — link display, no CRM interaction ID

---

## Judgment Calls

- **S15 `Xem 360 >` and `Nguyễn Văn A ↗ 360` both → A-S15-007**: same target, different chip texts from different regions (header vs body_internal). Both mapped; elements map is per-surface so no conflict.
- **S05 `All ▼` → A-S05-003** (filter_assignee): inferred from contrast with `Gán cho tôi`. Would be clearer if the filter label read "Assignee ▼".
- **S03 `+` → A-S03-013**: single `[+]` chip in sidebar.contact; context makes it unambiguous (add contact method → M15 tab=contacts).
- **S07 `Priority ▼`, `Party 🔍`, `Status ▼`**: chips shown in topbar sample but no matching interactions in contract; skipped rather than guessing.
- **S13 `Edit` chip**: maps to A-S13-005 (btn_edit_custom_field). The context is the custom-fields tab — both occurrences edit a field. If Settings content renders a Tags tab with `[✏][✕]` buttons (different icon), those would need A-S13-008, but the sample `[Edit]` is unambiguously the custom-field edit.

---

## Validator Output

```
Scanned 54 spec files, 311 actions, 52 surfaces.
⚠ VR-ASCII-DRIFT in S01, S03, S07, O01 — expected, regenerated by build.mjs
⚠ wireframe-v2.html stale — expected, regenerated by build.mjs
✓ validation passed (5 warning(s)) — 0 VR-ELEMENT-REF warnings in owned files
```

---

## Unresolved Questions

1. **S07 missing filter interactions**: topbar sample shows `Priority ▼`, `Party 🔍`, `Status ▼` chips but S07 contract has no corresponding interaction IDs. Are these deferred, or should IDs be added to the contract?
2. **S11 `Kích hoạt`**: "Activate campaign" chip has no interaction. Intentional deferral or contract gap?
3. **S15 `← Quay lại`**: header back button is rendered but no btn_back interaction in S15 contract (unlike S03/S06/S09). Confirm if navigation is browser-back or needs an explicit interaction.
4. **S15 dynamic chip**: `Nguyễn Văn A ↗ 360` contains a customer name that varies per task instance. The chip text in elements is the sample value. Confirm whether the wireframe renderer resolves this against live data or uses the literal sample text.
