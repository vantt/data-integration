---
id: M06
type: modal
name: "Custom Fields Edit Modal"
platforms: [desktop]
hosted_by: [S03]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M06 — Custom Fields Edit Modal

## Purpose

Chỉnh sửa giá trị custom fields cho party hiện tại (entity_type='customer') trong Customer 360 (S03).
Render dynamically từ `crm_custom_field_def` registry — không hardcode fields.
Fields được group theo `section` và sort theo `sort_order` trong mỗi section.
Mỗi field render đúng input type (text/number/date/bool/select/multiselect).
Validate theo data_type + required trước khi save. Lưu vào `crm_customer_profile.custom` JSON1.

Chỉ hiển thị fields có `entity_type='customer'`. Order custom fields (entity_type='order') không hiện ở đây.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Chỉnh sửa thông tin bổ sung [✕]"
  body: "── Sức khoẻ & Da liễu ── · Da nhạy cảm [✓ Có / ✗ Không] · Loại da [Da dầu ▼] · ── Nguồn & Marketing ── · Nguồn KH [Facebook ▼] · Ngày sinh [dd/mm/yyyy] · ── Nội bộ ── · Ghi chú nội bộ [________________]"
  actions: "[Hủy]  [Lưu]"
elements:
  "✕": A-M06-001
  "Hủy": A-M06-002
  "Lưu": A-M06-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Chỉnh sửa thông tin bổ sung [x]                                           │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· ── Sức khoẻ & Da liễu ── · Da nhạy cảm [v Có / x Không] · Loại da [Da dầu…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Lưu]                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Render Rules

- Query: `SELECT * FROM crm_custom_field_def WHERE entity_type='customer' ORDER BY section, sort_order`
- Group fields vào sections (header = section text, hoặc "Thông tin bổ sung" nếu section IS NULL)
- Nếu chỉ có 1 section → không hiển thị section header
- `required=true` → label có dấu * đỏ; block save nếu empty

## States

- default: Fields loaded từ registry + current values prefilled từ crm_customer_profile.custom
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
    effects: [profile.custom.update, modal.close, ui.toast.show, left_col.custom_fields.reload]
```
