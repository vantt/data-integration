# Pack `finance` (dbt)

Toàn bộ **chi phí và lợi nhuận**: giá vốn (đối chiếu Sapo và MISA), dòng chi phí theo đơn, lợi nhuận đơn/khách/SKU, phân bổ chi phí chung, sổ cái và dòng tiền, ngân sách dòng tiền. Lõi chỉ giữ doanh thu: chỉ có lõi thì xem doanh thu, bật pack finance thì xem thêm lợi nhuận. Lý do (user chốt 14/10/2026): không phải connector nào cũng có giá vốn (sàn, Pancake, Haravan không quản lý kho), và chọn/đối chiếu nguồn giá vốn là logic kế toán chi phí. Pack là sản phẩm dùng lại được; Fine Japan là doanh nghiệp đầu tiên bật dùng. Kiến trúc: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 8.

**Cho ai:** kế toán, tài chính, ban điều hành (P&L kênh, dòng tiền, ngân sách); lõi (`dim_customers`, các mart sản phẩm) đang đọc một số cột lợi nhuận qua hook.

## Đầu vào

| Nguồn | Ghi chú |
|---|---|
| `cdm`: `std_misa_sales_lines`, `std_misa_account_ledger`, `std_inventory_movements`, `std_order_items`, `std_order_discount_items`, `std_fulfillments` | Tầng chuẩn |
| `core`: `fact_orders`, `fact_sales`, `fact_order_returns`, `fact_inventory_movements`, `int_return_sku_lines`, `dim_products`, `dim_channels` | Doanh thu và tồn kho của lõi |
| Connector `misa` (`src_misa_account_ledger`), khai báo trong `pack_connectors` | Sổ cái MISA |
| Connector `shopee` (`stg_shopee_order_revenue`, `stg_shopee_order_service_fees`) và pack `marketplace` (`int_shopee_order_fees`) | Phí sàn; ngoài `pack_connectors`, ghi trong allowlist |
| Source `gsheet_raw.overhead_account_classification_raw` | Phân loại tài khoản chi phí chung (Google Sheet); ghi trong allowlist |
| Seed `seed_cashflow_budget`, `seed_cash_allocation_policy` (`seeds/tenants/fine_japan/`), `ref_gl_accounts` (`seeds/taxonomy/`) | Ngân sách và chính sách phân bổ tiền thừa của tenant (job Google Sheet 02:30 ghi qua `seed_path`) |

## Đầu ra

| Nhóm | Model |
|---|---|
| Giá vốn (`intermediate/cogs/`, `marts/sales/`) | `int_order_cogs_reconciled`, `int_order_promo_goods_cost`, `int_promo_642_monthly_total` (đối soát TK 642, chưa model nào đọc), `mart_order_cogs_summary` |
| Chi phí và lợi nhuận (`marts/sales/`, `marts/intermediate/`) | `fact_order_costs`, `fact_order_economics`, `int_customer_economics`, `mart_sku_economics_monthly` |
| Chi phí chung (`staging/`, `intermediate/overhead/`) | `stg_overhead_account_classification`, `int_overhead_pool_monthly`, `int_order_overhead_allocation` |
| Kế toán MISA (`intermediate/misa/`, `marts/`) | `int_misa_sales_lines`, `dim_gl_account`, `fact_account_balance_monthly`, `fact_cash_movement` |
| Dòng tiền và ngân sách (`marts/`) | `fact_cashflow_budget`, `dim_cash_allocation_policy`, `mart_cashflow_budget_vs_actual`, `mart_cashflow_forecast`, `mart_cashflow_reserve_status`, `mart_cashflow_unmapped_actuals`, `mart_cash_surplus_allocation` |

Mart dùng ở Metabase (`docs/analytics-handbook/domains/finance.md`, blueprint `finance_cashflow_budget.md`) và app CRM (`fact_order_costs`, `fact_order_economics`, `int_order_cogs_reconciled`, `int_order_promo_goods_cost` ở tab tài chính của đơn). Tên relation không đổi khi dời vào pack.

## Cấu hình

- Biến dbt `cogs_primary_source` (`sapo_mac` mặc định, hoặc `misa`): nguồn giá vốn chính của `int_order_cogs_reconciled`.
- Ngân sách: Google Sheet Budget Matrix, đồng bộ bởi `budget_sheet_sync_asset` (connector `sheets`) vào hai seed của tenant.

## Phần còn là dữ liệu Fine Japan

- Seed ngân sách và chính sách phân bổ, bảng phân loại tài khoản chi phí chung (Google Sheet), hệ tài khoản và cách gom dòng tiền (TAXONOMY.md, nhóm "Thời gian, kế toán, chi phí").
- Từ khoá giảm giá và tên chương trình Shopee trong `fact_order_costs` (TAXONOMY.md mục 6).

## Lõi đọc gì từ pack này

Lõi chỉ đọc pack qua `pack_ref('finance', '<model>')`; danh sách cột và kiểu là hợp đồng trong `pack_contracts()` ([transformation/macros/packs/pack_contracts.sql](../../../macros/packs/pack_contracts.sql)), mỗi model gắn test `pack_contract` nên đổi tên hay kiểu một cột trong hợp đồng làm build lỗi. Thiết kế và giá trị khi tắt pack: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 7 và 8.1.

`mart_sku_economics_monthly` đọc doanh số SKU-tháng từ model lõi `int_sku_sales_monthly` (cùng tập dòng, giữ nguyên giá trị) và chỉ tính giá vốn/biên; doanh số, tốc độ bán và trả hàng thuộc lõi nên vẫn có khi tắt finance.

| Model của pack | Lõi đọc | Cột | Khi tắt finance |
|---|---|---|---|
| `int_customer_economics` | `dim_customers` | 10 cột lợi nhuận/giá vốn/trả hàng + `customer_key` | Các cột đó NULL (không `COALESCE` về 0) |
| `int_misa_sales_lines` | `dim_sku_alias` | `product_code`, `is_promo_line`, `is_service_line` | Không có alias tự động VTS → VCS |
| `fact_order_economics` | `mart_data_quality` | `has_cogs`, `has_platform_fees` (và số đơn) | `total_orders` 0, hai tỷ lệ NULL |
| `mart_sku_economics_monthly` | `mart_product_health` | `product_key`, `snapshot_month`, `realized_margin_pct`, `cogs_variance_pct`, `margin_outlier`, `cogs_source` | 4 cột biên NULL, `has_margin_data` FALSE, `health_class` NULL |

## Phụ thuộc chéo (ghi trong `scripts/checks/boundary_allowlist.yaml`)

| Cạnh | Loại |
|---|---|
| `fact_order_economics` → `int_shopee_order_fees` (pack `marketplace`) | Pack → pack |
| `mart_hug_attribution` (pack `hug`) → `fact_order_economics` | Pack → pack |
| `fact_order_costs` → `stg_shopee_order_revenue`, `stg_shopee_order_service_fees` | Pack → connector ngoài `pack_connectors` |

Ghi lại, chưa sửa: `fact_order_costs` đang coi giảm giá là một dòng chi phí, về nghĩa thuộc phía doanh thu.
