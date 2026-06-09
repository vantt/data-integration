---
title: "Phase 02 — COGS Reconciliation (int_order_cogs_reconciled + BUG-1 Fix)"
description: "Build int_order_cogs_reconciled (Sapo-MAC primary, MISA-632 recon, variance); fix BUG-1 TK642 lumping in fact_order_economics/fact_order_costs"
status: DONE
priority: P1
effort: 1.5d
tags: [cogs, reconciliation, misa, sapo-mac, bug-fix]
created: 2026-06-04
---

## Context Links

- Master plan: `plans/260604-1030-unified-order-pl-cogs-overhead/plan.md` — CONTRACT governs
- Design: `docs/architecture/order-pl/cogs-reconciliation-design.md` §3-§7 (feasibility, decision, model schema, aggregation rules)
- Phase 01 output (blocker): `phase-01-data-foundations-std-gate.md` — `std_misa_sales_lines` must be GREEN before this phase starts
- Source: `transformation/models/staging/standard/std_misa_sales_lines.sql` (to be created in phase 01)
- Source: `transformation/models/staging/standard/std_inventory_movements.sql` (exists)
- Source: `transformation/models/marts/inventory/fact_inventory_movements.sql` (exists)
- Affected models: `transformation/models/marts/sales/fact_order_economics.sql` (BUG-1 fix; CONCURRENT STREAM — coordinate)
- Affected models: `transformation/models/marts/sales/fact_order_costs.sql` (BUG-1 fix; CONCURRENT STREAM — coordinate)
- Analysis: `plans/reports/analysis-260604-0001-inventory-v2-data-nature.md` §5 (COGS = export_amount; trans_type=301 semantics)

---

## Overview

**Priority:** P1 — BUG-1 fix is independently shippable; full model feeds phase 03 + 04
**Status:** DONE
**Scope:**

1. **`int_order_cogs_reconciled`** (NEW, `intermediate/cogs/`) — grain `(order_code, sku)` — joins Sapo-MAC COGS (from `std_inventory_movements` trans_type=301, net of returns 350) against MISA TK632 COGS (from `std_misa_sales_lines` where `cost_account_group='632'`). Emits both sides + variance + flags + `cogs_goods_primary` (Sapo-MAC by default via dbt var).
2. **BUG-1 fix** (INTERIM) — add `WHERE m.cost_account_group = '632'` (or `cogs_account LIKE '632%'`) filter in:
   - `fact_order_economics.sql` `misa_order` CTE (line ~32: `SUM(cogs_amount)`)
   - `fact_order_costs.sql` `cogs` CTE (line ~27: `WHERE m.cogs_amount IS NOT NULL`)
   - This is interim (direct MISA filter); longer-term repoint to `int_order_cogs_reconciled` in phase 05.

---

## Key Insights

- **BUG-1 (live, high impact):** `fact_order_economics.misa_order` CTE does `SUM(cogs_amount)` from `int_misa_sales_lines` with NO TK filter → the ~1.08B TK642 promo-goods cost is lumped into `cogs_amount`. Effect: `gross_profit` understated, promo spend invisible, `channel_net_profit` skewed. Fix = add `cost_account_group = '632'` filter (once std_ is live) or `cogs_account LIKE '632%'` (direct to stg, interim). Expected delta: COGS drops ~1.08B across all orders with promo lines.
- **Sapo-MAC COGS filter = `trans_type=301` only.** Per analysis: `trans_type=301` = `sale_order_fulfillment` (24,725 rows, 48.4B COGS). Exclude: `200/203` stock_transfer (16B, inter-warehouse), `400/401` stock_adjustment, `501` catalog-init, `600` cost-adjust. Returns = `trans_type=350` → net against 301 COGS.
- **Promo lines ride inside trans_type=301**: verified (cogs-reconciliation-design §2b). Promo/gift orders are fulfilled as zero-price sale orders. Sapo-MAC COGS(301) therefore INCLUDES promo goods cost. The split COGS(sold) vs promo_goods_cost happens via a JOIN to `std_order_items.line_amount` (revenue per line) in phase 03 — NOT in this phase. Phase 02 builds the full reconciliation; phase 03 adds the revenue=0 split.
- **Join keys**: MISA `voucher_no` ↔ Sapo `document_code` (= `order_code`); MISA `product_code` ↔ Sapo `sku` (~96% match, ~4% gap is 8 MISA codes unmatched + 8 Sapo SKUs MISA never sees — handle with FULL OUTER JOIN, flag gaps).
- **`cogs_goods_primary`** defaults to `cogs_goods_sapo` per CONTRACT. Switchable via dbt var `cogs_primary_source` (`'sapo_mac'` default | `'misa'`). Never sum both sides.
- **`fact_inventory_movements` vs `std_inventory_movements`** for COGS source: use `std_inventory_movements` (filtered to trans_type=301/350) since `fact_inventory_movements` already excludes `quantity_delta=0` rows but passes through all trans_types. Either works; `std_` is preferred for an int model (per R1).

---

## Requirements

### Functional

**`int_order_cogs_reconciled`:**
- Grain: `(order_code, sku)` — one row per order × SKU pair (FULL OUTER JOIN of Sapo and MISA sides)
- Sapo side:
  - Source: `std_inventory_movements`
  - Filter: `trans_type IN (301, 350)` only; `quantity_delta != 0`
  - COGS for OUT (sales) = SUM(`cogs_amount`) where `movement_direction='OUT'` AND `trans_type=301`
  - Net of returns = subtract SUM(`cogs_amount`) where `movement_direction='IN'` AND `trans_type=350`
  - Keys: `document_code AS order_code`, `sku`
  - `qty_sapo` = SUM(`quantity_delta`) net (negative for OUT, net with 350 return INs)
  - `variant_id` = MAX(`variant_id`) — denormalize for downstream joins
- MISA side:
  - Source: `std_misa_sales_lines`
  - Filter: `cost_account_group = '632'` (true COGS only; excludes 642 promo and service lines)
  - Also exclude `is_service_line = TRUE` (DV%/CPBH% product codes)
  - Keys: `voucher_no AS order_code`, `product_code AS sku`
  - `cogs_goods_misa` = SUM(`cogs_amount`) per (order_code, sku)
  - `qty_misa` = SUM(`quantity`)
- Output columns (per design §5):

| Column | Type | Derivation |
|--------|------|------------|
| `order_code` | VARCHAR | COALESCE(sapo.document_code, misa.voucher_no) |
| `sku` | VARCHAR | COALESCE(sapo.sku, misa.product_code) |
| `variant_id` | VARCHAR | from Sapo side; NULL if sapo_only gap |
| `qty_sapo` | DECIMAL | net signed quantity from Sapo (OUT−return IN) |
| `qty_misa` | BIGINT | from MISA |
| `cogs_goods_sapo` | BIGINT | Sapo MAC COGS net of returns (trans_type=301 OUT − 350 IN) |
| `cogs_goods_misa` | BIGINT | MISA SUM(cogs_amount) WHERE cost_account_group='632' |
| `cogs_variance` | BIGINT | cogs_goods_sapo − cogs_goods_misa (NULL if either side absent) |
| `cogs_variance_pct` | DOUBLE | cogs_variance / NULLIF(cogs_goods_misa, 0) |
| `has_sapo_cogs` | BOOLEAN | cogs_goods_sapo IS NOT NULL |
| `has_misa_cogs` | BOOLEAN | cogs_goods_misa IS NOT NULL |
| `cogs_source` | VARCHAR | 'sapo_mac'\|'misa'\|'both'\|'none' |
| `cogs_goods_primary` | BIGINT | var-driven: default = cogs_goods_sapo; if var='misa' → cogs_goods_misa |

- `cogs_source` derivation:
  - `'both'` = has_sapo_cogs AND has_misa_cogs
  - `'sapo_mac'` = has_sapo_cogs AND NOT has_misa_cogs (incl. marketplace orders, ~33%)
  - `'misa'` = has_misa_cogs AND NOT has_sapo_cogs
  - `'none'` = neither

- dbt var `cogs_primary_source` (default `'sapo_mac'`):
  ```sql
  {{ var('cogs_primary_source', 'sapo_mac') }}
  -- Used in: CASE WHEN '{{ var(...) }}' = 'sapo_mac' THEN cogs_goods_sapo ELSE cogs_goods_misa END
  ```

**BUG-1 fix (interim, in `fact_order_economics` and `fact_order_costs`):**
- `fact_order_economics.sql` `misa_order` CTE: add filter on MISA join to exclude TK642 rows
- `fact_order_costs.sql` `cogs` CTE: add same filter
- Two options (implement Option A, document Option B for phase 05):
  - **Option A (interim, this phase):** Filter via `std_misa_sales_lines.cost_account_group = '632'` — requires int to expose cost_account_group OR change the source ref in misa_order CTE directly to `std_misa_sales_lines`. Prefer: add `cost_account_group` to `int_misa_sales_lines` pass-through (no functional change, just column add), then filter `WHERE i.cost_account_group = '632'`.
  - **Option B (full repoint, phase 05):** Replace `misa_order` CTE with join to `int_order_cogs_reconciled` — cleaner but deferred.
- After BUG-1 fix: `cogs_amount` in `fact_order_economics` drops by ~1.08B (orders with TK642 promo lines). `gross_profit` and `channel_net_profit` increase by same amount. Promo cost is NOT yet surfaced in fact_order_costs as a separate row in this phase (that is phase 03).

### Non-Functional
- `int_order_cogs_reconciled` materialized as TABLE (or incremental if row count grows; start with TABLE for simplicity, KISS)
- DuckDB: pause schedules before any dbt build that touches mart models
- `fact_order_economics` / `fact_order_costs` are SHARED with concurrent stream — serialize edits; confirm no concurrent uncommitted changes before BUG-1 commit

---

## Architecture

### Data Flow

```
std_inventory_movements  (trans_type=301/350, quantity_delta!=0)
  └─[sapo_cogs CTE: SUM export_amount by document_code+sku, net of 350 returns]
                              ┐
                              ├──FULL OUTER JOIN on (order_code, sku)──► int_order_cogs_reconciled
                              ┘
std_misa_sales_lines  (cost_account_group='632', NOT is_service_line)
  └─[misa_cogs CTE: SUM cogs_amount by voucher_no+product_code]


int_order_cogs_reconciled ──► (phase 03) int_order_cogs_with_promo_split
                          ──► (phase 05) fact_order_economics (replaces misa_order CTE)
                          ──► (phase 05) fact_order_costs COGS rows

BUG-1 fix (interim, this phase):
fact_order_economics.misa_order CTE: + WHERE cost_account_group='632'
fact_order_costs.cogs CTE:           + WHERE cost_account_group='632'
```

### Join Logic — Handling the ~4% Gap

FULL OUTER JOIN on `(order_code, sku)`:
- Matched (~96%): both sides populated; `cogs_source='both'`
- Sapo-only (~4% MISA gap + marketplace orders ~33%): `cogs_source='sapo_mac'`
- MISA-only (rare; 8 codes never seen in Sapo): `cogs_source='misa'`; flag for audit
- Neither: `cogs_source='none'`; flag (data quality issue)

For marketplace orders (~33%, document_code is marketplace code not SON…): MISA may have them under the same voucher_no. Join still works via `order_code`. If MISA lacks the record → `cogs_source='sapo_mac'` (acceptable per design §6).

### CTE Structure

```sql
sapo_cogs AS (
  -- FROM std_inventory_movements
  -- WHERE trans_type IN (301, 350) AND quantity_delta != 0
  -- GROUP BY document_code, sku
  -- OUT legs: SUM(cogs_amount) WHERE movement_direction='OUT' AND trans_type=301
  -- Return legs: SUM(cogs_amount) WHERE movement_direction='IN' AND trans_type=350
  -- cogs_goods_sapo = out_cogs - return_cogs
)

misa_cogs AS (
  -- FROM std_misa_sales_lines
  -- WHERE cost_account_group = '632'
  --   AND NOT (product_code LIKE 'DV%' OR product_code LIKE 'CPBH%')
  -- GROUP BY voucher_no, product_code
)

FULL OUTER JOIN sapo_cogs s ON misa_cogs m
  ON s.order_code = m.voucher_no
  AND s.sku = m.product_code
SELECT ... cogs_source ... cogs_goods_primary
```

---

## Related Code Files

### To Create
- `transformation/models/intermediate/cogs/int_order_cogs_reconciled.sql`

### To Modify
- `transformation/models/marts/sales/fact_order_economics.sql` — BUG-1: add `cost_account_group='632'` filter in `misa_order` CTE (CONCURRENT STREAM — coordinate before editing)
- `transformation/models/marts/sales/fact_order_costs.sql` — BUG-1: add `cost_account_group='632'` filter in `cogs` CTE (CONCURRENT STREAM — coordinate before editing)
- `transformation/models/intermediate/misa/int_misa_sales_lines.sql` — add `cost_account_group` to SELECT list (pass-through from std_; needed so BUG-1 filter can reference it in fact models)
- `transformation/models/staging/standard/schema.yml` — add `int_order_cogs_reconciled` docs (or add to intermediate schema.yml if one exists)

### DO NOT TOUCH (phase 05 owns)
- Full repoint of `fact_order_economics` → `int_order_cogs_reconciled` (deferred)

---

## Implementation Steps

1. **Confirm phase 01 is GREEN** — `std_misa_sales_lines` Dagster run SUCCESS before proceeding.

2. **Coordinate with concurrent stream** — confirm `fact_order_economics.sql` and `fact_order_costs.sql` have no uncommitted changes. Agree on serialization: this phase's BUG-1 commit goes in AFTER any concurrent stream commits to those files.

3. **Add `cost_account_group` pass-through to `int_misa_sales_lines.sql`**
   - Add `cost_account_group` to the SELECT list (already computed in `std_misa_sales_lines`)
   - This allows `fact_order_economics`/`fact_order_costs` to filter without changing their source table

4. **Create `transformation/models/intermediate/cogs/` directory** (if not exists)

5. **Create `int_order_cogs_reconciled.sql`**:
   - Config: `materialized='table'`, `tags=['int', 'cogs']`
   - Header comment: grain, PK, key semantics (trans_type=301 filter rationale, return netting, FULL OUTER JOIN logic, ~4% gap handling)
   - `sapo_cogs` CTE: from `std_inventory_movements`, filter `trans_type IN (301, 350)`, aggregate per `(document_code, sku)`, compute `cogs_goods_sapo = SUM out COGS - SUM return COGS`, `qty_sapo = SUM(quantity_delta)`, `variant_id = MAX(variant_id)`
   - `misa_cogs` CTE: from `std_misa_sales_lines`, filter `cost_account_group='632'` AND NOT is_service_line, aggregate per `(voucher_no, product_code)`, compute `cogs_goods_misa`, `qty_misa`
   - FULL OUTER JOIN + derived columns per schema above
   - dbt var for `cogs_goods_primary`

6. **BUG-1 fix — `fact_order_economics.sql`**:
   - In `misa_order` CTE, change source ref from `int_misa_sales_lines` to `std_misa_sales_lines` (or keep int but add `WHERE cost_account_group = '632'` — simpler if int now exposes the column)
   - Add `cost_account_group` to `misa_order` CTE filter: `WHERE cost_account_group = '632'`
   - Add `cogs_source` column (from `int_order_cogs_reconciled` — either via a new join or via a subselect; for interim fix, a `LEFT JOIN int_order_cogs_reconciled` on `order_code` may be too heavy at this stage; defer `cogs_source` column to phase 05 full repoint. For now, just fix the filter.)

7. **BUG-1 fix — `fact_order_costs.sql`**:
   - In `cogs` CTE, add `WHERE m.cost_account_group = '632'` (after adding cost_account_group to int_)
   - Verify `ABS(SUM(m.cogs_amount))` now excludes 642 rows

8. **dbt compile** both changes:
   ```bash
   docker exec data_platform dbt compile \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select int_order_cogs_reconciled fact_order_economics fact_order_costs
   ```

9. **dbt build** (pause schedules first):
   ```bash
   docker exec data_platform dbt build \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select int_misa_sales_lines int_order_cogs_reconciled fact_order_economics fact_order_costs
   ```

10. **Quantify BUG-1 delta** — run before/after comparison:
    ```sql
    -- Before (baseline from git): total cogs_amount in fact_order_economics
    -- After fix: SELECT SUM(cogs_amount) FROM fact_order_economics
    -- Expected delta: ≈ +1.08B (COGS decreases by ~1.08B = 642 promo portion removed)
    -- gross_profit increases by same amount
    ```

11. **Validate `int_order_cogs_reconciled`**:
    ```sql
    SELECT cogs_source, COUNT(*), SUM(cogs_goods_sapo), SUM(cogs_goods_misa)
    FROM int_order_cogs_reconciled
    GROUP BY 1;
    -- 'both': expect ~96% of MISA-matched orders
    -- 'sapo_mac': expect marketplace + unmatched
    -- 'misa': expect ≤8 cases (MISA codes with no Sapo SKU)
    -- 'none': expect 0 or near-0
    ```

12. **Dagster manual run** — launch full transformation job. Confirm SUCCESS for all affected assets.

---

## Todo

- [x] Phase 01 GREEN (gate check)
- [x] Concurrent stream coordination confirmed (no open edits on fact_order_economics / fact_order_costs)
- [x] Add `cost_account_group` to `int_misa_sales_lines` SELECT
- [x] Create `intermediate/cogs/` directory
- [x] Create `int_order_cogs_reconciled.sql`
- [x] BUG-1: fix `fact_order_economics.sql` misa_order CTE (add cost_account_group='632' filter)
- [x] BUG-1: fix `fact_order_costs.sql` cogs CTE (add cost_account_group='632' filter)
- [x] `dbt compile` — no errors
- [x] `dbt build` — all green
- [x] BUG-1 delta verified (~+1.08B COGS drop from economics total)
- [x] `int_order_cogs_reconciled` cogs_source distribution validated
- [x] Dagster manual run → SUCCESS
- [x] Resume Dagster schedules

---

## Success Criteria

| Check | Pass condition |
|-------|---------------|
| `int_order_cogs_reconciled` row count | ≥ distinct (order_code, sku) pairs in Sapo inventory trans_type=301 |
| `cogs_source='both'` coverage | ≥ 96% of MISA-matched orders (per feasibility §3) |
| `cogs_variance` distribution | Median variance near 0 for '632%' lines; outliers surfaced not silenced |
| BUG-1 `fact_order_economics.cogs_amount` | Drops ~1.08B (TK642 removed); `gross_profit` rises by same |
| BUG-1 `fact_order_costs` | No cost_type='cogs' rows where original cost was TK642 |
| No double-count | `SUM(cogs_goods_primary)` uses exactly one column per row |
| Dagster run | Manual launch → SUCCESS, no broken assets |
| `cogs_source='none'` | 0 rows or flagged as data-quality exceptions |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Concurrent stream edits `fact_order_economics` simultaneously | Medium | High | Coordinate explicitly; serialize commit; check git diff before editing |
| FULL OUTER JOIN on (order_code, sku) produces fanout (multiple variant_ids per SKU) | Low | Medium | `variant_id = MAX(variant_id)`; validate no unexpected row multiplication |
| ~4% unmatched MISA codes silently drop COGS | Low | Medium | FULL OUTER JOIN + `cogs_source='misa'` flag; do NOT inner join |
| `trans_type=350` return netting overstates return deduction | Low | Low | Validate: net `cogs_goods_sapo` must be ≥ 0 for normal orders |
| `int_order_cogs_reconciled` as TABLE creates DuckDB write contention | Medium | Medium | Pause Dagster schedules; single-writer rule |
| BUG-1 fix changes existing dashboard numbers unexpectedly | High | Medium | Communicate change to stakeholders before deploying; delta is expected and positive (COGS drops, profit rises) |

---

## Security / Data Integrity

- Never `SUM(cogs_goods_sapo + cogs_goods_misa)` — aggregation rule #1 in design §6 is binding.
- `cogs_goods_primary` must be the ONLY column used in downstream COGS totals; `cogs_goods_misa` is reconciliation-only.
- BUG-1 fix alters reported `gross_profit` / `channel_net_profit` — this is a correction, not a regression. Ensure dashboard owners are informed before deployment.

---

## Next Steps

- Phase 03 (`phase-03-cost-taxonomy-promo-642-dedup.md`) reads `int_order_cogs_reconciled` + `std_order_items` to split promo lines; gate: this phase must be GREEN.
- Phase 05 (mart serving) will fully repoint `fact_order_economics` to use `int_order_cogs_reconciled` instead of the interim BUG-1 filter — removing the interim workaround cleanly.
- Phase 04 (overhead) also needs this phase GREEN: it uses `channel_net_profit` as an input to the contribution waterfall, which must be BUG-1-clean.

---

## Unresolved Questions

1. **4% MISA gap — mapping table or accept?** 8 MISA product codes not in Sapo SKUs. Accept gap (`cogs_source='misa'`) with flag, or build a manual mapping seed? Recommendation: accept for now, revisit if the 8 codes represent material COGS.
2. **MISA quantity vs Sapo quantity agreement** — when quantities differ on the same (order_code, sku), which drives unit-economics calculation? Not needed for this phase (COGS-amount based), but relevant for phase 06 detailView.
3. **Freshness lag**: MISA posts days after fulfillment. For recently shipped orders, `cogs_source='sapo_mac'` initially then gains MISA counterpart. Acceptable staleness for reconciliation variance reports?
4. **Intermediate schema.yml location** — does the `intermediate/cogs/` directory need its own `schema.yml`, or does it inherit from `intermediate/`? Check existing `intermediate/misa/` for pattern.
