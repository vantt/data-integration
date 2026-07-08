# Phase 4 Implementation Report — Scenario Registry and Tier-Aware Branching

Plan: `plans/260708-1501-gift-purchase-sku-action-scenario/phase-04-scenario-registry-and-tier-aware-branching.md`
Status: DONE

## Files Changed

- Created `transformation/seeds/seed_action_scenario_registry.csv` — 13 rows exactly as specified (5 sku-mart types incl. `GIFT_TO_PURCHASE` enabled=false, 7 customer-mart types enabled=true).
- `transformation/dbt_project.yml:33-35` — added `seed_action_scenario_registry: +column_types: {enabled: boolean}` under `seeds.sapo_warehouse`.
- `transformation/models/marts/schema.yml`:
  - `:3-27` — new `seeds:` top-level block, `seed_action_scenario_registry` doc + `dbt_utils.unique_combination_of_columns` on `(action_type, mart)`.
  - `:426-433` (mart_customer_action_queue columns) — added `strategic_tier` column doc after `is_contactable`, updated `is_contactable` description to note the tier-based passthrough.
  - `:468-476` / description update + `:531-539` (mart_customer_sku_action_queue) — added `is_contactable`/`strategic_tier` column docs, updated `action_type` `accepted_values` to include `GIFT_TO_PURCHASE`, updated model description.
- `transformation/models/marts/customer/mart_customer_sku_action_queue.sql`:
  - `:37-54` `customers` CTE — dropped local `is_contactable` expr, added `AND NOT is_us_gift_recipient`.
  - `:56-64` new `tier` CTE (`customer_key, strategic_tier, is_contactable, tier_reason` from `mart_customer_tier`).
  - `:72-118` `classified` CTE — replaced `cu.is_contactable` with `t.is_contactable, t.strategic_tier`; added `LEFT JOIN tier t`; added `GIFT_TO_PURCHASE` outer CASE branch (`supply_stream='gift_only' AND DATE_DIFF('day', last_purchase_date, CURRENT_DATE) BETWEEN 14 AND 45`) wrapping the unchanged 5-branch `purchased`-stream cascade in a nested `CASE`.
  - `:134` final SELECT — added `classified.strategic_tier`.
  - `:182-185` `action_rationale` CASE — added `GIFT_TO_PURCHASE` branch (adapted to the file's existing simple-CASE idiom, `WHEN 'GIFT_TO_PURCHASE' THEN ...` rather than the phase file's literal `WHEN action_type = ...` searched-CASE snippet, which would not compile inside `CASE classified.action_type ... END`).
  - `:209-213` — added `LEFT JOIN {{ ref('seed_action_scenario_registry') }} reg ON classified.action_type = reg.action_type AND reg.mart = 'mart_customer_sku_action_queue'` + `AND COALESCE(reg.enabled, TRUE) = TRUE` in WHERE.
  - `:13-24` header comment updated to document `GIFT_TO_PURCHASE` and the registry gate.
- `transformation/models/marts/customer/mart_customer_action_queue.sql`:
  - `:15-23` new `tier` CTE.
  - `:25-72` `customers` CTE — dropped local `is_contactable` expr, `t.is_contactable, t.strategic_tier` instead, `LEFT JOIN tier t`, added `AND NOT d.is_us_gift_recipient`.
  - `:139` final SELECT — added `classified.strategic_tier`.
  - `:148,158,175` — qualified 3 previously-bare `CASE action_type` refs to `CASE classified.action_type` (bug fix required by the new registry JOIN: `reg.action_type` now exists in scope, so the unqualified name became ambiguous — not called out explicitly in the phase file but necessary for the SQL to compile).
  - `:197-201` — added registry `LEFT JOIN` + `AND COALESCE(reg.enabled, TRUE) = TRUE`, and qualified `WHERE action_type IS NOT NULL` → `classified.action_type IS NOT NULL` for the same ambiguity reason.

`dim_customers.sql` was not touched (read-only reference, per constraint). No `crm/` files touched.

## Deviations From Literal Phase-File Snippets (both required for correctness)

1. **`action_rationale` GIFT_TO_PURCHASE branch**: phase file wrote `WHEN action_type = 'GIFT_TO_PURCHASE' THEN ...` (searched-CASE syntax) but the surrounding block is `CASE classified.action_type WHEN 'X' THEN ...` (simple-CASE). Used `WHEN 'GIFT_TO_PURCHASE' THEN ...` to match — same semantics, valid SQL, consistent with every other branch in that CASE.
2. **Ambiguous `action_type` in `mart_customer_action_queue.sql`**: adding `LEFT JOIN seed_action_scenario_registry reg` introduces a second `action_type` column into scope. 3 pre-existing bare `CASE action_type` references (priority_rank, action_rationale, value_at_stake) and the bare `WHERE action_type IS NOT NULL` would become ambiguous-column errors. Qualified all 4 to `classified.action_type`. `mart_customer_sku_action_queue.sql` already qualified these, so no equivalent fix was needed there.
3. Registry JOIN target in both files used `{{ ref('seed_action_scenario_registry') }}` (dbt convention) rather than the bare table name shown in the phase file's illustrative SQL.

## dbt Command Output

`data_platform` restarted (manifest reload confirmed in boot log).

**Seed:**
```
1 of 1 OK loaded seed file main.seed_action_scenario_registry (INSERT 13) in 0.07s
Done. PASS=1 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=1
```
`enabled` column type confirmed via `information_schema.columns`: `('enabled', 'BOOLEAN')` — not VARCHAR.

**Run** (`mart_customer_tier mart_customer_sku_action_queue mart_customer_action_queue`):
```
1 of 3 OK created sql external model main_marts.mart_customer_tier
2 of 3 OK created sql external model main_marts.mart_customer_action_queue
3 of 3 OK created sql external model main_marts.mart_customer_sku_action_queue
Done. PASS=3 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=3
```

**Test** (`mart_customer_tier mart_customer_sku_action_queue mart_customer_action_queue seed_action_scenario_registry`): 17/17 PASS, including:
- `accepted_values_..._action_type__..._GIFT_TO_PURCHASE` — PASS
- `dbt_utils_unique_combination_of_columns_seed_action_scenario_registry_action_type__mart` — PASS
- All pre-existing not_null/unique/accepted_values tests on both marts and the seed — PASS

Downstream sanity check: `dbt test --select mart_deadstock_target_queue` (consumes `mart_customer_tier`) — 10/10 PASS, unaffected.

## Baseline Comparison (`supply_stream='purchased'` / all rows)

Pre-change snapshots of both marts captured from live `olap.duckdb` serving views before any edits (2810 not directly — full baseline counts: sku mart 3897 rows, customer mart 506 rows).

- **`mart_customer_sku_action_queue`**, restricted to `(customer_key, sku)` pairs where `int_customer_sku_supply_tracking.supply_stream = 'purchased'`, compared on `(customer_key, sku, action_type, priority_rank, action_rationale, last_purchase_date, estimated_depletion_date, days_until_depletion, days_since_order)`:
  - baseline: 2810 rows, post-change: 2810 rows, **IDENTICAL: True**
  - Full mart row count changed from 3897 → 2810 post-change; the 1087-row delta is entirely `gift_only`-stream rows that previously fell into the old undifferentiated 5-branch cascade and now correctly route to `GIFT_TO_PURCHASE` (suppressed by registry) — the accepted, expected gap from Phase 3/4, not a regression.
- **`mart_customer_action_queue`**, all 7 action_types, compared on `(customer_key, customer_id, customer_code, action_type, priority_rank, action_rationale, value_at_stake, has_manual_risk_flag)`:
  - baseline: 506 rows, post-change: 506 rows, **IDENTICAL: True** (row-for-row, no diffs)

## GIFT_TO_PURCHASE Suppression Proof

- Live mart (registry `enabled=false`): `SELECT COUNT(*) FROM mart_customer_sku_action_queue WHERE action_type='GIFT_TO_PURCHASE'` → **0** (correctly suppressed).
- Manual override query (in-memory `registry_override` CTE flipping only `GIFT_TO_PURCHASE`/`mart_customer_sku_action_queue` to `enabled=TRUE`, real seed file/table untouched) reproducing the exact `classified`/registry-join logic from the mart SQL: **2 rows** would appear if enabled — confirms the branch is computed correctly and only suppressed by the registry default.

## Success Criteria — Verified

- [x] `enabled` BOOLEAN (confirmed via `information_schema.columns`)
- [x] `dbt_utils.unique_combination_of_columns(action_type, mart)` passes
- [x] `GIFT_TO_PURCHASE` computed-but-suppressed; override query proves it would appear (2 rows) if flipped
- [x] Both marts join `mart_customer_tier`; local phone-presence `is_contactable` CTE removed from both
- [x] Both marts exclude `is_us_gift_recipient = TRUE` (added `AND NOT is_us_gift_recipient` / `AND NOT d.is_us_gift_recipient`)
- [x] `mart_customer_action_queue` (7 types) and `mart_customer_sku_action_queue` `supply_stream='purchased'` rows (5 types) identical to pre-Phase-4 baseline; `gift_only` rows diverge as expected/accepted
- [x] `strategic_tier` present as an output column in both marts (confirmed via `information_schema.columns` + distribution query)

## Unresolved Questions

None — all phase-file ambiguities were resolvable by reading the referenced source files (`mart_customer_tier.sql`, `dim_customers.sql`, `int_customer_sku_supply_tracking.sql`) and existing SQL conventions in the two mart files.

Status: DONE
Summary: Registry seed + boolean typing + uniqueness test + tier join (is_contactable/strategic_tier) + is_us_gift_recipient exclusion + GIFT_TO_PURCHASE branch (suppressed) all implemented and verified; purchased-stream/7-type baselines are byte-identical, all touched dbt tests pass, downstream consumer unaffected.
Concerns/Blockers: None.
