# Card 1520 Recon Semantics Audit — 2026-06-24

## Card Intent

**Card 1520 "Shopee Orders Missing Fee Data"** is a DIAGNOSTIC / EXCEPTION TABLE card in the `Exception Table` tab of the Accounting Reconciliation Cockpit (Dashboard 78). Its purpose is to surface individual Shopee orders that have `has_platform_fees = FALSE` (no Shopee settlement fee data matched), so the accounting team can investigate. It is NOT a margin KPI — it is a row-level drill-through list.

The card selects: `order_code`, `date`, `gross_revenue`, `net_revenue`, `gross_profit`, and a hardcoded `'MISSING_SHOPEE_FEES'` label. LIMIT 200.

## Before (commit bfcaace)

```sql
WHERE dim_channels.channel_name ILIKE '%shopee%'
  AND fact_order_economics.status = 'COMPLETED'
  AND NOT fact_order_economics.has_platform_fees
  -- ADDED in bfcaace:
  AND fact_order_economics.has_cogs
```

The batch commit added `AND fact_order_economics.has_cogs` to this card as part of a sweep over 8 cards / 7 blueprints that used `gross_profit`. The logic: `gross_profit` goes NULL when `has_cogs=FALSE`, which causes issues on margin KPI cards.

## After (pre-fix state, same as bfcaace)

The card was deployed with the gate. Live SQL confirmed via `GET /api/card/1520` (Metabase v0.60, `dataset_query.stages[0].native`).

## Verdict: GATE IS WRONG

The `has_cogs` gate is semantically incorrect for this card. Reasons:

1. **This is a diagnostic, not a KPI.** The card's job is to find every Shopee order missing fee data. A NULL in the `gross_profit` column is acceptable — it is informative (the order also has no MISA match). Hiding it defeats the purpose.
2. **Suppressed problem rows.** Count query result:
   - Total Shopee COMPLETED orders with `has_platform_fees=FALSE`: **3 866**
   - Of those, orders also with `has_cogs=FALSE` (hidden by gate): **1**
   - That 1 row: `SON06338`, gross_revenue=0, net_revenue=0, gross_profit=NULL — a zero-value doubly-unreconciled order.
3. **The gross_profit NULL does not error.** DuckDB returns NULL cleanly in a SELECT; Metabase displays it as a blank cell. There is no Binder Error or crash — the original reason for the gate (NULL-breaking aggregations in margin KPI cards) does not apply to a row-level table.
4. **`gross_profit` is informational, not load-bearing.** The core diagnostic predicate is `NOT has_platform_fees`. The `gross_profit` column is decorative context for the investigator.

## Fix Applied

Changed in `docs/analytics-handbook/blueprints/metabase/finance_accounting_recon.md`:

1. Removed `AND fact_order_economics.has_cogs` from WHERE clause.
2. Upgraded `'MISSING_SHOPEE_FEES'` literal to a CASE expression:
   - `NOT has_cogs` → `'MISSING_SHOPEE_FEES + NO_COGS'`
   - else → `'MISSING_SHOPEE_FEES'`
   This makes the doubly-faulted row self-documenting in the exception label.
3. Added inline comment on `gross_profit` column explaining NULL is expected and intentional.

## Deploy + Verify

Deployed via:
```
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_accounting_recon.md
```

Result: ✅ `Updated Question 'Shopee Orders Missing Fee Data' (ID: 1520)`

Post-fix verification:
- `POST /api/card/1520/query` → 200 rows (LIMIT cap), no error.
- Raw count query (no LIMIT): 3 866 rows total with gate removed; 1 previously-hidden no-cogs row is now included in the eligible set (sorts last due to 0 net_revenue; visible when date filter narrows the window).
- Live SQL via `GET /api/card/1520` confirmed: `has_cogs` gate absent, CASE label present.

## Needs Committing

Yes — `docs/analytics-handbook/blueprints/metabase/finance_accounting_recon.md` has been modified. Orchestrator should commit.

## Unresolved Questions

- The 1 hidden row (`SON06338`, zero-value) may warrant investigation in its own right — a Shopee order with both zero revenue and no fees likely indicates a cancelled/refunded order that wasn't filtered by `status='COMPLETED'` correctly, or a data anomaly. Not in scope here but flagged.
- If future COGS coverage improves and more no-cogs Shopee orders appear with real revenue, the new label `MISSING_SHOPEE_FEES + NO_COGS` will correctly triage them as the worst-case exception class.
