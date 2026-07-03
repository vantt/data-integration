---
phase: 3
title: "C360 Claimed State"
status: pending
priority: P2
dependencies: [1]
---

# Phase 3: C360 Claimed State

## Overview

Hiển thị trạng thái "đã được nhận" trên C360 insight panel khi action item đã có active task. C360 không dùng `AND t.task_id IS NULL` filter như WorkList — insight panel vẫn hiển thị tất cả action items của khách, kể cả những cái đã được nhận. Cần phân biệt trạng thái: unclaimed → "Nhận việc" / claimed → "👤 [tên] đang xử lý" + "Mở task".

## Requirements

- **Functional:**
  - C360 insight panel: action item đã claimed → hiện "👤 [tên nhân viên] đang xử lý" badge + "Mở task" link
  - "Mở task" link → `/customers/{party_id}?tab=tasks` (tab tasks đã có sẵn trên C360)
  - Action item chưa claimed → hiện "Nhận việc" button (cùng endpoint Phase 1)
  - Action item đã resolved (task done/activity logged) → giữ nguyên behavior hiện tại (`ActionTaskResolver.resolved_action_ids()`)

- **Non-functional:**
  - Tránh N+1 query: batch lookup tất cả claimed action_ids cho customer trong 1 query
  - Không thay đổi `InsightReader` hay query path của CacheInsight — chỉ enrich thông tin hiển thị

## Architecture

```
C360 Screen (screen_customer_360.py)
  ↓
_load_c360_data(party_id)
  ├─ existing: ActionTaskResolver.resolved_action_ids(party_id) → set[action_id]
  └─ NEW: ClaimedActionResolver.claimed_tasks_for_party(party_id) → dict[action_id, ClaimedTask]

ClaimedTask = namedtuple/dataclass: task_id, assignee_user_id, assignee_name

Template (C360 insight panel)
  for action in insight.actions:
    if action.action_id in resolved_ids:
      → [resolved UI - existing]
    elif action.action_id in claimed_tasks:
      → 👤 {claimed_tasks[action_id].assignee_name} đang xử lý  [Mở task →]
    else:
      → [Nhận việc button]
```

**Về `resolved_action_ids` hiện tại:** Protocol định nghĩa: "action_ids that have a resolved CRM task (outcome IS NOT NULL)". Claimed (task tồn tại nhưng chưa có outcome) là trạng thái khác — cần protocol riêng để tách bạch.

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py`
  - Thêm `ClaimedActionResolver` protocol
  - Thêm `claimed_action_resolver` param vào `make_customer_360_router()`
  - Pass `claimed_tasks` dict sang template
- Modify: `crm/src/adapters/outbound/sqlite/task_repository.py`
  - Thêm `get_claimed_tasks_by_action_ids(action_ids: list[str]) -> dict[str, Task]`
- Modify: `crm/src/composition.py` (hoặc equivalent DI setup)
  - Wire `ClaimedActionResolver` → `SQLiteTaskRepository`
- Modify: C360 insight template (file cần grep tìm)
  - Thêm claimed state UI vào action item render block
- Modify: `crm/src/adapters/outbound/sqlite/task_repository.py`
  - Thêm JOIN với `crm_app_user` để lấy `full_name` của assignee

## Implementation Steps

1. **task_repository.py** — thêm `get_claimed_tasks_by_action_ids()`:
   ```python
   def get_claimed_tasks_by_action_ids(
       self, action_ids: list[str]
   ) -> dict[str, Task]:
       """Batch: action_id → Task cho các action items đã được claim (active task tồn tại).
       
       Trả về dict rỗng khi action_ids rỗng.
       """
       if not action_ids:
           return {}
       placeholders = ",".join("?" * len(action_ids))
       rows = self._conn.execute(
           f"""SELECT t.*, u.full_name AS assignee_name
               FROM crm_task t
               LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
               WHERE t.source = 'action_queue'
                 AND t.source_ref IN ({placeholders})
                 AND t.status NOT IN ('done', 'cancelled')""",
           action_ids,
       ).fetchall()
       result = {}
       for row in rows:
           task = _row_to_task(row)
           task._assignee_name = row["full_name"] or row["assignee_user_id"] or "nhân viên"
           result[task.source_ref] = task
       return result
   ```

   **Lưu ý:** `crm_app_user` có `full_name` column — kiểm tra tên column chính xác bằng:
   ```bash
   grep -n "full_name\|display_name\|name" crm/migrations/0001_*.up.sql | head -20
   ```

2. **screen_customer_360.py** — thêm protocol và param:
   ```python
   class ClaimedActionResolver(Protocol):
       def claimed_tasks_for_party(self, party_id: str) -> dict[str, Any]:
           """action_id → task-like object với assignee_name field."""
           ...

   # Thêm param vào make_customer_360_router():
   def make_customer_360_router(
       ...,
       claimed_action_resolver: Optional[ClaimedActionResolver] = None,
   ) -> APIRouter:
   ```

   Trong `_load_base()` hoặc route handler, sau khi load insight:
   ```python
   claimed_tasks: dict = {}
   if claimed_action_resolver is not None and ins is not None:
       action_ids = [a.action_id for a in ins.actions]
       try:
           claimed_tasks = claimed_action_resolver.claimed_tasks_for_party(action_ids)
       except Exception as exc:
           log.warning("c360: claimed_tasks: %s", exc)
   ```

   Pass `claimed_tasks` sang template context.

3. **Implement `ClaimedActionResolver` adapter:**
   ```python
   class SQLiteClaimedActionResolver:
       def __init__(self, task_repo: SQLiteTaskRepository) -> None:
           self._repo = task_repo

       def claimed_tasks_for_party(self, action_ids: list[str]) -> dict:
           return self._repo.get_claimed_tasks_by_action_ids(action_ids)
   ```
   Hoặc wire trực tiếp `SQLiteTaskRepository` vì nó đã implement cả hai methods.

4. **Wire trong composition.py:**
   ```python
   # Tìm nơi `make_customer_360_router()` được gọi trong composition.py
   # Thêm claimed_action_resolver=task_repo vào call
   ```

5. **C360 insight template — thêm claimed state UI:**
   Tìm template:
   ```bash
   grep -rn "action_id\|actions.*loop\|resolved_ids" crm/templates/ --include="*.html" -l
   ```

   Thêm vào action item render block:
   ```html
   {% if action.action_id in resolved_ids %}
     {# existing resolved UI #}
     <span class="bdg bdg--good">✓ Đã xử lý</span>
   {% elif action.action_id in claimed_tasks %}
     {# NEW: claimed state #}
     {% set ct = claimed_tasks[action.action_id] %}
     <span class="bdg bdg--warn">
       👤 {{ ct._assignee_name }} đang xử lý
     </span>
     <a href="/customers/{{ action.party_id }}?tab=tasks"
        class="btn btn--sm btn--ghost">Mở task →</a>
   {% else %}
     {# Unclaimed: show "Nhận việc" button #}
     <button
       hx-patch="/worklist/actions/{{ action.action_id }}/claim"
       hx-swap="outerHTML"
       hx-target="closest .action-item"
       class="btn btn--sm btn--primary">
       Nhận việc
     </button>
   {% endif %}
   ```

6. **Test thủ công:**
   - Claim 1 action item từ WorkList
   - Mở C360 của khách đó → action item hiện "👤 [tên] đang xử lý"
   - Khách khác không claim → hiện "Nhận việc"
   - Task done → action item không còn trong insight (hoặc hiện resolved state)

## Success Criteria

- [ ] C360 insight panel phân biệt 3 trạng thái: unclaimed / claimed / resolved
- [ ] Claimed state hiển thị đúng tên assignee (không phải UUID)
- [ ] "Mở task" link dẫn đến đúng `/customers/{party_id}?tab=tasks`
- [ ] "Nhận việc" button trên C360 dùng cùng endpoint `/worklist/actions/{id}/claim`
- [ ] Batch query — không có N+1 (1 query cho tất cả action_ids của customer)
- [ ] `claimed_action_resolver=None` → graceful degradation (chỉ hiện unclaimed UI cho tất cả)

## Risk Assessment

- **`crm_app_user.full_name` column name:** Cần verify tên column chính xác trước khi viết query.
- **`ins.actions` có thể rỗng:** `if ins is not None and ins.actions` để guard.
- **C360 template structure chưa biết chính xác:** Grep tìm file trước khi edit. Nếu action items không render trong Jinja2 loop mà dùng HTMX fragment riêng, cần xử lý thêm.
- **`_assignee_name` là dynamic attr trên Task dataclass:** Nếu `Task` là `@dataclass` frozen, cần dùng dict wrapper hoặc thêm optional field vào Task entity. Phương án an toàn: trả về `dict[action_id, dict]` từ resolver thay vì Task object.
