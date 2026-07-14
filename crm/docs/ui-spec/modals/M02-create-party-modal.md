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
content:
  header:
    - row:
        - { h: "Tạo khách hàng mới" }
        - { btn: "✕", action: A-M02-001 }
  body:
    - row:
        - { text: "Tên hiển thị *" }
        - { input: "___" }
    - row:
        - { text: "Số điện thoại *" }
        - { input: "0901234567" }
        - { text: "→ +84901234567" }
    - row:
        - { text: "Email" }
        - { input: "___" }
    - row:
        - { text: "Ghi chú nhanh" }
        - { input: "___" }
    - text: "⚠ Nếu SĐT đã tồn tại, hệ thống sẽ cảnh báo"
  actions:
    - row:
        - { btn: "Hủy", action: A-M02-002 }
        - { btn: "Tạo khách", action: A-M02-003, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tạo khách hàng mới [x]                                                    │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Tên hiển thị * [input: ___] · Số điện thoại * [input: 0901234567] → +8490…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Tạo khách]                                                         │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

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
