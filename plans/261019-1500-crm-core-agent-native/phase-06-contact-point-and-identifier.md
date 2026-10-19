# Phase 6: tách identity thành ContactPoint và PartyIdentifier, mở rộng merge

**Effort:** 6d · **Phụ thuộc:** phase 5 (nguồn contact từ `wh_party_source_contact`), phase 4 (đề xuất identity) · **Đụng prod:** có (CRM, migration dữ liệu) · **Cần user duyệt giờ:** có (hai lần: deploy ghi song song, đổi cờ đọc) · **Migration:** 0060–0069

## Bối cảnh

- `crm_party_identity` trộn kênh liên hệ với khoá hệ khác, UNIQUE (`identity_type`, `identity_value`) (`0002...up.sql:27-38`); 19 file ngoài test tham chiếu (design §7.2); export dbt join nó để lấy `customer_id` (`crm_writeback_assets.py:44-60`).
- `crm_party_external_id` không ai ghi (`tag_acl_sync_service.py:9-12`, phase 0 xác nhận số dòng).
- Hug ghi `crm_party_identity` (nâng `contact_quality`) qua `hug/identity_resolver*.py`.
- Merge chỉ chuyển identity (`merge_service.py:52-115`).
- Thiết kế: design §3.3 (ContactPoint, PartyIdentifier), §7.2 (ví dụ), §8.1 (khuôn chuyển).

## Yêu cầu

1. **Bước A, refactor không đổi schema:** port `IdentityRepository` (`crm/src/domain/ports/identity_repository.py`) với các hàm mà 19 file đang cần (tìm party theo SĐT/email/mã ngoài, liệt kê identity của party, thêm/cập nhật/vô hiệu, nâng chất lượng, lấy `customer_id` Sapo cho nhiều party). Mọi SQL chạm `crm_party_identity` ngoài `adapters/outbound/sqlite/` chuyển vào adapter của port này. `crm_writeback_assets.py` chưa đổi (phase 11).
2. **Migration `0060_contact_point_identifier`:** bảng `crm_contact_point`, `crm_party_identifier` theo design §3.3, các index (gồm hai partial unique). Down: drop.
3. **Migration `0061_backfill_contact_point_identifier`:** chép từ `crm_party_identity`, **giữ nguyên id**, theo bảng ánh xạ (chốt ở phase 0 theo số đo):

   | `identity_type` | Đích | Ghi chú |
   |---|---|---|
   | `phone` | contact point `phone`, `is_preferred` theo cột cũ hoặc 1 nếu là dòng phone duy nhất | `quality` = `contact_quality`, `source_quality` = `source_contact_quality`, `label` = `display_label`, `status` = `contact_status` |
   | `phone_secondary` | contact point `phone`, `is_preferred=0` | |
   | `email` | contact point `email` | |
   | `zalo_uid` | contact point `zalo` | |
   | `psid` | contact point `messenger` | `source_ref` = page nếu biết |
   | `facebook` | contact point `social_other` | |
   | `sapo_customer` | identifier `sapo_v2`/`customer_id`, `confirmed`, `method='seed_sync'` | `source_system` theo cột (sau 0018 là `sapo_v2`) |
   | `customer_code` | identifier `sapo_v2`/`customer_code`, `confirmed` | |
   | loại khác do phase 0 tìm ra | quyết định ở phase 0 | |

   Idempotent (`ON CONFLICT DO NOTHING`). Down: xoá dòng có id trùng `crm_party_identity`.
4. **Ghi song song:** adapter `IdentityRepository` ghi bảng cũ và bảng mới trong cùng transaction (thêm, sửa, vô hiệu, nâng chất lượng, chuyển party khi merge). Sync party (`party_seed_service.py`) đọc nguồn từ `wh_party_source` + `wh_party_source_contact` khi cờ phase 5 là `v1`.
5. **Merge mở rộng:** snapshot chứa thêm `contact_point_id`, `identifier_id` đã chuyển; undo trả về đúng. Giữ nguyên hành vi với các bảng khác (task, ghi chú, tag không chuyển, như hôm nay).
6. **Tìm kiếm:** nguồn của `crm_party_search` (`crm/sync/search_index.py` và trigger liên quan) đọc qua port, cho cùng nội dung.
7. **Parity identity hằng ngày:** ở cuối `/admin/refresh` (giới hạn thời gian), so `crm_party_identity` với hai bảng mới theo id và giá trị; log số khác biệt; parity snapshot thêm mục này.
8. **Chuyển đọc** sau cờ `CRM_READ_IDENTITY=old|new` khi parity 0 khác biệt 3 ngày liền. Đọc `new` vẫn tiếp tục ghi song song (bảng cũ còn phục vụ export và Hug edge).
9. **Đề xuất identity** (phase 4) chuyển executor sang tạo identifier `proposed` → `confirmed` khi duyệt, hoặc contact point mới; giao diện tool không đổi.
10. **Hug:** `identity_resolver*.py` ghi qua port (nâng chất lượng trên contact point; zalo UID thành contact point `zalo`).
11. `crm_party_external_id`: không xoá ở phase này (phase 11).
12. Tài liệu: schema reference thêm hai bảng; `crm/AGENTS.md` quy tắc "không SQL chạm identity ngoài adapter của `IdentityRepository`".

## File

- Tạo: migration `0060_contact_point_identifier`, `0061_backfill_contact_point_identifier` (up/down); `crm/src/domain/ports/identity_repository.py`, `crm/src/domain/entities/contact_point.py`, `party_identifier.py`; `crm/src/adapters/outbound/sqlite/identity_repository.py`; test (`test_identity_repository_dual_write.py`, `test_identity_backfill.py`, `test_merge_undo_contact_points.py`).
- Sửa: 19 file ở design §7.2 trừ `crm_writeback_assets.py` và hai file chỉ có comment; `crm/src/application/merge_service.py`, `party_seed_service.py`, `party_service.py`; `crm/src/adapters/outbound/sqlite/dedup_repository*.py`, `party_repository*.py`; `crm/src/composition.py` (một instance port).

## Các bước

1. Worktree `feat/crm-contact-point-identifier`.
2. Bước A (refactor) + parity snapshot trên bản sao: **rỗng** (không đổi schema, không đổi hành vi). Có thể deploy riêng bước A nếu muốn chia nhỏ rủi ro (đề xuất: có, giờ user duyệt).
3. Migration + backfill trên bản sao; kiểm mọi dòng cũ có đúng một dòng mới.
4. Ghi song song + merge mở rộng + test.
5. Deploy (backup + verify trước), cờ `old`. Theo dõi parity 3 ngày.
6. Đổi cờ `new` (giờ user duyệt). Theo dõi 7 ngày trước khi phase 11 contract.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Backfill: mỗi `identity_type` vào đúng bảng; id giữ nguyên; chạy lại không nhân đôi |
| Unit | Ghi song song: mọi hàm ghi của port làm bảng cũ và mới khớp nhau; lỗi ở một bên thì rollback cả hai |
| Unit | Partial unique: thêm SĐT đã thuộc party khác bị từ chối như cũ; địa chỉ trùng được phép |
| Unit | Merge rồi undo: hash các bảng party, identity, contact point, identifier giống trước merge |
| Tích hợp | Mọi test hiện có chạy với `CRM_READ_IDENTITY=old` và `new` |
| Tích hợp | Hug: test resolver hiện có xanh; nâng chất lượng phản ánh ở contact point |

## Kiểm "CRM như cũ"

- Bước A: `parity_snapshot diff` rỗng.
- Sau migration, cờ `old`: chỉ khác số dòng hai bảng mới; `crm_export_parity.py` 11 bảng giống hệt.
- Cờ `new`: `parity_snapshot diff` giữa `old` và `new` rỗng (tìm theo SĐT và mã Sapo trên 100% khoá của bản sao cho cùng party).
- Sau deploy: tìm khách theo SĐT trên UI, mở C360, ghi hoạt động; `sync_parties` trong `/admin/refresh` không có lỗi mới; nightly export xanh.

## Đụng prod và duyệt

Có: migration dữ liệu (backup bắt buộc), đổi cờ. Cần user duyệt giờ cho mỗi deploy.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Một đường ghi bỏ sót không qua port, làm hai bên lệch | Trung bình × Trung bình | Bước A tách riêng; `grep` không còn SQL `crm_party_identity` ngoài adapter (test kiểm bằng quét mã nguồn); parity hằng ngày |
| Loại identity lạ không ánh xạ được | Thấp × Thấp | Phase 0 đã đếm; migration thất bại rõ ràng nếu gặp loại chưa khai báo (không bỏ qua im lặng) |
| Migration chậm làm container khởi động lâu | Thấp × Thấp | Số dòng nhỏ (cỡ chục nghìn); đo trên bản sao |

## Rollback

- Cờ: `CRM_READ_IDENTITY=old`.
- Code và bảng: `docker stop crm`; `git revert`; `migration_down.py` 0061 rồi 0060; `docker start crm`. Bảng cũ vẫn là nguồn đầy đủ nhờ ghi song song, nên không mất dữ liệu.
