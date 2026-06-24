# Phase 04 — Corrected margin at order/CEO level (research → decide → implement)

**Priority:** Medium (BI correctness) | **Status:** ⬜ TODO (research first — CEO-facing, do NOT blind-edit)
**Context:** [plan](plan.md) · audit finding "Evidence CEO + detailView show gross_margin_pct (H010-uncorrected)" · [[reference_realized_vs_gross_margin_pct]] · L143 (don't break BI consumers)

## Problem (as flagged)
Evidence `ceo-weekly-pulse` + detailView read `fact_order_economics.gross_margin_pct`. Memory says `realized_margin_pct` (SKU/product marts) has the H010 cost correction; `gross_margin_pct` does not → CEO may see inflated margin for ~5 H010 SKUs.

## BUT — verify before acting (the real question)
`fact_order_economics` computes margin from `o.net_revenue - m.cogs_amount`, where `m = int_order_cogs_reconciled` (Sapo-MAC repointed COGS), NOT the MISA-book cost. The H010 problem specifically afflicts **MISA-based** gross_profit. So order-level margin may ALREADY be correct (Sapo-MAC), and the audit flag (pattern-matched on the column name `gross_margin_pct`) may NOT apply at order grain.

**Research tasks (do these first):**
1. Read `transformation/models/intermediate/sapo/int_order_cogs_reconciled.sql` — does `cogs_amount` use Sapo-MAC (H010-correct) or MISA? Is the H010 fix applied here?
2. Read `mart_sku_economics_monthly.sql` — what EXACTLY is the H010 correction in `realized_margin_pct` (vs `gross_margin_pct`)? Is it a cost source swap or a specific SKU override?
3. Query serving: for the ~5 H010 SKUs, compare order-level `gross_margin_pct` (fact_order_economics) vs SKU `realized_margin_pct`. Are they consistent? (read_only=True on olap.duckdb)

## Decision tree
- **If order-level COGS already H010-correct** → audit finding is moot at order grain. Action: just a doc/comment note + maybe rename perception; NO mart change. (Cheapest, likely.)
- **If genuinely uncorrected** → add `realized_gross_profit` / `realized_margin_pct` to `fact_order_economics` sourced from corrected cost, then:
  - `dbt run --full-refresh` the fact (incremental — new column only backfills changed rows otherwise; see [[feedback_dim_customers_incremental_full_refresh]])
  - regenerate serving DB (`generate_serving_db.py`, stop Metabase) + rebuild Evidence container
  - update Evidence `ceo-weekly-pulse` + detailView queries to the corrected column
  - **L143:** audit all consumers of the old column before changing; don't break SUM/AVG.

## Success criteria
- Documented verdict on whether order-level margin was actually wrong.
- If changed: CEO page + detailView show corrected margin; no BI card silently broken; row/aggregate parity checked.

## Risk
- CEO/Finance-facing number → wrong change is high-visibility. Research + consumer audit are mandatory before any SQL edit.
