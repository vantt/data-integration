---
id: M08
type: modal
name: "Log Activity Modal"
platforms: [desktop]
hosts: [S03, S01, S06, P02, P03, P05]
status: active
design_ref: ""
rules: [R6]
regions: [header, contact_pref_banner, body, actions]
---

# M08 — Log Activity Modal

## Purpose

Ghi log activity (`crm_activity`) sau tương tác với khách, hoặc tạo note (`crm_note`).
Dùng từ Customer 360 (S03), Worklist (S01 quick-action), Conversation Detail (S06), các panels.

**Modes:**
- `activity` (default): ghi crm_activity với activity_type + content
- `contact_attempt`: ghi crm_activity với channel_used + contact_outcome + structured fields; nếu callback → auto-suggest tạo task follow-up
- `note_only`: tạo crm_note với note_type selector
- `edit_note`: chỉnh sửa crm_note đã có

## Contact Pref Banner

Nếu party có `crm_note.note_type='contact_pref'` và `pinned=true` → hiển thị banner vàng nhạt
trước form body để nhắc rep trước khi ghi log.

```
┌─ Lưu ý ──────────────────────────────────────────┐
│ 💬 Chỉ nhắn Zalo sau 8pm, không nghe số lạ       │
└───────────────────────────────────────────────────┘
```

## Layout — Mode: activity (default)

```
┌ MODAL — Ghi log hoạt động ────────────────────────┐
│  Ghi log: Nguyễn Văn A                      [✕]  │
├───────────────────────────────────────────────────┤
│  [banner contact_pref nếu có]                    │
│  Loại *    [● Cuộc gọi  ○ Ghi chú  ○ Email ...]  │
│  Nội dung *                                       │
│  [Khách xác nhận sẽ đặt tuần tới.______________]  │
│  Đơn liên quan  [ORD-20060812] (optional)         │
│  Thời gian      [13/06/2026 10:32] (ICT)          │
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

## Layout — Mode: contact_attempt

```
┌ MODAL — Ghi nhận liên lạc ────────────────────────┐
│  Liên lạc: Nguyễn Văn A                     [✕]  │
├───────────────────────────────────────────────────┤
│  [banner contact_pref nếu có]                    │
│  Kênh *    [● Phone  ○ Zalo  ○ Facebook  ○ Visit] │
│  Kết quả * [● Đã nghe  ○ Không bắt  ○ Hẹn lại   │
│             ○ Từ chối]                            │
│                                                   │
│  [Nếu "Đã nghe"] Ghi chú nội dung:               │
│  [______________________________________________]  │
│                                                   │
│  [Nếu "Hẹn lại"] Hẹn gọi lại lúc:               │
│  [dd/mm/yyyy hh:mm]  ✓ Tạo task nhắc tự động    │
│                                                   │
│  Thời lượng (giây, optional): [___]              │
│  Thời gian: [13/06/2026 10:32] (ICT, prefilled)  │
├───────────────────────────────────────────────────┤
│  [Hủy]                              [Lưu]        │
└───────────────────────────────────────────────────┘
```

## Layout — Mode: note_only

```
┌ MODAL — Thêm ghi chú ─────────────────────────────┐
│  Ghi chú: Nguyễn Văn A                      [✕]  │
├───────────────────────────────────────────────────┤
│  Loại ghi chú  [Chung ▼]                          │
│  -- Chung / Sở thích / Ưu tiên liên lạc /        │
│     Cảnh báo / Kết quả / Nội bộ                  │
│                                                   │
│  Nội dung *                                       │
│  [______________________________________________]  │
│                                                   │
│  Ghim ghi chú  [○ Không ● Có]                    │
│  [Nếu ghim] Hết hạn: [dd/mm/yyyy] (optional)    │
│  Hiển thị:     [Team ▼]  (Team / Manager / Riêng)│
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

## Save Effects by Mode

| Mode | Save vào đâu | Effects |
|------|-------------|---------|
| `activity` | `crm_activity` | timeline.reload |
| `contact_attempt` | `crm_activity` (channel_used, contact_outcome, callback_at, duration) | timeline.reload; nếu callback → tạo `crm_task` với due_at=callback_at, action_queue_id từ context |
| `note_only` | `crm_note` | notes.reload |
| `edit_note` | `crm_note` (UPDATE) | notes.reload |

## States

- default: Form với mode prefilled từ caller
- submitting: Save in-flight
- callback_task_confirm: Nếu callback → hỏi "Tạo task nhắc?" sau khi save

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
    guard: "form.content != '' || form.contact_outcome != null"
    action: mutate
    effects: [activity_or_note.save, modal.close, ui.toast.show, timeline_or_notes.reload]
  - id: A-M08-004
    element: contact_outcome_select
    region: body
    trigger: change
    guard: "mode == 'contact_attempt'"
    action: mutate
    effects: [callback_fields.toggle_visibility, note_fields.toggle_visibility]
```
