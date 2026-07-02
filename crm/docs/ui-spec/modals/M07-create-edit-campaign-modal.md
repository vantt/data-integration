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

```
┌ MODAL — Tạo chiến dịch ───────────────────────────┐
│  Tạo chiến dịch mới                          [✕]  │
├───────────────────────────────────────────────────┤
│  Tên chiến dịch * [React-Jul-2026__________]     │
│  Mục tiêu *       [Reactivation ▼]               │
│  Kênh *           [Messenger ▼]                  │
│  Segment *        [Reactivation tháng 7 ▼]       │
│                   → 34 khách (3 bị loại consent) │
│  Giao cho         [NV A, NV B ▼] (multi)        │
│  Ngày bắt đầu *   [01/07/2026]                  │
├───────────────────────────────────────────────────┤
│  [Hủy]                         [Tạo & Kích hoạt] │
└───────────────────────────────────────────────────┘
```

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
