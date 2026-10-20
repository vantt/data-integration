# Phase 9: Engagement, cơ chế module và module bán lẻ

**Effort:** 3.5d · **Phụ thuộc:** phase 8 · **Đụng prod:** có (CRM) · **Cần user duyệt giờ:** có · **Migration:** 0080–0084

## Bối cảnh

- Không có khái niệm chung cho đơn hàng, hợp đồng, lịch hẹn, gói. Tương tác chỉ có `related_order_code` (`0004`), task và ghi chú không tham chiếu được đơn.
- Đơn bán lẻ là sự thật của kho (`wh_order_hdr`, từ phase 5 là `wh_transaction`); CRM không được giữ bản sao (quyết định số 3).
- Mã riêng của Hug (`crm/src/hug/`) và các loại tín hiệu bán lẻ đang nằm lẫn trong lõi; chưa có cách bật/tắt theo tenant.
- Thiết kế: design §3.4 (registry, manifest), §3.5 (Engagement), §3.6 (bốn mảng).

## Yêu cầu

1. **Cơ chế module** `crm/src/modules/`:
   - `manifest.py` mỗi module khai báo các mục ở design §3.4 bằng dataclass.
   - `crm/src/modules/__init__.py`: nạp module theo `CRM_MODULES` (Fine Japan: `retail,b2b_lite,hug`), kiểm phụ thuộc giữa module, đồng bộ registry vào DB lúc khởi động bằng upsert (idempotent), đặt `is_enabled=0` cho loại của module tắt.
   - Module `retail` (loại engagement `retail_order` với `system_of_record='warehouse'`, ánh xạ tín hiệu → task kind hiện có trong `crm/src/application/task_kind.py`, bảng cache `wh_retail_deadstock_target`), `b2b_lite` (vai trò và quan hệ đã seed ở phase 8), `hug` (khai báo bảng `crm_hug_*`, quyền, không dời code).
2. **Migration `0080_engagement_type`:** `crm_engagement_type` (design §3.5).
3. **Migration `0081_engagement`:** `crm_engagement`, `crm_engagement_party`.
4. **Migration `0082_engagement_ref`:** cột `engagement_ref` ở `crm_activity_log`, `crm_task`, `crm_note`; backfill `crm_activity_log.engagement_ref = 'wh:' || transaction_id` khi `related_order_code` tra được trong `wh_transaction.source_ref` (tra trong migration không được vì không có khoá ngoại qua `cache.db`: làm bằng job backfill trong process lúc khởi động, idempotent, giới hạn số dòng mỗi lần). Giữ `related_order_code`.
5. **`EngagementService`:** tạo/cập nhật engagement `crm` theo trạng thái hợp lệ của loại (từ `statuses_json`); `list_for_party(party_id)` trả **hợp** của `crm_engagement` và `wh_transaction` (read model, design §3.5); kiểm `engagement_ref` hợp lệ khi gắn vào tương tác, task, ghi chú.
6. **Giao diện:** khi ghi tương tác hoặc tạo task từ khung đơn hàng ở C360, gắn `engagement_ref` (thay cho chỉ `related_order_code`). Không đổi bố cục màn hình.
7. **API/hàm agent:** `GET /api/v1/parties/{id}/engagements` (hàm `parties_engagements`, `x-agent-function`); `parties_timeline` trả engagement; `interactions_log` và `tasks_create` nhận `engagement_ref` tuỳ chọn. Route của module tắt không có trong OpenAPI, nên hàm của nó không hiện trong `search_api`.
8. **Module giả trong test** `appointment` (chỉ trong `crm/src/tests/fixtures/modules/`): khai báo loại `appointment`, vai trò `client`, bảng chi tiết `crm_appt_appointment` (tạo trong test), chứng minh tạo, đọc, đổi trạng thái, gắn tương tác qua API chung mà **không sửa file nào của lõi**.
9. Tài liệu: `crm/docs/modules.md` (mới): cách viết một module (manifest, migration, bảng cache, quyền, route REST v1 sinh ra hàm SDK), ví dụ bốn mảng (trỏ design §3.6); `crm/AGENTS.md` mục module.

## File

- Tạo: `crm/src/modules/__init__.py`, `crm/src/modules/{retail,b2b_lite,hug}/manifest.py`; migration 0080–0082 (up/down); `crm/src/application/engagement_service.py`; entity, port, adapter; `crm/docs/modules.md`; test (`test_module_loader.py`, `test_engagement_service.py`, `test_fake_appointment_module.py`).
- Sửa: `crm/src/composition.py` (nạp module), `activity_service.py`, `task_service.py`, `note_service.py` (nhận `engagement_ref`), screen C360 phần đơn hàng, query timeline, MCP tool, `crm/AGENTS.md`.

## Các bước

1. Worktree `feat/crm-engagement-modules`.
2. Bộ nạp module + manifest ba module + test bật/tắt.
3. Migration + service + backfill `engagement_ref` + test.
4. Module giả `appointment` trong test.
5. API/MCP; parity; deploy giờ user duyệt.

## Test

| Mức | Nội dung |
|---|---|
| Unit | Nạp module: thiếu phụ thuộc → lỗi rõ lúc khởi động; tắt `b2b_lite` → loại của nó `is_enabled=0`, dữ liệu cũ còn |
| Unit | Engagement: trạng thái không hợp lệ bị từ chối; `list_for_party` trả cả đơn từ cache và engagement của CRM, sắp theo thời gian |
| Unit | Backfill `engagement_ref` idempotent; dòng không tra được giữ NULL |
| Tích hợp | Module giả `appointment` chạy trọn vòng qua REST v1 và qua `execute` của code mode (hàm agent sinh từ route của module có `x-agent-function`) |

## Kiểm "CRM như cũ"

- `parity_snapshot diff`: chỉ khác bảng mới và cột `engagement_ref` (khai báo); worklist, 360, task, tìm kiếm giống hệt.
- `crm_export_parity.py`: 11 bảng giống hệt (cột mới chưa xuất ở phase này; nếu export dùng `SELECT *` ở bảng nào thì phải giữ danh sách cột cũ, kiểm trong phase 0).
- Sau deploy: C360 hiển thị đơn như cũ; ghi tương tác từ khung đơn hàng có `engagement_ref`.

## Đụng prod và duyệt

Có: migration chỉ thêm, khởi động lại CRM. Cần user duyệt giờ.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Thiết kế module quá trừu tượng so với nhu cầu thật | Trung bình × Trung bình | Chỉ khai báo những gì ba module thật và module giả cần; không thêm điểm mở rộng không có người dùng |
| Backfill lúc khởi động làm chậm | Thấp × Thấp | Giới hạn số dòng mỗi lần, chạy nền sau khi server sẵn sàng |

## Rollback

`docker stop crm`, `git revert`, `migration_down.py` 0082 → 0080, `docker start crm`. `related_order_code` vẫn còn nên không mất liên kết đơn.
