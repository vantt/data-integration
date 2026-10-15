# Khả năng dữ liệu (`seeds/capabilities/`)

Seed **của sản phẩm** (không phải dữ liệu tenant): mỗi connector cung cấp dữ liệu gì, và khả năng nào lõi hay pack cần. `monitoring/mart_capabilities` đọc hai seed này cùng biến dbt `enabled_connectors`, `enabled_packs` và đếm dòng trên dữ liệu thật để trả lời "triển khai này có dữ liệu gì" ở ba mức. Thiết kế: [docs/architecture/modules.md](../../../docs/architecture/modules.md) mục 5.1, 8, 11b.

**Bản xem trước:** danh sách khả năng là bản đầu, sẽ sửa khi catalog report định nghĩa `requires`/`enhances`.

## Hai seed

| Seed | Cột | Quy tắc |
|---|---|---|
| `connector_capabilities.csv` | `connector_id`, `capability`, `note` | `connector_id` là id trong `connectors:` của `orchestration/config/modules.yaml` (package `orchestration/connectors/<id>/`), không phải tên thư mục dbt (`misa`, `gsheet`). Mỗi connector là một khối dòng liền nhau. Khoá `(connector_id, capability)` |
| `capability_catalog.csv` | `capability`, `required_by`, `description_vi` | `required_by` là `core` hoặc id pack (`orchestration/packs/<id>/`); nhiều pack cần thì nhiều dòng. Khoá `(capability, required_by)` |

Kiểm tra: test dbt trong `_capabilities__seeds.yml` (khoá, `capability` của connector có trong catalog) và pytest `scripts/tests/test_capabilities_seeds.py` (id connector/pack có thật, khối liền nhau, mỗi khả năng của catalog có probe).

## Khả năng và cách đo "quan sát được"

Probe nằm một chỗ, dict `probes` đầu `transformation/models/monitoring/mart_capabilities.sql`: `count(*)` trên một model connector hoặc cdm (không bao giờ đọc pack, vì pack có thể tắt), có điều kiện lọc nếu cần, và cột ngày cho `last_observed_date` nếu có. Khả năng trong catalog mà không có probe làm model lỗi lúc build.

| Khả năng | Connector khai báo | Cần bởi | Probe | Ngày mới nhất |
|---|---|---|---|---|
| `orders` | sapo_v2 | core | `std_orders` | `created_at` |
| `order_items` | sapo_v2 | core | `std_order_items` | — |
| `customers` | sapo_v2 | core | `std_customers` | `created_at` |
| `products` | sapo_v2 | core | `std_variants` | — |
| `returns` | sapo_v2 | core | `std_order_returns` | `created_at` |
| `payments` | sapo_v2 | core | `std_payments` | `paid_at` |
| `fulfillments` | sapo_v2 | core | `std_fulfillments` | `created_at` |
| `staff` | sapo_v2 | core | `std_accounts` | — |
| `inventory` | sapo_v2 | core | `std_inventory_movements` | `issued_date_key` |
| `cogs_moving_avg` | sapo_v2 | finance | `std_inventory_movements` có `cogs_amount` | `issued_date_key` |
| `purchase_price` | sapo_v2 | finance | `std_variant_prices` với `price_list_code = 'GIANHAP'` (bảng giá nhập của Sapo; `dim_price_lists` cũng dùng mã này; chưa kiểm trên tài khoản Sapo khác) | — |
| `marketplace_fees` | shopee | finance, marketplace | `stg_shopee_order_service_fees` | — |
| `platform_discount` | shopee | finance | `stg_shopee_order_revenue` có `product_subsidy_from_shopee` (giảm giá sàn chịu; đếm dòng có cột này, kể cả giá trị 0) | `order_placed_at` |
| `gl` | misa_amis | finance | `std_misa_account_ledger` | `period_month` |
| `cogs_accounting` | misa_amis | finance | `std_misa_sales_lines` có `cogs_amount` | `posting_date` |
| `targets` | sheets | core | `std_targets` | `cycle_start_date` |
| `marketing_spend` | sheets | core | `std_marketing_spend` | — |
| `teams` | sheets | core | `std_teams` | — |
| `hug_scans` | hug | hug | `src_hug_scan` (connector `hug` chỉ có `src_*`) | — |

Không có trong danh sách: dữ liệu `crm_export.*` (do chính pack `crm` ghi, không phải connector) và seed tenant (ngân sách, giá US shipment).

## Trạng thái trong `mart_capabilities`

| `status` | Điều kiện | Nên làm |
|---|---|---|
| `OK` | Cần (lõi hoặc pack đang bật), có connector đang bật khai báo, probe có dòng | — |
| `DECLARED_NO_DATA` | Cần, khai báo, probe 0 dòng | Kiểm ingestion của connector (hoặc dữ liệu theo mùa) |
| `PACK_ON_NO_SOURCE` | Cần, không connector đang bật nào khai báo (dù còn dữ liệu cũ) | Bật connector cung cấp, hoặc tắt pack |
| `DATA_NOT_DECLARED` | Không cần, không khai báo, nhưng probe có dòng | Dữ liệu còn lại của connector đã tắt; thường bỏ qua |
| `NOT_NEEDED` | Còn lại (không pack đang bật nào cần) | — |

## Thêm hoặc đổi

- **Connector mới:** thêm khối dòng vào `connector_capabilities.csv` (cùng lúc thêm package, dòng `modules.yaml` và `enabled_connectors`).
- **Khả năng mới:** thêm dòng `capability_catalog.csv` cho từng module cần nó và một probe trong `mart_capabilities.sql`.
- **Pack mới cần khả năng:** thêm dòng `capability_catalog.csv` với `required_by` là id pack.
