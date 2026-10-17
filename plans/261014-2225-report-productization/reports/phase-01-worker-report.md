# Phase 01 — báo cáo worker

**Trạng thái:** xong. Registry tối thiểu (25 chỉ tiêu Weekly Pulse), compiler, validator, docs sinh ra, validator chạy trong `run-all.sh`.

## File của phase này (worktree `/home/vantt/app/fg-dw-report`)

Mới:
- `analytics/__init__.py`, `analytics/__main__.py` (CLI `python3 -m analytics validate|compile|docs`), `analytics/README.md`
- `analytics/schema/{semantic-model,metric,tenant-profile}.schema.json`
- `analytics/registry/semantic/{orders,order_economics,order_returns,targets,customers,channels}.yml`
- `analytics/registry/metrics/{sales,customers,finance}.yml`
- `analytics/compiler/{__init__,loader,formula,sql,validate}.py` (`formula.py` thêm ngoài danh sách: cú pháp biểu thức `derived`, tách riêng cho dễ kiểm)
- `analytics/renderers/{__init__,docs}.py`
- `analytics/tests/{__init__,golden_cases,regen_golden,test_schema,test_validate,test_compile_golden}.py`, `analytics/tests/golden/*.sql` (53 file)
- `tenants/fine_japan/analytics/profile.yml`
- `scripts/checks/check_analytics_registry.py`
- Sinh ra: `docs/analytics-handbook/semantic/metric-registry.md`, `docs/analytics-handbook/semantic/glossary.md`

Sửa:
- `scripts/checks/run-all.sh` (bước 5: validator + pytest `analytics/tests` trong image prod, worktree `:ro`, `--network none`)
- `scripts/checks/check_boundaries.py` (luật `py-import` cho `analytics/`), `scripts/tests/test_check_boundaries.py`
- `scripts/checks/README.md`, `docs/architecture/modules.md` (§13, bảng trạng thái, §12), `docs/analytics-handbook/semantic/metrics.md` (banner), `docs/analytics-handbook/semantic/README.md` (2 dòng file sinh ra)

Thư mục plan: `definition-decisions.md` (thêm lưu ý vào QĐ-07), file báo cáo này.

## Kiểm chứng

- Bước 1: `yaml`, `jsonschema` có trên host (Python 3.14) và trong image `data_platform` (Python 3.10, jsonschema 4.26, duckdb 1.5.5); không có gói `analytics` trùng tên. pytest không có trên host → chạy trong image (ghi trong README).
- `python3 scripts/checks/check_analytics_registry.py`: 0 lỗi, 12 cảnh báo "cột chưa có dbt docs" (cột có trong mart, chỉ thiếu mô tả trong yml; thành lỗi khi có contract ở phase 10). Fixture hỏng đều exit ≠ 0 (thiếu trường bắt buộc, measure tỉ lệ theo dòng, join hai bước, `legacy_names` trùng id active, thiếu `coverage_metric`, cờ chi phí sai, biểu thức không tuyến tính, phân đoạn không có ràng buộc, vòng phụ thuộc).
- `pytest analytics/tests`: 93 passed (trong image). Compile hai lần ra chuỗi giống hệt.
- Bước 5 (so sớm): SQL compile của mọi chỉ tiêu so với SQL blueprint (thay `current_date` bằng literal) trên bản chụp chỉ đọc, 4 ngày tham chiếu 11/10, 04/10 (tuần qua ranh giới tháng), 15/09, 01/10 (ngày 1 của tháng): **136/136 khớp** (số làm tròn so theo kiểu DuckDB, nửa xa 0). Bản chụp tạm đã xoá.
- `scripts/checks/run-all.sh` (với `SHADOW_ROOT` trỏ vào scratchpad, không dùng `fg-dw-shadow`): `RUN-ALL: PASS`.

## Quyết định thiết kế cần biết

- Ranh giới ngày dùng `timezone(<tz của hồ sơ>, ...)` thay vì dựa vào múi giờ phiên DuckDB (an toàn cho Evidence; kết quả bằng blueprint khi phiên là ICT).
- Ràng buộc phân đoạn trong hồ sơ theo **từng model** (`segments.in_sales_scope.orders/order_economics/order_returns`), vì phiếu hoàn lấy kênh bán qua join `dim_channels`. Plan ghi dạng một dòng; đây là mở rộng tối thiểu.
- Thêm hai cửa sổ để tái tạo blueprint: `mtd_before_as_of` (QĐ-07) và `prev_week_start_to_date` (QĐ-09).
- Pace / Forecast / Run-rate biểu diễn được bằng `derived` (biểu thức tuyến tính với hệ số lịch), nên không cần `inline_sql`; dự kiến chỉ 2 card `inline_sql` như plan.
- `as_of` lúc chạy gọi là `runtime` (`--as-of runtime`).

## Ghi chú

- `scratchpad/q.py`, `run.sh` của phiên coordinator (nếu có) có thể đã bị tôi ghi đè ở phase 00 trước khi chuyển file của tôi vào `scratchpad/rp/`.
