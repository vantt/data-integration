# ADR-017: Pack và tenant: logic là pack, dữ liệu/cấu hình là tenant

> **Trạng thái:** Accepted
> **Ngày:** 2026-10-14
> **Tham chiếu:** [`docs/architecture/modules.md` mục 8, 10](../architecture/modules.md#8-packs-), [`orchestration/packs/README.md`](../../orchestration/packs/README.md), [`orchestration/tenants/fine_japan/README.md`](../../orchestration/tenants/fine_japan/README.md), [`transformation/models/tenants/fine_japan/README.md`](../../transformation/models/tenants/fine_japan/README.md), [`scripts/checks/boundary_allowlist.yaml`](../../scripts/checks/boundary_allowlist.yaml), [ADR-015](./015-module-boundaries.md)

## Bối cảnh

Sau khi tách connector, cdm và core ([ADR-015](./015-module-boundaries.md)), phần còn lại của suite (CRM, HUG, tài chính, kịch bản bán hàng, US shipment) cần được xếp chỗ. Bản kế hoạch đầu đặt cả khối này vào "tenant overlay Fine Japan". Ngày 14/10/2026 user chốt lại: phần lớn khối này là **sản phẩm** dùng được cho doanh nghiệp khác, không phải đặc thù Fine Japan. Đồng thời cần một tiêu chí rõ để xếp các model chi phí (giá vốn, phí sàn, lợi nhuận) giữa lõi và pack, vì không phải nguồn nào cũng có giá vốn (sàn, Pancake, Haravan không quản lý kho).

## Quyết định

### 1. Logic là pack, dữ liệu và cấu hình là tenant

- **Pack** = logic sản phẩm dùng lại được, không phụ thuộc ngành: `transformation/models/packs/<id>/` và (nếu có code Dagster) `orchestration/packs/<id>/`, khai báo ở `packs:` của `orchestration/config/modules.yaml`. Pack: `crm`, `hug` (nối lại khách từ sàn về mua trực tiếp với shop), `finance`, `sales_playbook` (thử nghiệm, chưa chuẩn hoá), cùng `marketplace`, `facebook_*` (chỉ dbt).
- **Tenant** = dữ liệu và cấu hình của một doanh nghiệp: `transformation/seeds/tenants/<t>/` (6 seed Fine Japan), `orchestration/tenants/<t>/config.py` (endpoint CRM, đọc qua `orchestration.tenants.setting(name)`: env cùng tên ghi đè, thiếu thì `TenantConfigError`), và biến môi trường.
- **Chỉ US shipment là riêng Fine Japan**: 3 model `stg_us_shipment_prices`, `int_us_shipment_line_prices`, `fact_us_shipment_economics` ở `transformation/models/tenants/fine_japan/`.

### 2. Lõi giữ doanh thu, pack finance giữ chi phí và lợi nhuận

Nguyên tắc: **số liệu do nguồn cung cấp thuộc lõi; chọn, đối chiếu, tính chi phí thuộc pack finance.**

| Lõi (`core`) | Pack `finance` |
|---|---|
| Doanh thu, đơn, khách, sản phẩm, tồn kho | Giá vốn: `int_order_cogs_reconciled`, `int_order_promo_goods_cost`, `int_promo_642_monthly_total`, `mart_order_cogs_summary` |
| `fact_inventory_movements.cogs_amount` / `moving_avg_cost` (định giá kho bình quân do Sapo cung cấp, nghiệp vụ kho) | Chi phí và lợi nhuận: `fact_order_costs`, `fact_order_economics`, `int_customer_economics`, `mart_sku_economics_monthly` |
| `dim_price_lists`, `fact_variant_prices_snapshot` (giá nhập do nguồn cung cấp) | Chi phí chung, MISA, sổ cái, dòng tiền, ngân sách (22 model) |

Chỉ có lõi thì xem được doanh thu; bật finance thì xem thêm lợi nhuận.

### 3. Connector lấy dữ liệu, pack dùng dữ liệu, gặp nhau ở `std_*`

Pack đọc `cdm`, `core` và chính nó. Ngoại lệ có khai báo trong `pack_connectors` của `scripts/checks/model_buckets.yaml`: `finance → misa`, `marketplace → shopee`, `hug → hug`, `facebook_* → facebook_*`. Pack đọc seed tenant là đúng thiết kế (pack logic, tenant dữ liệu); lõi thì không (luật `dbt-seed`).

### 4. Hook lõi → pack/tenant: allowlist ngay, `pack_ref` sau Đợt 1

Chỗ lõi còn đọc pack hoặc tenant được giữ nguyên (không đổi số) và ghi thành mục allowlist có lối ra:

| Hook | Cạnh (sinh từ manifest) | Lối ra sau Đợt 1 |
|---|---|---|
| Lõi → finance | `dim_customers` → `int_customer_economics`; `mart_data_quality` → `fact_order_economics`; `dim_sku_alias` → `int_misa_sales_lines` | `pack_ref('finance', ...)`: cột rỗng/NULL khi tắt finance |
| Lõi → finance qua `mart_sku_economics_monthly` | `int_product_velocity_trend`, `mart_inventory_health` (chỉ dùng tốc độ bán); `mart_product_health`, `mart_product_action_queue` (`realized_margin_pct`, `cogs_variance_pct`, `margin_outlier`) | **Tách đôi** `mart_sku_economics_monthly`: phần doanh số/tốc độ bán theo SKU về lõi, phần giá vốn/biên ở finance; hai mart sản phẩm lấy cột biên qua `pack_ref` |
| Lõi → crm | `dim_staff` → `stg_crm__app_user` (`crm_user_id`) | `pack_ref('crm', ...)` |
| Lõi → tenant | `mart_data_quality` → `fact_us_shipment_economics` | Dời check US vào tenant |
| Lõi → seed tenant (`dbt-seed`) | `dim_channel_targets` → `seed_channel_targets`; `int_customer_sku_supply_tracking` → `seed_sku_regimen_config`; `dim_sku_alias` → `seed_sku_alias_manual` | Lõi có seed mặc định rỗng đúng cột, tenant ghi đè (cùng `pack_ref`) |
| Pack → pack (khai báo) | `mart_hug_attribution` → `fact_order_economics`; `fact_order_economics` → `int_shopee_order_fees`; `sales_playbook` → `crm` (3 cạnh) | Khai báo phụ thuộc pack + `pack_ref` |

`pack_ref(pack, model, columns)` (macro, sau Đợt 1): trả `ref()` khi pack bật, bảng rỗng đúng cột khi tắt; danh sách pack bật lấy từ `modules.yaml` qua biến dbt `enabled_packs`. Ngoài ra `mart_customer_tier` (đọc `lifetime_contribution_margin` qua `dim_customers`) và hai cột `implied_gross_margin_pct`, `is_below_cost` của `fact_variant_prices_snapshot` nằm trong danh sách xử lý cùng đợt này. Nhánh `CROSSBORDER` của `dim_customers` (mã nhóm `CTN00014` + kênh `US` viết trong SQL) là **logic hook**, không phải cạnh `ref`, nên không có trong allowlist; xử lý cùng bộ máy phân loại ([ADR-016](./016-taxonomy-module.md)).

### 5. Orchestration: `crm_cache_refresh` vẫn được connector import, có allowlist

Job của bốn connector `sapo_v2`, `shopee`, `misa_amis`, `sheets` chọn asset `crm_cache_refresh` bằng cách import `orchestration.packs.crm` (user giữ import, 14/10). Mỗi file là một mục `orch-import` trong allowlist; `sales_playbook` import `crm` là mục thứ năm. Lối ra sau Đợt 1: pack crm tự đăng ký refresh sau các job connector (đảo chiều). Hệ quả: **chưa tắt được pack** bằng cách bỏ khỏi `modules.yaml`.

### 6. Cấu hình Fine Japan: mỗi giá trị khai báo một nơi, không có mặc định trong code

- **URL Google Sheet** (6: `TARGETS`, `MARKETING_SPEND`, `US_SHIPMENT_PRICES`, `TEAM_CONFIG`, `OVERHEAD_CLASSIFICATION`, `BUDGET`): chỉ ở biến môi trường `SOURCES__SPREADSHEET_URL__<NAME>` (tên trong `.env.docker.example`). Reader `ingestion/src/gsheet_*.py`, `gsheet_budget_sync` và `sensors/sheets_modified_sensor.py` đọc cùng biến qua `spreadsheet_url(name)` (`ingestion/src/gsheet_auth.py`); thiếu biến thì lỗi nêu tên biến **lúc dùng**, Dagster definitions vẫn load. Ingestion không import `orchestration.tenants`. URL mặc định trong reader và bản sao `SHEETS_SENSOR_*_URL` trong tenant config đã bỏ.
- **Endpoint CRM** (`CRM_REFRESH_URL`, `CRM_BACKUP_URL`, `CRM_DRILL_URL`, `APPROACH_SCRIPT_LOAD_URL`): `orchestration/tenants/fine_japan/config.py`, vì luật `pack-url` cấm URL trong pack.
- **Domain Sapo, `login_url`, worker URL**: giữ ở `ingestion/.dlt/config.toml` (user quyết định 14/10), ghi nhận là cấu hình Fine Japan trong README tenant.

## Hệ quả

- Doanh nghiệp thứ hai dùng lại pack, chỉ cần dữ liệu và cấu hình riêng; phần riêng Fine Japan trong dbt chỉ còn 3 model.
- Ranh giới đã hiện hình nhưng chưa tắt được pack: lõi còn 8 pack hook + 1 tenant hook + 3 seed hook, connector còn import pack crm. Tất cả đều trong allowlist với lối ra.
- Thiếu một URL hoặc endpoint là lỗi rõ ràng (fail closed), không còn âm thầm dùng giá trị của Fine Japan.
- Tên relation, schema, asset key, job không đổi (gate M chứng minh), nên CRM, Metabase, Evidence đọc như cũ.

## Alternatives Rejected

- **Đặt CRM, HUG, finance, kịch bản bán hàng vào tenant Fine Japan** (kế hoạch đầu): khoá logic dùng lại được vào một doanh nghiệp.
- **Giữ COGS và lợi nhuận ở lõi** (quyết định 13/10): lõi sẽ phụ thuộc nguồn có giá vốn; nhiều nguồn không có.
- **Thêm `shopee` vào `pack_connectors` của finance** để bỏ hai mục allowlist `fact_order_costs → stg_shopee_*`: nới luật; chọn allowlist, lối ra là dời phần phí sàn về pack `marketplace`.
- **Tắt pack bằng `enabled: false` ngay trong Đợt 1**: hook của lõi sẽ gãy; cần `pack_ref` trước.
- **Đặt URL Google Sheet trong `orchestration/tenants/fine_japan/config.py`**: ingestion không được import orchestration, nên reader và sensor sẽ giữ hai bản; env là nơi duy nhất cả hai đọc được.

## Khi nào xem xét lại

- Khi làm cơ chế pack (`pack_ref`, `enabled_packs`, khai báo "connector cung cấp gì"), ngay sau Đợt 1: gỡ các mục hook, tách `mart_sku_economics_monthly`, đảo chiều `crm_cache_refresh`.
- Khi chuẩn hoá CRM, HUG, finance thành sản phẩm (plan riêng).
- Khi có `tenant.yaml` (Đợt 5) thay `modules.yaml`: cấu hình tenant và tên biến môi trường có thể gom về đó.
