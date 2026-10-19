# Phase 10: campaign hợp nhất (gộp Hug), holdout và quy công

**Effort:** 4d · **Phụ thuộc:** phase 4 (đề xuất hàng loạt), phase 5 (`wh_transaction`); câu trả lời Q9 · **Đụng prod:** có (CRM; data_platform cho export `arm`) · **Cần user duyệt giờ:** có · **Migration:** 0085–0089

## Bối cảnh

- Hai hệ campaign song song: `crm_campaign` + `crm_campaign_target` (`0005`) và `crm_hug_campaign` + `crm_hug_campaign_history` (`0024`), cộng sổ voucher `crm_hug_voucher` (`0025`). Hug chưa ai dùng (0 request `/hug*` từ 10/08, báo cáo triage).
- Quy công hiện tại (R11) tính mọi đơn sau `scheduled_at` là chuyển đổi; với khách mua lặp 7 ngày thì quy công thừa (research §7). Không có holdout trong campaign CRM; `wh_deadstock_target.is_holdout` đã có 20% tất định ở kho.
- Plan cũ được gộp vào đây: `260620-1408-crm-hug-voucher-a2-golive` (phần kỹ thuật), `260620-2357-hug-a2-pilot-holdout`.
- `crm_identity_link` là nhật ký quét tem Hug nhưng tên dễ nhầm với identity lõi (design §7.1).

## Yêu cầu

1. **Migration `0085_campaign_type_holdout`:** `crm_campaign` thêm `campaign_type` (mặc định `outreach`), `holdout_pct` (mặc định 0), `conversion_rule_json`; `crm_campaign_target` thêm `arm` (mặc định `treatment`), `assigned_at`, `first_success_contact_at`.
2. **Migration `0086_hug_campaign_into_campaign`:**
   - Bảng module `crm_hug_campaign_rule` (`campaign_id` PK = FK `crm_campaign`, `targeting`, `destination_type`, `destination_url`, `offer_ref`, `priority`, `schedule_start`, `schedule_end`, `quota_total`, `status`), giữ đúng cột như edge D1 để `campaign_push.py` không đổi biến đổi.
   - Backfill: mỗi dòng `crm_hug_campaign` thành một dòng `crm_campaign` (`campaign_type='hug'`, cùng `campaign_id`) + một dòng rule.
   - `crm_hug_campaign_history` giữ nguyên (lịch sử).
   - `crm_hug_campaign` cũ: đổi tên thành `crm_hug_campaign_legacy`, tạo VIEW tên `crm_hug_campaign` (join campaign + rule, cùng cột) cho người đọc chưa chuyển.
   - Down: drop view, đổi tên lại, xoá dòng campaign loại `hug` và bảng rule.
3. **Migration `0087_hug_scan_resolution_rename`:** `crm_identity_link` → `crm_hug_scan_resolution`, VIEW tên cũ chỉ đọc. Người ghi (`hug/identity_resolver_io.py`) chuyển sang tên mới; người đọc (`voucher_issuer.py`, `screen_hug_review_data.py`) chuyển sang tên mới.
4. **Holdout:** khi sinh target, `arm = holdout` nếu `hash(campaign_id || party_id) mod 10000 < holdout_pct * 100`; tất định (tạo lại cho cùng arm). Target `holdout` không sinh task, không vào worklist từ campaign, không được gửi offer.
5. **Quy công mới** (`conversion_rule_json`, mặc định `{"basis": "first_success_contact", "window_days": 30}`):
   - Treatment: đơn đầu tiên trong `wh_transaction` (`retail_order`, `status_norm` hợp lệ) sau tiếp xúc thành công đầu tiên (`contact_outcome='reached'` hoặc tương đương) trong cửa sổ.
   - Holdout: đơn đầu tiên sau `assigned_at` trong cùng cửa sổ.
   - Báo cáo: tỉ lệ chuyển đổi và doanh thu/target mỗi arm, **lift** = treatment − holdout, kèm số mẫu và cảnh báo khi mẫu < 100 mỗi arm.
   - Số theo quy tắc R11 cũ vẫn hiện cạnh số mới, gắn nhãn "cách tính cũ", cho tới khi user chọn bỏ (thay đổi số báo cáo là thay đổi có khai báo).
6. **Hug:** màn hình admin Hug và `campaign_push.py` đọc/ghi qua `crm_campaign` + `crm_hug_campaign_rule`; voucher issuer kiểm `arm` (holdout không nhận voucher). Không làm go-live A2 (mã HUG50 trên Sapo, in tem, nội dung landing): việc vận hành riêng (Q9).
7. **Agent:** `get_campaign_results` trả lift; `propose_bulk_operation` hỗ trợ "tạo target campaign từ segment" (chạy thử trả số mỗi arm).
8. **Export:** `crm_campaign_target` thêm `arm`, `first_success_contact_at` (thêm cột, tương thích); `stg_crm__campaign_target` thêm cột.
9. Tài liệu: schema reference; `crm/AGENTS.md` mục Hug (bảng `crm.db` đổi tên); `orchestration/packs/crm/README.md`.

## File

- Tạo: migration 0085–0087 (up/down); `crm/src/application/campaign_attribution.py`; test (`test_campaign_holdout.py`, `test_campaign_attribution.py`, `test_hug_campaign_migration.py`).
- Sửa: `crm/src/application/campaign_service.py`, `crm/src/adapters/outbound/sqlite/campaign_repository.py` (phần campaign), `hug_campaign_repository_adapter.py`, `crm/src/hug/campaign_repository.py`, `campaign_push.py`, `voucher_issuer.py`, `identity_resolver_io.py`, `screen_hug_review_data.py`, screen campaign/Hug liên quan, `adapters/inbound/http/campaign_handler.py` (`/roi`, `/scan-conversions`), query/MCP campaign, `crm_writeback_assets.py`, `transformation/models/packs/crm/staging/stg_crm__campaign_target.sql`.

## Các bước

1. Worktree `feat/crm-campaign-holdout`.
2. Migration + backfill Hug trên bản sao; so view `crm_hug_campaign` với bảng cũ (giống hệt).
3. Holdout + quy công + test với dữ liệu giả có đơn lặp 7 ngày (chứng minh không quy công thừa).
4. Chuyển Hug sang bảng mới; test Hug hiện có xanh (`test_hug_campaign_*`, `test_hug_voucher_*`).
5. Export + staging; gate S (cột mới).
6. Deploy (backup trước), giờ user duyệt.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Arm tất định; tỉ lệ holdout trong ±2% với 10.000 party giả |
| Unit | Quy công: khách mua lặp không tiếp xúc thành công thì không tính; đơn ngoài cửa sổ không tính; holdout đo từ `assigned_at` |
| Unit | View `crm_hug_campaign` trả cùng cột, cùng dòng như bảng cũ; push D1 sinh cùng payload trước/sau |
| Unit | Holdout không nhận voucher, không sinh task |

## Kiểm "CRM như cũ"

- `parity_snapshot diff`: campaign hiện có (chưa đặt `holdout_pct`) có mọi target `arm=treatment`, cùng số target; worklist giống hệt; ROI hiện cả số cũ (giống trước) và số mới (khai báo).
- `crm_export_parity.py`: 10 bảng giống hệt; `crm_campaign_target` thêm cột, các cột cũ giống hệt.
- Sau deploy: màn hình campaign và Hug admin mở được; payload push D1 (chạy chế độ thử, không đẩy) giống trước.

## Đụng prod và duyệt

Có: migration dữ liệu (backup bắt buộc), export đổi cột. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Đổi bảng Hug làm sai payload đẩy lên edge D1 | Thấp × Trung bình | So payload trước/sau; Hug chưa có người dùng |
| User hiểu nhầm số quy công mới thấp hơn cũ là CRM kém đi | Trung bình × Trung bình | Hiện song song có nhãn; giải thích trong tài liệu báo cáo |
| Mẫu holdout nhỏ, lift nhiễu | Cao × Thấp | Cảnh báo mẫu nhỏ; khoảng tin cậy để sau |

## Rollback

`docker stop crm`, `git revert`, `migration_down.py` 0087 → 0085 (đổi tên lại bảng Hug, xoá dòng campaign loại `hug`), `docker start crm`; export theo runbook data_platform.
