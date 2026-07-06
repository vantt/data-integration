---
id: M10
type: modal
name: "Close Conversation Modal"
platforms: [desktop]
hosted_by: [S06]
status: active
design_ref: ""
rules: [R6]
regions: [header, body, actions]
---

# M10 — Close Conversation Modal

## Purpose

Đóng hội thoại Messenger (set `status=closed`) và tùy chọn ghi activity `type=chat` gắn party
(nếu party đã link). Tạo activity giúp timeline khách phản ánh đầy đủ tương tác chat.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Đóng hội thoại với Nguyễn Văn A [✕]"
  body: "Kết quả xử lý: [Đã giải quyết thắc mắc về đơn hàng] · [✓] Ghi vào activity timeline của khách"
  actions: "[Hủy]  [Đóng hội thoại]"
elements:
  "✕": A-M10-001
  "Hủy": A-M10-002
  "Đóng hội thoại": A-M10-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Đóng hội thoại với Nguyễn Văn A [x]                                       │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Kết quả xử lý: [Đã giải quyết thắc mắc về đơn hàng] · [v] Ghi vào activit…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Đóng hội thoại]                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Textarea trống, checkbox checked by default (nếu party linked)
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M10-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M10-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M10-003
    element: btn_close_conversation
    region: actions
    trigger: click
    action: mutate
    effects: [conversation.status.set_closed, activity.create_if_checkbox, modal.close, ui.toast.show]
