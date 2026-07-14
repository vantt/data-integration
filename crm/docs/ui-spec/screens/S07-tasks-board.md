---
id: S07
type: screen
name: "Tasks Board"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R8, R11, R15]
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

```yaml ui-layout
columns: [1fr, 4fr]
row_heights: [auto, "minmax(280px,auto)"]
areas:
  - [sidebar, topbar]
  - [sidebar, board]
content:
  sidebar:
    - slot: "C01 Sidebar Nav (global)"
  topbar:
    - row:
        - { h: "Tasks" }
        - { btn: "+ Tạo task", action: A-S07-001, primary: true }
    - row:
        - { select: "Assignee" }
        - { select: "Priority" }
        - { input: "🔍 Party" }
        - { select: "Campaign" }
        - { select: "Status" }
        - { tabs: ["List", "Board"], action: A-S07-007 }
  board:
    - row:
        - { h: "OPEN" }
        - { h: "DOING" }
        - { h: "DONE" }
    - row:
        - { list: { item: "[AUTO] CALL_NOW Nguyễn V. A · Due: hôm nay", rows: 3 } }
        - { list: { item: "Follow-up A · Due: 15/06", rows: 2 } }
        - { list: { item: "Gọi T. B ✓ 12/06", rows: 2 } }
```

<!-- ui-layout:ascii:start -->
```
┌───────────────┬────────────────────────────────────────────────────────────┐
│SIDEBAR        │TOPBAR                                                      │
│· <<C01 Sideba…│· Tasks [+ Tạo task] · [Assignee v] [Priority v] [input: (?…│
│               ├────────────────────────────────────────────────────────────┤
│               │BOARD                                                       │
│               │· OPEN DOING DONE · list ×3 {[AUTO] CALL_NOW Nguyễn V. A · …│
└───────────────┴────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

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
  - id: A-S07-008
    element: filter_priority
    region: topbar
    trigger: change
    action: mutate
    effects: [board.reload_with_filters]
  - id: A-S07-009
    element: filter_status
    region: topbar
    trigger: change
    action: mutate
    effects: [board.reload_with_filters]
  - id: A-S07-010
    element: filter_party
    region: topbar
    trigger: change
    action: mutate
    effects: [board.reload_with_filters]
  - id: A-S07-LSN01
    listens_to: filter_bar.changed
    action: mutate
    effects: [board.reload_with_filters]
  - id: A-S07-LSN02
    listens_to: filter_bar.cleared
    action: mutate
    effects: [board.reload]
```

## Implementation Notes (Phase 06)

- **Item 5 — AUTO badge for `action_queue_claim` (Phase 06)**: `tasks_board.html` and `c360_tasks_panel.html` now show `AUTO` badge for both `source='action_queue'` and `source='action_queue_claim'`. `action_queue_claim` tooltip reads "Nhận từ hàng đợi (claim)".
- **AI-11 — Dismissed actions manager view (R15)**: read-only `GET /tasks/dismissed` (`dismissed_actions.html`), linked from the Tasks Board pagehead. Lists active `crm_action_dismissal` rows (party, action_type, dismissed_by, dismissed_at, dismissed_until). Not part of the formal interaction contract above — plain navigational link, no mutation.
