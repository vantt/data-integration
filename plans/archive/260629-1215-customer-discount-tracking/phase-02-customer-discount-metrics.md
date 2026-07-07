---
phase: 2
title: "Customer Discount Metrics"
status: pending
priority: P2
dependencies: [1]
---

# Phase 2: Customer Discount Metrics

## Overview

Tạo model intermediate mới `int_customer_discount_metrics` tính 6 discount fields per customer từ `fact_orders` và `fact_sales`. Tách riêng khỏi `int_customer_metrics` (file đó đã >450 lines, KISS).

## Unified Taxonomy (4 buckets)

| Bucket | Source | discount_type filter |
|---|---|---|
| `line_discount` | `fact_sales.discount_rate` | N/A (all line-items with discount_amount > 0) |
| `voucher` | `fact_orders.max_discount_rate` | primary_discount_type = 'voucher_promotional' |
| `campaign` | `fact_orders.max_discount_rate` | primary_discount_type IN ('bundle', 'campaign', 'sampling_gift') |
| `negotiated` | `fact_orders.max_discount_rate` | primary_discount_type IN ('negotiated_micro', 'negotiated_standard', 'negotiated_deep', 'wholesale_explicit', 'employee_internal', 'overseas') |

**Note on `primary_discount_type` proxy:** `primary_discount_type = MAX_BY(discount_type, amount)` — dominant type per order. Orders with mixed types classified by the larger amount. Acceptable approximation for customer-level metrics.

## Related Code Files

- Create: `transformation/models/marts/core/intermediate/int_customer_discount_metrics.sql`
- Create: `transformation/models/marts/core/intermediate/int_customer_discount_metrics.yml` (schema + tests)

## Implementation Steps

### 1. Create `int_customer_discount_metrics.sql`

```sql
{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'intermediate']
) }}

-- Per-customer discount metrics across 4 unified buckets.
-- Grain: 1 row per customer_key.
-- Buckets:
--   line_discount  = item-level price reduction (fact_sales.discount_rate)
--   voucher        = customer actively redeemed a voucher code
--   campaign       = merchant applied promo: bundle/CTKM/sampling
--   negotiated     = B2B/direct deal: đại lý/hợp đồng/nhân viên/overseas

WITH changed_customers AS (
    {% if is_incremental() %}
    SELECT DISTINCT customer_key
    FROM {{ ref('fact_orders') }}
    WHERE updated_at >= (SELECT MAX(metric_calculated_at) - INTERVAL '1 day' FROM {{ this }})
    {% else %}
    SELECT DISTINCT customer_key FROM {{ ref('fact_orders') }}
    {% endif %}
),

-- ── BUCKET 1: line_discount ───────────────────────────────────────────────
-- Source: fact_sales.discount_rate (item-level, no type label available)
-- Aggregate to order-level (max rate across discounted lines), then to customer.
line_discount_per_order AS (
    SELECT
        fs.customer_key,
        fs.order_id,
        fo.ordered_at,
        MAX(fs.discount_rate) AS order_line_max_rate
    FROM {{ ref('fact_sales') }} fs
    JOIN {{ ref('fact_orders') }} fo ON fs.order_id = fo.order_id
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON fs.customer_key = cc.customer_key
    {% endif %}
    WHERE fs.discount_amount > 0
      AND fs.discount_rate IS NOT NULL
      AND fo.is_active_order
    GROUP BY fs.customer_key, fs.order_id, fo.ordered_at
),

line_discount_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key
            ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM line_discount_per_order
),

line_discount_cte AS (
    SELECT
        customer_key,
        MAX(order_line_max_rate) FILTER (WHERE rn_desc = 1) AS last_line_discount_rate,
        MAX(order_line_max_rate)                             AS max_line_discount_rate
    FROM line_discount_ranked
    GROUP BY customer_key
),

-- ── Shared helper: order-level discount facts ─────────────────────────────
-- Used by buckets 2-4. Filter by primary_discount_type per bucket.
order_discount_facts AS (
    SELECT
        customer_key,
        order_id,
        ordered_at,
        max_discount_rate,
        primary_discount_type
    FROM {{ ref('fact_orders') }}
    {% if is_incremental() %}
    INNER JOIN changed_customers cc USING (customer_key)
    {% endif %}
    WHERE is_active_order
      AND max_discount_rate IS NOT NULL
      AND primary_discount_type IS NOT NULL
),

-- ── BUCKET 2: voucher ─────────────────────────────────────────────────────
-- Customer actively redeemed a seller voucher code.
voucher_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM order_discount_facts
    WHERE primary_discount_type = 'voucher_promotional'
),

voucher_cte AS (
    SELECT
        customer_key,
        MAX(max_discount_rate) FILTER (WHERE rn_desc = 1) AS last_voucher_discount_rate,
        MAX(max_discount_rate)                             AS max_voucher_discount_rate
    FROM voucher_ranked
    GROUP BY customer_key
),

-- ── BUCKET 3: campaign ────────────────────────────────────────────────────
-- Merchant proactively applied: bundle deal, CTKM, sampling/gift.
campaign_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM order_discount_facts
    WHERE primary_discount_type IN ('bundle', 'campaign', 'sampling_gift')
),

campaign_cte AS (
    SELECT
        customer_key,
        MAX(max_discount_rate) FILTER (WHERE rn_desc = 1) AS last_campaign_discount_rate,
        MAX(max_discount_rate)                             AS max_campaign_discount_rate
    FROM campaign_ranked
    GROUP BY customer_key
),

-- ── BUCKET 4: negotiated ──────────────────────────────────────────────────
-- Direct deal: đại lý, hợp đồng, nhân viên/CTV, khách US.
negotiated_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM order_discount_facts
    WHERE primary_discount_type IN (
        'negotiated_micro', 'negotiated_standard', 'negotiated_deep',
        'wholesale_explicit', 'employee_internal', 'overseas'
    )
),

negotiated_cte AS (
    SELECT
        customer_key,
        MAX(max_discount_rate) FILTER (WHERE rn_desc = 1) AS last_negotiated_discount_rate,
        MAX(max_discount_rate)                             AS max_negotiated_discount_rate
    FROM negotiated_ranked
    GROUP BY customer_key
),

all_customers AS (
    SELECT DISTINCT customer_key FROM {{ ref('fact_orders') }}
    {% if is_incremental() %}
    INNER JOIN changed_customers cc USING (customer_key)
    {% endif %}
    WHERE is_active_order
)

SELECT
    ac.customer_key,
    ld.last_line_discount_rate,
    ld.max_line_discount_rate,
    v.last_voucher_discount_rate,
    v.max_voucher_discount_rate,
    c.last_campaign_discount_rate,
    c.max_campaign_discount_rate,
    n.last_negotiated_discount_rate,
    n.max_negotiated_discount_rate,
    current_timestamp AS metric_calculated_at
FROM all_customers ac
LEFT JOIN line_discount_cte ld ON ac.customer_key = ld.customer_key
LEFT JOIN voucher_cte        v  ON ac.customer_key = v.customer_key
LEFT JOIN campaign_cte       c  ON ac.customer_key = c.customer_key
LEFT JOIN negotiated_cte     n  ON ac.customer_key = n.customer_key
```

### 2. Create `int_customer_discount_metrics.yml`

```yaml
version: 2

models:
  - name: int_customer_discount_metrics
    description: "Per-customer discount metrics across 4 unified buckets: line_discount, voucher, campaign, negotiated."
    columns:
      - name: customer_key
        tests: [unique, not_null]
      - name: last_line_discount_rate
        description: "Rate (0-1) of item-level discount from most recent order with line discount. NULL = never had line discount."
      - name: max_line_discount_rate
        description: "Highest item-level discount rate ever applied to this customer."
      - name: last_voucher_discount_rate
        description: "Rate from most recent order where customer actively redeemed a voucher."
      - name: max_voucher_discount_rate
        description: "Highest voucher discount rate ever redeemed."
      - name: last_campaign_discount_rate
        description: "Rate from most recent order with merchant-applied promo (bundle/CTKM/sampling)."
      - name: max_campaign_discount_rate
        description: "Highest campaign discount rate ever received."
      - name: last_negotiated_discount_rate
        description: "Rate from most recent order with B2B/direct deal (đại lý/hợp đồng/nhân viên/overseas)."
      - name: max_negotiated_discount_rate
        description: "Highest negotiated discount rate ever."
```

## Success Criteria

- [ ] `int_customer_discount_metrics` exists and materializes without error
- [ ] `SELECT COUNT(*) FROM int_customer_discount_metrics` ~ matches customer count in `fact_orders`
- [ ] Spot-check: WHOLESALE customer has non-null `last_negotiated_discount_rate`
- [ ] Spot-check: frequent buyer has non-null `last_voucher_discount_rate`
- [ ] `line_discount` customers: ~31,890 distinct `customer_key` (bounded by orders with line discounts)
- [ ] All rates are between 0.0 and 1.0 (not percentages)
- [ ] Incremental run processes only changed customers (check logs)

## Risk Assessment

- **Incremental watermark**: uses same `metric_calculated_at - 1 day` pattern as `int_customer_metrics` — consistent
- **NULL for all 3 buckets**: customers who never received any discount → all 6 fields NULL → expected, not a bug
- **Mixed-type orders**: `primary_discount_type` proxy captures the dominant type only; edge case where voucher + negotiated on same order → classified by larger amount → acceptable
- **Rates > 1.0**: impossible if `discount_amount <= unit_price * quantity`, but add note to verify max during QA
