# Phase 0 — Track A: Extend `mart_staff_performance_weekly` (no schema change, ship ngay)

## Context
`transformation/models/marts/crm/mart_staff_performance_weekly.sql` hiện đo: activities_total, activities_outbound, contacts_reached, reach_rate_pct, tasks_assigned, tasks_completed, orders_sold, revenue_vnd — grain `staff_key × week_start_date`. Không có "thông tin thu thập" (note outcome, tag sức khỏe mới). Dữ liệu nguồn (`stg_crm__note`, `stg_crm__party_tag`) ĐÃ tồn tại, không cần export gì thêm — chỉ cần thêm CTE + cột.

## Requirements
Thêm 4 nhóm cột mới vào mart hiện có, KHÔNG đổi grain, KHÔNG đổi cột cũ:

1. **`outcome_notes_count`** — số note `note_type='outcome'` tác giả là staff đó, theo tuần `created_at`.
2. **`health_concern_tags_new`** — số tag `category='health_concern'` gắn LẦN ĐẦU cho 1 party (đếm theo `(party_id, tag_id)` xuất hiện sớm nhất, tránh đếm trùng nếu bị gắn lại — xem plan.md câu hỏi mở #2), theo `tagged_by` = staff, theo tuần `tagged_at`.
3. **`other_tags_new`** — tương tự #2 nhưng `category != 'health_concern'` (hoặc tất cả category khác, xem `stg_crm__party_tag` để liệt kê category thực tế đang dùng).
4. **`channel_breakdown`** — số activity theo `channel` (phone/zalo/sms/in_store/other) — có thể làm 1 cột JSON/MAP hoặc 4 cột riêng `activities_phone/zalo/sms/other`; ưu tiên 4 cột riêng cho dễ query Metabase (tránh JSON parsing trong dashboard).

5. **Phễu gọi sprint** *(bổ sung 2026-07-10 — phục vụ Sprint Gọi Ra 45 ngày, xem plan.md)*:
   - **`calls_dialed`** — `COUNT(*) FILTER (WHERE direction='out' AND channel_type='call')` — mẫu số reach rate của riêng kênh gọi (activities_outbound hiện gộp mọi channel).
   - **Sửa định nghĩa `contacts_reached`** — thêm `'callback', 'refused', 'purchased'` vào filter (dòng 26-28 mart hiện tại): người thật nghe máy rồi hẹn gọi lại/từ chối/chốt mua đều là reach (`purchased` là enum mới, quyết định 2026-07-10 — xem plans/reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md; filter viết sẵn để forward-compatible dù enum chưa ship). Ghi chú thay đổi ngữ nghĩa vào schema.yml (câu hỏi mở #4 plan.md).
   - **`conversations_count`** — cuộc nói chuyện thật: `contact_outcome='answered' AND (contact_duration_s >= 60 OR có note outcome đính qua source_activity_id)`. Nếu 2 tuần đầu `contact_duration_s` đa số NULL → dùng riêng proxy note (câu hỏi mở #6).
   - **`wrong_number_count`** — `contact_outcome='wrong_number'` — chỉ số làm sạch danh sách (SĐT chết), mục tiêu sprint là enrichment tệp.

## Files to modify
- `transformation/models/marts/crm/mart_staff_performance_weekly.sql` — thêm CTE `outcome_notes`, `new_tags`, `channel_mix`, join vào SELECT cuối theo `(crm_user_id, week_start_date)` giống pattern các CTE hiện có (`activities`, `tasks_assigned`...).
- `transformation/models/marts/schema.yml` (hoặc file schema riêng của mart này nếu có) — khai báo cột mới + description.

## Implementation steps
1. Đọc `stg_crm__party_tag.sql` và `stg_crm__note.sql` để xác nhận tên cột chính xác (`tagged_by`, `tagged_at`, `category`, `author_user_id`, `created_at`, `note_type`).
2. Viết CTE `outcome_notes`: `SELECT author_user_id AS crm_user_id, DATE_TRUNC('week', created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE AS week_start_date, COUNT(*) AS outcome_notes_count FROM stg_crm__note WHERE note_type='outcome' AND deleted_at IS NULL GROUP BY 1,2`.
3. Viết CTE `first_tag_per_party`: `SELECT party_id, tag_id, tagged_by, category, MIN(tagged_at) AS first_tagged_at FROM stg_crm__party_tag GROUP BY 1,2,3,4` rồi CTE `new_tags` group theo `(tagged_by, DATE_TRUNC('week', first_tagged_at), category='health_concern')`.
4. Viết CTE `channel_mix` từ `stg_crm__activity_log` (đã có cột `channel` — xác nhận giá trị enum thực tế trước khi hard-code tên cột, có thể là `phone|zalo|sms|in_store|other` hoặc khác).
5. Thêm vào `spine` CTE hiện có (dòng 77-84) các nguồn mới nếu staff có hoạt động nhưng không có activities/tasks (không bắt buộc nếu new_tags/outcome_notes luôn đi kèm activities thật).
6. LEFT JOIN các CTE mới vào SELECT cuối, COALESCE 0 như các cột hiện có.

## Tests / validation
- `dbt build --select mart_staff_performance_weekly` chạy sạch.
- Kiểm tra 1 staff biết trước có gắn tag sức khỏe tuần này → số liệu khớp tay (query trực tiếp `crm_party_tag` so sánh).
- Không có cột cũ nào đổi giá trị (snapshot trước/sau, diff = 0 dòng khác ngoài cột mới).

## Rollout
- Không cần Dagster export mới, không cần bootstrap serving view mới nếu mart này đã có trong Metabase — chỉ cần `dbt run --select mart_staff_performance_weekly` rồi Metabase tự thấy cột mới lần sync tiếp theo (theo [[feedback_new_mart_crm_serving_integration]] nếu mart CHƯA có trong serving view thì cần bootstrap; kiểm tra trước).

## Rủi ro
- Nếu `channel` enum có giá trị chưa liệt kê hết (VD `null`/`unknown`) → cần 1 cột `activities_channel_unknown` fallback, không được âm thầm drop.
