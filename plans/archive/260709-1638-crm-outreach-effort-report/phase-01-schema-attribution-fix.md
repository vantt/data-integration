# Phase 1 — Track B: Schema fix để nối action_type + tag về đúng cuộc gọi (fix-forward only)

## Context
Xem plan.md "Sự thật đã xác minh" #1-3. Đây là điều kiện tiên quyết bắt buộc để phase 2/3 tách được hiệu quả theo action_type. KHÔNG backfill quá khứ — chỉ áp dụng từ ngày migration chạy trở đi.

## Requirements

### 1. `crm_task.claimed_action_types` — snapshot lúc claim
- Migration mới `crm/migrations/00XX_task_claimed_action_types.up.sql` (số thứ tự = số migration tiếp theo, kiểm tra `crm/migrations/` để lấy đúng số): `ALTER TABLE crm_task ADD COLUMN claimed_action_types TEXT` (JSON array string, VD `'["REORDER_PREEMPT","PROGRESS_CHECK"]'`, NULL cho task cũ và cho task không phải action_queue_claim).
- Sửa `crm/src/application/task_service.py::claim_customer_actions` (dòng ~221-237, nơi đã có sẵn `actions: list` đầy đủ action_type từng item) — serialize `json.dumps([a.action_type for a in actions])` vào cột mới khi tạo/update task claim.
- **Quyết định (xem plan.md câu hỏi mở #1)**: snapshot 1 LẦN lúc claim, KHÔNG cập nhật lại nếu action_type của khách đổi sau đó (VD do dbt refresh nâng REORDER_PREEMPT → REORDER_OVERDUE) — giữ đúng ý nghĩa "tại thời điểm quyết định gọi, đây là lý do".

### 1b. Zalo connect — capture thay tem *(bổ sung 2026-07-10, phục vụ Sprint Gọi Ra)*
- Form Log Activity (M08, `modal_log_activity.html` + `screen_customer_360_activity.py`): thêm checkbox "Đã kết bạn Zalo" — chỉ hiện khi `channel_type='call'` hoặc `'zalo'`.
- Lưu vào `custom_fields.zalo_connected = true` của activity (cột JSON đã tồn tại — KHÔNG cần migration).
- Export: xác nhận `crm_activity_log_export` đã mang `custom_fields`; nếu chưa → thêm cột. `stg_crm__activity_log` derive `zalo_connected` boolean từ JSON.
- Mart (phase 3 hoặc bổ sung phase 0 khi export xong): cột `zalo_connected_count` — KPI capture chính của sprint khi chưa có tem (target ≥50% reached).

### 1c. `outcome_reason='do_not_contact'` + suppression *(bổ sung 2026-07-10)*
- Thêm `"do_not_contact"` vào `VALID_OUTCOME_REASONS` (`crm/src/domain/entities/activity.py:60-71`) — khách yêu cầu đừng gọi nữa, khác `refused` thường (từ chối lần này nhưng gọi lại được).
- Suppression: worklist loại party có activity gần nhất mang reason này (đề xuất filter runtime trong `worklist_query_service` — không đổi schema party; chốt theo câu hỏi mở #5 plan.md).
- Test: log activity với reason `do_not_contact` → party biến mất khỏi worklist ở lần load kế tiếp.

### 2. `crm_party_tag.source_activity_id` — nối tag về activity
- Migration mới: `ALTER TABLE crm_party_tag ADD COLUMN source_activity_id TEXT` (nullable FK → `crm_activity_log.activity_id`, NULL nếu tag gắn ngoài luồng Log Activity — vẫn hợp lệ, không bắt buộc).
- Sửa `TagService.attach_tag()` (`crm/src/application/tag_service.py:30-52`) — thêm param `source_activity_id: Optional[str] = None`, truyền vào `PartyTag(...)`.
- Sửa `PartyTag` entity (`crm/src/domain/entities/profile.py` — cạnh `PartyTag` dataclass) thêm field `source_activity_id: Optional[str] = None`.
- Sửa write path: tìm chỗ tag-attach được gọi TRONG luồng Log Activity (M08) — theo test `crm/src/tests/test_health_domain_collect_and_tags_inline.py` đang test đúng luồng "collect and tags inline", đọc test này trước để biết chính xác handler nào (nhiều khả năng `screen_customer_360_activity.py` hoặc modal tags gọi từ đó) — truyền `activity.activity_id` vào làm `source_activity_id`. Các chỗ gọi `attach_tag()` khác (chip modal độc lập, không trong context Log Activity) giữ nguyên `source_activity_id=None`.

## Files to modify
- `crm/migrations/00XX_task_claimed_action_types.up.sql` + `.down.sql`
- `crm/migrations/00XX_party_tag_source_activity.up.sql` + `.down.sql`
- `crm/src/domain/entities/task.py` (nếu Task dataclass cần field mới để đọc lại — kiểm tra có cần hiển thị UI không, có thể không cần nếu chỉ dùng cho export)
- `crm/src/domain/entities/profile.py` (`PartyTag`)
- `crm/src/application/task_service.py` (`claim_customer_actions`)
- `crm/src/application/tag_service.py` (`attach_tag`)
- Handler nối tag ↔ activity trong luồng Log Activity (xác định qua test file nêu trên)
- `crm/sync/cache_schema.sql` KHÔNG cần đổi (đây là cache.db warehouse tables, khác `crm.db` nguồn — chỉ đổi nếu wh_* cần cột mới, không cần cho phase này vì export đi thẳng dbt, không qua cache.db)

## Export + staging (đồng thời sửa gap đã phát hiện)
- `orchestration/assets/crm_writeback_assets.py`: export query của `crm_task_export` — thêm `claimed_action_types` VÀ backfill gap đã phát hiện (`outcome, task_kind, channel, value_at_stake_vnd, top_affinity_product` đang bị bỏ sót dù cột đã tồn tại trong `crm_task`).
- `crm_party_tag_export` — thêm `source_activity_id`.
- `transformation/models/staging/stg_crm__task.sql` — thêm cột tương ứng vào SELECT.
- `transformation/models/staging/stg_crm__party_tag.sql` — thêm `source_activity_id`.
- Kiểm tra trước khi đổi: `channel`/`outcome`/`task_kind` thêm vào `stg_crm__task` có ảnh hưởng dashboard/mart nào đang SELECT * từ staging model này không (xem câu hỏi mở #3 plan.md) — grep `ref('stg_crm__task')` toàn repo trước khi sửa.

## Tests
- Unit test `task_service.py`: claim khách có 2 action pending → `claimed_action_types` JSON có đúng 2 phần tử, đúng thứ tự priority_rank.
- Unit test `tag_service.py`: `attach_tag(..., source_activity_id="act-123")` → `PartyTag.source_activity_id == "act-123"`; gọi không truyền param → vẫn hoạt động (backward-compatible), `source_activity_id=None`.
- Test luồng Log Activity end-to-end (tái dùng cấu trúc `test_health_domain_collect_and_tags_inline.py`): log activity + tag inline → note.source_activity_id VÀ party_tag.source_activity_id cùng trỏ về 1 activity_id.
- `dbt build --select stg_crm__task stg_crm__party_tag` sạch sau khi thêm cột.

## Rollback
- Down-migration đơn giản (`DROP COLUMN` — SQLite: cần rebuild table hoặc dùng cách chuẩn của migration framework hiện tại, xem migration cũ nào từng ALTER+rollback để theo đúng convention, VD `0032_task_kind.down.sql`).

## Rủi ro
- SQLite JSON column không có type-check — nếu code ghi sai format (không phải JSON array), phase 2 parse sẽ lỗi. Thêm validate JSON hợp lệ trước khi ghi trong `task_service.py`.
- Đổi `crm_task_export`/staging có thể phá dashboard/mart khác đang phụ thuộc cột thứ tự SELECT * — luôn chỉ định tên cột tường minh, không dùng SELECT *.
