---
id: O03
type: overlay
name: "Postpone Task Overlay"
platforms: [desktop]
hosts: [P04, S07]
status: active
design_ref: ""
rules: [R6]
regions: [body, actions]
---

# O03 — Postpone Task Overlay

## Purpose

Popover nhỏ anchor-positioned (gần element kích hoạt) cho phép NV đổi `due_at` của một task
mà không cần mở full M05. Pre-populate date + time từ `task.due_at` hiện tại (ICT display).

## Layout

```
  ┌─────────────────────────────┐
  │  Hoãn đến:                  │
  │  [27/06/2026]  [14:30]      │
  │                             │
  │  [Huỷ]         [Xác nhận]  │
  └─────────────────────────────┘
```

- Date: `<input type="date">` pre-filled từ ICT date của `task.due_at`
- Time: `<input type="time">` pre-filled từ ICT time của `task.due_at`
- Dismiss on scrim click hoặc Esc

## Save Effects

- `task.due_at` = new date+time (ICT → UTC trước khi lưu, per R6)
- `task.status` reset về `open` nếu hiện đang `doing`
- System timeline entry tự ghi: "Task hoãn đến [new_due ICT]" — không mở M08
- `task_list.reload`

## States

- default: form pre-filled
- error: date field trống → disable btn Xác nhận

## Interactions

```yaml crm-contract
interactions:
  - id: A-O03-001
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-O03-002
    element: scrim
    region: body
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-O03-003
    element: btn_confirm
    region: actions
    trigger: click
    guard: "form.date != ''"
    action: mutate
    effects: [task.due_at.update, task.status.reset_to_open_if_doing, timeline.log_postpone, overlay.close, task_list.reload]
```
