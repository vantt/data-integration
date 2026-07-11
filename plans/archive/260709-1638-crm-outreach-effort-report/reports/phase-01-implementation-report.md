# Phase 01 — Schema attribution fix — Implementation Report

Status: DONE_WITH_CONCERNS (xem "Handoff wiring" + "Unresolved")

## Đã làm

### 1. `crm_task.claimed_action_types` (snapshot lúc claim)
- Migration `crm/migrations/0043_task_claimed_action_types.up.sql` / `.down.sql` (ALTER TABLE ADD COLUMN TEXT nullable; down = no-op theo convention `0032_task_kind.down.sql`, SQLite pre-3.35 không DROP COLUMN).
- `crm/src/domain/entities/task.py`: thêm field `claimed_action_types: Optional[str]`.
- `crm/src/adapters/outbound/sqlite/task_repository.py`: thêm cột vào `_INSERT` + toàn bộ 8 câu SELECT (`_GET_BY_ID`, `_GET_BY_SOURCE_REF`, `_GET_CUSTOMER_CLAIM`, `_LIST_*`) + row mapper (fallback None cho DB cũ). `_UPDATE` KHÔNG đổi — cột là snapshot bất biến, không ghi lại sau claim.
- `crm/src/application/task_service.py::claim_customer_actions` (dòng ~254-292): serialize `[a.action_type for a in actions]` bằng `json.dumps` + validate round-trip (`json.loads`) trước khi gán vào Task, log warning + fallback None nếu serialize lỗi. `actions` đã đến sẵn theo thứ tự `priority ASC` (từ `cache_repository.list_all_action_queue()` → `ORDER BY priority ASC`, giữ nguyên qua filter ở `screen_worklist.py`), nên JSON giữ đúng thứ tự priority_rank không cần sort lại.

### 2. `crm_party_tag.source_activity_id` (nối tag về activity)
- Migration `0044_party_tag_source_activity.up.sql` / `.down.sql` (ALTER TABLE ADD COLUMN TEXT REFERENCES crm_activity_log(activity_id), + index; down = no-op + drop index, theo đúng convention `0019_note_source_activity`).
- `crm/src/domain/entities/profile.py::PartyTag`: thêm field `source_activity_id: Optional[str] = None`.
- `crm/src/application/tag_service.py::attach_tag()`: thêm param `source_activity_id: Optional[str] = None`, backward-compatible.
- `crm/src/adapters/outbound/sqlite/tag_note_repository.py::SQLiteTagRepository.attach_tag()`: `_SQL_ATTACH` ghi cột mới; `ON CONFLICT` dùng `COALESCE(excluded.source_activity_id, crm_party_tag.source_activity_id)` — re-attach không activity context không xoá link đã có.
- `crm/src/composition.py::_ProfileTagCFComposite.attach_tag()` + `screen_modal_shared.py::ProfileSvc` Protocol: cập nhật signature để forward kwarg mới qua toàn bộ chuỗi delegate.
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_tags.py::post_tags_inline` (KHÔNG phải file cấm): thêm optional `Form` field `source_activity_id`, passthrough vào `attach_tag()`. Đây là API surface hợp lệ, không có caller nào gửi giá trị này hiện tại — xem "Handoff wiring".

### 3. Export gap (`orchestration/assets/crm_writeback_assets.py`)
- Grep `ref('stg_crm__task')` toàn `transformation/` trước khi sửa — 3 consumer (`int_crm_party_tag_flags.sql`, `mart_crm_activity_log.sql`, `mart_staff_performance_weekly.sql`), cả 3 đều SELECT cột tường minh, không SELECT *. An toàn để thêm cột.
- `crm_task_export`: thêm `outcome, task_kind, channel, value_at_stake_vnd, top_affinity_product, claimed_action_types`.
- `crm_party_tag_export`: thêm `source_activity_id`.
- `crm_activity_log_export`: thêm `custom_fields` (chưa có trước đây — cần cho zalo_connected) + **`channel_type`** (bổ sung theo yêu cầu coordinator giữa chừng — cột tồn tại từ migration 0033 nhưng chưa từng được export; phễu gọi trước đây phải dùng `activity_type` proxy gộp zalo/fb thành 'chat').

### 4. Staging
- `stg_crm__task.sql`: thêm 6 cột tương ứng (cast `value_at_stake_vnd::BIGINT`, còn lại `::VARCHAR`; `claimed_action_types` giữ raw JSON string, không parse — parse thuộc phase 2).
- `stg_crm__party_tag.sql`: thêm `source_activity_id::VARCHAR`.
- `stg_crm__activity_log.sql`: thêm `channel_type` (pass-through) + derive `zalo_connected` boolean qua `COALESCE(TRY_CAST(json_extract_string(custom_fields, '$.zalo_connected') AS BOOLEAN), false)`.
- KHÔNG đụng `stg_crm__note.sql` (đúng yêu cầu).

### 5. Suppression `do_not_contact`
- Xác định đúng service quyết định worklist: `crm/src/application/worklist_query_service.py::WorklistQueryService.list_all_action_queue()` — đây là điểm entry duy nhất mà `screen_worklist.py::_load_worklist_data` gọi để lấy `all_actions` trước khi rank/filter, phù hợp nhất để chặn sớm.
- Thêm `_SuppressionPort` protocol (`list_do_not_contact_party_ids() -> set[str]`) + param `suppression: Optional[...] = None` — filter loại action nào có `party_id` nằm trong tập suppressed. Lỗi query suppression không làm sập cả worklist (try/except, degrade về unfiltered — suppression chỉ là visibility nicety).
- `crm/src/adapters/outbound/sqlite/activity_repository.py::SQLiteActivityRepository.list_do_not_contact_party_ids()`: SQL 1 câu, self-join lấy activity MỚI NHẤT theo `party_id` (`MAX(occurred_at)`), lọc `outcome_reason = 'do_not_contact'` — so sánh string literal, KHÔNG import gì từ `domain.entities.activity`.
- Wiring: `crm/src/composition.py` — `WorklistQueryService(..., suppression=sqlite_repos["activity"])` (duck-typed, `SQLiteActivityRepository` đã có method mới nên tự động khớp protocol).
- Data KHÔNG bị xoá — chỉ filter runtime, đúng UX yêu cầu.

## Handoff wiring (thuộc 4 file cấm — KHÔNG sửa)

Phần "nối tag-attach vào đúng activity vừa log" **không thể hoàn thành trọn vẹn** vì mọi call site thực tế nằm trong file cấm hoặc phụ thuộc state chỉ có trong file cấm:

1. **`crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`** (`handle_log_activity`, dòng ~228-277): handler này hiện KHÔNG gọi `attach_tag()` ở đâu cả (chỉ note có `source_activity_id=getattr(activity, "activity_id", None)`, dòng 274). Tag-attach (health_domain/health_concern) xảy ra qua request HTMX riêng biệt tới `POST /customers/{party_id}/tags/inline` (`screen_modal_tags.py`), KHÔNG nằm trong cùng transaction với log-activity. Muốn nối đúng, cần 1 trong 2 hướng:
   - (a) Client-side (JS trong `modal_log_activity.html` hoặc `c360_call_cockpit_panel.html`) giữ lại `activity_id` vừa được server trả về sau khi submit Log Activity, rồi gửi kèm nó như hidden field `source_activity_id` trong mọi request `/tags/inline` tiếp theo trong cùng phiên gọi.
   - (b) Hoặc gộp tag-attach vào cùng POST `log-activity` (đổi luồng UX — rep chọn tag ngay trong modal Log Activity thay vì tag rời qua S14 cockpit inline).
2. **`crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`**: các form `tag_multiselect` (S14 collect-row, render bởi `_s14_collect_row.html`) hiện KHÔNG có hidden input `source_activity_id` — cần thêm nếu chọn hướng (a) ở trên.
3. **`crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`**: nếu chọn hướng (a), cần JS lưu `activity_id` trả về từ response log-activity (hiện response là fragment HTML, không có activity_id lộ ra client — cần thêm data attribute hoặc đổi response).
4. **`crm/src/domain/entities/activity.py`**: KHÔNG động tới — agent khác sở hữu `VALID_OUTCOME_REASONS`/`do_not_contact` enum. Đã xác nhận qua `git diff --stat` là file này đã có thay đổi song song (5 dòng) trong lúc tôi làm việc; suppression filter của tôi chỉ so sánh string, không phụ thuộc thứ tự merge.

**Việc ĐÃ làm sẵn (không forbidden) để khi (a)/(b) triển khai chỉ cần đổi 3 file trên**: `screen_modal_tags.py::post_tags_inline` đã nhận optional Form field `source_activity_id`, `attach_tag()` cả chain (`TagService` → `_ProfileTagCFComposite` → `ProfileSvc` protocol) đã sẵn sàng nhận và ghi giá trị này — chỉ còn thiếu người gửi.

## Bổ sung giữa chừng (theo yêu cầu coordinator)

`crm_activity_log.channel_type` (migration 0033, enum `phone|zalo|fb|email|visit|other` — thực ra giá trị lưu là `call|zalo|fb|email|visit|other` theo dữ liệu thật) chưa từng được export/staged. Đã thêm vào `crm_activity_log_export` (cùng chỗ `custom_fields`) và `stg_crm__activity_log.sql`. Verify bằng query trực tiếp trên warehouse sau khi materialize lại: `channel_type` phân bố `call:6, fb:1, zalo:1, NULL:48` (NULL = activity trước migration 0033).

## Validation

- **pytest trong container** (`docker compose exec -T crm pytest ...`):
  - 3 file test mới: `test_task_claim_action_types_snapshot.py`, `test_tag_service_source_activity_id.py`, `test_worklist_suppression_do_not_contact.py` — 13/13 PASS (unit + integration round-trip qua `seeded_crm_db` thật, có migration áp dụng).
  - Full suite `crm/src/tests` (trừ `test_approach_script_handler.py` — lỗi collection *pre-existing*, không liên quan thay đổi của tôi — import `wire_approach_script_router` không tồn tại, thuộc công việc khác đang dở): **956 passed**, 0 failed liên quan tới thay đổi của tôi.
  - 2 failure loại trừ khỏi lần chạy cuối vì xác nhận KHÔNG do tôi gây ra: `test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit` và `test_outcome_reason_enum.py::test_valid_reasons_count` (expect 11 reasons, thực tế 12 — do agent khác đã thêm `do_not_contact` vào `VALID_OUTCOME_REASONS` trong `activity.py`, xác nhận qua `git diff --stat` chỉ có `activity.py` thay đổi, test cũ của họ chưa cập nhật theo — không phải việc của tôi, file cấm).
- **`dbt build --select stg_crm__task stg_crm__party_tag stg_crm__activity_log`**: sạch (3 view OK, 2 test PASS) sau khi:
  1. Phát hiện lỗi Binder Error ban đầu vì parquet cũ trong data lake chưa có cột mới (export chưa từng chạy với query mới) — reset cursor + xoá batch cũ (`crm_activity_log`, `crm_task`, chỉ 104K/100K, an toàn tái tạo từ `crm.db`) rồi `dagster asset materialize --select crm_activity_log_export,crm_task_export,crm_party_tag_export` để backfill full 1 lần với schema mới.
  2. Gặp `IOException: Could not set lock` do agent khác đang chạy dbt song song trên cùng `sapo_warehouse.duckdb` — retry có backoff (15s × 6 lần) tới khi lock nhả, KHÔNG phải sleep-loop che giấu lỗi thật.
  - Mở rộng `dbt build --select stg_crm__task+ stg_crm__party_tag+ stg_crm__activity_log+` (bao cả downstream: `mart_crm_activity_log`, `int_crm_party_tag_flags`, `mart_staff_performance_weekly`, `mart_customer_action_queue`) — 16/16 PASS, không có mart nào vỡ vì cột mới.
- **Migration mechanism xác nhận**: `composition.py` gọi `db.apply_migrations()` lúc startup (dòng 218, 354) → `docker compose restart crm` áp dụng migration mới, KHÔNG cần rebuild. Đã restart container thật, log xác nhận `[entrypoint] migrations OK`, verify trực tiếp `PRAGMA table_info` trên `crm.db` sống: `crm_task.claimed_action_types` và `crm_party_tag.source_activity_id` tồn tại, `schema_migrations` có `0043` + `0044`. `/healthz` và `/worklist` trả 200 sau restart.
- **Không giả vờ pass**: phần "Handoff wiring" (mục 2 phần cuối scope #2) rõ ràng CHƯA hoàn thành — chỉ có hạ tầng ghi (API + service + DB), chưa có ai gọi với giá trị thật vì cần sửa file cấm.

## Unresolved

1. `source_activity_id` chưa có dữ liệu thật nào trong `crm_party_tag` — hạ tầng ghi đã sẵn sàng nhưng cần agent sở hữu 3 file cấm (activity/modal_log_activity/c360_call_cockpit_panel) hoàn thành wiring theo 1 trong 2 hướng (a)/(b) ở mục Handoff.
2. `claimed_action_types` cũng chưa có dữ liệu thật trong `crm.db` hiện tại — đúng kỳ vọng "fix-forward only", sẽ chỉ có giá trị từ claim mới sau khi container đã restart (đã restart lúc 14:24 ICT hôm nay); cần theo dõi lần claim thật đầu tiên để xác nhận.
3. `test_outcome_reason_enum.py::test_valid_reasons_count` và `test_approach_script_file_repository.py` đang đỏ trong repo do công việc song song khác (không thuộc phase-01) — cần agent tương ứng tự vá, không phải phần việc tôi được giao xử lý.

Status: DONE_WITH_CONCERNS
Summary: Đủ cả 5 mục scope (migration+entity+service+repo, export, staging, suppression) đã implement + test + verify trên container/DB thật; riêng phần nối tag↔activity trong luồng Log Activity chỉ làm được hạ tầng (API optional param) vì điểm nối thật sự nằm trong 3/4 file cấm — đã ghi rõ Handoff.
Concerns: (1) Tag↔activity linking chưa end-to-end do phụ thuộc file cấm; (2) 2 test đỏ pre-existing không liên quan (do_not_contact enum count, approach_script file repo) — không sửa vì ngoài scope/thuộc code người khác đang sửa song song.
