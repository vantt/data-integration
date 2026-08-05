# Phase 01 — Expose action scenario registry to the serving layer

**Priority:** P2 · **Status:** pending · **Effort:** 1.5h · **Blocked by:** —
**File ownership:** `transformation/**` only. Touches no CRM file.

## Context

- Seed: `transformation/seeds/seed_action_scenario_registry.csv` — 13 rows (not 12), columns
  `action_type, mart, enabled, scenario_group, description_vi`.
- Typed in `transformation/dbt_project.yml:38-40` (`+column_types: {enabled: boolean}`).
- Documented + tested in `transformation/models/marts/schema.yml:4` (`dbt_utils.unique_combination_of_columns`
  on `(action_type, mart)`).
- Consumed today ONLY as a feature flag inside the two marts:
  `mart_customer_action_queue.sql:197-201`, `mart_customer_sku_action_queue.sql:210-214`.

## Key insight (the blocker this phase removes)

**dbt seeds do not reach `olap.duckdb`.** Marts materialise as external parquet
(`transformation/dbt_project.yml:71-77` `+materialized: external`, `macros/get_rolling_location.sql:1`)
into `$DBT_EXPORT_PATH/rolling/{table}/`. `scripts/provisioning/bootstrap_serving_views.py:120-149`
then creates one `main.{table}` + `main_marts.{table}` view per **rolling subdirectory**.
Seeds materialise as plain tables in `main` of `sapo_warehouse.duckdb` — they never produce a rolling
folder, so `main_marts.seed_action_scenario_registry` does not exist and the CRM reverse-ETL
(`crm/sync/duckdb_reader.py:206` opens `olap.duckdb` read-only) cannot see it.

Fix: one thin passthrough mart model. The seed stays the single source of truth (DRY).

## Requirements

**Functional**
1. `main_marts.dim_action_scenario_registry` exists in `olap.duckdb` with all 5 seed columns.
2. Row content identical to the seed — no filtering, no renaming, no derived columns.
3. `description_vi` carries proper Vietnamese diacritics (currently ASCII-folded, e.g.
   `Het lieu trinh qua han`) because it becomes the staff-facing label in P07.

**Non-functional**
4. Zero change to the two marts' existing filter behaviour.
5. `dbt build --select seed_action_scenario_registry+` stays green.

## Architecture / data flow

```
seed_action_scenario_registry.csv
   └─ dbt seed ─→ main.seed_action_scenario_registry   (sapo_warehouse.duckdb)
        ├─ ref() ─→ mart_customer_action_queue      (existing feature flag, unchanged)
        ├─ ref() ─→ mart_customer_sku_action_queue  (existing feature flag, unchanged)
        └─ ref() ─→ dim_action_scenario_registry    (NEW passthrough)
                       └─ external parquet → rolling/dim_action_scenario_registry/
                            └─ bootstrap_serving_views → main_marts.dim_action_scenario_registry
                                 └─ Phase 02: reverse-ETL → cache.wh_action_scenario_registry
```

## Related code files

**Create**
- `transformation/models/marts/customer/dim_action_scenario_registry.sql`

**Modify**
- `transformation/seeds/seed_action_scenario_registry.csv` — add diacritics to `description_vi`.
- `transformation/models/marts/schema.yml` — document + test the new model.

**Delete** — none.

## Implementation steps

1. Create `dim_action_scenario_registry.sql` mirroring the mart config block used by
   `mart_customer_action_queue.sql:1-5`:
   ```sql
   {{ config(
       tags=['mart', 'customer', 'crm_sync'],
       options={'format': 'parquet'},
       location="{{ get_rolling_location() }}"
   ) }}

   -- Canonical opportunity-type taxonomy. Passthrough of the scenario registry seed so the
   -- CRM app can read the same enable flags + Vietnamese labels the marts filter on.
   SELECT
       action_type,
       mart,
       enabled,
       scenario_group,
       description_vi
   FROM {{ ref('seed_action_scenario_registry') }}
   ```
2. Rewrite `description_vi` with diacritics, keeping the per-mart distinction that already exists
   (SKU `REORDER_NUDGE` = "Hết liệu trình hôm nay" vs customer `REORDER_NUDGE` = "Quá hạn nhịp mua").
   Suggested labels — final wording is the implementer's call with CS:
   | action_type | mart | description_vi |
   |---|---|---|
   | REORDER_OVERDUE | sku | Hết liệu trình quá hạn |
   | REORDER_NUDGE | sku | Hết liệu trình hôm nay |
   | REORDER_PREEMPT | sku | Sắp hết liệu trình |
   | PROGRESS_CHECK | sku | Hỏi cảm nhận D12-16 |
   | USAGE_FOLLOWUP | sku | Xác nhận bắt đầu dùng D5-9 |
   | GIFT_TO_PURCHASE | sku | Từng được tặng, chưa từng mua |
   | CALL_NOW | customer | VIP đang nguội — gọi ngay |
   | MANUAL_RISK_REVIEW | customer | NV gắn tag rủi ro |
   | REORDER_NUDGE | customer | Quá hạn nhịp mua |
   | REORDER_PREEMPT | customer | Sắp tới hạn nhịp mua |
   | WIN_BACK | customer | Đã churn — cần offer |
   | SECOND_ORDER | customer | Mua 1 lần — đẩy đơn 2 |
   | HIGH_CANCEL_RISK | customer | Tỷ lệ hủy cao |
   3. **Before editing values**: `grep -n "description_vi" transformation/models/marts/schema.yml` —
      confirm no `accepted_values` test asserts on the ASCII strings. If one exists, update it in the
      same commit.
4. Add to `transformation/models/marts/schema.yml`: model doc, `not_null` on `action_type`/`mart`,
   `dbt_utils.unique_combination_of_columns` on `(action_type, mart)`, `accepted_values` on `mart`
   limited to the two mart names.
5. Run `dbt seed --select seed_action_scenario_registry` then
   `dbt build --select dim_action_scenario_registry mart_customer_action_queue mart_customer_sku_action_queue`.
6. Confirm the rolling folder appeared, then run the serving bootstrap so the view is created:
   `python scripts/provisioning/bootstrap_serving_views.py` (or the Dagster `sapo_serving_db` asset).
7. Verify in `olap.duckdb`: `SELECT COUNT(*) FROM main_marts.dim_action_scenario_registry` → 13.

## Todo list

- [x] Create `dim_action_scenario_registry.sql`
- [x] Grep for tests asserting current `description_vi` values (none found — safe to edit)
- [x] Add diacritics to `seed_action_scenario_registry.csv`
- [x] Add model + tests to `schema.yml`
- [x] `dbt seed` + `dbt build` green (6/6 tests pass)
- [x] Rolling folder + `main_marts.dim_action_scenario_registry` view exist, 13 rows (verified via read-only query)

## Success criteria

- `SELECT COUNT(*) FROM main_marts.dim_action_scenario_registry` in `olap.duckdb` returns 13.
- `SELECT DISTINCT mart FROM main_marts.dim_action_scenario_registry` returns exactly the 2 mart names.
- `GIFT_TO_PURCHASE` still absent from `mart_customer_sku_action_queue` output (`enabled=false` path intact).
- `dbt build --select seed_action_scenario_registry+` passes.

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| Editing `description_vi` breaks an `accepted_values` test | Low×Med | Step 3 greps first; update test in same commit |
| Adding a 4th `ref()` on the seed changes mart compile order/behaviour | Low×Low | Passthrough is a leaf model; marts untouched. Assert mart row counts unchanged before/after |
| Serving view not created because bootstrap not re-run | Med×Med | Step 6 explicit; Phase 02 fails loudly (`_check_columns`) rather than silently syncing 0 rows |
| `enabled` loads as VARCHAR not BOOLEAN | Low×High | Already pinned in `dbt_project.yml:38-40`; assert `typeof` in step 7 |

## Rollback

Delete `dim_action_scenario_registry.sql` + its `schema.yml` block, revert the CSV, re-run
`dbt build`. Nothing downstream depends on it until Phase 02 lands. Zero CRM impact.

## Security considerations

Reference data only — no PII, no customer rows. Read-only for CRM.

## Next steps

Unblocks Phase 02 (`crm/sync` reads `main_marts.dim_action_scenario_registry`).
