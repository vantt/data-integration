---
phase: 3
title: "Áp pack_ref cho 4 hook lõi → pack đơn giản"
status: pending
priority: P1
effort: "0.5d"
dependencies: [2]
---

# Phase 3: `pack_ref` cho các hook lõi đơn giản

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` §7 (core: cột nào đến từ pack, giá trị khi pack tắt), §8 (bảng hợp đồng lõi ↔ pack); `transformation/models/packs/finance/README.md` và `transformation/models/packs/crm/README.md` (mục "Lõi đọc gì từ pack này", trỏ về `pack_contracts()`); mô tả cột trong `transformation/models/core/marts/_core__models.yml` và `core/marts/sales/_core__models.yml` cho các cột bị ảnh hưởng ("NULL khi tắt pack finance").

## Phạm vi (đã kiểm với code 14/10/2026)

Cạnh lõi → pack tìm bằng grep `ref()` trong `models/{core,cdm,connectors,tenants,monitoring}` tới tên model trong `models/packs/` và đối chiếu `scripts/checks/boundary_allowlist.yaml`. Phase này lo 4 cạnh "một model đọc vài cột"; 4 cạnh tới `mart_sku_economics_monthly` để phase 4.

| Model lõi | Đọc từ pack | Cột dùng | Hợp đồng `pack_contracts()` | Khi tắt pack |
|---|---|---|---|---|
| `dim_customers` (`core/marts/dim_customers.sql:14-16, 128-130, 163, 350-351`) | `finance.int_customer_economics` | `customer_key`, `lifetime_gross_profit`, `lifetime_contribution_margin` | 3 cột trên | Hai cột lãi là **NULL** (xem dưới) |
| `dim_staff` (`core/marts/dim_staff.sql:10-13, 26, 29`) | `crm.stg_crm__app_user` | `crm_user_id`, `email`, `is_active` | 3 cột trên | `crm_user_id` NULL |
| `dim_sku_alias` (`core/marts/dim_sku_alias.sql:98-103`) | `finance.int_misa_sales_lines` | `product_code`, `is_promo_line`, `is_service_line` | 3 cột trên | Không sinh alias tự động VTS→VCS (chỉ còn alias tay từ seed) |
| `mart_data_quality` (`core/marts/sales/mart_data_quality.sql:11-17`) | `finance.fact_order_economics` | `has_cogs`, `has_platform_fees` (và `count(*)`) | 2 cột trên | Các đếm giá vốn/phí sàn = 0 |

Kiểu cột trong hợp đồng lấy bằng `DESCRIBE` trên lake-A (shadow), không đoán. `mart_customer_tier` (`core/marts/customer/mart_customer_tier.sql:26, 31, 72`) chỉ chuyển tiếp `lifetime_contribution_margin` từ `dim_customers` và không dùng nó trong `CASE strategic_tier` (L37-56), nên **không sửa**; khi tắt finance cột này NULL theo `dim_customers`.

Hai cạnh `dim_sku_alias` và `mart_data_quality` không có trong danh sách của user nhưng nếu giữ `ref()` thẳng thì profile lõi trần không parse được (câu hỏi mở #3 ở plan.md). Lối ra tốt hơn (đọc `std_misa_sales_lines` ở `dim_sku_alias`, dời phần kiểm finance của `mart_data_quality` sang pack) có thể đổi số nên để sau.

## Cách sửa

- Mỗi model thay `{{ ref('<m>') }}` bằng `{{ pack_ref('<pack>', '<m>') }}` đúng tại chỗ; giữ nguyên mọi chữ khác, kể cả `SELECT *` trong CTE `economics` của `dim_customers` (khi pack tắt, quan hệ rỗng chỉ có cột hợp đồng; mọi chỗ dùng `e.` trong `dim_customers` đã kiểm chỉ đọc `customer_key` và hai cột lãi).
- `dim_customers` L350-351: bọc `COALESCE(x, 0)` bằng `{% if pack_enabled('finance') %}COALESCE(x, 0){% else %}CAST(NULL AS <type>){% endif %}` để tắt finance ra NULL (câu hỏi mở #2). Nhánh bật compile ra đúng chuỗi cũ.
- Thêm 4 mục vào `pack_contracts()`; gắn test `pack_contract` vào `int_customer_economics`, `stg_crm__app_user`, `int_misa_sales_lines`, `fact_order_economics` trong file properties của pack tương ứng (`transformation/models/packs/<pack>/**/_*.yml`).
- Xoá 4 dòng allowlist `core -> pack` tương ứng (rule `dbt-ref`, subject `dim_customers`, `dim_staff`, `dim_sku_alias`, `mart_data_quality` → `fact_order_economics`). Dòng `mart_data_quality` → `fact_us_shipment_economics` (tenant) **giữ nguyên**.

## Files

- Modify: `transformation/models/core/marts/dim_customers.sql`, `core/marts/dim_staff.sql`, `core/marts/dim_sku_alias.sql`, `core/marts/sales/mart_data_quality.sql`, `transformation/macros/packs/pack_contracts.sql`, properties YAML của 4 model pack, `scripts/checks/boundary_allowlist.yaml`, tài liệu ở khối đầu.

## Verification

- **Gate M `--allow-new --allow-code-change`** (checksum SQL nguồn đổi; test mới là asset check mới): golden 83/83.
- **Compiled SQL giống hệt:** chạy riêng `scripts/checks/dbt_inventory.py compiled-diff <lake-A manifest> <lake-B manifest>` **không cờ**, phải exit 0. Đây là bằng chứng "Fine Japan byte-identical" (sau chuẩn hoá khoảng trắng).
- 4 test `pack_contract` pass trên lake-B.
- `check_boundaries.py` pass với allowlist đã bớt 4 dòng; thêm tạm một `ref('int_customer_economics')` thẳng vào `dim_customers` → fail (rồi bỏ).
- `build-profile.sh` với `{enabled_packs: []}`: parse không còn báo lỗi ở 4 model này (còn lỗi ở 4 model đọc `mart_sku_economics_monthly`, phase 4 xử lý).

**Đổi số:** không (profile Fine Japan).

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Khoảng trắng do khối `{% if %}` làm compiled-diff báo khác | compiled-diff chuẩn hoá khoảng trắng; dùng `{%- -%}` nếu cần |
| Kiểu trong hợp đồng lệch kiểu thật (vd. `crm_user_id` từ parquet CRM) | Lấy bằng `DESCRIBE`; test `pack_contract` bắt khi lệch |

## Rollback

`git revert` theo runbook. Không có relation mới hay bị xoá.
