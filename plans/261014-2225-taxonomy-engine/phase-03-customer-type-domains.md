---
phase: 3
title: "Pilot: đặc trưng, luật Fine Japan và hai domain customer_type"
status: pending
priority: P2
effort: "1.25d"
dependencies: [2]
---

# Phase 3: Hai domain `customer_type`

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `transformation/docs/TAXONOMY.md` mục `customer_type` và `is_us_gift_recipient` (thêm dòng "Bộ máy: domain `customer_type` và `customer_type__group_blob`, luật ở `seeds/tenants/fine_japan/taxonomy_rule_tenant.csv`, chưa nối mart"), §5 (seed luật có dữ liệu); `docs/architecture/taxonomy-engine.md` mục "Hiện thực MVP" (danh mục đặc trưng đầu tiên, hai domain pilot, quy ước `<domain>__<biến thể>`); `docs/architecture/modules.md` §9 (sơ đồ: đặc trưng → `lbl_*` → `entity_labels`) và §3 (số model theo bucket).

## Mục tiêu

`lbl_customer_type` và `lbl_customer_type__group_blob` cho ra đúng nhãn mà SQL cũ cho, với mọi khách, trên dữ liệu shadow, và đúng trên các ca biên chưa có trong dữ liệu (unit test với luật thật). Mart chưa đọc bộ máy.

## Hiện trạng cần tái tạo (đã kiểm trên nhánh)

| Logic | Vị trí | Đầu vào | Ghi chú |
|---|---|---|---|
| `dim_customers` | `transformation/models/core/marts/dim_customers.sql` L215–230 (`customer_type`), L330–332 (`is_us_gift_recipient`), L31–37 (CTE `us_channel_customers`: `fact_orders` ⋈ `dim_channels`, `channel_name = 'US'`, `status != 'CANCELLED'`) | `customer_group_code`, `customer_group_name` | Cột public; cờ là phép OR năm vị từ, có thể NULL |
| Blob (`fact_orders`) | `transformation/models/core/marts/sales/fact_orders.sql` L107–119 (CTE `customer_type_info` đọc `dim_customers_base`), dùng ở `scope_retail` L207–214 và `scope_b2b` L215–219 qua `COALESCE(cu2.customer_type, 'RETAIL')`, join L245 | `customer_group` (blob JSON) | Không xuất thành cột |
| Blob (benchmarks) | `transformation/models/core/marts/intermediate/int_customer_benchmarks.sql` L47–54 (tiền tố `c.`), dùng ở `benchmark_status` L76 | `c.customer_group` | Cùng logic với `fact_orders` (`TAXONOMY.md` mục `customer_type`) |

Người dùng cờ NULL: `transformation/models/packs/sales_playbook/marts/mart_customer_action_queue.sql` L71 và `mart_customer_sku_action_queue.sql` L53 (`AND NOT is_us_gift_recipient` loại dòng NULL).

## Files

- Create: `transformation/models/core/intermediate/taxonomy/feat_customer_profile.sql` — từ `dim_customers_base`: `customer_key`, `customer_group AS group_blob`, `customer_group_code AS group_code`, `customer_group_name AS group_name`. Không chuẩn hoá. Gồm cả dòng sentinel `Unknown`.
- Create: `transformation/models/core/intermediate/taxonomy/feat_customer_orders.sql` — `customer_key`, `list(DISTINCT ch.channel_name) FILTER (WHERE ch.channel_name IS NOT NULL) AS channels_ordered_on`, từ `fact_orders fo JOIN dim_channels ch ON fo.channel_key = ch.channel_key WHERE fo.status != 'CANCELLED'` (giữ đúng `!=`, đúng phép join trong; khoá theo **tên** `'US'` như SQL cũ).
- Create: `transformation/models/core/intermediate/taxonomy/lbl_customer_type.sql`, `lbl_customer_type__group_blob.sql` — `config(materialized='table', tags=['taxonomy'])` + `{{ taxonomy_label_model('<domain>') }}`.
- Create: `transformation/models/core/intermediate/taxonomy/_taxonomy__models.yml` — mô tả cột, test, unit test.
- Create: `transformation/models/monitoring/entity_labels.sql` (view, `{{ taxonomy_entity_labels() }}`) và mục tương ứng trong `transformation/models/monitoring/schema.yml`.
- Create: `transformation/tests/fixtures/taxonomy_rule_tenant_customer_type.csv` — bản sao đúng từng byte của seed luật tenant (fixture cho unit test).
- Create: `scripts/tests/test_taxonomy_fixtures.py` — fixture bằng đúng byte với seed (để unit test luôn chạy trên luật thật).
- Modify: `transformation/seeds/tenants/fine_japan/taxonomy_rule_tenant.csv` — 24 dòng (bảng dưới).
- Modify: bảng nhãn của plan cơ chế pack — thêm bộ nhãn `customer_type` nếu plan pack chưa có (sáu nhãn, neo tạm ở câu hỏi mở 2 của `plan.md`).
- Modify: `transformation/dbt_project.yml` — registry thêm 2 đặc trưng, 2 domain.
- Modify: `scripts/checks/model_buckets.yaml` — `feat_customer_profile`, `feat_customer_orders`, `lbl_customer_type`, `lbl_customer_type__group_blob` → `core`; `entity_labels` → `monitoring`.
- Modify: tài liệu ở đầu file.

## Registry của hai domain

```yaml
features:
  feat_customer_profile: {subject: customer, key: customer_key, columns: {group_blob: varchar, group_code: varchar, group_name: varchar}}
  feat_customer_orders:  {subject: customer, key: customer_key, columns: {channels_ordered_on: "varchar[]"}}
domains:
  customer_type:
    subject: customer, cardinality: single, hit_policy: FIRST, label_set: customer_type
    features: [feat_customer_profile, feat_customer_orders]
    matched_flags: [CROSSBORDER]
    survey: {features: [group_code, group_name], metrics_model: int_customer_metrics, order_count: frequency, revenue: monetary_value}
  customer_type__group_blob:
    subject: customer, cardinality: single, hit_policy: FIRST, label_set: customer_type
    features: [feat_customer_profile]          # không có feat_customer_orders: tránh vòng fact_orders → lbl → fact_orders
    survey: {features: [group_blob], metrics_model: int_customer_metrics, order_count: frequency, revenue: monetary_value}
```

`feat_customer_orders` khi ghép vào domain `customer_type` phải `COALESCE(channels_ordered_on, [])`, vì `EXISTS` của SQL cũ không bao giờ NULL; việc này nằm trong macro (đặc trưng kiểu danh sách mặc định rỗng khi `LEFT JOIN` hụt), có unit test ở phase 2.

## Luật Fine Japan (seed tenant)

| Domain | priority | label | Điều kiện (`feature op value`) | Số dòng |
|---|---|---|---|---|
| `customer_type` | 10, 11 | WHOLESALE | `group_code like %WHOLESALE%`; `group_name like %WHOLESALE%` | 2 |
| | 20–23 | PARTNER | `group_code`/`group_name like %TYPE_PARTNER%`; `group_code`/`group_name like %KY_GUI%` | 4 |
| | 30, 31 | STAFF | `group_code`/`group_name like %TYPE_STAFF%` | 2 |
| | 40, 41 | KOL | `group_code`/`group_name like %TYPE_KOL%` | 2 |
| | 50–54 | CROSSBORDER | `group_code`/`group_name like %TYPE_CROSSBORDER%`; `group_code`/`group_name like %CTN00014%`; `channels_ordered_on has US` | 5 |
| | 9999 | RETAIL | (không điều kiện) | 1 |
| `customer_type__group_blob` | 10 | WHOLESALE | `group_blob like %WHOLESALE%` | 1 |
| | 20, 21 | PARTNER | `group_blob like %TYPE_PARTNER%`; `group_blob like %KY_GUI%` | 2 |
| | 30 | STAFF | `group_blob like %TYPE_STAFF%` | 1 |
| | 40 | KOL | `group_blob like %TYPE_KOL%` | 1 |
| | 50, 51 | CROSSBORDER | `group_blob like %TYPE_CROSSBORDER%`; `group_blob like %CTN00014%` | 2 |
| | 9999 | RETAIL | (không điều kiện) | 1 |

Mỗi vế `OR` của một nhánh `CASE` là một luật riêng cùng nhãn; vì các nhãn được xếp đúng thứ tự nhánh, "luật đầu tiên khớp" trùng với "nhánh đầu tiên có một vế `TRUE`". `rule_id` đặt theo mẫu `ct_<nhãn>_<n>` và `ctb_<nhãn>_<n>`.

## Các bước

1. Viết hai model đặc trưng; build trên shadow; kiểm số dòng `feat_customer_profile` bằng `dim_customers_base`.
2. Điền seed luật; chạy `check_taxonomy_rules.py` (phải thoát 0).
3. Thêm bộ nhãn `customer_type` vào bảng nhãn của plan pack (nếu chưa có).
4. Khai báo registry, viết hai stub `lbl_*` và `entity_labels`.
5. Test lúc build trong `_taxonomy__models.yml`: `unique` + `not_null` cho `customer_key` (error); `relationships` ngược để mọi `customer_key` của `dim_customers_base` có mặt (error); `not_null` cho `customer_type` (error); `customer_type` thuộc bộ nhãn (error); tỉ lệ `UNMAPPED`/`UNKNOWN` bằng 0 (warn).
6. Unit test với **luật thật** (fixture là bản sao seed, `test_taxonomy_fixtures.py` kiểm bằng byte). Mỗi ca một test:

   | Ca | Domain | Đầu vào | Kỳ vọng |
   |---|---|---|---|
   | `_` là wildcard | cả hai | nhóm `KY GUI`, `KYxGUI` | PARTNER |
   | Phân biệt hoa thường | cả hai | nhóm `type_wholesale` | RETAIL |
   | Thứ tự ưu tiên | cả hai | nhóm chứa cả `TYPE_PARTNER` và `TYPE_STAFF` | PARTNER |
   | WHOLESALE thắng CROSSBORDER | `customer_type` | `TYPE_WHOLESALE` + có đơn `US` | WHOLESALE, `matched__crossborder = TRUE` |
   | Chỉ có tín hiệu đơn US | `customer_type` | nhóm `TYPE_RETAIL`, có đơn `US` | CROSSBORDER, cờ TRUE |
   | Đơn US đã huỷ | `customer_type` | nhóm NULL, đơn `US` duy nhất `CANCELLED` (không vào đặc trưng) | RETAIL, cờ NULL |
   | Code NULL, name khớp | `customer_type` | code NULL, name `TYPE_KOL` | KOL |
   | Nhóm thiếu hoàn toàn | `customer_type` | code NULL, name NULL, không đơn US | RETAIL, cờ **NULL** |
   | Nhóm có, không phải CROSSBORDER | `customer_type` | code `TYPE_RETAIL`, name `Bán lẻ`, không đơn US | RETAIL, cờ FALSE |
   | Sentinel `Unknown` | cả hai | blob `'Unknown'`, code/name NULL | RETAIL |
   | Blob khớp ở trường khác | blob | `{"name":"X","note":"WHOLESALE"}` | WHOLESALE |
   | Blob NULL | blob | NULL | RETAIL |
   | Khách không có đơn nào | `customer_type` | không có dòng ở `feat_customer_orders` | như khách không có đơn US |
   | Nhóm cũ `CTN00014` | cả hai | code `CTN00014` | CROSSBORDER |

7. Đối chiếu trên shadow (truy vấn tay trong lake-B, không commit): (a) `lbl_customer_type` so với `dim_customers` theo `customer_key`: `customer_type` khác hoặc `matched__crossborder IS DISTINCT FROM is_us_gift_recipient` phải ra 0 dòng; (b) `lbl_customer_type__group_blob` so với truy vấn chạy nguyên văn khối `CASE` của `fact_orders` trên `dim_customers_base`: 0 dòng. Lặp lại trên bộ backup của ngày khác (dựng lake-base từ cặp backup cũ hơn).
8. Ghi thời gian build của bốn model mới (từ `run_results.json`), và thời gian unit test.
9. Cập nhật tài liệu, commit.

## Verification

- Unit test pilot và selftest pass; `test_taxonomy_fixtures.py` pass; validator pass.
- Đối chiếu bước 7 = 0 dòng trên hai bộ dữ liệu khác ngày.
- Gate: `scripts/shadow/gate.sh S --allow-new`: golden 83/83 (mart chưa đổi), compiled SQL model hiện có không đổi, lake trống và full-refresh pass.
- `check_boundaries.py`: `entity_labels` ở bucket `monitoring`, không model core/pack nào đọc nó.
- Kiểm điều kiện dừng: số đặc trưng chỉ Fine Japan dùng = 0; không có SQL tự do trong luật; tổng công từ đầu phase 1 ≤ 4 ngày. Nếu bước 7 còn khác biệt chưa giải thích được, báo user trước khi sang phase 4.

## Đổi số?

**Không.** Mart chưa đọc `lbl_*`; bảng mới không phải bảng public.

## Rollback

Chưa lên prod. Revert commit trên nhánh.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Tên kênh `'US'` đổi thành `US (Unspecified)` khi có nguồn mới, luật gãy âm thầm | Giữ khoá theo tên để đúng byte; ghi vào Known divergences của `TAXONOMY.md` và hướng đổi sang `source_id` khi thống nhất |
| Fixture lệch seed thật | `test_taxonomy_fixtures.py` so byte |
| Bảng nhãn của plan pack có test "nhãn → mã chuẩn là hàm" ở mức error, dòng mới sai làm đỏ build | Chạy validator trước; gate bắt được |

## Effort

1.25 ngày (0.25 đặc trưng, 0.25 luật + nhãn + registry, 0.5 unit test, 0.25 đối chiếu + gate + tài liệu).
