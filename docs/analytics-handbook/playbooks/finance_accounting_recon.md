# Playbook: Accounting Reconciliation Cockpit [Internal]

## Overview

- **Audience:** Accounting Manager, CFO
- **Goal:** Monitor daily reconciliation status between Sapo (order system), MISA (accounting/invoicing), and Shopee (settlement fees). Detect unmatched orders, track drift trends, and surface exceptions for manual follow-up.
- **Tool:** metabase
- **Collection:** `Finance`
- **Blueprint:** [blueprints/finance_accounting_recon.md](../blueprints/metabase/finance_accounting_recon.md)

## Data Lineage

- **Primary source:** [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql) — per-order join of Sapo revenue, MISA COGS, and Shopee fees
- **MISA match proxy:** `has_cogs` flag — TRUE when `int_misa_sales_lines.voucher_no` matched `fact_orders.order_code`
- **Shopee match proxy:** `has_platform_fees` flag — TRUE when `int_shopee_order_fees.order_code` matched
- **Channels:** [`dim_channels`](../../../transformation/models/marts/core/dim_channels.sql) — for channel name and Shopee identification

## Proxy Mode Caveats

**`recon_sapo_orders_daily` and `recon_misa_daily` do not yet exist.** All recon metrics are derived proxies:

| What we want | Proxy used | Accuracy |
|:---|:---|:---|
| Sapo↔MISA invoice match | `has_cogs = TRUE` | ~65% coverage is expected baseline — not a bug |
| Sapo↔Shopee settlement match | `has_platform_fees = TRUE` (Shopee channel only) | Depends on Shopee payout ingestion completeness |
| "Unmatched" reason | Inferred from flag combo | Cannot distinguish "invoice not issued yet" vs "genuinely missing" |
| Last sync timestamp | Not available | Would require `recon_*` tables with `synced_at` column |

When `recon_*` tables are built, update this playbook and the blueprint SQL to query them directly.

## Domain Metrics

| Metric | Definition Link |
|:---|:---|
| MISA Coverage % | [RC1](../domains/finance.md#rc1-misa-coverage--tỷ-lệ-khớp-misa) |
| Unmatched Rate % | [RC2](../domains/finance.md#rc2-unmatched-rate--no-misa-tỷ-lệ-thiếu-misa-invoice) |
| Shopee Fee Coverage % | [RC3](../domains/finance.md#rc3-shopee-fee-coverage--tỷ-lệ-có-dữ-liệu-phí-shopee) |
| Recon Status Distribution | [RC4](../domains/finance.md#rc4-recon-status-distribution-phân-loại-trạng-thái-đối-soát) |
| Daily Unmatched Trend | [RC5](../domains/finance.md#rc5-daily-unmatched-trend-xu-hướng-đơn-chưa-đối-soát-theo-ngày) |
| Shopee Fee Gap | [RC6](../domains/finance.md#rc6-saposhopee-fee-gap-đơn-shopee-thiếu-dữ-liệu-phí) |

## Reading Flow

1. **Recon Status Overview tab** — Check MISA Coverage % and Unmatched Rate. Is MISA coverage above 65%? Is unmatched rate below 30%?
2. **Exception Table tab** — Review unmatched orders by order_code. Are these recent orders (last 7 days) that might not have been invoiced yet, or old orders that are genuinely missing?
3. **Drift Trend tab** — Is the daily unmatched % stable or spiking? A sudden spike on a specific date indicates a Dagster pipeline failure or MISA data export delay.
4. **Reconciliation Funnel tab** — Understand the full coverage picture: what % of completed orders have MISA + Shopee fee data? Check MISA Coverage by Channel for channel-specific gaps.
5. **Action** — Escalate unmatched orders > 7 days old to accounting team for manual MISA invoice check. Escalate Shopee fee gaps to data team to verify Shopee payout ingestion job.

## Filters

- **Period:** Default = past 30 days. Use date range for specific audit windows.

## Action Triggers

| Metric | Threshold | Owner | Action |
|:---|:---|:---|:---|
| MISA Coverage % | < 50% | Accounting Manager | Check MISA AMIS export — ingestion pipeline failure? |
| MISA Coverage % | < 65% (below baseline) | Data Team | Verify `int_misa_sales_lines` freshness via Dagster |
| Unmatched Rate % | > 50% any day | Accounting + Data Team | Emergency: MISA data missing for that date range |
| Daily Unmatched % spike | +20pp above prior 7-day avg | Data Team | Investigate Dagster run for `misa_sales_lines` asset |
| Shopee Fee Coverage % | < 80% | Data Team | Check Shopee payout file ingestion job |
| Unmatched orders > 7 days old | Any | Accounting Manager | Manual MISA invoice lookup for listed order_codes |

## Visualizations

### Tab 1: Recon Status Overview

| Chart Title | Visualization Type | Notes |
|:---|:---|:---|
| **MISA Coverage %** | Scalar | All-time baseline. Alert < 50% |
| **Unmatched Rate %** | Scalar | Inverse of MISA Coverage |
| **Shopee Fee Coverage %** | Scalar | Shopee-channel orders only |
| **Unmatched Orders (30d)** | Scalar | Count — absolute volume check |
| **Recon Status Distribution** | Table | 4 categories with revenue_at_risk |
| **Recon Status Donut** | Pie | Visual % split by category |
| **Revenue at Risk by Status** | Bar | VND at risk per recon category |

### Tab 2: Exception Table

| Chart Title | Visualization Type | Notes |
|:---|:---|:---|
| **Unmatched Orders — Missing MISA** | Table | Top 200 by date DESC, sorted by net_revenue |
| **Shopee Orders Missing Fee Data** | Table | Top 200 Shopee orders without settlement |

### Tab 3: Drift Trend

| Chart Title | Visualization Type | Notes |
|:---|:---|:---|
| **Daily Unmatched % Trend** | Line Chart | 30 days, goal line at 30% |
| **Daily Volume vs Unmatched Count** | Combo (bar+line) | Bar = total orders, Line = unmatched |

### Tab 4: Reconciliation Funnel

| Chart Title | Visualization Type | Notes |
|:---|:---|:---|
| **Reconciliation Funnel** | Bar (horizontal funnel) | 4 steps: Total → MISA → Shopee → Both |
| **MISA Coverage by Channel** | Table | Flag channels with < 50% coverage |
| **Recon Coverage Trend by Month** | Line (dual series) | MISA % vs Shopee Fee % over 6 months |

## Implementation Notes

### Data Caveats

1. **65% baseline is expected:** `has_cogs` ≈ 65% of completed orders is the known baseline — MISA only covers orders with issued invoices in the ingestion date window. Orders before ingestion start OR cancelled orders are correctly excluded.
2. **Shopee-only orders with `has_platform_fees = FALSE`:** Shopee orders without released payouts (`payout_released_at IS NULL`) are excluded from `int_shopee_order_fees` — this is correct behavior, not a gap.
3. **`has_cogs AND has_platform_fees`:** For non-Shopee orders, `has_platform_fees` is always FALSE. The "Fully Reconciled" funnel step only applies to Shopee orders. Non-Shopee orders are "reconciled" if `has_cogs = TRUE`.
4. **date_key is INTEGER (YYYYMMDD format):** All date comparisons cast `current_date` arithmetic to INTEGER via `CAST(... AS INTEGER)` — consistent with other blueprints.
5. **ILIKE '%shopee%' for channel filter:** Matches `int_shopee_order_fees` join pattern. If channel naming convention changes, update this filter.

### What's NOT Covered (requires `recon_*` tables)

- Exact "last sync timestamp" for Sapo↔MISA and MISA↔Shopee
- Invoice-level mismatch (amount mismatch, not just presence/absence)
- Auto-categorized exception reasons (e.g., "fee mismatch" vs "missing invoice" vs "timing lag")
- Click-through drill to full invoice details from exception rows (requires MISA invoice detail table)

### Upgrade Path

When `recon_sapo_orders_daily` and `recon_misa_daily` are available:
1. Update RC1-RC6 SQL in `domains/finance.md` to query the dedicated recon tables
2. Replace proxy-based blueprint SQL with joins to `recon_*` tables
3. Add `last_sync_at` scalars to the Status Overview tab
4. Add "exception reason" column (AMOUNT_MISMATCH, TIMING_LAG, MISSING_INVOICE) to Exception Table
5. Remove "Proxy Mode Notice" block from blueprint header
