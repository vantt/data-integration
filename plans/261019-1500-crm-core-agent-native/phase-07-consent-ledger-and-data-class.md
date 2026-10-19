# Phase 7: sổ cái consent và phân loại dữ liệu cho ghi chú, trường tuỳ biến, tương tác

**Effort:** 4d · **Phụ thuộc:** phase 6 (contact point), phase 1 (cờ đồng ý riêng tạm); Q6 đã chốt, Q7 còn mở · **Đụng prod:** có (CRM; data_platform cho export consent) · **Cần user duyệt giờ:** có · **Migration:** 0070–0074

## Bối cảnh

- Consent hiện là `consent_enum` ở cấp party (`0026_consent_contact_enum.up.sql`), ghi qua `ProfileService` (`profile_service.py:68-112`), đọc ở campaign (`campaign_repository.py:203`).
- "Không liên hệ" ở worklist suy ra từ hoạt động gần nhất có `outcome_reason='do_not_contact'` (`activity_repository.py:71-78,200-201`; `worklist_query_service.py:54-65`): một hoạt động sau đó làm mất lệnh chặn (design H4).
- Luật 91/2025 và Nghị định 356/2025 yêu cầu chứng minh consent (khi nào, cách nào, mục đích gì); dữ liệu sức khoẻ cần consent riêng.
- Phase 1 đã có `data_class` ở loại tag và **bản tạm** của phương án C + B cho tag sức khoẻ: cờ đồng ý riêng `crm_sensitive_consent_flag` và trigger kiểm cờ (design §6.2). Phase này chuyển cờ tạm sang sổ cái và mở rộng phân loại cho ghi chú, trường tuỳ biến, tương tác (design §6.1).
- User đã chốt 19/10 (Q6): lệnh rút lại "không liên hệ" có hiệu lực tới khi khách đồng ý lại; bật sau khi user xem số khách bị ảnh hưởng.

## Yêu cầu

1. **Migration `0070_consent_purpose`:** `crm_consent_purpose` (design §6.2), seed `service_care`, `marketing`, `sensitive_profile` (`is_sensitive=1`, `requires_evidence=1`, `default_when_unknown='deny'`), `third_party_sharing`; Fine Japan: `default_when_unknown='allow'` cho `service_care` và `marketing` (giữ hành vi hiện tại; Q7 có thể đổi `marketing` bằng cấu hình).
2. **Migration `0071_consent_event`:** `crm_consent_event` (design §6.2), FK `party_id`, `contact_point_id`, `purpose_code`; index (`party_id`, `purpose_code`, `channel`, `effective_at`); trigger chặn UPDATE/DELETE.
3. **Migration `0072_consent_current_view`:** view `crm_consent_current` dùng `ROW_NUMBER()`.
4. **Migration `0073_backfill_consent_events`:** theo bảng ánh xạ design §6.3 (`denied`, `allowed`, cờ đồng ý riêng của phase 1, `do_not_contact`). Mỗi dòng `crm_sensitive_consent_flag` thành một sự kiện `sensitive_profile` giữ nguyên `method` gốc (trong `note`), bằng chứng, `captured_by`, thời điểm; nếu cờ từng đổi trạng thái thì dựng lại chuỗi sự kiện từ `crm_audit_event` (nhật ký tạm đã chép sang ở phase 2). Sự kiện từ `do_not_contact` được tạo nhưng **chưa thay bộ lọc worklist** (yêu cầu 8).
5. **Migration `0074_data_class_and_sensitive_trigger`:** `crm_custom_field_def.data_class`, `crm_note.data_class`, `crm_activity_log.data_class` (mặc định `basic`); bảng nhỏ `crm_note_type` (`note_type`, `label_vi`, `default_data_class`) seed từ các giá trị `note_type` hiện có (`general|preference|contact_pref|warning|outcome|internal`) + loại `health` (`sensitive`).
6. **`ConsentService`** (`append`, `current(party_id)`, `history(party_id)`) và **`ConsentPolicy.can_contact(party_id, channel, purpose)`** (design §6.3).
7. **Chuyển cờ tạm sang sổ cái (tag sức khoẻ, design §6.2):**
   - Trong migration `0074_data_class_and_sensitive_trigger`: thay trigger của `0049_sensitive_tag_guard` bằng trigger kiểm `crm_consent_current` (`purpose_code='sensitive_profile'`, `decision='granted'`, chưa hết hạn). Down: dựng lại trigger kiểm cờ.
   - `can_write_sensitive` và `can_view_sensitive` (đã ở `policy.py` từ phase 2) đọc trạng thái đồng ý từ `ConsentPolicy`; quy tắc người xem giữ nguyên (người phụ trách, manager, admin; khách chưa có người phụ trách: người ghi nhận đồng ý đang hiệu lực, nay đọc `captured_by` của sự kiện `granted` hiện hành (Q12); khách đã rút: chỉ admin).
   - `SensitiveConsentService` thành lớp mỏng gọi `ConsentService.append` với `purpose='sensitive_profile'`; modal "Ghi nhận khách đồng ý cho lưu thông tin sức khoẻ" ghi vào sổ cái (giao diện không đổi).
   - Ghi song song vào `crm_sensitive_consent_flag` tới phase 11 (để rollback được); parity cờ ↔ sổ cái trong `parity_snapshot`. Ghi consent bắt buộc `method`, `evidence_type`, `captured_by`; `evidence_type='none_legacy'` chỉ cho migration.
8. **Người tiêu thụ, giữ hành vi cho tới khi user duyệt bật:**
   - Modal liên hệ (`screen_modal_contact.py`) ghi qua `ConsentService` **và** cập nhật `consent_enum` như cũ (tương thích tới phase 11); bắt người dùng chọn cách thu thập (gọi điện, form, Zalo, tại cửa hàng) và mục đích.
   - Campaign (`fetch_consent_map`) đọc `ConsentPolicy` với `purpose='marketing'`; do backfill phản chiếu `consent_enum`, kết quả bằng hôm nay (kiểm bằng parity).
   - Worklist giữ bộ lọc `do_not_contact` cũ khi deploy. User **đã chốt** ngữ nghĩa sổ cái (Q6): sau deploy, chạy `crm/ops/dnc_impact_report.py` (mới, chỉ in số đếm: số party đang được gọi lại dù từng có lý do "không liên hệ" và sẽ bị chặn; số party ngược lại nếu có; phân theo nhân viên phụ trách), gửi user. **User duyệt số đó rồi mới bật** cờ `CRM_DNC_SOURCE=ledger` (worklist đọc `ConsentPolicy` với `service_care`), giờ user duyệt.
   - Kết quả cuộc gọi có lý do `do_not_contact` từ nay cũng ghi một sự kiện consent `withdrawn` (method `outcome_do_not_contact`, bằng chứng là `activity_id`).
9. **Agent:** executor của đề xuất `consent_change` (hàm SDK `crm.proposals.consentChange`, phase 4) chuyển sang `ConsentService.append`; `crm.parties.get360` trả consent hiện hành (không trả bằng chứng chi tiết).
10. **Phân loại:** cùng quy tắc với tag sức khoẻ (design §6.1–6.2): ghi chú, tương tác, trường tuỳ biến `sensitive` chỉ hiện với người phụ trách, manager, admin (`can_view_sensitive`), không bao giờ với agent; có audit gắn và xem; form ghi chú/tương tác có lựa chọn "chứa thông tin sức khoẻ" (đặt `data_class='sensitive'`), chỉ chọn được khi khách đã có đồng ý `sensitive_profile` (chưa có thì hiện nút ghi nhận đồng ý như ở picker tag). Loại ghi chú `health` theo cùng điều kiện.
11. **Export** (`crm_writeback_assets.py`): thêm `crm_consent_current` (design §4.4); lọc `crm_note`, `crm_activity_log`, `crm_customer_profile.custom` (trường `sensitive`) khỏi export. Model staging `stg_crm__consent_current` trong pack `crm` dbt (mới, public).
12. Tài liệu: schema reference; `crm/docs/ui-spec` cho modal liên hệ; `orchestration/packs/crm/README.md` (export mới).

## File

- Tạo: migration 0070–0074 (up/down); `crm/src/application/consent_service.py`, `crm/src/domain/consent_policy.py`, entity và port consent, adapter SQLite; `crm/ops/dnc_impact_report.py`; `transformation/models/packs/crm/staging/stg_crm__consent_current.sql` + yml; test.
- Sửa: `profile_service.py`, `profile_repository.py`, `campaign_repository.py` (đoạn consent), `campaign_service.py`, `worklist_query_service.py` (thêm nhánh cờ), `activity_side_effects.py` (ghi sự kiện khi `do_not_contact`), `note_service.py`, `custom_field_service.py`, `sensitive_consent_service.py` (phase 1), `tag_service.py` (đọc trạng thái đồng ý qua policy), `domain/policy.py`, template modal đồng ý riêng và form ghi chú/tương tác, `screen_modal_contact.py`, `screen_modal_shared.py`, `crm_writeback_assets.py`, `transformation/models/packs/crm/staging/_sources.yml`, `scripts/checks/public_models.yaml`.

## Các bước

1. Worktree `feat/crm-consent-ledger`.
2. Migration + backfill trên bản sao; đếm sự kiện theo `method`; kiểm mỗi cờ đồng ý riêng có đúng một sự kiện.
3. Service, policy, chuyển cờ tạm sang sổ cái, người tiêu thụ; test.
4. Export + model staging; gate `S --allow-new`.
5. Deploy CRM (backup trước) và data_platform, giờ user duyệt; cờ `CRM_DNC_SOURCE=activity`.
6. Chạy `dnc_impact_report.py` trên prod (chỉ số đếm), gửi user; user duyệt số và giờ, rồi bật `CRM_DNC_SOURCE=ledger` (`docker compose up -d crm` sau khi lưu log); kiểm khác biệt worklist đúng bằng báo cáo.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Sổ cái: UPDATE/DELETE bị trigger chặn; view current lấy đúng dòng mới nhất; độ ưu tiên contact point > party+kênh > party+any > mặc định |
| Unit | Backfill: `denied` → withdrawn mọi mục đích; `allowed` → granted `service_care`; NULL → không có |
| Unit | Campaign đọc policy cho cùng tập khách bị loại như `consent_enum` cũ |
| Unit | Ghi consent thiếu `method`/`evidence_type` → lỗi; agent đề xuất thiếu bằng chứng → từ chối |
| Unit | Ghi chú `sensitive` không hiện với staff không phụ trách, hiện với người phụ trách/manager/admin (có audit xem), không ra export, không ra MCP |
| Unit | Chuyển cờ: mỗi cờ phase 1 thành đúng một sự kiện `sensitive_profile` (giữ bằng chứng, người ghi); trigger mới chặn/cho qua giống trigger cũ trên cùng bộ trường hợp; ghi nhận đồng ý qua modal tạo sự kiện sổ cái và cập nhật cờ tạm |
| Unit | `dnc_impact_report.py` chỉ in số đếm (không tên, không SĐT) |
| Tích hợp | Worklist với `CRM_DNC_SOURCE=activity` (mặc định) cho cùng kết quả như cũ; với `ledger` khác đúng bằng số trong báo cáo ảnh hưởng |

## Kiểm "CRM như cũ"

- `parity_snapshot diff` (cờ `CRM_DNC_SOURCE=activity`): worklist, campaign target, tìm kiếm giống hệt; tập tag sức khoẻ mỗi người dùng thấy giống hệt trước (quy tắc xem không đổi, chỉ đổi nguồn trạng thái đồng ý); chỉ khác số dòng bảng mới và thêm mục "consent hiện hành" trong hash 360 (khai báo trước).
- Khi user duyệt bật `ledger`: khác biệt worklist phải đúng bằng số trong `dnc_impact_report.py` (khai báo trước, không có khác biệt nào khác).
- `crm_export_parity.py`: 11 bảng cũ giống hệt (không có ghi chú/tương tác nhạy cảm nào trước phase này vì cột mới mặc định `basic`); thêm 1 bảng mới.
- Sau deploy: một người dùng ghi consent qua modal liên hệ; thấy sự kiện có `method`, `captured_by`; worklist không đổi số mục.

## Đụng prod và duyệt

Có: migration dữ liệu (backup bắt buộc), export mới. Cần user duyệt giờ. Bật `CRM_DNC_SOURCE=ledger` là một lần đổi cấu hình riêng, sau khi user duyệt số khách bị ảnh hưởng, cũng cần duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Người dùng thấy modal liên hệ phức tạp hơn | Trung bình × Thấp | Mặc định điền sẵn kênh đang gọi và mục đích `service_care` |
| Hiểu sai luật về mặc định khi chưa có consent | Trung bình × Cao | Để cấu hình, giữ hành vi hôm nay; quyết định là của user sau ý kiến pháp chế (Q7) |
| Hai nguồn consent (cũ và sổ cái) lệch nhau | Thấp × Trung bình | Một service ghi cả hai trong cùng transaction tới phase 11; parity |

## Rollback

`docker stop crm`, `git revert`, `migration_down.py` 0074 → 0070 (sổ cái mất; `consent_enum` và cờ đồng ý riêng vẫn đầy đủ nhờ ghi song song; trigger kiểm cờ của phase 1 được dựng lại), `docker start crm`; export theo runbook data_platform. Nếu đã bật `CRM_DNC_SOURCE=ledger` thì đặt lại `activity` trước.
