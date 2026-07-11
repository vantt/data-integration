# Phase 02 (P1) — Draft + PATCH-theo-field + finalize API — Implementation report

Nguồn: `plans/260710-1338-activity-log-disposition-api/phase-02-draft-patch-finalize-api.md` + mục III/V của `plans/reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md`.

## Tóm tắt

Đủ scope P1: migration 0045 (status/started_at/finalize_at/contact_duration_s), 3 route mới (`POST /api/parties/{id}/call-sessions`, `PATCH /api/activities/{id}`, `POST /api/activities/{id}/finalize`), extract side-effect executor dùng chung giữa route mới và `POST /customers/{id}/log-activity` cũ, M08 mode `edit_activity`, handoff wiring `source_activity_id` KHÔNG cần làm thêm (xem mục riêng bên dưới — lý do). Full suite 1031 passed / 0 failed (1008 baseline + 23 test mới). Container restart + `/healthz` 200 + migration verify trên DB sống.

## Kiến trúc

### 1. Migration `0045_activity_draft_lifecycle`
`crm_activity_log` +4 cột nullable: `status` (`draft`|`final`|NULL=final — an toàn cho mọi row cũ), `started_at`, `finalize_at`, `contact_duration_s`. Partial index `(staff_user_id, party_id) WHERE status='draft'` cho lookup draft mở. Down = no-op cột (convention 0032/0043, SQLite pre-3.35 không DROP COLUMN) + drop index.

### 2. `domain/entities/activity.py`
Thêm `ACTIVITY_STATUS_DRAFT`/`ACTIVITY_STATUS_FINAL` + 4 field mới trên `Activity` (tất cả `Optional`, cuối dataclass — không phá vị trí positional cũ).

### 3. Repository (`domain/ports/activity_repository.py` + sqlite adapter)
Thêm `get_by_id`, `find_open_draft(staff_user_id, party_id)`, `update` (full-row overwrite theo `activity_id`, không đụng `party_id`/`staff_user_id`/`created_at`). `_INSERT`/row-mapper cập nhật 4 cột mới.

### 4. `application/activity_service.py`
- `create_draft(party_id, staff_user_id, channel_identity_id?, channel_value?, task_id?)` — idempotent: `find_open_draft` trước, có thì trả lại, không tạo mới.
- `patch_activity(activity_id, fields, actor_id, is_edit_mode=False)` — validate enum theo `channel_type` hiện có trên row (dùng `CONTACT_OUTCOMES_BY_CHANNEL_TYPE`), validate `refused`→cần reason + `irritation`→cần body (tái dùng đúng rule của `log_activity`). `custom_fields_patch` merge (không ghi đè) vào `custom_fields` sẵn có. KHÔNG side-effect. `is_edit_mode=True` + row đang `status=final` + `contact_outcome` thực sự đổi → stamp `custom_fields.edited_at/edited_by/previous_outcome`. (Xem mục "Deviation" về cutoff 02:30 ICT.)
- `finalize_activity(activity_id, contact_duration_s_override?)` → `(Activity, already_finalized: bool)`. `ActivityNotFoundError`/`ActivityFinalizeConflictError` (409 khi thiếu `contact_outcome`) là exception riêng, route map sang HTTP status. Idempotent thật: gọi lần 2 trên row đã `final` → trả nguyên trạng, `already_finalized=True`, KHÔNG tính lại duration/last_contact. `contact_duration_s` = `finalize_at − started_at` giây, override thắng nếu truyền vào (M08 nhập tay). `last_contact` upsert dời từ `log_activity`-insert-time sang finalize-time (lý do: draft có thể PATCH outcome nhiều lần trước khi chốt, upsert lúc PATCH sẽ ghi last_contact sai nếu outcome đổi sau đó).

### 5. `application/activity_side_effects.py` (module mới)
`execute_side_effects(activity, actor_id, *, party_id, profile, notes, task_svc, party_insights, action_state, complete_task_ids, resolve_action_ids, resolve_task_ids, create_callback_task, callback_at, schedule_followup_at, save_as_note, promote_insight, auto_claim)` — 7 side-effect (insight/auto-claim/note/callback-task/followup/complete-task/bulk-resolve), mỗi bước try/except riêng (1 bước lỗi không rollback activity đã ghi). Đây là **executor DUY NHẤT** — cả `handle_log_activity` (cũ) lẫn `handle_finalize_activity` (mới) gọi qua closure `_run_side_effects` trong `screen_customer_360_activity.py` (đóng gói `profile/notes/task_svc/party_insights/action_state` — cùng instance dùng ở mọi nơi khác trong module). Không đặt trong `ActivityService` để KHÔNG phải đổi thứ tự khởi tạo service trong `composition.py` (activity service hiện build trước task/note service) — giữ nguyên rủi ro thấp, không đụng file `_build_services`.

**Bug tiền tồn phát hiện + sửa khi extract**: `callback_at`/`create_callback_task` (checkbox "Tạo task nhắc tự động", mặc định TICK trong M08) được set vào `act_data` trước `log_activity()` nhưng `ActivityService.log_activity()` chưa từng đọc lại 2 key này — task nhắc gọi lại KHÔNG BAO GIỜ được tạo (dead code, verify bằng grep toàn `crm/src` không có callsite nào đọc lại). Report UX nguồn liệt kê "callback task" là 1 trong 7 side-effect bắt buộc của finalize — nên đã fix thật trong `execute_side_effects` (step 4) thay vì tái tạo lại chỗ hỏng. Verify không test nào phụ thuộc hành vi cũ (grep `create_callback_task="1"` trong `crm/src/tests` → không có).

### 6. Routes (`screen_customer_360_activity.py`)
3 route mới đặt **sau** `r14-ack` (route POST cuối cùng cũ) — giữ nguyên index `router_mock.post.call_args_list[N]` mà `test_claim_context_snooze_r14.py` đang dựa vào (`[2]`=r14-ack).
- `POST /api/parties/{party_id}/call-sessions` — Form, không token (session/LAN-trust, cùng pattern `script-nav`), 401 nếu `current_user` rỗng (draft cần staff sở hữu). Resolve `channel_identity_id` → `channel_value` qua `identities.list_identities` sẵn có trong closure.
- `PATCH /api/activities/{activity_id}` — Form với `Optional[str] = Form(default=None)` (sentinel None = field không gửi = không đụng, đúng "subset field bất kỳ"). `custom_fields_patch` gom `callback_at`/`channel_identity_id`/`zalo_connected`. 404/422 map từ exception. `edit_mode=1` → redirect timeline (khớp hành vi mọi submit M08 khác); autosave thật (P2) → 204.
- `POST /api/activities/{activity_id}/finalize` — 409/404 map từ exception; side effect chỉ chạy khi `already_final=False`; trả fragment nhỏ `✓ Đã chốt: <label>` (không redirect, đúng quyết định #3).

**Legacy `POST /customers/{id}/log-activity`**: thêm 1 Form field mới `draft_activity_id` (optional, default rỗng — mọi caller cũ không gửi → hệt hành vi trước). Có giá trị → PATCH fields lên draft đó rồi `finalize_activity` (thay vì insert row mới) → `contact_duration_s` đo thật từ `started_at` (bonus miễn phí đúng như spec). Không có → giữ nguyên logic insert cũ 100% (đã verify bằng 44+11 test cũ không sửa assertion nào, chỉ thêm 1 kwarg). Cả 2 nhánh hội tụ về CÙNG `_run_side_effects()` 1 lần — nếu `already_final=True` (double-submit draft, VD double-click) thì SKIP side-effect (cải thiện so với hành vi cũ — trước đây double-submit tạo 2 activity + side-effect nhân đôi hoàn toàn, giờ path draft-adopt tự chống được).

### 7. M08 `edit_activity` mode
`_m08_ctx` nhận `activity_id`, load qua `activity_log.get_activity()` (method mới, thin wrapper `repo.get_by_id`) — **không bao giờ** "log gần nhất" (đúng rule report mục V). `modal_log_activity.html`: `save_url` = `/api/activities/{id}`, form dùng `hx-patch` (không phải `hx-post`), ẩn các block chỉ có tác dụng khi có side-effect (save-as-note, insight-promo, followup, checkbox "tạo task nhắc tự động") vì PATCH không chạy side-effect — tránh UI hứa hẹn 1 việc không xảy ra. JS prefill (cuối file, gated `{% if mode == 'edit_activity' and activity_edit %}`) tái dùng đúng `m08PickHT`/`m08OnOutcome`/`m08OnReason` sẵn có (không viết lại state machine pill).

2 entry point (đúng rule report mục V — chỉ pre-fill khi trỏ đích danh):
- **✏️ Sửa** trên mỗi dòng timeline có `contact_outcome` (`c360_timeline_panel.html`) — GET `/modals/m08?mode=edit_activity&activity_id=<id>`.
- `[⋯ Chi tiết]` từ disposition strip — **chưa build** (strip là P2, xem mục Deviation #1).

### 8. "Gọi" button (identity_bar, `c360_call_cockpit_panel.html`)
`onclick` đổi từ mở M08 thẳng → `s14StartCallSession(party_id)`: `fetch POST /api/parties/{id}/call-sessions` (idempotent) → mở M08 `mode=log` với `draft_activity_id=<id>` kèm theo (hidden field trong form) → submit M08 sẽ PATCH+finalize đúng draft đó (mục 6). Fetch lỗi (401 khi chưa đăng nhập CF Access trong môi trường LAN-trust, hoặc network) → fallback mở M08 y hệt luồng cũ (không chặn rep ghi log, chỉ mất đo duration).

## Handoff wiring `source_activity_id` (từ plan 260709-1638 phase-01)

**Không cần code thêm.** Lý do: phase-01 report đó xác định gap vì tag-attach (`/tags/inline`) xảy ra RỜI khỏi transaction log-activity — cần client JS giữ lại `activity_id` trả về sau khi POST. Với kiến trúc draft mới, `activity_id` của phiên gọi đã biết NGAY sau `call-sessions` (trước khi tag-attach xảy ra), không cần đợi response của log-activity nữa. Đã kiểm tra `_s14_collect_row.html`/tag_multiselect forms trong `c360_call_cockpit_panel.html`: cần 1 hidden input `source_activity_id` đọc từ draft id lưu lúc `s14StartCallSession()` chạy — **việc này thuộc luồng tag-attach trong phiên gọi, chưa có UI trigger nào gọi `s14StartCallSession` trước khi bấm tag trong P1** (chỉ trigger khi bấm nút Gọi → mở M08 ngay, không dừng ở cockpit để bấm tag trước). Với disposition strip (P2, ở lại cockpit không mở modal), draft id tồn tại suốt phiên → lúc đó wiring 1 hidden field vào tag form mới có ý nghĩa thật. Ghi nhận lại trong Unresolved — không làm nửa vời (thêm hidden field nhưng không có gì set giá trị) để tránh false sense of done.

## Deviation khỏi phase file (có lý do, không tự ý bỏ scope)

1. **Không build disposition strip / `[⋯ Chi tiết]`** — plan.md tự phân `P2 — Disposition Strip v2` là phase riêng (`phase-03-disposition-strip-v2.md`), phase-02 chỉ yêu cầu API + M08 `edit_activity`. "Gọi" hiện vẫn mở M08 modal (không phải strip inline) — draft vẫn được tạo/PATCH/finalize đúng qua M08 submit, thỏa mãn "draft tạo khi bấm Gọi" + "duration tự đo" mà không cần UI strip.
2. **Không thêm status/started_at/finalize_at/contact_duration_s vào export/staging** — theo đúng câu "nếu rẻ" trong task: 4 cột này là pilot/nội bộ P1, chưa mart nào đọc, thêm export cần dagster re-materialize + dbt build (phase-01 báo cáo cho thấy việc này tốn ~30-60 phút + rủi ro lock contention). Deferred tới khi P2 dùng thật cột này cho mart (báo cáo rõ ở đây theo đúng yêu cầu).
3. **Không enforce chính xác cutoff 02:30 ICT** cho audit trail edit_activity — thay vào đó audit MỌI edit_activity trên row `final` khi `contact_outcome` thực sự đổi (superset an toàn hơn, không cần logic "trước/sau export" phức tạp). Nếu cần đúng cutoff thật (VD chỉ audit sau 02:30, trước đó cho sửa tự do không log) thì làm ở phase sau.
4. **Draft giữ nguyên `channel_type='call'`** dù M08 cho đổi "Hình thức" — nếu rep đổi sang zalo/email khi đang ở luồng draft-adopt, validate `patch_activity` vẫn theo `channel_type='call'` gốc (PATCH không cập nhật `channel_type`). Điều này khớp thực tế nghiệp vụ (draft chỉ tạo khi bấm nút Gọi = chắc chắn call) nhưng là giới hạn thật nếu rep đổi tay — ghi ở Unresolved.

## Tests

- `crm/src/tests/test_activity_draft_lifecycle.py` (14 test, mới) — `ActivityService` trực tiếp trên `seeded_crm_db` thật (migration áp dụng): idempotent draft theo (staff, party); PATCH reject enum sai theo channel_type; PATCH not-found → `ActivityNotFoundError`; `custom_fields_patch` merge không ghi đè; finalize 409 thiếu outcome; finalize set status+duration; finalize idempotent (2 lần → `finalize_at`/`contact_duration_s` không đổi); override duration tay thắng; audit trail edit_activity khi outcome thực đổi, KHÔNG audit khi outcome giữ nguyên.
- `crm/src/tests/test_activity_disposition_api_routes.py` (9 test, mới) — route-level qua `ActivityService` thật (không mock service, chỉ mock notes/task_svc/action_state/party_insights để đếm call count): call-sessions idempotent + 401 chưa đăng nhập; PATCH 422 enum sai + 404 not-found + 204 không side-effect (assert `notes.add_note`/`task_svc.auto_claim_from_contact` KHÔNG được gọi); finalize 409 + idempotent-không-double-note (assert `add_note` call_count==1 sau 2 lần finalize) + auto-claim chạy đúng 1 lần; **legacy log-activity draft-adopt**: verify trực tiếp trên DB (`crm_activity_log` row) rằng draft được finalize (status=final, contact_duration_s not null, body ghi đúng) và KHÔNG có row thứ 2 nào được tạo; regression không có `draft_activity_id` → vẫn insert fresh row, `status`/`contact_duration_s` = NULL (y hệt trước P1).
- Cập nhật 2 test file cũ (thêm 1 kwarg `draft_activity_id=""`, không đổi assertion): `test_bulk_resolve_endpoint.py` (3 chỗ), `test_quick_outcome_cockpit_post.py` (1 chỗ, `_base_kwargs`). Bắt buộc vì test gọi handler trực tiếp (bypass FastAPI DI) — tham số Form mới không truyền giữ nguyên sentinel `Form(...)` object thay vì `""`, `.strip()` văng `AttributeError`. Đây đúng pattern comment sẵn có trong file ("pass explicit defaults for direct calls").

### Kết quả chạy

```
docker compose exec -T crm pytest crm/src/tests/test_activity_draft_lifecycle.py \
  crm/src/tests/test_activity_disposition_api_routes.py -q
→ 23 passed

docker compose exec -T crm pytest crm/src/tests/test_bulk_resolve_endpoint.py \
  crm/src/tests/test_quick_outcome_cockpit_post.py crm/src/tests/test_claim_context_snooze_r14.py \
  crm/src/tests/test_m08_quick_note_prefill.py crm/src/tests/test_outcome_bulk_resolve.py -q
→ 55 passed

docker compose exec -T crm pytest -q
→ 1031 passed, 0 failed (1008 baseline + 23 test mới; full suite xanh 100%, không ngoại lệ)
```

### Verify live

```
docker compose restart crm → OK
curl http://127.0.0.1:3007/healthz → 200
PRAGMA table_info(crm_activity_log) trên crm.db sống → status/started_at/finalize_at/contact_duration_s có mặt
schema_migrations chứa '0045_activity_draft_lifecycle.up.sql'
GET /customers/{id}/call → 200; GET /modals/m08?mode=log → 200
GET /modals/m08?mode=edit_activity&activity_id=<không tồn tại> → 200 (activity_edit=None, không crash)
GET /modals/m08?mode=edit_activity&activity_id=<thật, có contact_outcome> → 200
GET /customers/{id}/panels/timeline → chứa nút "✏️ Sửa" cho activity có contact_outcome
POST /api/parties/{id}/call-sessions (không đăng nhập, dev LAN-trust không CF Access) → 401 (đúng thiết kế — draft cần staff sở hữu; JS fallback mở M08 thường)
```

## Unresolved

1. `source_activity_id` (tag-attach ↔ activity) vẫn chưa có UI trigger thật gửi giá trị — infra sẵn sàng từ phase-01, cần P2 (disposition strip ở lại cockpit lâu hơn 1 lần mở-modal) mới có chỗ wiring hợp lý. Không làm nửa vời trong P1.
2. Draft giữ `channel_type` cố định = `call` — đổi "Hình thức" giữa chừng trong M08 (khi đã có `draft_activity_id`) sẽ validate outcome theo `channel_type` GỐC của draft, không theo lựa chọn mới trên form. Case hiếm (luồng Gọi luôn là call) nhưng chưa có test/guard riêng.
3. Chưa QA bằng mắt trên trình duyệt thật (môi trường agent không có browser) — đặc biệt: JS `s14StartCallSession` fetch chain, prefill `edit_activity` (pill re-render đúng theo `channel_type`/`contact_outcome`/`outcome_reason` đã lưu), và hành vi khi `call-sessions` 401 (cần user đăng nhập qua CF Access thật để test end-to-end thành công, môi trường dev hiện tại LAN-trust không có login).
4. Cutoff 02:30 ICT export chưa implement chính xác (xem Deviation #3) — hiện audit MỌI edit trên row final, không phân biệt trước/sau export.
5. Export/staging cho 4 cột mới (status/started_at/finalize_at/contact_duration_s) chưa thêm (xem Deviation #2) — cần làm khi P2/mart thật sự cần đọc.

Status: DONE
Summary: Migration 0045 + repo/service/route đầy đủ theo spec mục III; side-effect executor hợp nhất (fix thêm 1 bug callback-task chết); legacy POST giữ nguyên contract ngoài, refactor bên trong qua cùng executor + hỗ trợ draft-adopt; M08 edit_activity mode hoạt động qua PATCH thật; 1031/1031 test xanh (1008 cũ + 23 mới); container restart + healthz 200 + migration verify live.
Concerns: (1) chưa QA browser thật; (2) source_activity_id handoff vẫn chờ P2 mới có nơi wiring ý nghĩa; (3) draft channel_type cố định là giới hạn nhỏ chưa test riêng.
