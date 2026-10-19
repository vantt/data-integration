# Phase 1: tag sức khoẻ theo phương án C + B (bản tạm), phân loại dữ liệu ở tag, bật chặn CSRF

**Effort:** 3d · **Phụ thuộc:** phase 0 (công cụ parity, danh sách đường ghi/xem tag) · **Đụng prod:** có (CRM; data_platform cho phần export) · **Cần user duyệt giờ:** có · **Migration:** 0047–0049

## Bối cảnh

- `health_concern` (8 tag, 0 lần gắn) và `health_domain` (8 tag, 2 lần gắn) là dữ liệu sức khoẻ, thuộc dữ liệu nhạy cảm theo Nghị định 356/2025 (báo cáo triage mục 3).
- **Quyết định user 19/10/2026 ~15:40: phương án C + B** (design §6.2), thay cho "chặn gắn, chỉ admin xem". Sales/CS là người thường ghi nhận thông tin này nên quy trình gắn không được bị phá:
  - C: loại tag mới "quan tâm nhóm sản phẩm" (`product_interest`, dữ liệu thường) là cách mặc định. **Sales/CS tự đặt tên danh mục ngay trong CRM** (Q11 đã chốt), có audit, chống trùng tên; deploy với danh mục rỗng được.
  - B: tag sức khoẻ thật giữ lại; gắn được khi khách đã có đồng ý riêng có bằng chứng; người xem là người phụ trách khách, manager, admin; mọi lần gắn/xem có audit; loại khỏi export, báo cáo, agent. Không xoá 2 lần gắn hiện có, chỉ ẩn theo quyền.
- Sổ cái consent ở phase 7 và audit chung ở phase 2 chưa có, nên phase này làm **bản tạm**: bảng cờ đồng ý riêng `crm_sensitive_consent_flag` và nhật ký tạm `crm_interim_audit_log`. Phase 2 chuyển nhật ký sang audit chung; phase 7 chuyển cờ sang sổ cái.
- Đường ghi tag: modal M03 `POST /customers/{id}/tags`, S14 inline (`INLINE_ALLOWED_CATEGORIES`), tạo tag L1 `POST /customers/{id}/tags/create`, API `POST /api/parties/{id}/tags` (`crm/src/adapters/inbound/http/customer360_handler.py:198`), admin `/settings/tags`, M14, governance promote/merge.
- Đường xem: view `crm_party_360.tags_json` (`0026_consent_contact_enum.up.sql`, không lọc), `GET /api/parties/{id}/360` (`customer360_handler.py:117`), `profile_repository.py`, `list_party_tags`, panel tag C360, call cockpit.
- Đường ra ngoài: export `crm_writeback_assets.py:150-157` (`crm_tag`, `crm_party_tag`) → `stg_crm__party_tag` → `mart_staff_performance_weekly` (`health_concern_tags_new`).
- "Người phụ trách khách" ở phase này là `crm_customer_profile.owner_user_id` (`0003`); phase 8 chuyển sang `owner_user_id` của vai trò `customer`. Khách chưa có người phụ trách: người đã ghi nhận đồng ý riêng đang hiệu lực cũng được xem (Q12 đã chốt).
- CSRF guard log-only, miễn trừ `/api/*` (`crm/src/adapters/inbound/http/csrf_guard.py:38,53`); 0 lần gắn cờ từ 10/08 (triage mục 2).

## Yêu cầu

### Tag và dữ liệu nhạy cảm

1. **Migration `0047_tag_category_registry`:** bảng `crm_tag_category` (`category_code` PK, `label_vi`, `data_class` `basic`/`sensitive`, `sensitive_kind`, `requires_consent_purpose` NULL hoặc mã mục đích, `audit_reads` 0/1, `sort_order`, `created_at`). Seed mọi giá trị `crm_tag.category` đang có (danh sách đo ở phase 0) với `basic`; `health_concern` và `health_domain` là `sensitive`/`health`/`requires_consent_purpose='sensitive_profile'`/`audit_reads=1`; thêm loại mới `product_interest` (`basic`, `label_vi` "Quan tâm nhóm sản phẩm", `sort_order` đầu tiên). **Không seed tag** trong `product_interest`: sales/CS tự tạo (yêu cầu 7b). Cùng migration tạo partial unique index `uidx_tag_product_interest_name ON crm_tag(name) WHERE category='product_interest'` (phase 0 kiểm hiện `crm_tag.name` có trùng hay không). Down: drop index và bảng.
2. **Migration `0048_sensitive_consent_flag_and_log`:**
   - `crm_sensitive_consent_flag` (design §6.2 bảng thứ tự triển khai): `party_id` PK FK, `purpose_code` mặc định `sensitive_profile`, `status` `granted`/`withdrawn` (CHECK), `method` (`verbal_call`/`paper_form`/`web_form`/`zalo_message`/`in_store`), `evidence_type` (`interaction`/`file`/`url`/`note`), `evidence_ref`, `captured_by` FK `crm_app_user`, `captured_at`, `note`.
   - `crm_interim_audit_log` (chỉ thêm, trigger chặn UPDATE/DELETE): `log_id`, `occurred_at`, `user_id`, `party_id`, `action` (`tag_attach`/`tag_detach`/`tag_view`/`consent_grant`/`consent_withdraw`/`product_interest_create`/`product_interest_rename`/`product_interest_archive`), `tag_id`, `channel` (`web`/`api`), `request_path`, `detail_json` (không chứa nhãn tag).
   - Down: drop hai bảng (ghi rõ trong down: mất nhật ký tạm, chỉ chạy khi rollback ngay sau deploy).
3. **Migration `0049_sensitive_tag_guard`:** trigger `BEFORE INSERT ON crm_party_tag` từ chối (`RAISE(ABORT, 'sensitive_tag_requires_consent')`) khi tag thuộc loại có `requires_consent_purpose` và **không** có dòng `crm_sensitive_consent_flag` `status='granted'` của party đó. Không archive tag, không xoá dòng `crm_party_tag` nào. Down: drop trigger.
4. **Policy tạm** trong `AuthorizationService` (phase 2 gộp vào `policy.py`, cùng chữ ký):
   - `can_view_sensitive(user, party_id)`: `admin` hoặc `manager`; hoặc `sales`/`care` là `owner_user_id` của khách; hoặc, khi khách **chưa có người phụ trách**, `sales`/`care` là `captured_by` của cờ đồng ý riêng đang `granted` (Q12). Khách có cờ `withdrawn`: chỉ `admin`.
   - `can_write_sensitive(user, party_id, category)`: người dùng web/API có role bất kỳ trừ `viewer`, **và** khách có cờ `granted`. Token API chung (`X-CRM-Token`) không gắn được tag nhạy cảm (không biết người gọi để audit).
5. **Service:** `TagService.attach_tag`, `create_tag`, `find_or_create_tag`, `update_tag`, `detach_tag`; `TagGovernanceService` promote, merge: tag nhạy cảm thì kiểm `can_write_sensitive` (gắn) và cấm tạo/chuyển tag vào loại nhạy cảm trừ `admin`; từ chối trả 403 `sensitive_tag_requires_consent` (adapter đổi thành thông báo tiếng Việt), không bao giờ 500. Merge của governance dùng `INSERT OR IGNORE`: test trigger vẫn chặn đúng.
6. **`SensitiveConsentService`** (tạm): `grant(party_id, method, evidence_type, evidence_ref, note, user)`, `withdraw(party_id, reason, user)`; bắt buộc `method` và `evidence_type`; ghi `crm_interim_audit_log`. Khi `withdraw`, không gỡ tag; tag ẩn với mọi người trừ admin.
7. **Giao diện (giữ quy trình sales/CS):**
   - Picker M03, S14 inline, hàng gợi ý S14 (`health_domain_collect.py`): hiện `product_interest` đầu tiên cho mọi khách. Loại sức khoẻ chỉ hiện khi khách có cờ `granted`; nếu chưa, thay bằng nút "Ghi nhận khách đồng ý cho lưu thông tin sức khoẻ" mở modal nhỏ (cách thu thập, bằng chứng: chọn hoạt động vừa ghi hoặc ghi chú, ô ghi chú), lưu xong thì picker hiện loại sức khoẻ ngay (một lần bấm thêm, không phải đổi màn hình).
   - Danh sách loại lấy từ `crm_tag_category` (bỏ viết cứng trong `INLINE_ALLOWED_CATEGORIES`, `_CREATE_CATEGORY_LABEL`, option M14, nút chipify); thứ tự theo `sort_order`.
   - C360 hiện trạng thái đồng ý riêng (đã đồng ý / chưa / đã rút) cho người có quyền xem.
7b. **Danh mục "quan tâm nhóm sản phẩm" do sales/CS tự quản** (design §6.2, Q11):
   - `ProductInterestService.create(label, user)`, `rename(tag_id, label, user)`, `archive(tag_id, user)`; tạo: `sales`, `care`, `manager`, `admin`; sửa tên và lưu trữ: người tạo (`crm_tag` cần biết người tạo: ghi `created_by` vào `detail_json` của nhật ký và cột mới `crm_tag.created_by` trong migration 0047) hoặc `manager`/`admin`.
   - Chuẩn hoá tên: chữ thường, bỏ dấu, gộp khoảng trắng, bỏ tiền tố "quan tâm nhóm"; slug từ tên chuẩn hoá làm `name`; hiển thị "Quan tâm nhóm …". Trùng (kể cả với tag đã lưu trữ) → trả `duplicate` kèm tag sẵn có để chọn (UI hiện "Đã có nhóm này, dùng luôn?").
   - Chặn tên mang nghĩa bệnh: tên chuẩn hoá khớp nhãn của tag sức khoẻ hoặc danh sách từ khoá bệnh/triệu chứng (bảng cấu hình nhỏ `crm_health_term` seed từ 16 nhãn tag sức khoẻ hiện có, admin thêm được) → từ chối với gợi ý đặt theo nhóm sản phẩm.
   - Giao diện: nút "+ Thêm nhóm sản phẩm" ngay trong picker M03, S14 inline (tạo xong gắn luôn cho khách đang mở); trang nhỏ "Nhóm sản phẩm khách quan tâm" (danh sách, số khách đang gắn, người tạo, đổi tên, lưu trữ) mở cho mọi role trừ `viewer`.
   - Mọi lần tạo, đổi tên, lưu trữ ghi `crm_interim_audit_log`.
8. **Lọc xem và audit xem:** mọi chỗ trả tag (`Party360.tags` trong `profile_repository.py`, đầu trang C360, panel tag, call cockpit, `GET /api/parties/{id}/360`, `list_party_tags`) lọc tag `data_class='sensitive'` theo `can_view_sensitive`. Mỗi lần hiển thị tag nhạy cảm cho người được xem ghi một dòng `tag_view` (gộp: một dòng mỗi lần render mỗi party, không một dòng mỗi tag). View `crm_party_360` giữ nguyên định nghĩa; mọi chỗ đọc `tags_json` đi qua hàm lọc. Người không có quyền không thấy cả số lượng tag nhạy cảm.
9. **Ra ngoài:**
   - Export (`crm_writeback_assets.py`): `crm_tag` và `crm_party_tag` loại category có `data_class='sensitive'` (đọc `crm_tag_category`, thêm tên bảng vào `_CRM_TABLE_NAMES`); không export `crm_sensitive_consent_flag`, `crm_interim_audit_log`.
   - Báo cáo: `health_concern_tags_new` trong `mart_staff_performance_weekly` luôn bằng 0; ghi chú trong `transformation/models/packs/crm/README.md`. Tag `product_interest` đi qua export bình thường.
   - Agent: chưa có kênh agent ở phase này; quy tắc "không bao giờ tới agent" được ghi vào `crm/AGENTS.md` để phase 3 tuân theo.
10. Tài liệu: `crm/docs/crm-database-schema-reference.md` (ba bảng mới, trigger), `crm/AGENTS.md` (loại tag nhạy cảm khai báo ở `crm_tag_category`; dữ liệu nhạy cảm không ra export/agent), `crm/docs/ui-spec` (picker và modal đồng ý riêng).

### CSRF

11. `docker-compose.yml`: `CRM_CSRF_ENFORCE: ${CRM_CSRF_ENFORCE:-true}`.
12. `csrf_guard.py`: bỏ miễn trừ `/api/*` **đối với request có `Origin` hoặc `Referer`**; request không có cả hai vẫn được cho qua (webhook, gọi bằng token, Dagster). Không đổi gì khác.

## File

- Tạo: `crm/src/application/product_interest_service.py`, screen/fragment "Nhóm sản phẩm khách quan tâm"; `crm/migrations/0047_tag_category_registry.{up,down}.sql` (gồm `crm_tag.created_by`, unique index, bảng `crm_health_term`), `0048_sensitive_consent_flag_and_log.{up,down}.sql`, `0049_sensitive_tag_guard.{up,down}.sql`; `crm/src/application/sensitive_consent_service.py`; port và adapter cho cờ và nhật ký; template modal đồng ý riêng; test `crm/src/tests/test_sensitive_tags_consent_gate.py`, `test_sensitive_tag_visibility.py`, `test_product_interest_category.py`.
- Sửa: `crm/src/application/tag_service.py`, `tag_governance_service.py`, `health_domain_collect.py`, `authorization_service.py`; `crm/src/adapters/outbound/sqlite/tag_note_repository.py`, `profile_repository.py`; `crm/src/domain/ports/tag_repository.py`; screen `modals/screen_modal_tags.py`, `customer360/screen_customer_360.py`, `screen_customer_360_panels.py`, `screen_call_cockpit.py`, screen M14 và governance (danh sách đủ từ phase 0); `adapters/inbound/http/customer360_handler.py`, `csrf_guard.py`; `crm/src/composition.py` (wiring service mới); `docker-compose.yml` (một dòng); `orchestration/packs/crm/crm_writeback_assets.py`; tài liệu nêu trên.
- Sửa test: `test_health_domain_collect_and_tags_inline.py`, `test_m03_tag_inline_creation.py`, `test_tag_governance_admin.py`, `test_csrf_guard.py`.

## Các bước

1. Worktree `feat/crm-sensitive-tags-csrf`.
2. Migration + test trigger (insert trực tiếp, `INSERT OR IGNORE`, có/không có cờ, cờ `withdrawn`).
3. Policy tạm, `SensitiveConsentService`, kiểm ở service + adapter 403.
4. Giao diện picker, modal đồng ý riêng, trạng thái trên C360; lọc xem và log xem.
5. Lọc export + test DuckDB trên DB tạm.
6. CSRF + test.
7. Parity trên bản sao (mục kiểm bên dưới); `crm_export_parity.py`.
8. Gate data_platform cho thay đổi `orchestration/`: `scripts/shadow/gate.sh S` (dbt không đổi code; `health_concern_tags_new` đổi là khác biệt được khai báo).
9. Deploy với danh mục `product_interest` rỗng (user đã chốt: sales/CS tự thêm ngay trong picker).
10. Deploy một cửa sổ, giờ user duyệt: lưu log CRM (`docker logs -t crm > <backup>`); backup CRM + verify; data_platform theo runbook "Refactor deploys"; `docker compose up -d crm` (env đổi nên phải tạo lại container).
11. Hướng dẫn ngắn cho sales/CS (một đoạn trong `crm/docs/ui-spec` hoặc tin nhắn do user gửi): dùng "quan tâm nhóm sản phẩm" là mặc định; khi cần ghi tình trạng sức khoẻ thì ghi nhận đồng ý riêng trước.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Mỗi đường ghi tag (M03, S14 inline, tạo L1, API token, `/settings/tags`, M14, governance promote/merge): tag sức khoẻ cho khách **chưa có cờ** → 403, không có dòng mới; **có cờ `granted`** → gắn được với người dùng web, có dòng log `tag_attach`; qua `X-CRM-Token` → 403; tag thường và `product_interest` gắn như cũ, không có log |
| Unit | Trigger: chặn insert trực tiếp và `INSERT OR IGNORE` khi chưa có cờ hoặc cờ `withdrawn`; cho qua khi `granted`; down gỡ trigger |
| Unit | Xem: `admin`, `manager`, người phụ trách thấy tag sức khoẻ (có log `tag_view`); `sales` không phụ trách và `viewer` không thấy tag, không thấy số lượng; khách có cờ `withdrawn`: chỉ admin thấy |
| Unit | Hai lần gắn `health_domain` hiện có (fixture mô phỏng): còn nguyên trong DB, ẩn với người không có quyền |
| Unit | `SensitiveConsentService`: thiếu `method`/`evidence_type` → lỗi; grant/withdraw có log; withdraw không gỡ tag |
| Unit | Picker: `product_interest` đứng đầu; loại sức khoẻ chỉ hiện khi có cờ; nút ghi nhận đồng ý hiện khi chưa có |
| Unit | Nhóm sản phẩm: sales tạo được, tạo xong có nhật ký; trùng tên (khác hoa thường, dấu, khoảng trắng, có/không tiền tố "quan tâm nhóm", kể cả tag đã lưu trữ) → `duplicate`; tên khớp nhãn sức khoẻ ("mất ngủ") → từ chối; sales khác người tạo không đổi tên được, manager đổi được; đổi tên giữ gắn trên khách |
| Unit | Q12: khách chưa có người phụ trách, sales đã ghi nhận đồng ý xem được tag sức khoẻ (có log `tag_view`); sales khác không xem được; khi khách có người phụ trách thì quyền xem theo người phụ trách |
| Unit | Query export không có dòng thuộc loại nhạy cảm; có dòng `product_interest` |
| Unit | Nhật ký tạm: UPDATE/DELETE bị trigger chặn |
| Unit | CSRF: POST có `Origin` khác host → 403 khi enforce; cùng host → qua; không có `Origin`/`Referer` → qua; `/admin/refresh` không Origin → qua |
| Tích hợp | Toàn bộ `crm/src/tests`, `crm/sync/tests` xanh; gate S |

## Kiểm "CRM như cũ"

- `parity_snapshot diff` trên bản sao (trước = code `main`, sau = code nhánh + migration) chỉ được khác các mục khai báo trước:
  - (a) danh sách tag của các party đang có tag `health_domain` khi xem bằng user không phải admin/manager/người phụ trách (theo đo phase 0: 1 party);
  - (b) số dòng ba bảng mới; `crm_tag_category` có thêm loại `product_interest`;
  - (c) danh sách loại trong picker: thêm `product_interest`, loại sức khoẻ ẩn với khách chưa có cờ (hiện tại là mọi khách).
- Mọi hash worklist, task, tìm kiếm, segment, campaign, 360 (phần không phải tag) giữ nguyên. `crm_tag` và `crm_party_tag` **không bị đổi** (không archive, không xoá).
- `crm_export_parity.py`: chỉ `crm_tag` (bớt 16 dòng loại sức khoẻ) và `crm_party_tag` (bớt số lần gắn sức khoẻ, theo đo phase 0 là 2) khác; 9 bảng còn lại giống hệt.
- Sau deploy: `docker inspect crm` thấy `CRM_CSRF_ENFORCE=true`; POST thử với `Origin` lạ trả 403 và log có `BLOCKED`; một sales tạo một nhóm sản phẩm mới ngay trong picker và gắn cho khách (thấy dòng nhật ký `product_interest_create`), thử tạo trùng tên thì được gợi ý tag sẵn có, gắn một tag thường, ghi một hoạt động thành công; thử trên một khách thử nghiệm do user chọn: ghi nhận đồng ý riêng rồi gắn tag sức khoẻ, thấy log; lần `/admin/refresh` kế tiếp 202; nightly kế tiếp 11 export xanh.

## Đụng prod và duyệt

Có: migration CRM, tạo lại container CRM, deploy data_platform. Cần user duyệt giờ (một cửa sổ, ngoài 02:30–04:00).

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Sales/CS thấy thêm một bước khi muốn ghi tình trạng sức khoẻ | Chắc chắn × Thấp | `product_interest` là mặc định không cần bước nào; bước đồng ý chỉ một modal, ngay trong picker |
| Sales đặt tên nhóm lộn xộn hoặc gần trùng | Trung bình × Thấp | Chuẩn hoá và chống trùng; manager xem danh sách, đổi tên, lưu trữ; đổi tên không mất gắn |
| Sales đặt tên nhóm mang nghĩa bệnh (biến dữ liệu sức khoẻ thành dữ liệu thường) | Trung bình × Cao (pháp lý) | Chặn theo nhãn tag sức khoẻ và danh sách từ khoá; manager rà danh sách; nhật ký người tạo |
| Cờ đồng ý bị bấm cho có, không có đồng ý thật | Trung bình × Cao (pháp lý) | Bắt buộc cách thu thập và bằng chứng; mọi lần ghi có log người ghi; manager xem được nhật ký |
| Một màn hình ít dùng gửi Origin khác (ví dụ trang Hug) bị chặn | Thấp × Trung bình | Audit form 06/07 cho thấy cùng origin; rollback bằng một biến môi trường |
| Log xem phình to | Thấp × Thấp | Chỉ ghi khi thật sự hiển thị tag nhạy cảm (rất ít khách) |

## Rollback

- CSRF: đặt `CRM_CSRF_ENFORCE=false`, `docker compose up -d crm` (lưu log trước).
- Tag: `docker stop crm`; `crm/ops/migration_down.py` cho 0049, 0048, 0047 (sau khi đã có backup; down 0048 làm mất cờ và nhật ký tạm, nên trước khi down xuất hai bảng đó ra file trong thư mục backup an toàn); `git revert` phạm vi đã deploy; `docker start crm`. Phần export: `git revert` theo runbook data_platform.
- Còn lại sau rollback: tag `product_interest` đã tạo vẫn là dòng `crm_tag` với `category='product_interest'`, hiển thị như tag thường (vô hại).
