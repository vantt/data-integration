---
id: P05
type: panel
name: "Notes Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: []
regions: [toolbar, pinned_section, notes_list]
---

# P05 — Notes Panel

## Purpose

Panel tab "Ghi chú" trong Customer 360 (S03). Hiển thị tất cả `crm_note` gắn party này.
Notes là thông tin lâu dài về khách (sở thích, cảnh báo, kết quả liên lạc, nhận định),
khác activity timeline (P03) là event log immutable theo thời gian.

Notes có type để surface đúng chỗ:
- `warning` + `contact_pref` nổi lên đầu left col của S03
- `contact_pref` hiển thị inline trên S01 worklist row
- `preference` hiển thị trong P01 insight panel
- Notes khác tập trung ở P05 này

## Layout

```
┌ TOOLBAR ──────────────────────────────────────────────────────────┐
│  [Tất cả] [★ Ưu tiên] [⚠ Cảnh báo] [📞 Liên lạc] [Campaign]     │
│                                              [+ Thêm ghi chú]    │
├ PINNED ────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ ★ [warning]  NV A  •  15/06/2026                [Sửa] [Xóa]  │ │
│  │ "Hoàn hàng 3 lần. Xác nhận kỹ trước khi ship."              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ ★ [contact_pref]  NV A  •  10/06/2026          [Sửa] [Xóa]  │ │
│  │ "Chỉ nhắn Zalo sau 8pm, không nghe số lạ."                  │ │
│  │ Hết hạn: 31/12/2026                                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
├ NOTES LIST ────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ [preference]  NV A  •  13/06/2026 10:45        [Sửa] [Xóa]  │ │
│  │ "Da nhạy cảm, thích dòng gentle. Không dùng retinol."       │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ [outcome]  NV C  •  01/06/2026 14:00           [Sửa] [Xóa]  │ │
│  │ "Gọi lần 3: nói đang khó khăn, hẹn tháng 7."               │ │
│  │ Task: WIN_BACK #45  ·  [★ Đúc kết thành insight]            │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## Note Types

| Type | Label hiển thị | Behavior |
|------|---------------|---------|
| `general` | (không badge) | Default |
| `preference` | [preference] xanh | Hiển thị trong P01 |
| `contact_pref` | [liên lạc] tím | S01 inline + S03 contact section |
| `warning` | [⚠ cảnh báo] đỏ | S03 top of left col, chỉ manager xóa |
| `outcome` | [kết quả] xám | Linked task_id + "Đúc kết" button |
| `internal` | [nội bộ] xám đậm | Ẩn với junior staff |

## Note Display Rules

- Pinned notes (`pinned=true`) luôn nằm phần PINNED, trước notes list
- `pinned_until` đã qua → tự move xuống notes list bình thường
- `visibility='manager_only'` → ẩn với role < manager
- `visibility='private'` → chỉ người tạo thấy
- `deleted_at IS NOT NULL` → ẩn hoàn toàn (soft delete)
- Sort notes list: created_at DESC

## States

- ST-LOADING: Notes fetch in-flight
- ST-EMPTY: Chưa có ghi chú nào → placeholder + CTA "Thêm ghi chú đầu tiên"

## Interactions

```yaml crm-contract
interactions:
  - id: A-P05-001
    element: btn_add_note
    region: toolbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "note_only" }
  - id: A-P05-002
    element: note_edit_btn
    region: notes_list
    trigger: click
    action: open_overlay
    target: M08
    payload: { note_id: "$note.id", mode: "edit_note" }
  - id: A-P05-003
    element: note_delete_btn
    region: notes_list
    trigger: click
    action: open_overlay
    target: O01
    payload: { confirm_type: "delete_note", note_id: "$note.id" }
  - id: A-P05-004
    element: tab_filter
    region: toolbar
    trigger: click
    action: mutate
    effects: [notes_list.reload_with_type_filter]
  - id: A-P05-005
    element: btn_promote_insight
    region: notes_list
    trigger: click
    action: open_overlay
    target: M16
    payload: { party_id: "$party.id", source_note_id: "$note.id", prefill_body: "$note.body" }
```
