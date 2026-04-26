# Plan: fact_order_economics (Unified Order P&L)

**Status:** ✅ COMPLETE (2026-04-19)
**Created:** 2026-04-11 (implementation), 2026-04-19 (plan extracted)
**Branch:** main
**Model:** `transformation/models/marts/sales/fact_order_economics.sql`
**Depends on:** Shopee P0 (`plans/260409-1710-shopee-pipeline/`), MISA P0 (`plans/260409-1742-misa-amis-pipeline/`)

## Objective

Unified per-order profitability fact table combining:
- **Sapo `fact_orders`** — base order grain (revenue, discounts, tax)
- **Shopee `int_shopee_order_fees`** — platform fees, shipping, vouchers (ECOM channel only)
- **MISA `int_misa_sales_lines`** — COGS per line, aggregated to order level

## Architecture

```
fact_order_economics (rolling, serving → Metabase):
  = fact_orders                          ← base grain: 1 row/order
    LEFT JOIN int_shopee_order_fees      ← Shopee fees ON order_code
    LEFT JOIN int_misa_sales_lines       ← MISA COGS ON voucher_no (SUM by order)
  
  → Computes:
    - gross_profit = net_revenue - cogs_amount
    - gross_margin_pct
    - channel_net_profit = gross_profit - shopee_fees (for ECOM)
    - channel_net_margin_pct
```

**Why separate fact (not enrich `fact_orders`):**
- `fact_orders` in production with existing dashboards — adding 40+ columns = break risk
- Not all orders have Shopee/MISA data → many NULLs
- Different update cadence: Sapo real-time, Shopee/MISA weekly/ad-hoc

**Shopee Fee Structure (important):**
- `total_platform_fees` = service_fee + payment_fee + fixed_fee + affiliate + piship + auto_topup (from "Doanh thu" sheet)
- `infrastructure_fee` + `voucher_xtra_fee` = **separate** fees from "Service Fee Details" sheet
- These are **additive**, not overlapping — all must be summed for total deductions

## Phases

| # | Phase | Status | Evidence |
|---|-------|--------|----------|
| 1 | Prerequisites: Shopee P0 | ✅ done | `plans/260409-1710-shopee-pipeline/` phases 0-7 |
| 2 | Prerequisites: MISA P0 | ✅ done | `plans/260409-1742-misa-amis-pipeline/` phases 0-6 |
| 3 | Model implementation | ✅ done | `fact_order_economics.sql` (commit `e8ee5da` 2026-04-11) |
| 4 | Schema tests | ✅ done | `marts/schema.yml` — unique/not_null on order_id, relationships on channel_key/date_key |
| 5 | Serving layer | ✅ done | Rolling parquet via `get_rolling_location()`, auto-discovered by bootstrap |
| 6 | voucher_no join validation | ✅ done | 92.7% MISA→Sapo coverage (2026-04-19) |
| 7 | E2E verification report | ✅ done | `plans/reports/verify-260419-fact-order-economics.md` |

## Key Columns

| Column | Source | Description |
|--------|--------|-------------|
| `order_id`, `order_code` | fact_orders | Primary keys |
| `gross_revenue`, `net_revenue` | fact_orders | Sapo revenue |
| `cogs_amount` | int_misa_sales_lines | SUM of COGS per order |
| `has_cogs` | derived | TRUE if MISA data exists |
| `gross_profit` | derived | net_revenue - cogs_amount |
| `gross_margin_pct` | derived | gross_profit / net_revenue |
| `shopee_platform_fees` | int_shopee_order_fees | Total Shopee deductions |
| `shopee_net_settlement` | int_shopee_order_fees | What Shopee pays seller |
| `has_shopee_fees` | derived | TRUE if Shopee data exists |
| `channel_net_profit` | derived | gross_profit - all channel fees |
| `channel_net_margin_pct` | derived | channel_net_profit / net_revenue |

## Remaining work

### Phase 6: voucher_no join validation — ✅ DONE (2026-04-19)

**Coverage Results:**

| Metric | Value |
|--------|-------|
| MISA Total Vouchers | 344 |
| Matched to Sapo | 319 (92.7%) ✅ |
| Matched to Shopee | 84 (24.4%) |
| Unmatched | 25 (7.3%) |

**Unmatched Vouchers Breakdown:**

| Source Hint | Count | Pattern | Explanation |
|-------------|-------|---------|-------------|
| OTHER | 9 | DVUS*, PT* | Internal/miscellaneous vouchers |
| SAPO_DEALER | 8 | SON* | Dealer sales (separate B2B system) |
| AEON | 6 | 58* | AEON mall orders (retail, not in Sapo POS) |
| SHOPEE | 2 | 2512* | Timing lag — orders not yet synced to Sapo |

**Conclusion:** 92.7% coverage is excellent. The 7.3% unmatched are legitimate non-Sapo channels (dealer, AEON, internal) — NOT data format issues. No action needed.

### COGS Timing Analysis — ✅ DONE (2026-04-19)

**Finding:** MISA `posting_date` typically lags `order_date` by 1-7 days.

| Lag Bucket | Lines | % |
|------------|-------|---|
| Same day | 40 | 9.3% |
| 1-3 days | 220 | 51.3% |
| 4-7 days | 106 | 24.7% |
| >7 days | 63 | 14.7% |

- **Average lag:** 3.7 days
- **Range:** 0 to 42 days

**Impact:** For monthly P&L reports, orders from the last ~7 days of the month may not have COGS data yet. This is expected accounting behavior (invoice posting follows fulfillment).

**Mitigation:** When running period reports, either:
1. Use prior month's data (fully settled), or
2. Add a footnote: "COGS coverage incomplete for orders < 7 days old"

### Phase 7: E2E verification report — ✅ DONE (2026-04-19)

See `plans/reports/verify-260419-fact-order-economics.md` for full report.

## Resolved Questions

### Q1: Unmatched MISA vouchers — dealer/retail or format mismatch?

**Answer: Legitimate non-Sapo channels.** The 25 unmatched vouchers (7.3%) break down as:
- **SAPO_DEALER** (8): B2B dealer sales via separate system
- **AEON** (6): AEON mall retail — physical store, not in Sapo POS
- **OTHER** (9): Internal vouchers (DVUS*, PT*) — accounting adjustments
- **SHOPEE** (2): Timing lag — orders will sync within 24-48h

**No action needed.** These are intentionally outside Sapo's scope.

### Q2: COGS timing lag — does it affect period report accuracy?

**Answer: Yes, but predictably.** MISA posting lags order date by 3.7 days on average (90.7% post AFTER order). For month-end reports:
- Orders from last 7 days may lack COGS
- This is normal accounting behavior (invoice follows fulfillment)

**Mitigation:**
1. Run P&L reports 7+ days after month close, OR
2. Add footnote: "COGS data incomplete for recent orders"
