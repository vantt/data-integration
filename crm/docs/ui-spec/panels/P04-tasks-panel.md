---
id: P04
type: panel
name: "Tasks Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: []
regions: [toolbar, task_list]
---

# P04 — Tasks Panel

## Purpose

Panel tab "Tasks" trong Customer 360 (S03). Hiển thị tất cả task gắn party này (`crm_task`
WHERE party_id = current), sort due_at ASC. NV tạo follow-up task mới, đánh dấu done, hoặc
chỉnh sửa. Task từ action_queue có badge "AUTO" + source_ref.

## Layout

```
┌ TOOLBAR ──────────────────────────────────────────────────────────┐
│  Tasks   [+ Tạo task]   [Filter: open/all ▼]                     │
├ TASK LIST ────────────────────────────────────────────────────────┤
│  ☐ [AUTO] Follow-up sau cuộc gọi    Due: 20/06  P2  NV A        │
│  ☐ Gửi catalogue mới                Due: 25/06  P3  NV A        │
│  ✓ Gọi giới thiệu SP X              Done: 13/06                  │
└────────────────────────────────────────────────────────────────────┘
```

## States

- ST-LOADING: Tasks fetch in-flight
- ST-EMPTY: Không có task nào

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
    element: task_checkbox
    region: task_list
    trigger: click
    action: mutate
    effects: [task.status.set_done, task.completed_at.set_now]
  - id: A-P04-003
    element: task_row_edit
    region: task_list
    trigger: click
    action: open_overlay
    target: M05
    payload: { task_id: "$task.id" }
  - id: A-P04-004
    element: filter_status
    region: toolbar
    trigger: change
    action: mutate
    effects: [task_list.reload]
