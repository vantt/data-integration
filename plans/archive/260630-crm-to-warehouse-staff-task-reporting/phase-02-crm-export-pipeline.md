# Phase 2: CRM → Warehouse Export Pipeline

**Status:** DONE

## What was done

- `crm_writeback_assets.py`: added `crm_app_user` (snapshot) and `crm_task` (incremental by `updated_at`)
- `crm_app_user` export: all columns including `staff_id`
- `crm_task` export: joins `crm_party_identity` to resolve `customer_id`; watermark on `updated_at` (not `created_at`) so edits/assignments are captured
- `sources.yml`: added `crm_app_user` (single parquet) and `crm_task` (hive-partitioned incremental)

## Files modified

- `orchestration/assets/crm_writeback_assets.py`
- `transformation/models/sources.yml`

## Run order

1. `crm_app_user_export` (Dagster) → `crm_export/crm_app_user.parquet`
2. `crm_task_export` (Dagster) → `crm_export/crm_task/date=YYYYMMDD/batch_HHMMSS.parquet`
3. dbt run (Phase 3)

## Notes

- `crm_task` uses `updated_at` watermark so status changes (open→done, reassignments) are picked up
- `stg_crm__task` deduplicates to latest snapshot per `task_id` via `ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY updated_at DESC)`
