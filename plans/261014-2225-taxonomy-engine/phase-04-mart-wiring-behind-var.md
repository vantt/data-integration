---
phase: 4
title: "Nối mart sau var (mặc định tắt), monitor đối chiếu và giá trị chưa phân loại, golden với var bật"
status: pending
priority: P2
effort: "1d"
dependencies: [3]
---

# Phase 4: Nối mart sau `var`, monitor, golden với bộ máy bật

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `transformation/docs/TAXONOMY.md` (bảng "Vị trí và hash" của `customer_type`, `is_us_gift_recipient` với dòng mới; ba khối bản sao trong `monitor_taxonomy_parity`; §6 ghi literal giờ còn ở seed tenant); `scripts/checks/taxonomy_inventory.yaml` (dòng mới, ba bản sao); `docs/architecture/taxonomy-engine.md` (biến `taxonomy_engine_customer_type`, cách chạy gate với biến bật, ba model monitor); `docs/architecture/modules.md` §9 (monitor) và §10 (logic hook CROSSBORDER: hai đường, bộ máy chưa bật).

## Mục tiêu

Ba model đang chứa `customer_type` có hai đường: đường SQL cũ (khi `var('taxonomy_engine_customer_type')` là `false`, mặc định) và đường bộ máy. Chứng minh golden 83/83 0 khác biệt khi bật bộ máy, trong khi build mặc định vẫn cho compiled SQL như cũ. Thêm monitor đối chiếu (dùng cho 14 đêm và 30 ngày) và truy vấn liệt kê giá trị thô chưa phân loại kèm doanh thu.

## Vì sao dùng `if var` mà không dùng `depends_on` cố định

Khi parse, dbt chỉ ghi lại `ref()` của nhánh Jinja được render với giá trị biến hiện hành. Với `var = false`, `lbl_*` **không** là tổ tiên của mart, nên trong 14 đêm chạy song song, lỗi build hay test `error` của bộ máy không thể làm SKIP `dim_customers`, `fact_orders`, `int_customer_benchmarks`. Với `var = true`, cạnh `ref` được ghi bình thường và thứ tự build đúng. Bước 6 kiểm điều này trên manifest; không thêm comment `-- depends_on` ở bất kỳ bên nào.

## Files

- Modify: `transformation/models/core/marts/dim_customers.sql`
  - Sau `FROM joined_data`: `{%- if var('taxonomy_engine_customer_type') %} LEFT JOIN {{ ref('lbl_customer_type') }} ct ON ct.customer_key = joined_data.customer_key {%- endif %}`.
  - Khối `CASE` L215–230: `{%- if var(...) %} ct.customer_type AS customer_type, {%- else %} <khối cũ nguyên văn, kể cả "as customer_type,"> {%- endif %}`. Alias phải nằm **trong** mỗi nhánh: `check_taxonomy_inventory.py` nhận alias ngay sau `END`, và snippet của biểu thức gồm cả alias.
  - Biểu thức L330–332: `{%- if var(...) %} ct.matched__crossborder AS is_us_gift_recipient, {%- else %} <biểu thức cũ nguyên văn, kể cả "AS is_us_gift_recipient,"> {%- endif %}`.
  - CTE `us_channel_customers` L31–37 giữ nguyên ở cả hai đường (DuckDB bỏ CTE không dùng); xoá ở phase 8.
- Modify: `transformation/models/core/marts/sales/fact_orders.sql` — thân CTE `customer_type_info` L107–119: `{%- if var(...) %} SELECT customer_key, customer_type FROM {{ ref('lbl_customer_type__group_blob') }} {%- else %} <SELECT cũ nguyên văn> {%- endif %}`. Tên CTE, alias `cu2`, hai biểu thức `scope_*` không đổi.
- Modify: `transformation/models/core/marts/intermediate/int_customer_benchmarks.sql` — trong CTE `base`: khối `CASE` L47–54 thành `{%- if var(...) %} ctb.customer_type AS customer_type, {%- else %} <khối cũ nguyên văn, kể cả "END AS customer_type,"> {%- endif %}`; thêm `{%- if var(...) %} LEFT JOIN {{ ref('lbl_customer_type__group_blob') }} ctb ON ctb.customer_key = c.customer_key {%- endif %}`.
- Modify: `transformation/dbt_project.yml` — `vars.taxonomy_engine_customer_type: false`.
- Create: `transformation/models/monitoring/monitor_taxonomy_parity.sql` (view) — mỗi khách một dòng mỗi domain: nhãn và cờ của bộ máy, nhãn và cờ của **bản sao nguyên văn** ba khối cũ (`customer_type` của `dim_customers`, `is_us_gift_recipient`, `customer_type` của `fact_orders`), cột `is_diff` dùng `IS DISTINCT FROM`. Bản sao dùng đúng tên CTE `joined_data`, `us_channel_customers` và tên cột như file gốc để sha256 khối trùng với inventory; alias đặt `legacy_customer_type`, `legacy_is_us_gift_recipient`, `legacy_customer_type_blob` để `check_taxonomy_inventory.py` không coi là khối mới gán cột taxonomy.
- Create: `transformation/models/monitoring/monitor_taxonomy_parity_log.sql` — `materialized='incremental'`, `full_refresh=false`, mỗi lần chạy thêm một dòng mỗi domain: `run_at`, `run_date` (giờ Việt Nam), `domain`, `ruleset_version`, `n_entities`, `n_label_diff`, `n_flag_diff`, `n_legacy_else` (số khách mà khối cũ rơi vào `ELSE`), `n_engine_default` (số khách khớp luật không điều kiện), `n_unmapped`, `n_unknown`.
- Create: `transformation/models/monitoring/monitor_taxonomy_unmapped.sql` (view) — với mỗi domain không phải selftest: giá trị thô của `survey.features` của các khách rơi vào `UNMAPPED`, `UNKNOWN` hoặc luật không điều kiện; kèm số khách, tổng `frequency` và tổng `monetary_value` từ `int_customer_metrics`; sắp theo doanh thu giảm dần.
- Modify: `transformation/models/monitoring/schema.yml` — mô tả; test `monitor_taxonomy_parity`: không có dòng `is_diff` (severity `warn`).
- Modify: `scripts/checks/model_buckets.yaml` — ba monitor → `monitoring`.
- Modify: `scripts/checks/taxonomy_inventory.yaml` — cập nhật `line` của các khối cũ (đã dời dòng, hash giữ nguyên); thêm hai khối `CASE` bản sao trong `monitor_taxonomy_parity` vào domain `customer_type` với **cùng sha256** khối gốc (hash khối `CASE` không gồm alias); bản sao biểu thức `is_us_gift_recipient` là loại `expr` mà snippet gồm cả alias, nên ghi thành một dòng riêng với snippet và hash của chính nó, kèm ghi chú "bản sao của khối ở `dim_customers.sql`".
- Modify: tài liệu ở đầu file.

## Các bước

1. Sửa ba model như mục Files, dùng `{%-`/`-%}` để khi `var = false` SQL biên dịch trùng bản cũ.
2. So compiled SQL (`var = false`) của ba model với baseline: mục tiêu là trùng hệt. Nếu chỉ lệch khoảng trắng mà không khử được, chấp nhận ở bước 7 bằng `--allow-code-change` và lưu diff đính kèm commit message.
3. Viết ba model monitor; build trên shadow; `monitor_taxonomy_parity` phải 0 dòng `is_diff`; `monitor_taxonomy_unmapped` liệt kê nhóm khách rơi vào `RETAIL` mặc định kèm doanh thu.
4. Chạy `check_taxonomy_inventory.py`: chỉ có `INFO moved` cho khối cũ; hai bản sao `CASE` khớp hash của khối gốc, bản sao biểu thức khớp dòng riêng của nó; không `WARN new`, không `WARN changed`. Cập nhật `taxonomy_inventory.yaml` và bảng hash trong `TAXONOMY.md` (test `test_check_taxonomy_inventory.py` phải pass).
5. Đo: thời gian build thêm của ba monitor; tổng thời gian `dbt build` trên shadow so với baseline.
6. Kiểm manifest: với `var = false`, `depends_on.nodes` của `dim_customers`, `fact_orders`, `int_customer_benchmarks` **không** chứa `lbl_*`; với `--vars '{taxonomy_engine_customer_type: true}'` thì có.
7. Gate trên nhánh (`var = false`): `scripts/shadow/gate.sh S --allow-new`.
8. Commit nháp (không merge, không push lên nhánh chính của plan) đổi mặc định `taxonomy_engine_customer_type: true`; chạy `scripts/shadow/gate.sh S --allow-new --allow-code-change` từ worktree ở commit nháp; xong thì bỏ commit nháp.
9. Cập nhật tài liệu, commit (commit thật giữ `var = false`).

## Verification

- Gate bước 7: golden 83/83, compiled SQL ba model trùng baseline (hoặc chỉ khác khoảng trắng đã ghi), Dagster inventory không đổi ngoài asset mới, lake trống, full-refresh pass.
- Gate bước 8 (bộ máy bật): **golden 83/83 0 khác biệt**, gồm `dim_customers` (thứ tự cột không đổi), `fact_orders`, `mart_customer_action_queue`, `mart_customer_sku_action_queue`; full-refresh pass; lake trống pass. dbt inventory chỉ báo thêm phụ thuộc mới (được `--allow-code-change` chấp nhận).
- `monitor_taxonomy_parity` 0 dòng `is_diff` ở cả hai chế độ.
- Đây là mốc "0 khác biệt golden" của điều kiện dừng 1: tổng công từ đầu phase 1 phải ≤ 5 ngày.

## Đổi số?

**Không.** Mặc định vẫn là đường SQL cũ; gate bước 8 chứng minh đường bộ máy cũng không đổi số.

## Rollback

Chưa lên prod. Revert commit trên nhánh.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Ba file này hay bị analyst sửa trên `main` | Rebase lên `main` trước bước 7; sửa tối thiểu; bản sao trong monitor phải cập nhật cùng khi khối gốc đổi (inventory báo `WARN changed` cho cả hai) |
| Bản sao trong monitor lệch khối gốc | Hash trùng là điều kiện bước 4; inventory cảnh báo khi một bên đổi |
| `LEFT JOIN` thêm vào `dim_customers` nhân dòng | `lbl_customer_type` có test `unique` (error); golden so số dòng |
| Bảng log incremental bị xoá khi ai đó chạy full-refresh | `full_refresh=false` trong config |

## Effort

1 ngày (0.4 sửa ba model + kiểm compiled SQL, 0.3 ba monitor, 0.3 inventory + hai gate + tài liệu).
