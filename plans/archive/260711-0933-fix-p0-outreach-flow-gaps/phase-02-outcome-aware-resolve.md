# Phase 02 — Resolve theo outcome: no_answer/busy auto-snooze thay vì dismiss

## Bối cảnh

`activity_side_effects.execute_side_effects()` bước 7 "Bulk-resolve" (`activity_side_effects.py:164-183`)
chạy **vô điều kiện** bất kể `contact_outcome`:

```python
skip_ids = set(complete_task_ids)
remaining_task_ids = [t for t in resolve_task_ids if t not in skip_ids]
if resolve_action_ids or remaining_task_ids:
    uid: Optional[str] = actor_id or None
    if action_state is not None:
        for aid in resolve_action_ids:
            try:
                action_state.dismiss(aid, user_id=uid)
            except Exception as exc:
                log.warning("side_effects: dismiss action %s: %s", aid, exc)
    if task_svc is not None:
        for tid in remaining_task_ids:
            try:
                task_svc.transition_status(tid, "done")
            except Exception as exc:
                log.warning("side_effects: bulk-resolve transition task %s: %s", tid, exc)
```

`action_state.dismiss()` ghi CẢ `crm_action_state` (episode) LẪN `crm_action_dismissal` TTL **30 ngày**
theo (party_id, action_type) (`action_state_repository.py:40-79`). Khi outcome là `no_answer`/`busy`
(gọi không thành công), tín hiệu thật (khách vẫn cần được liên hệ) bị chôn 30 ngày — sai với ý nghĩa
"đã xử lý xong".

**Quyết định user (2026-07-11, ①)**: `no_answer`/`busy` → auto-snooze thay vì dismiss. Số ngày cụ thể
chưa chốt (report để mở "1 hay 3?") — plan này chọn **2 ngày** làm mặc định (điểm giữa), dễ đổi thành
hằng số cấu hình sau nếu user muốn số khác.

## Thiết kế fix

`execute_side_effects()` đã nhận `activity` object (có `.contact_outcome`) — tận dụng trực tiếp, KHÔNG
cần thêm param mới. Thêm hằng số + logic rẽ nhánh trong bước 7:

- outcome ∈ `{"no_answer", "busy"}` → với mỗi `action_id` trong `resolve_action_ids`: gọi
  `action_state.snooze(aid, until_date, user_id=uid)` thay vì `dismiss()`. `remaining_task_ids`
  **KHÔNG** transition sang done — giữ nguyên `open`/`doing` để còn thấy trong "Đã Claim" cho lần gọi
  lại (claimed task đại diện quyền sở hữu, không nên tự đóng khi cuộc gọi trượt).
- outcome khác (mọi giá trị còn lại: `answered`, `purchased`, `refused`, `wrong_number`, `callback`,
  `met`, `not_met`, `replied`, v.v.) → giữ nguyên hành vi hiện tại (dismiss action + done task).

`action_state.snooze()` đã có sẵn signature `(action_id: str, until_date: str, user_id: Optional[str])`
— `until_date` dạng `YYYY-MM-DD` (xem cách `screen_worklist.py::handle_snooze_action` dòng 542-555 tính
— tái dùng đúng công thức `(datetime.now(timezone.utc) + timedelta(days=N)).strftime("%Y-%m-%d")`).

## Files to modify

1. `crm/src/application/activity_side_effects.py`

## Implementation steps

Thêm hằng số đầu file (sau `log = logging.getLogger(__name__)`, dòng ~26):
```python
# Quyết định UX 2026-07-11 (①): outcome cho thấy cuộc gọi KHÔNG thành công (khách không nhấc máy /
# đang bận) không nên "resolve" tín hiệu như một cuộc gọi thành công — snooze ngắn hạn để action
# quay lại hàng đợi thay vì dismiss TTL 30 ngày (mất tín hiệu thật).
_NO_CONTACT_OUTCOMES = frozenset({"no_answer", "busy"})
_NO_CONTACT_SNOOZE_DAYS = 2
```

Import thêm ở đầu file:
```python
from datetime import datetime, timedelta, timezone
```
(file đã import `datetime, timezone` — chỉ cần bổ sung `timedelta` vào import hiện có ở dòng 21.)

Sửa bước 7 (dòng 164-183) thành:
```python
# 7. Bulk-resolve (dismiss actions + complete tasks) from the cockpit outcome
# bar's rail — skip any task_id already handled by step 6 above so a task
# showing up in both complete_task_ids and resolve_task_ids is not
# transitioned twice.
skip_ids = set(complete_task_ids)
remaining_task_ids = [t for t in resolve_task_ids if t not in skip_ids]
if resolve_action_ids or remaining_task_ids:
    uid: Optional[str] = actor_id or None
    outcome = getattr(activity, "contact_outcome", None) or ""
    if outcome in _NO_CONTACT_OUTCOMES:
        # Cuộc gọi không thành công — snooze ngắn hạn, KHÔNG dismiss (quyết định ①).
        # Claimed task liên quan giữ nguyên trạng thái (không auto-done) để còn gọi lại.
        until_date = (
            datetime.now(timezone.utc) + timedelta(days=_NO_CONTACT_SNOOZE_DAYS)
        ).strftime("%Y-%m-%d")
        if action_state is not None:
            for aid in resolve_action_ids:
                try:
                    action_state.snooze(aid, until_date, user_id=uid)
                except Exception as exc:
                    log.warning("side_effects: snooze action %s: %s", aid, exc)
    else:
        if action_state is not None:
            for aid in resolve_action_ids:
                try:
                    action_state.dismiss(aid, user_id=uid)
                except Exception as exc:
                    log.warning("side_effects: dismiss action %s: %s", aid, exc)
        if task_svc is not None:
            for tid in remaining_task_ids:
                try:
                    task_svc.transition_status(tid, "done")
                except Exception as exc:
                    log.warning("side_effects: bulk-resolve transition task %s: %s", tid, exc)
```

## Tests

- `docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest tests/test_bulk_resolve_endpoint.py tests/test_claim_context_snooze_r14.py tests/test_activity_disposition_api_routes.py tests/test_disposition_strip_v2.py -q"`.
- Thêm test mới trong `test_bulk_resolve_endpoint.py` (hoặc file tương đương side-effects): giả
  `action_state`/`task_svc` fake, gọi `execute_side_effects()` với `activity.contact_outcome="no_answer"`
  + `resolve_action_ids=["a1"]` + `resolve_task_ids=["t1"]` → assert `action_state.snooze` được gọi
  (KHÔNG gọi `dismiss`), `task_svc.transition_status` **KHÔNG** được gọi cho `t1`. Test đối chứng với
  `contact_outcome="answered"` → assert hành vi cũ (dismiss + done) không đổi.

## Verify thủ công

1. Vào cockpit khách có action CALL_NOW, bấm Gọi → T2 chọn outcome "Không bắt" → Lưu.
2. Vào lại Worklist: action đó phải biến mất khỏi "Cơ Hội Hệ Thống" trong 2 ngày rồi **tự xuất hiện
   lại** (không phải biến mất 30 ngày). Nếu có claimed task liên quan (do đã claim trước khi gọi), task
   đó vẫn `open`, không tự chuyển `done`.
3. Đối chứng: outcome "Đã nghe" → action dismiss như cũ (không snooze).

## Risks / rollback

- Rủi ro thấp-trung: thay đổi hành vi runtime (không chỉ additive) — cần chạy đủ test suite bulk-resolve
  trước khi merge. Rollback = revert diff, không có migration DB liên quan.

## Câu hỏi mở

- Số ngày snooze mặc định (2) là lựa chọn tạm — nếu user muốn số khác (1 hoặc 3, như report gốc đề
  cập) chỉ cần đổi hằng số `_NO_CONTACT_SNOOZE_DAYS`.

## Amendment (2026-07-11) — gap tìm thấy qua red-team review độc lập của `plans/260711-0838-worklist-claim-call-log-flow-fixes`

**Critical: fix ở `execute_side_effects()` bị vô hiệu hóa bởi 1 đường resolve song song khác, UI tự
show đúng lúc outcome cần bảo vệ.** Grep-verify lại (2026-07-11), KHÔNG chỉ dựa vào review report gốc:

- `c360_call_cockpit_panel.html:944-945` — nút `id="s14-strip-zalofollowup"` (`+Nhắn Zalo`),
  `style="display:none"` mặc định.
- `c360_call_cockpit_panel.html:1237-1238` — JS: `zaloBtn.style.display = (S.chosenOutcome ===
  'no_answer') ? '' : 'none';` — nút CHỈ hiện khi outcome đúng là `no_answer`, tức đúng lúc phase này
  cần bảo vệ tín hiệu nhất.
- `c360_call_cockpit_panel.html:1248-1259` (`s14StripZaloFollowup()`) — đọc CÙNG hidden field
  `#s14-resolve-action-ids`/`#s14-resolve-task-ids` mà `s14StripSave()` dùng, POST tới
  `/customers/{party_id}/reason/resolve-async`.
- `screen_customer_360_activity.py:390-448` (`handle_resolve_async`) → gọi `_bulk_resolve()`
  (`outcome_resolve_helpers.py:19-62`) — **KHÔNG nhận outcome, KHÔNG gate gì cả**: luôn
  `action_state.dismiss(...)` (ghi TTL 30 ngày) + `task_svc.transition_status(tid, "done")` vô điều
  kiện.

**Failure scenario**: rep chọn outcome "Không bắt" → phase này (execute_side_effects) đúng: action
snooze 2 ngày, task giữ open. Rep bấm luôn "+Nhắn Zalo" (nút mà chính UI vừa hiện ra cho outcome này)
→ `resolve-async` dismiss + done NGAY LẬP TỨC, undo hoàn toàn effect vừa làm — action mất 30 ngày dù
outcome vẫn là "Không bắt". Acceptance criteria #4 của `plan.md` tổng ("action snooze N ngày, KHÔNG
dismiss") **không đạt được** trong flow thực tế nếu rep dùng nút Zalo follow-up, chỉ đúng khi rep
finalize thẳng không bấm nút đó.

**Fix cần bổ sung** (mở rộng phạm vi Files to modify sang `screen_customer_360_activity.py` +
`outcome_resolve_helpers.py`): `handle_resolve_async`/`_bulk_resolve` cần biết `contact_outcome` của
activity hiện tại (đọc từ draft `activity_id`/`S.draftId` gửi kèm, hoặc `S.chosenOutcome` gửi thẳng
trong request body của `s14StripZaloFollowup()`) và áp dụng CÙNG logic `_NO_CONTACT_OUTCOMES` gate như
bước 7 của `execute_side_effects()` — không viết lại logic 2 lần, factor ra 1 hàm helper dùng chung
nếu khả thi (`_NO_CONTACT_OUTCOMES`/`_NO_CONTACT_SNOOZE_DAYS` đã định nghĩa trong
`activity_side_effects.py`, có thể import hoặc di chuyển ra module dùng chung).
