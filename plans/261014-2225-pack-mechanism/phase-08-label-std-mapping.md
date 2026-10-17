---
phase: 8
title: "Lớp ánh xạ nhãn → mã chuẩn: taxonomy_canonical, taxonomy_label, lbl_<domain>"
status: pending
priority: P1
effort: "0.5d"
dependencies: [5]
---

# Phase 8: Lớp nhãn chuẩn (`*_std`, bản xem trước)

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `transformation/docs/TAXONOMY.md` (mục mới "Lớp ánh xạ nhãn → mã chuẩn" + dòng "Mã chuẩn (xem trước)" trong 5 domain `channel_format`, `channel_category`, `customer_type`, `value_group`, `customer_lifecycle_stage`); `docs/architecture/modules.md` §9 (taxonomy: phần §3.3–3.4 của thiết kế đã có dạng dữ liệu, bộ máy luật chưa có); `docs/architecture/taxonomy-engine.md` (ghi lớp nhãn đã làm trước, bộ máy sẽ thay phần sinh nhãn, giữ tên `lbl_<domain>` và hai bảng seed); `transformation/models/tenants/fine_japan/README.md` (bảng nhãn của Fine Japan); `transformation/seeds/defaults/README.md`.

## Mục tiêu

Report chuẩn có cột `*_std` ngay, chưa cần bộ máy luật: mỗi nhãn Fine Japan đang ra được neo vào **một** mã chuẩn ([taxonomy-engine-design.md](../261013-1751-modularize-data-platform-suite/taxonomy-engine-design.md) §3.3–3.4). Bộ mã là **bản xem trước, chưa chốt** (chưa có doanh nghiệp thứ hai, quyết định #1 §8 của thiết kế). Không thêm cột nào vào mart public đang có (golden so cả thứ tự cột); `*_std` chỉ nằm ở model mới, không lên serving.

## Domain và cột nguồn (đã kiểm với `transformation/docs/TAXONOMY.md`)

| Domain (id theo `TAXONOMY.md`) | Bảng nguồn, khoá | Cột nhãn | Nhãn Fine Japan |
|---|---|---|---|
| `channel_format` | `dim_channels`, `channel_key` | `channel_format` | Marketplace, Social, System, Other, Direct, B2B, Web, CrossBorder Fulfillment, Retail (hàng `Unknown` = `Other`) |
| `channel_category` | `dim_channels`, `channel_key` | `channel_category` | Online-Ecommerce, Offline, Internal |
| `customer_type` | `dim_customers`, `customer_key` | `customer_type` | WHOLESALE, PARTNER, STAFF, KOL, CROSSBORDER, RETAIL |
| `value_group` | `dim_customers`, `customer_key` | `value_group` | VALUE_VIP, VALUE_GOLD, VALUE_SILVER, VALUE_BRONZE |
| `customer_lifecycle_stage` | `dim_customers`, `customer_key` | `lifecycle_stage` | LIFECYCLE_NEW, LIFECYCLE_ACTIVE, LIFECYCLE_AT_RISK, LIFECYCLE_CHURNED |

Khi code, kiểm lại tập nhãn bằng `SELECT DISTINCT` trên lake-B; nhãn có trong dữ liệu mà không có trong bảng trên thì thêm vào `taxonomy_label`, không bỏ qua. `customer_type` của `dim_customers` khác `fact_orders` ở khách chỉ có tín hiệu kênh US (Known divergence trong `TAXONOMY.md`); `lbl_customer_type` theo `dim_customers` và ghi điều này trong mô tả model.

## Thiết kế

### Hai bảng dữ liệu

- `transformation/seeds/taxonomy/taxonomy_canonical.csv` (sản phẩm sở hữu): `domain, code, parent_code, name_vi, name_en, is_reserved`. Mỗi domain có thêm 4 mã dành riêng `UNMAPPED`, `UNKNOWN`, `NOT_APPLICABLE`, `OTHER` (`is_reserved = true`). Mã lấy từ thiết kế §5.1–5.2: `channel_format` = MARKETPLACE, SOCIAL, WEB, RETAIL_STORE, B2B, DIRECT_SALES, NON_SALES; `channel_category` = ONLINE, OFFLINE, INTERNAL; `customer_type` = cây CONSUMER; TRADE (WHOLESALE, DEALER, CONSIGNMENT, RESELLER_CTV); INTERNAL (STAFF, RELATED_PARTY); CREATOR (KOL, AFFILIATE); `value_group` = TOP, HIGH, MID, BASE (thiết kế gọi domain này là `value_tier`; ghi ở `name_en`); `customer_lifecycle_stage` = NEW, ACTIVE, AT_RISK, CHURNED, REACTIVATED.
- `transformation/seeds/tenants/fine_japan/taxonomy_label.csv` (tenant sở hữu): `domain, label, label_std, note`. Lõi đọc qua `tenant_ref('taxonomy_label')`; seed mặc định `transformation/seeds/defaults/taxonomy_label__default.csv` chỉ có tiêu đề (cơ chế phase 5). Không có tenant thì mọi nhãn ra `UNMAPPED`.

### Ánh xạ đề xuất cho Fine Japan (xem trước; dòng in nghiêng cần user xác nhận)

| Domain | Nhãn → mã chuẩn |
|---|---|
| `channel_format` | Marketplace → MARKETPLACE; Social → SOCIAL; Web → WEB; Retail → RETAIL_STORE; B2B → B2B; Direct → DIRECT_SALES; *System → NON_SALES*; *CrossBorder Fulfillment → NON_SALES*; *Other → OTHER* |
| `channel_category` | Online-Ecommerce → ONLINE; Offline → OFFLINE; Internal → INTERNAL |
| `customer_type` | RETAIL → CONSUMER; WHOLESALE → WHOLESALE; *PARTNER → TRADE* (nút cha: `TYPE_PARTNER` và `KY_GUI` gộp, chưa tách được ký gửi); STAFF → STAFF; KOL → KOL; *CROSSBORDER → OTHER* (câu hỏi nghiệp vụ §9 của thiết kế) |
| `value_group` | VALUE_VIP → TOP; VALUE_GOLD → HIGH; VALUE_SILVER → MID; VALUE_BRONZE → BASE |
| `customer_lifecycle_stage` | LIFECYCLE_NEW → NEW; LIFECYCLE_ACTIVE → ACTIVE; LIFECYCLE_AT_RISK → AT_RISK; LIFECYCLE_CHURNED → CHURNED |

Giới hạn đã biết (ghi trong `TAXONOMY.md`): ánh xạ chỉ nhìn nhãn, nên khách chưa mua (đang mang `LIFECYCLE_CHURNED`, `VALUE_BRONZE`) không ra `NOT_APPLICABLE`; việc đó cần luật, để bộ máy làm.

### Model `lbl_<domain>`

- Macro `label_std_model(domain, subject_model, key, label_column)` (`transformation/macros/labels/label_std_model.sql`) sinh: `SELECT s.<key>, s.<label_column>, COALESCE(l.label_std, IF(s.<label_column> IS NULL, 'UNKNOWN', 'UNMAPPED')) AS <label_column>_std FROM {{ ref(subject_model) }} s LEFT JOIN (nhãn của domain từ tenant_ref('taxonomy_label')) l ON l.label = s.<label_column>`. So khớp chính xác, phân biệt hoa/thường như SQL hiện tại. Không dùng `CASE ... END AS`, nên `check_taxonomy_inventory.py` không báo khối mới; nếu vẫn báo thì đăng ký trong `scripts/checks/taxonomy_inventory.yaml`.
- 5 model, mỗi file một dòng gọi macro: `lbl_channel_format`, `lbl_channel_category` (grain `channel_key`), `lbl_customer_type`, `lbl_value_group`, `lbl_customer_lifecycle_stage` (grain `customer_key`). Tên trùng tên model mà bộ máy sẽ sinh (thiết kế §4), để bộ máy thay phần tính mà người đọc không phải đổi.
- Thư mục `transformation/models/core/marts/labels/`, `materialized='table'`, không `location`. Thêm 5 dòng `core` vào `scripts/checks/model_buckets.yaml`.

### Test

| Test | Mức | Ý nghĩa |
|---|---|---|
| `dbt_utils.unique_combination_of_columns [domain, label]` trên `taxonomy_label` và `taxonomy_label__default` | error | Nhãn → mã chuẩn là hàm |
| `dbt_utils.unique_combination_of_columns [domain, code]` trên `taxonomy_canonical`; singular test `parent_code` tồn tại cùng domain | error | Bộ mã hợp lệ |
| Singular test: mọi `(domain, label_std)` của `tenant_ref('taxonomy_label')` có trong `taxonomy_canonical` | error | Chỉ neo vào mã có thật |
| `unique` + `not_null` trên khoá của từng `lbl_*` | error | Grain đúng |
| Generic test `labels_mapped` trên cột `*_std` của từng `lbl_*`: không có dòng `UNMAPPED` | **warn** | Mọi nhãn Fine Japan có mã. Để `warn` để nhãn mới do seed `ref_order_sources` đổi không làm đỏ nightly; gate đòi test này `pass` (xem Verification) |

## Files

- Create: `transformation/seeds/taxonomy/taxonomy_canonical.csv`, `transformation/seeds/tenants/fine_japan/taxonomy_label.csv`, `transformation/seeds/defaults/taxonomy_label__default.csv`, properties YAML cho 3 seed; `transformation/macros/labels/label_std_model.sql`; `transformation/tests/generic/labels_mapped.sql`; 2 singular test; 5 file `transformation/models/core/marts/labels/lbl_*.sql` + `_labels__models.yml`.
- Modify: `transformation/dbt_project.yml` (`+column_types` cho seed mới nếu cần), `scripts/checks/model_buckets.yaml`, tài liệu ở khối đầu.

## Verification

- **Gate M `--allow-new`**: golden 83/83; compiled SQL của model cũ giống hệt; inventory chỉ có node mới.
- Trên lake-B, `run_results.json`: 5 test `labels_mapped` đều `pass` (không phải `warn`); mọi test seed `pass`. `SELECT <label>_std, count(*) ... GROUP BY 1` cho từng `lbl_*` để rà bằng mắt, dán vào báo cáo phase.
- Bước 6b (lõi trần, không tenant): 5 model build được, mọi dòng `UNMAPPED`/`UNKNOWN`, `labels_mapped` ra `warn` (đúng thiết kế, không fail build).
- Không có thư mục mới trong `export/marts/rolling/`.

**Đổi số:** không.

## Deploy D3 (sau phase 8, gộp phase 7–8)

Như D1. Sau deploy kiểm thêm: nightly có 5 bảng `lbl_*` và `mart_capabilities` trong `main_marts`, test `labels_mapped` `pass`.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Report dùng `*_std` như mã đã chốt | Mô tả model và README ghi "xem trước, chưa chốt"; không lên serving trong plan này |
| Nhãn mới xuất hiện sau deploy | `labels_mapped` cảnh báo trong nightly; thêm dòng vào `taxonomy_label` qua gate |

## Rollback

`git revert`. Bảng `lbl_*`, `taxonomy_canonical`, `taxonomy_label`, `taxonomy_label__default` còn trong warehouse: vô hại, xoá khi tiện.
