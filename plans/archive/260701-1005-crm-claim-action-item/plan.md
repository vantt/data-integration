---
title: "CRM: Claim Action Item — WorkList + C360"
description: "Nhân viên nhận việc từ action queue, tạo task, track ownership rõ ràng"
status: completed
priority: P2
branch: "main"
tags: ["crm", "worklist", "action-queue", "task"]
blockedBy: []
blocks: []
created: "2026-07-01T03:07:44.779Z"
createdBy: "ck:plan"
source: skill
---

# CRM: Claim Action Item — WorkList + C360

## Overview

Thêm gesture "Nhận việc" (claim) để nhân viên chuyển action queue item thành task được gán cho mình.
Hiện tại không có luồng rõ ràng giữa action item và task — nhân viên chỉ có thể dismiss/snooze chứ không "nhận".

**Key insight từ codebase:** `cache_repository.py` đã có `AND t.task_id IS NULL` — action items tự biến mất khỏi WorkList khi có active task. Tạo task là đủ để "claim", không cần thêm trạng thái vào `crm_action_state`. Không cần migration.

**Scope:** WorkList chỉ claim. C360 mới log activity (M08 modal đã có `task_id` param).

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Claim API](./phase-01-claim-api.md) | Done (per-customer, not per-action) |
| 2 | [WorkList Task Row UX](./phase-02-worklist-task-row-ux.md) | Done |
| 3 | [C360 Claimed State](./phase-03-c360-claimed-state.md) | Done |

## Acceptance Criteria

- [x] Bấm "Nhận việc" trên WorkList → ALL action items for customer biến mất → task xuất hiện trong My Tasks section (VERIFIED: endpoint calls `claim_customer_actions()`)
- [x] Bấm "Nhận việc" trên C360 insight panel → action items hiện "👤 [tên] đang xử lý" + "Trả việc" button (VERIFIED: c360_insight_panel.html lines 26–38)
- [x] Race condition safe: người thứ hai claim cùng customer → endpoint returns existing task, no duplicate created (VERIFIED: `claim_customer_actions()` checks `get_customer_claim()` first)
- [x] C360 M08 modal nhận `task_id` từ URL param → log activity gắn vào task (VERIFIED: _wl_row.html line 235)
- [x] Không thay đổi pipeline/mart layer (VERIFIED: only CRM schema changes)

## Architecture Notes

```
WorkList Action Queue (cache_repository UNION ALL)
  ├─ Filters: AND t.task_id IS NULL  ← auto-hides claimed items
  └─ "Nhận việc" button → PATCH /worklist/actions/{id}/claim
                              ↓
                         TaskService.create_task()
                              ↓
                         Action item disappears (hx-swap="delete")
                         Task appears in My Tasks section

WorkList My Tasks (task_service.list_tasks)
  └─ Task row: title + customer link → /customers/{party_id}?tab=tasks
                                         M08 pre-filled với task_id

C360 Insight Panel (InsightReader.get_customer_insight)
  ├─ Does NOT filter by t.task_id (different query path)
  └─ Uses ActionTaskResolver.resolved_action_ids() for "resolved" state
     → Extend to also return "claimed" state (task exists, no outcome yet)
```

## Files Involved

| File | Change |
|------|--------|
| `crm/src/adapters/inbound/web/screen_worklist.py` | Add claim route + `claim_action` to protocol |
| `crm/src/application/task_service.py` | `claim_action_item()` method (create task + return owner if exists) |
| `crm/src/adapters/outbound/sqlite/task_repository.py` | `get_task_by_source_ref()` method |
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py` | Extend `ActionTaskResolver` protocol |
| `crm/src/adapters/outbound/sqlite/task_repository.py` | `claimed_tasks_by_action_ids()` method |
| `crm/templates/fragments/_wl_action_row.html` (or equivalent) | "Nhận việc" button |
| `crm/templates/fragments/_wl_task_row.html` (or equivalent) | Customer link on task row |
| `crm/templates/` (C360 insight panel) | Claimed state display |

## Implementation Notes

**Design deviation from plan:** The plan describes per-action claiming (`source='action_queue', source_ref=action_id`), but the actual implementation uses per-customer claiming (`source='action_queue_claim', source_ref=party_id`).

- **Endpoint `/worklist/actions/{id}/claim`**: Implemented (line 382 in screen_worklist.py) but claims ALL actions for a customer at once via `task_claim.claim_customer_actions()`.
- **Per-action method `claim_action_item()`**: Exists in task_service.py (line 272) but is not wired to any HTTP endpoint.
- **C360 claimed state**: Fully implemented in c360_insight_panel.html (line 26–38) showing "👤 [assignee_name] đang xử lý" + "Trả việc" button for per-customer claims.
- **Claim endpoint behavior**: Reloads entire worklist after claiming so action queue refreshes and claimed items disappear (filtered by `AND t.task_id IS NULL` in cache_repository).

**Why per-customer instead of per-action:** Per-customer claiming prevents race conditions when multiple staff attempt to claim the same customer — second claim attempt returns soft error message showing existing assignee.

## Dependencies

Phase 2 phụ thuộc Phase 1 (cần endpoint để test button).
Phase 3 độc lập với Phase 2, có thể làm song song với Phase 2 sau Phase 1.
