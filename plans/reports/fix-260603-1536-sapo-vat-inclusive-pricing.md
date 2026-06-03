# Fix: Sapo selling price is VAT-inclusive — strip embedded VAT across pipeline

**Date:** 2026-06-03 | **Branch:** main | **Strategy:** Trust Sapo `$.total_tax` (user-approved)

## Root cause (verified with real data)

Sapo selling prices (giá bán) are **VAT-inclusive**. The pipeline wrongly treated `$.total` as
pre-tax net and **added** VAT on top for `total_collected`.

Evidence (1,357 taxed orders, latest `fact_orders` parquet):
- `tax / net` clusters at **0.07407 = 8/108** (1083 orders) + **0.0909 = 10/110** (148 orders).
  → embedded VAT, NOT additive (additive would give exactly 0.08).
- Sapo provides exact embedded VAT per order in `$.total_tax` (8/108, 10/110, or 0 for exports).
- 60% of orders have `tax = 0`: US channel 99.6% zero-tax (exports, own VAT-aware mart), retail/POS scattered.

## The bug (fact_orders.sql, pre-fix)

| Column | Old formula | Problem |
|---|---|---|
| `net_revenue` | `total_amount` | gross w/ VAT inside → overstated ~7.4% |
| `total_collected` | `total_amount + tax_amount` | **double-counts VAT** → overstated 8% |
| `gross_profit`, margins, LTV, AOV, SKU margins | inherit above | all overstated |

## Fix applied (earliest meaningful layer)

**1. `transformation/models/marts/sales/fact_orders.sql`** — revenue waterfall (single canonical definition):
- `net_revenue   = total_amount - COALESCE(total_tax_amount,0)`  (VAT-exclusive)
- `total_collected = total_amount`  (gross = giá bán, VAT inside — no addition)
- `tax_amount`, `gross_revenue`, `discount_amount` unchanged.

**2. `transformation/models/marts/sales/fact_sales.sql`** — line-level revenue → VAT-exclusive via the
order's exact VAT ratio `(total_amount - tax)/total_amount`; exports (tax=0) keep full amount; 8%/10% auto-handled.

**3. `docs/analytics-handbook/guides/revenue_terminology.md`** — rewrote waterfall, example, mapping &
formula blocks to embedded-VAT model (was stating `$.total` = pre-tax, which was wrong).

**Auto-corrected downstream (no edit needed — they inherit `net_revenue`/`total_collected`):**
`fact_order_economics` (gross_profit, gross_margin_pct, channel_net_profit/margin),
`int_customer_metrics` → `dim_customers` (LTV/AOV), `mart_sku_economics_monthly` (via fact_sales).

## Impact (simulated on live parquet, before/after)

| Metric | Old | New | Δ |
|---|---|---|---|
| Σ net_revenue | 10,988 Mn | 10,332 Mn | −5.97% (VAT removed) |
| Σ total_collected | 11,644 Mn | 10,988 Mn | −5.63% (un-double-counted) |
| Σ fact_sales revenue | 75,041 Mn | 74,059 Mn | −1.31% |
| Embedded VAT separated | — | 656 Mn | — |
| Orders with net < 0 | — | **0** | safe |

Now consistent: new `total_collected` (10,988) = `total_amount`; new `net_revenue` = collected − VAT.
This also makes `gross_margin_pct` valid for the first time (net excl-VAT vs MISA COGS excl-VAT).

## ⚠ Required next step — rematerialize (NOT done; warehouse locked by Metabase)

```powershell
# 1. Stop Metabase (releases sapo_warehouse.duckdb lock)
# 2. Rebuild affected models + downstream:
python transformation\scripts\run_dbt.py --select fact_orders+ fact_sales+
# 3. Restart Metabase
```
No schema/column changes → `bootstrap_serving_views.py` NOT required.

## Unresolved questions

1. **Domestic zero-tax orders (non-US):** retail/POS orders with `tax=0` keep full gross as net_revenue.
   Confirmed strategy = trust Sapo. If some of these SHOULD have 8% embedded but Sapo didn't record it,
   they remain un-stripped. Recommend a data-quality check: domestic non-export orders with `tax=0`.
2. **Refunds** (`fact_order_returns.refund_amount`) stay VAT-inclusive (Sapo returns have no tax field).
   Low risk (returns are reference-only, not subtracted from channel_net_profit). Flagged for future.
3. **MISA COGS basis** assumed VAT-exclusive (standard). If MISA COGS is VAT-inclusive, margins shift —
   verify against one reconciled order.
