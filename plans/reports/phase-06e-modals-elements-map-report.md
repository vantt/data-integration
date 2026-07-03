# Phase 06e — Modals `elements:` Map Report

Date: 2026-07-03
Files owned: `crm/docs/ui-spec/modals/` M01–M16 (16 files)

## Rules applied

- Only chips from `samples:` inside the `yaml ui-layout` fence
- Only button/link/tab elements with `trigger: click` are mapped; form controls (input, select, radio, textarea, blur/input/change trigger) are skipped
- WRONG MAPPINGS WORSE THAN MISSING — uncertain pairs skipped
- Same chip text appearing multiple times → single entry (e.g. `[+]` in M03)

---

## Per-file summary

| File | Chips in samples | Mapped | Skipped |
|------|-----------------|--------|---------|
| M01 | ✕, ✓, Hủy, Xác nhận Merge | 3 | 1 |
| M02 | ✕, ___, 0901234567, Hủy, Tạo khách | 3 | 2 |
| M03 | ✕, VIP ✕, repeat ✕, da-nhạy-cảm ✕, 🔍…, + (×4), Đóng, Lưu | 7 | 1 |
| M04 | ✕, NV A ▼, Hủy, Lưu | 3 | 1 |
| M05 | ✕, many form fields, Hủy, Lưu task | 3 | 7 |
| M06 | ✕, many form fields, Hủy, Lưu | 3 | 5 |
| M07 | ✕, many form fields, Hủy, Tạo & Kích hoạt | 3 | 5 |
| M08 | ✕, Cuộc gọi ▾, 0901234567…, Dùng số khác, Đã nghe, Không bắt, Hẹn lại, Từ chối, textarea, datetime ICT, ORD-…, Hủy, Lưu hoạt động | 7 | 6 |
| M09 | ✕, CSKH B ▼, Hủy, Gán | 3 | 1 |
| M10 | ✕, resolution textarea, ✓ checkbox, Hủy, Đóng hội thoại | 3 | 2 |
| M11 | ✕, 🔍…, + Tạo khách mới, Hủy, Gắn khách đã chọn | 4 | 1 |
| M12 | ✕, ORD-…, ✓ checkbox, __, Hủy, Ghi nhận | 3 | 3 |
| M13 | ✕, many form fields, + Thêm tùy chọn, Hủy, Lưu | 3 | 7 |
| M14 | ✕, many form fields, Hủy, Tạo tag | 3 | 4 |
| M15 | ✕, Liên lạc, Địa chỉ, Thông tin cơ bản, ✎, ✗ (×3), + Thêm kênh liên lạc, Hủy, Lưu | 7 | 2 |
| M16 | ✕, Persona ▼, textarea, radio, Hủy, Lưu insight | 3 | 3 |

**Total mapped:** 61 entries (across 16 files). **Total skipped:** 51 chips.

---

## Mappings detail

### M01
| Chip | Action |
|------|--------|
| ✕ | A-M01-001 |
| Hủy | A-M01-002 |
| Xác nhận Merge | A-M01-003 |

Skipped: `✓` (confirm checkbox — no action ID; only used as guard on A-M01-003)

### M02
| Chip | Action |
|------|--------|
| ✕ | A-M02-001 |
| Hủy | A-M02-002 |
| Tạo khách | A-M02-003 |

Skipped: `___` (text inputs ×3), `0901234567` (phone_input blur → A-M02-004 is blur trigger, not click)

### M03
| Chip | Action |
|------|--------|
| ✕ | A-M03-001 |
| VIP ✕ | A-M03-003 |
| repeat ✕ | A-M03-003 |
| da-nhạy-cảm ✕ | A-M03-003 |
| + | A-M03-004 |
| Đóng | A-M03-002 |
| Lưu | A-M03-005 |

Skipped: `🔍 Tìm hoặc tạo tag mới...` (search input, input trigger → A-M03-006)

**Judgment call:** Tag-remove chips "VIP ✕" etc. are data-driven instances of the same action (A-M03-003); all included since chip text is unique per tag and the mapping is unambiguous. The `+` chip appears 4× in sample (skin-care, wholesale, gift-buyer, price-sensitive) — one elements entry suffices.

### M04
| Chip | Action |
|------|--------|
| ✕ | A-M04-001 |
| Hủy | A-M04-002 |
| Lưu | A-M04-003 |

Skipped: `NV A ▼` (owner select dropdown, no click action in contract)

### M05
| Chip | Action |
|------|--------|
| ✕ | A-M05-001 |
| Hủy | A-M05-002 |
| Lưu task | A-M05-003 |

Skipped: `Follow-up sau cuộc gọi` (text input), `Nguyễn Văn A ▼` (select), `Liên hệ ▼` (task_kind_select, change trigger → A-M05-005), `20/06/2026` (due_date_input, blur trigger → A-M05-004), `10:00` (time input), `P2 — Cao ▼` (select), `NV A ▼` (select), `___` (notes input)

**Judgment call:** `[Liên hệ ▼]` has action A-M05-005 (change trigger) but is a select form control, not a button — skipped for consistency with S14 element style.

### M06
| Chip | Action |
|------|--------|
| ✕ | A-M06-001 |
| Hủy | A-M06-002 |
| Lưu | A-M06-003 |

Skipped: All body chips are form controls (bool toggle, selects, date, text input).

### M07
| Chip | Action |
|------|--------|
| ✕ | A-M07-001 |
| Hủy | A-M07-002 |
| Tạo & Kích hoạt | A-M07-004 |

Skipped: `React-Jul-2026` (text), `Reactivation ▼` (select), `Messenger ▼` (select), `Reactivation tháng 7 ▼` (segment_select, change trigger → A-M07-003), `NV A, NV B ▼` (multi-select), `01/07/2026` (date)

### M08
| Chip | Action |
|------|--------|
| ✕ | A-M08-001 |
| Đã nghe | A-M08-005 |
| Không bắt | A-M08-005 |
| Hẹn lại | A-M08-005 |
| Từ chối | A-M08-005 |
| Hủy | A-M08-002 |
| Lưu hoạt động | A-M08-003 |

Skipped: `📞 Cuộc gọi ▾` (select, change trigger → A-M08-004), `● 0901234567 (chính)` (phone radio/option), `Dùng số khác` (no action ID in contract), `textarea` / `datetime ICT` / `ORD-…` (form inputs)

### M09
| Chip | Action |
|------|--------|
| ✕ | A-M09-001 |
| Hủy | A-M09-002 |
| Gán | A-M09-003 |

Skipped: `CSKH B ▼` (assignee select)

### M10
| Chip | Action |
|------|--------|
| ✕ | A-M10-001 |
| Hủy | A-M10-002 |
| Đóng hội thoại | A-M10-003 |

Skipped: `Đã giải quyết thắc mắc về đơn hàng` (textarea input), `✓` (checkbox, no action ID)

### M11
| Chip | Action |
|------|--------|
| ✕ | A-M11-001 |
| + Tạo khách mới | A-M11-006 |
| Hủy | A-M11-002 |
| Gắn khách đã chọn | A-M11-005 |

Skipped: `🔍 Tìm theo SĐT, tên, email...` (search_input, input trigger → A-M11-003)

Note: `party_result_row` (A-M11-004) does not appear as a named chip in samples (rows shown as plain text without brackets).

### M12
| Chip | Action |
|------|--------|
| ✕ | A-M12-001 |
| Hủy | A-M12-002 |
| Ghi nhận | A-M12-004 |

Skipped: `ORD-____________` (order_code_input, blur trigger → A-M12-003), `✓` (manual checkbox, no action ID), `__________` (revenue text input)

### M13
| Chip | Action |
|------|--------|
| ✕ | A-M13-001 |
| Hủy | A-M13-002 |
| Lưu | A-M13-004 |

Skipped: `● Khách hàng ○ Đơn hàng` (radio), `da_nhay_cam` / `Da nhạy cảm` / `Sức khoẻ & Da liễu` / `1` (text/number inputs), `Boolean (Có/Không) ▼` (data_type_select, change → A-M13-003), `○ Có ● Không` (radio), `+ Thêm tùy chọn` (no action ID in contract — options management not defined)

### M14
| Chip | Action |
|------|--------|
| ✕ | A-M14-001 |
| Hủy | A-M14-002 |
| Tạo tag | A-M14-003 |

Skipped: `vip-repeat` / `VIP Repeat` (text inputs), `Phân tầng VIP ▼` (select), `● Xanh ○ Đỏ ○ Vàng ...` (color radio)

### M15
| Chip | Action |
|------|--------|
| ✕ | A-M15-001 |
| Liên lạc | A-M15-002 |
| Địa chỉ | A-M15-003 |
| Thông tin cơ bản | A-M15-004 |
| ✗ | A-M15-006 |
| + Thêm kênh liên lạc | A-M15-005 |
| Lưu | A-M15-007 |

Skipped: `✎` (edit-channel icon — no btn_edit_channel action ID in M15 contract), `Hủy` (no btn_cancel defined in M15 — contract only defines btn_close A-M15-001 for header, no separate cancel button; mapping to btn_close would be incorrect element assignment)

Note: `✕` (header close, U+2715) and `✗` (deactivate channel, U+2717) are different Unicode characters — no ambiguity.

### M16
| Chip | Action |
|------|--------|
| ✕ | A-M16-001 |
| Hủy | A-M16-002 |
| Lưu insight | A-M16-003 |

Skipped: `Persona ▼` (select), `Mua cho shop tại Q7…` (textarea), `● Cao ○ Trung bình ○ Thấp` (radio)

---

## Validation result

```
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec

Scanned 54 spec files, 311 actions, 52 surfaces.
⚠ VR-ASCII-DRIFT: S01, S03, S07, O01 (not owned)
⚠ stale wireframe-v2.html (not owned)

✓ validation passed (5 warning(s)).
```

**VR-ELEMENT-REF in owned files: 0.**

---

## Unresolved questions

1. **M15 `Hủy` unmapped** — M15 contract has no `btn_cancel` interaction (unlike all other modals). The `[Hủy]` button in actions has no action ID. Is this an oversight in the spec? If a cancel action should be added (e.g. A-M15-008 `btn_cancel → close_overlay`), the elements map can be updated.

2. **M13 `+ Thêm tùy chọn` unmapped** — Adding select/multiselect options has no defined interaction in the M13 contract. Should an action (e.g. `A-M13-005 btn_add_option`) be defined?

3. **M03 tag-remove chips are data-specific** — "VIP ✕", "repeat ✕", "da-nhạy-cảm ✕" are sample tag names. All correctly map to A-M03-003, but if the wireframe renderer uses exact chip-text matching, these entries only work for the illustrated sample data. A wildcard pattern (e.g. `"*✕" → A-M03-003`) may be needed in the renderer for generality.
