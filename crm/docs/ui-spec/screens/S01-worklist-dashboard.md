---
id: S01
type: screen
name: "Worklist / Dashboard"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R2, R6, R8]
regions: [topbar, sidebar, main, task_list]
---

# S01 — Worklist / Dashboard

## Purpose

Màn hình chính mà Sales Rep mở mỗi buổi sáng. Hiển thị danh sách task hôm nay được giao cho NV
(từ `crm_task` + `wh_action_queue`), sắp xếp theo due_at + priority. Mỗi task row có tên khách,
lý do hành động (`rationale_vi`), giá trị tiềm năng (`value_at_stake_vnd`), kênh liên lạc ưu tiên,
và `contact_pref` note inline (nếu có) để rep biết cách tiếp cận ngay mà không cần mở S03.

NV nhấn vào task → Customer 360. NV có thể filter theo assignee, tag task done trực tiếp từ list,
hoặc tạo task mới thủ công. Badge trên sidebar cập nhật theo SSE khi có task mới hoặc cache refresh.

## Layout

```
┌─ C01 SIDEBAR NAV ─┬─────────────────────────────────────────────────────┐
│  [≡] CRM          │  TOPBAR: Worklist hôm nay   [+ Tạo task] [Filter ▼] │
│  > Worklist  ●    ├─────────────────────────────────────────────────────┤
│    Khách hàng     │  TASK LIST                                           │
│    Inbox     3    │  ┌──────────────────────────────────────────────────┐│
│    Tasks          │  │ ☐ CALL_NOW   Nguyễn Văn A                       ││
│    Segments       │  │   "Sắp hết hàng yêu thích — gọi ngay"           ││
│    Chiến dịch     │  │   💰 2.400.000đ  ·  Due: Hôm nay                ││
│    Ads            │  │   💬 Chỉ Zalo sau 8pm                           ││
│    Cài đặt        │  │   [📞 Gọi] [💬 Zalo] [Xem 360]                  ││
│                   │  ├──────────────────────────────────────────────────┤│
│  [User: NV A]     │  │ ☐ WIN_BACK   Trần Thị B                         ││
│                   │  │   "Chưa mua 92 ngày, GOLD"                       ││
│                   │  │   💰 1.800.000đ  ·  Due: Hôm nay                ││
│                   │  │   📞 0912 345 678                                ││
│                   │  │   [📞 Gọi] [Xem 360]                             ││
│                   │  └──────────────────────────────────────────────────┘│
│                   │  ... (paginated list)                                │
│                   │                                                      │
│                   │  FRESHNESS: cache cập nhật lúc 07:15 ICT ✓          │
└───────────────────┴──────────────────────────────────────────────────────┘
```

## Task Row Detail

Mỗi task row hiển thị:
- Checkbox done + action_type badge (CALL_NOW, WIN_BACK, UPSELL, ...)
- Tên khách hàng
- `rationale_vi` (lý do từ action_queue hoặc task notes)
- `value_at_stake_vnd` (nếu từ action_queue)
- Due date + priority badge
- `contact_pref` note inline (nếu party có note_type='contact_pref' và pinned=true)
- Kênh liên lạc ưu tiên (`is_preferred=true` từ crm_party_identity)
- Quick-action buttons: [Gọi] / [Zalo] / [Facebook] tuỳ theo kênh available + [Xem 360]

Quick-action buttons chỉ log contact attempt (M08 mode=contact_attempt), không navigate ra ngoài.

## States

- ST-WORKLIST-EMPTY: Không có task hôm nay → empty state + CTA browse customers
- ST-WORKLIST-ALL-DONE: Tất cả done → celebratory message
- ST-LOADING: Skeleton rows khi query worklist
- ST-STALE-CACHE: `refreshed_at` > 24h → yellow badge trên freshness footer

## Interactions

```yaml crm-contract
interactions:
  - id: A-S01-001
    element: task_row
    region: task_list
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$task.party_id" }
  - id: A-S01-002
    element: btn_open_customer
    region: task_list
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$task.party_id" }
  - id: A-S01-003
    element: task_checkbox
    region: task_list
    trigger: click
    action: mutate
    effects: [task.status.set_done, task.completed_at.set_now]
  - id: A-S01-004
    element: btn_create_task
    region: topbar
    trigger: click
    action: open_overlay
    target: M05
  - id: A-S01-005
    element: filter_assignee
    region: topbar
    trigger: change
    action: mutate
    effects: [task_list.reload]
  - id: A-S01-006
    element: filter_priority
    region: topbar
    trigger: change
    action: mutate
    effects: [task_list.reload]
  - id: A-S01-007
    element: btn_quick_call
    region: task_list
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$task.party_id", task_id: "$task.id", mode: "contact_attempt", channel: "phone" }
  - id: A-S01-008
    element: btn_quick_zalo
    region: task_list
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$task.party_id", task_id: "$task.id", mode: "contact_attempt", channel: "zalo" }
  - id: A-S01-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [freshness_badge.update]
  - id: A-S01-LSN02
    listens_to: task.due.soon
    action: mutate
    effects: [task_list.reload, ui.toast.show]
  - id: A-S01-LSN03
    listens_to: nav.item.selected
    action: navigate
    target: S01
  - id: A-S01-LSN04
    listens_to: action_queue.task_requested
    action: open_overlay
    target: M05
    payload: { source: "action_queue", action_id: "$event.action_id", party_id: "$event.party_id" }
  - id: A-S01-LSN05
    listens_to: action_queue.card_clicked
    action: navigate
    target: S03
    payload: { party_id: "$event.party_id" }
  - id: A-S01-LSN06
    listens_to: filter_bar.changed
    action: mutate
    effects: [task_list.reload_with_filters]
  - id: A-S01-LSN07
    listens_to: filter_bar.cleared
    action: mutate
    effects: [task_list.reload]
```
