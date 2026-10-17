# Spike: cơ chế bật/tắt pack trong dbt

Ngày 14/10/2026 (ICT), phase 1 của plan [261014-2225-pack-mechanism](../plan.md).

## Môi trường

- dbt-core 1.11.12, dbt-duckdb 1.10.1, duckdb 1.5.5, dbt-extractor 0.6.0 (image prod `fg-dataware-house-data_platform:latest`, khớp `ingestion/requirements.txt:15-16`).
- Chạy bằng `scripts/shadow/run-shadow.sh` (không mạng, không secret), code từ worktree nháp `/home/vantt/app/fg-dw-spike` (detached tại `8eb9920f`, đã xoá sau spike), dữ liệu từ lake nháp `lake-S` (clone `lake-base`, đã xoá sau spike).
- Thay đổi nháp: thêm `vars.enabled_packs` và `+enabled` cho 7 thư mục `models/packs/<pack>` trong `dbt_project.yml`; macro `pack_ref(pack, model, columns)`; đổi 8 hook lõi (`dim_customers`, `dim_staff`, `dim_sku_alias`, `mart_data_quality`, `mart_product_health`, `mart_product_action_queue`, `mart_inventory_health`, `int_product_velocity_trend`) sang `pack_ref`; 2 model thăm dò (`spike_pack_ref_probe`, `spike_empty_rel_probe`) và 2 seed thăm dò.

Macro dùng trong spike:

```jinja
{% macro pack_ref(pack, model, columns) %}
  {%- if pack in var('enabled_packs', []) -%}
    {{ return(ref(model)) }}
  {%- else -%}
    {%- set cols = [] -%}
    {%- for name, type in columns.items() -%}
      {%- do cols.append('CAST(NULL AS ' ~ type ~ ') AS ' ~ name) -%}
    {%- endfor -%}
    {{ return('(SELECT ' ~ cols | join(', ') ~ ' WHERE FALSE)') }}
  {%- endif -%}
{% endmacro %}
```

## Kết quả tóm tắt

| # | Câu hỏi | Kết quả |
|---|---|---|
| a | `ref()` trong `if` cho lineage khi đúng, không tạo cạnh khi sai | **Đạt** |
| b | `+enabled` theo biến tắt cả thư mục pack, `config.enabled` là bool | **Đạt, có điều kiện**: `var()` trong `dbt_project.yml` **không thấy** khối `vars:` của chính file đó, phải có tham số mặc định (xem dưới) |
| c | Test đơn lẻ trỏ model đã tắt | **Đạt**: dbt tự tắt test, không lỗi, **không in cảnh báo** |
| d | Seed chỉ có tiêu đề + `+column_types` | **Đạt**: 0 dòng, đúng kiểu. Thiếu `column_types` thì mọi cột thành `INTEGER` |
| e | Quan hệ rỗng dùng được trong `JOIN`/`LEFT JOIN`/subquery | **Đạt** |
| f | Đổi `--vars` làm dbt parse lại toàn bộ | **Đạt** |
| g | `vars` danh sách trong `dbt_project.yml` bị `--vars` ghi đè | **Đạt** trong ngữ cảnh model; xem (b) cho ngữ cảnh `dbt_project.yml` |

Thêm: khi pack bật, `pack_ref` compile ra SQL **giống hệt** `ref()` (8/8 model hook, so `compiled_code` sau chuẩn hoá khoảng trắng với manifest của lake-A). Cạnh pack → pack tới pack đã tắt làm parse lỗi rõ (fail closed).

## Chi tiết

### (b) `+enabled` theo biến, và giới hạn của `vars` trong `dbt_project.yml`

Lần đầu khai báo `+enabled: "{{ ('finance' in var('enabled_packs')) | as_bool }}"` cùng `vars: enabled_packs: [crm, hug, finance, ...]` trong `dbt_project.yml`, `dbt parse` không có `--vars` lỗi:

```text
Compilation Error
  Could not render {{ ('finance' in var('enabled_packs')) | as_bool }}: Required var 'enabled_packs' not found in config:
  Vars supplied to <Configuration> = {}
```

Config trong `dbt_project.yml` được render lúc nạp project, khi đó chỉ có biến từ `--vars`. Khối `vars:` của project chỉ có hiệu lực trong ngữ cảnh model/macro. Hai cách đã thử đều chạy:

- Có `--vars '{enabled_packs: [...]}'`: parse được (rc 0).
- Thêm mặc định: `+enabled: "{{ ('finance' in var('enabled_packs', ['crm', 'hug', 'finance', 'sales_playbook', 'marketplace', 'facebook_ads', 'facebook_messenger'])) | as_bool }}"`: parse không cần `--vars` (rc 0), `--vars` vẫn ghi đè.

Manifest (đếm model `enabled` theo thư mục `models/packs/<pack>`):

| Lệnh | Model bật | Model pack bật | `int_customer_economics.config.enabled` |
|---|---|---|---|
| không `--vars` (mặc định) | 173 | finance 22, crm 14, hug 5, marketplace 3, sales_playbook 3 | `True` (bool) |
| `--vars '{enabled_packs: [crm, sales_playbook, marketplace]}'` | 146 | crm 14, marketplace 3, sales_playbook 3 | `False` (bool, trong `disabled`) |
| `--vars '{enabled_packs: []}'` | 126 | không có | `False` (bool) |

`dbt ls --resource-type model` với finance tắt không còn model nào của `models/packs/finance`.

Ghi chú:

- `facebook_ads`, `facebook_messenger` (2 model mỗi pack) **đã tắt sẵn ở baseline** bằng config trong model; `+enabled: true` theo thư mục không bật lại (config trong model thắng). Manifest baseline có 10 model tắt sẵn (6 ở `connectors/`, 4 ở hai pack facebook).
- Cảnh báo "12 unused configuration paths" có sẵn ở baseline (do anchor `*layer_intermediate` gắn `shopee/misa/us_shipment` vào mọi module); tắt pack không làm tăng con số này.
- Config đã resolve của model pack khi bật không đổi so với baseline (`dbt_inventory.py diff` không báo khác biệt config nào, chỉ checksum của 8 file hook).

**Hệ quả cho phase 2 (cần chọn một):**

1. **Mặc định lặp trong từng `+enabled`** (7 dòng), giữ `vars.enabled_packs` cho `pack_ref`; check đồng bộ `modules.yaml` ↔ `vars.enabled_packs` ↔ danh sách mặc định trong từng `+enabled` (so khớp nguyên chuỗi với mẫu sinh ra, lỗi in sẵn khối cần dán). Đã chạy được trong spike; ít file nhất. **Đề xuất.**
2. Đảo nghĩa thành `disabled_packs` mặc định `[]`: không lặp danh sách, nhưng đổi tên biến và profile "lõi trần" (`--vars '{disabled_packs: [...]}'`) khác plan.
3. Phương án dự phòng của phase 1: `config(enabled=pack_enabled('<pack>'))` trong từng model pack (~50 file); ngữ cảnh model thấy `vars:` của project nên chỉ có một nguồn, đổi nhiều file.
4. Luôn truyền `--vars` (container start, Dagster, `run-all.sh`): loại, vì phải đổi mọi lời gọi dbt trên prod.

### (a) `ref()` trong `if`: lineage đúng theo biến

`spike_pack_ref_probe` gọi `pack_ref('finance', 'int_customer_economics', {...})`.

| Lệnh parse | `depends_on.nodes` của probe | `dim_staff` (hook crm) |
|---|---|---|
| không `--vars` | `dim_customers_base`, `int_customer_economics` | `std_accounts`, `stg_crm__app_user` |
| `enabled_packs: [crm, sales_playbook, marketplace]` | chỉ `dim_customers_base` | `std_accounts`, `stg_crm__app_user` |
| `enabled_packs: []` | chỉ `dim_customers_base` | chỉ `std_accounts` |

Parse không lỗi khi model pack bị tắt. `refs` trong manifest cũng mất tên model pack khi tắt. `ref()` gọi trong macro vẫn được ghi nhận như gọi trong model.

**Pack → pack fail closed:** `enabled_packs: [crm, hug, sales_playbook, marketplace]` (finance tắt, hug bật) → `dbt parse` rc 2:

```text
Model 'model.sapo_warehouse.mart_hug_attribution' (models/packs/hug/marts/mart_hug_attribution.sql) depends on a node named 'fact_order_economics' which is disabled
```

### (c) Test đơn lẻ trỏ model đã tắt

Không lỗi, không cảnh báo. Node test vẫn nằm trong `manifest.nodes` nhưng `config.enabled = False`, `depends_on.nodes` mất model đã tắt; `dbt ls --resource-type test` không liệt kê nó. Một ref tới model tắt là đủ để tắt test (`assert_overhead_accounts_classified` vẫn ref `std_misa_account_ledger` của lõi nhưng bị tắt vì `stg_overhead_account_classification`).

| Test | finance + hug tắt | mọi pack tắt |
|---|---|---|
| `assert_no_promo_in_overhead_costs` | tắt | tắt |
| `assert_overhead_accounts_classified` | tắt | tắt |
| `assert_overhead_allocation_closure` | tắt | tắt |
| `assert_promo_account_not_in_keep_pool` | tắt | tắt |
| `assert_shopee_no_platform_service_double_count` | tắt | tắt |
| `assert_shopee_net_settlement_matches_total_paid` (ref `int_shopee_order_fees` của marketplace) | bật | tắt |

Generic test trong YAML của pack cũng ở lại `nodes` với `enabled = False` (finance + hug tắt: 390 bật / 74 tắt; mọi pack tắt: 341 / 123; baseline 464 / 0).

**Hệ quả:** phase 2 **không cần** dời 6 file vào `tests/packs/<pack>/`. Vì dbt im lặng, script nào duyệt `manifest.nodes` (`dbt_inventory.py`, `check_boundaries.py`, `dagster_inventory.py`, tải asset check trong Dagster) phải lọc `config.enabled`, hoặc chứng minh đã lọc, trước khi dùng manifest của profile tắt pack (phase 4).

### (d) Seed rỗng

`seeds/spike/seed_x__default.csv` chỉ có dòng tiêu đề, `+column_types` khai báo dưới `seeds: sapo_warehouse: spike: seed_x__default:`. `dbt seed` báo `INSERT 0`; `DESCRIBE main.seed_x__default`: `label VARCHAR, label_std VARCHAR, is_active BOOLEAN, weight DOUBLE, valid_from DATE`, 0 dòng.

Cùng tệp nhưng không có `column_types` (`seed_y_untyped`): 0 dòng, **mọi cột `INTEGER`**. Seed mặc định của `tenant_ref` (phase 5) phải khai báo kiểu cho từng cột.

### (e) Quan hệ rỗng

`spike_empty_rel_probe` (finance tắt) gồm CTE `SELECT * FROM (<rỗng>)`, alias `FROM (<rỗng>) m`, subquery vô hướng `WHERE m.snapshot_month = (SELECT MAX(snapshot_month) FROM (<rỗng>))`, hai `LEFT JOIN` và `COALESCE` vào `dim_customers_base`. `dbt run` OK; bảng 7 737 dòng (bằng `dim_customers_base`), kiểu đúng như khai báo (`gross_margin_pct DOUBLE`, `units_sold BIGINT`, `snapshot_month DATE`). `spike_pack_ref_probe` (view, `LEFT JOIN`) 7 737 dòng, cột finance NULL.

Thử trực tiếp trên warehouse: `JOIN` (inner) với quan hệ rỗng ra 0 dòng; `SUM` ra NULL, `COALESCE(MAX(x), 0)` ra 0, `COUNT(*)` ra 0; `UNION ALL` với seed rỗng chạy được.

Ghi chú: chỗ lõi `JOIN` (inner) hoặc `CROSS JOIN` vào dữ liệu pack sẽ ra 0 dòng khi pack tắt. Rà 8 model hook ở baseline:

- `dim_sku_alias.sql:118` `INNER JOIN misa_codes` (từ `int_misa_sales_lines`): tắt finance thì không có alias VTS→VCS nào. Đúng nghĩa (không có MISA thì không có alias), nhưng phase 3 phải ghi rõ.
- `int_product_velocity_trend.sql:28` `CROSS JOIN latest_month` và `:86` `JOIN first_sale`, cả hai lấy từ `mart_sku_economics_monthly`; `mart_product_health.sql:122` `INNER JOIN int_product_velocity_trend`. Nếu chỉ thay `ref` bằng `pack_ref` thì tắt finance làm `int_product_velocity_trend` rỗng và `mart_product_health` mất mọi dòng. Phase 4 (lõi đọc `int_sku_sales_monthly` của lõi, không đọc pack) xử lý đúng chỗ này; profile "lõi trần" phải kiểm số dòng của hai bảng đó.
- Các `JOIN` inner còn lại (`dim_customers.sql:34`, `mart_data_quality.sql:30`) nối giữa các model lõi, không bị ảnh hưởng.

### (f) Đổi `--vars` làm parse lại toàn bộ

Chuỗi parse liên tiếp trên cùng thư mục `target` (partial parse bật):

| Lần | `--vars` | Log | Model bật |
|---|---|---|---|
| 1 | không | `Unable to do partial parsing because config vars, config profile, or config target have changed` | 173 |
| 2 | `{enabled_packs: []}` | như trên | 126 |
| 3 | `{enabled_packs: [crm, sales_playbook, marketplace]}` | như trên | 146 |
| 4 | như lần 3 | không có (dùng partial parse) | — |
| 5 | không | parse lại toàn bộ | 173 |

Manifest luôn khớp biến mới; không thấy trạng thái lẫn của lần trước.

### (g) `vars` danh sách trong `dbt_project.yml` và `--vars`

Trong ngữ cảnh model (`pack_ref`), `var('enabled_packs')` không `--vars` lấy danh sách của khối `vars:` (probe có cạnh tới `int_customer_economics`); `--vars` ghi đè (probe mất cạnh). Trong ngữ cảnh `dbt_project.yml`, xem (b).

### Compiled SQL khi pack bật

`dbt compile` 8 model hook trên worktree nháp (không `--vars`), so `compiled_code` với manifest lake-A (baseline `8eb9920f`) sau chuẩn hoá khoảng trắng: **8/8 giống hệt** (`dim_customers`, `dim_staff`, `dim_sku_alias`, `mart_data_quality`, `mart_product_health`, `mart_product_action_queue`, `mart_inventory_health`, `int_product_velocity_trend`). `dbt_inventory.py diff` chỉ báo khác checksum của đúng 8 file đó (cần `--allow-code-change`, như phase 3 đã định), không khác config, ref hay relation.

## Ảnh hưởng tới các phase sau

1. Phase 2: chọn cách xử lý mặc định của `+enabled` (đề xuất cách 1 ở mục b); check đồng bộ phải kiểm cả danh sách mặc định trong từng `+enabled`.
2. Phase 2: không dời 6 test đơn lẻ; thay vào đó các script đọc manifest phải lọc `config.enabled` (test bị tắt vẫn ở `nodes`).
3. Phase 3–4: `pack_ref` cho compiled SQL giống hệt khi pack bật; xem lại các `JOIN` inner/`CROSS JOIN` vào dữ liệu pack đã liệt kê ở mục (e) (`dim_sku_alias`, chuỗi `int_product_velocity_trend` → `mart_product_health`).
4. Phase 5: seed `__default` phải có `+column_types` cho mọi cột.
5. Profile "lõi trần" phải tắt cả các pack phụ thuộc (hug khi tắt finance), nếu không parse fail.
