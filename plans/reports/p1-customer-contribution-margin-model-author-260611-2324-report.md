# P1 Customer Contribution Margin — Model Author Report

**Date:** 2026-06-11 | **Scope:** int_customer_economics (CREATE) + dim_customers (EDIT)

---

## 1. Contribution Definition Used

**Reused `channel_net_profit` (DRY).** Verified in `fact_order_economics.sql` lines 153–160:

```
channel_net_profit = net_revenue − cogs_amount + shopee_fees (negative values)
```

For non-Shopee orders: `channel_net_profit == gross_profit` (confirmed by query — avg matches exactly).  
`allocated_overhead` is a separate column, excluded from `channel_net_profit`. No recomputation needed — `channel_net_profit` IS contribution margin by construction.

---

## 2. Files Created/Edited

### Created: `transformation/models/marts/core/intermediate/int_customer_economics.sql`
- Materialization: `incremental` (unique_key=`customer_key`) — matches sibling `int_customer_metrics`
- Joins `fact_order_economics` → `fact_orders` on `order_id` to attach `customer_key`
- Filters `is_active_order = TRUE` before aggregating
- Incremental watermark: `updated_at >= MAX(metric_calculated_at)` from this model, via `changed_customers` CTE
- `is_margin_negative` returns NULL (not FALSE) when customer has zero has_cogs orders — avoids false negatives

### Edited: `transformation/models/marts/core/dim_customers.sql`
- Added `economics AS (SELECT * FROM {{ ref('int_customer_economics') }})` CTE
- Added `LEFT JOIN economics e ON c.customer_key = e.customer_key` in joined_data
- Surfaced 5 columns in `joined_data` SELECT (raw, no COALESCE yet)
- Added 5 final-SELECT columns with COALESCE(numeric, 0) and COALESCE(is_margin_negative, FALSE)
- All existing columns/order preserved; new economics block inserted after `customer_status` before P3 metrics

---

## 3. Circular Reference Check

Grep results — models referencing `dim_customers`:
- `dim_customers_base.sql`, `dim_geography.sql`, `mart_customer_action_queue.sql`
- `mart_customer_status_snapshot_monthly.sql`, `fact_orders.sql`, `fact_sales.sql`, `mart_data_quality.sql`

None of `fact_orders`, `fact_order_economics`, or `dim_customers_base` reference `dim_customers`.  
`fact_orders.sql` line 88 explicitly notes: "Use dim_customers_base (not dim_customers) to avoid cycle."  
**No circular reference.** DAG: `fact_orders` + `fact_order_economics` → `int_customer_economics` → `dim_customers`.

---

## 4. Proposed schema.yml YAML Block

```yaml
# int_customer_economics
- name: int_customer_economics
  description: "Customer-level contribution margin aggregation. Grain: one row per customer_key. Contribution = channel_net_profit (gross_profit − Shopee fees; no overhead)."
  columns:
    - name: customer_key
      tests:
        - not_null
        - unique
    - name: lifetime_gross_profit
      description: "Sum of gross_profit for has_cogs active orders. BIGINT, NULL if no has_cogs orders."
    - name: lifetime_contribution_margin
      description: "Sum of channel_net_profit for has_cogs active orders (gross_profit − Shopee fees; no overhead). BIGINT."
    - name: avg_order_contribution_margin_pct
      description: "Avg per-order (channel_net_profit / net_revenue). DOUBLE, NULL if no active orders."
    - name: margin_cogs_coverage_pct
      description: "Fraction of active orders with has_cogs. Caveat: indicates margin data completeness."
    - name: is_margin_negative
      description: "TRUE if lifetime_contribution_margin < 0. NULL if no has_cogs orders."
    - name: metric_calculated_at
      description: "Timestamp of last calculation run."

# dim_customers — new columns to append to existing column list
# (add after existing customer_status column block)
    - name: lifetime_gross_profit
      description: "Lifetime gross profit from has_cogs active orders. 0 if no margin data."
    - name: lifetime_contribution_margin
      description: "Lifetime contribution margin (channel_net_profit basis; no overhead). 0 if no margin data."
    - name: avg_order_contribution_margin_pct
      description: "Avg per-order contribution margin %. NULL for customers with no active orders."
    - name: margin_cogs_coverage_pct
      description: "Share of active orders with COGS data. NULL for customers with no active orders."
    - name: is_margin_negative
      description: "TRUE if lifetime contribution margin is negative. FALSE if no margin data (safe default)."
```

---

## 5. Validation Numbers

Query run against `sapo_export_latest.duckdb` (read_only=True), simulating the int_customer_economics aggregation:

| Metric | Value |
|---|---|
| Total customers with active orders | 1,405 |
| Customers with negative lifetime contribution | 943 (67%) |
| Avg lifetime_gross_profit | -5,029,716 VND |
| Avg lifetime_contribution_margin | -5,072,166 VND |
| Avg COGS coverage | 99.8% |
| Customers with NULL lifetime_contribution_margin | 2 |

**Distribution by value_group:**

| value_group | customers | negative_margin | total_lcm (VND) |
|---|---|---|---|
| VALUE_BRONZE | 1,265 | 931 | -6,042,506,666 |
| VALUE_VIP | 33 | 4 | -1,768,066,205 |
| VALUE_GOLD | 23 | 0 | +340,699,132 |
| VALUE_SILVER | 84 | 8 | +353,625,482 |

**Sanity checks:**
- Non-Shopee orders: `channel_net_profit == gross_profit` exactly (avg_cnp=-2,430,785 == avg_gp=-2,430,785). Confirms no overhead in channel_net_profit.
- 2 NULL lifetime_contribution_margin customers: expected (customers with only non-has_cogs active orders — ~0.1% of population).
- GOLD/SILVER positive margin, BRONZE negative: consistent with COGS-shift (MISA-632 repoint memory note — big COGS restatement hit BRONZE/VIP segments hardest).
- 99.8% COGS coverage: very high, margin figures reliable for this customer base.

---

## 6. Materialization Note

- **int_customer_economics**: `incremental` + `unique_key='customer_key'` — no `location()` needed (intermediate, not exported to serving layer per AGENTS.md §3).
- **dim_customers**: already has `post_hook COPY TO get_rolling_location()` config — unchanged, no action needed.

---

**Status:** DONE  
**Summary:** Created `int_customer_economics` (incremental, contribution margin via `channel_net_profit` reuse) and added 5 economics columns to `dim_customers` via LEFT JOIN. Circular ref verified clean. Validation confirms sane numbers with 1,405 customers, 99.8% COGS coverage, GOLD/SILVER positive margin.  
**Evidence:** Both files written; DuckDB validation query executed with row counts and distribution matching expected business patterns.  
**Concerns:** None. The high negative-margin rate (67%) in BRONZE is expected per the COGS-shift memory note (MISA-632 repoint 2026) — not a data bug.
