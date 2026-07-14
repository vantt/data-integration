---
id: M09
type: modal
name: "Assign Conversation Modal"
platforms: [desktop]
hosted_by: [S05, S06]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M09 — Assign Conversation Modal

## Purpose

Gán hoặc chuyển NV xử lý (`assignee_user_id`) cho hội thoại Messenger. Dùng từ Inbox (S05)
và Conversation Detail (S06). Dropdown từ `crm_app_user` với role care/sales. SSE
`conversation.assigned` cập nhật inbox realtime sau khi lưu.

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
        - { h: "Gán NV: PSID_abc" }
        - { btn: "✕", action: A-M09-001 }
  body:
    - text: "NV hiện tại: CSKH B"
    - row:
        - { text: "Gán cho:" }
        - { select: "CSKH B" }
    - checklist: ["CSKH A", "[x] CSKH B (hiện tại)", "CSKH C"]
  actions:
    - row:
        - { btn: "Hủy", action: A-M09-002 }
        - { btn: "Gán", action: A-M09-003, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Gán NV: PSID_abc [x]                                                      │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· NV hiện tại: CSKH B · Gán cho: [CSKH B v] · [ ] CSKH A [x] CSKH B (hiện t…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Gán]                                                               │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Current assignee preselected
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M09-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M09-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M09-003
    element: btn_assign
    region: actions
    trigger: click
    guard: "selected_user_id != null"
    action: mutate
    effects: [conversation.assignee_user_id.update, modal.close, ui.toast.show]
