---
phase: 7
title: "Khai báo connector cung cấp gì + mart_capabilities (khai báo / bật / quan sát được)"
status: pending
priority: P2
effort: "0.5d"
dependencies: [2]
---

# Phase 7: Khả năng của connector

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` §5.1 (hợp đồng connector có thêm "khai báo khả năng"), §8 (pack cần khả năng nào), mục mới về `mart_capabilities` trong §11 hoặc §monitoring; `orchestration/connectors/README.md` (thêm connector mới thì thêm dòng vào `connector_capabilities.csv`); README mới `transformation/seeds/capabilities/README.md` (nghĩa từng khả năng, cách đo "quan sát được"); `transformation/AGENTS.md`.

## Mục tiêu

Trả lời được "doanh nghiệp này có dữ liệu gì" ở 3 mức theo [report-product-design.md](../261013-1751-modularize-data-platform-suite/report-product-design.md) §4 ②: **khai báo** (connector đang bật nói nó cung cấp), **bật** (pack cần khả năng đó đang bật, hoặc khả năng thuộc lõi), **quan sát được** (dữ liệu thật có). Ví dụ roadmap: "bật pack finance nhưng chưa có nguồn giá vốn" hiện thành một dòng trạng thái. Catalog report dùng sau; plan này không làm catalog.

## Thiết kế

### Nơi khai báo: seed sản phẩm, đọc được bởi cả dbt và Python

dbt không đọc được `modules.yaml` hay file Python của connector, còn `mart_capabilities` phải biết khai báo lúc build. Vì vậy khai báo là hai seed CSV do sản phẩm sở hữu (không phải dữ liệu tenant):

- `transformation/seeds/capabilities/connector_capabilities.csv`: `connector_id, capability, note`. `connector_id` dùng **id của `modules.yaml`** (`sapo_v2`, `shopee`, `misa_amis`, `sheets`, `hug`), không dùng tên thư mục dbt (`misa`, `gsheet` khác tên). Mỗi connector là một khối dòng liền nhau: đây là "manifest theo connector" ở dạng dbt đọc được.
- `transformation/seeds/capabilities/capability_catalog.csv`: `capability, required_by, description_vi`. `required_by` là `core` hoặc id pack; một khả năng nhiều pack cần thì nhiều dòng. Khoá `(capability, required_by)`.
- Biến dbt `enabled_connectors` trong `dbt_project.yml` (rule `module-config` mở rộng: bằng `connectors` của `modules.yaml`).
- pytest (`scripts/tests/`): mọi `connector_id` là một package trong `orchestration/connectors/`; mọi `required_by` là `core` hoặc thư mục trong `orchestration/packs/`; mọi `capability` của `connector_capabilities` có trong catalog.

### Danh sách ban đầu (bản xem trước; probe phải kiểm lại cột khi code)

| Khả năng | Connector khai báo | `required_by` | Probe "quan sát được" (relation, điều kiện) |
|---|---|---|---|
| `orders` | sapo_v2 | core | `std_orders` có dòng |
| `order_items` | sapo_v2 | core | `std_order_items` |
| `customers` | sapo_v2 | core | `std_customers` |
| `products` | sapo_v2 | core | `std_variants` |
| `returns` | sapo_v2 | core | `std_order_returns` |
| `payments` | sapo_v2 | core | `std_payments` |
| `fulfillments` | sapo_v2 | core | `std_fulfillments` |
| `staff` | sapo_v2 | core | `std_accounts` |
| `inventory` | sapo_v2 | core | `std_inventory_movements` |
| `cogs_moving_avg` | sapo_v2 | finance | `std_inventory_movements.cogs_amount IS NOT NULL` (cột ở `cdm/staging/std_inventory_movements.sql:55`) |
| `purchase_price` | sapo_v2 | finance | `std_variant_prices` với `price_list_code = 'GIANHAP'` [UNVERIFIED: mã bảng giá nhập là riêng Sapo của Fine Japan hay mặc định Sapo] |
| `marketplace_fees` | shopee | finance, marketplace | `stg_shopee_order_service_fees` có dòng |
| `platform_discount` | shopee | finance | `stg_shopee_order_revenue` [UNVERIFIED: tên cột giảm giá do sàn chịu] |
| `gl` | misa_amis | finance | `std_misa_account_ledger` |
| `cogs_accounting` | misa_amis | finance | `std_misa_sales_lines.cogs_amount IS NOT NULL` (`cdm/staging/std_misa_sales_lines.sql:51`) |
| `targets` | sheets | core | `std_targets` |
| `marketing_spend` | sheets | core | `std_marketing_spend` |
| `teams` | sheets | core | `std_teams` |
| `hug_scans` | hug | hug | `src_hug_scan` (connector `hug` chỉ có `src_*`: `models/connectors/hug/staging/`) |

Nguồn của pack `crm` (`crm_export.*`) là dữ liệu do chính pack ghi, không phải connector, nên không vào danh sách. Seed tenant (ngân sách, giá US shipment) không phải khả năng của connector.

### Model `mart_capabilities`

- Vị trí `transformation/models/monitoring/mart_capabilities.sql`, bucket `monitoring` (được đọc mọi module theo ma trận `check_boundaries.py:149`), `materialized='table'`, không `location` (không lên serving, không tạo thư mục rolling).
- Probe viết **một lần** trong model dưới dạng dict Jinja hằng `{capability: {model, where}}` và một vòng lặp sinh `UNION ALL`; `ref()` trên literal nên lineage tĩnh. Probe chỉ đọc `connector`/`cdm`, không đọc pack (pack có thể tắt). Khả năng có trong catalog mà không có probe → lỗi biên dịch.
- Grain một dòng mỗi `capability`. Cột: `capability`, `required_by` (danh sách), `declared_by` (danh sách connector đang bật khai báo), `is_declared`, `is_pack_enabled` (có `core` hoặc có pack trong `enabled_packs`), `observed_rows`, `last_observed_date` (nếu probe có cột ngày), `is_observed` (`observed_rows > 0`), `status` ∈ {`OK`, `NOT_NEEDED` (không pack nào đang bật cần), `PACK_ON_NO_SOURCE` (pack bật, không connector nào khai báo), `DECLARED_NO_DATA`, `DATA_NOT_DECLARED`}. Không có cột thời điểm build, nên kết quả tất định.
- Test: `unique` + `not_null` trên `capability`; `accepted_values` trên `status`.
- `model_buckets.yaml`: `mart_capabilities: monitoring`.

## Files

- Create: `transformation/seeds/capabilities/{connector_capabilities,capability_catalog}.csv`, `_capabilities__seeds.yml` (mô tả, `column_types`, test khoá), `README.md`; `transformation/models/monitoring/mart_capabilities.sql` + properties YAML; test pytest.
- Modify: `transformation/dbt_project.yml` (var `enabled_connectors`), `scripts/checks/check_boundaries.py` (rule `module-config` thêm connectors), `scripts/checks/model_buckets.yaml`, tài liệu ở khối đầu.

## Verification

- **Gate M `--allow-new`**: golden 83/83 (không đụng model cũ); compiled SQL của model cũ giống hệt; inventory chỉ có node mới.
- Trên lake-B: mọi khả năng của connector đang bật có `is_observed = true`; dòng nào không đạt thì ghi lý do vào báo cáo phase (vd. dữ liệu theo mùa) thay vì sửa probe cho đẹp.
- Bước 6b (lõi trần): `mart_capabilities` build được; các khả năng chỉ finance cần ra `NOT_NEEDED`.
- Thử nhanh trên shadow: build với `--vars '{enabled_connectors: [sapo_v2, shopee, sheets, hug]}'` → `gl`, `cogs_accounting` ra `PACK_ON_NO_SOURCE` (finance bật, MISA tắt). Đây là phép thử cho thông báo "bật pack finance nhưng chưa có nguồn".

**Đổi số:** không.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Probe trên bảng lớn làm nightly chậm | Chỉ `count(*)`/`max(date)`; đo thời gian model trong `run_results.json`, chấp nhận khi < 10 s |
| Danh sách khả năng là đoán | Ghi rõ "bản xem trước" trong README seed; catalog report sẽ sửa khi định nghĩa `requires`/`enhances` |

## Rollback

`git revert`. Bảng `mart_capabilities` và 2 seed còn trong warehouse: vô hại, xoá khi tiện.
