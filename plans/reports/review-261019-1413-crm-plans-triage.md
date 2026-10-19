# Rà plan CRM/HUG cũ, log CSRF và tag sức khoẻ — 19/10/2026

Chỉ đọc: không sửa code, không đụng prod (chỉ `docker inspect`, `docker logs`, đọc bản sao `crm.db`
đã xoá sau khi đếm). Không có dữ liệu khách trong báo cáo, chỉ số đếm.

## Kết luận

- Trong 12 plan, chỉ hai việc nhỏ nên làm tiếp: bật chặn CSRF và kiểm tra migration D1 của Hug
  (`260623-0852`). Cụm Hug/A2/tag nên gộp vào đợt chuẩn hoá CRM; còn lại đóng.
- Không có code nào nằm ngoài `main`: mọi nhánh và worktree đều không đi trước `main`, không có
  thay đổi chưa commit ở `crm/` hay `webhook_receiver/`, stash rỗng. "Code xong chưa deploy" của
  `260623-0852` đã ở trên `main` và đã nằm trong lần deploy Worker 10/07.
- CRM đang chạy đúng code `main`: `docker-compose.yml` mount `crm/src` và `crm/migrations` từ checkout
  prod. Image build 10/08, process khởi động lại 09/10; sau đó chỉ một commit đụng `crm/src`, và chỉ
  sửa test.
- Hug chưa ai dùng: log container từ 10/08 (khoảng 927 nghìn dòng) không có request `/hug*` nào.

## 1. Trạng thái 12 plan

| Plan | Trạng thái thật trên `main` | Còn lại | Đề xuất | Effort | Rủi ro |
|---|---|---|---|---|---|
| 260618 crm-i18n-json-locale | Chưa làm gì (không có `i18n.py`, `locales/`) | Cả 6 phase | Đóng | (3–4 ngày nếu làm) | Không; một tenant tiếng Việt, research §8 không cần |
| 260619 crm-nba-resell-engine | Plan tổng: A1 xong (`mart_customer_tier`); A3/A4 thành action type `SECOND_ORDER`/`WIN_BACK`; code Hug M2–M5 xong; Stage B hoãn | A2 go-live, Stage B | Đóng (lưu trữ); A2 chuyển sang chuẩn hoá | 0 | Không |
| 260620-1148 crm-hug-campaign-admin-ui | Xong phase 1–6 (`e64f9b19`), đang chạy; plan vẫn ghi "pending" | Phase 7 (đã hoãn) | Đóng (cập nhật status); gộp `crm_hug_campaign` thành Campaign có `type` thuộc chuẩn hoá §8.3 | 0 | Không |
| 260620-1408 crm-hug-voucher-a2-golive | P1–P4 xong (`6da9ceea`: migration 0025, issuer/redeem trong `/admin/refresh`, landing có `campaign_id`); Worker deploy 10/07 | P5 go-live (mã HUG50 trên Sapo, dòng campaign A2, in tem); landing vẫn hiện mã ngay, lệch quyết định #2 ngày 10/07 (gửi qua Zalo OA) | Gộp vào chuẩn hoá (Campaign type=hug + arm holdout) | 1–2 ngày kỹ thuật + vận hành | Copy landing lệch quyết định; cần người vận hành |
| 260620-2357 hug-a2-pilot-holdout | Không có code | Toàn bộ | Gộp vào chuẩn hoá (§8.4 bước 4 "Holdout và quy công") | 2–3 ngày + 8–20 tuần chạy | Mẫu nhỏ (khoảng 40/22 khách); cần M5 chạy trước |
| 260623-0852 hug-campaign-matching-and-preview | Code P1–P3 trên `main` (`ed6bdfa`, `43c6b65b`, `86043cc3`); deploy Worker 10/07 (`6b049e49`) đã gồm code này | Chưa xác minh migration D1 `add_hug_customer_type_column.sql` và full resync (`HUG_CUSTOMER_PUSH_FULL=1`) | **Làm tiếp**: đọc schema D1, chạy migration nếu thiếu, resync | 0,5 ngày | Thiếu cột thì query quét tem lỗi (đọc code: có thể âm thầm về fallback, chưa xác nhận); chưa ai quét nên chưa ảnh hưởng, nhưng chặn go-live |
| 260623-1019 hug-claim-scan-robustness | P1–3 xong và đã deploy (`afd271d`, `2d38bec`) | P4: cột `attributes` dùng chung ở edge | Đóng (P4 chưa có nhu cầu) | 0 (P4 khoảng 0,5 ngày nếu cần) | Không |
| 260623-2257 crm-messenger-webhook-hmac | Chưa làm; còn TODO ở `conversation_handler.py:85` | Toàn bộ (công thức có trong plan) | Đóng, chuyển vào backlog Messenger (research: hoãn) | 0,5 ngày khi bật Messenger | Thấp: endpoint chưa xác thực nhưng chỉ bind 127.0.0.1, sau CF Access, 0 lần gọi |
| 260623-2318 crm-csrf-guard | Code xong, chạy log-only (`CRM_CSRF_ENFORCE=false`, đã kiểm `docker inspect`) | Bật chặn | **Làm tiếp** (mục 2) | 0,1 ngày | Thấp |
| 260626-1113 s14-dynamic-branching-script | P1–P3, P5 (PoC) xong (`5a460d12`); P4 bỏ có chủ đích | Chưa có bộ sinh tạo `nodes`; chỉ 1 file PoC | Đóng; tự sinh kịch bản phân nhánh, nếu cần, thuộc pack `sales_playbook` | (2–3 ngày nếu đưa vào dùng) | Không |
| 260707-2343 crm-tag-deferred-followups | Không làm gì (`crm_sync_outbox` không tồn tại) | 2 phase bị chặn + ý tưởng | Gộp vào chuẩn hoá (§8.3: write-back thành `crm_export`, ghi Sapo hoãn, tag theo cấu hình tenant), rồi đóng | — | Không |
| 260805-1216 crm-worklist-suppression-settings-panel | Xong và đã deploy (`8e322145`, migration 0046, panel P07); reverse-ETL `wh_action_scenario_registry` 13 dòng ok; plan vẫn ghi "pending" | Không | Đóng (cập nhật status) | 0 | Không |

Ba plan ghi "pending" nhưng code đã xong và đang chạy: 260620-1148, 260620-1408 (P1–P4), 260805-1216.
Phần lớn việc dọn là cập nhật status rồi lưu trữ.

## 2. CSRF guard ở chế độ log-only

**Kết quả: 0 lần gắn cờ** (cả "would block" lẫn "BLOCKED") từ 10/08/2026 tới nay (coordinator kiểm
lại: `docker logs crm | grep -c "csrf_guard:"` = 0).

- **Không có log tháng 7:** container `crm` được tạo lại 10/08 15:47 UTC, log cũ mất. Từ đó chỉ
  restart nên log còn đủ; driver `json-file` không đặt max-size, không bị cắt.
- **Guard xét gì:** POST/PUT/PATCH/DELETE ngoài `/api/*`, so host của `Origin` (hoặc `Referer`) với
  `Host`. Request không có cả hai được cho qua và chỉ ghi ở mức debug.
  - Code: `crm/src/adapters/inbound/http/csrf_guard.py`.
  - Log ra stderr của container, không có timestamp trong message (dùng `docker logs --timestamps`).
- **Người gọi (242.058 request trong access log):**

| Người gọi | Request | Số lần | Kết luận |
|---|---|---|---|
| 127.0.0.1 | `GET /healthz` | 200.055 | Healthcheck |
| `data_platform` (urllib, không gửi Origin) | `POST /admin/refresh` | 42.764 | Hợp lệ; guard cho qua, bật chặn vẫn chạy |
| như trên | `POST /admin/backup` | 70 | Hợp lệ |
| Người dùng qua Cloudflare tunnel | GET | khoảng 160 (tháng 8: 150, tháng 9: 12, tháng 10: 0) | — |
| như trên | `POST /customers/<id>/log-activity` (14/08, 200) | 1 | Không bị gắn cờ: tunnel giữ nguyên Host |

- **Bật chặn được chưa: được**, rủi ro chặn nhầm thấp:
  - không người gọi hợp lệ nào bị gắn cờ;
  - lệnh gọi giữa các service không có Origin;
  - audit form ngày 06/07 cho thấy mọi form đều gửi cùng origin.

  Bằng chứng mỏng: hơn 2 tháng chỉ có 1 POST từ trình duyệt, chưa có Hug hay S14, nên một màn hình
  chưa từng dùng vẫn có thể bị chặn. Rollback rất nhanh.
- **Lỗ hổng riêng, nên sửa ở đợt sau, không phải điều kiện để bật:** một số route `/api/*` được gọi
  từ trình duyệt bằng cookie CF Access, không có token, nên guard không bảo vệ:
  - `POST /api/parties/{id}/call-sessions`
  - `PATCH /api/activities/{id}`
  - `POST /api/activities/{id}/finalize`
  - `POST /api/parties/{id}/script-nav`

  Cách sửa: bỏ miễn trừ `/api/*`. Request không có Origin (webhook, gọi bằng token) vẫn được cho qua.
- **Cách bật** (theo runbook `docs/operations/deployment.md`, giờ do user duyệt):
  1. Lưu log cũ trước, vì tạo lại container sẽ xoá log: `docker logs -t crm > <backup>`.
  2. Đổi default trong `docker-compose.yml` thành `${CRM_CSRF_ENFORCE:-true}`, commit để cấu hình
     nằm trong git; hoặc đặt `CRM_CSRF_ENFORCE=true` trong `.env`.
  3. `docker compose up -d crm`. Phải tạo lại container: restart không đọc lại env. Lúc khởi động,
     entrypoint chạy migration, reverse-ETL và sync.
  4. Kiểm tra:
     - `docker inspect` cho thấy biến = true;
     - POST thử tới một route CRM với `Origin` lạ trả 403, log có `BLOCKED`;
     - cùng request với Origin cùng host không bị 403;
     - một thao tác thật trên UI (gắn tag, ghi hoạt động) chạy được;
     - lần `/admin/refresh` kế tiếp vẫn trả 202.
  5. Rollback: đặt lại `false`, rồi `docker compose up -d crm`.

## 3. Tag sức khoẻ: bước an toàn chờ luật sư (đề xuất, chưa làm)

**Dữ liệu hiện có** (đếm trên bản sao `crm.db`):
- `health_concern` (migration 0042): 8 tag trong catalog, **0 lần gắn** cho khách.
- `health_domain` (cũng là dữ liệu sức khoẻ): 8 tag, 2 lần gắn cho 1 khách (tháng 07/2026, do người
  dùng CRM gắn).
- `crm_party_tag` có tổng 1.464 dòng; tài khoản gồm 2 admin, 3 sales.

**Đường ghi tag:**
- Modal M03: `POST /customers/{id}/tags` gắn bất kỳ tag nào, không kiểm category.
- S14 inline: `INLINE_ALLOWED_CATEGORIES`.
- Tạo tag L1: `POST /customers/{id}/tags/create`.
- API token: `POST /api/parties/{id}/tags`.
- Admin:
  - `/settings/tags`;
  - M14 có option `health_concern`;
  - governance promote/merge, nút "Tạo tag L1: health_concern".
- Sync nhóm khách Sapo qua `crm_ext_tag_map`: hiện không có map nào sang tag sức khoẻ.

**Đường xem và rò rỉ:**
- Đầu trang C360 lấy từ view `crm_party_360.tags_json`. View này không lọc tag archive.
- `GET /api/parties/{id}/360`.
- Export sang data lake: `crm_writeback_assets.py` snapshot `crm_party_tag` (kèm `customer_id`),
  rồi vào `stg_crm__party_tag`, Metabase/Rill đọc được, và `mart_staff_performance_weekly`
  (`health_concern_tags_new`).

**Phân quyền hiện có:** `AppUser.role` gồm sales, care, manager, admin, lấy từ JWT của CF Access.
Hiện chỉ có `require_admin`; `AuthorizationService` chưa kiểm theo role.

**Cách làm đề xuất:**
1. Một hằng số domain `RESTRICTED_TAG_CATEGORIES = {"health_concern"}` (thêm `health_domain` nếu user
   duyệt).
2. **Ngừng gắn mới:**
   - Migration 0047 thêm trigger SQLite chặn INSERT vào `crm_party_tag` và tạo hoặc đổi category của
     `crm_tag` thuộc nhóm hạn chế. Lớp chặn ở DB nên mọi đường ghi đều bị chặn.
   - Cùng migration đặt `is_archived=1` cho các tag đó để chúng biến mất khỏi picker M03/S14/M14. Có
     file down đi kèm.
   - Thêm kiểm tra rõ ràng trong `TagService` (`attach_tag`, `create_tag`, `find_or_create_tag`,
     `update_tag`) và `TagGovernanceService` (promote, merge), trả 400/403 thay vì 500.
   - Bỏ category khỏi `INLINE_ALLOWED_CATEGORIES`, `_CREATE_CATEGORY_LABEL`, option M14 và nút chipify.
   - Cần test trigger với `INSERT OR IGNORE`, vì merge của governance dùng câu lệnh này.
3. **Giới hạn người xem:**
   - Thêm `AuthorizationService.can_view_restricted_tags(user)`.
   - Lọc trong `Party360.tags` (`profile_repository.py`: đầu trang C360 và API 360) và trong
     `list_party_tags`.
   - Lọc khỏi export: `WHERE category NOT IN (...)` trong `crm_writeback_assets.py`. Khi đó
     `health_concern_tags_new` luôn bằng 0.
4. **Ảnh hưởng:**
   - Không xoá dòng nào.
   - `health_concern` đang có 0 lần gắn nên người dùng chỉ thấy picker bớt lựa chọn.
   - Nếu gồm `health_domain`: 2 dòng còn nguyên nhưng chỉ người được phép thấy, và hàng gợi ý
     "Lĩnh vực sức khoẻ" trên S14 (`health_domain_collect.py`) phải ẩn.
5. **Test:**
   - Sửa `test_health_domain_collect_and_tags_inline.py`, `test_m03_tag_inline_creation.py`,
     `test_tag_governance_admin.py`.
   - Thêm test: trigger chặn, mỗi route trả 400/403, role được xem và không được xem, export không
     chứa category hạn chế.
6. **Effort và deploy:**
   - Khoảng 1 ngày cho CRM, cộng 0,5 ngày cho export và dbt.
   - Code và migration của CRM được bind-mount: deploy bằng `docker restart crm`, giữ được log CSRF.
     Nếu làm cùng việc bật CSRF thì `up -d` một lần, sau khi đã lưu log.
   - Phần export cần deploy `data_platform` theo runbook.

## Câu hỏi còn mở (cần user)

1. Chặn cả `health_domain` (2 lần gắn hiện có) hay chỉ `health_concern`?
2. Ai được xem tag sức khoẻ: chỉ admin, hay admin và manager?
3. Có lọc dữ liệu sức khoẻ khỏi export data lake ngay trong bước tạm này không?
4. Giờ deploy bật CSRF, có gộp chung với bước tag sức khoẻ không?
5. `260623-0852`: có cho đọc schema D1 production (wrangler, chỉ đọc) để xác minh cột
   `customer_type` không?
