---
id: F01
type: flow
name: "Morning Worklist → Call → Re-sell"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: []
regions: []
---

# F01 — Morning Worklist → Call → Re-sell

## Purpose

Luồng chính của Sales Rep mỗi buổi sáng: xem worklist task, mở hồ sơ khách, gọi điện,
ghi log, tạo follow-up task. Tương ứng J1 trong PRD.

## Surfaces Involved

- S01 — Worklist / Dashboard
- S03 — Customer 360 Detail
- P01 — Insight Panel
- P03 — Activity Timeline Panel
- M08 — Log Activity Modal
- M05 — Create / Edit Task Modal

## Happy Path

1. NV mở S01 lúc 8h → thấy danh sách task hôm nay (CALL_NOW, REORDER_NUDGE)
2. NV click task_row → navigate S03, tab Insight mặc định (P01)
3. NV đọc rationale_vi + value_at_stake, nhấn "Đặt Lịch" trên C03 → M05 mở để tạo follow-up task
4. NV gọi điện (ngoài app), sau đó click btn_log_activity → M08
5. NV điền outcome note, loại=call, lưu → activity ghi vào P03 timeline
6. NV click btn_create_task → M05, tạo follow-up due 7 ngày
7. Task mới xuất hiện trong P04 và S01 worklist hôm đó

## Branches / Edge Cases

- Khách không nghe máy: log activity type=call, outcome="Không liên hệ được"
- Khách yêu cầu gọi lại: tạo task due = ngày mai, priority P1

## Flow Contract

```yaml crm-contract
flow:
  goal: "Sales Rep xử lý worklist sáng: xem hồ sơ, gọi điện, ghi log, tạo follow-up"
  preconditions:
    - "user.role == sales"
    - "wh_action_queue has items for today"
  steps:
    - A-S01-001
    - A-S03-004
    - A-C03-002
    - A-S03-011
    - A-M08-003
    - A-S03-012
    - A-M05-003
  branches:
    - { when: "no tasks today", action: A-S01-004 }
    - { when: "task already done", action: A-S01-003 }
```
