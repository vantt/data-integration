# Phase 01 — dbt Model Contracts

## Context Links

- Plan overview: `plans/260624-1952-warehouse-app-boundary-hardening/plan.md`
- Research grounding: `plans/reports/from-research-to-planner-boundary-hardening-findings-260624-1952-report.md`
- dbt project config: `transformation/dbt_project.yml:69-76`
- Mart schema: `transformation/models/marts/schema.yml`
- CRM column lists: `crm/sync/duckdb_reader.py:39-148`
- dbt rules: `transformation/AGENTS.md`

---

## Overview

| | |
|---|---|
| **Priority** | P1 — Tier 1 foundation; phase-02 depends on this |
| **Status** | Pending |
| **Effort** | ~3h (spike 1h + schema edits 1.5h + on_schema_change 0.5h) |

Harden the dbt→parquet write boundary: pin package versions (currently floating), add schema.yml entries + `data_type` for all 6 consumer-facing marts, override `on_schema_change: sync_all_columns` on contracted models, and enable `contract: {enforced: true}`. A spike first determines whether dbt-duckdb 1.10.x enforces contracts on `materialized: external` (parquet) — if not, fall back to a dbt generic/singular schema-assertion test.

Value: contract violations surface as a failed Dagster asset (`sapo_dbt_assets`) before bad parquet ships, triggering the existing `run_failure_sensor` → Lark. The serving-view layer (`bootstrap_serving_views.py:53-77`) is `SELECT *` and remains unchanged (YAGNI — CRM already guards column presence in `duckdb_reader.py`).

---

## Key Insights

1. **Versions floating** — `ingestion/requirements.txt:10` has bare `dbt-duckdb`; actual runtime is dbt-core 1.11.8 / dbt-duckdb 1.10.1 (contracts since 1.5). Pin first or a minor bump could silently change enforcement semantics.
2. **Spike is non-negotiable** — dbt-duckdb `materialized: external` outputs parquet via COPY, not a CREATE TABLE; it's unclear whether the contract type-check hook fires. We empirically verify with one model before committing to all six.
3. **Two missing schema entries** — `mart_customer_tier` and `mart_customer_action_queue` have NO entry in `schema.yml`. Their column shapes are known from the SQL SELECT lists (`mart_customer_tier.sql:60-88`, `mart_customer_action_queue.sql:76-139`) and from `duckdb_reader.py:88-121` (CRM's pinned consumer names — which differ slightly from the SQL column names for action_queue via aliasing).
4. **`on_schema_change: sync_all_columns`** at `dbt_project.yml:75` silently absorbs adds/drops — semantically opposed to contract enforcement. Must override to `fail` (or `append_new_columns` if strict fail proves too disruptive) on contracted models.
5. **CRM column aliases** — `duckdb_reader.py:114-121` expects `rationale_vi`, `value_at_stake_vnd`, `priority`, `generated_date` but `mart_customer_action_queue.sql` outputs `action_rationale`, `value_at_stake`, `priority_rank`, `queue_generated_at`. These are aliased somewhere in the query. The schema.yml `data_type` declarations must match the SQL's actual output names (not the CRM alias names); contract enforces at parquet write time before aliasing.
6. **`mart_hug_optin` is `materialized: table`** (`:1-4` of its SQL) — NOT external/parquet. Standard table materialization → contract enforcement is unambiguous (no spike needed for this one). However, it is NOT in `dbt_project.yml` marts config (it overrides to `table`), so the `on_schema_change` override in dbt_project.yml won't apply; set it directly in the model config.
7. **Action-queue column name gap** — dbt_project.yml marks all marts `materialized: external`, but `mart_hug_optin.sql` overrides to `table` without `location`. The serving bootstrap script checks for parquet files by folder. This is an existing oddity, not in scope to change.

---

## Requirements

### Functional

1. Pin `dbt-duckdb` and `dbt-core` in `ingestion/requirements.txt` to exact installed versions (1.11.8 / 1.10.1).
2. Run the contract spike: add `contract: {enforced: true}` to one mart, rename a col in the SQL, run `dbt build`, observe pass/fail.
3. **Branch A (spike passes):** Add `data_type` to all columns of the 6 marts + `contract: {enforced: true}` to each.
4. **Branch B (spike fails):** Add a dbt singular or generic test asserting expected column names and types exist; document the gap clearly.
5. Add complete `schema.yml` entries for `mart_customer_tier` and `mart_customer_action_queue`.
6. Override `on_schema_change` to `fail` (or document why `append_new_columns`) on each contracted model via dbt_project.yml config block or individual model config.
7. Verify the full `dbt build --select tag:mart` passes cleanly with contracts enabled.
8. Verify a deliberate contract violation (rename one column) produces a Dagster asset failure (not merely a dbt WARNING).

### Non-functional

- No change to serving-view layer (`bootstrap_serving_views.py`, `refresh_rolling.py`).
- No new Python dependencies.
- `dbt build` wall-clock does not increase by > 20% (contracts add per-model validation, not heavy re-computation).
- All changes confined to `transformation/` and `ingestion/requirements.txt`. No changes to `crm/` or `orchestration/`.

---

## Architecture

### Data Flow

```
dbt build (Dagster: sapo_dbt_assets)
    └─► for each contracted mart:
            1. Run SQL → produces parquet
            2. Contract check: compare output schema vs declared columns+types in schema.yml
                ├─ Match  → proceed, parquet written
                └─ Mismatch → DbtRuntimeError → Dagster asset FAILED
                                  └─► run_failure_sensor → Lark alert
```

### Decision Gate: Spike Result

```
spike: dbt build mart_customer_tier with contract:enforced + intentional col rename
    ├─ dbt build FAILS (error referencing contract violation)
    │       → Branch A: add contracts to all 6 marts
    └─ dbt build SUCCEEDS (contract silently ignored for external)
            → Branch B: write schema-assertion singular test
                         document gap + revisit on next dbt-duckdb release
```

### 6 Consumer Marts

| Mart | Materialization | Schema entry today | data_type today |
|---|---|---|---|
| `dim_customers` | external/parquet | Yes (`:159`) | 8 seg cols typed; 10+ untyped |
| `fact_orders` | external/parquet | Yes (`:572`) | FK cols partly typed; revenue cols untyped |
| `mart_customer_tier` | external/parquet | **MISSING** | n/a |
| `mart_customer_action_queue` | external/parquet | **MISSING** | n/a |
| `mart_product_health` | external/parquet | Yes (`:1272`) | NONE |
| `mart_hug_optin` | **table** (override) | Yes (`:5`) | NONE |

### Serving-View Consumer Gap (Open Question 2)

Serving views (`bootstrap_serving_views.py:53-77`) use `SELECT * EXCLUDE(filename)` — no column gating. The contract added here guards at write time (parquet), not at read time (serving views). This is intentional and sufficient for Tier 1:

- CRM already fails-loud via `_check_columns()` / `MissingColumnError` (`duckdb_reader.py:194-209`).
- Evidence/Rill/Metabase/DetailView are all BI tools reading parquet; they'll error visibly when columns disappear.
- Explicit column lists in serving views = YAGNI — adds drift risk for no incremental safety gain.

Decision: **do NOT add explicit column lists to serving views in this phase.** Rationale preserved here so it doesn't need to be relitigated.

---

## Related Code Files

### Modify

- `ingestion/requirements.txt` — pin dbt-duckdb and dbt-core
- `transformation/dbt_project.yml` — add per-mart `on_schema_change: fail` block for contracted models (or use config per model)
- `transformation/models/marts/schema.yml` — add `data_type` to untyped columns of the 6 marts; add entries for 2 missing marts

### Create (only if spike → Branch A)

- No new files needed; `contract: {enforced: true}` is YAML inside `schema.yml`

### Create (only if spike → Branch B)

- `transformation/tests/assert_consumer_mart_columns.sql` — singular test asserting expected columns exist on each of the 6 marts

### Do NOT touch

- `transformation/exposures.yml` (auto-generated, Metabase-only)
- `crm/sync/duckdb_reader.py` (CRM contract already in place)
- `bootstrap_serving_views.py`, `refresh_rolling.py`
- Any orchestration file

---

## Implementation Steps

### Step 1 — Pin versions

1. Open `ingestion/requirements.txt`.
2. Replace bare `dbt-duckdb` with `dbt-duckdb==1.10.1` and add `dbt-core==1.11.8` if not already present.
3. Verify: `pip show dbt-duckdb dbt-core` in container confirms these are the actual installed versions. If the container version differs, pin to the actual version, not the assumed one.

### Step 2 — Spike: contract enforcement on external materialization

1. Pick `mart_product_health` as spike model (all columns typed yet; known simple shape).
2. In `transformation/models/marts/schema.yml` at the `mart_product_health` entry (`:1272`), add a single column with `data_type` and enable the contract:
   ```yaml
   - name: mart_product_health
     config:
       contract:
         enforced: true
     columns:
       - name: product_key
         data_type: varchar
         # ... (just product_key is enough for the spike)
   ```
3. In `mart_product_health.sql` `{{ config(...) }}` block, temporarily rename `product_key` to `product_key_SPIKE` in the SELECT.
4. Run `dbt build --select mart_product_health` inside the transformation container.
5. Observe:
   - **Fail with contract error** → Branch A (contracts work on external). Restore `product_key`.
   - **Succeed (no error)** → Branch B (contract silently ignored). Restore `product_key`.
6. Record the result in a comment at the top of the `schema.yml` block.

### Step 3A — Branch A: complete schema.yml + enable contracts

Only if Step 2 confirms enforcement works.

1. **Add `data_type` to all untyped columns across the 6 marts.**

   **`dim_customers` (`:159`)** — already has 8 typed. Add types for remaining columns (cross-reference SQL select list and DuckDB introspection or doc-string types):
   - `customer_key`: `varchar`, `customer_id`: `varchar`, `customer_code`: `varchar`, `full_name`: `varchar`
   - `phone`: `varchar`, `email`: `varchar`, `customer_group`: `varchar`
   - `lifetime_value`: `bigint`, `recency_days`: `integer`, `customer_status`: `varchar`
   - `lifetime_gross_profit`: `bigint`, `lifetime_contribution_margin`: `bigint`
   - `avg_order_contribution_margin_pct`: `double`, `margin_cogs_coverage_pct`: `double`
   - `is_margin_negative`: `boolean`, `order_count`: `integer`, `first_order_date`: `timestamp with time zone`
   - `last_order_date`: `date`, `avg_order_spend`: `bigint`, `avg_days_between_orders`: `double`
   - `predicted_next_purchase_date`: `date`, `next_purchase_signal`: `varchar`
   - `discount_sensitivity`: `varchar`, `cancel_rate`: `double`
   - `contact_quality`: `varchar`, `source_contact_quality`: `varchar`, `is_contactable`: `boolean`
   - `last_purchased_product`: `varchar`, `last_purchased_sku`: `varchar`
   - `top_affinity_product`: `varchar`, `top_affinity_sku`: `varchar`
   - `second_affinity_product`: `varchar`, `payment_behavior`: `varchar`
   - NOTE: `customer_status` DEPRECATED col still present in SQL — keep entry, mark deprecated in description

   **`fact_orders` (`:572`)** — add missing revenue col types:
   - `order_id`: `varchar`, `date_key`: `integer` (already typed), `time_key`: `integer` (already typed)
   - `gross_revenue`: `bigint`, `discount_amount`: `bigint`, `net_revenue`: `bigint`
   - `vat_amount`: `bigint`, `total_collected`: `bigint`, `is_active_order`: `boolean`
   - `ordered_at`: `timestamp with time zone`, `status`: `varchar`
   - `max_discount_rate`: `double`, `primary_discount_type`: `varchar`
   - `client_info`: `varchar`, `discount_codes`: `varchar`

   **`mart_product_health` (`:1272`)** — all columns need types (currently NONE):
   - `product_key`: `varchar`, `sku`: `varchar`, `product_name`: `varchar`, `category`: `varchar`, `brand_name`: `varchar`
   - `abc_class`: `varchar`, `has_margin_data`: `boolean`, `health_class`: `varchar`
   - `velocity_momentum`: `varchar`, `lifecycle_stage`: `varchar`, `oos_risk`: `varchar`
   - `velocity_90d`: `double`, `daily_velocity`: `double`, `units_sold`: `integer`
   - `revenue_share_pct`: `double`, `days_since_last_sale`: `integer`
   - `realized_margin_pct`: `double`, `cogs_variance_pct`: `double`, `margin_outlier`: `boolean`
   - `on_hand`: `integer`, `days_of_supply`: `double`, `is_oos`: `boolean`
   - `is_low_stock`: `boolean`, `is_dead_stock`: `boolean`
   - `stock_value_at_mac`: `bigint`, `dead_stock_value_at_risk`: `bigint`
   - `discount_dependency`: `varchar`, `discount_share`: `double`
   - `calculated_at`: `timestamp with time zone`

   **`mart_hug_optin` (`:5`)** — add types (currently only `not_null` on token):
   - `token`: `varchar`, `buyer_customer_id`: `varchar`, `phone`: `varchar`
   - `zalo_uid`: `varchar`, `name`: `varchar`, `consent_json`: `varchar`
   - `campaign_id`: `varchar`, `event_ts`: `timestamp with time zone`, `ingested_at`: `timestamp with time zone`

2. **Add full entry for `mart_customer_tier`** — new block in schema.yml (insert after `dim_customers`):
   ```yaml
   - name: mart_customer_tier
     description: >
       Strategic tier classification: one row per customer (full recompute each run).
       Single source of truth for which strategic outreach track a customer belongs to.
       Consumed by CRM reverse-ETL and the Hug touchpoint platform.
     config:
       contract:
         enforced: true
     columns:
       - name: customer_key
         data_type: varchar
         tests: [not_null, unique]
       - name: customer_id
         data_type: varchar
         tests: [not_null]
       - name: customer_code
         data_type: varchar
       - name: full_name
         data_type: varchar
       - name: customer_type
         data_type: varchar
       - name: value_group
         data_type: varchar
       - name: customer_status
         data_type: varchar
       - name: order_count
         data_type: integer
       - name: recency_days
         data_type: integer
       - name: last_order_date
         data_type: date
       - name: lifetime_value
         data_type: bigint
       - name: lifetime_contribution_margin
         data_type: bigint
       - name: channel_preference
         data_type: varchar
       - name: is_contactable
         data_type: boolean
       - name: source_contact_quality
         data_type: varchar
       - name: contact_quality
         data_type: varchar
       - name: strategic_tier
         data_type: varchar
         tests: [not_null]
         tests:
           - accepted_values:
               arguments:
                 values: ['LIVE_CORE', 'SECOND_ORDER', 'DORMANT_VALUABLE', 'LAPSED_VALUABLE', 'MASKED_REPEAT', 'NONBUYER', 'GRAVEYARD']
       - name: tier_reason
         data_type: varchar
       - name: tier_generated_at
         data_type: timestamp with time zone
   ```
   Column list derived from: `mart_customer_tier.sql:60-88` (SELECT list) and `duckdb_reader.py:88-108` (CRM consumer).

3. **Add full entry for `mart_customer_action_queue`** — the SQL output names (not the CRM alias names):
   ```yaml
   - name: mart_customer_action_queue
     description: >
       Actionable outreach queue: one row per RETAIL customer needing outreach.
       action_type drives the detailView Actions tab and CS/Sales daily workflow.
       Excludes BRONZE-tier and margin-negative customers by design.
     config:
       contract:
         enforced: true
     columns:
       - name: customer_key
         data_type: varchar
         tests: [not_null]
       - name: customer_id
         data_type: varchar
       - name: customer_code
         data_type: varchar
       - name: full_name
         data_type: varchar
       - name: phone
         data_type: varchar
       - name: email
         data_type: varchar
       - name: value_group
         data_type: varchar
       - name: customer_status
         data_type: varchar
       - name: next_purchase_signal
         data_type: varchar
       - name: discount_sensitivity
         data_type: varchar
       - name: lifetime_value
         data_type: bigint
       - name: order_count
         data_type: integer
       - name: avg_order_spend
         data_type: bigint
       - name: avg_days_between_orders
         data_type: double
       - name: cancel_rate
         data_type: double
       - name: recency_days
         data_type: integer
       - name: last_order_date
         data_type: date
       - name: predicted_next_purchase_date
         data_type: date
       - name: channel_preference
         data_type: varchar
       - name: product_affinity
         data_type: varchar
       - name: last_purchased_product
         data_type: varchar
       - name: last_purchased_sku
         data_type: varchar
       - name: top_affinity_product
         data_type: varchar
       - name: top_affinity_sku
         data_type: varchar
       - name: second_affinity_product
         data_type: varchar
       - name: payment_behavior
         data_type: varchar
       - name: is_contactable
         data_type: boolean
       - name: lifetime_contribution_margin
         data_type: bigint
       - name: is_margin_negative
         data_type: boolean
       - name: action_type
         data_type: varchar
         tests: [not_null]
       - name: priority_rank
         data_type: integer
         tests: [not_null]
       - name: action_rationale
         data_type: varchar
       - name: value_at_stake
         data_type: bigint
       - name: queue_generated_at
         data_type: timestamp with time zone
   ```
   NOTE: CRM's `_MART_ACTION_QUEUE_COLS` (`duckdb_reader.py:114-121`) uses aliased names (`rationale_vi`, `value_at_stake_vnd`, `priority`, `generated_date`). Those aliases are applied in the duckdb_reader SELECT queries, not in the mart itself. The contract is on the parquet column names — no mismatch.

4. **Enable `contract: {enforced: true}`** on all 6 marts (in their `schema.yml` model entry `config:` block).

5. **Override `on_schema_change`** for contracted models. The safest approach: add explicit model config blocks in `dbt_project.yml` or per-model in the SQL `{{ config() }}`. Adding to dbt_project.yml under a `+contract` section is cleanest:
   ```yaml
   # in dbt_project.yml, under models.sapo_warehouse.marts:
   marts:
     +on_schema_change: sync_all_columns  # existing global default
     # contracted consumer marts: override to fail so schema drift is never silently absorbed
     core:
       dim_customers:
         +on_schema_change: fail
     sales:
       fact_orders:
         +on_schema_change: fail
     customer:
       mart_customer_tier:
         +on_schema_change: fail
       mart_customer_action_queue:
         +on_schema_change: fail
       mart_hug_optin:
         +on_schema_change: fail
     # mart_product_health is in core/
     # add similarly
   ```
   Alternative (cleaner, less dbt_project.yml clutter): add `on_schema_change='fail'` in each mart's `{{ config() }}` SQL block. Prefer this — co-located with the contract declaration.

### Step 3B — Branch B: schema-assertion test (if spike fails)

1. Create `transformation/tests/assert_consumer_mart_columns.sql`:
   ```sql
   -- Asserts that all consumer-facing mart columns exist in the DuckDB information_schema.
   -- Returns rows (= test failures) when an expected column is absent.
   -- Run as part of dbt build; failure surfaces as a failed Dagster test node.
   {% set consumer_contracts = {
     'main_marts.dim_customers':            ['customer_key','customer_id','value_group','lifetime_value', ...],
     'main_marts.fact_orders':              ['order_id','net_revenue','date_key', ...],
     'main_marts.mart_customer_tier':       ['customer_key','strategic_tier','tier_reason', ...],
     'main_marts.mart_customer_action_queue': ['customer_key','action_type','priority_rank', ...],
     'main_marts.mart_product_health':      ['product_key','health_class','oos_risk', ...],
     'main_marts.mart_hug_optin':           ['token','phone','event_ts', ...],
   } %}
   -- Returns name of each expected column that is missing from information_schema
   SELECT table_schema || '.' || table_name AS mart, column_name AS expected_but_missing
   FROM (VALUES ...) AS expected(mart, col)
   WHERE NOT EXISTS (
     SELECT 1 FROM information_schema.columns
     WHERE table_schema || '.' || table_name = expected.mart
       AND column_name = expected.col
   )
   ```
   This approach works regardless of materialization type.

2. Do NOT add `contract: {enforced: true}` blocks (they're no-ops on external). Add a comment in `schema.yml` explaining why contracts are declared but not enforced.
3. Document the dbt-duckdb version to watch for a fix.

### Step 4 — Verify Dagster failure propagation

1. With contracts enabled (Branch A), deploy to the container (`docker compose exec data_platform ...`).
2. Deliberately break one mart (e.g., rename a column in a `{{ config() }}` CTE alias).
3. Trigger `dbt build --select tag:mart` via Dagster UI or `run_dbt.py`.
4. Confirm: the Dagster asset `sapo_dbt_assets` shows FAILED (not WARNING, not partial).
5. Confirm: `run_failure_sensor` fires → Lark message received.
6. Restore the intentional break.

### Step 5 — Final validation

1. Run `dbt build --select tag:mart` clean (no breakage). All tests pass.
2. Check Dagster run history: no unexpected failures.
3. Update `freshness.md` — note contract enforcement added for the 6 marts (so future column renames generate a prominent failure before deployment).

---

## Todo List

- [ ] Pin `dbt-duckdb==1.10.1` and `dbt-core==1.11.8` in `ingestion/requirements.txt`
- [ ] Run spike: add contract on `mart_product_health`, intentionally break, run `dbt build`
- [ ] Record spike result (branch decision) in a comment in `schema.yml`
- [ ] **Branch A**: Add `data_type` to all untyped columns of `dim_customers`
- [ ] **Branch A**: Add `data_type` to all untyped columns of `fact_orders`
- [ ] **Branch A**: Add `data_type` to all untyped columns of `mart_product_health`
- [ ] **Branch A**: Add `data_type` to all untyped columns of `mart_hug_optin`
- [ ] Add schema.yml entry for `mart_customer_tier` (columns + data_type)
- [ ] Add schema.yml entry for `mart_customer_action_queue` (columns + data_type)
- [ ] **Branch A**: Add `contract: {enforced: true}` to all 6 marts in schema.yml
- [ ] **Branch A**: Add `on_schema_change: fail` to contracted models (in model `{{ config() }}` or dbt_project.yml)
- [ ] **Branch B**: Create `transformation/tests/assert_consumer_mart_columns.sql`
- [ ] Run `dbt build --select tag:mart` clean
- [ ] Verify Dagster failure propagation (deliberate break → failed asset)
- [ ] Confirm Lark alert fires on Dagster asset failure
- [ ] Restore any deliberate breakage

---

## Success Criteria

1. `ingestion/requirements.txt` has pinned `dbt-duckdb==X.Y.Z` and `dbt-core==X.Y.Z`.
2. `mart_customer_tier` and `mart_customer_action_queue` have complete `schema.yml` entries with `data_type` on every column.
3. `dim_customers`, `fact_orders`, `mart_product_health`, `mart_hug_optin` have `data_type` on all columns.
4. Either:
   - **Branch A**: `contract: {enforced: true}` on all 6 marts; `on_schema_change: fail` overrides in place; a deliberate rename produces a `dbt build` error **before** any parquet is written.
   - **Branch B**: `assert_consumer_mart_columns.sql` returns 0 rows in clean state and ≥1 row when a column is removed.
5. Deliberate contract break → Dagster asset `sapo_dbt_assets` FAILED → Lark alert fires.
6. Clean `dbt build --select tag:mart` completes without new failures.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Spike: contracts silently no-op on external materialization | Medium | Medium | Branch B fallback (schema-assertion test) provides equivalent guard at test phase |
| `data_type` mismatch between schema.yml declaration and actual DuckDB inferred type | Medium | High | Introspect actual mart output with `DESCRIBE` in container before finalizing; DuckDB is permissive (`varchar` catches most string variants) |
| `on_schema_change: fail` breaks an existing incremental model in staging/intermediate | Low | Medium | Override is scoped only to the 6 mart models; staging uses `delete+insert`, not affected |
| Version pin disrupts existing container builds | Low | Low | Pin to already-installed version — no functional change; if `pip install` hash-checks fail, use `~=1.10` constraint |
| `mart_customer_action_queue` CRM alias gap (`action_rationale` vs `rationale_vi`) causes confusion | Medium | Low | Document clearly: contract enforces parquet names; CRM aliases at query time in `duckdb_reader.py`; no runtime conflict |
| `dim_customers` has many columns — data_type typo causes build failure | Medium | Medium | Add types in a single commit; run full dbt build in staging container before merging |

---

## Security Considerations

- No new auth surface, no secrets. `schema.yml` changes are compile-time only.
- Contract enforcement does not add runtime DuckDB connections; it runs inside the dbt execution context already isolated in the container.
- Pin versions reduce supply-chain risk from floating deps.

---

## Next Steps

- Phase 02 (`phase-02-consumer-contract-exposures.md`) depends on this phase completing. Exposure declarations reference the mart nodes by name — those names must be in schema.yml first.
- If Branch B: file a watch note on dbt-duckdb changelog for external materialization contract support; re-evaluate on next minor version bump.
- Phase 03 (`phase-03-crm-sync-observability-alerting.md`) can proceed in parallel (different files).

---

## Unresolved Questions

1. **Spike result unknown until execution.** This phase must branch at Step 2; the plan accounts for both outcomes but the implementer must make the call.
2. **Exact DuckDB column types for `dim_customers` computed columns** (e.g., `avg_days_between_orders` — is it `double` or `float`?). Verify with `DESCRIBE main_marts.dim_customers` inside the container before finalizing `data_type` declarations. The plan lists `double` as the expected type based on SQL-style division logic, but confirm.
3. **`mart_hug_optin` materialized as `table` (not external/parquet)** — contract enforcement is unambiguous for this one, but it means it's NOT picked up by `refresh_rolling.py` GC logic. This is a pre-existing condition; flag for awareness but out of scope here.
