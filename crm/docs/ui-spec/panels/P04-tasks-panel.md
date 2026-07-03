---
id: P04
type: panel
name: "Tasks Panel"
platforms: [desktop]
hosted_by: [S03]
status: active
design_ref: ""
rules: []
regions: [toolbar, task_list]
---

# P04 — Tasks Panel

## Purpose

Panel tab "Tasks" trong Customer 360 (S03). Hiển thị tất cả task gắn party này (`crm_task`
WHERE party_id = current), sort: overdue trước → open → doing → done cuối. NV ghi log kết quả,
đánh dấu xong nhanh, hoặc tạo task mới. Task từ action_queue có badge "AUTO" + source_ref.

## Task Status

| Status | Indicator | Nghĩa |
|--------|-----------|-------|
| `open` | ● xám | Chưa bắt đầu |
| `doing` | ⟳ xanh | Đang xử lý |
| `overdue` | ● đỏ | `due_at < now` AND `status IN (open, doing)` — derived |
| `done` | ✓ mờ | Hoàn thành |
| `cancelled` | — mờ | Đã huỷ |

## Layout

```yaml ui-layout
areas:
  - [toolbar]
  - [task_list]
samples:
  toolbar: "Tasks  [+ Tạo task]  [Filter: open/all ▼]"
  task_list: "● [AUTO] Follow-up sau cuộc gọi  P2  NV A · Quá hạn 2 ngày · [Ghi log] [Xong nhanh] [···]"
elements:
  "+ Tạo task": A-P04-001
  "Filter: open/all ▼": A-P04-007
  "Ghi log": A-P04-002
  "Xong nhanh": A-P04-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│TOOLBAR                                                                     │
│· Tasks  [+ Tạo task]  [Filter: open/all v]                                 │
├────────────────────────────────────────────────────────────────────────────┤
│TASK_LIST                                                                   │
│· o [AUTO] Follow-up sau cuộc gọi  P2  NV A · Quá hạn 2 ngày · [Ghi log] [X…│
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

```
┌ TOOLBAR ──────────────────────────────────────────────────────────┐
│  Tasks   [+ Tạo task]   [Filter: open/all ▼]                     │
├ TASK LIST ────────────────────────────────────────────────────────┤
│  ● [AUTO] Follow-up sau cuộc gọi               P2  NV A          │
│    Quá hạn 2 ngày · "Khách cân nhắc SP X, hẹn lại"              │
│    [Ghi log]  [Xong nhanh]  [···]                                │
├───────────────────────────────────────────────────────────────────┤
│  ⟳ Win-back — Gửi catalogue mới                P1  NV A          │
│    Đến hạn: hôm nay                                               │
│    [Ghi log]  [Xong nhanh]  [···]                                │
├───────────────────────────────────────────────────────────────────┤
│  ✓ Gọi giới thiệu SP X              Done: 13/06  NV A            │
│    "Đã nghe · Khách đặt đơn ORD-2406"                            │
└────────────────────────────────────────────────────────────────────┘
```

## Task Item Structure

- **Line 1**: `[indicator] [AUTO?] [title]  [priority] [assignee]`
- **Line 2**: `[due/overdue label] · [rationale hoặc last log snippet — max 60 chars]`
- **Line 3 — actions**: `[Ghi log]` `[Xong nhanh]` `[···]` — ẩn khi `status = done/cancelled`

Task done: Line 1 + 2 chỉ, title mờ, không có action row.

## Context Menu (`···`)

| Action | Guard | Effect |
|--------|-------|--------|
| Sửa task | always | open M05 prefilled |
| Tạm hoãn | `status != done` | open O03 prefilled với `due_at` hiện tại |
| Huỷ task | `status != done` | confirm → `task.status = cancelled` |

## States

- ST-LOADING: Tasks fetch in-flight
- ST-EMPTY-OPEN: Không có task đang mở → "Không có task nào đang mở."
- ST-EMPTY-ALL: Filter = all, chưa có task nào

## Interactions

```yaml crm-contract
interactions:
  - id: A-P04-001
    element: btn_create_task
    region: toolbar
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id" }
  - id: A-P04-002
    element: btn_log
    region: task_list
    trigger: click
    guard: "task.status != 'done' && task.status != 'cancelled'"
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "log", task_id: "$task.id", party_name: "$party.display_name" }
  - id: A-P04-003
    element: btn_done_quick
    region: task_list
    trigger: click
    guard: "task.status != 'done' && task.status != 'cancelled'"
    action: mutate
    effects: [task.status.set_done, task.completed_at.set_now, task_list.reload]
  - id: A-P04-004
    element: menu_edit
    region: task_list
    trigger: click
    action: open_overlay
    target: M05
    payload: { task_id: "$task.id" }
  - id: A-P04-005
    element: menu_postpone
    region: task_list
    trigger: click
    guard: "task.status != 'done' && task.status != 'cancelled'"
    action: open_overlay
    target: O03
    payload: { task_id: "$task.id", due_at: "$task.due_at" }
  - id: A-P04-006
    element: menu_cancel
    region: task_list
    trigger: click
    guard: "task.status != 'done'"
    action: mutate
    effects: [task.status.set_cancelled, task_list.reload]
  - id: A-P04-007
    element: filter_status
    region: toolbar
    trigger: change
    action: mutate
    effects: [task_list.reload]
  - id: A-P04-008
    element: task_row
    region: task_list
    trigger: click
    action: navigate
    target: S15
    payload: { task_id: "$task.id" }
