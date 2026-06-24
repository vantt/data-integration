# Metabase Audit: gross_profit NULL Impact After fact_order_economics Change

**Date:** 2026-06-24  
**Auditor:** read-only scan via Metabase API  
**Change audited:** `fact_order_economics.gross_profit` and `gross_margin_pct` now return NULL when `has_cogs = FALSE` (previously held uncorrected/understated values). Any card SUMming/AVGing these columns without a `WHERE has_cogs` gate will show NULL gaps or shifted aggregates.

---

## Summary

| Metric | Count |
|---|---|
| Total cards scanned | 852 |
| Cards referencing gross_profit / gross_margin_pct | 41 |
| Safe — has_cogs gate present | 6 |
| Safe — uses only `realized_gross_profit` (no raw gross_profit) | 4 |
| **AT RISK — raw gross_profit/margin_pct, no has_cogs gate** | **31** |

Of the 31 at-risk cards:
- **20** query `fact_order_economics` (directly affected by the NULL change)
- **11** query `int_misa_sales_lines` (`int_misa.gross_profit` is a separate column not touched by this change, but is also noted in memory as uncorrected for H010 SKUs — see unresolved questions)

---

## Safe Cards (has_cogs gated) — ✅ No action needed

| ID | Name | has_cogs gate |
|---|---|---|
| 2187 | 3-Tier Profit Trend | `AND has_cogs` |
| 1130 | Avg Gross Margin % | `AND has_cogs` |
| 1668 | Cost Waterfall % of Net Revenue | `AND econ.has_cogs = TRUE` |
| 2188 | Margin % Trend | `AND has_cogs` |
| 1136 | Margin Distribution | `AND has_cogs` |
| 1131 | Total Gross Profit | `AND has_cogs` |

## Realized-Only Cards — ✅ No action needed

These cards use `realized_gross_profit` (safe column, never NULL) and do not reference raw `gross_profit`.

| ID | Name | Column used |
|---|---|---|
| 2331 | Avg Margin % | `realized_gross_profit` |
| 2340 | Avg Margin % (Cost Tab) | `realized_gross_profit` |
| 2338 | Product Detail Table | `realized_gross_profit` |
| 2335 | Top Products by Profit | `realized_gross_profit` |

---

## AT RISK Cards — ⚠️ fact_order_economics source (directly impacted)

These 20 cards query `fact_order_economics` (aliased as `e`, `oe`, `foe`, etc.) and SUM/use `gross_profit` or `gross_margin_pct` without gating on `has_cogs`. After the change, rows where `has_cogs = FALSE` produce NULL, which silently drops them from SUM() and shifts all aggregates downward.

| ID | Name | Dashboard(s) | SQL Snippet (gross_profit usage) | Recommendation |
|---|---|---|---|---|
| 1706 | Gross Margin % | CEO Weekly Pulse [All] | `SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0)` | Add `AND has_cogs` or switch to `realized_gross_profit` |
| 1589 | Monthly Gross Margin % | CEO Monthly Scorecard [All] | `SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100` | Add `AND has_cogs` or switch to `realized_gross_profit` |
| 2111 | Gross Margin % Trend (12M) | Sales Monthly Business Review [All] | `SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0)` | Add `AND e.has_cogs` |
| 2110 | Gross Margin % vs Last Month | Sales Monthly Business Review [All] | `ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)` | Add `AND e.has_cogs` |
| 2112 | Channel Profit Contribution (Top 10) | Sales Monthly Business Review [All] | `SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0)` | Add `AND e.has_cogs` |
| 2394 | Core vs Marketplace Summary | Channel Profitability Monthly [Cross] | `SUM(foe.gross_profit)`, `ROUND(SUM(foe.gross_profit) * 100.0 / ...)` | Add `AND foe.has_cogs` |
| 2395 | Per-Channel Profitability Table | Channel Profitability Monthly [Cross] | `SUM(foe.gross_profit)`, `ROUND(SUM(foe.gross_profit) * 100.0 / ...)` | Add `AND foe.has_cogs` |
| 2388 | Core vs Marketplace — Revenue & Margin Summary | Channel P&L Deep Dive [Cross] | `ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)` | Add `AND e.has_cogs` |
| 1505 | Channel Scorecard Table | Channel P&L Deep Dive [Cross] | `ROUND(SUM(e.gross_profit) * 100.0 / ...) AS gross_margin_pct` | Add `AND e.has_cogs` |
| 1511 | Loss Leader Detail Table | Channel P&L Deep Dive [Cross] | `COALESCE(SUM(e.gross_profit), 0) AS "Gross Profit"` | Add `AND e.has_cogs` |
| 1135 | Cost Structure by Channel | Order Profitability [All] | `SUM(e.gross_profit) AS "Lai gop"` | Add `AND e.has_cogs` |
| 1138 | Order P&L Table | Order Profitability [All] | `e.gross_profit AS "Lai gop"`, `e.gross_margin_pct * 100` | Row-level; add `WHERE e.has_cogs` or display NULL as N/A |
| 1137 | Profit by Date | Order Profitability [All] | `SUM(e.gross_profit) AS "Lai gop"` | Add `AND e.has_cogs` |
| 1673 | Monthly Margin by Channel | Sales Ops Monthly Summary [Retail] | `COALESCE(SUM(e.gross_profit), 0) AS gp_tm` | Add `AND e.has_cogs`; note COALESCE masks NULL silently |
| 1671 | Weekly Margin by Channel | Sales Ops Weekly Review [Retail] | `COALESCE(SUM(e.gross_profit), 0) AS gp_tw` | Add `AND e.has_cogs`; COALESCE masks NULLs silently |
| 1592 | Weekly Channel Margin & Delta | Marketing Weekly Tracker [Retail] | `SUM(oe.gross_profit) / NULLIF(SUM(oe.net_revenue), 0) * 100` | Add `AND oe.has_cogs` |
| 1638 | Profitable ROAS by Channel | Marketing ROI [Retail] | `SUM(e.gross_profit) AS gross_profit` | Add `AND e.has_cogs` |
| 1639 | Channel ROI Quadrant (Optional) | Marketing ROI [Retail] | `SUM(e.gross_profit) AS gross_profit` | Add `AND e.has_cogs` |
| 1640 | ROAS + Margin by Channel | Marketing Monthly Analysis [Retail] | `SUM(o.gross_profit) AS gross_profit` | Add `AND o.has_cogs` (o = fact_order_economics alias) |
| 1520 | Shopee Orders Missing Fee Data | Accounting Reconciliation Cockpit [Internal] | `fact_order_economics.gross_profit AS "Gross Profit (VND)"` | Row-level diagnostic; NULL rows will appear for no-COGS orders — acceptable or add WHERE has_cogs |

### Special note — COALESCE masks the NULL silently

Cards 1673 (Monthly Margin by Channel) and 1671 (Weekly Margin by Channel) use `COALESCE(SUM(e.gross_profit), 0)`. After the change, orders without COGS contribute NULL to the SUM, which SUM() treats as 0 (drops them), and COALESCE then hides that the denominator still includes those orders. The result is a **silently understated gross margin %** — particularly dangerous because it looks valid.

---

## AT RISK Cards — ⚠️ int_misa_sales_lines source (indirect concern)

These 11 cards query `int_misa_sales_lines.gross_profit`. This column is **NOT directly changed** by the `fact_order_economics` NULL modification. However, per project memory, `int_misa.gross_profit` is independently uncorrected for H010 SKUs (~5 SKUs with ~2× understated gross_profit). These cards predate and are unaffected by the current change, but are flagged here for completeness.

| ID | Name | Dashboard(s) | SQL Snippet | Note |
|---|---|---|---|---|
| 1101 | Gross Margin % | Channel Profitability Monthly [Cross] | `SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0)` | int_misa source; NOT affected by this change |
| 2393 | Gross Margin % by Channel Group — Bar | (standalone, not on dashboard) | `ROUND(SUM(gross_profit) * 100.0 / ...) AS "Gross Margin %"` | int_misa source |
| 1114 | Gross Margin Percent | Finance P&L [All] | `SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0)` | int_misa source |
| 1113 | Gross Profit MTD | Finance P&L [All] | `COALESCE(SUM(gross_profit), 0) AS val` | int_misa source; YoY comparison card |
| 1110 | Low-Margin Products | Channel Profitability Monthly [Cross] | `SUM(gross_profit) ... HAVING margin < 25` | int_misa source |
| 1105 | Margin by Channel | Channel Profitability Monthly [Cross] | `SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0)` | int_misa source |
| 1117 | Margin by Channel | Finance P&L [All] | `SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0)` | int_misa source |
| 1107 | Margin Trend by Channel | Channel Profitability Monthly [Cross] | `SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0)` | int_misa source |
| 2391 | Revenue & Margin by Channel Group (MISA) | (standalone, not on dashboard) | `ROUND(SUM(gross_profit) * 100.0 / ...) AS "Gross Margin %"` | int_misa source |
| 1109 | Top Products by Profit | Channel Profitability Monthly [Cross] | `SUM(gross_profit) AS "Lai gop"` | int_misa source |
| 1104 | Total Gross Profit | Channel Profitability Monthly [Cross] | `COALESCE(SUM(gross_profit), 0) AS val` | int_misa source; YoY comparison |

---

## Priority by Dashboard Impact

| Priority | Dashboard | At-Risk Cards (fact_order_econ) |
|---|---|---|
| P0 | CEO Weekly Pulse [All] | 1706 |
| P0 | CEO Monthly Scorecard [All] | 1589 |
| P1 | Sales Monthly Business Review [All] | 2111, 2110, 2112 |
| P1 | Channel Profitability Monthly [Cross] | 2394, 2395, 1105, 1107, 1109, 1104, 1110, 1101 |
| P1 | Finance P&L [All] | 1114, 1113, 1117 |
| P1 | Channel P&L Deep Dive [Cross] | 2388, 1505, 1511 |
| P2 | Order Profitability [All] | 1135, 1138, 1137 |
| P2 | Sales Ops Monthly Summary [Retail] | 1673 |
| P2 | Sales Ops Weekly Review [Retail] | 1671 |
| P2 | Marketing ROI [Retail] | 1638, 1639 |
| P2 | Marketing Weekly Tracker [Retail] | 1592 |
| P2 | Marketing Monthly Analysis [Retail] | 1640 |
| P3 | Accounting Reconciliation Cockpit [Internal] | 1520 (row-level, NULLs may be acceptable) |

---

## Recommendation (to apply via /deploy-metabase-blueprint — DO NOT apply manually)

For all fact_order_economics cards (20 cards):
1. **Primary fix:** Add `AND <alias>.has_cogs` (or `AND has_cogs`) to the WHERE clause of the innermost query that touches gross_profit. This ensures only COGS-covered orders contribute to the aggregation — consistent with the 6 already-safe cards.
2. **Alternative for margin % KPIs:** Switch from `gross_profit` to `realized_gross_profit` + `realized_margin_pct` — these columns always have values (no NULL), making them safer for KPI cards like CEO dashboards. See memory note: `reference_realized_vs_gross_margin_pct.md`.
3. **Cards with COALESCE wrapping (1673, 1671):** COALESCE must be removed or the gate added BEFORE the SUM — not after. `COALESCE(SUM(col), 0)` does not protect against NULLs inside SUM.

For int_misa cards (11 cards): no action for this change. Pre-existing H010 accuracy issue is a separate ticket.

---

## Unresolved Questions

1. **What fraction of orders have `has_cogs = FALSE`?** Determines severity — if 5% of orders lack COGS, aggregates shift by ~5%; if 30%, the impact is major. Need `SELECT COUNT(*), COUNT(*) FILTER (WHERE has_cogs) FROM fact_order_economics` to size the drift.
2. **Do any of the 20 at-risk fact_order_econ cards use a CTE or view that already filters `has_cogs` upstream?** Audit checked the final WHERE clause only; a deeper CTE scan may find implicit gates in 1–2 cards (especially multi-CTE cards like 1639, 1638, 1640).
3. **Should CEO/monthly scorecard cards (1706, 1589) switch to `realized_*` instead of adding a gate?** A gate excludes no-COGS orders from the denominator too (revenue), which may or may not match business intent. `realized_gross_profit` uses a different formula and always has a value — but memory note warns `realized_margin_pct` differs from `gross_margin_pct` for H010 SKUs.
4. **Card 1520 (Shopee Orders Missing Fee Data):** This is a diagnostic/recon card listing individual orders. NULLs in gross_profit may actually be informative (orders missing COGS). Confirm whether NULLs should be shown or filtered.
5. **int_misa_sales_lines has no `has_cogs` column** — the H010 gross_profit correction cannot be applied to those 11 cards without a model-level fix to `int_misa_sales_lines`. Is that in scope?
