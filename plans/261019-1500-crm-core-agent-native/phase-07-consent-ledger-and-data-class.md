# Phase 7: sổ cái consent và phân loại dữ liệu cho ghi chú, trường tuỳ biến, tương tác

**Effort:** 3.5d · **Phụ thuộc:** phase 6 (contact point); câu trả lời Q6, Q7 · **Đụng prod:** có (CRM; data_platform cho export consent) · **Cần user duyệt giờ:** có · **Migration:** 0070–0074

## Bối cảnh

- Consent hiện là `consent_enum` ở cấp party (`0026_consent_contact_enum.up.sql`), ghi qua `ProfileService` (`profile_service.py:68-112`), đọc ở campaign (`campaign_repository.py:203`).
- "Không liên hệ" ở worklist suy ra từ hoạt động gần nhất có `outcome_reason='do_not_contact'` (`activity_repository.py:71-78,200-201`; `worklist_query_service.py:54-65`): một hoạt động sau đó làm mất lệnh chặn (design H4).
- Luật 91/2025 và Nghị định 356/2025 yêu cầu chứng minh consent (khi nào, cách nào, mục đích gì); dữ liệu sức khoẻ cần consent riêng.
- Phase 1 đã có `data_class` ở loại tag; phase này mở rộng cho ghi chú, trường tuỳ biến, tương tác (design §6.1).

## Yêu cầu

1. **Migration `0070_consent_purpose`:** `crm_consent_purpose` (design §6.2), seed `service_care`, `marketing`, `sensitive_profile`, `third_party_sharing`; Fine Japan: `default_when_unknown='allow'` cho `service_care` và `marketing` (giữ hành vi hiện tại; Q7 có thể đổi `marketing` bằng cấu hình).
2. **Migration `0071_consent_event`:** `crm_consent_event` (design §6.2), FK `party_id`, `contact_point_id`, `purpose_code`; index (`party_id`, `purpose_code`, `channel`, `effective_at`); trigger chặn UPDATE/DELETE.
3. **Migration `0072_consent_current_view`:** view `crm_consent_current` dùng `ROW_NUMBER()`.
4. **Migration `0073_backfill_consent_events`:** theo bảng ánh xạ design §6.2 (`denied`, `allowed`, `do_not_contact`). Sự kiện từ `do_not_contact` được tạo nhưng **chưa thay bộ lọc worklist** (yêu cầu 7).
5. **Migration `0074_data_class_columns`:** `crm_custom_field_def.data_class`, `crm_note.data_class`, `crm_activity_log.data_class` (mặc định `basic`); bảng nhỏ `crm_note_type` (`note_type`, `label_vi`, `default_data_class`) seed từ các giá trị `note_type` hiện có (`general|preference|contact_pref|warning|outcome|internal`) + loại `health` (`sensitive`).
6. **`ConsentService`** (`append`, `current(party_id)`, `history(party_id)`) và **`ConsentPolicy.can_contact(party_id, channel, purpose)`** (design §6.2). Ghi consent bắt buộc `method`, `evidence_type`, `captured_by`; `evidence_type='none_legacy'` chỉ cho migration.
7. **Người tiêu thụ, giữ hành vi:**
   - Modal liên hệ (`screen_modal_contact.py`) ghi qua `ConsentService` **và** cập nhật `consent_enum` như cũ (tương thích tới phase 11); bắt người dùng chọn cách thu thập (gọi điện, form, Zalo, tại cửa hàng) và mục đích.
   - Campaign (`fetch_consent_map`) đọc `ConsentPolicy` với `purpose='marketing'`; do backfill phản chiếu `consent_enum`, kết quả bằng hôm nay (kiểm bằng parity).
   - Worklist giữ bộ lọc `do_not_contact` cũ. **Chỉ khi user chọn ngữ nghĩa sổ cái ở Q6**, bật cờ `CRM_DNC_SOURCE=ledger` để worklist đọc `ConsentPolicy` (`service_care`). Trước khi bật, phase in số party sẽ thay đổi trạng thái (số đếm) để user duyệt.
   - Kết quả cuộc gọi có lý do `do_not_contact` từ nay cũng ghi một sự kiện consent `withdrawn` (method `outcome_do_not_contact`, bằng chứng là `activity_id`).
8. **Agent:** executor của `propose_consent_change` (phase 4) chuyển sang `ConsentService.append`; `get_party_360` trả consent hiện hành (không trả bằng chứng chi tiết).
9. **Phân loại:** policy ẩn ghi chú, tương tác, trường tuỳ biến `sensitive` với người không có `data.sensitive.read` và với mọi agent; form ghi chú/tương tác có lựa chọn "chứa thông tin sức khoẻ" (đặt `data_class='sensitive'`). Loại ghi chú `health` bị chặn tạo khi loại tag sức khoẻ đang bị hạn chế (giữ nhất quán với phase 1).
10. **Export** (`crm_writeback_assets.py`): thêm `crm_consent_current` (design §4.4); lọc `crm_note`, `crm_activity_log`, `crm_customer_profile.custom` (trường `sensitive`) khỏi export. Model staging `stg_crm__consent_current` trong pack `crm` dbt (mới, public).
11. Tài liệu: schema reference; `crm/docs/ui-spec` cho modal liên hệ; `orchestration/packs/crm/README.md` (export mới).

## File

- Tạo: migration 0070–0074 (up/down); `crm/src/application/consent_service.py`, `crm/src/domain/consent_policy.py`, entity và port consent, adapter SQLite; `transformation/models/packs/crm/staging/stg_crm__consent_current.sql` + yml; test.
- Sửa: `profile_service.py`, `profile_repository.py`, `campaign_repository.py` (đoạn consent), `campaign_service.py`, `worklist_query_service.py` (thêm nhánh cờ), `activity_side_effects.py` (ghi sự kiện khi `do_not_contact`), `note_service.py`, `custom_field_service.py`, `screen_modal_contact.py`, `screen_modal_shared.py`, `crm_writeback_assets.py`, `transformation/models/packs/crm/staging/_sources.yml`, `scripts/checks/public_models.yaml`.

## Các bước

1. Worktree `feat/crm-consent-ledger`.
2. Migration + backfill trên bản sao; đếm sự kiện theo `method`.
3. Service, policy, người tiêu thụ; test.
4. Export + model staging; gate `S --allow-new`.
5. Deploy CRM (backup trước) và data_platform, giờ user duyệt.
6. Báo user số party bị ảnh hưởng nếu bật `CRM_DNC_SOURCE=ledger`; chờ Q6.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Sổ cái: UPDATE/DELETE bị trigger chặn; view current lấy đúng dòng mới nhất; độ ưu tiên contact point > party+kênh > party+any > mặc định |
| Unit | Backfill: `denied` → withdrawn mọi mục đích; `allowed` → granted `service_care`; NULL → không có |
| Unit | Campaign đọc policy cho cùng tập khách bị loại như `consent_enum` cũ |
| Unit | Ghi consent thiếu `method`/`evidence_type` → lỗi; agent đề xuất thiếu bằng chứng → từ chối |
| Unit | Ghi chú `sensitive` không hiện với staff, không ra export, không ra MCP |
| Tích hợp | Worklist với `CRM_DNC_SOURCE=activity` (mặc định) cho cùng kết quả như cũ |

## Kiểm "CRM như cũ"

- `parity_snapshot diff`: worklist, campaign target, tìm kiếm giống hệt; chỉ khác số dòng bảng mới và thêm mục "consent hiện hành" trong hash 360 (khai báo trước).
- `crm_export_parity.py`: 11 bảng cũ giống hệt (không có ghi chú/tương tác nhạy cảm nào trước phase này vì cột mới mặc định `basic`); thêm 1 bảng mới.
- Sau deploy: một người dùng ghi consent qua modal liên hệ; thấy sự kiện có `method`, `captured_by`; worklist không đổi số mục.

## Đụng prod và duyệt

Có: migration dữ liệu (backup bắt buộc), export mới. Cần user duyệt giờ; bật `CRM_DNC_SOURCE=ledger` là quyết định riêng của user (Q6).

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Người dùng thấy modal liên hệ phức tạp hơn | Trung bình × Thấp | Mặc định điền sẵn kênh đang gọi và mục đích `service_care` |
| Hiểu sai luật về mặc định khi chưa có consent | Trung bình × Cao | Để cấu hình, giữ hành vi hôm nay; quyết định là của user sau ý kiến pháp chế (Q7) |
| Hai nguồn consent (cũ và sổ cái) lệch nhau | Thấp × Trung bình | Một service ghi cả hai trong cùng transaction tới phase 11; parity |

## Rollback

`docker stop crm`, `git revert`, `migration_down.py` 0074 → 0070 (sổ cái mất; `consent_enum` vẫn đầy đủ nhờ ghi song song), `docker start crm`; export theo runbook data_platform. Nếu đã bật `CRM_DNC_SOURCE=ledger` thì đặt lại `activity` trước.
