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

## Phụ thuộc chéo (ghi trong `scripts/checks/boundary_allowlist.yaml`)

| Cạnh | Loại |
|---|---|
| `dim_customers` → `int_customer_economics` (`lifetime_gross_profit`, `lifetime_contribution_margin`) | Pack hook |
| `int_product_velocity_trend`, `mart_inventory_health` → `mart_sku_economics_monthly` (chỉ tốc độ bán) | Pack hook |
| `mart_product_health`, `mart_product_action_queue` → `mart_sku_economics_monthly` (`realized_margin_pct`, `cogs_variance_pct`, `margin_outlier`) | Pack hook |
| `mart_data_quality` → `fact_order_economics` | Pack hook (kiểm tra chất lượng dữ liệu) |
| `dim_sku_alias` → `int_misa_sales_lines` | Pack hook (có từ trước) |
| `fact_order_economics` → `int_shopee_order_fees` (pack `marketplace`) | Pack → pack |
| `mart_hug_attribution` (pack `hug`) → `fact_order_economics` | Pack → pack |
| `fact_order_costs` → `stg_shopee_order_revenue`, `stg_shopee_order_service_fees` | Pack → connector ngoài `pack_connectors` |

Hướng thoát sau Đợt 1: tách `mart_sku_economics_monthly` thành phần doanh số/tốc độ bán (lõi) và phần chi phí/biên (finance); cột biên đọc qua `pack_ref`. Ghi lại, chưa sửa: `fact_order_costs` đang coi giảm giá là một dòng chi phí, về nghĩa thuộc phía doanh thu.
