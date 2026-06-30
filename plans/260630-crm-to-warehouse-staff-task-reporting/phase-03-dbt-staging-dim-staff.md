# Phase 3: dbt Staging + dim_staff Enrichment

**Status:** DONE

## What was done

- `stg_crm__app_user` (new view): normalizes email to `lower(trim(email))`, casts types, exposes `crm_user_id` + `staff_id`
- `stg_crm__task` (new view): deduplicates incremental batches to latest-per-task_id; resolves `customer_id`
- `dim_staff`: LEFT JOIN with `stg_crm__app_user` on normalized email → adds `crm_user_id` column

## Files modified

- `transformation/models/staging/stg_crm__app_user.sql` (new)
- `transformation/models/staging/stg_crm__task.sql` (new)
- `transformation/models/marts/core/dim_staff.sql`

## Deploy steps

```bash
# 1. Run Dagster asset to produce parquet first
#    (Dagster UI → crm_writeback group → crm_app_user_export)

# 2. Run dbt inside data_platform container
docker exec data_platform dbt run --select stg_crm__app_user stg_crm__task dim_staff

# 3. dim_staff is rolling parquet → rebuild serving views
#    Stop Metabase first (DuckDB single-writer)
docker compose stop metabase
docker exec data_platform python bootstrap_serving_views.py
docker compose start metabase
```

## Risks

- `dim_staff` column addition (`crm_user_id`) changes parquet schema → any downstream mart referencing `dim_staff.*` needs a full-refresh or explicit column list. Current dependents: `fact_orders` join is on `staff_id` (integer), not `SELECT *`, so safe.
- `stg_crm__task` depends on `crm_task` parquet existing — dbt run will fail if `crm_task_export` has never run. Run Dagster asset first.
