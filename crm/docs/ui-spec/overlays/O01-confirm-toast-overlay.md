---
id: O01
type: overlay
name: "Confirm / Toast Overlay"
platforms: [desktop]
hosted_by: [S03, S05, S13, P05]
status: active
design_ref: ""
rules: []
regions: [content, actions]
---

# O01 — Confirm / Toast Overlay

## Purpose

Lightweight confirmation overlay cho các hành động destructive nhỏ (xóa note, xóa custom field)
không đủ quan trọng để mở modal đầy đủ. Cũng dùng như toast notification (auto-dismiss 3s)
khi không cần confirm. `confirm_type` payload điều khiển nội dung.

## Layout

```yaml ui-layout
areas:
  - [content]
  - [actions]
content:
  content:
    - text: "⚠ Xóa ghi chú này? Hành động không thể hoàn tác."
  actions:
    - row:
        - { btn: "Hủy", action: A-O01-002 }
        - { btn: "Xóa", action: A-O01-003, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│CONTENT                                                                     │
│· ! Xóa ghi chú này? Hành động không thể hoàn tác.                          │
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Xóa]                                                               │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Trigger

Mở từ destructive action buttons trên P05 (xóa note), S13 (xóa custom field def).
Toast mode: auto-triggered sau mutate thành công, auto-dismiss sau 3s.

## States

- default: Confirm dialog với message từ confirm_type
- toast: Auto-dismiss notification (success/error/info)

## Interactions

```yaml crm-contract
interactions:
  - id: A-O01-001
    element: overlay_backdrop
    region: content
    trigger: click
    action: close_overlay
  - id: A-O01-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
  - id: A-O01-003
    element: btn_confirm_delete
    region: actions
    trigger: click
    action: mutate
    effects: [entity.delete_by_type, overlay.close, ui.toast.show]
```

## Implementation Notes (Phase 06)

- **Item 6 — S14 collect inline toast**: `_s14_collect_row.html` appends a self-removing fixed-position toast (`✓ Đã lưu`, green, 2 s) when the server returns `saved=True`. Scoped to custom_select kind; does not use this O01 overlay (inline fragment swap pattern, not a modal/overlay). Documented here as the canonical toast reference.
