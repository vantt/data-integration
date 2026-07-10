# Phase 02 — Intermediate model: effort events tách theo action_type — Implementation Report

Status: DONE

## Đã làm

### Files tạo mới
- `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.sql`
- `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.yml`

Grain `(task_id, action_type)`, chỉ lọc `task.source = 'action_queue_claim'`, `staff_user_id` giữ nguyên UUID CRM (không join `dim_staff`), không lọc `is_us_gift_recipient` — đúng spec.

## Join/explode logic thực tế implement

Về cơ bản theo đúng sketch trong phase file, nhưng có 3 điểm khác biệt CÓ CHỦ ĐÍCH (không phải silent deviation) so với pseudocode gốc:

### 1. `customer_bridge` — dùng thẳng `customer_id` đã resolve sẵn, không tự join lại `crm_party_identity`
Phase file sketch đề xuất join `party_id → crm_party_identity(identity_type='sapo_customer') → dim_customers`. Đọc `orchestration/assets/crm_writeback_assets.py::_dedup_identity_join` xác nhận: join này ĐÃ xảy ra ở tầng export (mọi bảng `crm_export.*` — kể cả `crm_task`, `crm_party_tag`, `crm_activity_log` — đều có sẵn cột `customer_id` là `identity_value` đã resolve). `stg_crm__task.sql` đã select cột này thẳng. Model dùng `LEFT JOIN dim_customers dc ON TRY_CAST(dc.customer_id AS BIGINT) = TRY_CAST(te.customer_id AS BIGINT)` — giống hệt pattern đã có ở `mart_crm_activity_log.sql` / `int_crm_party_tag_flags.sql`. Không phải "khác join key" — cùng 1 khoá logic (party_id ↔ sapo_customer identity), chỉ dùng cột đã vật chất hoá sẵn thay vì tự derive lại (DRY).

### 2. `channel` — dùng `activity.channel_type`, không dùng `activity.channel` (raw) như pseudocode gốc
Phase-00 report đã xác nhận: `crm_activity_log.channel` là RAW VALUE (số điện thoại/handle Zalo), KHÔNG phải loại kênh; cột đúng nghĩa là `channel_type` (call|zalo|fb|email|visit|other, migration 0033). Lúc phase-02 file được viết, `channel_type` CHƯA được export/staged — nhưng phase-01 addendum (cùng ngày, coordinator yêu cầu giữa chừng) đã thêm `channel_type` vào `crm_activity_log_export` + `stg_crm__activity_log.sql`. Nên model này dùng `COALESCE(activity.channel_type, task.channel)` thay vì `activity.channel` — đúng ý nghĩa "loại kênh liên hệ", tránh lặp lại gap đã biết là sai. Đây là trường hợp literal pseudocode "rõ ràng sai" theo phát hiện đã verify (phase-00 report), không phải quyết định tuỳ tiện.

### 3. `is_reached` — GIỮ NGUYÊN literal spec (answered/replied/met), KHÔNG mở rộng theo Phase 0
Phase 0 (cùng ngày) đã đổi `contacts_reached` trong `mart_staff_performance_weekly` thêm `callback/refused/purchased`. Phase-02 file (literal text) chỉ ghi `answered/replied/met`. Task giao việc yêu cầu bám sát đúng cột/logic trong phase file trừ khi "rõ ràng sai" — trường hợp này KHÔNG rõ ràng sai (chỉ là 1 định nghĩa khác/hẹp hơn, không phải bug), nên giữ nguyên literal + ghi rõ trong `.yml`/code comment để Phase 3 quyết định có cần đồng bộ 2 định nghĩa hay không.

## Xử lý multi-activity-per-task (phát hiện thực tế, không có trong pseudocode gốc)

Data thật cho thấy 1 task_id có THỂ có >1 activity gắn (`task_id`, `staff_user_id` giống nhau, 5 activity log rows — xác nhận trực tiếp qua query). Grain của model là `(task_id, action_type)`, không phải theo activity — nên cần 1 quy tắc pick/aggregate rõ ràng (spec gốc không nói tới trường hợp này):
- `contact_outcome`, `staff_user_id`, `channel` (single-value columns): lấy từ activity MỚI NHẤT theo `occurred_at DESC` (ROW_NUMBER, rn=1) — "kết quả cuối cùng đã biết của nỗ lực gọi đó".
- `outcome_note_count`, `health_concern_tags_new`, `other_tags_new` (info-collected columns): SUM qua TẤT CẢ activity gắn với task đó (không chỉ activity mới nhất) — mọi note/tag phát sinh trong suốt task đều tính là nỗ lực của task đó.
- Cả 2 nhóm cột info-collected này đều broadcast ra MỌI row action_type của task (theo đề xuất trong câu hỏi mở của phase file — áp dụng cho outcome_note_count luôn, không chỉ health_concern_tags_new, vì cùng logic "info thu được thuộc về cả cuộc gọi, không chia theo action_type").

## DuckDB JSON explode — verify cú pháp

Container `data_platform`: `duckdb` python lib 1.5.4, `dbt-duckdb` plugin 1.10.1. Dùng pattern ĐÃ CÓ TIỀN LỆ trong repo (`int_order_tags.sql`, `stg_sapo_v2_customer_tags.sql`): `LATERAL UNNEST(json_extract(col, '$[*]'))`. Vì `UNNEST` của array rỗng/NULL trả về 0 row (không phải 1 row NULL), dùng `UNION ALL` giữa nhánh "có claimed_action_types" (LATERAL UNNEST) và nhánh "NULL/rỗng" (`SELECT ... NULL AS action_type`) thay vì cố ép LEFT JOIN LATERAL — đảm bảo đúng yêu cầu "task không có claimed_action_types → 1 row action_type=NULL".

Verify bằng synthetic query độc lập (không đụng warehouse thật, DuckDB in-memory):
```
task-A ['REORDER_PREEMPT','PROGRESS_CHECK'] → 2 rows: PROGRESS_CHECK, REORDER_PREEMPT
task-B NULL                                  → 1 row: NULL
task-C '[]'                                  → 1 row: NULL
task-D ['WIN_BACK']                          → 1 row: WIN_BACK
```
Khớp chính xác kỳ vọng — quote-stripping, NULL fallback, multi-element explode đều đúng.

## Verify trên data thật

Không có claim thật nào có `claimed_action_types` non-NULL trong data hiện tại (37/37 task `action_queue_claim` đều `claimed_action_types IS NULL` — đúng kỳ vọng "fix-forward only", chưa có claim mới nào từ sau khi cột được ship trong phase 01). Không dùng backfill giả để né việc này — báo cáo đúng thực trạng, dùng synthetic query ở trên để verify logic explode.

Đã verify các phần verify được với data thật:
- `dbt run --select int_crm_outreach_effort_events` → PASS, 37 rows (= số task `action_queue_claim` thật).
- `dbt test --select int_crm_outreach_effort_events` → PASS 2/2 (`not_null(task_id)`, `unique_combination_of_columns(task_id, action_type)`).
- `customer_key` resolve đủ 100% (0 NULL/37) — bridge qua `customer_id` hoạt động đúng.
- 1 task_id thật (`9a8396e3-...`) có 5 activity gắn cùng — verify multi-activity fan-out KHÔNG làm vỡ grain: model trả đúng 1 row cho task_id đó, `staff_user_id` = đúng assignee thật (`87f7cfb9-...`), `contact_outcome`/`channel` = NULL (đúng vì data thật của cả 5 activity đó `contact_outcome` và `channel_type` đều NULL).
- `outcome_note_count`/`health_concern_tags_new`/`other_tags_new` hiện = 0 toàn bộ 37 rows — đúng kỳ vọng vì `stg_crm__note` chưa có note nào note_type='outcome' gắn `source_activity_id` khớp activity của các task action_queue_claim này trong data hiện tại, và `source_activity_id` trong `crm_party_tag` chưa có data thật (đã ghi trong phase-01 report, "Handoff wiring" chưa xong).

## Vấn đề vận hành gặp phải: DuckDB lock

Gặp `IOException: Could not set lock` 2 lần do 1 tiến trình khác (Dagster sensor, `dbt build --select fqn:*`) đang chạy song song trên cùng `sapo_warehouse.duckdb`. Đúng theo development-rules (không chạy ghi đồng thời) — poll `/proc/<pid>` tới khi tiến trình đó kết thúc rồi retry, không dùng workaround nào khác (không tắt lock, không ép force).

## Unresolved / cần theo dõi

1. **Chưa có claim thật nào có `claimed_action_types` 2+ phần tử** để verify explode trên data thật — chỉ verify được bằng synthetic query. Cần theo dõi claim thật đầu tiên sau cutover (giống unresolved #2 của phase-01 report) rồi re-verify model output khớp đúng N action_type.
2. **`is_reached` (answered/replied/met) khác `mart_staff_performance_weekly.contacts_reached`** (đã mở rộng thêm callback/refused/purchased ở Phase 0) — cần Phase 3 quyết định có đồng bộ 2 định nghĩa hay giữ khác biệt có chủ đích (effort-events là per-activity-cuối-cùng, staff-weekly là per-activity-tất-cả).
3. **Multi-activity-per-task**: pseudocode gốc phase file không lường trước trường hợp 1 task có nhiều activity — đã tự quyết định rule pick-latest/sum-all (ghi rõ ở trên + trong code comment), chưa có xác nhận từ coordinator. Nếu ý định khác (VD: tách riêng theo từng activity thay vì gộp về task), cần sửa lại trước khi Phase 3 build trên model này.
4. `outcome_note_count`/`*_tags_new` = 0 toàn bộ hiện tại — logic đúng nhưng chưa có data thật kích hoạt (giống concern đã ghi ở phase-00/01 report cho các cột tương tự).

Status: DONE
Summary: Model + schema.yml tạo xong đúng grain (task_id, action_type); dbt run + test PASS trên data thật (37 rows, 0 lỗi); JSON-explode logic verify bằng synthetic query (data thật chưa có claim nào có 2+ action_type). 3 điểm khác biệt có chủ đích so với pseudocode gốc (customer bridge dùng cột đã resolve sẵn, channel dùng channel_type thay channel raw, multi-activity-per-task pick/sum rule) đều ghi rõ lý do trong model + report.
Concerns/Blockers: (1) chưa verify explode trên claim thật có 2+ action_type — chờ cutover; (2) is_reached vs contacts_reached định nghĩa lệch nhau giữa 2 model, cần Phase 3 chốt; (3) multi-activity-per-task rule là quyết định tôi tự đưa ra do spec gốc không lường trước — cần coordinator xác nhận trước khi Phase 3 dựa vào.
