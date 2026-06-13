---
id: O01
type: overlay
name: "Confirm / Toast Overlay"
platforms: [desktop]
hosts: [S03, S05, S13, P05]
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

```
     ┌ OVERLAY ──────────────────────────────┐
     │  ⚠ Xóa ghi chú này?                  │
     │  Hành động không thể hoàn tác.        │
     ├───────────────────────────────────────┤
     │  [Hủy]              [Xóa]            │
     └───────────────────────────────────────┘
```

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
