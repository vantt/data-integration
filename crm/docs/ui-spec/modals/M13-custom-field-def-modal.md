---
id: M13
type: modal
name: "Custom Field Definition Modal"
platforms: [desktop]
hosts: [S13]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M13 — Custom Field Definition Modal

## Purpose

Tạo mới hoặc chỉnh sửa `crm_custom_field_def` từ Settings (S13). Định nghĩa field mới không
cần migration — schema-less JSON1. Admin chọn: field_name (slug), display_label, data_type
(text/number/date/bool/select/multiselect), required, options (nếu select/multiselect).

## Layout

```
┌ MODAL — Định nghĩa custom field ──────────────────┐
│  Tạo custom field mới                        [✕]  │
├───────────────────────────────────────────────────┤
│  Field name (slug) *  [da_nhay_cam__________]    │
│  Nhãn hiển thị *      [Da nhạy cảm__________]   │
│  Loại dữ liệu *       [Boolean (Có/Không) ▼]    │
│  Bắt buộc             [○ Có  ● Không]           │
│  (options — chỉ hiện khi loại = select):         │
│  Tùy chọn             [+ Thêm tùy chọn]         │
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

## States

- default: Form trống hoặc prefilled khi edit
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M13-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M13-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M13-003
    element: data_type_select
    region: body
    trigger: change
    action: mutate
    effects: [options_section.toggle_visibility]
  - id: A-M13-004
    element: btn_save
    region: actions
    trigger: click
    guard: "form.field_name != '' && form.display_label != '' && form.data_type != null"
    action: mutate
    effects: [custom_field_def.save, modal.close, ui.toast.show]
