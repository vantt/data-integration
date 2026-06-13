---
id: M14
type: modal
name: "Create Tag Modal"
platforms: [desktop]
hosts: [S13, M03]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M14 — Create Tag Modal

## Purpose

Tạo tag mới trong `crm_tag`. Dùng từ Settings (S13) hoặc inline từ Tag Management Modal (M03).
Tag có name (slug), display_label, category (free text). Sau khi tạo, tag khả dụng ngay trong
toàn hệ thống.

## Layout

```
┌ MODAL — Tạo tag mới ──────────────────────────────┐
│  Tạo tag mới                                 [✕]  │
├───────────────────────────────────────────────────┤
│  Tag name (slug) *   [vip-repeat____________]    │
│  Nhãn hiển thị *     [VIP Repeat____________]   │
│  Category            [customer-segment______]   │
│  Màu (optional)      [● Xanh  ○ Đỏ  ○ Vàng]   │
├───────────────────────────────────────────────────┤
│  [Hủy]                               [Tạo tag]  │
└───────────────────────────────────────────────────┘
```

## States

- default: Form trống
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M14-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M14-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M14-003
    element: btn_create_tag
    region: actions
    trigger: click
    guard: "form.name != '' && form.display_label != ''"
    action: mutate
    effects: [tag.create, modal.close, ui.toast.show]
