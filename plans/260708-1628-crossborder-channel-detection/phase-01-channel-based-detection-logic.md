---
phase: 1
title: "Channel-Based Detection Logic"
status: completed
priority: P1
dependencies: []
---

# Phase 1: Channel-Based Detection Logic

## Overview

Thêm tín hiệu "khách có ≥1 đơn trên kênh Sapo `channel_name='US'`" vào `dim_customers.sql`, OR vào `customer_type`'s CROSSBORDER branch và `is_us_gift_recipient` — bổ sung cho manual group-tag hiện có (không thay thế).

## Requirements

- Functional: customer_type/is_us_gift_recipient TRUE cho khách có US-channel order, kể cả khi Sapo group chưa được tag.
- Non-functional: không hardcode customer_id; logic phải tự động re-derive mỗi lần `dbt run` (self-healing khi có đơn mới trên kênh US).
- Non-functional: giữ nguyên toàn bộ branch precedence hiện có trong CASE (WHOLESALE/PARTNER/STAFF/KOL vẫn ưu tiên trước CROSSBORDER).

## Architecture

```
fact_orders (customer_key, channel_key, status)
         │
         │  JOIN dim_channels ON channel_key, WHERE channel_name = 'US'
         ▼
   us_channel_customers CTE (DISTINCT customer_key)
         │
         │  LEFT JOIN vào joined_data (dim_customers.sql CTE hiện có)
         ▼
customer_type CASE (dim_customers.sql:197-211)
  ... existing WHOLESALE/PARTNER/STAFF/KOL branches unchanged ...
  WHEN <existing CROSSBORDER group-tag condition> OR uc.customer_key IS NOT NULL
      THEN 'CROSSBORDER'
  ELSE 'RETAIL'

is_us_gift_recipient (dim_customers.sql:305-306)
  (<existing group-tag condition> OR uc.customer_key IS NOT NULL) AS is_us_gift_recipient
```

Tham chiếu pattern đã có sẵn trong repo cho "đơn Mỹ": `transformation/models/intermediate/us_shipment/int_us_shipment_line_prices.sql:16-26` — dùng `fact_orders JOIN dim_channels ON channel_key WHERE channel_name = 'US' AND status != 'CANCELLED'`. Giữ đúng pattern này (bao gồm loại trừ CANCELLED) để nhất quán.

## Related Code Files

- Modify: `transformation/models/marts/core/dim_customers.sql`
- Modify: `transformation/models/marts/schema.yml` (nếu có doc riêng cho `customer_type`/`is_us_gift_recipient`, cập nhật mô tả)
- Modify: `docs/context/order-customer-classification-staff-guide.md` — nguồn thật hiện tại cho logic `customer_type` (mục 8.2/9/12); phải cập nhật để tương lai không tưởng nhầm channel-signal là dead code
- Read only (reference pattern): `transformation/models/intermediate/us_shipment/int_us_shipment_line_prices.sql`

## Implementation Steps

1. Add a new CTE in `dim_customers.sql`, alongside the existing `customers`/`metrics`/`economics`/`benchmarks`/`discount_metrics` CTEs (top of file, `dim_customers.sql:6-24`):
   ```sql
   us_channel_customers AS (
       SELECT DISTINCT fo.customer_key
       FROM {{ ref('fact_orders') }}   fo
       JOIN {{ ref('dim_channels') }}  ch ON fo.channel_key = ch.channel_key
       WHERE ch.channel_name = 'US'
         AND fo.status != 'CANCELLED'
   ),
   ```

2. In the `joined_data` CTE's FROM/JOIN clauses (`dim_customers.sql:26` area), add:
   ```sql
   LEFT JOIN us_channel_customers uc ON c.customer_key = uc.customer_key
   ```
   Carry `uc.customer_key` (or a derived boolean) through to wherever `customer_type`/`is_us_gift_recipient` are computed — confirm whether these CASE expressions live in `joined_data` itself or a later CTE/final SELECT (read the full file before editing; the snippet reviewed this session showed them in the final SELECT reading from `joined_data`, so the join must happen in `joined_data` and the flag threaded through, OR added as a second join at the final SELECT level if `joined_data` is a pure passthrough — verify actual structure at implementation time).

3. Modify the `customer_type` CASE (`dim_customers.sql:197-211`):
   ```sql
   CASE
       WHEN customer_group_code LIKE '%WHOLESALE%' OR customer_group_name LIKE '%WHOLESALE%'
           THEN 'WHOLESALE'
       WHEN customer_group_code LIKE '%TYPE_PARTNER%' OR customer_group_name LIKE '%TYPE_PARTNER%'
         OR customer_group_code LIKE '%KY_GUI%' OR customer_group_name LIKE '%KY_GUI%'
           THEN 'PARTNER'
       WHEN customer_group_code LIKE '%TYPE_STAFF%' OR customer_group_name LIKE '%TYPE_STAFF%'
           THEN 'STAFF'
       WHEN customer_group_code LIKE '%TYPE_KOL%' OR customer_group_name LIKE '%TYPE_KOL%'
           THEN 'KOL'
       WHEN customer_group_code LIKE '%TYPE_CROSSBORDER%' OR customer_group_name LIKE '%TYPE_CROSSBORDER%'
         OR customer_group_code LIKE '%CTN00014%' OR customer_group_name LIKE '%CTN00014%'
         OR uc.customer_key IS NOT NULL                          -- NEW: channel-derived signal
           THEN 'CROSSBORDER'  -- US giao hàng hộ (người nhận VN); group-tag OR has US-channel order
       ELSE 'RETAIL'
   END as customer_type,
   ```
   Update the preceding comment block (`dim_customers.sql:187-196`) to document the new signal and why it's additive, not a replacement (mirror the tone of the existing comment explaining the group-tag migration gap).

4. Modify `is_us_gift_recipient` (`dim_customers.sql:300-306`):
   ```sql
   (customer_group_code LIKE '%TYPE_CROSSBORDER%' OR customer_group_name LIKE '%TYPE_CROSSBORDER%'
     OR customer_group_code LIKE '%CTN00014%' OR customer_group_name LIKE '%CTN00014%'
     OR uc.customer_key IS NOT NULL) AS is_us_gift_recipient,        -- NEW: channel-derived signal
   ```
   Update the preceding comment (`dim_customers.sql:300-304`) — it currently says "Group-code detection mirrors the customer_type CASE above"; update to say detection now also includes the channel-based signal.

5. Restart `data_platform` (manifest reload, upstream `fact_orders`/`dim_channels` refs unchanged but `dim_customers.sql` itself changed) → `dbt run --full-refresh --select dim_customers` (lock-retry pattern per `feedback_dim_customers_incremental_full_refresh.md`).

6. Cập nhật `docs/context/order-customer-classification-staff-guide.md` — nguồn thật hiện có cho logic `customer_type` (theo pattern đã dùng cho lần fix trước "ĐÃ XÁC NHẬN 2026-06-05"):
   - **Mục 8.2** (dòng ~242, bảng "Sapo group → customer_type"): thêm cột/ghi chú cho dòng CROSSBORDER — nêu rõ giờ có 2 đường: group-tag (`TYPE_CROSSBORDER`/`CTN00014`) **HOẶC** có ≥1 đơn `dim_channels.channel_name='US'`, đánh dấu ngày implement.
   - **Mục 9** (dòng ~256-268, SQL snippet `customer_type`): cập nhật khối SQL trích dẫn để khớp code thật — thêm nhánh `OR uc.customer_key IS NOT NULL` vào CROSSBORDER, kèm chú thích tham chiếu `us_channel_customers` CTE.
   - **Mục 12** (dòng ~309-313, "Chất lượng dữ liệu"): thêm 1 dòng mới trong bảng rủi ro, theo đúng format các dòng "ĐÃ GIẢI QUYẾT" hiện có — ghi rõ: (a) đây là tín hiệu **thường trực/tự-heal**, KHÔNG phải patch tạm; (b) khi nhân viên tag đúng group sau này, tín hiệu channel trở thành dư thừa-nhưng-vô-hại (OR), không cần gỡ bỏ; (c) lý do giữ vĩnh viễn — gap tag-thủ-công có thể tái diễn (nhân viên mới/khách mới chưa kịp tag).
   - Mục đích: để người đọc sau này (kể cả không phải người viết code) biết cơ chế channel-signal đang hoạt động và tại sao không nên xóa nó khi thấy group-tag "đã đủ".

## Success Criteria

- [x] `us_channel_customers` CTE exists, correctly excludes CANCELLED orders (matches `int_us_shipment_line_prices.sql` pattern)
- [x] `customer_type` CASE branch order unchanged (WHOLESALE/PARTNER/STAFF/KOL still take precedence over CROSSBORDER)
- [x] `is_us_gift_recipient` independently OR's the channel signal
- [x] `dbt run --full-refresh --select dim_customers` succeeds without lock errors (required a lock-retry loop — a Dagster realtime/incremental job held the write lock on several attempts; succeeded on retry)
- [x] Spot-check: a handful of customer_ids from `plans/reports/us-customers-260606.csv` that were previously `customer_type != 'CROSSBORDER'` now show `CROSSBORDER` (or `is_us_gift_recipient=TRUE` if a higher-precedence branch applies) — 813/817 now CROSSBORDER, 4 WHOLESALE-with-flag-TRUE (see Phase 2)
- [x] `docs/context/order-customer-classification-staff-guide.md` mục 8.2/9/12 cập nhật, phản ánh đúng logic mới (group-tag OR channel-signal) và ghi rõ tính chất thường trực/tự-heal của channel-signal

**Implementation note (2026-07-08)**: first implementation used an unqualified `EXISTS (... WHERE uc.customer_key = customer_key)` — this self-correlated to the subquery's own `us_channel_customers` alias instead of the outer `joined_data` row, making the condition true for every customer. Caught by running the full-refresh and inspecting the resulting distribution (RETAIL dropped to 0, CROSSBORDER=7429/7601) before proceeding to Phase 2. Fixed by qualifying as `uc.customer_key = joined_data.customer_key` (final SELECT reads `FROM joined_data` unaliased, so the table name itself is a valid qualifier). Re-ran full-refresh; distribution became plausible (see Phase 2). Also verified via a real Dagster asset materialization (`dagster asset materialize --select marts/dim_customers`) — 14/14 dbt tests/checks passed.

## Risk Assessment

- **Medium risk**: `dim_customers` is a widely-consumed dimension table; full-refresh + logic change touches every downstream consumer's customer_type values for the affected population.
- **Mitigation**: additive `OR` condition — no existing TRUE/CROSSBORDER classification can flip to FALSE/RETAIL; only previously-mistagged RETAIL customers move to CROSSBORDER (or another higher-precedence type if applicable). This is strictly a completeness fix, not a redefinition.
- **Risk**: `fact_orders`/`dim_channels` join adds a new upstream dependency to `dim_customers` — verify no circular dependency (dim_customers should not itself be an input to fact_orders' customer_key generation in a way that creates a dbt DAG cycle; `fact_orders.sql:13` reads `dim_customers_base`, not `dim_customers` — the fact/dim split makes this safe, but confirm during implementation).
- **Rollback**: revert the `OR uc.customer_key IS NOT NULL` additions, `dbt run --full-refresh --select dim_customers` again.
