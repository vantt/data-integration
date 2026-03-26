# Research Report: Daily & Yesterday Sales Dashboard Improvement Analysis

> **Date:** 2026-03-26 | **Scope:** `analytics-handbook` playbooks & blueprints for `sales_daily_operation` and `sales_yesterday_operation`

## Executive Summary

Both dashboards cover basic sales metrics (GMV, Orders, AOV, Channel, Top Products, Payment Methods) but **severely underutilize available data models**. `dim_customers` has rich segmentation (VIP/Loyal/Regular, Active/At Risk/Churned) that is only used as simple New/Returning count. `dim_staff`, `dim_geography`, `fact_targets`, and promotion data are completely absent from daily dashboards.

**Key gaps:** No customer segment breakdown, no staff performance, no store comparison, no target tracking, no order status health, no geographic insights. Daily dashboard also lacks Net Revenue and Discount Impact (yesterday has them, today doesn't).

## Research Methodology
- Sources: 8 internal files (playbooks, blueprints, domain definitions, dbt models)
- Cross-referenced: SQL queries in blueprints vs. available columns in dbt models
- Evaluated against: business goal "sell more orders + understand customers better"

## Key Findings

### 1. Inconsistency Between Daily & Yesterday Dashboards

| Metric | Daily (Today) | Yesterday |
|--------|:---:|:---:|
| GMV | Yes | Yes |
| Net Revenue | **NO** | Yes |
| Orders | Yes | Yes |
| AOV | Yes | Yes |
| Return Count | **NO** | Yes |
| Discount Impact | **NO** | Yes |
| DoD % Change | **NO** | Yes |
| New vs Returning | Yes | Yes |

**Problem:** Daily dashboard is weaker than Yesterday's. Store managers monitoring real-time can't see returns, discounts, or Net Revenue — they need to wait until tomorrow.

**Fix:** Add Net Revenue, Return Count, Discount Impact, and DoD % change to Daily dashboard (mirror Yesterday's Section 1 structure).

### 2. Customer Understanding: Severely Underutilized

`dim_customers` already has these fields **ready to use but NOT shown in either dashboard**:

| Available Field | Used? | Impact |
|--------|:---:|--------|
| `customer_segment` (VIP/Loyal/Regular) | NO | Know WHO is buying today |
| `customer_status` (Active/At Risk/Churned) | NO | Spot reactivated churned customers |
| `lifetime_value` | NO | Revenue quality assessment |
| `total_orders_count` | NO | Frequency context |
| `recency_days` | NO | Customer health |

**Current state:** Only "New vs Returning" binary split. This tells you almost nothing actionable.

**Recommended additions:**

#### A. Revenue by Customer Segment (Both dashboards)
```sql
SELECT
    c.customer_segment,
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue",
    ROUND(SUM(o.gmv) * 100.0 / NULLIF(SUM(SUM(o.gmv)) OVER(), 0), 1) as "Revenue %"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 3 DESC
```
**Why:** Shows if revenue is VIP-dependent or broad-based. If 80% from VIP, you need acquisition. If VIP drops, urgent action needed.

#### B. Reactivated Customers (Yesterday dashboard)
```sql
SELECT COUNT(DISTINCT o.customer_key) as "Reactivated Customers"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
  AND c.customer_status IN ('At Risk', 'Churned')
  AND date(c.first_order_date) < current_date - INTERVAL '1 day'
```
**Why:** Tracks win-back success. If a "Churned" customer buys again, that's a signal to replicate whatever brought them back.

#### C. Customer Acquisition Quality
```sql
SELECT
    CASE
        WHEN date(c.first_order_date) = current_date THEN 'New'
        WHEN c.customer_status = 'Churned' THEN 'Reactivated (was Churned)'
        WHEN c.customer_status = 'At Risk' THEN 'Reactivated (At Risk)'
        ELSE 'Active Returning'
    END as "Customer Type",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue",
    ROUND(AVG(o.gmv), 0) as "Avg Order Value"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
```
**Why:** Replaces the simplistic "New vs Returning" with actionable segments. Shows if new customer AOV matches returning — if much lower, first-purchase offers may be too aggressive.

### 3. Missing Operational Metrics

#### A. Order Status Health (Both dashboards)
```sql
SELECT
    status,
    fulfillment_status,
    COUNT(DISTINCT order_id) as "Orders",
    SUM(gmv) as "GMV"
FROM fact_orders
WHERE date(order_timestamp) = current_date
GROUP BY 1, 2
```
**Why:** Catch operational issues early. Spike in "cancelled" = potential system/payment issue. High "unfulfilled" = shipping bottleneck.

#### B. Staff Performance (Both dashboards)
```sql
SELECT
    s.staff_name as "Salesperson",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue",
    ROUND(AVG(o.gmv), 0) as "AOV"
FROM fact_orders o
JOIN dim_staff s ON o.staff_key = s.staff_key
WHERE date(o.order_timestamp) = current_date
  AND s.staff_name != 'Unknown'
GROUP BY 1
ORDER BY 3 DESC
```
**Why:** Identify top performers for daily recognition and underperformers for coaching. Direct lever to sell more.

#### C. Store/Location Comparison (Both dashboards)
```sql
SELECT
    bl.location_name as "Store",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 3 DESC
```
**Why:** Multi-store businesses need per-store visibility. Underperforming store = investigate (staffing, stock, foot traffic).

#### D. Target Achievement (Both dashboards)
Not currently possible at daily grain. `fact_targets` is monthly. But could show:
```sql
-- Monthly target progress (cumulative)
SELECT
    SUM(o.gmv) as "MTD Revenue",
    t.target_revenue as "Monthly Target",
    ROUND(SUM(o.gmv) * 100.0 / NULLIF(t.target_revenue, 0), 1) as "Achievement %"
FROM fact_orders o
CROSS JOIN (SELECT SUM(target_revenue) as target_revenue FROM fact_targets
            WHERE target_month = date_trunc('month', current_date)) t
WHERE date(o.order_timestamp) >= date_trunc('month', current_date)
  AND date(o.order_timestamp) <= current_date
GROUP BY t.target_revenue
```
**Why:** Without target context, revenue numbers are meaningless. "500K today" — is that good or bad?

### 4. Geographic Insights (Missing entirely)

`dim_geography` and shipping address in `fact_orders` are available but unused.

```sql
SELECT
    g.province as "Province",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_geography g ON o.shipping_geography_key = g.geography_key
WHERE date(o.order_timestamp) = current_date
  AND g.province != 'Unknown'
GROUP BY 1
ORDER BY 3 DESC
LIMIT 10
```
**Why:** Understand WHERE customers are. Informs delivery optimization, marketing geo-targeting, and expansion decisions.

### 5. Product Insights Enhancement

Current Top Products shows only name/revenue/units. Missing:
- **Category-level view** — Product Types rollup (`dim_product_types` exists)
- **Average units per order** — basket depth signal

### 6. Time-to-Fulfill Metric (Yesterday only)

`fact_orders.time_to_complete_hours` is computed but never displayed.

```sql
SELECT
    ROUND(AVG(time_to_complete_hours), 1) as "Avg Hours to Complete",
    MAX(time_to_complete_hours) as "Max Hours"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
  AND time_to_complete_hours IS NOT NULL
```
**Why:** Operational efficiency metric. Long fulfillment = customer dissatisfaction = fewer repeat orders.

## Prioritized Recommendations

| Priority | Change | Dashboard | Effort | Impact |
|----------|--------|-----------|--------|--------|
| **P0** | Add Net Revenue, Returns, Discount Impact to Daily | Daily | Low | High — parity with Yesterday |
| **P0** | Add Revenue by Customer Segment (VIP/Loyal/Regular) | Both | Low | High — understand who drives revenue |
| **P1** | Replace "New vs Returning" with 4-way Customer Type split | Both | Low | High — actionable customer insight |
| **P1** | Add Order Status Health (cancelled/returned breakdown) | Both | Low | High — catch operational issues |
| **P1** | Add Staff Performance table | Both | Low | Medium — direct sales lever |
| **P2** | Add Store/Location comparison | Both | Low | Medium — multi-store visibility |
| **P2** | Add MTD Target Achievement | Both | Medium | High — revenue context |
| **P2** | Add Geographic breakdown (Top provinces) | Both | Low | Medium — marketing insight |
| **P3** | Add Time-to-Fulfill metric | Yesterday | Low | Medium — ops efficiency |
| **P3** | Add Product Category rollup | Both | Low | Low — category trends |

## Implementation Notes

- All P0/P1 changes use **existing dbt models** — no new models needed
- Blueprint SQL can be added directly to existing blueprint files
- Playbook visualization tables need corresponding rows added
- Currency should use VND (not USD — current blueprint has USD in column formatting)
- Consider adding DoD % change to Daily dashboard scalars (requires CTE pattern from Yesterday blueprint)

## Unresolved Questions

1. **Daily target granularity:** `fact_targets` appears monthly. Does business want daily pro-rated targets (target/days_in_month)?
2. **Staff attribution:** How complete is `staff_key` mapping in `fact_orders`? If most are "Unknown", Staff Performance chart won't be useful.
3. **Multi-store relevance:** How many active store locations exist? If just 1, Store Comparison is unnecessary.
4. **Heatmap scope:** Daily dashboard heatmap uses `date_trunc('week')` — should it be last 7 days rolling instead?
5. **Currency bug:** Blueprint uses `"currency": "USD"` but domain says VND. Which is correct?
