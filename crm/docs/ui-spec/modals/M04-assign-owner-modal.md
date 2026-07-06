---
id: M04
type: modal
name: "Assign Owner Modal"
platforms: [desktop]
hosted_by: [S03]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M04 — Assign Owner Modal

## Purpose

Gán hoặc thay đổi NV phụ trách (`owner_user_id`) cho party trong Customer 360 (S03).
Dropdown từ `crm_app_user` list. Sau khi lưu, worklist của NV được gán sẽ cập nhật.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Gán phụ trách: Nguyễn Văn A [✕]"
  body: "Phụ trách hiện tại: NV A · Chọn NV mới: [NV A ▼] · ○ NV A (hiện tại) ○ NV B ○ CSKH B ○ Manager C"
  actions: "[Hủy]  [Lưu]"
elements:
  "✕": A-M04-001
  "Hủy": A-M04-002
  "Lưu": A-M04-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Gán phụ trách: Nguyễn Văn A [x]                                           │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Phụ trách hiện tại: NV A · Chọn NV mới: [NV A v] · ? NV A (hiện tại) ? NV…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Lưu]                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Current owner preselected
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M04-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M04-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M04-003
    element: btn_save
    region: actions
    trigger: click
    guard: "selected_user_id != null"
    action: mutate
    effects: [party.owner_user_id.update, modal.close, ui.toast.show]
