# ADR-018: Bật/tắt pack và điểm cắm lõi ↔ pack/tenant

> **Trạng thái:** Accepted
> **Ngày:** 2026-10-15
> **Tham chiếu:** [`docs/architecture/modules.md` mục 4, 5.1, 7, 8.1, 9, 10, 11b](../architecture/modules.md), [`orchestration/packs/README.md`](../../orchestration/packs/README.md), [`transformation/seeds/defaults/README.md`](../../transformation/seeds/defaults/README.md), [`transformation/seeds/capabilities/README.md`](../../transformation/seeds/capabilities/README.md), [`transformation/docs/TAXONOMY.md` mục 5b](../../transformation/docs/TAXONOMY.md), [`scripts/checks/README.md`](../../scripts/checks/README.md), [ADR-015](./015-module-boundaries.md), [ADR-017](./017-packs-and-tenants.md)

## Bối cảnh

Sau [ADR-017](./017-packs-and-tenants.md), các pack (`crm`, `hug`, `finance`, `sales_playbook`, `marketplace`, `facebook_*`) đã có thư mục riêng nhưng **chưa tắt được**: lõi `ref()` thẳng vào 8 model pack, lõi đọc 3 seed của tenant Fine Japan, và job của 4 connector import asset `crm_cache_refresh` của pack `crm`. Muốn một doanh nghiệp thứ hai chỉ bật phần mình cần, lõi phải build được khi pack tắt, mà Fine Japan (mọi pack bật) không đổi một con số nào. Plan `261014-2225-pack-mechanism`, 9 phase, đã làm điều đó và kiểm chứng trên shadow gate (golden 83/83 bảng public 0 khác biệt ở mọi phase).

## Quyết định

### 1. `modules.yaml` là nguồn, `dbt_project.yml` là bản sao có kiểm

- `orchestration/config/modules.yaml` liệt kê `connectors`, `packs`, `tenants` của triển khai. Dagster nạp package theo đó.
- dbt không đọc được file này, và `dbt parse` chạy ở nhiều nơi không qua Dagster, nên `dbt_project.yml` giữ bản sao: `vars.enabled_packs`, `vars.enabled_connectors`, `vars.tenant`, và `+enabled: "{{ ('<pack>' in var('enabled_packs', [<mặc định>])) | as_bool }}"` cho **mọi** thư mục `models/packs/<pack>/`.
- Danh sách mặc định phải lặp trong từng `+enabled`, vì dbt render `dbt_project.yml` trước khi nạp khối `vars:` của chính nó (spike phase 1: `Required var 'enabled_packs' not found`).
- Luật `module-config` của `check_boundaries.py` giữ các bản sao khớp nhau (cả `pack_ids()`), không allowlist được, và in sẵn khối cần dán.

### 2. Lõi đọc pack chỉ qua `pack_ref` với hợp đồng cột

- `pack_ref('<pack>', '<model>')`: pack bật thì `ref(model)`, SQL compile ra giống hệt `ref()` cũ (Fine Japan byte-identical); pack tắt thì `(SELECT CAST(NULL AS <kiểu>) AS <cột>, ... WHERE FALSE)`, không tạo cạnh phụ thuộc.
- Hợp đồng nằm **một chỗ**, `pack_contracts()`: model pack → các cột lõi đọc và kiểu DuckDB. Test generic `pack_contract` gắn trên model pack so cột và kiểu thật với hợp đồng (mức error).
- Khi pack tắt, cột lấy từ pack là **NULL, không phải 0**: thiếu giá vốn không phải lãi bằng 0 (user chốt 14/10/2026; áp cả `is_margin_negative`).
- Model lõi chỉ cần doanh thu đọc lõi, không đọc pack: nửa doanh thu của `mart_sku_economics_monthly` tách thành `int_sku_sales_monthly` ở lõi; mart finance đọc lại nguyên giá trị và chỉ thêm giá vốn/biên.
- `check_boundaries.py` (`dbt-ref`) chỉ chấp nhận cạnh lõi → pack khi SQL gọi đúng dạng `pack_ref('<p>', '<m>'`, không có `ref('<m>')` thẳng, và `m` có hợp đồng của pack `p`. Allowlist không còn cạnh lõi → pack nào.

### 3. Lõi đọc seed tenant chỉ qua `tenant_ref` và seed mặc định rỗng

- `tenant_ref('<seed>')`: `var('tenant')` có giá trị thì `ref(seed)` của tenant; rỗng thì `ref('<seed>__default')`, bản mặc định của lõi ở `seeds/defaults/`, chỉ có tiêu đề, **mọi cột có kiểu** khai trong `dbt_project.yml` (CSV chỉ có tiêu đề mà thiếu kiểu thì mọi cột thành `INTEGER`).
- Luật `tenant-seed-contract` kiểm tiêu đề bản mặc định trùng seed của tenant đang bật và mọi cột có kiểu.

### 4. Connector không import pack: pack đăng ký asset chạy sau serving

- Pack export `AFTER_SERVING_ASSETS`; kernel gộp qua `job_support.after_serving_selection()` (import pack trong thân hàm); 6 job đồng bộ của connector gắn đuôi `| after_serving_selection()`.
- Tắt `crm` thì Definitions vẫn nạp được và không job nào chọn `crm_cache_refresh`.
- Asset chỉ chạy trong job nightly/full refresh nằm ở `job_support.NIGHTLY_ONLY_ASSETS`, các job đồng bộ trừ selection đó (hôm nay `mart_capabilities` và hai seed khả năng, user chốt 15/10/2026).

### 5. Khai báo khả năng của connector bằng seed sản phẩm

`seeds/capabilities/connector_capabilities.csv` (connector → khả năng, id của `modules.yaml`) và `capability_catalog.csv` (khả năng → `core` hay pack cần); model `monitoring/mart_capabilities` cho mỗi khả năng ba mức khai báo / cần / quan sát được và `status` (`OK`, `DECLARED_NO_DATA`, `PACK_ON_NO_SOURCE`, `DATA_NOT_DECLARED`, `NOT_NEEDED`). Bảng trong warehouse, chưa lên serving.

### 6. Lớp nhãn chuẩn dạng dữ liệu, bản xem trước

`seeds/taxonomy/taxonomy_canonical.csv` (bộ mã, sản phẩm) và `seeds/tenants/<t>/taxonomy_label.csv` (nhãn → mã, tenant, đọc qua `tenant_ref`); 5 model `lbl_<domain>` với cột `*_std`. Chỉ neo nhãn đang có, bộ mã chưa chốt, chưa lên serving. Bộ máy phân loại sau này thay phần sinh nhãn nhưng giữ tên `lbl_<domain>` và hai seed.

### 7. Gate có profile lõi trần

`scripts/shadow/gate.sh` bước 6b build nhánh với `{enabled_packs: [], tenant: ""}` và phải xanh; khác biệt so với Fine Japan in ra để đối chiếu danh sách dự kiến (`scripts/shadow/README.md`). Bước 1b đòi mọi test `labels_mapped` (mức warn trong dbt) `pass`.

## Phương án đã loại

| Phương án | Lý do loại |
|---|---|
| Truyền `--vars '{enabled_packs: [...]}'` ở mọi lời gọi dbt | `dbt parse` chạy ở lệnh start container, Dagster (`parse` rồi `build`), `build-lake.sh`, `run-all.sh`: một chỗ quên là pack bật/tắt sai mà không báo |
| Hai bản model lõi cho mỗi hook (bật/tắt bằng `enabled`, cùng `alias`) | Gấp đôi file và SQL lặp; spike phase 1 cho thấy `ref()` trong `if` đã cho lineage đúng |
| `config(enabled=pack_enabled(...))` trong từng model pack (~50 file) | Sửa hàng loạt file pack; `+enabled` theo thư mục với mặc định lặp, có check đồng bộ, gọn hơn |
| Dùng `graph` hoặc `run_query` lúc parse để biết pack nào có model | Lineage không còn tĩnh, phụ thuộc trạng thái warehouse; quyết định bật/tắt chỉ dựa trên `var` |
| Tắt pack thì cột lợi nhuận = 0 | Đọc như lãi bằng 0; NULL đúng nghĩa "không có dữ liệu giá vốn" |
| Dời `implied_gross_margin_pct`, `is_below_cost` (bảng public `fact_variant_prices_snapshot`) sang finance ngay | Đổi bảng public tích luỹ (serving gộp file: ngày cũ còn giá trị, ngày mới NULL); hai cột không đọc pack nên không cản lõi trần. Giữ ở lõi như ngoại lệ có lối ra (user chốt 14/10/2026) |

## Hệ quả

- Fine Japan không đổi số: golden 83/83, compiled SQL của model cũ giống hệt ở các phase chỉ đổi cách đọc (3, 5), inventory Dagster giống hệt ở phase 6.
- dbt build xanh với mọi pack tắt và không tenant; orchestration nạp được khi tắt `crm` (cùng `sales_playbook` phụ thuộc nó).
- Allowlist còn 21 mục, không còn lõi → pack, lõi → seed tenant, connector → pack. Còn lại: pack → pack (`ref()` thẳng, tắt pack đích làm `dbt parse` lỗi rõ), pack → connector ngoài `pack_connectors`, pack đọc source `crm_export`, tenant hook `mart_data_quality` → `fact_us_shipment_economics`.
- Giới hạn đã biết: test bị dbt tắt khi model của nó tắt (không cảnh báo), nên script đọc manifest bỏ qua `config.enabled = false`; model `external` 0 dòng được dbt-duckdb ghi thành parquet một dòng toàn NULL (serving đọc thẳng file sẽ thấy); khi tắt finance, số liệu trả hàng trong `dim_customers` cũng mất vì đang tính ở `int_customer_economics`.

## Khi nào xem xét lại

- Khi có doanh nghiệp thứ hai: chốt bộ mã chuẩn, tách `taxonomy_label`, đưa `lbl_*` và `mart_capabilities` lên serving (plan report).
- Khi cần tắt một pack mà pack khác phụ thuộc: khai báo phụ thuộc pack → pack, cho cạnh pack → pack đi qua cơ chế tương tự `pack_ref`.
- Khi dbt cho phép `var()` trong `dbt_project.yml` thấy khối `vars:` của chính nó: bỏ danh sách mặc định lặp trong `+enabled`.
