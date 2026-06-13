---
id: M06
type: modal
name: "Custom Fields Edit Modal"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M06 — Custom Fields Edit Modal

## Purpose

Chỉnh sửa giá trị custom fields cho party hiện tại trong Customer 360 (S03). Render dynamically
từ `crm_custom_field_def` registry — không hardcode fields. Mỗi field render đúng input type
(text/number/date/bool/select/multiselect). Validate theo data_type + required trước khi save.
Lưu vào `crm_customer_profile.custom` JSON1.

## Layout

```
┌ MODAL — Thông tin bổ sung ─────────────────────────┐
│  Chỉnh sửa thông tin bổ sung                 [✕]  │
├────────────────────────────────────────────────────┤
│  Da nhạy cảm    [✓ Có / ✗ Không]  (bool)         │
│  Nguồn KH       [Facebook ▼]       (select)       │
│  Ngày sinh      [dd/mm/yyyy]       (date)         │
│  Ghi chú nội bộ [________________] (text)         │
├────────────────────────────────────────────────────┤
│  [Hủy]                                   [Lưu]   │
└────────────────────────────────────────────────────┘
```

## States

- default: Fields loaded từ registry + current values prefilled
- submitting: Save in-flight
- error: Validation lỗi inline per field

## Interactions

```yaml crm-contract
interactions:
  - id: A-M06-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M06-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M06-003
    element: btn_save
    region: actions
    trigger: click
    guard: "form.requiredFields.allValid"
    action: mutate
    effects: [profile.custom.update, modal.close, ui.toast.show]
