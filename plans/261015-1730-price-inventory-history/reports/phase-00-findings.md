# Phase 0: kết quả kiểm chứng

> Đo ngày 15/10/2026, 18:00–18:25 ICT, trong container `data_platform` trên prod: DuckDB/pyarrow trong bộ nhớ đọc parquet, cộng một số GET chỉ đọc tới Sapo qua client có sẵn (`ingestion/src/sapo/client.py`). Không chạy job, không ghi vào `app_data`, không in secret hay cookie. File tạm trong `/tmp` của container đã xoá. `git status` của checkout prod không đổi.

## Tóm tắt

Không có phát hiện nào chặn phase 1. Có ba điểm làm phase 1 khác so với phase file:

1. **Bố cục file raw:** `layout` dlt dùng placeholder tĩnh (`ingestion/.dlt/config.toml:6-7`, `extra_placeholders = {ingest_method="batch_sync", year="_default", month="_default"}`). Các cột `year`/`month` trong envelope **không** quyết định thư mục; batch sản phẩm hiện nằm ở `product/ingest_method=batch_sync/year=_default/month=_default/`. Để có `ingest_method=daily_snapshot/year=<ICT>/month=<ICT>/`, runner mới tự dựng destination `dlt.destinations.filesystem(extra_placeholders=...)` theo `captured_at`. Pytest kiểm đường dẫn file với layout của prod.
2. **Check độ phủ:** không có cơ chế SLA nào đọc metadata asset. Một check nằm trong asset (`@asset(check_specs=...)`) làm **vỡ** `health_checks_asset_job`: job này chọn `AssetSelection.all_asset_checks()`, mà check gắn trong asset thì không chạy tách khỏi asset được. Đã thử trên Dagster 1.13.17 và nhận `DagsterInvalidDefinitionError: Failed to resolve asset job`. Một `@asset_check` riêng thì phải đăng ký ở `definitions.py` hoặc thêm export mới vào hợp đồng connector, cả hai nằm ngoài quyền sở hữu file của phase 1. Vì vậy chọn cách ít code nhất: check `row_count_within_trend` có sẵn với `trend_min_ratio: 0.98` cho asset mới (WARN khi một đêm chụp ít hơn 98% trung vị 7 ngày). Độ phủ so với tổng Sapo được ghi vào metadata asset và `ingestion_health`, và log `WARN` khi dưới 0,98.
3. **Payload gọn lưu bằng snappy (mặc định dlt), không phải zstd:** khoảng 440 KB/run, tức khoảng 160 MB/năm. Vẫn nằm trong khoảng 70–275 MB/năm user đã chấp nhận (Q2), nên không đổi codec.

## 1. Kích thước payload gọn so với đầy đủ

File `sapo_v2_raw/product/ingest_method=batch_sync/year=_default/month=_default/11026f1190.parquet` (lần tải đủ 13/06/2026): 560 sản phẩm, 757.189 byte trên đĩa (snappy, cùng các cột envelope). Cách đo: pyarrow ghi lại hai bảng `{entity_id, payload}` vào thư mục tạm, một bảng payload đầy đủ, một bảng payload gọn (`id`, `modified_on`, `variants[].{id, sku, variant_prices, inventories}`), rồi xoá thư mục.

| Payload | JSON (byte) | parquet zstd | parquet snappy |
|---|---|---|---|
| Đầy đủ | 6.361.784 | 239.355 | 799.949 |
| Gọn | 4.735.417 | 107.235 | 438.571 |

Gọn nhỏ hơn khoảng 2,2 lần (zstd) hoặc 1,8 lần (snappy). Phần lớn payload gọn là `variant_prices[].price_list` lồng trong từng giá. Phần này được giữ lại, vì phase 2 cần `code` và `is_cost` của bảng giá.

Cùng file: 684 variant, 9.745 dòng giá, 2.052 dòng tồn theo kho. Khoá trong `inventories`: `amount, available, bin_location, committed, incoming, location_id, mac, max_value, min_value, modified_on, on_hand, onway, variant_id, wait_to_pack`.

## 2. Chi phí quét đủ

- `GET products.json?page=1&limit=1` → `metadata.total = 560` (18:05 ICT). Với `page_size` 50 thì cần 12 trang, cộng một trang rỗng để kết thúc.
- `request_delay` của client là **2,0 giây** (`ingestion/.dlt/config.toml:12`; mặc định trong code là 0,5).
- **Chạy thử thật** code quét mới (`scan_catalogue`) trên Sapo lúc 18:2x ICT, chỉ GET, không qua dlt và không ghi gì: **33,6 giây**, 12 trang, 560/560 sản phẩm, không trùng, `coverage_ratio = 1.0`; 684 variant, 9.769 dòng giá, 2.052 dòng tồn. Thời lượng dưới ngưỡng 2 phút của phase 1, nên asset được đưa thẳng vào nightly.

## 3. API Sapo có lịch sử giá hay tồn không

Probe GET (`page=1&limit=1`) qua client có sẵn, 15/10 18:0x:

| Endpoint | Kết quả |
|---|---|
| `products.json` | 200, total 560 |
| `variants.json` | 200, total 684 (tồn và giá hiện tại, không có lịch sử) |
| `price_lists.json` | 200, total 22 |
| `stock_adjustments.json` | 200, total 0 |
| **`price_adjustments.json`** | **403 `missing permission`, `permission: read_price_adjustment`**. Endpoint có tồn tại, nhưng tài khoản tích hợp chưa được cấp quyền |
| `price_histories.json`, `variant_price_histories.json`, `inventory_histories.json`, `inventory_reports.json`, `stock_histories.json`, `inventories.json`, `inventory_adjustments.json` | 403 `unauthorized` (phản hồi chung cho route không có hoặc không được phép) |
| `variants/history.json` | 404 |

Tìm web không thấy tài liệu công khai của Sapo GO cho `price_adjustments`.

**Đề xuất (plan riêng, không chặn plan này):** nếu chủ cửa hàng cấp quyền `read_price_adjustment` cho tài khoản tích hợp, các phiếu điều chỉnh giá có thể cho lịch sử đổi giá có chủ đích (kể cả trước 28/05/2026). Độ sâu và cấu trúc chưa biết cho tới khi có quyền. User đã chốt Q1 (giá từ 28/05/2026 là đủ), nên việc này chỉ ghi lại để tham khảo. Không có endpoint nào cho lịch sử vị trí tồn.

## 4. Webhook sản phẩm

Không có. `ingestion/src/sapo/webhook_consumer.py:164` có định tuyến `product`, nhưng mọi sự kiện webhook Sapo đang về `sapo_v2_raw/unknown/ingest_method=webhook` (17.199 dòng, 28/01 → 15/10/2026). Toàn bộ là payload đơn hàng: có `order_line_items`, không có `variants`, `event_type` là `update` hoặc `create`. Thư mục `product` chỉ có `batch_sync` và `history_log`. Thiết kế không đổi.

## 5. Múi giờ

Container: `TZ=Asia/Ho_Chi_Minh`; DuckDB `current_setting('TimeZone') = 'Asia/Ho_Chi_Minh'`.

```sql
select (timezone('Asia/Ho_Chi_Minh', TIMESTAMPTZ '2026-10-15 20:01:00+00') - interval 6 hour)::date  -- 2026-10-15
select (timezone('Asia/Ho_Chi_Minh', TIMESTAMPTZ '2026-10-16 03:00:00+00') - interval 6 hour)::date  -- 2026-10-16
```

03:01 ICT ngày 16/10 cho `as_of_date` 15/10, còn lần chạy tay 10:00 ICT ngày 16/10 cho 16/10, đúng như design §4. Ở phía Python, runner tính `year`/`month` bằng `zoneinfo` `Asia/Ho_Chi_Minh` và không phụ thuộc `TZ` của container (có pytest cho 31/10 23:30 UTC → tháng 11, và 31/12 17:00 UTC → 2027/1).

## 6. Câu trả lời của user

Theo `plan.md` mục "Đã chốt" (15/10/2026 ~17:50):

| Câu | Đã chốt |
|---|---|
| Q1 độ sâu | Lịch sử giá từ 28/05/2026 là đủ; không tìm thêm nguồn |
| Q2 retention | Giữ raw ảnh chụp vĩnh viễn |
| Q3 payload | Gọn (chỉ giá và tồn) |
| Q4 giờ chốt | 06:00 |
| Q5 deploy D1 | Phase 1 tách riêng, sớm nhất có thể; **giờ deploy cụ thể chưa có, cần user duyệt** |
| Q6 | Có: plan riêng, ưu tiên, chuyển `fact_inventory_snapshot`/`mart_inventory_health` sang ảnh chụp mới |

## 7. Đối chiếu plan DR

`plans/261015-1140-backup-restore-dr/design.md` §4:
- Dòng 83: `data_lake/sapo_v2_raw` lên off-site **nguyên thư mục**, hằng ngày.
- Dòng 85: đã có dòng riêng cho `data_lake/sapo_v2_raw/product_daily_snapshot`, lớp "Không dựng lại được", lên off-site, khôi phục bằng giải nén và "không chạy lại full refresh đè lên".

Phase 2 của plan DR (`phase-02-offsite-backup-sidecar.md:42`) dựng `offsite-include.txt` với exclude chỉ gồm phái sinh và mồ côi, không có danh sách include theo bảng trong `sapo_v2_raw`. Đường dẫn mới vì vậy tự được phủ, không cần thêm gì. `restic ls latest` kiểm được khi DR phase 2 đã chạy (tiêu chí 7, phase 3 của plan này).
