---
id: M08
type: modal
name: "Log Activity Modal"
platforms: [desktop]
hosts: [S03, S06, P02, P03, P05]
status: active
design_ref: ""
rules: [R6]
regions: [header, body, actions]
---

# M08 — Log Activity Modal

## Purpose

Ghi log activity (`crm_activity`) sau tương tác với khách. Dùng từ Customer 360 (S03),
Conversation Detail (S06), Order History Panel (P02), Timeline Panel (P03), Notes Panel (P05).
Types: call/note/visit/email/chat/other. Optional: related_order_code (soft ref).
Mode "note_only" ẩn activity_type và chỉ lưu note vào `crm_note`.

## Layout

```
┌ MODAL — Ghi log hoạt động ────────────────────────┐
│  Ghi log: Nguyễn Văn A                      [✕]  │
├───────────────────────────────────────────────────┤
│  Loại *    [● Cuộc gọi  ○ Ghi chú  ○ Email ...]  │
│  Kết quả / Nội dung *                            │
│  [Khách xác nhận sẽ đặt tuần tới. SP X, Y.___]  │
│  [_____________________________________________]  │
│  Đơn liên quan  [ORD-20060812] (optional)        │
│  Thời gian      [13/06/2026 10:32] (ICT)         │
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

## States

- default: Form với activity_type preselected (hoặc prefilled từ caller)
- note_only: Chỉ hiện textarea, lưu vào crm_note
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M08-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M08-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M08-003
    element: btn_save
    region: actions
    trigger: click
    guard: "form.content != ''"
    action: mutate
    effects: [activity.save, modal.close, ui.toast.show, timeline.reload]
