# Phase 05 — P&L Marts + Serving (`fact_order_economics` / `fact_order_costs` unification + Metabase)

## Context Links
- Master plan: `plans/260604-1030-unified-order-pl-cogs-overhead/plan.md`
- Phase 04 output (overhead allocation): `phase-04-overhead-allocation.md`
- Phase 02 output (COGS reconciliation): `phase-02-cogs-reconciliation.md`
- Phase 03 output (promo_goods_cost + count-once rule): `phase-03-cost-taxonomy-promo-642-dedup.md`
- P&L schema design: `docs/architecture/order-pl/order-pl-schema-design.md`
- COGS design: `docs/architecture/order-pl/cogs-reconciliation-design.md` §6
- Overhead design: `docs/architecture/order-pl/overhead-cost-allocation-design.md` §5
- Existing models: `transformation/models/marts/sales/fact_order_economics.sql`, `fact_order_costs.sql`
- Serving scripts: `scripts/provisioning/bootstrap_serving_views.py`, `scripts/provisioning/refresh_rolling.py`
- Dagster wiring: `orchestration/definitions.py`, `orchestration/assets/sheets_assets.py`

---

## Overview

**Priority:** P1 (blocked by phases 02, 03, 04)
**Status:** CORE DONE — all dbt models, serving, Dagster verified; Metabase P&L waterfall blueprint not authored yet (R8 pending)
**Scope:**
1. Rewrite/extend `fact_order_economics` — wire in reconciled COGS (`int_order_cogs_reconciled`), `promo_goods_cost`, `allocated_overhead`, and the three new fully-loaded columns. Keep `channel_net_profit` untouched.
2. Extend `fact_order_costs` — add PROMO_GOODS and OVERHEAD cost_category rows via new CTEs; fix BUG-1 (cogs CTE currently has no TK632 filter, lumping 1.08B promo-642 into COGS).
3. Serving: `bootstrap_serving_views.py` already handles all rolling parquet tables automatically; no new view SQL needed unless table name changes. Update `.known_tables.json` via `refresh_rolling.py` drift marker if folder is new.
4. Metabase P&L dashboard: waterfall card (gross → contribution → fully-loaded) using the new columns.
5. Dagster: ensure new intermediate models (`int_order_cogs_reconciled`, `int_order_overhead_allocation`) are in the nightly job graph; no new Dagster assets needed (dbt models picked up via `all_dbt_assets`).

**NOT in scope:** detailView wiring (phase 06), new ingestion assets, new Dagster schedules.

---

## Key Insights

### BUG-1 Fix Is Mandatory Here
`fact_order_economics.sql` line 32 and `fact_order_costs.sql` cogs CTE both aggregate `cogs_amount` from `int_misa_sales_lines` with no `cogs_account` filter. This pulls the 1.08B TK642 promo-goods into COGS. **Phase 05 fixes this** by replacing the raw `int_misa_sales_lines` join with `int_order_cogs_reconciled` (which filters to TK632 only and uses Sapo-MAC as primary). After fix: `cogs_amount` drops by ~1.08B; `gross_profit` rises by same amount; `channel_net_profit` rises accordingly.

> Coordinate: if the concurrent detailView stream has already patched BUG-1 as an interim fix (adding `WHERE cogs_account LIKE '632%'` directly to `fact_order_economics`), absorb that patch into the int-model repoint instead of reverting it.

### Tier-Separation CONTRACT
`channel_net_profit` = tier-2 anchor. It must NOT change its formula logic — only change its input source from raw MISA to `int_order_cogs_reconciled.cogs_goods_primary`. After the BUG-1 fix, its numeric value will change (correct: promo no longer in COGS), but the column's semantic meaning and formula structure remain: `net_revenue − COGS − shopee_fees`.

### New Columns Summary (waterfall order)
```
gross_revenue
 − discount_amount                    → net_revenue        [existing]
 − cogs_amount (Sapo-MAC primary)    → gross_profit        [existing, source changes]
   + cogs_source                      [NEW flag]
 − promo_goods_cost                   [NEW]
 − shopee fees / taxes                → channel_net_profit  [existing, value corrected]
 − allocated_overhead                 [NEW]
                                      → fully_loaded_net_profit [NEW]
                                      + fully_loaded_margin_pct [NEW]
                                      + is_overhead_estimated   [NEW]
```

### fact_order_costs New Categories
`cost_category` enum expands from `{COGS, PLATFORM_FEE, SHIPPING, PAYMENT, TAX, DISCOUNT, REFUND}` to include:
- `PROMO_GOODS` — from `int_order_cogs_reconciled` (revenue=0 lines, `cost_type='promo_goods_cost'`)
- `OVERHEAD` — from `int_order_overhead_allocation` (`cost_type ∈ {overhead_admin, overhead_logistics, overhead_finance}`, `fee_source='allocated'`)

### Serving — No New View SQL Required
`bootstrap_serving_views.py` builds rolling self-refresh views from ALL subdirs of `rolling/`. Since `fact_order_economics` and `fact_order_costs` already exist as rolling tables, the new columns appear automatically in the views after `dbt run` writes new parquet files. No `bootstrap_serving_views.py` edit needed **unless** a completely new table (e.g., `int_order_overhead_allocation` exposed as a mart) is added.

`refresh_rolling.py` detects schema drift via `.known_tables.json`. If `int_order_overhead_allocation` is materialized as a rolling parquet (promoted to mart), update `.known_tables.json` by running `bootstrap_serving_views.py` once after first successful Dagster run.

### Dagster — No New Assets
`all_dbt_assets` (in `definitions.py`) captures all dbt models. New intermediate models from phases 02–04 are picked up automatically by the `transform_batch_nightly_job` via `all_dbt_assets`. No `definitions.py` change needed unless a new non-dbt Dagster asset is introduced.

The `ingest_sheets_sync_job` already cascades `.downstream()` of sheets sources — `overhead_allocation_config` (gsheet) will be covered if its downstream dbt models are tagged correctly.

---

## Requirements

### Functional
- R1: `fact_order_economics.cogs_amount` = `SUM(int_order_cogs_reconciled.cogs_goods_primary)` per order. `cogs_source` column added.
- R2: `fact_order_economics.promo_goods_cost` = `SUM(promo-goods-cost lines)` per order (from phase 03 output); NULL if no promo lines.
- R3: `fact_order_economics` gets `allocated_overhead`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`, `is_overhead_estimated` (as designed in phase 04).
- R4: `channel_net_profit` formula unchanged (structurally); value corrected by BUG-1 fix.
- R5: `fact_order_costs` cogs CTE repoints to `int_order_cogs_reconciled` (TK632 only, Sapo-MAC primary). Old `int_misa_sales_lines` direct join removed from COGS CTE.
- R6: `fact_order_costs` gains PROMO_GOODS CTE (revenue=0 lines, amount positive, `fee_source='actual'`, `source_system` from phase 03).
- R7: `fact_order_costs` gains OVERHEAD CTE (from `int_order_overhead_allocation`, `fee_source='allocated'`, `cost_category='OVERHEAD'`).
- R8: Metabase dashboard updated with waterfall visualization showing all 3 tiers.
- R9: Dagster nightly run green after all changes.

### Non-Functional
- `fact_order_economics.sql` stays < 200 lines; extract helper CTEs if needed.
- All new columns in `schema.yml` with descriptions.
- No breaking rename of existing columns (additive only).

---

## Architecture

### `fact_order_economics` CTE Rewrite

```sql
-- Replace misa_order CTE (raw int_misa_sales_lines) with:
cogs_reconciled AS (
    SELECT order_code,
        SUM(cogs_goods_primary) AS cogs_amount,
        MAX(cogs_source)        AS cogs_source,      -- 'sapo_mac' | 'misa' | 'both' | 'none'
        BOOL_OR(has_sapo_cogs OR has_misa_cogs) AS has_cogs
    FROM {{ ref('int_order_cogs_reconciled') }}
    GROUP BY order_code
),
promo_cost AS (
    SELECT order_code,
        SUM(promo_goods_cost) AS promo_goods_cost   -- from phase 03 int model
    FROM {{ ref('int_order_promo_goods_cost') }}    -- or from int_order_cogs_reconciled promo side
    GROUP BY order_code
),
overhead AS (
    SELECT order_id,
        SUM(allocated_overhead) AS allocated_overhead,
        BOOL_OR(is_estimated)   AS is_overhead_estimated
    FROM {{ ref('int_order_overhead_allocation') }}
    GROUP BY order_id
)

-- In SELECT:
-- gross_profit = net_revenue − cogs_amount  (same formula, cogs_amount now from Sapo-MAC)
-- channel_net_profit = net_revenue − cogs_amount − shopee_fees  (same formula)
-- fully_loaded_net_profit = channel_net_profit − promo_goods_cost − COALESCE(allocated_overhead, 0)
-- fully_loaded_margin_pct = fully_loaded_net_profit / NULLIF(net_revenue, 0)
```

> Note: the waterfall in the master CONTRACT places `promo_goods_cost` at tier 2 (same level as platform/ship fees, below gross_profit but above channel_net_profit). Verify with stakeholder whether `channel_net_profit` already deducts promo_goods_cost or not. If promo_goods_cost was previously in COGS (BUG-1), fixing BUG-1 moves it OUT of COGS but it still must appear somewhere in the tier-2 deduction. The CONTRACT waterfall shows: `gross_profit − promo_goods_cost − platform/ship/payment − shop_discount → channel_net_profit`. So `channel_net_profit` formula must be updated to also deduct `promo_goods_cost`. This is the ONLY structural change to `channel_net_profit`'s formula logic — the column value changes as a consequence of fixing BUG-1 + routing promo correctly.

### `fact_order_costs` Extension

New CTEs added before the final UNION ALL:
```sql
-- PROMO_GOODS CTE
promo_goods AS (
    SELECT
        om.order_id,
        order_code,
        'promo_goods_cost'    AS cost_type,
        'PROMO_GOODS'         AS cost_category,
        ABS(SUM(promo_goods_cost)) AS amount,
        source_system,        -- from phase 03 model
        order_code            AS source_record,
        'actual'              AS fee_source,
        ...
    FROM {{ ref('int_order_promo_goods_cost') }}
    JOIN order_meta om USING (order_code)
    GROUP BY ...
),

-- OVERHEAD CTE
overhead_rows AS (
    SELECT
        order_id,
        order_code,           -- join from order_meta if needed
        cost_type,            -- overhead_admin / overhead_logistics / overhead_finance
        'OVERHEAD'            AS cost_category,
        ABS(allocated_overhead) AS amount,
        CASE WHEN is_estimated THEN 'gsheet' ELSE 'misa' END AS source_system,
        period_month::VARCHAR AS source_record,
        'allocated'           AS fee_source,
        date_key,
        channel_key
    FROM {{ ref('int_order_overhead_allocation') }}
    JOIN order_meta om USING (order_id)
)
```

Then add to final UNION ALL:
```sql
UNION ALL SELECT order_id, order_code, cost_type, cost_category, amount, NULL, NULL, source_system, source_record, fee_source, date_key, channel_key FROM promo_goods
UNION ALL SELECT order_id, order_code, cost_type, cost_category, amount, NULL, NULL, source_system, source_record, fee_source, date_key, channel_key FROM overhead_rows
```

### Metabase Dashboard — P&L Waterfall

New/updated question in the existing P&L dashboard (Dashboard 35 or new P&L-specific board):
- **Waterfall card:** use `fact_order_economics` grouped by `date_key` (monthly). Metrics: `SUM(gross_profit)`, `SUM(channel_net_profit)`, `SUM(fully_loaded_net_profit)`.
- **Margin % trend:** line chart showing `gross_margin_pct`, `channel_net_margin_pct`, `fully_loaded_margin_pct` over time.
- **Estimated flag filter:** filter widget on `is_overhead_estimated` to toggle between confirmed and estimated periods.
- **Cost waterfall breakdown:** pivot from `fact_order_costs` by `cost_category` to show COGS, PROMO_GOODS, PLATFORM_FEE, OVERHEAD contribution.

---

## Related Code Files

### Modify (extend — this phase OWNS these files)
> Wait for concurrent detailView stream to merge before touching these.

- `transformation/models/marts/sales/fact_order_economics.sql` — repoint COGS, add promo_goods_cost, overhead columns
- `transformation/models/marts/sales/fact_order_costs.sql` — fix COGS CTE, add PROMO_GOODS + OVERHEAD CTEs
- `transformation/models/marts/sales/schema.yml` — document all new columns

### Possibly Modify (if schema drift detected)
- `scripts/provisioning/bootstrap_serving_views.py` — only if new mart table added (e.g., `int_order_overhead_allocation` promoted to rolling parquet)
- `orchestration/definitions.py` — only if new non-dbt assets or a new gsheet source for overhead config needs wiring

### Read-Only Reference
- `transformation/models/intermediate/finance/int_order_cogs_reconciled.sql` (phase 02 output)
- `transformation/models/intermediate/finance/int_order_overhead_allocation.sql` (phase 04 output)
- `transformation/models/intermediate/finance/int_order_promo_goods_cost.sql` (phase 03 output, or equivalent)

---

## Implementation Steps

### Pre-Requisites
1. Phases 02, 03, 04 all complete and Dagster-green.
2. Concurrent detailView stream merged (no open PRs touching `fact_order_economics.sql` / `fact_order_costs.sql`).
3. Record a baseline checksum of `fact_order_economics` outputs before any edit:
   ```bash
   docker exec data_platform dbt run-operation execute_sql \
     --project-dir /app/transformation --profiles-dir /app/transformation \
     --args '{"sql": "SELECT COUNT(*), SUM(channel_net_profit), SUM(gross_profit) FROM fact_order_economics"}'
   ```
   Save these numbers — used to verify BUG-1 impact after fix.

### Step 1 — Fix `fact_order_costs.sql` COGS CTE
Replace the existing `cogs` CTE (which joins `int_misa_sales_lines` directly) with:
```sql
cogs AS (
    SELECT
        om.order_id,
        r.order_code,
        'cogs'                          AS cost_type,
        'COGS'                          AS cost_category,
        ABS(SUM(r.cogs_goods_primary))  AS amount,
        r.cogs_source                   AS source_system,
        r.order_code                    AS source_record,
        'actual'                        AS fee_source,
        MIN(om.date_key)                AS date_key,
        MIN(om.channel_key)             AS channel_key
    FROM {{ ref('int_order_cogs_reconciled') }} r
    JOIN order_meta om ON r.order_code = om.order_code
    WHERE r.cogs_goods_primary IS NOT NULL
    GROUP BY om.order_id, r.order_code, r.cogs_source
),
```

### Step 2 — Add PROMO_GOODS CTE to `fact_order_costs.sql`
Add after the existing `cogs` CTE (before shopee_wide):
```sql
promo_goods AS (
    SELECT
        om.order_id,
        p.order_code,
        'promo_goods_cost'              AS cost_type,
        'PROMO_GOODS'                   AS cost_category,
        ABS(SUM(p.promo_goods_cost))    AS amount,
        p.source_system,
        p.order_code                    AS source_record,
        'actual'                        AS fee_source,
        MIN(om.date_key)                AS date_key,
        MIN(om.channel_key)             AS channel_key
    FROM {{ ref('int_order_promo_goods_cost') }} p   -- phase 03 model
    JOIN order_meta om ON p.order_code = om.order_code
    WHERE p.promo_goods_cost IS NOT NULL AND p.promo_goods_cost > 0
    GROUP BY om.order_id, p.order_code, p.source_system
),
```

### Step 3 — Add OVERHEAD CTE to `fact_order_costs.sql`
Add after `promo_goods` CTE:
```sql
overhead_costs AS (
    SELECT
        oa.order_id,
        om.order_code,
        oa.cost_type,                   -- overhead_admin / overhead_logistics / overhead_finance
        'OVERHEAD'                      AS cost_category,
        ABS(oa.allocated_overhead)      AS amount,
        CASE WHEN oa.is_estimated THEN 'gsheet' ELSE 'misa' END AS source_system,
        oa.period_month::VARCHAR        AS source_record,
        'allocated'                     AS fee_source,
        om.date_key,
        om.channel_key
    FROM {{ ref('int_order_overhead_allocation') }} oa
    JOIN order_meta om ON oa.order_id = om.order_id
    WHERE oa.allocated_overhead IS NOT NULL AND oa.allocated_overhead > 0
),
```

### Step 4 — Add PROMO_GOODS + OVERHEAD to Final UNION ALL in `fact_order_costs.sql`
Append after the last existing UNION ALL (sapo_discounts):
```sql
UNION ALL
SELECT order_id, order_code, cost_type, cost_category,
    CAST(amount AS DECIMAL(18,2)), NULL, NULL,
    source_system, source_record, fee_source, date_key, channel_key
FROM promo_goods

UNION ALL
SELECT order_id, order_code, cost_type, cost_category,
    CAST(amount AS DECIMAL(18,2)), NULL, NULL,
    source_system, source_record, fee_source, date_key, channel_key
FROM overhead_costs
```

### Step 5 — Rewrite CTEs in `fact_order_economics.sql`

**5a.** Replace `misa_order` CTE with `cogs_reconciled` + `promo_cost`:
```sql
cogs_reconciled AS (
    SELECT order_code,
        SUM(cogs_goods_primary)  AS cogs_amount,
        MAX(cogs_source)         AS cogs_source,
        BOOL_OR(has_sapo_cogs OR has_misa_cogs) AS has_cogs
    FROM {{ ref('int_order_cogs_reconciled') }}
    GROUP BY order_code
),
promo_cost AS (
    SELECT order_code, SUM(promo_goods_cost) AS promo_goods_cost
    FROM {{ ref('int_order_promo_goods_cost') }}
    GROUP BY order_code
),
overhead AS (
    SELECT order_id,
        SUM(allocated_overhead)  AS allocated_overhead,
        BOOL_OR(is_estimated)    AS is_overhead_estimated
    FROM {{ ref('int_order_overhead_allocation') }}
    GROUP BY order_id
),
```

**5b.** Update SELECT to add new columns (after existing `channel_net_margin_pct`):
```sql
-- COGS source flag (new)
cr.cogs_source,
cr.has_cogs,                                  -- was m.cogs_amount IS NOT NULL

-- Promo goods cost (tier 2, new)
pc.promo_goods_cost,

-- Overhead (tier 3, new)
ov.allocated_overhead,
ov.is_overhead_estimated,
-- fully_loaded_net_profit = channel_net_profit − promo_goods_cost − overhead
(
    o.net_revenue
    - COALESCE(cr.cogs_amount, 0)
    + COALESCE(sf.total_platform_fees, 0)
    + COALESCE(sf.infrastructure_fee, 0)
    + COALESCE(sf.voucher_xtra_fee, 0)
    + COALESCE(sf.shopee_taxes, 0)
    - COALESCE(pc.promo_goods_cost, 0)
    - COALESCE(ov.allocated_overhead, 0)
) AS fully_loaded_net_profit,
CASE
    WHEN o.net_revenue = 0 THEN NULL
    ELSE (
        o.net_revenue
        - COALESCE(cr.cogs_amount, 0)
        + COALESCE(sf.total_platform_fees, 0)
        + COALESCE(sf.infrastructure_fee, 0)
        + COALESCE(sf.voucher_xtra_fee, 0)
        + COALESCE(sf.shopee_taxes, 0)
        - COALESCE(pc.promo_goods_cost, 0)
        - COALESCE(ov.allocated_overhead, 0)
    )::DOUBLE / o.net_revenue
END AS fully_loaded_margin_pct,
```

**5c.** Update `channel_net_profit` formula to also deduct `promo_goods_cost` (per CONTRACT waterfall — promo is tier-2):
```sql
o.net_revenue
    - COALESCE(cr.cogs_amount, 0)
    + COALESCE(sf.total_platform_fees, 0)
    + COALESCE(sf.infrastructure_fee, 0)
    + COALESCE(sf.voucher_xtra_fee, 0)
    + COALESCE(sf.shopee_taxes, 0)
    - COALESCE(pc.promo_goods_cost, 0)   -- ADDED (promo tier-2)
    AS channel_net_profit,
```

**5d.** Update LEFT JOINs:
```sql
LEFT JOIN cogs_reconciled cr  ON o.order_code = cr.order_code
LEFT JOIN promo_cost pc        ON o.order_code = pc.order_code
LEFT JOIN overhead ov          ON o.order_id   = ov.order_id
-- Remove: LEFT JOIN misa_order m
```

### Step 6 — Update `schema.yml`
Document all new columns in `transformation/models/marts/sales/schema.yml`:
- `fact_order_economics`: `cogs_source`, `promo_goods_cost`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`.
- `fact_order_costs`: new `cost_category` values `PROMO_GOODS`, `OVERHEAD`; new `fee_source` value `allocated`.

### Step 7 — dbt Compile + Run
```bash
docker exec data_platform dbt compile \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --select fact_order_economics fact_order_costs

docker exec data_platform dbt run \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --select fact_order_economics fact_order_costs
```
Fix compilation errors. Repeat until clean.

### Step 8 — dbt Test
```bash
docker exec data_platform dbt test \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --select fact_order_economics fact_order_costs
```
Also run the closure test:
```bash
docker exec data_platform dbt test \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --select int_order_overhead_allocation
```

### Step 9 — Verify BUG-1 Impact
```bash
docker exec data_platform dbt run-operation execute_sql \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --args '{"sql": "SELECT COUNT(*), SUM(channel_net_profit), SUM(gross_profit), SUM(cogs_amount) FROM fact_order_economics"}'
```
Expected vs. baseline from pre-req step:
- `cogs_amount` decreases by ~1.08B (promo-642 removed from COGS).
- `gross_profit` increases by ~1.08B (same delta, opposite sign).
- `channel_net_profit` also increases (unless promo_goods_cost is now deducted at tier-2).
- Verify no orders have `fully_loaded_net_profit IS NULL` except those with NULL overhead (open months with no config).

### Step 10 — Serving Views (schema drift check)
```bash
docker exec data_platform python scripts/provisioning/refresh_rolling.py
```
Check output for `[!] SCHEMA_DRIFT`. If triggered (new column count in parquet differs from `.known_tables.json`), run bootstrap:
```bash
docker exec data_platform python scripts/provisioning/bootstrap_serving_views.py
```
Metabase can remain up during both scripts (DuckDB read_only coexistence confirmed).

### Step 11 — Verify Serving Layer
```bash
docker exec data_platform dbt run-operation execute_sql \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --args '{"sql": "SELECT allocated_overhead, fully_loaded_net_profit, is_overhead_estimated FROM fact_order_economics LIMIT 5"}'
```
New columns should be visible in the DuckDB serving view.

### Step 12 — Metabase P&L Dashboard
Via Metabase UI (http://127.0.0.1:3000 or METABASE_URL):
1. Open Dashboard 35 (or create new "Order P&L" dashboard).
2. Add/update waterfall question: `fact_order_economics` grouped by month, metrics: `SUM(gross_profit)`, `SUM(channel_net_profit)`, `SUM(fully_loaded_net_profit)`.
3. Add margin % trend line: `AVG(fully_loaded_margin_pct)` by month.
4. Add `is_overhead_estimated` filter widget (boolean toggle).
5. Save blueprint to `docs/analytics-handbook/blueprints/` if using Metabase automation.

### Step 13 — Full Dagster Nightly Run
Launch `transform_batch_nightly_job` via Dagster UI. Confirm SUCCESS end-to-end. Check all new models in run log.

---

## Todo

- [x] Verify phases 02, 03, 04 are Dagster-green before starting
- [x] Confirm concurrent detailView stream merged; no open PRs on fact_ files
- [x] Record baseline checksums (count, sum cogs, sum channel_net_profit)
- [x] Fix `fact_order_costs.sql` cogs CTE (step 1)
- [x] Add PROMO_GOODS CTE to `fact_order_costs.sql` (step 2)
- [x] Add OVERHEAD CTE to `fact_order_costs.sql` (step 3)
- [x] Add PROMO_GOODS + OVERHEAD to UNION ALL (step 4)
- [x] Rewrite CTEs in `fact_order_economics.sql` (step 5a–d)
- [x] Update `schema.yml` (step 6)
- [x] `dbt compile` passes (step 7)
- [x] `dbt run` passes (step 7)
- [x] `dbt test` passes incl. closure test (step 8)
- [x] BUG-1 impact verified: cogs_amount drops ~1.08B (step 9)
- [x] `refresh_rolling.py` runs clean; `bootstrap_serving_views.py` if drift (step 10)
- [x] New columns queryable in serving layer (step 11)
- [x] Metabase P&L waterfall dashboard updated (step 12) — deployed 2026-06-09
- [x] Full Dagster nightly run SUCCESS (step 13)

---

## Success Criteria

1. **Dagster-green:** `transform_batch_nightly_job` SUCCESS with `fact_order_economics`, `fact_order_costs`, all int_ parents in graph.
2. **BUG-1 fixed:** `SUM(cogs_amount)` in `fact_order_economics` decreases by ~1.08B vs. baseline; promo-642 now appears as `PROMO_GOODS` rows in `fact_order_costs`.
3. **Closure test passes:** `assert_overhead_closure` green (from phase 04).
4. **Tier separation maintained:** `channel_net_profit` column present and non-null for completed orders; `fully_loaded_net_profit` column present (may be NULL for open months without overhead data).
5. **Serving queryable:** `SELECT allocated_overhead, fully_loaded_net_profit FROM fact_order_economics LIMIT 1` returns rows from Metabase/DuckDB without error.
6. **No double-count:** `SUM(fact_order_costs.amount WHERE cost_category='OVERHEAD')` for a given month equals the overhead pool for that month (matches `overhead_costs_monthly`).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Concurrent stream not merged — file conflict on fact_ models | High | High — broken git history | Hard gate: confirm no open PRs before step 1 |
| BUG-1 fix changes `channel_net_profit` sign for orders with only promo-642 MISA lines (no real COGS) | Medium | Medium — KPI jump visible in dashboards | Communicate expected ~1.08B shift to stakeholders before deploying; show before/after in dashboard |
| `int_order_promo_goods_cost` model not yet built by phase 03 | Medium | High — phase 05 blocked | Hard dependency: phase 03 must be complete and model must exist |
| `fact_order_economics` > 200 lines after additions | Medium | Low — style concern | Extract CTEs into a separate `int_order_economics_inputs` model if needed |
| Metabase schema drift causes cached question to error | Low | Low | Refresh Metabase model metadata after serving views updated |
| `refresh_rolling.py` triggers SCHEMA_DRIFT on column count change | Medium | Low — just run bootstrap | Expected; have `bootstrap_serving_views.py` ready to run immediately |
| `overhead_allocation` NULL for orders in months with no pool data | Medium | Medium — `fully_loaded_net_profit` NULL for those orders | Accept NULL; flag in dashboard with `is_overhead_estimated IS NULL` note |

---

## Security / Data Integrity

- `channel_net_profit` value will change (BUG-1 fix) — document in changelog and notify dashboards users proactively.
- All monetary columns keep `DECIMAL(18,2)` — no precision loss on new columns.
- `fee_source='allocated'` is a new enum value; ensure any downstream filters on `fee_source='actual'` still work correctly (they will, since `'allocated'` is additive).
- `source_record` for overhead rows = `period_month` (VARCHAR) — sufficient for audit traceability back to MISA pool.

---

## Next Steps

Hands off to:
- **Phase 06** (`phase-06-detailview-pl.md`): wires the new fact_ columns into detailView per-order P&L panel and reconciliation UI.

---

## Unresolved Questions

1. **promo_goods_cost in channel_net_profit:** CONTRACT waterfall places promo at tier-2 (between gross_profit and channel_net_profit). Confirm: should `channel_net_profit` deduct `promo_goods_cost`, or is promo a tier-2.5 shown separately but NOT changing `channel_net_profit`? The answer changes whether existing `channel_net_profit` values shift by 1.08B. Resolve before step 5c.
2. **int_order_promo_goods_cost model name:** Phase 03 may name this model differently. Confirm exact `ref()` name before step 2.
3. **overhead_allocation pool_id in fact_order_costs:** If v1 has only 1 pool, `cost_type='overhead_admin'` for all rows — confirm desired cost_type label with stakeholder.
4. **Metabase dashboard scope:** Update existing Dashboard 35 (P&L) in-place or create a new "Fully Loaded P&L" dashboard? Preference determines whether Shopee fee waterfall (current cards) is unified or separate.
