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

```
┌ MODAL — Gán NV xử lý ─────────────────────────────┐
│  Gán NV: PSID_abc                            [✕]  │
├────────────────────────────────────────────────────┤
│  NV hiện tại: CSKH B                              │
│                                                    │
│  Gán cho:  [CSKH B ▼]                            │
│  ○ CSKH A                                        │
│  ● CSKH B (hiện tại)                             │
│  ○ CSKH C                                        │
├────────────────────────────────────────────────────┤
│  [Hủy]                                   [Gán]   │
└────────────────────────────────────────────────────┘
```

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
