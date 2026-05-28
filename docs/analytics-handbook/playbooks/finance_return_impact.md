# Playbook: Return Impact Analysis [All]

## Overview

- **Audience:** CEO, CFO, Sales Ops Lead
- **Goal:** Track refund liability exposure, detect channels with abnormal return rates, understand return reason breakdown, and monitor daily return volume trends.
- **Collection:** `Finance`
- **Blueprint:** [blueprints/finance_return_impact.md](../blueprints/finance_return_impact.md)

## Data Lineage

- **Returns:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql) — per-return event with refund amount, reason, channel, and timestamps
- **Returns × SKU (approximate):** [`int_return_sku_lines`](../../../transformation/models/intermediate/sapo/int_return_sku_lines.sql) — Case B approximation: all SKUs present in returned orders, refund proportional by line revenue. **Not exact per-SKU accounting.**
- **Orders (for rate/cohort):** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — join on `order_code` to get total order volume and order date
- **Sales lines (denominator for SKU rate):** [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql) — units sold per SKU per period
- **Products:** [`dim_products`](../../../transformation/models/marts/core/dim_products.sql) — SKU code, product name
- **Channels:** [`dim_channels`](../../../transformation/models/marts/core/dim_channels.sql) — join on `channel_key` for channel name and `is_sales_channel` filter

## Domain Metrics

| Metric | Definition Link |
|:---|:---|
| Return Rate MTD | [R1 — Return Rate MTD](../domains/finance.md#r1-return-rate-mtd-ty-le-hoan-hang) |
| Refund Liability | [R2 — Refund Liability](../domains/finance.md#r2-refund-liability-gia-tri-hoan-tien) |
| Avg Days-to-Return | [R3 — Average Days-to-Return](../domains/finance.md#r3-average-days-to-return-so-ngay-trung-binh-den-hoan) |
| Top Return Reason | [R4 — Return Reason Top](../domains/finance.md#r4-return-reason-top-ly-do-hoan-pho-bien) |
| Return Rate by Channel | [R5 — Return Rate by Channel](../domains/finance.md#r5-return-rate-by-channel-ty-le-hoan-theo-kenh) |
| Return Revenue Impact | [R6 — Return Revenue Impact](../domains/finance.md#r6-return-revenue-impact-doanh-thu-bi-hoan) |

## Reading Flow

1. **KPI Overview tab** — Check Return Rate MTD and Refund Liability. Review days-to-return histogram: 0-3d spikes → QC issue; >30d → fraud review.
2. **Channel Analysis tab** — Which channels have > 5% return rate? Focus investigation on top offenders.
3. **Return Reasons tab** — What is the top reason by revenue impact? Is it product quality, sizing, or logistics?
4. **Cohort & Trend tab** — Is daily return volume trending up? What is the typical lag distribution across order cohorts?
5. **Return-prone SKUs tab** — Which SKUs drive the most refund VND? Which have abnormal return rate (>3× portfolio avg)? Check action table for prescriptive next steps per SKU.
6. **Action** — SKU action table routes each SKU to the right owner (QC/Sourcing for defects, Merch for sizing, Ops for wrong-item, Sales Ops otherwise).

## Filters

- **Period:** Default = this month (MTD). Supports date range picker for custom analysis.
- **Channel:** Filter by channel_name to focus on a specific channel.

## Action Triggers

| Metric | Threshold | Owner | Action |
|:---|:---|:---|:---|
| Return Rate MTD | > 5% overall | CFO / Sales Ops | Full investigation: channel breakdown + reason analysis |
| Return Rate by Channel | > 5% any channel | Sales Ops | Channel-level root cause: pricing, product, logistics |
| Days-to-Return: 0-3d bucket | > 20% of returns | Quality / Ops | Pre-ship QC review; possible product mismatch |
| Days-to-Return: >30d bucket | > 10% of returns | Sales Ops | Policy review — fraud risk; tighten return window |
| Refund Liability MTD | > 10% of net revenue | CFO | Emergency review of return policy and channel mix |
| Top Return Reason (volume spike) | > 30% increase MoM | Product / Sourcing | Investigate supplier or product quality issue |
| SKU Return Rate | > 3× portfolio avg | Sales Ops | Immediate investigation per SKU action table |
| SKU Return Rate | > 10% + "loi/defect" reason | QC / Sourcing | Supplier quality review; consider temporary delist |
| SKU Return Rate | > 5% + "size" reason | Merchandise | Update sizing chart / product description |
| SKU Return Rate | > 5% + "sai/wrong" reason | Operations | Picking & packing process audit |
| SKU Refund Amount | > 5M VND MTD | Merchandise / Finance | Priority review: delist vs renegotiate vs reprice |

## Visualizations

### Tab 1: KPI Overview

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Return Rate MTD** | Scalar | [R1](../domains/finance.md#r1-return-rate-mtd-ty-le-hoan-hang) | % — Alert threshold 5% |
| **Refund Liability MTD** | Scalar | [R2](../domains/finance.md#r2-refund-liability-gia-tri-hoan-tien) | VND, compact format |
| **Days-to-Return Histogram** | Stacked Bar | [R3](../domains/finance.md#r3-average-days-to-return-so-ngay-trung-binh-den-hoan) | Buckets: 0-3/4-7/8-14/15-30/>30d, stacked by top-3 reasons. Replaces scalar avg. |
| **Top Return Reason MTD** | Scalar | [R4](../domains/finance.md#r4-return-reason-top-ly-do-hoan-pho-bien) | Text — most frequent reason |

### Tab 2: Channel Analysis

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Return Rate by Channel** | Horizontal Bar | [R5](../domains/finance.md#r5-return-rate-by-channel-ty-le-hoan-theo-kenh) | Sort DESC, red flag > 5% |
| **Channel Return Detail** | Table | [R5](../domains/finance.md#r5-return-rate-by-channel-ty-le-hoan-theo-kenh), [R6](../domains/finance.md#r6-return-revenue-impact-doanh-thu-bi-hoan) | Columns: channel, don hoan, tong don, rate %, gia tri hoan |

### Tab 3: Return Reasons

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Top 10 by Revenue Impact** | Horizontal Bar | [R6](../domains/finance.md#r6-return-revenue-impact-doanh-thu-bi-hoan) | Sort by refund_amount DESC |
| **Top 10 by Volume** | Bar Chart | [R4](../domains/finance.md#r4-return-reason-top-ly-do-hoan-pho-bien) | Sort by COUNT DESC |

### Tab 4: Cohort & Trend

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Daily Return Count (90 days)** | Line Chart | [R1](../domains/finance.md#r1-return-rate-mtd-ty-le-hoan-hang) | Dual axis: count (left) + value (right) |
| **Return Lag Cohort Table** | Table | [R3](../domains/finance.md#r3-average-days-to-return-so-ngay-trung-binh-den-hoan) | order_month × return_month, rate % |

### Tab 5: Return-prone SKUs

> **Data caveat:** `int_return_sku_lines` is a Case B approximation (Sapo API = order-level only). All SKUs in a returned order are included with proportional refund allocation. Use for triage and ranking direction — not precise per-SKU P&L.

| Chart Title | Visualization Type | Notes |
|:---|:---|:---|
| **Top 20 SKUs by Refund Amount (MTD)** | Table | SKU, product name, return count, refund VND. Red flag > 5M VND. |
| **Top 20 SKUs by Return Rate (MTD)** | Table | Return rate %, portfolio avg %, anomaly flag (>3× avg). Min 3 sold orders filter. |
| **Return Reason × Top SKUs Matrix** | Table | Top 15 SKUs × reason: count + refund VND. Reveals concentrated reason per SKU. |
| **SKU Action Table (Prescriptive)** | Table | Return rate + top reason → recommended action + owner. CASE-driven routing. |

## Implementation Notes

### Data Caveats

1. **Empty data:** `fact_order_returns` created 2026-05-27 — may have no data initially. All SQL uses `COALESCE(SUM(...), 0)` and `NULLIF(COUNT, 0)` for safe zero handling.
2. **Return rate grain:** Rate = `COUNT(DISTINCT returned order_codes)` / `COUNT(DISTINCT valid order_codes)`. Do NOT use `COUNT(return events)` as numerator — one order can have multiple return rows.
3. **Refund amount:** `refund_amount` comes from Sapo's `total_amount` on the return event — may be partial refund if only some items returned.
4. **channel_key join:** `fact_order_returns` gets `channel_key` from `fact_orders` via `order_code` join in the mart. Always LEFT JOIN to keep returns even if order is not found.
5. **Days-to-return:** Filter `date_diff(...) >= 0` to exclude edge cases where return_date < order_date (data quality issue).
6. **is_sales_channel filter:** All channel-level queries filter `WHERE c.is_sales_channel = true` to exclude internal/system channels.
7. **return_status / refund_status:** Not filtered in the mart queries by default — include all statuses to get full liability picture. Adjust if only "completed" refunds should count.

### SKU Return Analysis — Approximation Caveats

1. **Sapo returns API is order-level only.** `int_return_sku_lines` includes all SKUs in any returned order. If a customer returned only 1 of 3 SKUs in an order, all 3 appear as "potentially returned."
2. **Refund allocation is proportional by line revenue.** If SKU A = 70% of order revenue, it gets 70% of refund_amount. This is an approximation — actual per-SKU refund is unknown.
3. **Minimum sold_orders >= 3 filter** applied on SKU rate widgets to suppress long-tail noise.
4. **Return rate denominator** is `COUNT(DISTINCT order_id)` from `fact_sales` — not unit quantity. A rate of 5% means 1 in 20 orders containing this SKU was returned (not 1 in 20 units).

### What's NOT Covered

- True per-SKU return accounting (requires Sapo to expose `return_items` in API — not available as of 2026-05-28)
- Return forecast / prediction
- Customer-level return behavior (requires `customer_key` on returns — not yet in mart)
- Return-adjusted margin per SKU (requires COGS from MISA per line — future enhancement via `int_misa_sales_lines` join)
