# Phase 1: tag sức khoẻ an toàn, phân loại dữ liệu ở tag, bật chặn CSRF

**Effort:** 2d · **Phụ thuộc:** phase 0 (công cụ parity, câu trả lời Q3) · **Đụng prod:** có (CRM; data_platform cho phần export) · **Cần user duyệt giờ:** có · **Migration:** 0047–0049

## Bối cảnh

- `health_concern` (8 tag, 0 lần gắn) và `health_domain` (8 tag, 2 lần gắn) là dữ liệu sức khoẻ, thuộc dữ liệu nhạy cảm theo Nghị định 356/2025 (báo cáo triage mục 3). User đã đồng ý bước an toàn: ngừng thêm, giới hạn người xem, lọc khỏi export.
- Đường ghi tag: modal M03 `POST /customers/{id}/tags`, S14 inline (`INLINE_ALLOWED_CATEGORIES`), tạo tag L1 `POST /customers/{id}/tags/create`, API `POST /api/parties/{id}/tags` (`crm/src/adapters/inbound/http/customer360_handler.py:198`), admin `/settings/tags`, M14, governance promote/merge.
- Đường xem: view `crm_party_360.tags_json` (`0026_consent_contact_enum.up.sql`, không lọc), `GET /api/parties/{id}/360` (`customer360_handler.py:117`), `profile_repository.py`, `list_party_tags`.
- Đường export: `crm_writeback_assets.py:150-157` (`crm_tag`, `crm_party_tag`) → `stg_crm__party_tag` → `mart_staff_performance_weekly` (`health_concern_tags_new`).
- CSRF guard log-only, miễn trừ `/api/*` (`crm/src/adapters/inbound/http/csrf_guard.py:38,53`); 0 lần gắn cờ từ 10/08 (triage mục 2). Bốn route `/api/*` được trình duyệt gọi bằng cookie không được bảo vệ.
- Đây là bước đầu tiên của khái niệm "loại dữ liệu" trong lõi (design §6.1): registry `crm_tag_category` có `data_class`.

## Yêu cầu

1. **Migration `0047_tag_category_registry`:** bảng `crm_tag_category` (`category_code` PK, `label_vi`, `data_class` `basic`/`sensitive`, `sensitive_kind`, `is_restricted` 0/1, `created_at`); seed mọi giá trị `crm_tag.category` đang có (danh sách đo ở phase 0) với `data_class='basic'`; `health_concern` và `health_domain` (theo Q3) là `sensitive`/`health`/`is_restricted=1`. Down: drop bảng.
2. **Migration `0048_restricted_tag_guard`:**
   - Lưu `is_archived` hiện tại của các tag thuộc loại hạn chế vào `crm_tag_restriction_snapshot(tag_id, prev_is_archived)`, rồi đặt `is_archived=1`.
   - Trigger `BEFORE INSERT ON crm_party_tag` chặn khi tag thuộc loại `is_restricted=1` (`RAISE(ABORT, 'restricted_tag_category')`).
   - Trigger `BEFORE INSERT ON crm_tag` và `BEFORE UPDATE OF category ON crm_tag` chặn tạo hoặc chuyển tag vào loại hạn chế.
   - Down: drop trigger, khôi phục `is_archived` từ snapshot, drop snapshot.
   - Không xoá dòng `crm_party_tag` nào.
3. **Kiểm ở service** (trả lỗi nghiệp vụ, adapter đổi thành 403 `restricted_tag_category` thay vì 500): `TagService.attach_tag`, `create_tag`, `find_or_create_tag`, `update_tag`; `TagGovernanceService` promote, merge (merge dùng `INSERT OR IGNORE`: test trigger vẫn chặn).
4. **Gỡ khỏi UI:** bỏ loại hạn chế khỏi `INLINE_ALLOWED_CATEGORIES`, `_CREATE_CATEGORY_LABEL`, option M14, nút chipify "Tạo tag L1: health_concern"; ẩn hàng gợi ý "Lĩnh vực sức khoẻ" ở S14 (`crm/src/application/health_domain_collect.py`) khi loại đó bị hạn chế. Danh sách loại lấy từ `crm_tag_category`, không viết cứng.
5. **Giới hạn người xem:** `AuthorizationService.can_view_sensitive(user)` (v1: `role == admin`, hoặc theo câu trả lời Q3). Lọc tag thuộc `data_class='sensitive'` trong `Party360.tags` (`profile_repository.py`, đầu trang C360 và API 360), `list_party_tags`, panel tag C360. View `crm_party_360` giữ nguyên định nghĩa (không biết người xem); mọi chỗ đọc `tags_json` từ view phải đi qua hàm lọc. Phase 2 gộp hàm này vào policy.
6. **Lọc export:** trong `crm_writeback_assets.py`, `crm_tag` và `crm_party_tag` thêm điều kiện loại bỏ category có `data_class='sensitive'` (đọc `crm_tag_category`, thêm tên bảng vào `_CRM_TABLE_NAMES`). `health_concern_tags_new` trong `mart_staff_performance_weekly` sẽ luôn là 0: ghi chú thay đổi này trong `transformation/models/packs/crm/README.md`.
7. **CSRF:**
   - `docker-compose.yml`: `CRM_CSRF_ENFORCE: ${CRM_CSRF_ENFORCE:-true}`.
   - `csrf_guard.py`: bỏ miễn trừ `/api/*` **đối với request có `Origin` hoặc `Referer`**; request không có cả hai vẫn được cho qua (webhook, gọi bằng token, Dagster).
   - Không đổi gì khác của guard.
8. Tài liệu: `crm/docs/crm-database-schema-reference.md` thêm `crm_tag_category`; `crm/AGENTS.md` thêm quy tắc "loại tag nhạy cảm khai báo ở `crm_tag_category`, không viết cứng".

## File

- Tạo: `crm/migrations/0047_tag_category_registry.{up,down}.sql`, `crm/migrations/0048_restricted_tag_guard.{up,down}.sql`, `crm/src/tests/test_restricted_tag_categories.py`.
- Sửa: `crm/src/application/tag_service.py`, `tag_governance_service.py`, `health_domain_collect.py`, `authorization_service.py`; `crm/src/adapters/outbound/sqlite/tag_note_repository.py`, `profile_repository.py`; `crm/src/domain/ports/tag_repository.py` (thêm hàm đọc loại); các screen: `adapters/inbound/web/screens/modals/screen_modal_tags.py`, `customer360/screen_customer_360.py`, `screen_customer_360_panels.py`, `screen_call_cockpit.py`, screen M14 và governance (phase 0 đã liệt kê đúng file); `adapters/inbound/http/customer360_handler.py`, `csrf_guard.py`; `docker-compose.yml` (một dòng); `orchestration/packs/crm/crm_writeback_assets.py`; tài liệu nêu trên.
- Sửa test: `test_health_domain_collect_and_tags_inline.py`, `test_m03_tag_inline_creation.py`, `test_tag_governance_admin.py`, `test_csrf_guard.py`.

## Các bước

1. Worktree `feat/crm-sensitive-tags-csrf`.
2. Migration + test trigger (insert trực tiếp, `INSERT OR IGNORE`, update category).
3. Kiểm service + adapter 403; gỡ UI; lọc xem.
4. Lọc export + test DuckDB trên DB tạm (dòng hạn chế không ra).
5. CSRF: test `Origin` lạ trên `/api/activities/{id}` bị 403 khi enforce; không có `Origin` thì qua.
6. Parity trên bản sao (mục kiểm bên dưới); `crm_export_parity.py`.
7. Gate data_platform cho thay đổi `orchestration/`: `scripts/shadow/gate.sh S` (dbt không đổi code; số `health_concern_tags_new` đổi là khác biệt được khai báo).
8. Deploy một cửa sổ, giờ user duyệt:
   - Lưu log CRM (`docker logs -t crm > <backup>`), vì `up -d` tạo lại container và xoá log.
   - Backup CRM (migration 0048 đổi dữ liệu `is_archived`) + verify.
   - Data_platform theo runbook "Refactor deploys" (dừng, merge, start).
   - `docker compose up -d crm` (env đổi nên phải tạo lại container).
9. Kiểm sau deploy (bên dưới).

## Test

| Mức | Nội dung |
|---|---|
| Unit | Mỗi đường ghi tag (M03, S14 inline, tạo L1, API token, `/settings/tags`, M14, governance promote/merge) với tag hạn chế trả 400/403, không có dòng mới; tag thường vẫn gắn được |
| Unit | Trigger chặn insert trực tiếp và `INSERT OR IGNORE`; down khôi phục đúng `is_archived` |
| Unit | Người không phải admin: C360, API 360, danh sách tag không có tag nhạy cảm; admin thấy đủ |
| Unit | Query export không trả dòng thuộc loại nhạy cảm |
| Unit | CSRF: POST có `Origin` khác host → 403 khi enforce; cùng host → qua; không có `Origin`/`Referer` → qua; `/admin/refresh` không Origin → qua |
| Tích hợp | Toàn bộ `crm/src/tests`, `crm/sync/tests` xanh; gate S |

## Kiểm "CRM như cũ"

- `parity_snapshot diff` trên bản sao (trước = code `main`, sau = code nhánh + migration) chỉ được khác: (a) danh sách tag của các party đang có tag `health_domain` khi xem bằng user không phải admin; (b) số dòng `crm_tag_category`, `crm_tag_restriction_snapshot` (bảng mới); (c) `is_archived` của 16 tag hạn chế. Mọi hash worklist, task, tìm kiếm, segment, campaign giữ nguyên.
- `crm_export_parity.py`: chỉ `crm_tag` (bớt 16 dòng) và `crm_party_tag` (bớt số lần gắn hạn chế, theo đo phase 0 là 2) khác; 9 bảng còn lại giống hệt.
- Sau deploy: `docker inspect crm` thấy `CRM_CSRF_ENFORCE=true`; POST thử với `Origin` lạ trả 403 và log có `BLOCKED`; một người dùng gắn một tag thường và ghi một hoạt động thành công; lần `/admin/refresh` kế tiếp 202; nightly kế tiếp 11 export xanh.

## Đụng prod và duyệt

Có: migration CRM, tạo lại container CRM, deploy data_platform. Cần user duyệt giờ (một cửa sổ, ngoài 02:30–04:00).

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Một màn hình ít dùng gửi Origin khác (ví dụ trang Hug) bị chặn | Thấp × Trung bình | Audit form 06/07 cho thấy cùng origin; rollback bằng một biến môi trường |
| Trigger chặn cả luồng sync tag Sapo nếu sau này có map vào tag sức khoẻ | Thấp × Thấp | Hiện 0 map (triage); lỗi sẽ hiện rõ trong log sync, không im lặng |
| Người dùng cần xem tag sức khoẻ cũ | Thấp × Thấp | Admin vẫn xem được; dữ liệu không bị xoá |

## Rollback

- CSRF: đặt `CRM_CSRF_ENFORCE=false`, `docker compose up -d crm` (lưu log trước).
- Tag: `docker stop crm`; `crm/ops/migration_down.py` cho 0048 rồi 0047 (trên volume thật, sau khi đã có backup); `git revert` phạm vi đã deploy; `docker start crm`. Phần export: `git revert` theo runbook data_platform.
- Còn lại sau rollback: không có (down xoá bảng và trigger, khôi phục `is_archived`).
