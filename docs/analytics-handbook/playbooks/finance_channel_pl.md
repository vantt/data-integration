# Playbook: Channel P&L Deep Dive [Cross]

## Overview

- **Audience:** Finance Director, Sales Director
- **Goal:** Identify which channels are loss-leaders after deducting platform fees, monitor margin trends, and quantify the financial exposure from unprofitable channels.
- **Tool:** metabase
- **Collection:** `Finance`
- **Blueprint:** [blueprints/finance_channel_pl.md](../blueprints/metabase/finance_channel_pl.md)

## Data Lineage

- **Order Economics:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql) — per-order P&L with Sapo revenue, MISA COGS, and Shopee fees pre-joined. Grain: one row per order.
- **MISA Sales Lines:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) — invoice-line COGS and gross profit. Used for COGS ratio cross-check.
- **Channels:** [`dim_channels`](../../../transformation/models/marts/core/dim_channels.sql) — join on `channel_key` for `channel_name` and `is_sales_channel` filter.

## Key Coverage Constraint

`fact_order_economics` only covers orders matched in MISA (~65% of completed orders). All queries filter `has_cogs = true` to ensure COGS data is present. Orders without COGS are excluded from margin calculations — margin figures reflect the matched subset, not total GMV.

## Domain Metrics

| Metric | Definition Link |
|:---|:---|
| Channel Net Margin % | [CPL1 — Channel Net Margin %](../domains/finance.md#cpl1-channel-net-margin--biên-lợi-nhuận-ròng-kênh) |
| Loss Leader Flag | [CPL2 — Loss Leader Flag](../domains/finance.md#cpl2-loss-leader-flag-cờ-kênh-lỗ) |
| Channel Variance vs Prior | [CPL3 — Channel Variance vs Prior Period](../domains/finance.md#cpl3-channel-variance-vs-prior-period-biến-động-so-với-kỳ-trước) |
| Waterfall Components | [CPL4 — Waterfall Components](../domains/finance.md#cpl4-waterfall-components-thành-phần-thác-nước-pl) |
| Channel Scorecard | [CPL5 — Channel Scorecard](../domains/finance.md#cpl5-channel-scorecard-bảng-điểm-kênh) |
| Margin Heatmap | [CPL6 — Net Margin % Heatmap](../domains/finance.md#cpl6-net-margin--heatmap--channel--month) |

## Reading Flow

1. **P&L Waterfall tab** — Start here. See where revenue is lost: discounts → COGS → platform fees → net profit. If platform fees dwarf COGS as a deduction, Shopee economics need attention.
2. **Channel Scorecard tab** — Scan the table sorted by Net Margin % ascending. Red rows (< 0%) are loss-leaders requiring immediate action.
3. **Margin Heatmap tab** — Look for channels that are consistently red across months vs. those that spiked recently. Sustained red = structural problem. One-month spike = event-driven (campaign, fee change).
4. **Variance Analysis tab** — Check `Delta Margin pp` column. Channels with > -5 pp MoM decline need investigation even if still profitable.
5. **Loss-Leader Alert tab** — Use as daily/weekly check. If `So kenh lo > 0`, drill to the detail table for root cause.

## Filters

- **Period:** Default = this month (MTD). Supports date range picker. Note: YoY analysis requires setting date range manually (same month last year).
- **Channel:** Narrows all tabs to a single channel for deep-dive. Leave blank for cross-channel view.

## Action Triggers

| Metric | Threshold | Owner | Action |
|:---|:---|:---|:---|
| Net Margin % any channel | < 0% | Finance Director + Sales Director | Immediate review: pricing strategy + platform fee negotiation |
| Net Margin % trend | -5 pp MoM decline | Finance Director | Root cause: fee increase? Voucher campaign? Discount spike? |
| Platform Fees / Net Revenue | > 15% | Sales Director | Renegotiate Shopee fee tier or adjust pricing to compensate |
| Loss-leader count | > 1 channel | CFO | Cross-channel subsidy audit — is loss strategic or accidental? |
| Gross Margin % | < 25% any channel | Merchandising + Finance | COGS review: supplier pricing or product mix shift |
| Channel not in scorecard | Missing channel | Data Team | Verify `has_cogs` coverage for that channel in MISA |

## Visualizations

### Tab 1: P&L Waterfall

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **P&L Waterfall — All Channels** | Waterfall | [CPL4](../domains/finance.md#cpl4-waterfall-components-thành-phần-thác-nước-pl) | 6 bars: Gross → Discounts → Net → COGS → Fees → Net Profit |

### Tab 2: Channel Scorecard

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Channel Scorecard Table** | Table | [CPL5](../domains/finance.md#cpl5-channel-scorecard-bảng-điểm-kênh) | Sorted Net Margin % ASC; red row if < 0%, green if ≥ 20% |

### Tab 3: Margin Heatmap

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Net Margin Heatmap — Channel × Month** | Pivot Table | [CPL6](../domains/finance.md#cpl6-net-margin--heatmap--channel--month) | 12-month rolling window, color range -20% to +40% |

### Tab 4: Variance Analysis

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Channel MoM Variance Table** | Table | [CPL3](../domains/finance.md#cpl3-channel-variance-vs-prior-period-biến-động-so-với-kỳ-trước) | Sorted Delta Margin pp ASC; red row if Delta < -5 pp |
| **Net Margin Trend by Channel** | Multi-line | [CPL6](../domains/finance.md#cpl6-net-margin--heatmap--channel--month) | 12-month trend, one line per channel |

### Tab 5: Loss-Leader Alert

| Chart Title | Visualization Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **So kenh lo** (Loss Channel Count) | Scalar | [CPL2](../domains/finance.md#cpl2-loss-leader-flag-cờ-kênh-lỗ) | Alert if > 0 |
| **Tong lo** (Total Loss Exposure) | Scalar | [CPL2](../domains/finance.md#cpl2-loss-leader-flag-cờ-kênh-lỗ) | VND compact, shows financial magnitude |
| **Loss Leader Detail Table** | Table | [CPL2](../domains/finance.md#cpl2-loss-leader-flag-cờ-kênh-lỗ) | Only channels with Net Profit < 0; full row highlighted red |

## Implementation Notes

### Data Caveats

1. **COGS coverage ~65%:** `has_cogs = true` filter required. Channels with low MISA match rate (e.g., new channels) may appear to have better margins than reality. Cross-check with `int_misa_sales_lines` gross margin for those channels.
2. **Shopee fees sign:** In `fact_order_economics`, `shopee_platform_fees`, `shopee_infra_fee`, `shopee_voucher_xtra_fee`, `shopee_taxes` are already negative values (deductions). The `channel_net_profit` formula adds them (since they are negative). Do NOT negate again when summing.
3. **Non-Shopee channels:** `shopee_*` columns are NULL for non-Shopee orders. `COALESCE(..., 0)` guards handle this. `channel_net_profit` equals `gross_profit` for non-Shopee channels.
4. **date_key format:** `date_key` is an INTEGER (YYYYMMDD format). Cast via `CAST(CAST(date_key AS VARCHAR) AS DATE)` for date comparisons.
5. **Status filter:** Use `status NOT IN ('CANCELLED', 'Voided')` — this matches the mart's own filter logic. Do NOT use `status = 'COMPLETED'` alone as it would exclude in-progress orders.
6. **is_sales_channel:** Always filter `dim_channels.is_sales_channel = true` to exclude internal/system/warehouse channels.
7. **Variance MoM:** Current period = month-to-date (date >= first of current month AND < today). Prior period = full prior month. This means early in the month, variance may be misleading — note this to users.

### What's NOT Covered

- YoY variance (requires manual date range setting — not wired to a YoY filter by default)
- Per-SKU profitability within a channel (requires `fact_order_economics` → order line items join — use Product Cost-to-Margin Heatmap dashboard)
- Operational cost allocation (rent, staff, logistics) — not in `fact_order_economics`, requires GL integration
- Return impact on channel P&L (returns recognized at return date in `fact_order_returns`, not restated in original order economics)
