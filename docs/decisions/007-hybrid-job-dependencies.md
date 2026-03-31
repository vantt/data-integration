# ADR-007: Hybrid job explicit dependencies

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`dagster_dependencies.md`](../archive/dagster_dependencies.md)

## Bối cảnh

Dagster jobs có thể chạy subset of assets (ví dụ: Incremental job chỉ chạy webhook + history log, không chạy batch). Khi dbt staging model phụ thuộc cả 3 channels nhưng job chỉ chứa 2 → Dagster không biết dependency bị thiếu → dbt chạy ngay mà không đợi.

## Quyết định

**Explicitly declare dependencies** qua `get_upstream_asset_keys` trong dbt translator, kể cả assets không nằm trong job hiện tại.

Staging models phải depend on **tất cả** ingestion assets liên quan, không chỉ những cái trong cùng job.

## Lý do

- **Race condition thực tế**: dbt đọc data cũ/thiếu vì ingestion chưa xong
- **Dagster assumption**: nếu asset không trong job → không có dependency → run immediately
- **Bài học kinh nghiệm**: đã gặp bug production khi Incremental job chạy dbt trước khi webhook consumer kịp ghi data

## Hệ quả

- Cần maintain dependency mapping trong dbt translator code
- Khi thêm channel/entity mới → phải cập nhật dependency mapping
- Trade-off: explicit nhưng cần maintenance

## Khi nào xem xét lại

- Nếu Dagster hỗ trợ cross-job dependency natively → có thể simplify
- Nếu chuyển sang single job chứa tất cả assets → không cần explicit deps
