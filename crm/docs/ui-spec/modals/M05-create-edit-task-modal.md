---
id: M05
type: modal
name: "Create / Edit Task Modal"
platforms: [desktop]
hosts: [S01, S03, S07, P04]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M05 — Create / Edit Task Modal

## Purpose

Tạo mới hoặc chỉnh sửa `crm_task`. Dùng từ Worklist (S01), Customer 360 (S03), Tasks Board (S07),
Tasks Panel (P04). Khi mở từ action_queue (qua P01), prefill title/rationale từ action item.
Task có title, due_at, priority (P1–P4), assignee, party link (optional), status.

## Layout

```
┌ MODAL — Tạo / Sửa task ───────────────────────────┐
│  Tạo task mới                                [✕]  │
├───────────────────────────────────────────────────┤
│  Tiêu đề *   [Follow-up sau cuộc gọi________]    │
│  Khách hàng  [Nguyễn Văn A ▼] (optional)         │
│  Due date *  [20/06/2026]   Giờ [10:00]          │
│  Priority    [P2 — Cao ▼]                        │
│  Giao cho    [NV A ▼]                            │
│  Ghi chú     [_____________________________]    │
├───────────────────────────────────────────────────┤
│  [Hủy]                               [Lưu task]  │
└───────────────────────────────────────────────────┘
```

## States

- default: Form trống hoặc prefilled từ action_queue
- submitting: Save in-flight
- error: ERR-TASK-DUE-PAST (warn, không block)

## Interactions

```yaml crm-contract
interactions:
  - id: A-M05-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M05-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M05-003
    element: btn_save
    region: actions
    trigger: click
    guard: "form.title != '' && form.due_at != null"
    action: mutate
    effects: [task.save, modal.close, ui.toast.show]
  - id: A-M05-004
    element: due_date_input
    region: body
    trigger: blur
    action: mutate
    effects: [form.due_at.validate, ui.warn_if_past]
