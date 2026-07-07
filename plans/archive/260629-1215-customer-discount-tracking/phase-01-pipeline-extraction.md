---
phase: 1
title: "Pipeline Extraction"
status: done
priority: P1
dependencies: []
---

# Phase 1: Pipeline Extraction

## Overview

Thêm `discount_rate` vào pipeline line-item, bổ sung `discount_line_item` cost_type vào `fact_order_costs`, thêm `max_line_discount_rate` mới vào `fact_orders`. Không thay đổi các columns/contracts cũ.

## Architecture

```
stg_sapo_v2_order_items  (json_extract → discount_amount, unit_price, quantity)
         │
         ▼
std_order_items          + discount_rate = discount_amount / NULLIF(unit_price * quantity, 0)
         │
         ▼
fact_sales               + discount_rate (pass-through)
         │
         ├──► fact_order_costs  + UNION: discount_line_item (join order_id → fact_orders)
         │
         └──► fact_orders       + max_line_discount_rate (new column, agg per customer order)
```

## Related Code Files

- Modify: `transformation/models/staging/standard/std_order_items.sql`
- Modify: `transformation/models/marts/sales/fact_sales.sql`
- Modify: `transformation/models/marts/sales/fact_order_costs.sql`
- Modify: `transformation/models/marts/sales/fact_orders.sql`

## Implementation Steps

### 1. `std_order_items.sql` — add discount_rate

```sql
-- After existing discount_amount, distributed_discount_amount:
discount_amount,
distributed_discount_amount,
-- Rate: discount_amount / gross_line_amount (unit_price × quantity = pre-discount price)
-- NULL when no discount or price is zero (avoid division by zero)
CASE
    WHEN discount_amount > 0 AND unit_price > 0 AND quantity > 0
    THEN ROUND(
        discount_amount / NULLIF(unit_price * quantity, 0),
        4  -- keep 4 decimal places (~0.01% precision)
    )
    ELSE NULL
END AS discount_rate,
```

> `unit_price * quantity` = gross pre-discount amount. `line_amount = unit_price * quantity - discount_amount`.
> Using `unit_price * quantity` (not `line_amount + discount_amount`) for precision when both may have rounding.

### 2. `fact_sales.sql` — pass-through discount_rate

```sql
-- In the SELECT from items i:
i.discount_amount,
i.distributed_discount_amount,
i.discount_rate,          -- ← add this line
i.weight_grams,
```

### 3. `fact_order_costs.sql` — add discount_line_item UNION

Add a new CTE after `sapo_discounts`:

```sql
-- ============================================================
-- Line-item discounts — from std_order_items (item-level price reduction)
-- Separate from discount_items_json (order-level).
-- Source: order_items.discount_amount > 0
-- No reason/label available; classified as 'discount_line_item'.
-- ============================================================
line_item_discounts_raw AS (
    SELECT
        i.order_id,
        SUM(ABS(i.discount_amount))                     AS amount,
        MAX(i.discount_rate)                            AS discount_rate,
        'line_item'                                     AS discount_type
    FROM {{ ref('std_order_items') }} i
    WHERE i.discount_amount > 0
    GROUP BY i.order_id
),

line_item_discounts AS (
    SELECT
        om.order_id,
        om.order_code,
        'discount_line_item'    AS cost_type,
        'DISCOUNT'              AS cost_category,
        CAST(l.amount AS DECIMAL(18, 2)) AS amount,
        l.discount_rate,
        l.discount_type,
        'sapo_v2'               AS source_system,
        om.order_code           AS source_record,
        'actual'                AS fee_source,
        om.date_key,
        om.channel_key
    FROM line_item_discounts_raw l
    JOIN order_meta om ON l.order_id = om.order_id
),
```

Add to final UNION ALL:

```sql
UNION ALL

SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    amount,
    discount_rate,
    discount_type,
    source_system,
    source_record,
    fee_source,
    date_key,
    channel_key
FROM line_item_discounts
```

### 4. `fact_orders.sql` — add max_line_discount_rate

In the `discount_order_summary` CTE or a new CTE, aggregate line-item rates per order:

```sql
-- NEW CTE: line-item discount summary per order
line_discount_order_summary AS (
    SELECT
        order_id,
        -- max discount_rate across all discounted lines in this order
        MAX(
            CASE
                WHEN discount_amount > 0 AND unit_price > 0 AND quantity > 0
                THEN discount_amount / NULLIF(unit_price * quantity, 0)
                ELSE NULL
            END
        ) AS max_line_discount_rate
    FROM {{ ref('std_order_items') }}
    WHERE discount_amount > 0
    GROUP BY order_id
),
```

In the final SELECT, after `primary_discount_type`:

```sql
lds.max_discount_rate,
lds.primary_discount_type,
ld.max_line_discount_rate,   -- ← NEW column
```

Add LEFT JOIN:

```sql
LEFT JOIN line_discount_order_summary ld ON o.order_id = ld.order_id
```

> Do NOT modify `max_discount_rate` (from discount_items) — existing Metabase charts depend on it.
> `max_line_discount_rate` is a new column alongside it.

## Success Criteria

- [ ] `std_order_items` has `discount_rate` column, NULL where no discount
- [ ] `fact_sales` has `discount_rate` column
- [ ] `fact_order_costs` has rows with `cost_type = 'discount_line_item'`
  - Verify: `SELECT COUNT(*) FROM fact_order_costs WHERE cost_type = 'discount_line_item'` → ~31,890 orders
- [ ] `fact_orders` has `max_line_discount_rate` column, populated for ~31,890 orders
- [ ] Existing `max_discount_rate` column unchanged (no regression)
- [ ] dbt `dbt run --select std_order_items fact_sales fact_order_costs fact_orders` succeeds

## Risk Assessment

- **std_order_items is a VIEW** (materialized='view') → no full-refresh needed
- **fact_sales is a parquet table** (materialized implicitly via location) → will auto-rebuild on `dbt run`
- **fact_order_costs is a parquet table** → same
- **fact_orders is a parquet table** → adding a new column may need `--full-refresh` if incremental
  - Check: does `fact_orders` have `{% if is_incremental() %}`? → YES it does
  - Action: run `dbt run --full-refresh --select fact_orders` on first deploy
- **Metabase**: after `fact_orders` rebuild, `max_line_discount_rate` appears as new field — safe (additive)
- After changes, stop Metabase → run `bootstrap_serving_views.py` → restart to pick up new DuckDB columns
