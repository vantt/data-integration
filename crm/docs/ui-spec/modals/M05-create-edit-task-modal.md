---
id: M05
type: modal
name: "Create / Edit Task Modal"
platforms: [desktop]
hosted_by: [S01, S03, S07, P04, S15]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M05 — Create / Edit Task Modal

## Purpose

Tạo mới hoặc chỉnh sửa `crm_task`. Dùng từ Worklist (S01), Customer 360 (S03), Tasks Board (S07),
Tasks Panel (P04), Task Detail (S15). Khi mở từ action_queue (qua P01), prefill title/rationale từ action item.
Task có title, due_at, priority (P1–P4), assignee, party link (optional), status, **task_kind**.

### task_kind — auto-prefill, ẩn khi chắc chắn (progressive disclosure)
`task_kind` (contact | internal | generic) quyết định S15 render body nào. Nguyên tắc: **hệ thống tự
suy + prefill**, chỉ hiện selector khi KHÔNG chắc:
- Tạo từ action_queue outreach (CALL_NOW / REORDER_* / WIN_BACK / UPSELL / CROSS_SELL / SECOND_ORDER /
  HIGH_CANCEL_RISK) → **contact**, độ tin cao → auto-set + **ẩn field**.
- Tạo từ nguồn nội bộ (vd `source=verify_account` từ S14 STOP) → **internal**, auto-set + ẩn.
- Không có party_id → **generic**, auto-set + ẩn.
- Manual mơ hồ (có party, không rõ ý định) → **hiện selector** với giá trị đoán tốt nhất làm mặc định.
Field không bao giờ bắt NV chọn khi máy đã chắc — giảm ma sát, đảm bảo dữ liệu nhất quán.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: "Tạo task mới [✕]"
  body: "Tiêu đề * [Follow-up sau cuộc gọi] · Khách hàng [Nguyễn Văn A ▼] · Loại việc [Liên hệ ▼] (ẩn khi chắc) · Due date * [20/06/2026] Giờ [10:00] · Priority [P2 — Cao ▼] · Giao cho [NV A ▼] · Ghi chú [___]"
  actions: "[Hủy]  [Lưu task]"
elements:
  "✕": A-M05-001
  "Hủy": A-M05-002
  "Lưu task": A-M05-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tạo task mới [x]                                                          │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Tiêu đề * [Follow-up sau cuộc gọi] · Khách hàng [Nguyễn Văn A v] · Loại v…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Lưu task]                                                         │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

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
  - id: A-M05-005
    element: task_kind_select
    region: body
    trigger: change
    action: mutate
    effects: [form.task_kind.set, body.reveal_if_uncertain]
