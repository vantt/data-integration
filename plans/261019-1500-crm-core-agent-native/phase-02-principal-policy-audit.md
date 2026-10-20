# Phase 2: principal, credential, policy quyền, CommandBus, audit, idempotency

**Effort:** 4d · **Phụ thuộc:** phase 1 · **Đụng prod:** có (CRM) · **Cần user duyệt giờ:** có · **Migration:** 0050–0054

## Bối cảnh

- Lệnh ghi `/api/*` chỉ kiểm một token chung, không biết ai gọi; token rỗng thì bỏ kiểm (`crm/src/adapters/inbound/http/auth_dependency.py:26-50`). `/admin/refresh` dùng `CRM_REFRESH_TOKEN` hoặc `CRM_API_TOKEN` (`admin_handler.py:274-306`).
- Người dùng web được xác thực bằng JWT của Cloudflare Access (`cf_access_middleware.py:169-197`), có `role` sales/care/manager/admin; quyền chỉ có `require_admin` (`auth_dependency.py:53-71`) và so assignee (`authorization_service.py`).
- Không có audit chung: chỉ có lịch sử riêng lẻ (merge log, hug campaign history, `tagged_by`, `updated_by`).
- Đây là nền bắt buộc trước khi mở cho agent (design §5.2–5.6).

## Yêu cầu

1. **Migration `0050_app_user_principal_type`:** `crm_app_user.principal_type TEXT NOT NULL DEFAULT 'human'` và `agent_kind TEXT` (NULL với người; `assistant` hoặc `chat` với agent, design §5.9.3). Preset scope `assistant` và `chat_agent` trong `policy.py` (chat agent: chỉ party gắn với phiên, giới hạn ghi thấp hơn, không đề xuất hàng loạt, không merge); chưa tạo credential `chat` nào. Seed principal hệ thống: `system:sync` (sync trong process), `system:legacy_api` (người gọi `CRM_API_TOKEN`), `system:dagster` (người gọi `CRM_REFRESH_TOKEN`), `system:dev` (chế độ dev không có CF Access). Down: xoá các dòng seed; cột giữ lại (SQLite không drop cột an toàn với bản cũ; ghi rõ trong down là cột vô hại).
2. **Migration `0051_api_credential`:** bảng `crm_api_credential` theo design §5.2. Index `token_hash` unique.
3. **Migration `0052_audit_event`:** bảng `crm_audit_event` theo design §5.4; index (`party_id`, `occurred_at`), (`principal_id`, `occurred_at`), (`request_id`); trigger chặn UPDATE/DELETE trừ job dọn theo thời hạn (dọn bằng một lệnh có cờ phiên `crm_audit_retention`, hoặc tắt trigger trong transaction dọn; chọn cách đơn giản nhất khi làm và ghi lại).
4. **Migration `0053_idempotency_record`:** bảng `crm_idempotency_record` theo design §5.3.
5. **`crm/src/domain/policy.py`:** bảng quyền role → tập quyền (mã quyền dạng `party.read`, `interaction.write`, `tag.write`, `party.merge.execute`, `data.sensitive.read`, `proposal.approve`, `credential.admin`, `export.bulk`, …). **V1 mã hoá đúng hành vi hiện tại** cho người dùng (sales/care/manager được những gì hôm nay được; admin thêm `credential.admin`). Vai trò `agent`: tập quyền đọc + ghi an toàn + đề xuất, không bao giờ có các quyền liệt kê ở design §5.6. `AuthorizationService` giữ API hiện có, thêm `has(principal, permission)`. Dữ liệu nhạy cảm không phải một quyền phẳng mà theo quan hệ với khách (design §6.1–6.2): `can_view_sensitive(principal, party)` và `can_write_sensitive(principal, party, category)` của phase 1 chuyển vào `policy.py` **giữ nguyên quy tắc** (xem: người phụ trách, manager, admin; gắn: khi khách có đồng ý riêng; agent: không bao giờ). `proposal.approve` gán cho `manager` và `admin` (đã chốt 19/10).
6. **`crm/src/application/command_bus.py`:**
   - `CommandContext` (design §5.2) và `CommandBus.run(ctx, command_name, permission, handler, *, entity, party_id, idempotent=True)`.
   - Thứ tự: kiểm quyền (từ chối → audit `denied`) → kiểm idempotency (trùng → trả kết quả cũ) → transaction → handler → ghi idempotency + audit cùng transaction → commit.
   - `diff_json` che trường thuộc `data_class='sensitive'` và giá trị contact point (chỉ giữ dạng che).
   - Lệnh đọc của agent: `CommandBus.read(ctx, query_name, ...)` chỉ ghi audit, không idempotency.
7. **Xác thực thống nhất (`auth_dependency.py`):** thứ tự `Authorization: Bearer` (credential, tra `token_hash`, kiểm `revoked_at`, `expires_at`, cập nhật `last_used_at` tối đa mỗi phút) → `X-CRM-Token` (principal `system:legacy_api`, giữ hành vi bỏ kiểm khi biến trống như cũ, kèm cảnh báo) → người dùng CF Access → `system:dev` khi `CF_ACCESS_AUDIENCE` trống. Kết quả là `request.state.ctx`.
8. **Nối các lệnh ghi hiện có vào bus** (chỉ phần API và admin trong phase này; web UI ở phase 4): mọi route `/api/*` có POST/PUT/PATCH/DELETE (segment, campaign, dedup merge/undo, activity, task, profile, custom field, tag, note, conversation patch) và `/admin/refresh`, `/admin/backup`, `/admin/approach-scripts/load`. Hành vi và mã trả về không đổi.
9. **Job sync trong process** (`sync_parties`, `sync_party_tags`, reverse-ETL chỉ ghi `cache.db` nên không cần) chạy với ctx `system:sync`; audit gộp **một dòng mỗi lần chạy** (số party tạo/cập nhật), không một dòng mỗi party.
10. **Quản trị credential:** `crm/ops/credential_admin.py` (`create --principal <tên> --type agent --bound-user <user_id|none> --scopes <danh sách> --expires-days 90`, `list`, `revoke <id>`), chạy bằng `docker exec crm python -m crm.ops.credential_admin ...`; token in ra một lần; lệnh tự ghi audit với principal `system:ops`.
10a. **UUIDv7 (đã chốt 19/10, design §3.1.1):** `crm/src/domain/ids.py::new_id()` sinh UUIDv7 theo RFC 9562 (48 bit mili giây Unix, version 7, variant, 74 bit ngẫu nhiên từ `secrets`; tăng đơn điệu trong cùng mili giây bằng bộ đếm trong process), trả chuỗi 36 ký tự chữ thường. Thay **mọi** lời gọi `uuid.uuid4()` sinh id trong `crm/src`, `crm/sync`, `crm/ops` (19 file, đếm 19/10: `activity_service.py`, `task_service.py`, `app_user_service.py`, `tag_service.py`, `campaign_service.py`, `custom_field_service.py`, `segment_service.py`, `conversation_service.py`, `note_service.py`, `party_service.py`, `activity_side_effects.py`, `hug/identity_resolver_io.py`, `adapters/outbound/sqlite/dedup_repository.py`, `screens/management/screen_mgmt_settings.py`, `screens/modals/screen_modal_contact.py`, `screens/modals/screen_modals.py`, `screens/hug/screen_hug_review_data.py`, `crm/sync/reverse_etl_warehouse_to_crm.py`, `crm/ops/backfill_claim_tasks.py`). Không viết lại id cũ; giữ id tất định (`action_id` md5, seed `tag-...`). Test: định dạng và version/variant đúng; 100.000 id sinh liên tiếp duy nhất và tăng dần; id sinh trong cùng mili giây vẫn tăng; test quét mã nguồn: không còn `uuid4(` ngoài `ids.py` và test. `request_id`, `audit_id`, `idempotency_key` do hệ thống sinh, `credential_id` dùng `new_id()`; token bí mật dùng `secrets.token_urlsafe(32)`.
10b. **Chuyển nhật ký tạm của phase 1:** migration `0054_interim_audit_log_to_audit` chép mọi dòng `crm_interim_audit_log` sang `crm_audit_event` (`command` tương ứng `tag.attach_sensitive`, `tag.view_sensitive`, `sensitive_consent.grant`, …, giữ thời điểm, người, party), sau đó code ghi các sự kiện này vào audit chung qua bus; bảng tạm giữ lại chỉ đọc (trigger chặn ghi). Down: xoá các dòng audit đã chép (theo `command` và `occurred_at` ≤ thời điểm migration), code cũ ghi lại bảng tạm.
11. **Dọn:** idempotency hết hạn và audit quá thời hạn (Q5, mặc định 24 tháng) dọn ở cuối mỗi `/admin/refresh` thành công, giới hạn số dòng mỗi lần.
12. **ADR-020** `docs/decisions/020-crm-core-and-agent-interface.md`: quyết định CommandBus là cửa duy nhất, ba adapter mỏng, principal/credential, audit, đề xuất → duyệt, quy ước chung với MCP phân tích (design §5.10), lõi dữ liệu và hợp đồng (tóm tắt, trỏ tới schema reference). Cập nhật `docs/decisions/README.md`.

## File

- Tạo: migration `0050_app_user_principal_type`, `0051_api_credential`, `0052_audit_event`, `0053_idempotency_record`, `0054_interim_audit_log_to_audit` (mỗi cái có up/down); `crm/src/domain/policy.py`, `crm/src/domain/entities/command_context.py`, `crm/src/domain/ports/audit_repository.py`, `idempotency_repository.py`, `credential_repository.py`; `crm/src/application/command_bus.py`; `crm/src/adapters/outbound/sqlite/audit_repository.py`, `idempotency_repository.py`, `credential_repository.py`; `crm/ops/credential_admin.py`; test tương ứng; ADR-020.
- Sửa: `crm/src/application/authorization_service.py`, `crm/src/adapters/inbound/http/auth_dependency.py`, `cf_access_middleware.py` (gắn ctx), các `*_handler.py` có lệnh ghi (danh sách phase 0), `admin_handler.py`, `crm/src/sync_parties.py`, `sync_party_tags.py`, `crm/src/composition.py` (wiring bus, một instance), `crm/AGENTS.md` (quy tắc: lệnh ghi mới phải đi qua bus).

## Các bước

1. Worktree `feat/crm-command-bus-audit`.
2. Migration + repository + test.
3. Policy: viết test bảng quyền trước (mỗi role × mỗi quyền, khớp hành vi hiện tại theo danh sách route phase 0).
4. CommandBus + test (quyền, idempotency trùng/khác nội dung, rollback khi handler lỗi thì không có audit `ok` và không có idempotency `completed`).
5. Xác thực thống nhất; nối route API và admin.
6. Parity + toàn bộ test.
7. Deploy (backup trước vì có migration seed), giờ user duyệt. Tạo credential đầu tiên cho người thực thi để thử `/api/*` bằng Bearer.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Bảng quyền; agent không có quyền cấm dù scope ghi gì |
| Unit | Bus: một lệnh ghi → đúng một audit; lệnh bị từ chối → audit `denied`, không đổi dữ liệu; cùng key cùng body → kết quả cũ, không ghi thêm; cùng key khác body → 409 |
| Unit | Credential: token sai, hết hạn, bị thu hồi → 401; token đúng → ctx đúng principal và `on_behalf_of` |
| Tích hợp | Mỗi route `/api/*` ghi: mã trả về như cũ với `X-CRM-Token`; có audit với `system:legacy_api`; với Bearer có audit đúng principal |
| Tích hợp | `/admin/refresh` vẫn 202 với `X-Refresh-Token`; audit 1 dòng mỗi lần sync |

## Kiểm "CRM như cũ"

- Id mới có dạng UUIDv7 (cùng độ dài, cùng kiểu `TEXT`); parity snapshot so theo nội dung, không theo giá trị id mới sinh. Không chỗ nào sắp theo id (kiểm bằng `grep ORDER BY .*_id` trong adapter; nếu có chỗ dựa vào thứ tự id thì đổi sang `created_at` trong cùng phase).

- `parity_snapshot diff`: chỉ khác số dòng bảng mới (`crm_audit_event`, `crm_idempotency_record`, `crm_api_credential`) và 4 dòng principal hệ thống trong `crm_app_user`. Phải khai báo: `crm_app_user` export (`crm_writeback_assets.py:113`) sẽ có thêm 4 dòng; nếu không muốn đổi export thì lọc `principal_type='human'` trong query export (đề xuất: lọc, để `dim_staff` không thay đổi).
- `crm_export_parity.py`: 11 bảng giống hệt (sau khi lọc principal).
- Sau deploy: Dagster `crm_cache_refresh` xanh (dùng refresh token như cũ); `crm_backup_job` 02:00 đêm đó xanh; UI hoạt động như cũ (người dùng không thấy gì mới).

## Đụng prod và duyệt

Có (migration, khởi động lại CRM). Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Mã hoá quyền sai làm chặn một người dùng đang làm được việc | Trung bình × Trung bình | Bảng quyền v1 rộng như hiện tại; test theo danh sách route; log `denied` theo dõi 3 ngày đầu |
| Audit làm chậm lệnh ghi | Thấp × Thấp | Một INSERT trong cùng transaction; ~10 người dùng |
| Audit phình to | Thấp × Thấp | Sync gộp một dòng mỗi lần chạy; dọn theo hạn |

## Rollback

`docker stop crm`, `git revert`, `migration_down.py` cho 0053 → 0050 (bảng mới mất; cột `principal_type` ở lại vô hại), `docker start crm`. Mất audit đã ghi từ lúc deploy: chấp nhận được (chưa có gì phụ thuộc).
