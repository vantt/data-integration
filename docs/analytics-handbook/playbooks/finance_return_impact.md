# Playbook: Return Impact Analysis [All]

## Overview

- **Audience:** CEO, CFO, Sales Ops Lead
- **Goal:** Track refund liability exposure, detect channels with abnormal return rates, understand return reason breakdown, and monitor daily return volume trends.
- **Collection:** `Finance`
- **Blueprint:** [blueprints/finance_return_impact.md](../blueprints/finance_return_impact.md)

## Data Lineage

- **Returns:** [`fact_order_returns`](../../../transformation/models/marts/sales/fact_order_returns.sql) — per-return event with refund amount, reason, channel, and timestamps
- **Orders (for rate/cohort):** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — join on `order_code` to get total order volume and order date
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

1. **KPI Overview tab** — Check Return Rate MTD and Refund Liability. Are they within acceptable range?
2. **Channel Analysis tab** — Which channels have > 5% return rate? Focus investigation on top offenders.
3. **Return Reasons tab** — What is the top reason by revenue impact? Is it product quality, sizing, or logistics?
4. **Cohort & Trend tab** — Is daily return volume trending up? What is the typical lag (days between order and return)?
5. **Action** — Escalate to Sales Ops for channel-specific interventions; escalate to Product/Sourcing for quality-driven reasons.

## Filters

- **Period:** Default = this month (MTD). Supports date range picker for custom analysis.
- **Channel:** Filter by channel_name to focus on a specific channel.

## Action Triggers

| Metric | Threshold | Owner | Action |
|:---|:---|:---|:---|
| Return Rate MTD | > 5% overall | CFO / Sales Ops | Full investigation: channel breakdown + reason analysis |
| Return Rate by Channel | > 5% any channel | Sales Ops | Channel-level root cause: pricing, product, logistics |
| Avg Days-to-Return | < 2 days | Quality/Ops | Possible product mismatch or fraudulent return pattern |
| Avg Days-to-Return | > 30 days | Sales Ops | Policy review — are returns accepted too late? |
| Refund Liability MTD | > 10% of net revenue | CFO | Emergency review of return policy and channel mix |
| Top Return Reason (volume spike) | > 30% increase MoM | Product / Sourcing | Investigate supplier or product quality issue |

## Visualizations

### Tab 1: KPI Overview

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Return Rate MTD** | Scalar | [R1](../domains/finance.md#r1-return-rate-mtd-ty-le-hoan-hang) | % — Alert threshold 5% |
| **Refund Liability MTD** | Scalar | [R2](../domains/finance.md#r2-refund-liability-gia-tri-hoan-tien) | VND, compact format |
| **Avg Days-to-Return MTD** | Scalar | [R3](../domains/finance.md#r3-average-days-to-return-so-ngay-trung-binh-den-hoan) | Days, 1 decimal |
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

## Implementation Notes

### Data Caveats

1. **Empty data:** `fact_order_returns` created 2026-05-27 — may have no data initially. All SQL uses `COALESCE(SUM(...), 0)` and `NULLIF(COUNT, 0)` for safe zero handling.
2. **Return rate grain:** Rate = `COUNT(DISTINCT returned order_codes)` / `COUNT(DISTINCT valid order_codes)`. Do NOT use `COUNT(return events)` as numerator — one order can have multiple return rows.
3. **Refund amount:** `refund_amount` comes from Sapo's `total_amount` on the return event — may be partial refund if only some items returned.
4. **channel_key join:** `fact_order_returns` gets `channel_key` from `fact_orders` via `order_code` join in the mart. Always LEFT JOIN to keep returns even if order is not found.
5. **Days-to-return:** Filter `date_diff(...) >= 0` to exclude edge cases where return_date < order_date (data quality issue).
6. **is_sales_channel filter:** All channel-level queries filter `WHERE c.is_sales_channel = true` to exclude internal/system channels.
7. **return_status / refund_status:** Not filtered in the mart queries by default — include all statuses to get full liability picture. Adjust if only "completed" refunds should count.

### What's NOT Covered

- Per-SKU return rate (requires `fact_order_returns` → order line items join — not yet available)
- Return forecast / prediction
- Customer-level return behavior (requires `customer_key` on returns — not yet in mart)
