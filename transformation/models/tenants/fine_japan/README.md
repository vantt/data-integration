# Tenant `fine_japan` (dbt)

Phần dbt **chỉ riêng Fine Japan**. Nguyên tắc chia (user chốt 14/10/2026): logic là sản phẩm (pack), dữ liệu và cấu hình là của doanh nghiệp (tenant). CRM, HUG, tài chính và kịch bản bán hàng là pack (`models/packs/`); ở đây chỉ còn **US shipment**. Kiến trúc và danh sách hook: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 10.

## US shipment

Đơn "CrossBorder" của Fine Japan: khách Việt nhận hộ hàng gửi từ Mỹ, giá bán thực theo bảng giá US Shipment (Google Sheet), khác giá trên đơn Sapo.

| Model | Layer | Đọc | Dùng ở |
|---|---|---|---|
| `stg_us_shipment_prices` | staging (view) | source `gsheet_raw.us_shipment_prices_raw` | Trong tenant |
| `int_us_shipment_line_prices` | intermediate, thư mục `us_shipment/` (tag `int`, `us_shipment`) | `fact_orders`, `dim_channels`, `std_order_items` | Trong tenant |
| `fact_us_shipment_economics` | marts (rolling, serving) | các model trên | App CRM (tab tài chính của đơn), `mart_data_quality` |

Bảng giá được sensor `ingest_sheets_modified_sensor` theo dõi (URL ở [orchestration/tenants/fine_japan/config.py](../../../../orchestration/tenants/fine_japan/config.py)) và nạp bởi connector `sheets`.

## Seed của tenant

`transformation/seeds/tenants/fine_japan/` chứa dữ liệu doanh nghiệp mà pack và lõi dùng: `seed_action_scenario_registry` (pack `sales_playbook`), `seed_cashflow_budget`, `seed_cash_allocation_policy` (pack `finance`, do job Google Sheet ghi qua `seed_path`), `seed_channel_targets`, `seed_sku_alias_manual`, `seed_sku_regimen_config` (lõi). `+column_types` của `seed_action_scenario_registry` nằm dưới khoá `tenants: fine_japan:` trong `dbt_project.yml`.

Ba seed lõi đọc (`seed_channel_targets`, `seed_sku_alias_manual`, `seed_sku_regimen_config`) là **bản ghi đè của Fine Japan** cho seed mặc định rỗng của lõi ở [`transformation/seeds/defaults/`](../../../seeds/defaults/README.md). Lõi đọc chúng qua `tenant_ref('<seed>')`: biến dbt `tenant: fine_japan` (`dbt_project.yml`, khớp `tenants:` trong `orchestration/config/modules.yaml`) chọn bản Fine Japan; không có tenant thì lõi đọc bản mặc định 0 dòng. Tiêu đề ba file này phải trùng từng cột với bản mặc định (`check_boundaries.py`, luật `tenant-seed-contract`): thêm hay đổi cột thì sửa cả hai và `+column_types` của bản mặc định. Thiết kế: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 10.

## Hook (lõi phụ thuộc tenant)

- `mart_data_quality` → `fact_us_shipment_economics`: cạnh `ref`, ghi trong `scripts/checks/boundary_allowlist.yaml`.
- `dim_customers` (nhánh `CROSSBORDER`): **logic hook**, không phải cạnh `ref` (mã nhóm `TYPE_CROSSBORDER`/`CTN00014` và tín hiệu "có đơn kênh `US`" viết trong SQL), nên checker không thấy; ghi ở modules.md mục 10 và [TAXONOMY.md](../../../docs/TAXONOMY.md).
