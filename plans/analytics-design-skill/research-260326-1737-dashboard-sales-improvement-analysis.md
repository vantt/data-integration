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

**Reality check:** For a live dashboard, full-day DoD should not be the first comparison. A **same-hour pace vs yesterday** view is a better decision aid during the day, because it shows whether the team is behind schedule before the day closes.

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
WITH ordered_customers AS (
    SELECT
        customer_key,
        order_id,
        order_timestamp,
        LAG(order_timestamp) OVER (
            PARTITION BY customer_key
            ORDER BY order_timestamp
        ) as previous_order_timestamp
    FROM fact_orders
    WHERE date(order_timestamp) <= current_date - INTERVAL '1 day'
)
SELECT
    COUNT(DISTINCT CASE
        WHEN previous_order_timestamp IS NOT NULL
         AND date_diff('day', previous_order_timestamp, order_timestamp) BETWEEN 31 AND 90
        THEN customer_key END) as "Reactivated (31-90d gap)",
    COUNT(DISTINCT CASE
        WHEN previous_order_timestamp IS NOT NULL
         AND date_diff('day', previous_order_timestamp, order_timestamp) > 90
        THEN customer_key END) as "Reactivated (>90d gap)"
FROM ordered_customers
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```
**Why:** `dim_customers.customer_status` is a current snapshot derived from `recency_days`, so it is not reliable for labeling historical orders. Using the gap since the previous order is more faithful to actual reactivation behavior.

#### C. Customer Acquisition Quality (Initial Heuristic)
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

**Reality check:** The SQL above uses current `dim_customers.customer_status`, which is a current-state snapshot. For historical day analysis, prefer gap-based classification from order history:

```sql
WITH ordered_customers AS (
    SELECT
        o.customer_key,
        o.order_id,
        o.order_timestamp,
        o.gmv,
        LAG(o.order_timestamp) OVER (
            PARTITION BY o.customer_key
            ORDER BY o.order_timestamp
        ) as previous_order_timestamp
    FROM fact_orders o
),
classified AS (
    SELECT
        CASE
            WHEN previous_order_timestamp IS NULL THEN 'New'
            WHEN date_diff('day', previous_order_timestamp, order_timestamp) > 90 THEN 'Reactivated (>90d gap)'
            WHEN date_diff('day', previous_order_timestamp, order_timestamp) BETWEEN 31 AND 90 THEN 'Reactivated (31-90d gap)'
            ELSE 'Active Returning'
        END as "Customer Type",
        order_id,
        gmv
    FROM ordered_customers
    WHERE date(order_timestamp) = current_date
)
SELECT
    "Customer Type",
    COUNT(DISTINCT order_id) as "Orders",
    SUM(gmv) as "Revenue",
    ROUND(AVG(gmv), 0) as "Avg Order Value"
FROM classified
GROUP BY 1
```

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
    s.full_name as "Salesperson",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue",
    ROUND(AVG(o.gmv), 0) as "AOV"
FROM fact_orders o
JOIN dim_staff s ON o.staff_key = s.staff_key
WHERE date(o.order_timestamp) = current_date
  AND s.full_name != 'Unknown Staff'
GROUP BY 1
ORDER BY 3 DESC
```
**Why:** Identify top performers for daily recognition and underperformers for coaching. Direct lever to sell more.

#### C. Store/Location Comparison (Both dashboards)
```sql
SELECT
    bl.branch_location_name as "Store",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 3 DESC
```
**Why:** Multi-store businesses need per-store visibility. Underperforming store = investigate (staffing, stock, foot traffic).

#### D. Target Achievement (Both dashboards, First-Pass Concept)
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

**Reality check:** The target example above is directionally useful but does not match the current schema exactly. `fact_targets` currently exposes `target_date`, `metric_code`, and `target_val`, so implementation should be validated against those fields before dashboard rollout. For branch/channel/staff target comparison, follow the Sales domain warning and use a pre-aggregated model rather than a direct order-to-target join.

#### E. Payment Method Chart Needs Correction Before Decision-Making

Current dashboard blueprints query `fact_payments` by date only, while the Sales domain definition specifies filtering to completed payments.

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transaction Count",
    SUM(p.amount) as "Total Amount"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) = current_date
  AND p.status = 'completed'
GROUP BY 1
```

**Why:** If pending or failed attempts are included, the payment mix can be distorted and lead to bad conclusions about customer payment behavior.

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

### 7. Missing Decision Map For Sales Team

The report is technically useful, but it becomes more actionable for sales when each signal is tied to an immediate action.

| Signal on Dashboard | Likely Meaning | Immediate Sales / Ops Action |
|--------|--------|--------|
| **Behind same-hour pace** | Demand or conversion is soft today | Trigger outbound calls, live push, staff reallocation, campaign reminder |
| **Cancelled / unpaid orders spike** | Payment friction or poor follow-up | Call high-GMV pending orders first, check payment issue, review staff handling |
| **VIP revenue share drops** | Core customer base is cooling | Prioritize VIP outreach, check stock/service issues on high-value products |
| **New customer AOV is much lower than returning** | Acquisition quality is weak or discounts too deep | Review first-order offers, tighten low-quality promotion channels |
| **One store or one channel underperforms** | Local execution issue | Compare staffing, stock, and active promotions with better-performing peers |
| **Discount value rises without order lift** | Promo is burning margin without creating demand | Pause or narrow discount scope, inspect products/channels absorbing discount cost |

## Initial Prioritized Recommendations

This table reflects the first pass of prioritization. For rollout, use the revised action-first order in the next section.

| Priority | Change | Dashboard | Effort | Impact | Status |
|----------|--------|-----------|--------|--------|--------|
| **P0** | Add Net Revenue, Returns, Discount Impact to Daily | Daily | Low | High — parity with Yesterday | ✅ Done |
| **P0** | Add Revenue by Customer Segment (VIP/Loyal/Regular) | Both | Low | High — understand who drives revenue | ✅ Done |
| **P1** | Replace "New vs Returning" with 4-way Customer Type split | Both | Low | High — actionable customer insight | ⚠️ Partial — segment breakdown added but uses current-state dim_customers, not gap-based logic |
| **P1** | Add Order Status Health (cancelled/returned breakdown) | Both | Low | High — catch operational issues | ⚠️ Partial — Orders by Status pie added; no rescue queue/funnel |
| **P1** | Add Staff Performance table | Both | Low | Medium — direct sales lever | ❌ Not done |
| **P2** | Add Store/Location comparison | Both | Low | Medium — multi-store visibility | ✅ Done (Sales by Branch table) |
| **P2** | Add MTD Target Achievement | Both | Medium | High — revenue context | ❌ Not done |
| **P2** | Add Geographic breakdown (Top provinces) | Both | Low | Medium — marketing insight | ❌ Not done |
| **P3** | Add Time-to-Fulfill metric | Yesterday | Low | Medium — ops efficiency | ❌ Not done |
| **P3** | Add Product Category rollup | Both | Low | Low — category trends | ✅ Done (Revenue by Product Type) |

## Revised Priority Order For Sales Action

After checking the report against the actual schema and dashboard usage, the action-first rollout order should be:

| Priority | Change | Dashboard | Why it should move first | Status |
|--------|--------|--------|--------|--------|
| **P0** | Add same-hour Sales Pace vs Yesterday | Daily | Best real-time orientation metric for deciding whether the team is behind now | ✅ Done (Hourly Sales Trend + Cumulative Revenue charts) |
| **P0** | Add Revenue by Customer Segment (VIP/Loyal/Regular) | Both | Immediately improves customer understanding and revenue quality visibility | ✅ Done |
| **P1** | Add Order Status Health and rescue queue | Both | Most direct operational lever to recover orders before they are lost | ⚠️ Partial — status distribution done; rescue queue not added |
| **P1** | Add Net Revenue, Returns, Discount Impact to Daily | Daily | Closes important blind spots in today's decision-making | ✅ Done |
| **P1** | Add DoD driver table by channel / store / segment | Yesterday | Helps managers understand why performance changed and what to fix today | ⚠️ Partial — Channel Performance table done; no segment-level DoD breakdown |
| **P2** | Replace New vs Returning with gap-based customer type logic | Both | More accurate than current-state customer status for reactivation analysis | ⚠️ Partial — segment breakdown exists but uses dim_customers snapshot, not gap-based |
| **P2** | Correct Payment Method chart to completed payments only | Both | Prevents misleading interpretation of customer payment behavior | ❓ Unknown — not verified in blueprint SQL |
| **P2** | Add Staff / Store comparison | Both | Useful execution lever after core rescue and customer views are in place | ⚠️ Partial — Store/Branch done; Staff Performance not added |
| **P3** | Add MTD Target Achievement after validating `metric_code` | Both | Valuable, but should wait until target logic is confirmed against actual schema | ❌ Not done |
| **P3** | Add geography / product-type rollups / time-to-fulfill | Both / Yesterday | Helpful secondary diagnostics after the main action loops are covered | ⚠️ Partial — Product Type done; geography and time-to-fulfill not added |

## Additional Recommendations From Deeper Handbook Review

These additions focus less on passive reporting and more on helping the team sell more orders today while understanding customer quality more deeply.

### 1. Reframe Daily Dashboard Around Sales Rescue ⚠️ Partial

Current Daily dashboard is dominated by lagging outcomes (GMV, Orders, AOV). That is useful, but it does not tell managers where they can still recover missed orders during the day.

**Recommended additions for Daily dashboard:**

- **Sales Pace vs Same Hour Yesterday** ✅ Done — Hourly Sales Trend + Cumulative Revenue charts added
- **Order Status Funnel** ⚠️ Partial — Orders by Status pie added; no funnel view with payment_status + fulfillment_status breakdown
- **Pending / Unpaid / Cancelled Queue** ❌ Not done — no rescue queue table
- **MTD Progress / Pace to Target** ❌ Not done

**Suggested SQL: Sales pace by hour**

```sql
WITH today_hourly AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        COUNT(DISTINCT order_id) as orders_today,
        SUM(gmv) as revenue_today
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
    GROUP BY 1
),
yesterday_hourly AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        COUNT(DISTINCT order_id) as orders_yesterday,
        SUM(gmv) as revenue_yesterday
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(t.hour_of_day, y.hour_of_day) as hour_of_day,
    SUM(COALESCE(t.revenue_today, 0)) OVER (ORDER BY COALESCE(t.hour_of_day, y.hour_of_day)) as cumulative_revenue_today,
    SUM(COALESCE(y.revenue_yesterday, 0)) OVER (ORDER BY COALESCE(t.hour_of_day, y.hour_of_day)) as cumulative_revenue_yesterday,
    SUM(COALESCE(t.orders_today, 0)) OVER (ORDER BY COALESCE(t.hour_of_day, y.hour_of_day)) as cumulative_orders_today,
    SUM(COALESCE(y.orders_yesterday, 0)) OVER (ORDER BY COALESCE(t.hour_of_day, y.hour_of_day)) as cumulative_orders_yesterday
FROM today_hourly t
FULL OUTER JOIN yesterday_hourly y ON t.hour_of_day = y.hour_of_day
ORDER BY 1
```

**Business value:** If the dashboard shows the team is behind pace by 14:00, they still have time to trigger outbound calls, staff reallocation, live-stream pushes, or remarketing.

### 2. Make Yesterday Dashboard Explain the "Why", Not Only the "What" ⚠️ Partial

Yesterday dashboard already has DoD metrics, but it still behaves like a scoreboard. To improve next-day execution, it should explain the main drivers behind the change.

**Recommended additions for Yesterday dashboard:**

- **DoD Driver Table by Channel / Store / Customer Segment** ⚠️ Partial — Channel Performance vs Day Before exists; no store-level or segment-level DoD breakdown
- **Lost Revenue Breakdown** ❌ Not done — Discount Impact table exists but no cancellation/return revenue loss breakdown
- **Winners / Losers Table** ❌ Not done
- **Direct drill-through to Orders Reconciliation** ❓ Unknown — not verified

**Suggested SQL: DoD drivers by customer segment**

```sql
WITH yesterday AS (
    SELECT
        COALESCE(c.customer_segment, 'Unknown') as customer_segment,
        COUNT(DISTINCT o.order_id) as orders_yesterday,
        SUM(o.gmv) as revenue_yesterday
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
),
day_before AS (
    SELECT
        COALESCE(c.customer_segment, 'Unknown') as customer_segment,
        COUNT(DISTINCT o.order_id) as orders_day_before,
        SUM(o.gmv) as revenue_day_before
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '2 days'
    GROUP BY 1
)
SELECT
    COALESCE(y.customer_segment, d.customer_segment) as "Customer Segment",
    COALESCE(y.orders_yesterday, 0) as "Orders Yesterday",
    COALESCE(d.orders_day_before, 0) as "Orders Day Before",
    COALESCE(y.revenue_yesterday, 0) as "Revenue Yesterday",
    COALESCE(d.revenue_day_before, 0) as "Revenue Day Before",
    COALESCE(y.revenue_yesterday, 0) - COALESCE(d.revenue_day_before, 0) as "Revenue Delta"
FROM yesterday y
FULL OUTER JOIN day_before d ON y.customer_segment = d.customer_segment
ORDER BY 6 DESC
```

**Business value:** A manager can immediately see whether the drop came from VIP customers, a specific channel, or one weak store instead of reacting blindly to total revenue.

### 3. Pull Operational Customer Watchlists Into Sales Dashboards ⚠️ Partial

The handbook already has a separate Customer Operational Dashboard with actionable lists, but the two sales dashboards do not reuse that logic enough.

**High-value additions already supported by existing models:**

- **Revenue by VIP / Loyal / Regular** ✅ Done — Revenue by Customer Segment chart added to both dashboards
- **VIP Watchlist** ❌ Not done — no watchlist table with lifetime_value and last_order_date
- **At Risk Reactivation Watchlist** ❌ Not done — At Risk Customers scalar exists but no watchlist table
- **Customer Quality Table for New Buyers** ❌ Not done

**Why this matters:** "New vs Returning" is too shallow. A day with more orders is not equally good if those orders come mostly from low-value one-time buyers with deep discounts.

### 4. Reduce Dashboard Clutter and Prioritize Actionable Visuals ⚠️ Partial

The design guide says operations dashboards should follow a top-down flow and avoid too many primary charts. Today, both dashboards still spend prime space on charts that are more diagnostic than actionable.

**Recommended layout changes:**

- Keep first row as **scalar cards**, not a single wide summary table ✅ Done — KPI scalars are the first row
- Keep primary visuals to **6-8 main elements** maximum ❌ Not done — both dashboards have 18+ visual elements
- Move **Payment Methods** and **Hourly Heatmap** below the fold or into a secondary section ❌ Not verified
- Add **click-to-filter drill-down** from KPI cards and charts into detail tables ❌ Not done (Metabase limitation)
- Link directly to `orders_today` / `orders_yesterday` reconciliation dashboards when anomalies are detected ❓ Unknown

**Why:** Managers scan dashboards in seconds. The first screen should answer:

1. Are we ahead or behind?
2. Where are orders getting stuck?
3. Which customers, stores, or channels need action now?

### 5. Add Domain Definitions Before Blueprint Expansion ❌ Not done

Per `analytics-handbook/AGENTS.md`, new calculation logic should not be invented directly inside playbooks or blueprints.

Before implementing the deeper improvements above, define or extend these metrics in the relevant domain files:

- `domains/sales.md` ❌ Not updated
  - Sales Pace vs Same Hour Yesterday
  - Order Status Funnel / Queue Health
  - Lost Revenue by Cancellation / Return / Discount
  - DoD Driver by Channel / Store
- `domains/customer.md` ❌ Not updated
  - Revenue by Customer Segment
  - Reactivated Customers
  - Customer Acquisition Quality

This keeps `Domain -> Playbook -> Blueprint` traceability clean and reduces future drift.

## Implementation Notes

- All P0/P1 changes use **existing dbt models** — no new models needed
- Blueprint SQL can be added directly to existing blueprint files
- Playbook visualization tables need corresponding rows added
- Currency should use VND (not USD — current blueprint has USD in column formatting)
- Consider adding DoD % change to Daily dashboard scalars (requires CTE pattern from Yesterday blueprint)
- Treat current `dim_customers.customer_status` and `customer_segment` as current-state attributes; for older-date analysis, historical classification may need window logic or a dedicated snapshot model

- Follow the handbook golden rule: update metric definitions in `domains/*.md` before expanding `playbooks/*.md` or `blueprints/*.md`

## Unresolved Questions

1. **Daily target granularity:** `fact_targets` appears monthly. Does business want daily pro-rated targets (target/days_in_month)?
2. **Staff attribution:** How complete is `staff_key` mapping in `fact_orders`? If most are "Unknown", Staff Performance chart won't be useful.
3. **Multi-store relevance:** How many active store locations exist? If just 1, Store Comparison is unnecessary.
4. **Heatmap scope:** Daily dashboard heatmap uses `date_trunc('week')` — should it be last 7 days rolling instead?
5. **Currency bug:** Blueprint uses `"currency": "USD"` but domain says VND. Which is correct?
