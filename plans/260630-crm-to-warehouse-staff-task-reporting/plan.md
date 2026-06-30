# Plan: CRM → Warehouse — Staff Identity + Task Reporting

**Status:** Phase 1 DONE | Phase 2 DONE | Phase 3 DONE | Phase 4 DONE

## Goal

Export CRM app users and tasks to the warehouse, wire staff identity across systems, and build a staff performance mart.

## Phases

| # | Name | Status | File |
|---|------|--------|------|
| 1 | Staff identity wiring (CRM side) | DONE | [phase-01-staff-identity-wiring.md](phase-01-staff-identity-wiring.md) |
| 2 | CRM → Warehouse export pipeline | DONE | [phase-02-crm-export-pipeline.md](phase-02-crm-export-pipeline.md) |
| 3 | dbt staging + dim_staff enrichment | DONE (models created) | [phase-03-dbt-staging-dim-staff.md](phase-03-dbt-staging-dim-staff.md) |
| 4 | Staff performance mart | DONE | [phase-04-staff-performance-mart.md](phase-04-staff-performance-mart.md) |

## Dependencies

- `dim_staff` rebuild requires `stg_crm__app_user` (new) → restart data_platform after dbt run
- `crm_app_user_export` Dagster asset must run first to produce parquet before dbt can read it
- `dim_staff` is a rolling parquet — needs `bootstrap_serving_views.py` after column add (stop Metabase first)

## Acceptance Criteria

- [ ] `crm_app_user.staff_id` populated for all active staff on next login
- [ ] `crm_app_user_export` and `crm_task_export` Dagster assets run without error
- [ ] `dim_staff.crm_user_id` non-null for matched staff
- [ ] `mart_staff_performance` aggregates tasks + activities per staff per week
