# Phase 04 — Overhead Allocation (`int_order_overhead_allocation` + `fully_loaded_net_profit`)

## Context Links
- Master plan: `plans/260604-1030-unified-order-pl-cogs-overhead/plan.md`
- Overhead design spec (primary): `docs/architecture/order-pl/overhead-cost-allocation-design.md`
- COGS design (count-once rule): `docs/architecture/order-pl/cogs-reconciliation-design.md` §9
- P&L schema (extension points): `docs/architecture/order-pl/order-pl-schema-design.md` §5.1–5.2
- Phase 01 output (data sources): `phase-01-data-foundations-std-gate.md`
- Phase 03 output (count-once crux): `phase-03-cost-taxonomy-promo-642-dedup.md`

---

## Overview

**Priority:** P1 (blocked by phases 01 + 03)
**Status:** CORE DONE — P4-3 provisional (live-month uses actual data; budgeted-rate branch not exercised) | P4-5 VERIFIED 2026-06-09 (count-once separation clean; zero overlap)
**Scope:**
1. New dbt model `int_order_overhead_allocation` — closure-based allocation of TK642 (net-of-promo) + optional TK635/641-common pool(s) onto every completed order in the period.
2. Extend `fact_order_economics` with 4 new columns: `allocated_overhead`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`, `is_overhead_estimated`.
3. Add OVERHEAD rows to `fact_order_costs` (`cost_category='OVERHEAD'`, `fee_source='allocated'`).
4. dbt closure test: `SUM(allocated_overhead per period) == pool_period`.

**NOT in scope:** modifying `channel_net_profit` (tier-separation CONTRACT), building dashboards (phase 05), or detailView wiring (phase 06).

---

## Key Insights

### COUNT-ONCE Rule (cross-tier crux — MANDATORY)
Phase 03 establishes that MISA's sales ledger contains ~1.08B of **promo-goods 642** (gift/giveaway inventory issued to revenue=0 orders). This is already captured in `promo_goods_cost` (tier 2). The monthly overhead pool (tier 3) **MUST exclude this promo-642 portion** or the promo cost is counted twice.

Concretely: the overhead pool for any month = TK642 total from MISA overhead ledger **MINUS** the promo-goods-642 amount already in the sales ledger for that month. The promo-goods-642 lives in `std_misa_sales_lines` (via `cost_account_group='642'`); the cash G&A 642 lives in the new `overhead_costs_monthly` source ingested in phase 01 (separate MISA report). These are **different tables / different MISA reports** — if the ingestion is clean, the separation is natural. The risk is if any overlap exists between the two MISA report extracts.

**Verify explicitly:** after phase 01 ingests `overhead_costs_monthly`, confirm no rows in that table share voucher_no with the sales-ledger TK642 rows.

### Closure vs. Rate-Based Allocation
The overhead design mandates **closure-based** (proportional) allocation to guarantee `SUM(allocated_overhead) == pool_period`. A fixed-rate approach does NOT self-close and requires a "variance residual" line — explicitly rejected.

Formula per `(period_month × pool_id)`:
```
overhead_order = base_order / SUM(base_order for period) × pool_period_actual
```

### KISS v1: 1 Pool, Base = gross_profit
Start with one pool (all G&A overhead), base = `gross_profit` (channel_net_profit minus fees) as the capacity-to-bear measure. Config table (`overhead_allocation_config`) must support splitting pools later (admin/logistics/finance with different bases: qty, net_revenue, total_collected) **without** model changes — the config table is the extension point.

### `is_estimated` Flag (True-Up Pattern)
MISA closes books ~5–10 business days after month-end. During open months the pipeline uses `budgeted_rate` from `overhead_allocation_config` (gsheet) → `is_estimated = TRUE`. Once MISA export for that month lands in `overhead_costs_monthly`, rerun marks `is_estimated = FALSE` and actual pool is used → automatic true-up.

### Residual (Rounding) Handling
After proportional allocation, `SUM(allocated_overhead)` may differ from `pool_period` by rounding delta. Assign residual to the order with the largest base in that period.

### Orders In Scope for Overhead Base
Base population = orders with `status = 'completed'` only. Cancelled/returned orders do NOT bear overhead. This is a design decision (see open Q5 below).

---

## Requirements

### Functional
- R1: `int_order_overhead_allocation` emits one row per `(order_id, pool_id, period_month)`.
- R2: Closure: `SUM(allocated_overhead) = pool_period_actual` per `(period_month, pool_id)` — verified by dbt test.
- R3: `is_estimated = TRUE` while MISA not yet closed for period; auto-flips to FALSE after ingestion.
- R4: COUNT-ONCE: pool excludes sales-ledger promo-642 (phase 03 output). Documented assertion in model, not just comment.
- R5: `fact_order_economics` gains `allocated_overhead`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`, `is_overhead_estimated` — `channel_net_profit` UNCHANGED.
- R6: `fact_order_costs` gains rows with `cost_category='OVERHEAD'`, `cost_type ∈ {overhead_admin, overhead_logistics, overhead_finance}`, `fee_source='allocated'`.
- R7: Config table `overhead_allocation_config` must be version-aware (effective_from date) so historical reports are reproducible.
- R8: Allocation only for orders in months where a pool exists. Orders in months with no overhead data → `allocated_overhead = NULL`, `is_overhead_estimated = NULL`.

### Non-Functional
- Residual row assigned to max-base order in period — no free-floating "adjustment" rows in `fact_order_costs`.
- dbt model < 200 lines; split into CTE blocks by logical phase (pool aggregation → base aggregation → proportion → allocation → residual fix).
- All new columns documented in `schema.yml`.

---

## Architecture

### Data Flow

```
overhead_costs_monthly      (phase 01, MISA source — cash G&A only)
    │
    ├── [pool_period_actual per (period_month, pool_id)]
    │
overhead_allocation_config  (phase 01, gsheet — rules + budgeted rates + pool→base mapping)
    │
    ├── [pool_id, base_column, effective_from, budgeted_rate]
    │
    └──► int_order_overhead_allocation ◄── fact_orders (completed, base amounts)
                │                      ◄── int_order_cogs_reconciled (gross_profit base)
                │
                ├──► OVERHEAD rows → fact_order_costs  (long-format, amount +)
                └──► allocated_overhead JOIN → fact_order_economics (new columns)
```

### Model Grain
`int_order_overhead_allocation`: one row per `(order_id, pool_id, period_month)`.
- `period_month` = `DATE_TRUNC('month', order_date_ict)` — ICT date consistent with `fact_orders.date_key`.
- Aggregated by pool before joining `fact_order_economics`/`fact_order_costs` (phase 05 handles the JOIN).

### New Columns in `fact_order_economics`
| Column | Type | Formula |
|--------|------|---------|
| `allocated_overhead` | DECIMAL(18,2) | SUM over pool rows from `int_order_overhead_allocation` |
| `fully_loaded_net_profit` | DECIMAL(18,2) | `channel_net_profit − allocated_overhead` |
| `fully_loaded_margin_pct` | DOUBLE | `fully_loaded_net_profit / NULLIF(net_revenue, 0)` |
| `is_overhead_estimated` | BOOLEAN | TRUE if any pool for the period is budgeted |

### New Rows in `fact_order_costs`
| Column | Value |
|--------|-------|
| `cost_type` | `overhead_admin` / `overhead_logistics` / `overhead_finance` |
| `cost_category` | `OVERHEAD` |
| `amount` | positive allocated amount |
| `source_system` | `misa` (actual) or `gsheet` (estimated) |
| `fee_source` | `allocated` |
| `is_estimated` | mirrors `is_overhead_estimated` |

### Config Table Schema (`overhead_allocation_config`)
```
pool_id          VARCHAR    -- e.g., 'admin', 'logistics', 'finance'
base_column      VARCHAR    -- column name to use as base (e.g., 'gross_profit', 'net_revenue', 'quantity')
weight_pct       DECIMAL    -- optional channel weighting (future use; default 1.0)
effective_from   DATE       -- for version control
budgeted_rate    DECIMAL    -- monthly rate used while MISA not closed
cost_type        VARCHAR    -- maps to fact_order_costs cost_type
account_codes    VARCHAR[]  -- TK codes included in this pool (e.g., ['642', '635'])
```

---

## Related Code Files

### Create (new)
- `transformation/models/intermediate/finance/int_order_overhead_allocation.sql`
- `transformation/models/intermediate/finance/schema.yml` (document new model + columns)

### Modify (extend — COORDINATION REQUIRED)
- `transformation/models/marts/sales/fact_order_economics.sql` — add 4 columns JOIN
- `transformation/models/marts/sales/fact_order_costs.sql` — add OVERHEAD CTE + UNION ALL

> **CONCURRENCY FLAG:** `fact_order_economics.sql` and `fact_order_costs.sql` are actively edited by a concurrent detailView work-stream. **Confirm the concurrent stream has merged before touching these files.** Phase 05 owns the actual edits; phase 04 defines what to add. Do NOT edit these two files in this phase — the changes are designed here, written in phase 05.

---

## Implementation Steps

### Pre-Requisites (verify before starting)
1. Phases 01 + 03 complete and Dagster-green.
2. `overhead_costs_monthly` table exists in DuckDB with rows for at least 1 month.
3. `overhead_allocation_config` table exists with at least 1 pool row.
4. Resolve open questions (below) before coding: especially pool scope (Q2) and base choice (Q3).

### Step 1 — Verify COUNT-ONCE Separation (Data Assertion)
```bash
# Inside data_platform container
docker exec data_platform dbt run-operation execute_sql \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --args '{"sql": "SELECT period_month, SUM(amount) as promo_642 FROM overhead_costs_monthly WHERE account_code LIKE '"'"'642%'"'"' GROUP BY 1 ORDER BY 1"}'
```
Must return 0 rows, OR the amounts must be confirmed as pure cash-G&A 642 (not the promo-goods 642 from the sales ledger). If overlap found, add explicit exclusion logic in step 2.

### Step 2 — Create `int_order_overhead_allocation`
Location: `transformation/models/intermediate/finance/int_order_overhead_allocation.sql`

CTE structure (implement in order):
```
1. pool_config        — from overhead_allocation_config; pick effective config per period
2. pool_actuals       — from overhead_costs_monthly; actual pool for closed months
3. pool_estimates     — from overhead_allocation_config.budgeted_rate for open months
4. pool_resolved      — COALESCE(actual, estimate); emit is_estimated flag
5. order_base         — from fact_orders (completed only) + int_order_cogs_reconciled; 
                        compute base value (gross_profit or net_revenue) per order
6. period_base_totals — SUM(base) per (period_month, pool_id)
7. proportions        — order_base / period_base_totals
8. allocated          — proportions × pool_period_actual → raw allocated_overhead per order
9. residual_fix       — identify max-base order per period; adjust to close rounding gap
10. final             — emit order_id, pool_id, period_month, allocated_overhead, is_estimated
```

### Step 3 — Document in `schema.yml`
Add model + column-level descriptions to `transformation/models/intermediate/finance/schema.yml`.

### Step 4 — Write Closure dbt Test
In `schema.yml` for `int_order_overhead_allocation`, add a custom generic test:
```yaml
- name: overhead_closure_by_period
  description: >
    SUM(allocated_overhead) per (period_month, pool_id) must equal pool_period_actual.
    Residual rounding tolerance: abs(delta) < 1 VND.
```
Implement as a dbt test SQL in `tests/` directory:
```sql
-- tests/assert_overhead_closure.sql
SELECT period_month, pool_id, 
  SUM(allocated_overhead) AS total_allocated,
  MAX(pool_period_actual) AS pool_actual,
  ABS(SUM(allocated_overhead) - MAX(pool_period_actual)) AS residual
FROM {{ ref('int_order_overhead_allocation') }}
GROUP BY period_month, pool_id
HAVING ABS(SUM(allocated_overhead) - MAX(pool_period_actual)) > 1  -- tolerance: 1 VND
```

### Step 5 — Run dbt Compile + Test (Model Only)
```bash
docker exec data_platform dbt compile \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --select int_order_overhead_allocation

docker exec data_platform dbt test \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --select int_order_overhead_allocation
```
Fix any SQL errors before proceeding.

### Step 6 — Verify via Dagster Run
Launch `transform_batch_nightly_job` (or a focused run selecting `int_order_overhead_allocation` and its parents) via Dagster UI. Confirm SUCCESS. Check logs for row counts.

### Step 7 — Spot-Check Closure
```bash
docker exec data_platform dbt run-operation execute_sql \
  --project-dir /app/transformation --profiles-dir /app/transformation \
  --args '{"sql": "SELECT period_month, pool_id, SUM(allocated_overhead) AS allocated, MAX(pool_period_actual) AS pool, ABS(SUM(allocated_overhead)-MAX(pool_period_actual)) AS residual FROM int_order_overhead_allocation GROUP BY 1,2 ORDER BY 1,2"}'
```
All `residual` values must be ≤ 1.

---

## Todo

- [x] Resolve open questions (Q1–Q5) with stakeholder before coding
- [x] Verify phase 01 + 03 complete and Dagster-green
- [x] Confirm concurrent detailView stream has merged (or coordinate timing)
- [x] Run data assertion: confirm no overlap between `overhead_costs_monthly` 642 and sales-ledger 642
- [x] Create `int_order_overhead_allocation.sql` with 10-CTE structure
- [x] Write `schema.yml` entries for new model
- [x] Write closure dbt test `tests/assert_overhead_closure.sql`
- [x] `dbt compile` passes
- [x] `dbt test --select int_order_overhead_allocation` passes (closure test green)
- [x] Dagster run SUCCESS (int_order_overhead_allocation builds)
- [x] Spot-check closure: all residuals ≤ 1 VND
- [x] Hand off column specs to phase 05 (fact_order_economics/costs edits)
- [ ] P4-3: exercise budgeted-rate provisional branch (live-month uses actual data currently; test with simulated open month)
- [x] P4-5: reconcile 64214 sub-account vs sales-ledger-642 to confirm count-once exclusion is tight — VERIFIED 2026-06-09: zero voucher_no overlap across all 642x accounts (1,817 sales-ledger vs 1,894 account-ledger; intersection=0); 64214 classified `drop_promo_count_once` in live gsheet, confirmed excluded from all pools

---

## Success Criteria

1. **Dagster-green:** `transform_batch_nightly_job` succeeds with `int_order_overhead_allocation` in the asset graph.
2. **Closure test passes:** `assert_overhead_closure` dbt test green — `|SUM(allocated) − pool| ≤ 1` for all periods.
3. **Count-once verified:** data assertion confirms no sales-ledger promo-642 in `overhead_costs_monthly`.
4. **is_estimated flag correct:** open month rows have `is_estimated=TRUE`; closed months `FALSE`.
5. **Channel_net_profit unchanged:** existing `fact_order_economics.channel_net_profit` values byte-identical before/after (verify with checksum before phase 05 modifies the file).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| MISA overhead report not yet ingested (phase 01 incomplete) | Medium | High — blocks entirely | Hard dependency: do not start phase 04 until phase 01 Dagster-green |
| Promo-642 overlap between two MISA report extracts | Low | High — double-count, violates CONTRACT | Data assertion in step 1; add exclusion filter if found |
| Base = gross_profit can be negative (e.g., high-COGS orders) | Medium | Medium — negative denominators or perverse allocation | Clip base to 0 for proportion calc; negative-base orders get 0 overhead in v1 |
| Residual rounding accumulated across 10k+ orders/month | Low | Low | Residual fix (step 9 CTE) and 1 VND tolerance test |
| concurrent stream edits fact_order_economics.sql simultaneously | Medium | High — merge conflict | File ownership protocol: phase 05 owns the fact_ edits; phase 04 produces int_ only |
| MISA API unavailable → no true-up data | Medium | Medium — `is_estimated` stays TRUE, reports show budgeted figures | Accept for v1; flag visually in dashboards |
| Orders with gross_profit = 0 (base = 0) — zero-revenue orders | Low | Low — they correctly receive 0 overhead allocation | Document in model; these are promo/gift orders already in promo_goods_cost |

---

## Security / Data Integrity

- `overhead_allocation_config` gsheet must have version history (effective_from); never overwrite old rows — append only. Rationale: auditors need to reproduce prior-period reports.
- `overhead_costs_monthly` is an ingested source; do not allow manual edits to raw table — only via pipeline re-ingest.
- `is_estimated` flag must surface in all downstream reports so stakeholders know when numbers are preliminary.

---

## Next Steps

This phase hands off to:
- **Phase 05** (`phase-05-pl-marts-serving.md`): writes the actual SQL changes to `fact_order_economics` + `fact_order_costs`, creates serving views, builds Metabase P&L dashboard.
- **Phase 06** (`phase-06-detailview-pl.md`): reads overhead allocation via serving views for the per-order P&L panel.

---

## Unresolved Questions (must resolve before coding)

1. **Q1 — MISA overhead source:** Is the overhead MISA report available via AMIS API or only manual Excel export (`Sổ chi tiết TK642`)? How many days after month-end does it close? (Determines true-up lag.)
2. **Q2 — Pool scope:** Is v1 pool TK642 only, or include TK635 (lãi vay, phí NH) and TK641-common (non-traceable portion)? Each added TK requires its own account filter in `overhead_costs_monthly`.
3. **Q3 — Base choice:** Confirm: `gross_profit` or `net_revenue`? `gross_profit` is more fair (capacity-to-bear); `net_revenue` is simpler and avoids negative-base edge cases. Pick one and document.
4. **Q4 — Realtime budgeted rate:** Does the business need overhead visible for the current open month (requiring budgeted rate from gsheet), or is "closed months only" acceptable for v1? (Doubles complexity if realtime needed.)
5. **Q5 — Cancelled/returned order overhead:** Do orders with `status='cancelled'` or orders with returns bear overhead? Recommendation: completed-only. Confirm.
