# Rill Project

Local Rill project for fast metrics exploration next to Metabase.

## Scope

This project owns the last-mile semantic layer for Rill:

- source models over curated published Parquet files
- Rill SQL models
- metrics views
- explore dashboards

It does not replace dbt or the Metabase handbook workflow.

## Runtime

This project is intended to run through the repo root compose stack:

```bash
docker compose up -d rill
```

Default URLs:

- `http://localhost:9009`
- `https://rill.lan.fwg.vn` if Caddy is running

## Input Contract

Dagster publishes these files into `/app/data_lake/export/rill/current/`:

- `fact_orders.parquet`
- `fact_sales.parquet`
- `fact_marketing_spend.parquet`
- `fact_targets.parquet`
- `dim_channels.parquet`
- `dim_branch_location.parquet`
- `dim_geography.parquet`
- `dim_staff.parquet`
- `dim_products.parquet`
- `dim_order_status.parquet`
- `dim_customers.parquet`

## 3-Layer Scope Architecture

Metrics follow the analytics-handbook 3-layer architecture:

The Rill flags are the mart's `fact_orders.scope_*` columns gated by `fact_orders.is_active_order` (not cancelled, not draft), the combination the segment rules prescribe for revenue. The models never re-derive them, so Rill counts the same orders as Metabase; `sales_items_enriched` takes the flags of the line's order.

| Layer | Scope Flag | Filter | Audience |
|-------|------------|--------|----------|
| Executive [All] | `scope_sales` | `fact_orders.scope_sales AND is_active_order` | CEO, Directors |
| Retail [Retail] | `scope_retail` | `fact_orders.scope_retail AND is_active_order` (RETAIL customer, not on a B2B channel) | Sales, Marketing |
| B2B [B2B] | `scope_b2b` | `fact_orders.scope_b2b AND is_active_order` (WHOLESALE/PARTNER customer or B2B channel) | B2B Sales |

Pre-filtered measures available: `sales_revenue`, `retail_revenue`, `b2b_revenue`.

See [Report Segmentation Guide](../docs/analytics-handbook/guides/report_segmentation.md) and [segments.md](../docs/analytics-handbook/semantic/segments.md) for details.

## Initial Assets

Models:

- `orders_enriched`
- `sales_items_enriched`
- `marketing_spend_enriched`

Metrics views:

- `orders_core_metrics`
- `sales_items_core_metrics`
- `marketing_spend_core_metrics`

Dashboards:

- `orders_core`
- `sales_items_core`
- `marketing_spend_core`
