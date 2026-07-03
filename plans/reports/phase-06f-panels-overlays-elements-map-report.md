# Phase 06f — Panels & Overlays `elements:` Map Report

**Date:** 2026-07-03  
**Scope:** P01–P06 (panels) + O01–O03 (overlays)  
**Validator result:** ✓ 0 VR-ELEMENT-REF in owned files (2 ignorable warnings: VR-ASCII-DRIFT, stale wireframe)

---

## Per-File Summary

### P01 — Value & Behavior Panel

**Tokens found (9):** `2 việc`, `📞 Gọi ngay`, `Hoàn tất (2) ✓`, `GOLD`, `active`, `ON_TRACK`, `Persona`, `cao`, `+ Thêm insight`

**Mapped (3):**
| Chip text | Action |
|-----------|--------|
| `📞 Gọi ngay` | A-P01-005 (`btn_call_now`) |
| `Hoàn tất (2) ✓` | A-P01-008 (`session_checklist_form` submit) |
| `+ Thêm insight` | A-P01-002 (`btn_add_insight`) |

**Skipped (6):**
- `2 việc` — count pill, no interaction defined
- `GOLD`, `active`, `ON_TRACK` — RFM segment badges, display-only
- `Persona` — insight_type badge, display-only
- `cao` — confidence badge, display-only

---

### P02 — Order History Panel

**Tokens found (1):** `Xem thêm →`

**Mapped (0):** No interaction defined for "see more" pagination in toolbar. A-P02-002 is `btn_log_activity_with_order`, not a pagination link.

**Skipped (1):** `Xem thêm →` — no matching interaction id

**No `elements:` block added** (no mappable tokens).

---

### P03 — Activity Timeline Panel

**Tokens found (2):** `+ Ghi log`, `Filter type ▼`

**Mapped (2):**
| Chip text | Action |
|-----------|--------|
| `+ Ghi log` | A-P03-001 (`btn_log_activity`) |
| `Filter type ▼` | A-P03-002 (`filter_type`) |

---

### P04 — Tasks Panel

**Tokens found (6):** `+ Tạo task`, `Filter: open/all ▼`, `AUTO`, `Ghi log`, `Xong nhanh`, `···`

**Mapped (4):**
| Chip text | Action |
|-----------|--------|
| `+ Tạo task` | A-P04-001 (`btn_create_task`) |
| `Filter: open/all ▼` | A-P04-007 (`filter_status`) |
| `Ghi log` | A-P04-002 (`btn_log`) |
| `Xong nhanh` | A-P04-003 (`btn_done_quick`) |

**Skipped (2):**
- `AUTO` — source origin badge, display-only, no interaction
- `···` — context menu trigger; opens a menu with 3 sub-actions (A-P04-004, A-P04-005, A-P04-006); one chip → many actions; ambiguous, skipped

---

### P05 — Notes Panel

**Tokens found (8):** `Tất cả`, `★ Ưu tiên`, `⚠ Cảnh báo`, `📞 Liên lạc`, `Campaign`, `+ Thêm ghi chú`, `warning`, `preference`

**Mapped (6):**
| Chip text | Action |
|-----------|--------|
| `Tất cả` | A-P05-004 (`tab_filter`) |
| `★ Ưu tiên` | A-P05-004 (`tab_filter`) |
| `⚠ Cảnh báo` | A-P05-004 (`tab_filter`) |
| `📞 Liên lạc` | A-P05-004 (`tab_filter`) |
| `Campaign` | A-P05-004 (`tab_filter`) |
| `+ Thêm ghi chú` | A-P05-001 (`btn_add_note`) |

**Skipped (2):**
- `warning` — note type badge in pinned_section, display-only
- `preference` — note type badge in notes_list, display-only

---

### P06 — Conversations Panel

**Tokens found (2):** `Filter: status ▼`, `Xem →`

**Mapped (2):**
| Chip text | Action |
|-----------|--------|
| `Filter: status ▼` | A-P06-002 (`filter_status`) |
| `Xem →` | A-P06-001 (`conv_view_btn`) |

---

### O01 — Confirm / Toast Overlay

**Tokens found (2):** `Hủy`, `Xóa`

**Mapped (2):**
| Chip text | Action |
|-----------|--------|
| `Hủy` | A-O01-002 (`btn_cancel`) |
| `Xóa` | A-O01-003 (`btn_confirm_delete`) |

---

### O02 — Quick Customer Preview Overlay

**Tokens found (2):** `✕`, `Mở hồ sơ đầy đủ →`

**Mapped (2):**
| Chip text | Action |
|-----------|--------|
| `✕` | A-O02-002 (`btn_close`) |
| `Mở hồ sơ đầy đủ →` | A-O02-003 (`btn_open_full_profile`) |

---

### O03 — Postpone Task Overlay

**Tokens found (4):** `27/06/2026`, `14:30`, `Huỷ`, `Xác nhận`

**Mapped (2):**
| Chip text | Action |
|-----------|--------|
| `Huỷ` | A-O03-001 (`btn_cancel`) |
| `Xác nhận` | A-O03-003 (`btn_confirm`) |

**Skipped (2):**
- `27/06/2026` — date input placeholder value, not an action chip
- `14:30` — time input placeholder value, not an action chip

---

## Totals

| File | Tokens | Mapped | Skipped | elements: added |
|------|--------|--------|---------|-----------------|
| P01 | 9 | 3 | 6 | yes |
| P02 | 1 | 0 | 1 | no |
| P03 | 2 | 2 | 0 | yes |
| P04 | 6 | 4 | 2 | yes |
| P05 | 8 | 6 | 2 | yes |
| P06 | 2 | 2 | 0 | yes |
| O01 | 2 | 2 | 0 | yes |
| O02 | 2 | 2 | 0 | yes |
| O03 | 4 | 2 | 2 | yes |
| **Total** | **36** | **23** | **13** | **8/9** |

---

## Judgment Calls

1. **P04 `···` (context menu)** — skipped. Opens a dropdown exposing 3 separate actions (edit, postpone, cancel). No single action id for the opener itself; mapping any one of them would be misleading.

2. **P05 filter tabs (5 chips → same action A-P05-004)** — allowed. "One chip text → one action id" constraint is satisfied: each chip has a unique text; it is valid for multiple chips to point to the same action.

3. **P03 `Filter type ▼` (trigger: change)** — mapped. The trigger is a dropdown `change` event which is still user-triggered; the chip represents the control that produces that event.

4. **P02 `Xem thêm →`** — skipped. No defined interaction covers pagination / "see more" in the toolbar. Could become A-P02-003 in a future revision if pagination is specced.

---

## Unresolved Questions

- P02: `Xem thêm →` implies a pagination or full-list navigate action. No interaction is specced. Should A-P02-002 be renamed to cover it, or should a new A-P02-003 be added?
- P04: Should `···` get its own interaction id for "open context menu" so the chip can be linked without ambiguity?
