# Phase 8: vai trò, quan hệ, Person/Organization, khách sỉ ẩn

**Effort:** 4d · **Phụ thuộc:** phase 6; phase 4 (đề xuất); phase 5 (`customer_type`, `suspected_wholesale` trong `wh_customer_summary`) · **Đụng prod:** có (CRM; data_platform cho export vai trò) · **Cần user duyệt giờ:** có · **Migration:** 0075–0079

## Bối cảnh

- `crm_party.party_type` có `person`/`org` nhưng không có vai trò, không có quan hệ giữa party. `owner_user_id`, `lifecycle_stage`, `acquisition_source`, `birthday`, `gender` nằm ở `crm_customer_profile` (`0003`, `0016`, `0026`).
- Khách sỉ ẩn: research ghi nhận khoảng 15 tài khoản B2B/xuất khẩu lọt vào tệp bán lẻ; kho đã có `customer_type` trong `mart_customer_tier` và Hug đã loại theo cột này (`crm/src/hug/customer_push.py:151`).
- Người nhận quà, người mua hộ chưa được mô hình hoá.
- Thiết kế: design §3.3 (Party, PartyRole, PartyRelationship), §3.6 (mảng B2B).

## Yêu cầu

1. **Migration `0075_role_relationship_types`:** `crm_role_type`, `crm_relationship_type` (registry; có `module_id`, `is_enabled`). Seed lõi: vai trò `customer`, `prospect`, `contact`; quan hệ `contact_of`, `buys_for`, `gift_recipient_of`, `household_member_of`, `referred_by`. Module `b2b_lite` (seed ở đây, manifest ở phase 9): vai trò `wholesale_customer`, `reseller`; quan hệ `reseller_of`.
2. **Migration `0076_party_role`:** `crm_party_role` (design §3.3); backfill: mỗi party chưa merge có một vai trò `customer` `active`, chép `owner_user_id`, `lifecycle_stage`, `acquisition_source` từ `crm_customer_profile`.
3. **Migration `0077_person_organization`:** `crm_person`, `crm_organization`; backfill `crm_person` cho party `person` (chép `birthday`→`birth_date`, `gender`); `crm_organization` cho party `org` (nếu có).
4. **Migration `0078_party_relationship`:** `crm_party_relationship` (design §3.3).
5. **Ghi song song:** `ProfileService` cập nhật `owner_user_id`/`lifecycle_stage`/`acquisition_source` thì cập nhật cả vai trò `customer`; `birthday`/`gender` thì cả `crm_person`. Đọc vẫn từ hồ sơ cũ cho tới cờ `CRM_READ_PARTY_ROLE=new` (parity 0 khác biệt 3 ngày).
6. **Service:** `PartyRoleService` (gán, kết thúc vai trò), `PartyRelationshipService` (đề xuất, xác nhận, kết thúc; chặn tự quan hệ; kiểm loại party hai đầu theo registry).
7. **Khách sỉ ẩn (B2B tối thiểu):**
   - C360 hiện badge "Nghi khách sỉ" khi `wh_customer_summary.customer_type` hoặc `suspected_wholesale` báo vậy, kèm lý do từ kho (chỉ hiển thị, không tự đổi gì).
   - Lệnh `party.confirm_wholesale`: thêm vai trò `wholesale_customer`; tuỳ chọn tạo party `org` mới (tên công ty, mã số thuế) và quan hệ `contact_of` từ người hiện tại tới tổ chức. Người có quyền làm trực tiếp; agent dùng tool `propose_party_relationship` (thêm ở phase này, design §5.9 số 20).
   - Worklist và campaign loại party có vai trò `wholesale_customer` đang hiệu lực khỏi tín hiệu bán lẻ (cấu hình theo loại tín hiệu, mặc định loại tất cả tín hiệu của `mart_customer_action_queue` và `mart_customer_sku_action_queue`). Lúc deploy chưa có vai trò nào như vậy nên danh sách không đổi.
8. **Người nhận quà, mua hộ:** tạo quan hệ thủ công hoặc qua đề xuất của agent; quan hệ `gift_recipient_of` **không** tự đưa người nhận vào segment/campaign (người nhận phải có consent của chính họ).
9. **Export:** `crm_party_role` (design §4.4) để kho loại khách sỉ đã xác nhận khỏi tệp bán lẻ; model staging `stg_crm__party_role` (public). Kho dùng nó thế nào là việc của plan kho, không làm ở đây.
10. **API/MCP:** `get_party_360` trả vai trò và quan hệ; REST v1 `GET /api/v1/parties/{id}/relationships`, `POST /api/v1/parties/{id}/roles` (người), đề xuất qua `/api/v1/proposals`.
11. Tài liệu: schema reference; ui-spec cho badge và form xác nhận khách sỉ.

## File

- Tạo: migration 0075–0078 (up/down); `crm/src/application/party_role_service.py`, `party_relationship_service.py`; entity, port, adapter; screen/fragment xác nhận khách sỉ; `transformation/models/packs/crm/staging/stg_crm__party_role.sql` + yml; test.
- Sửa: `profile_service.py`, `profile_repository.py`, `worklist_query_service.py` hoặc `worklist_filters.py` (bộ lọc vai trò), `campaign_service.py` (loại khi tạo target), `screen_customer_360*.py`, query `get_party_360`, MCP tool, `crm_writeback_assets.py`, `_sources.yml`, `public_models.yaml`.

## Các bước

1. Worktree `feat/crm-party-roles`.
2. Migration + backfill trên bản sao; kiểm mỗi party chưa merge có đúng một vai trò `customer`.
3. Service + ghi song song + test.
4. Khách sỉ: badge, lệnh, bộ lọc, đề xuất agent.
5. Export + staging; gate `S --allow-new`.
6. Deploy (backup trước), giờ user duyệt; sau 3 ngày parity sạch, đổi cờ đọc.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Backfill vai trò và person đúng số dòng; chạy lại không nhân đôi |
| Unit | Cập nhật hồ sơ cập nhật cả vai trò và person; đọc `old`/`new` cho cùng kết quả |
| Unit | Xác nhận khách sỉ: vai trò thêm, tổ chức và quan hệ tạo đúng; worklist loại party đó; undo (kết thúc vai trò) trả lại |
| Unit | Quan hệ: chặn tự quan hệ, sai loại party hai đầu; `gift_recipient_of` không thêm người nhận vào segment |
| Unit | Agent chỉ đề xuất được, không gán vai trò trực tiếp |

## Kiểm "CRM như cũ"

- `parity_snapshot diff`: worklist, campaign, segment, tìm kiếm giống hệt (chưa có vai trò sỉ nào); hash 360 khác chỉ ở phần "vai trò/quan hệ" và badge (khai báo trước, chỉ party có `customer_type` sỉ).
- `crm_export_parity.py`: 11 bảng cũ giống hệt; thêm `crm_party_role`.
- Sau deploy: người dùng mở C360 một khách sỉ nghi vấn (do kho đánh dấu), thấy badge; không có thay đổi nào khác.

## Đụng prod và duyệt

Có: migration dữ liệu (backup bắt buộc), export mới. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Badge dựa trên phân loại kho sai | Trung bình × Thấp | Chỉ hiển thị; mọi thay đổi cần người xác nhận |
| Loại khách sỉ khỏi worklist làm mất cơ hội bán sỉ | Thấp × Trung bình | Bộ lọc cấu hình theo loại tín hiệu; chỉ áp cho khách đã xác nhận |
| Lệch hồ sơ cũ và vai trò mới | Thấp × Trung bình | Ghi song song trong một transaction; parity |

## Rollback

Cờ đọc về `old`; `docker stop crm`, `git revert`, `migration_down.py` 0078 → 0075, `docker start crm`; export theo runbook data_platform. Hồ sơ cũ vẫn đầy đủ nên không mất dữ liệu; các xác nhận khách sỉ đã làm sẽ mất (báo user danh sách số đếm trước khi rollback).
