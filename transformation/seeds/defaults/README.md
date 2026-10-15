# Seed mặc định của lõi (`seeds/defaults/`)

Bản **rỗng đúng cột** của các seed tenant mà lõi đọc. Lõi đọc seed tenant chỉ qua macro `tenant_ref('<seed>')` ([macros/tenants/tenant_ref.sql](../../macros/tenants/tenant_ref.sql)): biến dbt `tenant` có giá trị (Fine Japan: `fine_japan`) thì đọc `seeds/tenants/<tenant>/<seed>.csv`; rỗng thì đọc `<seed>__default` ở đây (0 dòng). Thiết kế: [docs/architecture/modules.md](../../../docs/architecture/modules.md) mục 10.

| Seed mặc định | Lõi đọc | Cột (kiểu) | Không có tenant thì | Bản ghi đè Fine Japan |
|---|---|---|---|---|
| `seed_channel_targets__default` | `dim_channel_targets` (`SELECT *`) | `channel_name` varchar, `period_month` date, `metric_type` varchar, `target_value` double, `target_source` varchar, `notes` varchar | `dim_channel_targets` rỗng | [seed_channel_targets.csv](../tenants/fine_japan/seed_channel_targets.csv) |
| `seed_sku_regimen_config__default` | `int_customer_sku_supply_tracking` (`SELECT *`) | `sku` varchar, `product_group` varchar, `display_name` varchar, `supply_days_per_unit` integer, `dose_reduction_buffer` double, `remind_lead_days` integer, `journey_enabled` boolean | không SKU nào được theo dõi | [seed_sku_regimen_config.csv](../tenants/fine_japan/seed_sku_regimen_config.csv) |
| `seed_sku_alias_manual__default` | `dim_sku_alias` (chọn cột) | `sapo_pack_sku` varchar, `sapo_pack_unit` varchar, `sapo_base_sku` varchar, `sapo_base_unit` varchar, `units_per_pack` integer, `misa_join_key` varchar, `misa_qty_multiplier` integer, `notes` varchar | chỉ còn alias tự động | [seed_sku_alias_manual.csv](../tenants/fine_japan/seed_sku_alias_manual.csv) |

## Hợp đồng cột

- Mỗi file chỉ có **dòng tiêu đề**, đúng tên và thứ tự cột của seed tenant.
- Kiểu khai trong `transformation/dbt_project.yml`, khối `seeds: sapo_warehouse: defaults: <seed>__default: +column_types`, cho **mọi** cột (CSV chỉ có tiêu đề mà thiếu kiểu thì dbt-duckdb tạo cột `INTEGER`). Kiểu lấy bằng `DESCRIBE` seed Fine Japan trong warehouse (seed Fine Japan để dbt tự suy kiểu), để model `SELECT *` có cùng kiểu dù chạy với tenant nào. Mô tả và `data_type` từng cột: [_defaults__seeds.yml](_defaults__seeds.yml).
- `check_boundaries.py`, luật `tenant-seed-contract`, fail khi: seed lõi gọi qua `tenant_ref` không có bản mặc định; tenant đang bật (`tenants:` trong `orchestration/config/modules.yaml`) thiếu file seed hoặc tiêu đề khác bản mặc định; `+column_types` của bản mặc định không đúng bằng tập cột tiêu đề.

## Tenant ghi đè thế nào

1. Đặt `seeds/tenants/<tenant>/<seed>.csv` cho **mọi** seed trong bảng trên, dòng tiêu đề chép nguyên từ bản mặc định ở đây, rồi thêm dữ liệu.
2. `tenants: [<tenant>]` trong `orchestration/config/modules.yaml` và `tenant: <tenant>` trong `vars:` của `dbt_project.yml` (luật `module-config`; mỗi triển khai tối đa một tenant).
3. Chạy `scripts/checks/run-all.sh`.

Đổi cột của một seed: sửa cùng lúc bản mặc định, `+column_types` của nó và seed của mọi tenant. Thêm seed lõi đọc mới: thêm bản mặc định, kiểu, dòng trong bảng trên, và gọi bằng `tenant_ref`.

Khi không có tenant, model `external` nào ra 0 dòng (vd. `dim_channel_targets`) được dbt-duckdb ghi thành file parquet một dòng toàn NULL để giữ schema; view trong warehouse lọc dòng đó, serving đọc thẳng file thì thấy (modules.md mục 10).
