# Phase 03 — Mart tuần: `mart_crm_outreach_effort_by_action_weekly` — Implementation Report

Status: DONE

## Đã làm

### Files tạo/sửa
- `transformation/models/marts/crm/mart_crm_outreach_effort_by_action_weekly.sql` (mới)
- `transformation/models/marts/crm/schema.yml` (thêm entry cho model mới — file này đã có sẵn per-directory convention riêng cho `crm/`, dùng thay vì `transformation/models/marts/schema.yml` gốc)

Grain: `(staff_key, week_start_date, action_type)`. Chỉ build Bảng A (effort theo action_type) — KHÔNG build Bảng B/info-collected, đúng quyết định của phase file (info-collected đã ship ở `mart_staff_performance_weekly`, phase 0).

## Xác nhận Phase 2 build sạch trước khi dựa vào

`dbt run --select int_crm_outreach_effort_events` → PASS (0.52s). `dbt test --select int_crm_outreach_effort_events` → PASS 2/2 (`not_null(task_id)`, `unique_combination_of_columns(task_id, action_type)`). Model Phase 2 build clean với 2 thay đổi hand-patch đã ghi trong task (`status` column, `is_reached` mở rộng answered/replied/met/callback/refused/purchased) — không đụng vào file này.

## Phát hiện quan trọng: lệch giữa `.yml` doc và code thật của `int_crm_outreach_effort_events.staff_user_id`

Trước khi viết SQL, verify bằng `dbt show` trên data thật:
```
status=open:      staff_user_id NULL   18/18
status=done:      staff_user_id NULL    9/9
status=cancelled: staff_user_id NULL    9/9
status=doing:     staff_user_id NOT NULL 1/1
```
`.yml` của `int_crm_outreach_effort_events` mô tả `staff_user_id` là "crm_task.assignee_user_id" — nhưng code thật của model (`ap.staff_user_id` trong final SELECT) lấy từ `activity_primary` (staff của activity GẦN NHẤT đã log), KHÔNG phải task assignee. Activity chỉ tồn tại khi đã có cuộc gọi log — nên với `open`/`done`/`cancelled` gần như luôn NULL (task chưa có activity nào gắn tại thời điểm này). Join thẳng theo sketch gốc của phase file (`dim_staff ON crm_user_id = e.staff_user_id`) sẽ làm rỗng gần hết `tasks_claimed_pending`/`avg_days_to_complete` (chỉ 1/37 dòng còn staff).

**Quyết định** (không sửa file Phase 2, đúng constraint): mart này JOIN THẲNG `stg_crm__task` lấy `assignee_user_id` + `created_at`/`completed_at` (cùng pattern `mart_staff_performance_weekly.sql` đã dùng cho `tasks_assigned`/`tasks_completed`), dùng `assignee_user_id` để bridge qua `dim_staff` thay vì cột `staff_user_id` đã export sẵn của `int_crm_outreach_effort_events`. Verify lại bằng data thật: cách này cho 26/37 dòng có staff_key hợp lệ (10 dòng orphan CRM user chưa map Sapo, 1 dòng assignee_user_id NULL) — so với ~1/37 nếu theo đúng sketch gốc. Ghi rõ lý do + số liệu verify trong code comment (đầu file SQL) và trong `.yml` description.

**Cần Phase-02 owner xem lại**: đây là bug tiềm ẩn trong `int_crm_outreach_effort_events` (mô tả cột sai với thực thi) — không sửa ở đây vì ngoài phạm vi/file ownership của Phase 3, nhưng flag để coordinator quyết định có cần vá lại cột `staff_user_id` của model đó (đổi nghĩa thành assignee, hoặc thêm cột riêng) hay không.

`created_at`/`completed_at` cũng không được `int_crm_outreach_effort_events` truyền ra final SELECT (chỉ dùng nội bộ để tính `week_start_date`) — cần cho `avg_days_to_complete` nên cũng lấy thẳng từ `stg_crm__task` (không sửa model Phase 2).

## SQL logic thực tế

```sql
WITH events AS (SELECT * FROM int_crm_outreach_effort_events),
task_detail AS (
    SELECT task_id, assignee_user_id, created_at, completed_at
    FROM stg_crm__task WHERE source = 'action_queue_claim'
),
staff AS (SELECT staff_key, crm_user_id FROM dim_staff WHERE staff_id != '-1')
SELECT
    s.staff_key, e.week_start_date, e.action_type,
    COUNT(DISTINCT e.task_id) FILTER (WHERE e.status IN ('open','doing')) AS tasks_claimed_pending,
    COUNT(DISTINCT e.task_id) FILTER (WHERE e.status = 'done')           AS tasks_completed,
    ROUND(AVG(DATE_DIFF('day', td.created_at, td.completed_at))
        FILTER (WHERE e.status = 'done' AND td.completed_at IS NOT NULL), 1) AS avg_days_to_complete,
    COUNT(DISTINCT e.task_id)                             AS contacts_attempted,
    COUNT(DISTINCT e.task_id) FILTER (WHERE e.is_reached)  AS contacts_reached,
    ROUND(COUNT(DISTINCT e.task_id) FILTER (WHERE e.is_reached) * 100.0
        / NULLIF(COUNT(DISTINCT e.task_id), 0), 1)          AS reach_rate_pct
FROM events e
JOIN task_detail td ON td.task_id = e.task_id
JOIN staff s        ON s.crm_user_id = td.assignee_user_id
GROUP BY 1, 2, 3
```

`COUNT(DISTINCT task_id)` dùng cho MỌI cột đếm (task-count lẫn effort/reach) theo đúng yêu cầu giao việc — dù trong 1 group (staff,week,action_type) mỗi task_id chỉ xuất hiện 1 lần (grain gốc `(task_id, action_type)` đã unique, test Phase 2 xác nhận), DISTINCT là guard phòng thủ, không phải fix cho double-count thật.

**Xử lý status='cancelled'** (giá trị thật có trong data, không nằm trong danh sách open/doing/done mà task instructions liệt kê): KHÔNG tính vào `tasks_claimed_pending` (không phải đang chờ xử lý) cũng KHÔNG tính vào `tasks_completed` (không phải hoàn thành) — nhưng VẪN tính vào `contacts_attempted` (effort thật đã bỏ ra trước khi hủy). Verify bằng data thật: staff `3ba31a89...` tuần 2026-06-29 có 4 cancelled + 1 doing + 2 open → `tasks_claimed_pending=3` (doing+open), `tasks_completed=0`, `contacts_attempted=7` (đúng = 3+4) — khớp chính xác thiết kế.

`is_reached` hiện luôn NULL trong data thật (không có `contact_outcome` nào được set — mọi task action_queue_claim thật hiện tại chưa có activity log gắn kèm) → `FILTER (WHERE e.is_reached)` loại các dòng NULL đúng như FALSE (SQL 3-valued logic), `contacts_reached=0` toàn bộ — đúng thực trạng, không phải bug.

## Rollout

- `dbt run --select mart_crm_outreach_effort_by_action_weekly` → PASS (0.41s, external/parquet).
- `dbt test --select mart_crm_outreach_effort_by_action_weekly` → PASS 4/4:
  - `accepted_values(action_type)` (11 giá trị từ `seed_action_scenario_registry`, UNION NULL qua `where: action_type IS NOT NULL`)
  - `dbt_utils.unique_combination_of_columns(staff_key, week_start_date, action_type)`
  - `not_null(staff_key)`
  - `not_null(week_start_date)`
- Manual sanity check (4 dòng thật hiện có, action_type=NULL toàn bộ — chưa có claim nào có `claimed_action_types` sau cutover):
  - Mọi dòng: `reach_rate_pct = contacts_reached / contacts_attempted * 100` khớp tay (tất cả = 0/N = 0.0% vì `is_reached` luôn NULL hiện tại).
  - `avg_days_to_complete` verify bằng raw `created_at`/`completed_at` của 8 task done — tất cả claim+complete trong cùng phiên (vài giây tới vài phút), đúng `DATE_DIFF('day', ...) = 0`.

**Chưa bootstrap Metabase serving view** — theo constraint của task, việc này thuộc Phase 4 Track B (cần dừng Metabase). Mart hiện chưa query được từ Metabase cho tới khi bootstrap.

## Vấn đề vận hành: DuckDB lock

Gặp lock 3 lần (Dagster sensor/realtime job định kỳ ghi `sapo_warehouse.duckdb`) trong lúc chạy `dbt run`/`dbt show`. Poll `/proc/<pid>` tới khi free rồi retry, đúng theo development-rules — không force/kill.

## Unresolved / cần theo dõi

1. **Bug tiềm ẩn ở `int_crm_outreach_effort_events.staff_user_id`** (mô tả `.yml` nói "assignee_user_id" nhưng code thật lấy từ activity gần nhất) — Phase 3 đã tự workaround bằng join thẳng `stg_crm__task` trong file của mình (không sửa model Phase 2), nhưng cần Phase-02 owner/coordinator xác nhận có nên vá lại ý nghĩa cột đó hay không — cột hiện tại gần như vô dụng cho mọi mục đích cần biết "ai đang xử lý task này" khi chưa có activity.
2. Action_type breakdown vẫn chưa có dữ liệu thật (0/37 claim có `claimed_action_types` non-NULL) — cùng vấn đề đã ghi nhận ở phase-01/02 report, chờ cutover thật.
3. Cần bootstrap serving view Metabase (Phase 4 Track B) trước khi dashboard query được mart này.

Status: DONE
Summary: Mart `mart_crm_outreach_effort_by_action_weekly` (Bảng A, staff×tuần×action_type) tạo xong; dbt run+test PASS trên data thật (4/4 test, 4 dòng); phát hiện + xử lý 1 lệch nghĩa cột nghiêm trọng giữa `.yml` doc và code thật của `int_crm_outreach_effort_events.staff_user_id` bằng cách join thẳng `stg_crm__task` (không sửa file Phase 2) — verify data thật xác nhận cách này đúng (26/37 dòng có staff_key hợp lệ, so với ~1/37 nếu theo sketch gốc); manual sanity check reach_rate_pct + avg_days_to_complete + logic cancelled-status đều khớp tay trên data thật.
Concerns/Blockers: (1) `int_crm_outreach_effort_events.staff_user_id` doc/code mismatch cần Phase-02 owner xem lại (không blocking Phase 3 vì đã workaround trong file riêng); (2) chưa bootstrap Metabase serving view (Phase 4 Track B); (3) action_type vẫn 100% NULL trong data thật, chờ cutover claim đầu tiên có 2+ action_type để verify explode + breakdown trên data thật.
