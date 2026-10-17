---
phase: 4
title: "Tách mart_sku_economics_monthly: doanh số/tốc độ ở lõi, giá vốn/biên ở finance; profile lõi trần vào gate"
status: pending
priority: P1
effort: "0.75d"
dependencies: [3]
---

# Phase 4: Tách `mart_sku_economics_monthly`

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` §7 (core có `int_sku_sales_monthly`; ngoại lệ `fact_variant_prices_snapshot` nếu user chọn giữ), §8 (finance đọc lõi để tính giá vốn/biên SKU); `transformation/models/packs/finance/README.md`; mô tả model/cột trong `transformation/models/core/marts/_core__models.yml` (hoặc file properties của `core/marts/intermediate/`) và `core/marts/sales/_core__models.yml` (mô tả `mart_inventory_health` L536, L580, L589 đang nhắc `mart_sku_economics_monthly`); `docs/operations/refactor-safety-harness.md` §6 và §7 (bước gate mới "lõi trần"); `scripts/shadow/README.md`.

## Hiện trạng (đã đọc code)

`transformation/models/packs/finance/marts/sales/mart_sku_economics_monthly.sql` (bảng public, rolling) trộn hai phần:

- **Doanh số/tốc độ** (chỉ đọc lõi: `dim_products`, `dim_channels`, `fact_sales`, `fact_orders`, `int_return_sku_lines`): CTE `snapshot_months`, `products`, `valid_channels`, `sales_base`, `valid_orders`, `sales_filtered`, `sales_agg`, `monthly_totals`, `top200_threshold`, `returns_agg`, `channel_revenue`, `channel_ranked`, `top_channel`.
- **Giá vốn/biên** (đọc `int_misa_sales_lines` của finance và `fact_inventory_movements` của lõi): `misa_per_unit`, `misa_cogs`, `sapo_mac_cogs`, `cogs_trailing`.

Người đọc ở lõi (4 cạnh `core -> pack:finance` trong allowlist):

| Model lõi | Chỗ đọc | Cột thật sự dùng |
|---|---|---|
| `int_product_velocity_trend` | `core/marts/intermediate/int_product_velocity_trend.sql:17, 27, 59` | `snapshot_month`, `daily_velocity`, `product_key`, `units_sold` |
| `mart_inventory_health` | `core/marts/sales/mart_inventory_health.sql:69-82` | `product_key`, `snapshot_month`, `daily_velocity`, `days_since_last_sale`, `is_slow_mover` |
| `mart_product_action_queue` | `core/marts/mart_product_action_queue.sql:30-36` | `product_key`, `net_revenue`, `units_sold`, `snapshot_month` (lý do trong allowlist nói dùng cột biên là **sai**; code chỉ dùng doanh số) |
| `mart_product_health` | `core/marts/mart_product_health.sql:34-63` | doanh số: `product_code`, `product_name`, `units_sold`, `net_revenue`, `daily_velocity`, `days_since_last_sale`, `revenue_share_pct`; biên: `realized_margin_pct`, `cogs_variance_pct`, `margin_outlier`, `cogs_source` |

## Thiết kế

1. **Model lõi mới `int_sku_sales_monthly`** (`transformation/models/core/marts/intermediate/`, `materialized='table'` như `int_product_velocity_trend`, không có `location` nên không tạo thư mục rolling, không lên serving). Grain `(product_key, snapshot_month)`, đúng tập dòng của `sales_agg`. Chuyển nguyên văn các CTE doanh số và các biểu thức cột doanh số từ mart cũ. Cột: `product_key`, `product_code`, `product_name`, `misa_join_key`, `misa_qty_multiplier`, `snapshot_month`, `units_sold`, `net_revenue`, `order_count`, `daily_velocity`, `return_count`, `return_quantity`, `refund_amount_allocated`, `return_rate`, `days_since_last_sale`, `is_slow_mover`, `revenue_share_pct`, `top_channel_name`, `top_channel_revenue_pct`. (Hai cột `misa_*` lấy từ `dim_products` của lõi, là khoá ghép mà finance cần; ghi rõ trong mô tả.)
2. **`mart_sku_economics_monthly` ở finance** đọc `int_sku_sales_monthly` (pack → lõi, được phép) thay cho các CTE doanh số; giữ các CTE giá vốn; câu `SELECT` cuối **giữ đúng thứ tự 29 cột và biểu thức** như hiện nay (`mart_sku_economics_monthly.sql`, khối `SELECT` cuối), giữ `ORDER BY`. Cột doanh số lấy thẳng từ lõi, không tính lại, để số thực không lệch do thứ tự cộng.
3. **Người đọc ở lõi:**
   - `int_product_velocity_trend`, `mart_inventory_health`, `mart_product_action_queue`: đổi `ref('mart_sku_economics_monthly')` → `ref('int_sku_sales_monthly')`; tên cột giữ nguyên nên chỉ đổi tên relation.
   - `mart_product_health`: CTE `latest_econ` đọc `int_sku_sales_monthly` cho cột doanh số và `LEFT JOIN {{ pack_ref('finance', 'mart_sku_economics_monthly') }}` theo `(product_key, snapshot_month)` cho 4 cột biên; `abc_base` đọc `int_sku_sales_monthly`. Vì mart finance có đúng tập dòng của `int_sku_sales_monthly`, `LEFT JOIN` cho cùng giá trị khi finance bật. Hợp đồng mới trong `pack_contracts()`: `mart_sku_economics_monthly` → `product_key`, `snapshot_month`, `realized_margin_pct`, `cogs_variance_pct`, `margin_outlier`, `cogs_source`.
4. Xoá 4 dòng allowlist `core -> pack:finance` tới `mart_sku_economics_monthly`; thêm `int_sku_sales_monthly: core` vào `scripts/checks/model_buckets.yaml`.

Khi finance tắt: `mart_product_health` có `has_margin_data = false` cho mọi SKU, `health_class`, `margin_score` và 4 cột biên NULL (đúng caveat 1 của model: không có dữ liệu biên thì không xếp hạng sức khoẻ); `mart_product_action_queue` theo đó.

## Quyết định cần user: `implied_gross_margin_pct`, `is_below_cost`

Hai cột nằm ở `core/marts/sales/fact_variant_prices_snapshot.sql:80-95` (bảng public, kind rolling, khoá `variant_id, price_list_id, snapshot_date` trong `public_models.yaml`). Bảng tích luỹ ảnh chụp hằng ngày (chú thích L6-8), serving đọc gộp các file. Dời hai cột sang finance là **đổi bảng public** (mất 2 cột; ngày cũ còn giá trị, ngày mới NULL qua `union_by_name`). Hai cột không đọc pack nào nên không cản profile lõi trần; grep không thấy người đọc nào trong repo (Metabase chưa kiểm được: chỉ có blueprint trong repo).

- **Đề xuất (mặc định của phase này):** giữ nguyên, ghi ngoại lệ "phép tính biên trên giá nhập Sapo nằm ở lõi" kèm lối ra trong `modules.md` §7. Không đổi file.
- **Nếu user chọn dời ngay:** tạo `packs/finance/marts/intermediate/int_variant_price_margin.sql` (table, khoá như trên) chứa hai cột; bỏ hai cột khỏi `fact_variant_prices_snapshot`; chạy **gate S**, đọc khác biệt (chỉ được khác đúng 2 cột của bảng này), cập nhật `public_models.yaml`, kiểm Metabase không có card nào dùng hai cột, deploy riêng (không gộp D1).

## Profile "lõi trần" vào gate

Sau phase này, `build-profile.sh` với `{enabled_packs: []}` phải build xanh. Thêm bước **6b** vào `scripts/shadow/gate.sh`: chạy `build-profile.sh lake-P '{enabled_packs: [], tenant: ""}'` (biến `tenant` chưa dùng tới phase 5, vô hại), fail khi build fail; in `golden_snapshot.py compare lake-A lake-P` để người làm đối chiếu.

**Danh sách khác biệt dự kiến** (ghi vào `scripts/shadow/README.md`, dùng để duyệt bằng mắt; gate chỉ fail theo kết quả build): bảng public của pack vắng mặt; `dim_customers` (2 cột lãi NULL), `mart_customer_tier` (`lifetime_contribution_margin` NULL), `dim_staff` (`crm_user_id` NULL), `dim_sku_alias`, `dim_products` và `int_customer_sku_supply_tracking` (mất alias tự động VTS→VCS; hai model sau đọc `dim_sku_alias`), `mart_data_quality` (đếm giá vốn/phí sàn = 0), `mart_product_health`, `mart_product_action_queue` (cột biên và `health_class`). Bảng khác ngoài danh sách là lỗi phải giải thích trước khi chấp nhận phase. Danh sách cuối cùng lấy từ manifest (con cháu của các model trên) và ghi vào báo cáo phase.

## Files

- Create: `transformation/models/core/marts/intermediate/int_sku_sales_monthly.sql` + mô tả trong properties YAML của thư mục.
- Modify: `packs/finance/marts/sales/mart_sku_economics_monthly.sql`, 4 model lõi ở trên, `transformation/macros/packs/pack_contracts.sql`, properties YAML của `mart_sku_economics_monthly` (test `pack_contract`), `scripts/checks/model_buckets.yaml`, `scripts/checks/boundary_allowlist.yaml`, `scripts/shadow/gate.sh`, `scripts/shadow/README.md`, tài liệu ở khối đầu.

## Verification

- **Gate M `--allow-new --allow-code-change`**: golden 83/83 (gồm `mart_sku_economics_monthly`, `mart_product_health`, `mart_inventory_health`, `mart_product_action_queue`, `int_product_velocity_trend` không public nhưng chảy vào các bảng trên). compiled-diff có cờ chỉ báo khác ở 5 model đã sửa và model mới; inventory dbt: `depends_on` đổi đúng như thiết kế.
- Kiểm không có thư mục mới trong `export/marts/rolling/` của lake-B so với lake-A.
- Bước 6b xanh; khác biệt nằm trong danh sách dự kiến.
- Test `pack_contract` của `mart_sku_economics_monthly` pass.
- Nếu golden lệch: `golden_snapshot.py keyed-diff` trên bảng lệch, sửa để cột doanh số đi thẳng từ lõi; không nới dung sai.

**Đổi số:** không (profile Fine Japan).

## Deploy D1 (sau phase 4, gộp phase 2–4)

Chạy lại gate trên commit đầu của lô, rồi runbook "Refactor deploys (shadow-verified)" với tên nhánh `feat/pack-mechanism` ở bước 4. Ngoài khung 02:30–04:00. Sau deploy: một lần `pipeline_sapo_v2_realtime_job` xanh, nightly kế tiếp xanh, kiểm thêm test `pack_contract` không đỏ.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Số thực lệch vì tính lại cột doanh số ở finance | Finance không tính lại, chỉ đọc lõi |
| Kiểu cột `mart_sku_economics_monthly` đổi (vd. `net_revenue` qua bảng trung gian) → golden và `SCHEMA_DRIFT` cột | Golden so kiểu; nếu lệch thì `CAST` về kiểu cũ ở finance |
| Bỏ sót người đọc khác của `mart_sku_economics_monthly` | Grep lại `ref('mart_sku_economics_monthly')` toàn repo và tên bảng trong `crm/`, `detailView/`, `evidence/`, `rill/`, blueprint trước khi sửa; người đọc ngoài dbt vẫn đọc bảng finance không đổi |

## Rollback

`git revert` theo runbook. Bảng `int_sku_sales_monthly` còn lại trong `main_marts` của warehouse sau revert: vô hại, xoá bằng `DROP TABLE` khi tiện.
