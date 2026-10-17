# Phase 0: chốt ẩn số và câu trả lời của user

**Effort:** 0.25d · **Phụ thuộc:** — · **Đụng prod:** chỉ đọc (truy vấn tổng hợp trên parquet, DuckDB trong bộ nhớ; không chạy job, không ghi) · **Tránh:** 02:30–04:00

## Bối cảnh

Design §1 đã đo các điểm sau: nguồn cũ, sản phẩm đổi tồn hoặc giá mà không đổi `modified_on`, dung lượng mỗi ngày. Phase này chốt những gì còn thiếu trước khi viết code. Kết quả ghi vào `reports/phase-00-findings.md` trong thư mục plan này.

## Việc

1. **Kích thước payload gọn so với đầy đủ:** trên file tải đủ 13/06/2026 (`sapo_v2_raw/product/ingest_method=batch_sync/.../11026f1190.parquet`), ghi một bản chỉ còn `id`, `modified_on`, `variants[].{id, sku, variant_prices, inventories}` vào scratch, rồi so kích thước parquet zstd với bản đầy đủ. Mục đích: trả lời Q3 bằng số đo.
2. **Chi phí quét đủ:** đếm số sản phẩm và số trang (`ingestion/src/sapo/api_count.py` đã có hàm lấy tổng) bằng một lần gọi `count` chỉ đọc, hoặc lấy từ metadata run batch sản phẩm gần nhất. Ghi lại `request_delay` hiện có (`client.request_delay`) để ước thời lượng asset.
3. **API Sapo có lịch sử giá hay tồn không:** đọc tài liệu Sapo (WebFetch) và `ingestion/src/sapo/client.py` để tìm endpoint điều chỉnh giá, lịch sử bảng giá, hoặc tồn theo ngày. Nếu có thì ghi rõ endpoint, độ sâu và quyền truy cập, kèm đề xuất plan riêng. Không gọi endpoint ghi.
4. **Webhook sản phẩm:** xác nhận Worker có nhận sự kiện `product` hay không. Hiện `sapo_v2_raw/product` chỉ có `ingest_method=batch_sync|history_log`, không có `webhook`. Nếu có sự kiện sản phẩm theo thời gian thực thì ghi lại, vì nó bổ sung cho nhật ký đổi giá, nhưng không đổi thiết kế.
5. **Múi giờ trong container:** xác nhận `current_timestamp` và `timezone('Asia/Ho_Chi_Minh', ...)` trong DuckDB của dbt cho ra `as_of_date` đúng với một `captured_at` mẫu (03:01 ICT ngày D+1 thì ra D). Chạy trong DuckDB bộ nhớ.
6. **Nhận câu trả lời Q1–Q6** (plan.md) từ user. Ghi lại các giá trị đã chốt: độ sâu, retention, gọn/đầy đủ, giờ chốt, giờ deploy D1, và có lập plan riêng cho Q6 hay không.
7. **Đối chiếu plan DR:** đọc lại `plans/261015-1140-backup-restore-dr/plan.md` và `design.md` §4 để xác nhận `sapo_v2_raw` vẫn lên off-site nguyên thư mục, không có danh sách include theo bảng. Nếu đã đổi sang danh sách theo bảng thì ghi việc cần thêm đường dẫn mới.

## Kiểm chứng

- `reports/phase-00-findings.md` có đủ 7 mục, mỗi số đo kèm lệnh hoặc truy vấn và thời điểm đo.
- Mọi file trong scratch đã xoá. `git status` của prod không đổi.

## Rủi ro và rollback

Chỉ đọc nên không cần rollback. Rủi ro duy nhất là truy vấn nặng chạy trùng lúc dbt chạy: các truy vấn đều chạy trên parquet (không mở `sapo_warehouse.duckdb`) và tránh khung 02:30–04:00.
