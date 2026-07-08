---
phase: 1
title: "Gift Line Classification"
status: done
priority: P1
dependencies: []
---

# Phase 1: Gift Line Classification

## Overview

Thêm cờ `is_gift_line` (STRICT `line_amount = 0`) vào line-item grain, làm nền tảng cho mọi phase sau. Tái dùng đúng định nghĩa đã validate ở finance layer (`int_order_promo_goods_cost.is_gift_no_invoice`), KHÔNG phát minh ngưỡng `discount_rate` mới.

## Requirements

- Functional: mọi line-item (`std_order_items`/`fact_sales`) có 1 cờ boolean rõ ràng phân biệt hàng bán vs hàng tặng.
- Non-functional: không phá vỡ cột hiện có (`discount_amount`, `distributed_discount_amount`, `discount_rate`, `line_amount`), additive only.

## Architecture

```
stg_sapo_v2_order_items ($.price, $.discount_amount, $.line_amount)
         │
         ▼
std_order_items          + is_gift_line = (line_amount = 0)
         │                 (view — no full-refresh needed)
         ▼
fact_sales                + is_gift_line (pass-through)
```

Tại sao dùng `line_amount = 0` thay vì `discount_rate ≥ threshold`:
- `discount_rate` trong `std_order_items` chỉ tính khi `discount_amount > 0` — nếu rep nhập thẳng `unit_price = 0` (không qua field discount) thì `discount_rate` là NULL dù line đó rõ ràng là tặng.
- `line_amount = unit_price × quantity − discount_amount` đã có sẵn, phản ánh đúng "khách trả bao nhiêu cho dòng này trước thuế" bất kể cơ chế (giá 0 hay discount 100%).
- Đây chính xác là **predicate** đã dùng ở `int_order_promo_goods_cost.sql:57` (`WHERE lr.line_revenue = 0`, tính từ `SUM(i.line_amount)` — line 22-31) — giữ nhất quán 1 định nghĩa "zero-revenue line" trong toàn repo.

> **Sửa sau red-team (Security Adversary Finding 2)**: `is_gift_line` KHÔNG "mirror" cột `is_gift_no_invoice` của `int_order_promo_goods_cost` — đó là 1 cột hẹp hơn nhiều, chỉ TRUE khi đồng thời: `line_revenue = 0` AND `cogs_source = 'sapo_mac'` AND không có MISA-642 entry AND có `cogs_goods_primary` AND SKU không phải `DV%`/`CPBH%` (service SKU) — và tính ở grain `(order_code, sku)` (SUM gộp), không phải per-line. `is_gift_line` chỉ tái dùng **predicate `line_revenue = 0`** ở grain line-item, KHÔNG áp các điều kiện COGS/MISA/service-SKU kia. Kỳ vọng: nhiều dòng `is_gift_line = TRUE` sẽ có `is_gift_no_invoice = FALSE` (ví dụ: có MISA-642 entry, hoặc là service SKU) — đây là bình thường, không phải bug.

**KHÔNG gộp `distributed_discount_amount`** (voucher/campaign order-level phủ hết 1 line, khiến `net_revenue` sau phân bổ = 0 dù `line_amount > 0`) vào `is_gift_line`. Đây là "khách dùng voucher 100%" — khác bản chất "rep tặng tay, không thu tiền, không qua cơ chế discount chính thức". Giữ 2 khái niệm tách biệt; nếu cần sau này có thể thêm `is_net_zero_after_distribution` riêng.

## Related Code Files

- Modify: `transformation/models/staging/standard/std_order_items.sql` (add `is_gift_line` column)
- Modify: `transformation/models/staging/standard/schema.yml` (doc + test)
- Modify: `transformation/models/marts/sales/fact_sales.sql` (pass-through `is_gift_line`)
- Modify: `transformation/models/marts/schema.yml` (doc + test for `fact_sales.is_gift_line`)
- Read only (reference, do not modify): `transformation/models/intermediate/cogs/int_order_promo_goods_cost.sql`

## Implementation Steps

1. In `std_order_items.sql`, after the existing `discount_rate` CASE expression, add:
   ```sql
   (line_amount = 0) AS is_gift_line,
   ```
   Place directly after `line_amount` in the SELECT list for readability.

2. In `fact_sales.sql`, add `i.is_gift_line` to the SELECT from `std_order_items` (alongside existing `i.discount_amount`, `i.discount_rate`).

3. Update `transformation/models/staging/standard/schema.yml` and `transformation/models/marts/schema.yml`: document `is_gift_line` as "TRUE when line_amount = 0 (STRICT) — rep-entered giveaway/gift, distinct from voucher/campaign discounts that reduce but don't zero the line. Mirrors int_order_promo_goods_cost.is_gift_no_invoice definition at line-item grain." Add `not_null` test (boolean, should never be NULL given `line_amount` is NOT NULL upstream — verify this assumption during implementation; if `line_amount` can be NULL, use `COALESCE(line_amount, -1) = 0` guard instead of bare equality).

4. Restart `data_platform` (manifest reload) → `dbt run --select std_order_items fact_sales`.

5. Verification query — **corrected after red-team** (original version referenced `fact_sales.sku`/`fact_sales.order_code`, neither of which exists; `fact_sales` only has `product_key`/`order_id`, resolved via `dim_products`/`fact_orders`). Cross-check against `int_order_promo_goods_cost`'s underlying `line_revenue = 0` aggregate (NOT its narrower `is_gift_no_invoice` flag — see note above):
   ```sql
   WITH fs_resolved AS (
       SELECT
           fo.order_code,
           dp.sku,
           fs.is_gift_line
       FROM fact_sales fs
       JOIN dim_products dp ON fs.product_key = dp.product_key
       JOIN fact_orders fo  ON fs.order_id    = fo.order_id
   ),
   fs_agg AS (
       -- int_order_promo_goods_cost's line_revenue is a SUM at (order_code, sku) grain —
       -- match that grain here rather than comparing single lines to an aggregate.
       SELECT order_code, sku, BOOL_AND(is_gift_line) AS all_lines_gift
       FROM fs_resolved
       GROUP BY order_code, sku
   )
   SELECT COUNT(*)
   FROM fs_agg a
   JOIN int_order_promo_goods_cost p
     ON a.order_code = p.order_code AND a.sku = p.sku
   WHERE a.all_lines_gift = FALSE AND p.line_revenue = 0
   -- Should return 0 rows: p.line_revenue=0 is itself derived from SUM(line_amount)=0,
   -- which is exactly what a.all_lines_gift=TRUE should also detect when all lines at
   -- that (order_code, sku) are zero. A disagreement here means the two SUM/predicate
   -- computations diverged — investigate before proceeding. Do NOT compare against
   -- p.is_gift_no_invoice — that column applies extra COGS/MISA/service-SKU filters
   -- unrelated to gift classification (see note above).
   ```

## Success Criteria

- [x] `std_order_items.is_gift_line` exists, `line_amount = 0` test, documented in schema.yml
- [x] `fact_sales.is_gift_line` pass-through, no NULL values where `line_amount` is populated
- [x] Cross-check query against `int_order_promo_goods_cost.line_revenue = 0` returns 0 disagreements
- [x] `dbt run --select std_order_items fact_sales` succeeds, no regression in row counts
- [x] Existing `discount_rate`/`discount_amount`/`distributed_discount_amount` columns unchanged

**Implementation report**: `reports/phase-01-implementation-report.md` (2026-07-08). All criteria verified: 19/19 dbt tests pass, `fact_sales` row count unchanged (27,687 → 27,687), 0 NULLs in `is_gift_line`, 0 disagreements in cross-check query.

## Risk Assessment

- **Low risk**: purely additive column, `std_order_items` is a view (no full-refresh needed), `fact_sales` rebuilds on every `dbt run`.
- **Risk**: if `line_amount` has unexpected NULLs (not observed so far, but not explicitly verified) — guard with `COALESCE` per step 3 note.
- **Rollback**: drop the column addition; no downstream consumer exists until Phase 2/3 wire it in.
