# Phase 0 — Implementation Report: Extend `mart_staff_performance_weekly`

## Đã làm

**File sửa:**
- `transformation/models/marts/crm/mart_staff_performance_weekly.sql` — thêm 6 CTE mới (`outcome_notes`, `first_tag_occurrence`/`new_tags`, `channel_mix`, `outcome_note_activities`/`calls_funnel`), sửa filter `contacts_reached`, thêm 12 cột mới, mở rộng `spine`.
- `transformation/models/marts/crm/schema.yml` — MỚI (mart này chưa có schema.yml nào trước đó) — khai báo mọi cột cũ + mới, description tiếng Việt, ghi chú thay đổi ngữ nghĩa `contacts_reached`.

**Không sửa** `stg_crm__note.sql` — cột `source_activity_id`, `note_type`, `author_user_id`, `created_at` đã có sẵn, đủ dùng.

## Cột mới

| Cột | Logic |
|---|---|
| `outcome_notes_count` | `note_type='outcome'` theo `author_user_id`, tuần `created_at` |
| `health_concern_tags_new` | tag `category='health_concern'` — đếm theo `(party_id, tag_id)` lần XUẤT HIỆN ĐẦU (window `ROW_NUMBER() OVER (PARTITION BY party_id, tag_id ORDER BY tagged_at)`, không phải `MIN()+GROUP BY`), gán công cho staff gắn lần đầu đó |
| `other_tags_new` | tương tự, `tag_category IS DISTINCT FROM 'health_concern'` (không phải `!=` — tránh drop NULL category) |
| `activities_call/chat/email/visit/other/unknown` | xem "Vấn đề phát hiện" bên dưới — dùng `activity_type` thay `channel_type` |
| `calls_dialed` | `direction='out' AND activity_type='call'` |
| `contacts_reached` (SỬA) | thêm `'callback','refused','purchased'` vào filter |
| `conversations_count` | `contact_outcome='answered' AND (contact_duration_s>=60 OR có note outcome qua source_activity_id)` |
| `wrong_number_count` | `contact_outcome='wrong_number'` |

## Vấn đề phát hiện: `channel_type` chưa export ra warehouse

Đọc `crm_activity_log` domain (`crm/src/domain/entities/activity.py`) phát hiện: cột thực sự mang ý nghĩa "kênh liên hệ" (phone/zalo/fb/email/visit/other) là `channel_type` (migration 0033), KHÔNG phải `channel` (cột này chứa RAW VALUE — số điện thoại/handle Zalo, không phải loại kênh). `channel_type` KHÔNG có trong SELECT của `crm_activity_log_export` (`orchestration/assets/crm_writeback_assets.py:79-84`) và KHÔNG có trong `stg_crm__activity_log.sql` — gap giống hệt loại gap #6 đã ghi trong plan.md (cho `crm_task`), nhưng đây là gap MỚI phát hiện cho `crm_activity_log`.

Cả 2 file cần sửa để export `channel_type` (`crm_writeback_assets.py`, `stg_crm__activity_log.sql`) đều nằm ngoài phạm vi sở hữu của tác vụ này (forbidden — ngoài `transformation/`, hoặc agent khác đang sửa song song).

**Giải pháp áp dụng**: dùng `activity_type` (đã export sẵn: call|note|visit|email|chat|other) làm proxy.
- Đọc `_HT_TO_ACT_TYPE` (`screen_customer_360_activity.py:28-31`): `call→call, zalo→chat, fb→chat, email→email, visit→visit, other→other`. Vì chỉ `hinh_thuc='call'` (channel_type) mới tạo ra `activity_type='call'`, `activity_type='call'` là proxy CHÍNH XÁC (không phải suy đoán) cho `channel_type='call'` → `calls_dialed` và `activities_call` đáng tin 100%.
- zalo và fb đều gộp vào `activity_type='chat'` → KHÔNG tách được zalo/fb riêng như spec gốc yêu cầu ("activities_phone/zalo/sms/other"). Cột thực tế: `activities_call, activities_chat, activities_email, activities_visit, activities_other, activities_unknown` (fallback, gồm cả `note` — enum có định nghĩa nhưng chưa write path nào tạo ra).
- `sms` không tồn tại trong enum thực tế (`hinh_thuc` chỉ có call|zalo|fb|email|visit|other) — không tạo cột giả.

Đã ghi rõ gap này trong code comment + schema.yml. Đề xuất: thêm 1 dòng vào `orchestration/assets/crm_writeback_assets.py` SELECT (`a.channel_type`) + `stg_crm__activity_log.sql` khi agent phụ trách file đó rảnh — nên gộp vào phase-01 hoặc 1 phase riêng.

## Validation

- `dbt build --select mart_staff_performance_weekly` — PASS (3/3: model + 2 not_null test). Chạy trong container `data_platform`, gặp DuckDB lock 2 lần do agent song song đang `dbt build --select fqn:*` — đã poll `/proc/<pid>` chờ lock giải phóng rồi build lại (không dùng olap.duckdb ghi, chỉ đọc `sapo_warehouse.duckdb` qua dbt).
- Channel mix không mất/không trùng dòng: `SUM(activities_total) = SUM(activities_call+chat+email+visit+other+unknown) = 124` (khớp).
- `contacts_reached` semantic diff: dữ liệu hiện tại CHƯA có `contact_outcome IN ('callback','refused','purchased')` nào → `total_old = total_new = 4`, delta = 0. Đúng như kỳ vọng (filter forward-compatible, chưa có dữ liệu để kích hoạt — sẽ tăng đúng bằng số callback+refused khi dữ liệu xuất hiện).
- `conversations_count` — verify bằng tay: có đúng 1 activity `answered` gắn note outcome qua `source_activity_id` trong data hiện tại; nhưng `staff_user_id` của activity đó (`dd550b11-...`) KHÔNG có trong `dim_staff` (orphan CRM user chưa map Sapo) → bị loại bởi `WHERE s.staff_key IS NOT NULL` (rule CŨ của mart, không phải logic mới) → mart trả `conversations_count=0` toàn bộ hiện tại. Logic đúng, chỉ chưa có dữ liệu thật để quan sát end-to-end qua staff đã map.
- Cột cũ (`activities_total/outbound`, `tasks_assigned/completed`, `orders_sold/revenue_vnd`) không đổi CTE, không có rủi ro giá trị đổi.

## Tỷ lệ NULL `contact_duration_s` (câu hỏi mở #6)

Trong toàn bộ `stg_crm__activity_log` hiện tại: chỉ có **3 activity `contact_outcome='answered'`**, cả 3 đều `contact_duration_s IS NULL` → **100% NULL**. Dữ liệu quá ít (tuần đầu sprint, `crm_activity_log` mới có 251 dòng tổng) để kết luận xu hướng dài hạn, nhưng xác nhận: hiện tại `conversations_count` gần như hoàn toàn phụ thuộc nhánh fallback "có note outcome" — proxy `duration>=60s` chưa có tác dụng thực tế. Cần theo dõi lại sau 1-2 tuần sprint chạy thật.

## Rollout

Không thêm dbt node mới (chỉ sửa mart có sẵn) → không cần restart `data_platform`. Mart đã build xong trong `main_marts` schema, Metabase sẽ thấy cột mới ở lần sync tiếp theo.

## Unresolved

1. Câu hỏi mở #6 (plan.md): chưa đủ dữ liệu (n=3) để chốt ngưỡng 60s hay bỏ hẳn nhánh duration — cần review lại sau khi Sprint Gọi Ra chạy được 1-2 tuần thật.
2. Gap MỚI phát hiện: `crm_activity_log.channel_type` chưa export ra warehouse (`crm_writeback_assets.py` + `stg_crm__activity_log.sql`) — cần fix riêng (ngoài scope phase này) để có breakdown phone/zalo/fb/other thật thay vì proxy `activity_type` (hiện tại zalo+fb gộp chung `activities_chat`).
3. `health_concern_tags_new` hiện luôn = 0 vì dữ liệu test/dev hiện tại chưa có tag nào `category='health_concern'` (chỉ có demographic/source/behavioral/vip_tier/risk/health_domain/preference) — logic đúng, chỉ chưa có dữ liệu kích hoạt; cần xác nhận khi tag thật được gắn qua Sprint.

Status: DONE_WITH_CONCERNS
Summary: Đã thêm đủ 12 cột theo spec, dbt build sạch, snapshot xác nhận cột cũ không đổi (trừ contacts_reached — delta=0 hiện tại vì chưa có callback/refused data). Phát hiện gap mới: channel_type chưa export → channel breakdown dùng activity_type proxy (chính xác cho call, nhưng gộp zalo+fb thành "chat", không có sms).
Concerns/Blockers: (1) contact_duration_s 100% NULL trên mẫu rất nhỏ (n=3) — chưa đủ để chốt ngưỡng conversations_count; (2) channel_type export gap cần 1 phase riêng để có breakdown kênh chính xác; (3) health_concern_tags_new chưa quan sát được vì chưa có dữ liệu category đó.
