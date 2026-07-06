# Phase 4: Staff Performance Mart

**Status:** TODO

## Goal

Cross-system weekly staff performance mart joining CRM activities, CRM tasks, and Sapo orders.

## Identity join path

```
stg_crm__activity_log.staff_user_id (UUID)
stg_crm__task.assignee_user_id      (UUID)
        ↓  via dim_staff.crm_user_id
        dim_staff.staff_key
        ↑  via fact_orders.seller_staff_key
fact_orders
```

`dim_staff.crm_user_id` is populated after Phase 3 runs.

## Output grain

`staff_key × week_start_date` (ICT Monday)

## Columns

| Column | Source | Description |
|--------|--------|-------------|
| `staff_key` | dim_staff | Surrogate |
| `staff_id` | dim_staff | Sapo account_id |
| `crm_user_id` | dim_staff | CRM UUID |
| `full_name` | dim_staff | |
| `week_start_date` | derived | Monday ICT |
| `activities_total` | crm_activity_log | All logged |
| `activities_outbound` | crm_activity_log | direction='out' |
| `contacts_reached` | crm_activity_log | contact_outcome IN ('answered','replied','met') |
| `call_duration_s` | crm_activity_log | SUM(contact_duration_s) |
| `tasks_assigned` | crm_task | assigned to this user, created in week |
| `tasks_completed` | crm_task | completed_at in week |
| `tasks_open_eow` | crm_task | open at end of week (snapshot as-of last batch) |
| `orders_sold` | fact_orders | seller_staff_key, confirmed status |
| `revenue_vnd` | fact_orders | SUM(net_revenue) |

## Files to create

- `transformation/models/marts/crm/mart_staff_performance_weekly.sql`
- Add to `transformation/models/marts/crm/` directory (create if absent)

## Dependencies

- `dim_staff` (Phase 3) — must run first, provides `crm_user_id`
- `stg_crm__activity_log` (existing)
- `stg_crm__task` (Phase 3)
- `fact_orders` (existing)

## Risks

- CRM staff not in dim_staff (email mismatch): activities will have NULL staff_key — include a `crm_only` row with `crm_user_id` populated but `staff_id` NULL
- `tasks_open_eow` is approximated from latest parquet snapshot, not a true point-in-time query
