# Phase 2 — Intermediate model: effort events tách theo action_type

## Context
Phụ thuộc Phase 1 (cột `claimed_action_types`, `source_activity_id` đã có trong staging). Model này KHÔNG phải mart cuối — chỉ là lớp nối + explode, để Phase 3 group theo tuần dễ dàng và test riêng được.

## Requirements
Tạo `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.sql`.

**Grain**: `(task_id, action_type)` — 1 task claim bundle N action_type sẽ ra N row (mỗi row đại diện "nỗ lực này được tính cho action_type này"). Task không có `claimed_action_types` (NULL — trước cutover, hoặc không phải action_queue_claim) → 1 row với `action_type = NULL`.

**Nguồn + join**:
```
task AS (SELECT * FROM {{ ref('stg_crm__task') }} WHERE source = 'action_queue_claim')
task_exploded AS (
  -- UNNEST claimed_action_types JSON array; NULL/rỗng → 1 row action_type=NULL
  SELECT task_id, party_id, assignee_user_id, created_at, completed_at, status,
         channel, outcome,
         COALESCE(unnest_action_type, NULL) AS action_type
  FROM task, LATERAL (giải JSON claimed_action_types bằng json_each/UNNEST DuckDB — xem cú pháp DuckDB JSON functions, KHÔNG dùng cú pháp Postgres)
)
activity AS (SELECT task_id, contact_outcome, occurred_at, staff_user_id, channel AS activity_channel
             FROM {{ ref('stg_crm__activity_log') }})
outcome_note AS (SELECT task_id, source_activity_id, COUNT(*) AS outcome_note_count
                  FROM {{ ref('stg_crm__note') }} WHERE note_type = 'outcome' AND deleted_at IS NULL
                  GROUP BY 1, 2)
new_tag AS (SELECT source_activity_id, party_id,
                    COUNT(*) FILTER (WHERE category = 'health_concern') AS health_concern_tags_new,
                    COUNT(*) FILTER (WHERE category != 'health_concern') AS other_tags_new
             FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY party_id, tag_id ORDER BY tagged_at) AS rn
                FROM {{ ref('stg_crm__party_tag') }}
             ) WHERE rn = 1  -- chỉ tính lần gắn đầu tiên (khớp Phase 0 quyết định #2)
             GROUP BY 1, 2)
customer_bridge AS (
  -- party_id -> customer_key qua crm_party_identity(identity_type='sapo_customer') -> dim_customers
  -- tham khảo cache_repository.py:172-176 / duckdb_reader.py cách join hiện có, KHÔNG tự chế lại join key khác
)
```

Join `task_exploded` ⟷ `activity` (via `task_id`) ⟷ `outcome_note`/`new_tag` (via `activity.activity_id` = `source_activity_id`, KHÔNG via `task_id` trực tiếp cho tag vì tag không có cột đó) ⟷ `customer_bridge` (via `party_id`).

**Output columns**: `task_id, party_id, customer_key, action_type, staff_user_id (assignee), week_start_date (từ completed_at nếu có, else created_at), channel, contact_outcome, is_reached (contact_outcome IN answered/replied/met), outcome_note_count, health_concern_tags_new, other_tags_new`.

## Files to create
- `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.sql`
- `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.yml` (schema doc, theo pattern `int_customer_sku_supply_tracking.yml` đã có)

## Implementation notes
- DuckDB JSON explode: dùng `json_each(claimed_action_types)` hoặc `UNNEST(from_json(claimed_action_types, '["VARCHAR"]'))` — kiểm tra cú pháp DuckDB version đang dùng trong `transformation/` (xem model khác đã parse JSON chưa, nếu chưa có tiền lệ thì test kỹ trong dbt trước khi merge).
- `staff_user_id` là CRM UUID — model NÀY để nguyên UUID, việc join sang `dim_staff.staff_key` để lấy tên thật làm ở Phase 3 (giữ nguyên tắc: intermediate model gần nguồn, mart mới denormalize).
- Không lọc `is_us_gift_recipient` ở tầng này (đây là effort/activity log, không phải action_type-based eligibility — khách bị exclude khỏi action queue có thể vẫn có activity log thật do rep tự gọi ngoài luồng; giữ nguyên để không mất dữ liệu, lọc ở Phase 3 nếu cần cho báo cáo).

## Tests
- `dbt test` — `not_null` trên `task_id`, `unique` trên `(task_id, action_type)`.
- Manual: claim 1 khách có 2 action (VD REORDER_PREEMPT + PROGRESS_CHECK) → xác nhận model ra đúng 2 row cùng `task_id`, khác `action_type`.
- Manual: log activity + tag health_concern trong luồng đó → `health_concern_tags_new = 1` đúng row của activity đó, không lặp qua các row action_type khác của cùng task (quyết định: gắn `health_concern_tags_new` vào MỌI row của task đó hay chỉ 1 row đại diện? Đề xuất: gắn vào mọi row action_type của task đó — vì thông tin thu thập được là do CUỘC GỌI đó, áp dụng chung cho mọi lý do gọi trong cùng task, không chia nhỏ theo action_type. Xác nhận lại khi implement nếu thấy vô lý).
