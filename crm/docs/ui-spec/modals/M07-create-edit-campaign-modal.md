---
id: M07
type: modal
name: "Create / Edit Campaign Modal"
platforms: [desktop]
hosted_by: [S10, S11]
status: active
design_ref: ""
rules: [R1]
regions: [header, body, actions]
---

# M07 — Create / Edit Campaign Modal

## Purpose

Tạo mới hoặc chỉnh sửa `crm_campaign`. Manager chọn: tên, objective
(reactivation/winback/upsell/crosssell), channel (messenger/call/email), segment gắn kèm,
assignee NV thực hiện, scheduled_at. Khi lưu, hệ thống sinh `crm_campaign_target` cho mỗi
party trong segment (consent_contact=true — R1).

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
        - { h: "Tạo chiến dịch mới" }
        - { btn: "✕", action: A-M07-001 }
  body:
    - row:
        - { text: "Tên chiến dịch *" }
        - { input: "React-Jul-2026" }
    - row:
        - { text: "Mục tiêu *" }
        - { select: "Reactivation" }
    - row:
        - { text: "Kênh *" }
        - { select: "Messenger" }
    - row:
        - { text: "Segment *" }
        - { select: "Reactivation tháng 7" }
    - text: "→ 34 khách (3 bị loại consent)"
    - row:
        - { text: "Giao cho" }
        - { select: "NV A, NV B" }
    - row:
        - { text: "Ngày bắt đầu *" }
        - { input: "01/07/2026" }
  actions:
    - row:
        - { btn: "Hủy", action: A-M07-002 }
        - { btn: "Tạo & Kích hoạt", action: A-M07-004, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tạo chiến dịch mới [x]                                                    │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Tên chiến dịch * [input: React-Jul-2026] · Mục tiêu * [Reactivation v] · …│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Tạo & Kích hoạt]                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Form trống
- submitting: Save + target generation in-flight
- error: ERR-CAMPAIGN-NO-SEGMENT

## Interactions

```yaml crm-contract
interactions:
  - id: A-M07-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M07-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M07-003
    element: segment_select
    region: body
    trigger: change
    action: mutate
    effects: [campaign.target_preview.reload]
  - id: A-M07-004
    element: btn_save
    region: actions
    trigger: click
    guard: "form.name != '' && form.segment_id != null && form.scheduled_at != null"
    action: mutate
    effects: [campaign.save, campaign_targets.generate, modal.close, ui.toast.show]
