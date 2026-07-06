---
id: M13
type: modal
name: "Custom Field Definition Modal"
platforms: [desktop]
hosted_by: [S13]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M13 — Custom Field Definition Modal

## Purpose

Tạo mới hoặc chỉnh sửa `crm_custom_field_def` từ Settings (S13). Định nghĩa field mới không
cần migration — schema-less JSON1. Admin chọn: entity_type (customer/order), field_name (slug),
display_label, section (grouping), sort_order, data_type, required, options (select/multiselect).

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Tạo custom field mới [✕]"
  body: "Áp dụng cho * [● Khách hàng ○ Đơn hàng] · Field name (slug) * [da_nhay_cam] · Nhãn hiển thị * [Da nhạy cảm] · Section [Sức khoẻ & Da liễu] · Thứ tự hiển thị [1] · Loại dữ liệu * [Boolean (Có/Không) ▼] · Bắt buộc [○ Có ● Không] · Tùy chọn [+ Thêm tùy chọn] (chỉ khi select/multiselect)"
  actions: "[Hủy]  [Lưu]"
elements:
  "✕": A-M13-001
  "Hủy": A-M13-002
  "Lưu": A-M13-004
  "+ Thêm tùy chọn": A-M13-005
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tạo custom field mới [x]                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Áp dụng cho * [o Khách hàng ? Đơn hàng] · Field name (slug) * [da_nhay_ca…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Lưu]                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Field Notes

- `entity_type`: bắt buộc. Quyết định field hiện ở M06 (customer) hay trong order detail (order)
- `section`: free-text, không enum. VD: "Sức khoẻ & Da liễu", "Nguồn & Marketing", "Nội bộ"
- `sort_order`: integer, sort trong cùng section. Mặc định = số thứ tự tạo
- `field_name`: slug không dấu, dùng làm key trong JSON1. Không thể đổi sau khi tạo (edit lock)
- Khi edit: field_name readonly, chỉ sửa được display_label, section, sort_order, required, options

## States

- default: Form trống hoặc prefilled khi edit
- edit_mode: field_name input disabled
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
    guard: "form.entity_type != null && form.field_name != '' && form.display_label != '' && form.data_type != null"
    action: mutate
    effects: [custom_field_def.save, modal.close, ui.toast.show, settings_list.reload]
  - id: A-M13-005
    element: btn_add_option
    region: body
    trigger: click
    action: mutate
    effects: [options_list.append_empty_row]
```
