# Phase 2 (P1) — Draft + PATCH-theo-field + finalize API

## Context
Nguồn: [ux-design report](../reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md) mục III (API), quyết định đã chốt #1, #3. Phụ thuộc Phase 1 (enum `purchased` + đường ghi M08 đã ổn định).

Nguyên tắc: "Một đường ghi duy nhất" — cockpit PATCH và M08 POST phải đi qua CÙNG `ActivityService` + side-effect executor (hiện side-effect nằm rải trong `handle_log_activity`, ~150 dòng, cần extract trước khi thêm đường ghi thứ hai — tránh lặp lại bài học `party_insights` factory divergence đã nêu trong report mục II).

## Requirements

1. **`POST /api/parties/{party_id}/call-sessions`** — tạo draft activity (`status='draft'`, `channel_type='call'`, `started_at`=now, `task_id?`, `channel_identity_id?`). Idempotent: nếu (staff, party) đã có draft mở → trả lại draft đó, không tạo mới. Gọi khi bấm nút Gọi trên `identity_bar` (quyết định #1 — KHÔNG tạo lúc mở cockpit, KHÔNG lazy).
2. **`PATCH /api/activities/{activity_id}`** — nhận subset field: `contact_outcome, outcome_reason, body, callback_at, related_order_code, occurred_at, channel_identity_id, custom_fields.*`. Autosave mỗi lần commit field (blur/pill). Validate enum theo `channel_type` (dùng `CONTACT_OUTCOMES_BY_CHANNEL_TYPE` sẵn có). KHÔNG chạy side-effect nào. Trả 200 + fragment nhỏ hoặc 204.
3. **`POST /api/activities/{activity_id}/finalize`** — nhận `{complete_task_ids[], resolve_action_ids[], create_callback_task?, schedule_followup_at?, save_as_note?, promote_insight?}`. 409 nếu chưa có `contact_outcome`. Idempotent. Chạy toàn bộ side-effect tại đây (auto-claim dời từ POST cũ về finalize — KHÔNG claim khách chỉ vì mở cockpit). Trả fragment "✓ đã chốt" — KHÔNG redirect.
4. `contact_duration_s` = `finalize_at − started_at`, tự đo server-side, không cần staff nhập.
5. **Vòng đời draft**: 1 draft mở duy nhất per (staff, party); mở lại cockpit → adopt draft cũ; draft có outcome mà quên chốt → auto-finalize khi bấm "Khách kế →"; draft KHÔNG outcome → chip đỏ "phiên chưa chốt" trên worklist, 1 click resume/hủy — không bao giờ tự bịa outcome.
6. **Tương thích ngược**: giữ `POST /customers/{id}/log-activity` cho M08 standalone nguyên trạng — refactor bên trong để gọi qua create+patch+finalize của cùng service, không đổi contract form/response bên ngoài (không big-bang).
7. **M08 mode `edit_activity`** (mới — gap đã xác nhận trong report mục V, `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` `_m08_ctx` hiện chỉ có `log|edit_note|note_only`): dùng chính PATCH API. Chính sách: sửa tự do trong ngày (trước export 02:30 ICT), sau đó sửa phải ghi audit vào `custom_fields` (không làm mềm số liệu mart — coordinate với plan 260709-1638 nếu mart đang đọc `contact_outcome` trực tiếp).
8. Zalo-connect = 1 PATCH `custom_fields.zalo_connected` (khớp plan 260709-1638 phase-01 mục 1b — REFERENCE, không tự implement cột mart ở đây).

## Files to modify/create
- `crm/src/domain/entities/activity.py` — thêm `status` field (`draft|final`), `started_at`, `finalize_at` nếu chưa có (kiểm tra schema DB trước — có thể cần migration).
- `crm/src/application/activity_service.py` — extract side-effect executor từ handler hiện tại; thêm `create_draft`, `patch_activity`, `finalize_activity`.
- Router mới hoặc mở rộng `screen_customer_360_activity.py` — 3 route mới (`/api/parties/{id}/call-sessions`, `/api/activities/{id}` PATCH, `/api/activities/{id}/finalize`).
- `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` — thêm mode `edit_activity` (load draft/activity theo id, prefill).
- Migration DB nếu `crm_activity_log` chưa có cột `status`/`started_at`/`finalize_at` — xác nhận schema thật trước khi viết code (không giả định).
- Test mới cho draft lifecycle + PATCH validate + finalize idempotency + `edit_activity` mode.

## Implementation steps (outline — chi tiết hoá khi bắt đầu phase này)
1. Đọc schema thật của `crm_activity_log` (migration files/`domain/entities/activity.py`) — xác nhận cột nào đã có, cột nào cần thêm.
2. Extract side-effect executor từ `handle_log_activity` (150 dòng) thành hàm/class dùng chung — KHÔNG đổi hành vi hiện tại (refactor thuần, có test bảo vệ trước khi đổi).
3. Viết `create_draft` với idempotency check (staff, party, status='draft').
4. Viết `patch_activity` — validate theo `CONTACT_OUTCOMES_BY_CHANNEL_TYPE`, không side-effect.
5. Viết `finalize_activity` — gọi side-effect executor dùng chung với M08 POST; tính `contact_duration_s`.
6. Route mới + wiring FastAPI.
7. M08 mode `edit_activity` — load activity theo id (không phải "log gần nhất" — chỉ khi trỏ đích danh, đúng quy tắc report mục V).
8. Refactor `handle_log_activity` cũ gọi qua service mới, giữ contract HTTP y nguyên.

## Tests
- Idempotent draft creation: gọi 2 lần cùng (staff, party) → cùng 1 activity_id.
- PATCH reject sai enum theo channel_type (VD `contact_outcome='replied'` khi `channel_type='call'`).
- Finalize 409 khi chưa có `contact_outcome`.
- Finalize idempotent: gọi 2 lần không side-effect kép (không double-claim, không double-resolve task).
- `contact_duration_s` tính đúng từ mốc `started_at`/`finalize_at`.
- M08 `edit_activity`: load đúng activity theo id, không load "log gần nhất" bừa bãi.
- Regression: `POST /customers/{id}/log-activity` (M08 cũ) vẫn tạo activity + side-effect y hệt trước refactor (snapshot test nếu có).

## Rollback
- 3 route mới độc lập, tắt bằng cách không đăng ký router (không ảnh hưởng route cũ).
- Nếu refactor side-effect executor gây regression: giữ nguyên `handle_log_activity` cũ, hoãn "một đường ghi duy nhất" sang lần sau — KHÔNG được để refactor chặn ship P1 nếu rủi ro cao, tách thành sub-step riêng có thể revert độc lập.
- Cột DB mới (nếu cần) thêm nullable, không backfill bắt buộc — draft cũ trước ngày ship không có, chấp nhận `status IS NULL` = final (default an toàn).
