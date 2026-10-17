---
phase: 1
title: "Registry tối thiểu: chỉ tiêu Weekly Pulse dùng; JSON Schema + validator + docs sinh ra"
status: pending
priority: P1
effort: "2d"
dependencies: [0]
---

# Phase 01: Registry chỉ tiêu tối thiểu

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: viết `analytics/README.md` (module làm gì, hai lớp registry, giới hạn cứng của compiler, cách chạy validator) và cập nhật mục "Analytics (report)" trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md`; `docs/architecture/modules.md` (mục Analytics: thư mục, ai đọc/ghi, phụ thuộc cho phép); `scripts/checks/README.md` (dòng cho validator mới); `docs/analytics-handbook/semantic/metric-registry.md` (file **sinh ra**, có banner "generated"); `docs/analytics-handbook/semantic/glossary.md` (chú giải Việt–Anh, sinh ra); banner đầu `metrics.md` trỏ tới hai file trên.

## Mục tiêu

Một registry máy đọc được, chỉ chứa các chỉ tiêu mà 30 card của Weekly Pulse dùng, cùng compiler biên dịch metric → SQL DuckDB có giới hạn cứng, JSON Schema và validator chạy trong `scripts/checks/run-all.sh`. Không đổi số: mọi chỉ tiêu tái tạo đúng blueprint đang chạy (phase 00, "Quy tắc khi user chưa chốt").

## Thiết kế

### Vì sao Python

Validator phải ở `scripts/checks/` (thiết kế §4 ①), job tin tóm tắt trong Dagster (Python) cần biên dịch SQL thẻ KPI, và so số chạy DuckDB Python. Vì vậy nạp registry, kiểm, biên dịch SQL và mọi renderer viết bằng Python, một chỗ duy nhất (DRY). Tầng gọi API Metabase giữ bằng Node (`.skills/metabase-automation/lib/`) và nhận IR JSON từ Python (phase 08). `pyyaml` và `jsonschema` có sẵn qua dbt-core (hội đồng tooling §7); bước 1 kiểm lại trên host và trong image `data_platform`, không thêm phụ thuộc mới.

### Hai lớp (cùng hình dạng MetricFlow để còn đường lui)

- **Lớp ngữ nghĩa** `analytics/registry/semantic/<model>.yml`: `id`, `model` (tên model dbt), `relation` (tên view serving), `grain`, `time_dimensions` (cột, mặc định), `joins` (chỉ many-to-one, tối đa một bước, ví dụ `fact_orders.channel_key → dim_channels`, `fact_orders.customer_key → dim_customers`), `measures` (`column`, `agg ∈ {sum, count, count_distinct, min, max}`), `gates` có tên dạng có cấu trúc (`{column, op, values}`, không chuỗi SQL). Cột tỉ lệ theo dòng (`gross_margin_pct`…) ghi `aggregatable: false`.
- **Lớp chỉ tiêu** `analytics/registry/metrics/<domain>.yml`: `id`, `version`, `label {vi, en}`, `description`, `type ∈ {simple, ratio, derived, snapshot}`, `measure` hoặc `numerator/denominator` hoặc `expression` tuyến tính trên metric khác, `filters` (tham chiếu gate), `time_axis`, `additivity`, `null_policy`, `cost_sensitive`, `coverage_metric` (bắt buộc cho chỉ tiêu biên/lợi nhuận), `requires`/`enhances` (khả năng dữ liệu), `legacy_names`, `unit`, `status ∈ {draft, active, deprecated}`, `replaced_by`.

### Giới hạn cứng của compiler (chống "semantic layer tự chế")

Chỉ sum/count/count_distinct/min/max, ratio là tỉ số của tổng (không bao giờ AVG một tỉ lệ), derived là tổ hợp tuyến tính của metric khác, một trục thời gian, một bước join many-to-one. Window, lịch sử, phân bổ chi phí, ghép hai fact khác grain phải làm trong dbt. Vượt giới hạn → validator báo lỗi, không có lối thoát trong registry (lối thoát duy nhất là `inline_sql` ở spec, phase 02).

### Phân đoạn của khách, không phụ thuộc `*_std`

Weekly Pulse lọc `scope_sales` (cột phân loại riêng FJ). Registry khai báo gate trừu tượng `in_sales_scope`; **giá trị ràng buộc nằm trong hồ sơ khách** (`tenants/fine_japan/analytics/profile.yml`: `segments.in_sales_scope: {column: scope_sales, eq: true}`). Khi plan pack cung cấp `order_scope_std`, ràng buộc chuẩn chuyển sang cột đó (phase 10). Nhờ vậy thí điểm không chờ `*_std`.

### Cửa sổ thời gian và `as_of`

Compiler nhận tham số `as_of` (ngày dữ liệu đến hết) ở hai dạng: literal (`DATE '2026-11-02'`, dùng cho so số và lịch sử) hoặc biểu thức lúc build (`current_date - INTERVAL 1 DAY`, dùng cho Evidence). Cửa sổ hỗ trợ: `wtd`, `prev_week_full`, `prev_wtd_same_span`, `mtd`, `last_n_days`, `month_full`. Blueprint so tuần đến nay với **trọn tuần trước** (`ceo_weekly_pulse.md:95-104`); compiler tái tạo đúng.

### NULL

`null_policy: propagate` cấm `COALESCE(x, 0)` trên giá trị theo dòng. Tổng trên tập rỗng của chỉ tiêu cộng dồn trả 0 (`COALESCE(SUM(x), 0)` ở mức tổng), khớp blueprint (vd. `ceo_weekly_pulse.md:1241`); đây không phải dữ liệu thiếu.

### Đổi tên theo quyết định 1 (không đổi số)

`net_sales` (nhãn "Doanh thu bán hàng (trước hoàn)") trỏ cột mart `fact_orders.net_revenue`, `legacy_names: [net_revenue]`. Cột mart **không đổi tên** (bất biến không đổi tên cột public); đổi tên cột chỉ cân nhắc khi có schema serving có phiên bản (Đợt 3). Id `net_revenue` mới (sau hoàn) chưa thêm ở phase này vì cần `returns_amount` theo trục ngày hoàn; thêm ở phase 09. Validator chặn mọi `legacy_names` trùng với một id đang `active`.

### Docs sinh ra

`metrics.md` còn ~56 định nghĩa chưa vào registry, nên phase này **không** thay `metrics.md`; renderer docs sinh `metric-registry.md` và `glossary.md`, banner trong `metrics.md` nói chỉ tiêu nào đã có nguồn chuẩn. Phase 10 (registry đủ) mới cho `metrics.md` thành file sinh ra.

## Files

- Tạo: `analytics/__init__.py`, `analytics/__main__.py` (CLI `python -m analytics validate|compile|docs`), `analytics/README.md`.
- Tạo: `analytics/schema/semantic-model.schema.json`, `analytics/schema/metric.schema.json`, `analytics/schema/tenant-profile.schema.json` (JSON Schema 2020-12).
- Tạo: `analytics/registry/semantic/{orders,order_economics,order_returns,targets,customers,channels}.yml` (chỉ phần Weekly Pulse cần).
- Tạo: `analytics/registry/metrics/{sales,customers,finance}.yml` (~16–20 chỉ tiêu Weekly Pulse, danh sách lấy từ phase 00).
- Tạo: `analytics/compiler/{loader,validate,sql}.py`.
- Tạo: `analytics/renderers/docs.py`.
- Tạo: `tenants/fine_japan/analytics/profile.yml` (chỉ `segments`, `locale.timezone`, tham số doanh thu ghi tường minh đúng như hôm nay: ghi nhận ngày tạo đơn, trừ hoàn theo ngày hoàn, VAT tách ra; xem phase 09).
- Tạo: `analytics/tests/test_schema.py`, `analytics/tests/test_compile_golden.py`, `analytics/tests/golden/*.sql` (SQL mong đợi cho từng chỉ tiêu × cửa sổ).
- Tạo: `scripts/checks/check_analytics_registry.py` (gọi `analytics.compiler.validate`; mẫu theo `check_taxonomy_inventory.py`).
- Sửa: `scripts/checks/run-all.sh` (do Đợt 1 phase 7 tạo) thêm validator; `scripts/checks/README.md`; `scripts/checks/check_boundaries.py` nếu cần thêm quy tắc: `analytics/` không import `orchestration`, `transformation`; chỉ đọc `tenants/` qua tham số `--profile`.
- Sinh: `docs/analytics-handbook/semantic/metric-registry.md`, `docs/analytics-handbook/semantic/glossary.md`.

## Các bước

1. Kiểm `python3 -c "import yaml, jsonschema"` trên host và trong `data_platform` (đọc, không cài). Nếu thiếu ở host thì chạy validator trong container theo cách `scripts/shadow/pytest-shadow.sh` đang làm; ghi vào README.
2. Viết schema, rồi registry cho nhóm Weekly Pulse theo bảng của phase 00.
3. Viết compiler; mỗi chỉ tiêu × cửa sổ có một file golden SQL, test so chuỗi SQL đã chuẩn hoá.
4. Validator kiểm: JSON Schema; mọi `column` có trong khai báo cột của model (đọc `manifest.json` của dbt; cột chưa có docs thì cảnh báo, phase 10 nâng thành lỗi khi có contract); không metric nào dùng cột `aggregatable: false` làm measure; `legacy_names` không trùng id active; metric biên/lợi nhuận có `coverage_metric`; metric có `cost_sensitive: true` đúng với danh sách (giá vốn, biên, lợi nhuận, CM1–CM3); derived không vượt giới hạn; `metric-registry.md` sinh lại không có diff.
5. Chạy SQL compile của từng chỉ tiêu trên bản chụp chỉ đọc và so với biểu thức tương ứng trong blueprint cho một tuần đã đóng (kiểm tra sớm, chưa phải cổng thí điểm).

## Verification

- `python3 scripts/checks/check_analytics_registry.py` exit 0 trên registry thật; exit ≠ 0 trên từng fixture hỏng (thiếu trường bắt buộc, AVG cột tỉ lệ, join hai bước, `legacy_names` trùng id).
- `pytest analytics/tests` xanh; compile hai lần ra chuỗi giống hệt (tất định).
- Bước 5: mọi chỉ tiêu ra cùng số với blueprint trên tuần đã đóng gần nhất.
- `scripts/checks/run-all.sh` xanh trên nhánh.

## Đổi số?

Không. Không đụng dbt, dashboard hay trang đang chạy.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Registry không biểu diễn được một card (vd. "Loss-Making Channel Count" là aggregate lồng) | Để card đó ở `inline_sql` (phase 02); đếm tỉ lệ card `inline_sql` (điều kiện dừng > 30%) |
| `manifest.json` thiếu khai báo cột | Cảnh báo ở phase này, lỗi cứng sau khi có contract (phase 10) |
| Tên module `analytics` trùng gói Python khác trên `sys.path` | Kiểm import trong `data_platform` ở bước 1 |

## Rollback

Revert commit. Không có gì chạy trên prod.
