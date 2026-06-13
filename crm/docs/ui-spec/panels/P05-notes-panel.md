---
id: P05
type: panel
name: "Notes Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: []
regions: [toolbar, notes_list]
---

# P05 — Notes Panel

## Purpose

Panel tab "Ghi chú" trong Customer 360 (S03). Hiển thị tất cả `crm_note` gắn party này, sort
`created_at` DESC (ICT). NV thêm note tự do (không gắn activity type). Khác activity timeline
(P03) — notes là thông tin lâu dài về khách, không phải sự kiện tương tác.

## Layout

```
┌ TOOLBAR ──────────────────────────────────────────────────────────┐
│  Ghi chú   [+ Thêm ghi chú]                                      │
├ NOTES LIST ───────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ NV A  •  13/06/2026 10:45 ICT                  [Sửa] [Xóa]  │ │
│  │ "Khách da nhạy cảm, thích dòng gentle. Không dùng retinol." │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ NV C  •  01/05/2026 14:00 ICT                  [Sửa] [Xóa]  │ │
│  │ "Mua quà cho con gái — prefer gift wrap."                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## States

- ST-LOADING: Notes fetch in-flight
- ST-EMPTY: Chưa có ghi chú nào

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
    payload: { note_id: "$note.id", mode: "edit" }
  - id: A-P05-003
    element: note_delete_btn
    region: notes_list
    trigger: click
    action: open_overlay
    target: O01
    payload: { confirm_type: "delete_note", note_id: "$note.id" }
