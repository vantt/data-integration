# Phase 11: hợp đồng export CRM → kho v1, dọn bảng cũ, kiểm khả chuyển Postgres, tài liệu

**Effort:** 3d · **Phụ thuộc:** phase 5–10, mỗi mục dọn chỉ làm khi phần tương ứng đã đọc từ nguồn mới ≥ 7 ngày không lỗi · **Đụng prod:** có (CRM và data_platform) · **Cần user duyệt giờ:** có · **Migration:** 0090–0099

## Bối cảnh

- Mọi query export join lặp lại `crm_party_identity` để lấy `customer_id` (`crm_writeback_assets.py:44-60`, dùng trong 7 bảng).
- Sau phase 5–10, nhiều chỗ còn ghi song song: bảng cache cũ, `crm_party_identity`, `consent_enum`, cột hồ sơ trong `crm_customer_profile`. Ghi song song kéo dài làm tăng rủi ro lệch.
- Đây là bước contract duy nhất khó đảo của plan (design §8.1 bước 5).

## Yêu cầu

1. **Export `crm_party_map`** (design §4.4) và viết lại `_dedup_identity_join` để join `crm_party_map` thay cho `crm_party_identity`. Kết quả 7 bảng export dùng join này phải giống hệt (cùng `customer_id` cho cùng `party_id`, kể cả quy tắc chọn một dòng khi có nhiều mã Sapo). Model staging `stg_crm__party_map` (public).
2. **Dọn cache:** bộ sync ngừng ghi bảng `wh_*` cũ (`wh_customer_insight`, `wh_customer_tier`, `wh_customer_base`, `wh_order_hdr`, `wh_action_queue`, `wh_sku_action_queue`, `wh_action_scenario_registry`, `wh_party_seed`, `wh_deadstock_target`); bỏ nhánh `v0` của `ContractReader` và cờ `CRM_CACHE_CONTRACT`; `cache_schema.sql` xoá DDL cũ, thêm `DROP TABLE IF EXISTS` cho bảng cũ. Pack `sales_playbook` bỏ nhánh đọc `wh_sku_action_queue`.
3. **Contract identity:**
   - Bỏ ghi song song vào `crm_party_identity` và cờ `CRM_READ_IDENTITY`.
   - Migration `0090_party_identity_compat_view`: đổi tên `crm_party_identity` thành `crm_party_identity_retired`, tạo VIEW `crm_party_identity` (UNION của contact point và identifier, đúng cột và giá trị cũ, `identity_type` dựng lại theo bảng ánh xạ phase 6) cho người đọc còn sót. Down: drop view, đổi tên lại, chạy lại backfill ngược từ hai bảng mới cho các dòng thêm sau phase 6 (viết và thử down trên bản sao trước khi deploy).
   - Migration `0091_drop_party_external_id`: drop `crm_party_external_id` (0 dòng, xác nhận lại ngay trước deploy). Down: tạo lại bảng rỗng.
4. **Contract hồ sơ và consent:** bỏ ghi song song `owner_user_id`, `lifecycle_stage`, `acquisition_source`, `birthday`, `gender` vào `crm_customer_profile` và cờ `CRM_READ_PARTY_ROLE`; ngừng ghi `consent_enum`; ngừng ghi song song `crm_sensitive_consent_flag` (migration `0093_sensitive_consent_flag_view`: đổi tên bảng thành `crm_sensitive_consent_flag_retired`, tạo VIEW cùng tên cũ dựng từ `crm_consent_current` với `purpose_code='sensitive_profile'`; down: drop view, đổi tên lại, chép ngược các sự kiện mới); `crm_interim_audit_log` giữ chỉ đọc làm hồ sơ. Cột cũ **giữ lại** (bỏ cột SQLite cần dựng lại bảng; lợi ích không đáng rủi ro), ghi chú "không còn ghi" trong schema reference; view `crm_party_360` đọc consent và hồ sơ từ nguồn mới (migration `0092_party_360_from_core` dựng lại view, cùng cột).
5. **Kiểm khả chuyển** `crm/ops/check_sql_portability.py` (design §8.2): quét migration từ 0047 và SQL trong adapter mới (danh sách file trong script); báo `INSERT OR`, `AUTOINCREMENT`, `strftime(`, `datetime('now'`, `json_group_array`, `json_extract` ngoài danh sách cho phép (trigger chỉ-thêm, trigger chặn tag, FTS5, `ATTACH`). Chạy trong test.
6. **Đánh dấu deprecated** các route `/api/*` cũ có route `/api/v1` tương đương (OpenAPI `deprecated=True`, header `Deprecation`); không xoá. Ghi danh sách người gọi còn lại (từ audit `system:legacy_api` 30 ngày).
7. **Tài liệu:**
   - `crm/docs/crm-database-schema-reference.md`: viết lại đầy đủ theo schema hiện tại (lõi, module, cache hợp đồng, export, quy ước), thay bản dừng ở 0014.
   - `crm/AGENTS.md`, `crm/README.md`: lõi, module, CommandBus, quy tắc khả chuyển.
   - `orchestration/packs/crm/README.md`, `transformation/models/packs/crm/README.md`: hợp đồng hai chiều.
   - `docs/architecture/modules.md` mục pack `crm`; ADR-020 cập nhật trạng thái.
8. Báo cáo đóng plan: so tiêu chí chấp nhận 1–10 của `plan.md`, ghi số đo.

## File

- Tạo: migration 0090–0093 (up/down); `crm/ops/check_sql_portability.py`; `transformation/models/packs/crm/staging/stg_crm__party_map.sql` + yml; test.
- Sửa: `orchestration/packs/crm/crm_writeback_assets.py`, `orchestration/packs/sales_playbook/approach_script_generation.py`, `crm/sync/*`, `crm/src/adapters/outbound/sqlite/contract_reader.py`, `identity_repository.py`, `profile_repository.py`, `profile_service.py`, `consent_service.py`, `scripts/checks/public_models.yaml`, tài liệu nêu trên.

## Các bước

1. Kiểm điều kiện: audit và log cho thấy mỗi phần đã đọc nguồn mới ≥ 7 ngày, parity hằng ngày 0 khác biệt.
2. Worktree `feat/crm-core-contract-cleanup`.
3. Export `crm_party_map` + viết lại join; `crm_export_parity.py` 11 bảng giống hệt; gate S.
4. Dọn cache (thử: xoá `cache.db` bản sao, sync dựng lại, parity snapshot không đổi).
5. Migration contract trên bản sao; thử down từng cái trên bản sao; parity.
6. Kiểm khả chuyển; tài liệu.
7. Backup + verify + sao ra thư mục an toàn; deploy data_platform và CRM trong một cửa sổ, giờ user duyệt.
8. Theo dõi 7 ngày; báo cáo đóng plan.

## Test

| Mức | Nội dung |
|---|---|
| Unit | View `crm_party_identity` trả cùng tập dòng, cùng cột như bảng cũ trên bản sao (so hash) |
| Unit | Join export qua `crm_party_map` cho cùng `customer_id` như join cũ, kể cả party có nhiều mã Sapo |
| Unit | `check_sql_portability.py` bắt được từng mẫu cấm trong fixture; 0 vi phạm trên code thật |
| Tích hợp | Toàn bộ test; sync dựng lại `cache.db` từ rỗng |

## Kiểm "CRM như cũ"

- `parity_snapshot diff` trước/sau: rỗng ngoài số dòng các bảng đã bỏ ghi (khai báo).
- `crm_export_parity.py`: 11 bảng giống hệt; bảng mới thêm.
- Sau deploy: UI, `/admin/refresh`, nightly export, approach script đêm kế tiếp như trước; 0 lỗi "no such table" trong `docker logs crm` 24 giờ.

## Đụng prod và duyệt

Có, cả CRM và data_platform; bước khó đảo nhất. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Còn người đọc bảng cũ chưa biết (script ops, notebook) | Trung bình × Trung bình | View tương thích tên cũ; `grep` toàn repo; log "no such table" |
| Down của 0090 sai làm mất identity thêm sau phase 6 | Thấp × Cao | Thử down trên bản sao có dữ liệu thêm giả; backup đã verify trước deploy |
| Dọn quá sớm khi ghi song song còn đang che lỗi | Thấp × Cao | Điều kiện 7 ngày và parity 0 trước khi bắt đầu |

## Rollback

`docker stop crm` (và data_platform theo runbook), `git revert` phạm vi đã deploy, `migration_down.py` 0093 → 0090 theo thứ tự ngược, `docker start crm`; sync dựng lại bảng cache cũ khi code cũ chạy lại. Nếu down 0090 lỗi: khôi phục backup theo `crm/docs/backup-restore-runbook.md` mục 3 (mất ghi sau thời điểm backup, phải báo user).
