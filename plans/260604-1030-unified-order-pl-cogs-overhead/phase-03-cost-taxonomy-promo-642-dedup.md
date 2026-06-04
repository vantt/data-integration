---
title: "Phase 03 — Cost Taxonomy, Promo Goods Cost & 642 Count-Once"
description: "Split promo_goods_cost (revenue=0 lines, gift-no-invoice) from COGS; define cross-tier 642 dedup mechanism so overhead pool (phase 04) never double-counts the sales-ledger-642 portion"
status: TODO
priority: P1
effort: 1d
tags: [cost-taxonomy, promo, cogs, 642-dedup, count-once]
created: 2026-06-04
---

## Context Links

- Master plan: `plans/260604-1030-unified-order-pl-cogs-overhead/plan.md` — CONTRACT §4 (count-once crux)
- Design: `docs/architecture/order-pl/cogs-reconciliation-design.md` §1a (TK642 promo nature), §2b (revenue=0 split decision), §5 (promo routing)
- Design: `docs/architecture/order-pl/overhead-cost-allocation-design.md` §2.6 (double-count warning), §4 (pool definition), §5.1 (fact_order_costs OVERHEAD rows)
- Phase 02 output (blocker): `phase-02-cogs-reconciliation.md` — `int_order_cogs_reconciled` must be GREEN
- Sources:
  - `transformation/models/intermediate/cogs/int_order_cogs_reconciled.sql` (phase 02 output)
  - `transformation/models/staging/standard/std_misa_sales_lines.sql` (phase 01 output)
  - `std_order_items` (existing — provides line-level `line_amount`/revenue per order × SKU)
  - `fact_sales` (existing — alternative line-level revenue source; check which has better coverage)
- Affected: `transformation/models/marts/sales/fact_order_costs.sql` — will add PROMO_GOODS rows (CONCURRENT STREAM — coordinate)
- Affected: `transformation/models/marts/sales/fact_order_economics.sql` — will add `promo_goods_cost` column (CONCURRENT STREAM — coordinate)

---

## Overview

**Priority:** P1 — phase 04 (overhead allocation pool) cannot be correctly defined without the count-once dedup rule established here
**Status:** TODO
**Scope:**

1. **Cost taxonomy boundaries** — formalize the 4-tier cost classification and document where each account code / line type lands. No new model; this is a codified decision that governs all downstream SQL.
2. **`int_order_promo_goods_cost`** (NEW, `intermediate/cogs/`) — grain `(order_code, sku)` — identifies lines with `revenue=0` (promo/gift), values them at Sapo-MAC, flags gift-no-invoice (`cogs_source='sapo_only'`). Output is a row-set ready to become `cost_type='promo_goods_cost'` rows in `fact_order_costs`.
3. **Extend `fact_order_costs`** — add PROMO_GOODS rows from `int_order_promo_goods_cost`.
4. **Extend `fact_order_economics`** — add `promo_goods_cost` column (SUM of PROMO_GOODS rows per order).
5. **Cross-tier 642 count-once mechanism** — define exactly how the ~1.08B sales-ledger TK642 promo amount is excluded from the phase 04 overhead pool. Produces a `overhead_pool_excluded_642_sales_ledger` table/seed or a documented SQL clause that phase 04 must apply.

---

## Key Insights

- **The promo-642 sits in the MISA SALES LEDGER, not the expense ledger.** The ~1.08B TK642 lines come from `std_misa_sales_lines` where `cost_account_group='642'` — they are goods issued as giveaways, booked by MISA to TK642 (not TK632). They are NOT cash G&A overhead (rent, salary, software).
- **Promo lines ride trans_type=301 in Sapo.** Zero-price sale orders are fulfilled normally; Sapo COGS(301) includes these units. Revenue=0 is the only reliable discriminator for the promo split. Source of line revenue: `std_order_items.line_amount` (= `quantity × price − discount` per line). A line is promo when `line_amount = 0` (or ≤ threshold) for a goods SKU.
- **Gift-no-invoice case:** Sapo has MAC cost (trans_type=301 OUT movement) but MISA has no corresponding 632 or 642 entry (goods given away without MISA invoice). These appear as `cogs_source='sapo_only'` in `int_order_cogs_reconciled`. Must be included in `promo_goods_cost`, not dropped. Flag: `cogs_source='sapo_only'` AND revenue=0.
- **The count-once crux:** When phase 04 builds the overhead pool from MISA expense ledger (TK642/635/641-common), it reads `overhead_costs_monthly` — a SEPARATE ingestion from the sales ledger. However, if the MISA expense ledger ALSO contains the same promo-goods-642 entries (possible if MISA books them to both ledgers, or if the Sổ cái TK642 aggregation includes them), there is a double-count risk. The dedup mechanism must subtract the sales-ledger-642 amount from the overhead pool. This phase defines that subtraction rule precisely.
- **`is_promo_line` flag in MISA** — `std_misa_sales_lines.is_promo_line` is already set (`TRUE` on 1,709 of 2,189 TK642 lines). The remaining 480 TK642 lines are "near-zero-revenue" (not strictly zero but flagged via `is_promo_line=FALSE`). Treat both subsets consistently: `cost_account_group='642'` is the controlling filter, `is_promo_line` is supplementary.
- **Sapo line revenue join**: `std_order_items` has `order_id`, `order_code`, `variant_id`, `sku` (infer from variant_id join or direct), `line_amount`. The join to `int_order_cogs_reconciled` is `(order_code, sku)`. Confirm `std_order_items.sku` is populated or derive via `variant_id → dim_variants`.

---

## Requirements

### Functional

**Cost taxonomy (codified, enforced by SQL structure):**

| Tier | Cost type | Account | Source | Lands in |
|------|-----------|---------|--------|----------|
| 1 | `cogs` | TK632 (MISA) / Sapo-MAC | `int_order_cogs_reconciled` (revenue>0 lines only) | `fact_order_costs.cost_category='COGS'`; `fact_order_economics.cogs_amount` |
| 2a | `promo_goods_cost` | TK642 (sales ledger) / Sapo-MAC (revenue=0 lines) | `int_order_promo_goods_cost` | `fact_order_costs.cost_category='PROMO_GOODS'`; `fact_order_economics.promo_goods_cost` |
| 2b | `platform_*` / `shipping_*` / `discount_*` | TK641 direct / Shopee fees / Sapo discounts | existing CTEs in `fact_order_costs` | unchanged |
| 3 | `overhead_*` | TK642 EXPENSE LEDGER net-of-promo / 635 / 641-common | `int_order_overhead_allocation` (phase 04) | `fact_order_costs.cost_category='OVERHEAD'` |

Rules:
- Tier 1 COGS: ONLY lines where `revenue > 0` (Sapo order_items `line_amount > 0`). Never include revenue=0 lines.
- Tier 2a promo: ONLY lines where `revenue = 0` for goods SKUs. NOT applicable to service lines (DV%/CPBH%).
- Tier 3 overhead pool: TK642 from MISA EXPENSE LEDGER (future `overhead_costs_monthly`) MINUS the sales-ledger-642 total already counted in tier 2a. See count-once mechanism below.
- These tiers are ADDITIVE (subtracted from revenue in sequence per waterfall); never summed into one number.

**`int_order_promo_goods_cost` (NEW):**
- Grain: `(order_code, sku)` — one row per promo line per order
- Sources: `int_order_cogs_reconciled` (for Sapo-MAC COGS value + cogs_source) + `std_order_items` (for line_amount = line revenue)
- Join: `int_order_cogs_reconciled LEFT JOIN std_order_items ON (order_code, sku)` — get line revenue
- Promo filter: `line_amount = 0` OR (`line_amount IS NULL` AND `cogs_source = 'sapo_only'`) for goods lines
  - Additional check: exclude service lines (product_code LIKE 'DV%' / 'CPBH%') if they surface here
- `promo_goods_cost_amount`: use `cogs_goods_primary` (= Sapo-MAC for promo lines; if both sides present but revenue=0, still use Sapo-MAC per CONTRACT)
- Columns:

| Column | Type | Derivation |
|--------|------|------------|
| `order_code` | VARCHAR | from int_order_cogs_reconciled |
| `sku` | VARCHAR | from int_order_cogs_reconciled |
| `variant_id` | VARCHAR | from int_order_cogs_reconciled |
| `promo_goods_cost_amount` | BIGINT | `cogs_goods_primary` (Sapo-MAC) |
| `line_revenue` | BIGINT | `std_order_items.line_amount` (0 or NULL for promo) |
| `cogs_source` | VARCHAR | inherited from int_order_cogs_reconciled |
| `is_gift_no_invoice` | BOOLEAN | `cogs_source = 'sapo_only'` (Sapo has MAC; MISA absent) |
| `has_misa_642` | BOOLEAN | corresponding TK642 row exists in std_misa_sales_lines for this (order_code, sku) |
| `misa_642_amount` | BIGINT | TK642 cogs_amount from std_misa_sales_lines (for cross-tier reconciliation) |
| `cost_type` | VARCHAR | `'promo_goods_cost'` (literal) |
| `cost_category` | VARCHAR | `'PROMO_GOODS'` (literal) |

- Note: `misa_642_amount` is populated by a secondary join to `std_misa_sales_lines WHERE cost_account_group='642'` on `(voucher_no, product_code)`. This enables the count-once dedup (see below).

**Extend `fact_order_costs` — add PROMO_GOODS rows:**
- New CTE `promo_goods` sourced from `int_order_promo_goods_cost`, emitting rows with:
  - `cost_type = 'promo_goods_cost'`
  - `cost_category = 'PROMO_GOODS'`
  - `amount = promo_goods_cost_amount`
  - `source_system = 'sapo'` (primary); `source_record = order_code`
  - `fee_source = 'actual'`
- UNION ALL into the final SELECT (after existing COGS, Shopee, discounts)
- `fact_order_costs` now has cost_category ∈ {COGS, PLATFORM_FEE, SHIPPING, PAYMENT, TAX, DISCOUNT, PROMO_GOODS, OVERHEAD (phase 04)}

**Extend `fact_order_economics` — add `promo_goods_cost` column:**
- New CTE `order_promo` = `SELECT order_code, SUM(promo_goods_cost_amount) AS promo_goods_cost FROM int_order_promo_goods_cost GROUP BY order_code`
- LEFT JOIN into final SELECT on `order_code`
- Add column `promo_goods_cost BIGINT` (NULL for orders with no promo lines)
- Do NOT change `channel_net_profit` formula yet (phase 05 repoints the full waterfall)
- Do NOT change `cogs_amount` (BUG-1 fix from phase 02 already correct)

**Cross-tier 642 count-once mechanism (the crux — feeds phase 04):**

The problem: when phase 04 ingests `overhead_costs_monthly` (TK642 from MISA expense/Sổ cái), that aggregate monthly TK642 figure may include the promo-goods entries already counted in tier 2a. If so, phase 04's overhead pool is inflated by ~1.08B.

Mechanism (defined here, consumed by phase 04):

1. **Determine sales-ledger-642 total per period** — `int_order_promo_goods_cost` carries `misa_642_amount` per (order_code, sku). Aggregate to monthly total:
   ```sql
   -- Model: int_promo_642_monthly_total (new, tiny, feeds phase 04)
   SELECT
       DATE_TRUNC('month', o.date_key::DATE) AS period_month,
       SUM(p.misa_642_amount)                 AS sales_ledger_642_amount
   FROM int_order_promo_goods_cost p
   JOIN fact_orders o ON p.order_code = o.order_code
   WHERE p.has_misa_642 = TRUE
   GROUP BY 1
   ```

2. **Phase 04 overhead pool formula** (to be implemented in phase 04):
   ```
   overhead_pool_net(period) =
       overhead_costs_monthly.amount  (raw TK642 from expense ledger)
     - COALESCE(int_promo_642_monthly_total.sales_ledger_642_amount, 0)
   ```
   This subtraction is only valid IF the expense ledger includes the sales-ledger-642 portion. If MISA books promo-642 to a SEPARATE sub-account that is already excluded from the Sổ cái TK642 export, the subtraction produces a double-subtraction (wrong). → **Phase 04 must verify this empirically** before applying the deduction.

3. **`int_promo_642_monthly_total`** (NEW, tiny helper model, ~12 rows/year):
   - Grain: `period_month` (first of month)
   - Columns: `period_month DATE`, `sales_ledger_642_amount BIGINT`, `line_count INT`
   - Materialized: TABLE (tiny; refreshed each run)
   - Purpose: the SINGLE authoritative source of "how much 642 is already counted in tier 2a per period" — phase 04 joins this to subtract from the expense-ledger pool

4. **Documentation requirement for phase 04**: phase 04 MUST confirm via empirical check whether `overhead_costs_monthly.account='642%'` totals include or exclude the sales-ledger-642 portion. If included → subtract `int_promo_642_monthly_total.sales_ledger_642_amount`. If excluded → no subtraction needed (they are already separate). This is an **open Q** (see end of file) that phase 04 must resolve.

### Non-Functional

- `int_order_promo_goods_cost`: TABLE materialization (grain same as int_order_cogs_reconciled; manageable size)
- `int_promo_642_monthly_total`: TABLE materialization (tiny — ~12–24 rows total)
- All CONCURRENT STREAM coordination applies to `fact_order_costs` and `fact_order_economics` edits
- DuckDB single-writer: pause schedules before any dbt build touching mart models

---

## Architecture

### Data Flow

```
int_order_cogs_reconciled  (phase 02 output)
  ├─── [promo filter: line_amount=0] ──► int_order_promo_goods_cost ──────────────────────────────────┐
  │      (LEFT JOIN std_order_items for line_amount)                                                    │
  │      (LEFT JOIN std_misa_sales_lines WHERE cost_account_group='642' for misa_642_amount)            │
  │                                                                                                     │
  └─── [sold filter: line_amount>0] ──► [phase 05: repoint fact cogs]                                 │
                                                                                                        │
int_order_promo_goods_cost ──────────────────────────────────────────────────────────────────────────► fact_order_costs (PROMO_GOODS rows)
                         └──► [GROUP BY order_code] ──────────────────────────────────────────────► fact_order_economics (promo_goods_cost col)
                         └──► [GROUP BY period_month, has_misa_642=TRUE] ──► int_promo_642_monthly_total ──► (phase 04 pool deduction input)


Cost taxonomy boundary enforcement:
  fact_order_economics.cogs_amount     ← only revenue>0 lines (BUG-1 fixed in phase 02)
  fact_order_economics.promo_goods_cost ← only revenue=0 lines (this phase)
  [channel_net_profit unchanged; phase 05 adds it to waterfall]
  [fully_loaded_net_profit: phase 04]
```

### `int_order_promo_goods_cost` — Key Join Logic

```sql
-- Step 1: start from reconciled COGS, join line revenue
WITH promo_candidates AS (
    SELECT
        r.order_code, r.sku, r.variant_id,
        r.cogs_goods_primary  AS promo_goods_cost_amount,
        r.cogs_source,
        COALESCE(i.line_amount, 0) AS line_revenue
    FROM int_order_cogs_reconciled r
    LEFT JOIN std_order_items i ON r.order_code = i.order_code AND r.sku = i.sku
    WHERE COALESCE(i.line_amount, 0) = 0   -- revenue=0 = promo/gift line
      AND r.cogs_goods_primary IS NOT NULL  -- must have a cost to record
      AND r.sku NOT LIKE 'DV%'             -- exclude service SKUs
      AND r.sku NOT LIKE 'CPBH%'
),

-- Step 2: join MISA TK642 rows to get misa_642_amount
misa_642 AS (
    SELECT voucher_no AS order_code, product_code AS sku,
           SUM(cogs_amount) AS misa_642_amount
    FROM std_misa_sales_lines
    WHERE cost_account_group = '642'
    GROUP BY 1, 2
)

SELECT
    p.*,
    p.cogs_source = 'sapo_only'  AS is_gift_no_invoice,
    m.misa_642_amount IS NOT NULL AS has_misa_642,
    m.misa_642_amount,
    'promo_goods_cost'  AS cost_type,
    'PROMO_GOODS'       AS cost_category
FROM promo_candidates p
LEFT JOIN misa_642 m ON p.order_code = m.order_code AND p.sku = m.sku
```

### `std_order_items` Join — Confirming SKU Column Availability

`std_order_items` has `order_id`, `order_code`, `variant_id`, `line_amount`. Check if `sku` column exists directly or must be derived via `dim_variants` (variant_id → sku). If `sku` is absent: join `dim_variants ON variant_id` to get `sku`, then join on `(order_code, sku)`. This lookup must be confirmed before implementation.

---

## Related Code Files

### To Create
- `transformation/models/intermediate/cogs/int_order_promo_goods_cost.sql`
- `transformation/models/intermediate/cogs/int_promo_642_monthly_total.sql`

### To Modify
- `transformation/models/marts/sales/fact_order_costs.sql` — add `promo_goods` CTE + UNION ALL (CONCURRENT STREAM — coordinate)
- `transformation/models/marts/sales/fact_order_economics.sql` — add `order_promo` CTE + `promo_goods_cost` column (CONCURRENT STREAM — coordinate)

### To Read (do not modify)
- `transformation/models/staging/standard/std_order_items.sql` — confirm `sku` column presence
- `transformation/models/marts/sales/dim_variants.sql` or equivalent — for variant_id → sku mapping if needed

### DO NOT TOUCH (other phases own)
- `phase-04-overhead-allocation.md` — reads `int_promo_642_monthly_total`; that file is phase 04's domain
- `phase-05-pl-marts-serving.md` — owns full waterfall repoint in `fact_order_economics`

---

## Implementation Steps

1. **Confirm phase 02 is GREEN** — `int_order_cogs_reconciled` Dagster SUCCESS before proceeding.

2. **Confirm concurrent stream coordination** — same as phase 02: no uncommitted edits to `fact_order_economics` / `fact_order_costs`.

3. **Verify `std_order_items` schema** — check if `sku` is a direct column:
   ```bash
   docker exec data_platform dbt show \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select std_order_items --limit 1
   ```
   If `sku` absent: identify the variant_id → sku mapping model (likely `dim_variants` or `std_variants`); add to join chain.

4. **Create `int_order_promo_goods_cost.sql`**
   - Config: `materialized='table'`, `tags=['int', 'cogs', 'promo']`
   - Header comment: grain, promo filter rationale, gift-no-invoice case, misa_642_amount purpose
   - CTEs: `promo_candidates` (int_order_cogs_reconciled × std_order_items, line_amount=0 filter), `misa_642` (std_misa_sales_lines cost_account_group='642' aggregated), final SELECT with all columns per schema
   - Validate: service SKU exclusion filter (`NOT LIKE 'DV%'` / `'CPBH%'`)

5. **Create `int_promo_642_monthly_total.sql`**
   - Config: `materialized='table'`, `tags=['int', 'cogs', 'promo', 'overhead-dedup']`
   - Header comment: PURPOSE — provides per-period sales-ledger-642 total for phase 04 overhead pool deduction; only valid if expense ledger includes this amount (confirm in phase 04)
   - Source: `int_order_promo_goods_cost` joined to `fact_orders` (for date_key → period_month)
   - Filter: `has_misa_642 = TRUE` (only lines where MISA also booked to 642; gift-no-invoice excluded since MISA never booked it, so it can't be in the expense ledger either)
   - Group by: `DATE_TRUNC('month', order_date)::DATE AS period_month`

6. **Extend `fact_order_costs.sql`** — add `promo_goods` CTE:
   ```sql
   promo_goods AS (
       SELECT
           o.order_id,
           p.order_code,
           p.cost_type,
           p.cost_category,
           CAST(SUM(p.promo_goods_cost_amount) AS DECIMAL(18,2)) AS amount,
           NULL           AS discount_rate,
           NULL           AS discount_type,
           'sapo'         AS source_system,
           p.order_code   AS source_record,
           'actual'       AS fee_source,
           o.date_key,
           o.channel_key
       FROM int_order_promo_goods_cost p
       JOIN order_meta o ON p.order_code = o.order_code
       GROUP BY o.order_id, p.order_code, p.cost_type, p.cost_category, o.date_key, o.channel_key
   )
   ```
   Add `UNION ALL SELECT ... FROM promo_goods` to final SELECT.

7. **Extend `fact_order_economics.sql`** — add `order_promo` CTE and column:
   ```sql
   order_promo AS (
       SELECT order_code, SUM(promo_goods_cost_amount) AS promo_goods_cost
       FROM {{ ref('int_order_promo_goods_cost') }}
       GROUP BY order_code
   )
   -- In final SELECT: p.promo_goods_cost (from LEFT JOIN order_promo p ON o.order_code = p.order_code)
   ```
   Add column between `has_cogs` and `gross_profit` for logical waterfall ordering.

8. **dbt compile**:
   ```bash
   docker exec data_platform dbt compile \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select int_order_promo_goods_cost int_promo_642_monthly_total fact_order_costs fact_order_economics
   ```

9. **dbt build** (pause schedules):
   ```bash
   docker exec data_platform dbt build \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select int_order_cogs_reconciled+ int_order_promo_goods_cost int_promo_642_monthly_total fact_order_costs fact_order_economics
   ```

10. **Validate promo split**:
    ```sql
    -- Total promo_goods_cost across all orders
    SELECT SUM(promo_goods_cost) FROM fact_order_economics WHERE promo_goods_cost IS NOT NULL;
    -- Cross-check: should approximate int_order_promo_goods_cost SUM(promo_goods_cost_amount)

    -- Gift-no-invoice count
    SELECT COUNT(*), SUM(promo_goods_cost_amount)
    FROM int_order_promo_goods_cost WHERE is_gift_no_invoice = TRUE;

    -- has_misa_642 coverage
    SELECT has_misa_642, COUNT(*), SUM(misa_642_amount)
    FROM int_order_promo_goods_cost GROUP BY 1;
    -- has_misa_642=TRUE SUM ≈ 1.08B (matches design §1a)

    -- int_promo_642_monthly_total spot-check
    SELECT period_month, sales_ledger_642_amount FROM int_promo_642_monthly_total ORDER BY 1;
    ```

11. **Validate no double-count**:
    ```sql
    -- fact_order_economics: cogs_amount + promo_goods_cost should NOT overlap
    -- cogs_amount = revenue>0 lines; promo_goods_cost = revenue=0 lines
    -- SUM(cogs_amount) should be BUG-1-clean (from phase 02)
    -- SUM(promo_goods_cost) ≈ Sapo-MAC cost of promo units
    SELECT
        SUM(cogs_amount)       AS total_cogs,
        SUM(promo_goods_cost)  AS total_promo,
        SUM(cogs_amount) + COALESCE(SUM(promo_goods_cost),0) AS combined
    FROM fact_order_economics;
    -- combined should equal pre-BUG-1-fix cogs_amount (all units at MAC, just re-labelled)
    ```

12. **Dagster manual run** → SUCCESS.

---

## Todo

- [ ] Phase 02 GREEN (gate check)
- [ ] Concurrent stream coordination confirmed
- [ ] Verify `std_order_items.sku` column presence (or identify variant_id→sku join)
- [ ] Create `int_order_promo_goods_cost.sql`
- [ ] Create `int_promo_642_monthly_total.sql`
- [ ] Extend `fact_order_costs.sql` — add promo_goods CTE + UNION ALL
- [ ] Extend `fact_order_economics.sql` — add order_promo CTE + promo_goods_cost column
- [ ] `dbt compile` — no errors
- [ ] `dbt build` — full chain green
- [ ] Validate promo split totals (SUM ~1.08B in has_misa_642 subset)
- [ ] Validate gift-no-invoice count / amount
- [ ] Validate no double-count (cogs + promo = pre-BUG-1 total)
- [ ] `int_promo_642_monthly_total` spot-check (period totals reasonable)
- [ ] Dagster manual run → SUCCESS
- [ ] Hand-off note to phase 04: document whether expense ledger includes sales-ledger-642

---

## Success Criteria

| Check | Pass condition |
|-------|---------------|
| `int_order_promo_goods_cost` row count | ≈ count of distinct (order_code, sku) pairs with line_amount=0 in std_order_items |
| `has_misa_642=TRUE` SUM(misa_642_amount) | ≈ 1.08B (matches design §1a TK642 total) |
| `is_gift_no_invoice` rows present | > 0 (Sapo-only promo cases captured) |
| No promo_goods_cost in COGS | `fact_order_costs` has 0 rows where cost_category='COGS' AND cost_type='promo_goods_cost' |
| No COGS in PROMO_GOODS | `int_order_promo_goods_cost` has 0 rows where line_revenue > 0 (no mis-classified sold lines) |
| `fact_order_economics.promo_goods_cost` | Non-null for all orders with revenue=0 lines; NULL for orders with no promo |
| `int_promo_642_monthly_total` row count | One row per calendar month with promo activity (expect ~12–24 rows) |
| Double-count check | `SUM(cogs) + SUM(promo_goods_cost)` ≈ total Sapo-MAC OUT COGS (trans_type=301) at order level |
| Dagster run | Manual launch → SUCCESS; no broken assets in chain |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `std_order_items.sku` absent → join fails | Medium | High | Check schema first (step 3); fall back to dim_variants join if needed |
| Some promo lines have line_amount slightly > 0 (rounding, partial discount) | Medium | Medium | Use threshold `line_amount < 100` (1 VND) OR rely on `is_promo_line` from MISA as secondary signal; document choice |
| Sales-ledger-642 in expense ledger = double subtraction in phase 04 | Unknown | High | `int_promo_642_monthly_total` is ready; phase 04 MUST verify empirically before applying deduction |
| `fact_order_economics` / `fact_order_costs` concurrent edits | Medium | High | Same coordination protocol as phase 02; serialize commits |
| Service SKU filter incomplete (new DV/CPBH codes) | Low | Low | Filter pattern `LIKE 'DV%' OR LIKE 'CPBH%'` matches current data; add dbt test for unexpected service SKUs in promo model |
| `int_promo_642_monthly_total` joins `fact_orders` for date — circular dependency risk | Low | Medium | `fact_orders` is a stable upstream mart; no circular ref. Verify dbt DAG with `dbt ls --select int_promo_642_monthly_total --output graph` |

---

## Security / Data Integrity

- `promo_goods_cost` is a new visible P&L line item. Before surfacing in dashboards, confirm stakeholder understanding: this cost was previously hidden inside COGS; its appearance raises COGS (slightly) but correctly reveals promo spend. Not a regression.
- `int_promo_642_monthly_total` is ONLY a dedup helper for phase 04. It must not be exposed directly in Metabase (it would be misread as overhead). Access via phase 04 model only.
- The count-once rule is contractual (CONTRACT §4). Any future code that reads `overhead_costs_monthly` without subtracting `int_promo_642_monthly_total` is a violation. Add a comment block to `int_order_overhead_allocation` (phase 04) referencing this rule.

---

## Next Steps

- Phase 04 (`phase-04-overhead-allocation.md`) reads `int_promo_642_monthly_total` for the pool deduction. **Critical hand-off:** phase 04 implementer must first empirically confirm whether `overhead_costs_monthly` for TK642 includes or excludes the sales-ledger-642 entries (see Unresolved Q1). The deduction is conditional on that answer.
- Phase 05 (`phase-05-pl-marts-serving.md`) will update `fact_order_economics` waterfall formula to include `promo_goods_cost` in the tier-2 contribution calculation (`channel_net_profit` definition).
- Phase 06 (`phase-06-detailview-pl.md`) will show per-line promo_goods_cost in the detailView cost ledger.

---

## Unresolved Questions

1. **Expense-ledger 642 overlap (THE critical open Q for phase 04):** Does the MISA Sổ cái TK642 (source for `overhead_costs_monthly`) include the same 1.08B promo-goods entries that appear in the sales ledger? If yes → phase 04 MUST subtract `int_promo_642_monthly_total`. If MISA books these to a distinct sub-account excluded from the Sổ cái export → no subtraction needed. **Resolve by inspecting the actual Sổ cái TK642 export before phase 04 implementation.**
2. **`std_order_items.sku` column:** Confirm presence. If absent, confirm the correct dim_variants join path for variant_id → sku resolution.
3. **Promo line threshold:** Is `line_amount = 0` strict enough, or should we use `line_amount < N` (small threshold for rounding)? Check actual distribution of `line_amount` values on MISA `is_promo_line=TRUE` orders.
4. **`int_promo_642_monthly_total` date source:** Should period_month come from `fact_orders.date_key` (ICT fulfillment date) or from `std_misa_sales_lines.posting_date` (MISA booking date)? The overhead pool is period-based on MISA's fiscal calendar — MISA posting date is likely more appropriate for matching the expense ledger. Resolve before phase 04 pool definition.
