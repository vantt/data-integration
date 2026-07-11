# Phase 3 — Mart tuần: `mart_crm_outreach_effort_weekly`

## Context
Phụ thuộc Phase 2 (`int_crm_outreach_effort_events`, grain `task_id × action_type`). Mart này rollup lên `(staff, tuần, action_type)` để Metabase query trực tiếp.

## ⚠️ Cạm bẫy double-count (đọc trước khi viết SQL)
`int_crm_outreach_effort_events` có N row cho 1 task nếu task bundle N action_type. Nếu SUM thẳng `health_concern_tags_new`/`outcome_note_count` trên các row đã explode → đếm nhân N lần cho cùng 1 cuộc gọi thật. Bắt buộc:
- **Effort/reach metrics** (số cuộc gọi, reach rate) → đếm theo `COUNT(DISTINCT task_id)` hoặc tách riêng theo action_type (đúng ý nghĩa: 1 task "phục vụ" N action_type, effort đó có thể coi là dùng chung hoặc chia đều — quyết định: coi là dùng CHUNG, tức 1 task claimed 2 action_type = 2 cuộc gọi "đóng góp" cho 2 action_type đó, không chia 0.5 mỗi bên — giữ đơn giản, chấp nhận effort bị đếm ở cả 2 dòng vì đó là sự thật: rep dùng 1 cuộc gọi giải quyết cả 2 vấn đề).
- **Info-collected metrics** (tag mới, note outcome) → PHẢI tính ở mức `task_id` DISTINCT trước (1 lần/task), rồi mới join ngược vào từng action_type row nếu cần hiển thị per-action_type, hoặc đơn giản hơn: chỉ báo cáo info-collected ở mức KHÔNG tách action_type (join thẳng vào 1 dòng tổng theo staff×tuần, tách riêng khỏi bảng action_type-sliced) — **đề xuất chọn cách này để tránh double-count hoàn toàn**, xem "Output shape" bên dưới.

## Output shape — 2 bảng con trong cùng 1 mart (hoặc 2 mart riêng nếu rõ ràng hơn)

**Bảng A — effort theo action_type** (grain `staff_key × week_start_date × action_type`):
`tasks_claimed, tasks_completed, avg_days_to_complete, contacts_attempted, contacts_reached, reach_rate_pct` — đếm trên `int_crm_outreach_effort_events`, KHÔNG kèm tag/note count.

**Bảng B — info thu thập, KHÔNG tách action_type** (grain `staff_key × week_start_date`):
`outcome_notes_count, health_concern_tags_new, other_tags_new` — tính từ `int_crm_outreach_effort_events` sau khi `SELECT DISTINCT task_id, ...` (loại bỏ explode) rồi mới SUM.

Quyết định implement: 2 model riêng (`mart_crm_outreach_effort_by_action_weekly.sql` + phần info-collected GỘP THẲNG vào `mart_staff_performance_weekly` đã mở rộng ở Phase 0, KHÔNG tạo bảng B riêng) — tránh 2 nguồn số cho cùng 1 khái niệm "tag mới thu thập" nếu Phase 0 đã làm rồi. Kiểm tra: nếu Phase 0 dùng trực tiếp `stg_crm__party_tag`/`stg_crm__note` (không qua task_id) thì số ở Phase 0 đã ĐÚNG (không bị explode) — giữ nguyên Phase 0 làm nguồn info-collected duy nhất, Phase 3 chỉ cần làm Bảng A.

## Files to create
- `transformation/models/marts/crm/mart_crm_outreach_effort_by_action_weekly.sql`
- Thêm entry vào `transformation/models/marts/schema.yml`

## SQL sketch (Bảng A only)
```sql
WITH events AS (SELECT * FROM {{ ref('int_crm_outreach_effort_events') }}),
staff AS (SELECT staff_key, staff_id, crm_user_id, full_name FROM {{ ref('dim_staff') }} WHERE staff_id != '-1')
SELECT
  s.staff_key, s.full_name,
  e.week_start_date, e.action_type,
  COUNT(DISTINCT e.task_id) FILTER (WHERE e.status IN ('open','doing')) AS tasks_claimed_pending,
  COUNT(DISTINCT e.task_id) FILTER (WHERE e.status = 'done')          AS tasks_completed,
  COUNT(*)                                                              AS contacts_attempted,
  COUNT(*) FILTER (WHERE e.is_reached)                                  AS contacts_reached,
  ROUND(COUNT(*) FILTER (WHERE e.is_reached) * 100.0 / NULLIF(COUNT(*),0), 1) AS reach_rate_pct
FROM events e
LEFT JOIN staff s ON s.crm_user_id = e.staff_user_id
WHERE s.staff_key IS NOT NULL
GROUP BY 1,2,3,4
```
(Giữ style/pattern giống `mart_staff_performance_weekly.sql` đã có — cùng convention DATE_TRUNC ICT, cùng cách exclude staff_key IS NULL.)

## dbt tests (schema.yml)
- `not_null`: staff_key, week_start_date
- `unique` (compound): `(staff_key, week_start_date, action_type)` — kể cả action_type NULL (dữ liệu pre-cutover) phải unique riêng theo NULL
- `accepted_values` cho `action_type`: danh sách từ `seed_action_scenario_registry.action_type` UNION NULL

## Rollout
- `dbt run --select mart_crm_outreach_effort_by_action_weekly`
- Bootstrap serving view (Metabase phải restart để thấy mart mới — theo [[feedback_new_mart_crm_serving_integration]])
- KHÔNG cần rebuild container CRM (mart này không phục vụ ngược CRM, chỉ phục vụ Metabase/BI)

## Rủi ro
- Data thưa trong vài tuần đầu sau cutover (action_type chỉ có dữ liệu từ ngày Phase 1 ship) — dashboard Phase 4 phải ghi chú rõ "action_type breakdown chỉ có từ [ngày cutover]", không để trống gây hiểu nhầm là 0 hoạt động.
