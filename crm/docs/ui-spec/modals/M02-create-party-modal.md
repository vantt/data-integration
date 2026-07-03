---
id: M02
type: modal
name: "Create Party Modal"
platforms: [desktop]
hosted_by: [S02]
status: active
design_ref: ""
rules: [R5]
regions: [header, body, actions]
---

# M02 — Create Party Modal

## Purpose

Tạo mới `crm_party` + `crm_party_identity` thủ công khi không tìm thấy khách qua search.
SĐT bắt buộc (normalized E.164 — R5). Tên hiển thị bắt buộc. Email tùy chọn. Sau khi tạo,
navigate thẳng đến Customer 360 (S03) của party mới.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Tạo khách hàng mới [✕]"
  body: "Tên hiển thị * [___] · Số điện thoại * [0901234567] → +84901234567 · Email [___] · Ghi chú nhanh [___] · ⚠ Nếu SĐT đã tồn tại, hệ thống sẽ cảnh báo"
  actions: "[Hủy]  [Tạo khách]"
elements:
  "✕": A-M02-001
  "Hủy": A-M02-002
  "Tạo khách": A-M02-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tạo khách hàng mới [x]                                                    │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Tên hiển thị * [___] · Số điện thoại * [0901234567] → +84901234567 · Emai…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Tạo khách]                                                        │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

```
┌ MODAL — Tạo khách hàng mới ────────────────────────┐
│  Tạo khách hàng mới                          [✕]  │
├────────────────────────────────────────────────────┤
│  Tên hiển thị *  [___________________________]    │
│  Số điện thoại * [0901234567]  → +84901234567     │
│  Email           [___________________________]    │
│  Ghi chú nhanh   [___________________________]    │
│                                                    │
│  ⚠ Nếu SĐT đã tồn tại, hệ thống sẽ cảnh báo     │
├────────────────────────────────────────────────────┤
│  [Hủy]                              [Tạo khách]  │
└────────────────────────────────────────────────────┘
```

## States

- default: Form trống
- submitting: Save in-flight
- error: ERR-DUPLICATE-IDENTITY hoặc ERR-PHONE-FORMAT

## Interactions

```yaml crm-contract
interactions:
  - id: A-M02-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M02-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M02-003
    element: btn_create
    region: actions
    trigger: click
    guard: "form.display_name != '' && form.phone.valid"
    action: mutate
    effects: [party.create, identity.create_phone, modal.close]
  - id: A-M02-004
    element: phone_input
    region: body
    trigger: blur
    action: mutate
    effects: [phone.normalize_e164, ui.phone_preview.update]
