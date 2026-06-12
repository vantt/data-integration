# Playbook: Order Revenue Explorer [All]

## Overview

- **Audience:** Analyst, Finance
- **Goal:** Audit tool — drill into gross/net/collected revenue at order level to verify numbers from other dashboards.
- **Collection:** `Analytics`
- **Blueprint:** [`blueprints/order_revenue_explorer.md`](../blueprints/order_revenue_explorer.md)

## Data Lineage

- **Core Model:** `fact_orders` + `dim_channels`
- **Scope:** `scope_sales` — all valid sales orders including CANCELLED/Voided (audit requires full picture)

## Filters

- **Date Range:** ordered_at (default: this month)
- **Channel:** Sales channel name

## When to Use

Use this dashboard when a number from another report looks wrong:
1. Finance P&L shows unexpected revenue → pull same date range here, compare totals
2. Channel Profitability gross revenue doesn't match → filter by channel, compare
3. Someone asks "why is net ≠ gross − discount?" → check Tax (VAT) column per order

## Reading Flow

1. Set **date range + channel** to match the suspect report.
2. Check **3 KPI scalars** (Gross / Net / Collected) — these sum the exact same order set as the table below.
3. Scan the **order detail table** — KPI = column sum, so any row-level anomaly is visible.
4. Sort by Gross Revenue DESC to find outliers.
5. Click **Mã đơn** → detailView for full order breakdown.

## Visualizations

| Card | Type | Notes |
|:---|:---|:---|
| Period header | Scalar | Date range + order count (mọi status) |
| Gross Revenue | Scalar | SUM(gross_revenue) — full, no compact rounding |
| Net Revenue | Scalar | SUM(net_revenue) |
| Total Collected | Scalar | SUM(total_collected) |
| Order detail table | Table | Gross → Discount → Tax → Net → Collected per order; Mã đơn links to detailView |

## Key Definitions

| Column | Formula |
|:---|:---|
| Gross Revenue | Total before discount and VAT extraction |
| Discount | Coupon / promotion amount |
| Tax (VAT) | Embedded VAT extracted from total (8/108 or 10/110) |
| Net Revenue | gross_revenue − discount_amount − vat_amount |
| Total Collected | Amount actually collected (≈ gross for COD, may differ for partial) |

## Implementation Notes

- Table shows max ~2000 rows (Metabase limit) — narrow date range for full reconciliation.
- KPI scalars always sum the full filtered set regardless of table row limit.
- CANCELLED/Voided orders are included by design — this is an audit tool, not a revenue report.
- Numbers are full (not compact) to enable exact cross-check against source systems.
