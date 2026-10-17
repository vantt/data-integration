---
phase: 15
title: "Rill: sinh measure và orders_enriched từ registry"
status: pending
priority: P3
effort: "2.5d"
dependencies: [10, "sửa lỗi Rill scope_* (session thực thi, ngoài plan)"]
---

# Phase 15: Rill sinh từ registry

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi phạm vi sinh (measure, danh sách chiều, model join) và phần giữ tay (`dashboards/*.yaml`) vào `rill/README.md` (tạo nếu chưa có) và `analytics/README.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `rill/README.md`; `analytics/README.md` (renderer Rill); `docs/guides/rill-with-metabase.md` (định nghĩa giờ chung với Metabase/Evidence); `docs/analytics-handbook/blueprints/rill/` (ghi file nào sinh ra); `docs/architecture/modules.md`.

## Mục tiêu

Rill dùng nội bộ cho phân tích tự do và hỗ trợ khách (thiết kế §4 ⑤). Sau khi định nghĩa đã thống nhất, sinh measure Rill từ registry để Rill, Metabase và Evidence ra cùng số. Không phải đường găng.

## Điều kiện vào

Lỗi Rill tự tính `scope_*` lệch mart (`rill/models/orders_enriched.sql:79-83`) đã được session thực thi sửa riêng (Rill dùng thẳng cột `scope_*` của mart, qua gate S, user duyệt). Plan này không sửa lại lỗi đó.

## Thiết kế

- `analytics/renderers/rill.py` sinh: `rill/metrics/*.yaml` phần `measures` (ánh xạ một-một `id → name`, `label → display_name`, `description`, biểu thức SQL DuckDB từ compiler với `filters` thành `... FILTER (WHERE ...)`, `unit → format_preset`) và danh sách `dimensions`; `rill/models/orders_enriched.sql` sinh từ các `joins` của lớp ngữ nghĩa (một nguồn join, giảm lệch). File `rill/dashboards/*.yaml` (dạng explore, `measures: "*"`) giữ tay.
- Định nghĩa Rill lệch registry (ví dụ `orders_count = count(*)` so với `COUNT(DISTINCT order_id)`) đã có quyết định ở phase 00; áp ở đây. Mọi measure ra số khác bản Rill hiện tại là **đổi số trên Rill**: lập danh sách trước/sau, user duyệt trước khi deploy.
- Rill đọc parquet export (`export/rill/current`), không đọc `olap.duckdb`; renderer dùng bảng ánh xạ relation riêng cho Rill.

## Các bước

1. Renderer + test golden (sinh hai lần không diff).
2. Kiểm cú pháp bằng container Rill đã ghim (`v0.87.8`, `Dockerfile.rill`) chạy thử dưới tên/cổng khác (cổng 3102), mount bản sao `rill/` [lệnh validate cụ thể cần xác minh với Rill 0.87.8].
3. Golden query: một số measure × kỳ chạy trên export Rill và trên DuckDB serving bằng SQL compiler, phải khớp.
4. Danh sách đổi số Rill → user duyệt → deploy (`rill/` được bind-mount vào container `rill`; restart ngoài khung cấm).

## Files

- Tạo: `analytics/renderers/rill.py`, test.
- Sinh: `rill/metrics/*.yaml` (phần measures/dimensions), `rill/models/orders_enriched.sql`.
- Sửa: tài liệu ở đầu file.

## Verification

- Sinh lại không diff; container Rill thử parse thành công và dashboard explore mở được.
- Golden query khớp giữa Rill và DuckDB serving.
- Danh sách đổi số Rill đã được user duyệt trước deploy.

## Đổi số?

Có thể, **chỉ trên Rill** và chỉ các measure trong danh sách user đã duyệt; Metabase và Evidence không đổi.

## Rollback

Revert commit sinh file; `docker compose restart rill`.
