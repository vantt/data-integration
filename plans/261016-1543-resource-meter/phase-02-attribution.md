# Phase 2: gắn số với job, bước Dagster và model dbt

**Effort:** 0.75d · **Phụ thuộc:** phase 1 · **Đụng prod:** không

## Yêu cầu

1. **Bước Dagster:** với mỗi tiến trình bước, lấy run id và step key theo cách phase 0 đã xác nhận. Gộp tiến trình con vào bước của cha. Ghi `steps-YYYYMMDD.tsv`: run id, tên job (nếu lấy được), step key, bắt đầu, kết thúc, RSS đỉnh (tổng cây tiến trình theo mẫu 1 giây), CPU-giây, đĩa đọc/ghi.
2. **Job `in_process_executor`:** ghi một dòng mức job cho cả tiến trình.
3. **Model dbt:** khi tiến trình dbt thoát, đọc `run_results.json` của lần chạy đó (đường dẫn theo phase 0). Với mỗi model: lấy khoảng `execute` từ `timing`, cắt chuỗi mẫu 1 giây của tiến trình dbt trong khoảng đó, tính RSS đỉnh, RSS tăng thêm so với lúc bắt đầu model, CPU-giây. Ghi `models-YYYYMMDD.tsv`: run id, unique_id model, trạng thái, thời gian, RSS đỉnh, RSS tăng, CPU-giây, số dòng (`adapter_response.rows_affected` nếu có).
4. Model ngắn hơn 1 giây: ghi thời gian, để trống RAM.
5. Không lưu `environ` hay dòng lệnh đầy đủ; chỉ khoá nhận diện.

## Test

- Unit: ghép mẫu với `timing` từ một `run_results.json` giả (tên model giả).
- So với một nightly thật (đọc lại sau, không chạy job): mọi step key của Dagster UI có dòng; thời gian model khớp `run_results.json`.
