---
title: "Phase 01 — Data Foundations & Std-Gate (MISA + Overhead Ingestion)"
description: "Add std_misa_sales_lines to close the std-gate; design overhead_costs_monthly ingest + overhead_allocation_config gsheet seed"
status: DONE
priority: P1
effort: 1d
tags: [std-layer, misa, ingestion, gsheet, overhead]
created: 2026-06-04
---

## Context Links

- Master plan: `plans/260604-1030-unified-order-pl-cogs-overhead/plan.md` — CONTRACT governs all decisions
- Design: `docs/architecture/order-pl/cogs-reconciliation-design.md` §5 (std-gate rationale, faithful pass-through rules)
- Design: `docs/architecture/order-pl/overhead-cost-allocation-design.md` §4 (overhead data sources: MISA vs GSheet)
- Existing staging: `transformation/models/staging/stg_misa_sales_lines.sql` (to be passed through faithfully)
- Existing int: `transformation/models/intermediate/misa/int_misa_sales_lines.sql` (to be repointed)
- Golden std for pattern: `transformation/models/staging/standard/std_inventory_movements.sql`
- Schema yml reference: `transformation/models/staging/standard/schema.yml`
- GSheet ingestion pattern: `ingestion/src/gsheet_marketing_spend.py`, `orchestration/assets/sheets_assets.py`

---

## Overview

**Priority:** P1 — blocks all other phases (02, 03, 04)
**Status:** DONE
**Scope:** Three deliverables in one phase:

1. `std_misa_sales_lines` — new std_ model, faithful pass-through of `stg_misa_sales_lines` + `cost_account_group` derived column + `source_system`/`source_version` provenance. Closes the std-gate gap (MISA is the **only** source currently skipping std_).
2. Repoint `int_misa_sales_lines` — change its source from `stg_misa_sales_lines` to `std_misa_sales_lines`. One-line ref change only; zero functional change to columns.
3. `overhead_costs_monthly` ingestion design + `overhead_allocation_config` gsheet seed — schema + ingestion path scoped; implementation is pre-work for phase 04. **No dbt models built in this phase.**

---

## Key Insights

- MISA is ingested from `So_chi_tiet_ban_hang_*.xlsx` → `src_misa_sales_lines` → `stg_misa_sales_lines`. `stg_` does all casts and enrichment. `int_misa_sales_lines` currently reads `stg_` directly (violates R1: all fact inputs must flow through `std_`). Verified: zero rows without `product_code` → sales ledger = goods-only (cogs-reconciliation-design §1b).
- `cogs_account` in the existing stg model takes values `632`, `632.1`, `632.3`, `642`, `642.14` (verified in design §1a). The `cost_account_group` derivation (`'632'` / `'642'` / `'other'`) is the critical discriminator for all downstream COGS vs promo-cost splits.
- `std_misa_sales_lines` is report-specific (NOT `std_misa`) — MISA is multi-report; future cash-overhead ledgers (`Sổ chi tiết TK642/641`) will get their own `std_misa_<report>` models. Do not create a monolithic `std_misa`.
- `overhead_costs_monthly` does NOT exist yet in any ingested source. The only "642" currently in the pipeline is promo-goods cost from the sales ledger — it is NOT cash G&A overhead (cogs-reconciliation-design §1b, §9).
- GSheet `overhead_allocation_config` mirrors the existing `gsheet_marketing_spend.py` / `gsheet_targets.py` pattern: CSV export from Google Sheet URL → parquet to data lake → `src_` → `stg_` → seed/source in dbt.

---

## Requirements

### Functional

- `std_misa_sales_lines`:
  - All columns from `stg_misa_sales_lines` preserved verbatim (no re-casting, no dropping)
  - ADD: `cost_account_group VARCHAR` → `'632'` when `cogs_account LIKE '632%'`, `'642'` when `LIKE '642%'`, else `'other'`
  - ADD: `source_system VARCHAR` = `'misa'` (literal)
  - ADD: `source_version VARCHAR` = `'sales_lines_v1'` (report-version tag; bump when parser changes)
  - Materialized as `VIEW` (same as all other std_ models — no parquet storage at std layer)
  - Tag `['standard', 'misa']`
  - PK: `misa_sales_line_sk` inherited from stg (via int surrogate — std does NOT recompute SK; leave sk derivation in int)
  - Business grain: `(voucher_no, line_no)` — identical to stg/int

- `int_misa_sales_lines` repoint:
  - Change `FROM {{ ref('stg_misa_sales_lines') }}` → `FROM {{ ref('std_misa_sales_lines') }}`
  - No column changes. Int still computes `is_service_line`, `misa_sales_line_sk`, enrichments.
  - Note: `cost_account_group` added to std will now be passable downstream; int may re-expose it or leave to int_order_cogs_reconciled to read from std directly.

- `overhead_costs_monthly` ingestion design (DESIGN ONLY this phase, no implementation):
  - Schema: `period_month DATE` (first of month), `account VARCHAR` (TK642/635/641-common), `amount BIGINT` (VND net of VAT), `source VARCHAR` (`'misa_amis'` or `'misa_export'`), `ingested_at TIMESTAMPTZ`
  - Source: MISA AMIS API (preferred if API accessible) OR manual export of Sổ cái TK642/635/641 → CSV/XLSX → ingest script (same pattern as `gsheet_marketing_spend.py`)
  - Partition: `year=YYYY/month=M` (matches data-lake partition convention)
  - **Open Q:** MISA AMIS API availability TBD (see Unresolved Q1 below). If no API, manual export cadence must be defined.

- `overhead_allocation_config` gsheet seed design (DESIGN ONLY this phase):
  - Schema: `pool_id VARCHAR`, `pool_name VARCHAR`, `account_pattern VARCHAR` (e.g. `'642%'`), `base_metric VARCHAR` (`'net_revenue'`|`'gross_profit'`|`'order_count'`), `channel_weight DECIMAL`, `budgeted_rate DECIMAL`, `effective_from DATE`, `effective_to DATE`, `version INTEGER`
  - Follows `gsheet_marketing_spend.py` pattern: CSV export URL → `SOURCES__SPREADSHEET_URL__OVERHEAD_CONFIG` env var → parquet → `src_overhead_allocation_config`
  - Must have `version`/`effective_from`/`effective_to` for config history (overhead-design §2.10)

### Non-Functional

- `std_misa_sales_lines` must be a VIEW (zero storage cost; stg already materialized)
- No breaking change to `int_misa_sales_lines` column list — downstream `fact_order_economics` / `fact_order_costs` must not be affected by the repoint
- DuckDB single-writer: pause/don't overlap Dagster scheduled runs during dbt build

---

## Architecture

### Data Flow

```
src_misa_sales_lines  (raw parquet, partitioned)
  └─► stg_misa_sales_lines  (VIEW — casts, channel enrichment, margin derivation)
        └─► std_misa_sales_lines  (VIEW — faithful + cost_account_group + provenance)  [NEW]
              └─► int_misa_sales_lines  (VIEW — enrichment, surrogate key)             [REPOINTED]
                    └─► fact_order_economics / fact_order_costs                        [unchanged this phase]
```

### `std_misa_sales_lines` Columns

| Column | Source | Note |
|--------|--------|------|
| `voucher_no` | stg | business key |
| `line_no` | stg | business key |
| `posting_date` | stg | DATE |
| `voucher_date` | stg | DATE |
| `invoice_date` | stg | DATE |
| `invoice_no` | stg | |
| `product_code` | stg | |
| `product_name` | stg | |
| `product_name_on_document` | stg | |
| `unit_of_measure` | stg | |
| `is_promo_line` | stg | BOOLEAN |
| `customer_code` | stg | |
| `customer_name` | stg | |
| `quantity` | stg | BIGINT |
| `unit_price` | stg | DECIMAL(18,4) |
| `revenue_gross` | stg | BIGINT |
| `discount_amount` | stg | BIGINT |
| `total_payment` | stg | BIGINT |
| `cogs_amount` | stg | BIGINT — KEEP verbatim (mixed 632+642) |
| `revenue_net_of_discount` | stg | derived |
| `gross_profit` | stg | derived (NOT filtered) |
| `gross_margin_pct` | stg | derived |
| `debit_account` | stg | KEEP — needed for audit |
| `credit_account` | stg | KEEP |
| `discount_account` | stg | KEEP |
| `cogs_account` | stg | KEEP — primary discriminator |
| `channel_code` | stg | |
| `channel_name` | stg | enriched |
| `channel_group` | stg | |
| `voucher_source_hint` | stg | heuristic |
| `salesperson_name` | stg | |
| `description` | stg | |
| `source_file` | stg | lineage |
| `ingested_at` | stg | |
| **`cost_account_group`** | **derived** | `CASE WHEN cogs_account LIKE '632%' THEN '632' WHEN cogs_account LIKE '642%' THEN '642' ELSE 'other' END` |
| **`source_system`** | **literal** | `'misa'` |
| **`source_version`** | **literal** | `'sales_lines_v1'` |

### Grain

- `std_misa_sales_lines`: `(voucher_no, line_no)` — 1 row per invoice line
- No dedup needed (stg reads src which is already deduped at ingestion)

### No surrogate key at std

`misa_sales_line_sk` is generated in `int_misa_sales_lines` via `dbt_utils.generate_surrogate_key`. Do NOT duplicate it in std_ (std is faithful; int is where enrichment/keys go).

---

## Related Code Files

### To Create
- `transformation/models/staging/standard/std_misa_sales_lines.sql`

### To Modify
- `transformation/models/intermediate/misa/int_misa_sales_lines.sql` — change one ref: `stg_misa_sales_lines` → `std_misa_sales_lines`
- `transformation/models/staging/standard/schema.yml` — add `std_misa_sales_lines` model entry with column docs + `cost_account_group` description

### To Design (not implement yet)
- `ingestion/src/gsheet_overhead_allocation_config.py` — NEW (implement in phase 04 pre-work)
- `orchestration/assets/sheets_assets.py` — will need `sheets_overhead_config_asset` added (phase 04)
- `ingestion/src/misa_overhead_costs_monthly.py` — NEW (MISA export/API ingest; implement in phase 04 pre-work)

### DO NOT TOUCH (concurrent stream owns)
- `transformation/models/marts/sales/fact_order_economics.sql`
- `transformation/models/marts/sales/fact_order_costs.sql`

---

## Implementation Steps

1. **Pause Dagster schedules** — DuckDB single-writer; ensure no scheduled run collides with dbt build during development.

2. **Create `std_misa_sales_lines.sql`**
   - File: `transformation/models/staging/standard/std_misa_sales_lines.sql`
   - Config block: `materialized='view'`, `tags=['standard', 'misa']`
   - Header comment: source, grain, PK, key semantics (same pattern as `std_inventory_movements.sql`)
   - Body: `SELECT * FROM {{ ref('stg_misa_sales_lines') }}` plus the three new columns (`cost_account_group`, `source_system`, `source_version`)
   - Use `SELECT <all_stg_cols_explicitly_listed>, CASE... AS cost_account_group, 'misa' AS source_system, 'sales_lines_v1' AS source_version FROM {{ ref('stg_misa_sales_lines') }}`
   - (Explicit column list preferred over SELECT * for clarity and schema-yml alignment)

3. **Update `schema.yml`** — add `std_misa_sales_lines` block under `models:`. Include:
   - `description` one-liner
   - `cogs_account` column note: "Raw account code from MISA; values include 632, 632.1, 632.3, 642, 642.14 — NOT filtered here"
   - `cost_account_group` column description: "Derived bucket: '632'=COGS goods sold, '642'=promo/giveaway goods cost, 'other'"
   - `source_version` description: "Parser report version tag; bump when MISA report format changes"
   - `source_system` description: "'misa' literal — identifies source for cross-source joins"

4. **Repoint `int_misa_sales_lines.sql`** — change line `FROM {{ ref('stg_misa_sales_lines') }}` to `FROM {{ ref('std_misa_sales_lines') }}`. No other change.

5. **Compile check**:
   ```bash
   docker exec data_platform dbt compile \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select std_misa_sales_lines int_misa_sales_lines
   ```

6. **Run dbt build**:
   ```bash
   docker exec data_platform dbt build \
     --project-dir /app/transformation \
     --profiles-dir /app/transformation \
     --select std_misa_sales_lines int_misa_sales_lines fact_order_economics fact_order_costs
   ```
   - Expect: all pass with no column errors (int column list unchanged)

7. **Dagster verification** — manually launch the `dbt_transformation` job (or whichever job materializes the MISA → fact chain). Confirm SUCCESS.

8. **Smoke-check query** (run in DuckDB or via Dagster asset materialization logs):
   ```sql
   SELECT cost_account_group, COUNT(*), SUM(cogs_amount)
   FROM std_misa_sales_lines
   GROUP BY 1;
   -- Expected: '632' ~9,248 rows ~21.5B, '642' ~2,189 rows ~1.08B
   ```

9. **Document overhead design** — write a brief note in `docs/architecture/order-pl/overhead-cost-allocation-design.md` §"Câu hỏi còn mở" with the schema decisions made here (period_month, account, amount columns). Do NOT modify design doc otherwise.

---

## Todo

- [x] Pause Dagster schedules before dev build
- [x] Create `std_misa_sales_lines.sql`
- [x] Update `schema.yml` with model + column docs
- [x] Repoint `int_misa_sales_lines.sql` (one ref change)
- [x] `dbt compile` check — no errors
- [x] `dbt build` — std + int + fact chain green
- [x] Dagster manual run → SUCCESS
- [x] Smoke-check: cost_account_group distribution matches design §1a (~95%/632, ~4.8%/642)
- [x] Document overhead schema decisions in design doc
- [x] Resume Dagster schedules

---

## Success Criteria

| Check | Pass condition |
|-------|---------------|
| `std_misa_sales_lines` exists as VIEW | `dbt ls --select std_misa_sales_lines` returns 1 result |
| Grain preserved | Row count matches `stg_misa_sales_lines` (should be identical) |
| cost_account_group coverage | 100% non-null; distribution: '632' ~95%, '642' ~4.8% |
| int repoint transparent | `fact_order_economics`/`fact_order_costs` row counts unchanged vs pre-change |
| Dagster run GREEN | Manual launch → all assets in MISA chain = SUCCESS |
| No double-count risk introduced | `fact_order_economics.cogs_amount` unchanged (BUG-1 fix deferred to phase 02) |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Column name mismatch stg→std (explicit list vs stg evolution) | Low | Medium | Use explicit column list; CI catches it |
| stg `gross_profit` already mixes 632+642 — exposing downstream | Low | Low | std is faithful; int/downstream are the filter layer; documented in schema.yml |
| Concurrent stream touches `int_misa_sales_lines` simultaneously | Low | High | Confirm with concurrent stream before committing; serialize commits |
| `overhead_costs_monthly` MISA API unavailable | Medium | Low (this phase only) | This phase is design-only; implementation deferred to phase 04 |
| DuckDB lock from concurrent Dagster run | Medium | Medium | Pause schedules during `dbt build` (single-writer rule) |

---

## Security / Data Integrity

- `cogs_amount` in std is NOT filtered — it retains the mixed 632+642 total. This is intentional (faithful std). Downstream int/fact layers apply the filter. Document clearly in schema.yml to prevent accidental use.
- MISA overhead data (when ingested) may contain total P&L-sensitive amounts — do not expose raw rows in public Metabase views.

---

## Next Steps

- Phase 02 (`phase-02-cogs-reconciliation.md`) reads `std_misa_sales_lines` directly; gate: this phase must be fully green (Dagster SUCCESS) before phase 02 starts.
- Phase 04 (overhead allocation) needs `overhead_costs_monthly` + `overhead_allocation_config` — implement the ingestion scripts (designed here) as phase 04 pre-work.

---

## Unresolved Questions

1. **MISA AMIS API**: Is there an accessible MISA AMIS API for TK642/635/641 monthly balances, or must we use manual export? Determines ingestion complexity for `overhead_costs_monthly`.
2. **`stg_misa_sales_lines` future evolution**: If the stg parser adds columns, does std_ need to be updated manually? → Confirm explicit column list policy or use `SELECT *, <new_cols>` pattern consistently across std models.
3. **`source_version` tag value**: `'sales_lines_v1'` — should this track the MISA report format version or the pipeline ingestion schema version? Align with std-layer conventions.
