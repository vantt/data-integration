---
id: S07
type: screen
name: "Tasks Board"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R8, R11]
regions: [topbar, sidebar, board]
---

# S07 — Tasks Board

## Purpose

Bảng task toàn công ty — Manager và NV xem tất cả task theo assignee, priority, party, hoặc
campaign. Khác Worklist (S01 chỉ hiện task của NV hiện tại theo due_date), Tasks Board hiển thị
column-view hoặc list-view theo status: open / doing / done / cancelled.

NV có thể tạo task mới, chỉnh sửa, đánh dấu done trực tiếp. Task từ `action_queue` có badge
"AUTO" phân biệt. Completed task từ campaign trigger conversion check (R11).

## Layout

```
┌─ C01 SIDEBAR ─┬─────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Tasks   [+ Tạo task]  [Assignee ▼][Priority ▼]    │
│               │  Filter: [Party 🔍] [Campaign ▼] [Status ▼]  [List|Board]  │
│               ├─────────────────────────────────────────────────────────────┤
│               │  BOARD (kanban columns)                                     │
│               │  ┌─── OPEN ───────┐ ┌── DOING ──────┐ ┌── DONE ──────┐   │
│               │  │ [AUTO] CALL_NOW │ │ Follow-up A   │ │ Gọi T. B ✓   │   │
│               │  │ Nguyễn V. A    │ │ Trần T. B     │ │ 12/06        │   │
│               │  │ Due: hôm nay   │ │ Due: 15/06    │ │              │   │
│               │  │                │ │               │ │              │   │
│               │  └────────────────┘ └───────────────┘ └──────────────┘   │
└───────────────┴─────────────────────────────────────────────────────────────┘
```

## States

- ST-TASKS-EMPTY: Không có task nào trong filter → empty state
- ST-LOADING: Board loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S07-001
    element: btn_create_task
    region: topbar
    trigger: click
    action: open_overlay
    target: M05
  - id: A-S07-002
    element: task_card
    region: board
    trigger: click
    action: navigate
    target: S15
    payload: { task_id: "$task.id" }
  - id: A-S07-003
    element: task_checkbox
    region: board
    trigger: click
    action: mutate
    effects: [task.status.set_done, task.completed_at.set_now, conversion_check.trigger]
  - id: A-S07-004
    element: task_card_drag
    region: board
    trigger: drag_drop
    action: mutate
    effects: [task.status.update_from_column]
  - id: A-S07-005
    element: filter_assignee
    region: topbar
    trigger: change
    action: mutate
    effects: [board.reload]
  - id: A-S07-006
    element: filter_campaign
    region: topbar
    trigger: change
    action: mutate
    effects: [board.reload]
  - id: A-S07-007
    element: btn_toggle_view
    region: topbar
    trigger: click
    action: mutate
    effects: [board.toggle_list_view]
  - id: A-S07-LSN01
    listens_to: filter_bar.changed
    action: mutate
    effects: [board.reload_with_filters]
  - id: A-S07-LSN02
    listens_to: filter_bar.cleared
    action: mutate
    effects: [board.reload]
