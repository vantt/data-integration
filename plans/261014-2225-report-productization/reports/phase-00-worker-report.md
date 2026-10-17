# Phase 00 — báo cáo worker

**Trạng thái:** xong cho nhóm Weekly Pulse (đúng phạm vi phase 01 cần); các nhóm chỉ tiêu khác ghi danh sách "chưa đối chiếu", làm trước phase 10 theo mục Rủi ro của phase.

## File của phase này

Worktree `/home/vantt/app/fg-dw-report` (nhánh `feat/report-productization`):
- `docs/architecture/modules.md` — dòng trạng thái, mục lục, mục mới "13. Analytics (report)" (mục đích, ranh giới, nguồn sự thật tương lai là registry, cách so bước 0).
- `docs/analytics-handbook/semantic/metrics.md` — chỉ thêm banner (tiếng Anh, theo ngôn ngữ file), không đổi định nghĩa.

Thư mục plan (checkout prod, chưa track):
- `plans/261014-2225-report-productization/definitions-comparison.md` (mới)
- `plans/261014-2225-report-productization/definition-decisions.md` (mới)
- `plans/261014-2225-report-productization/reports/phase-00-worker-report.md` (file này)

Không sửa code, dbt, Rill, blueprint.

## Kiểm chứng

- 30/30 question của `ceo_weekly_pulse.md` có dòng trong bảng ánh xạ (24 dữ liệu + 6 meta).
- 17 chỗ lệch, mỗi chỗ có số mẫu đo thật (tuần 05–11/10/2026, tháng 09/2026) và trạng thái `chờ user`.
- Bản chụp: chép `olap.duckdb` (catalog) sang scratchpad, mở `read_only=True` trong container `fg-dataware-house-data_platform` `--network none`, `app_data/data_lake` mount `:ro`. Bản chụp tạm đã xoá. Không mở `olap.duckdb` gốc.
- Hai lỗi số: một dòng tham chiếu (R-1), không đo lại, không đề xuất sửa.

## Quyết định chờ user (tóm tắt)

QĐ-01 Total Orders gồm đơn huỷ/nháp · QĐ-02 AOV trộn phân khúc · QĐ-03 AOV tập rỗng 0 hay NULL · QĐ-04 Discount Rate trộn B2B · QĐ-05 đạt mục tiêu theo GMV, metrics.md sai cột · QĐ-06 goal 600 tr cứng · QĐ-07 cửa sổ tháng không nhất quán (Pace/Forecast/Run-rate) · QĐ-08 Evidence "đến hết hôm qua" · QĐ-09 nhãn "14 Days" · QĐ-10 khách mới tính cả kênh nội bộ · QĐ-11 ba cách phân loại khách mới/cũ · QĐ-12 card khách không lọc hiệu lực · QĐ-13 Cancelled gồm nháp · QĐ-14 độ phủ giá vốn · QĐ-15 return_count trong metrics.md vô hiệu · QĐ-16 returns_amount lọc trạng thái nào · QĐ-17 múi giờ phiên.

## Ghi chú

- Link trong banner `metrics.md` để dạng đường dẫn chữ vì thư mục plan chưa có trong worktree.
- Dependency "Đợt 1 phase 7": coordinator giao chạy phase 00–03 ngay; không kiểm thêm.
