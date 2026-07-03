---
phase: 1
title: "Claim API"
status: pending
priority: P1
dependencies: []
---

# Phase 1: Claim API

## Overview

Thêm endpoint `PATCH /worklist/actions/{action_id}/claim` để tạo task từ action item và gán cho người dùng hiện tại. Không thay đổi schema — `AND t.task_id IS NULL` trong `cache_repository.py` đã đủ để ẩn claimed items khỏi WorkList queue.

## Requirements

- **Functional:**
  - Nhân viên bấm "Nhận việc" → task được tạo với `source='action_queue'`, `source_ref=action_id`, `assignee=current_user`
  - Idempotency: nếu task đã tồn tại (người khác đã claim) → trả về soft response với tên người nhận, không tạo task mới
  - Sau claim: action item row bị xóa khỏi WorkList (HTMX `hx-swap="delete"`)
  - My Tasks section tự refresh sau khi claim (HTMX trigger hoặc page reload nhẹ)

- **Non-functional:**
  - Auth required: `current_user` phải tồn tại; 401 nếu không
  - Cache invalidation: gọi `worklist_svc.invalidate_cache()` sau khi tạo task thành công

## Architecture

```
PATCH /worklist/actions/{action_id}/claim
  ↓
1. Auth guard: lấy current_user_id
2. Lookup action từ cache: list_all_action_queue() → find by action_id
   (cần party_id, rationale_vi, action_type, priority cho task)
3. task_service.get_task_by_source_ref('action_queue', action_id)
   → if exists: return 200 HTML fragment "Đã được {assignee_name} nhận"
   → if None: create task
4. task_service.create_task({...})
5. worklist_svc.invalidate_cache()
6. Return: HTMLResponse("", 200) + hx-swap="delete" (caller removes row)
```

**Lý do không dùng 409:** HTMX xử lý 4xx như lỗi — sẽ hiện error toast. Thay vào đó trả về 200 với HTML fragment "đã được nhận bởi X" để HTMX swap in-place, thông báo thân thiện.

## Related Code Files

- Modify: `crm/src/adapters/inbound/web/screen_worklist.py`
  - Thêm `claim_action` vào `ActionStateWriter` protocol
  - Thêm `TaskCreatorForClaim` protocol (hoặc reuse `TaskWriter`)
  - Thêm route `PATCH /worklist/actions/{action_id}/claim`
- Modify: `crm/src/application/task_service.py`
  - Thêm method `claim_action_item(action_id, action, assignee_id) -> tuple[Task, bool]`
    - bool = True nếu tạo mới, False nếu đã tồn tại
- Modify: `crm/src/adapters/outbound/sqlite/task_repository.py`
  - Thêm `get_by_source_ref(source, source_ref) -> Optional[Task]`
  - (có thể `exists_by_source_ref` đã đủ, nhưng cần trả về Task để lấy assignee_name)
- Create: `crm/templates/fragments/_wl_action_claimed_notice.html`
  - Fragment inline nhỏ: "✓ Đã nhận bởi [tên]" — hiện khi ai đó đã claim rồi

## Implementation Steps

1. **task_repository.py** — thêm `get_by_source_ref()`:
   ```python
   def get_by_source_ref(self, source: str, source_ref: str) -> Optional[Task]:
       row = self._conn.execute(
           "SELECT * FROM crm_task WHERE source=? AND source_ref=? AND status NOT IN ('done','cancelled') LIMIT 1",
           (source, source_ref)
       ).fetchone()
       return _row_to_task(row) if row else None
   ```

2. **task_service.py** — thêm `claim_action_item()`:
   ```python
   def claim_action_item(self, action_id: str, action, assignee_id: str) -> tuple[Optional[Task], bool]:
       """Returns (task, is_new). is_new=False khi action đã có owner."""
       existing = self._task_repo.get_by_source_ref('action_queue', action_id)
       if existing:
           return existing, False
       rationale = (action.rationale_vi or "")[:80]
       title = f"[{action.action_type}] {rationale or action.customer_name}"
       task = Task(
           task_id=str(uuid.uuid4()),
           party_id=action.party_id,
           title=title,
           description=action.rationale_vi or None,
           priority=action.priority,
           status=TASK_STATUS_OPEN,
           source=TASK_SOURCE_ACTION_QUEUE,
           source_ref=action_id,
           assignee_user_id=assignee_id,
           created_at=utc_now(), updated_at=utc_now(),
       )
       self._task_repo.insert(task)
       if self._db: self._db.commit()
       return task, True
   ```

3. **screen_worklist.py** — thêm protocol và route:
   ```python
   class TaskClaimWriter(Protocol):
       def claim_action_item(self, action_id: str, action, assignee_id: str) -> tuple: ...

   @router.patch("/worklist/actions/{action_id}/claim")
   async def handle_claim_action(request: Request, action_id: str) -> Response:
       uid = _current_user_id(request)
       if not uid:
           return HTMLResponse("not authenticated", status_code=401)

       # Find action in cache for context
       all_actions = worklist_svc.list_all_action_queue()
       action = next((a for a in all_actions if a.action_id == action_id), None)
       if action is None:
           # Already gone from queue (e.g., dismissed earlier) — just remove row
           return HTMLResponse("", status_code=200)

       task, is_new = task_claim.claim_action_item(action_id, action, uid)

       if not is_new:
           # Already claimed — return inline notice (HTMX swaps row content)
           assignee_name = task.assignee_user_id or "nhân viên khác"
           # Resolve name from app_users if possible
           html = f'<div class="action-claimed-notice">✓ Đã được <strong>{assignee_name}</strong> nhận</div>'
           return HTMLResponse(html, status_code=200)

       worklist_svc.invalidate_cache()
       # Success: empty 200, HTMX hx-swap="delete" removes row
       # hx-trigger on My Tasks section will reload it
       return HTMLResponse("", status_code=200, headers={
           "HX-Trigger": '{"claimSuccess": true}'
       })
   ```

4. **Template: "Nhận việc" button** — thêm vào action item row (xem Phase 2 cho template path):
   ```html
   <button
     hx-patch="/worklist/actions/{{ action.action_id }}/claim"
     hx-swap="outerHTML"
     hx-target="closest .action-row"
     class="btn btn--sm btn--primary">
     Nhận việc
   </button>
   ```

## Success Criteria

- [ ] `PATCH /worklist/actions/{id}/claim` tạo task với `source='action_queue'`, `source_ref=id`, `assignee=current_user`
- [ ] Action item biến mất khỏi WorkList sau khi claim thành công
- [ ] Claim lần 2 (người khác hoặc cùng người) → trả về 200 HTML notice, không tạo task trùng
- [ ] `cache.invalidate_cache()` được gọi sau claim thành công
- [ ] 401 khi không có `current_user`

## Risk Assessment

- **Lookup action từ cache:** action vừa bị dismiss/snooze sẽ không còn trong `list_all_action_queue()`. Xử lý: trả về 200 empty → row biến mất (behavior đúng vì action đã không còn hiệu lực).
- **Assignee name display:** `task.assignee_user_id` là UUID, cần join với `crm_app_user` để lấy tên. Phase 1 có thể dùng UUID tạm; Phase 3 sẽ resolve đúng tên khi build C360 panel.
- **My Tasks section refresh:** Sau claim, My Tasks section cần cập nhật. Dùng `HX-Trigger: claimSuccess` để trigger HTMX `hx-get` trên My Tasks container, hoặc đơn giản là reload page (ít HTMX hơn nhưng UX đơn giản hơn cho v1).
