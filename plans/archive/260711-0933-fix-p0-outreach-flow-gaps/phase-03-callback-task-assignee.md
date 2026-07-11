# Phase 03 — Task "Gọi lại"/"Theo dõi" phải gán đúng người vừa hẹn

## Bối cảnh

`execute_side_effects()` bước 4 (callback task) và bước 5 (follow-up task) trong
`activity_side_effects.py:125-154` tạo task mới KHÔNG có `assignee_user_id`:

```python
# 4. Callback task
if create_callback_task and callback_at:
    if task_svc is not None:
        try:
            task_svc.create_task({
                "party_id": party_id,
                "title": f"Gọi lại: {_display_name()}",
                "due_at": callback_at,
                "source": "manual",
                "priority": 0,
            })
        except Exception as exc:
            log.warning("side_effects: create_callback_task %s: %s", party_id, exc)

# 5. Follow-up task
if schedule_followup_at:
    if task_svc is not None:
        try:
            task_svc.create_task({
                "party_id": party_id,
                "title": f"Theo dõi: {_display_name()}",
                "due_at": schedule_followup_at,
                "source": "manual",
                "priority": 0,
            })
        except Exception as exc:
            log.warning("side_effects: schedule_followup %s: %s", party_id, exc)
```

`TaskService.create_task()` (`task_service.py:96-138`) đọc `assignee_user_id` từ `task_data` nếu có
(dòng ~130: `assignee_user_id=task_data.get("assignee_user_id")`) — không có thì `None`. Task rơi vào
"📥 Hàng Đợi Chung" (S01), ai cũng Nhận được thay vì chính người vừa cam kết hẹn khách.

`execute_side_effects()` đã nhận `actor_id: Optional[str]` — chính là user đang thực hiện cuộc gọi/log
— dùng thẳng làm `assignee_user_id`.

## Thiết kế fix

Thêm `"assignee_user_id": actor_id` và `"created_by": actor_id` vào cả 2 dict truyền cho
`task_svc.create_task()`. Giữ nguyên `"source": "manual"` (KHÔNG đổi — `derive_task_kind()` với
`source="manual"` + có `party_id` → `(TASK_KIND_CONTACT, False)`, đúng ý nghĩa task liên hệ; đổi source
là thay đổi ngoài phạm vi P0 #3, YAGNI).

Nếu `actor_id` là `None` (activity ghi bởi hệ thống không có staff — hiếm, ví dụ import), task vẫn tạo
với `assignee_user_id=None` như cũ — không regress trường hợp không xác định được actor.

## Files to modify

1. `crm/src/application/activity_side_effects.py`

## Implementation steps

Sửa bước 4 (dòng ~129-140):
```python
    if create_callback_task and callback_at:
        if task_svc is not None:
            try:
                task_svc.create_task({
                    "party_id": party_id,
                    "title": f"Gọi lại: {_display_name()}",
                    "due_at": callback_at,
                    "source": "manual",
                    "priority": 0,
                    "assignee_user_id": actor_id,
                    "created_by": actor_id,
                })
            except Exception as exc:
                log.warning("side_effects: create_callback_task %s: %s", party_id, exc)
```

Sửa bước 5 (dòng ~143-154):
```python
    if schedule_followup_at:
        if task_svc is not None:
            try:
                task_svc.create_task({
                    "party_id": party_id,
                    "title": f"Theo dõi: {_display_name()}",
                    "due_at": schedule_followup_at,
                    "source": "manual",
                    "priority": 0,
                    "assignee_user_id": actor_id,
                    "created_by": actor_id,
                })
            except Exception as exc:
                log.warning("side_effects: schedule_followup %s: %s", party_id, exc)
```

## Tests

- `docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest tests/test_activity_disposition_api_routes.py tests/test_task_service_title_fallback.py -q"`.
- Thêm test mới: gọi `execute_side_effects()` với `create_callback_task=True, callback_at="2026-07-13T10:00:00Z"`,
  `actor_id="staff-1"` → assert `task_svc.create_task` được gọi với `assignee_user_id="staff-1"`. Tương
  tự cho `schedule_followup_at`. Test đối chứng `actor_id=None` → `assignee_user_id=None` (không lỗi).

## Verify thủ công

1. Trong cockpit, T2 chọn outcome "Hẹn lại", chọn mốc "+2h", giữ checkbox "tạo task nhắc" đã tick →
   Lưu.
2. Vào Worklist: task "Gọi lại: <tên khách>" phải xuất hiện trong **"Đã Claim"** (của người vừa gọi),
   **không** nằm trong "📥 Hàng Đợi Chung".
3. Tương tự với M08 checkbox "Lên lịch theo dõi" (schedule_followup).

## Risks / rollback

- Rủi ro rất thấp: thay đổi additive, chỉ thêm field vào dict, không đổi contract hàm/route. Rollback
  = revert diff.
