# Rill + Metabase Integration Guide

> **Status:** Proposed
> **Date:** 2026-04-10
> **Scope:** Add Rill as a second reporting surface alongside Metabase without changing dbt/Dagster ownership of data modeling.

## 1. Goal

Add **Rill** as a companion analytics/reporting tool next to **Metabase**, while keeping the current architecture intact:

- **dbt + DuckDB** stay the single source of truth for business logic.
- **Metabase** stays the governed BI layer already backed by the Analytics Handbook.
- **Rill** is added for:
  - fast slice-and-dice exploration,
  - opinionated metrics dashboards,
  - operational comparisons,
  - scheduled reports,
  - optional embedding.

This is an addition, not a replacement.

## 2. Current Constraints In This Repo

The existing system already gives us a strong serving contract:

- dbt marts are exported as **rolling Parquet snapshots**
- the serving layer builds `olap.duckdb` views that always point to the latest snapshot
- Metabase reads from the serving DuckDB in read-only mode
- the repo is a **monorepo**
- local development is **Windows + Docker/WSL hybrid**
- data lake paths are **environment-driven**, not checked into git

That means the safest Rill design is one that:

- reuses curated marts,
- respects the dual-DuckDB strategy,
- avoids hardcoded Windows paths,
- does not move business logic out of dbt.

## 3. What Rill Is Good At

Based on the current Rill docs, Rill is strongest when used as a **metrics-first exploration and reporting layer**:

- **Explore dashboards** are built on top of **one metrics view / one big table**
- **Canvas dashboards** can combine multiple metrics views into a traditional dashboard
- **Reports** can send scheduled outputs to email or Slack
- **Security** can be applied at metrics-view/dashboard level with row filters and field-level visibility
- **Embeds** are supported through iframe URLs and an iframe API

This makes Rill a strong complement to Metabase for:

- operational cockpits,
- fast time comparisons,
- leaderboard-style exploration,
- interactive reports for one subject area at a time.

## 4. Important Rill Constraints From The Docs

The design must account for these Rill constraints:

1. **External DuckDB is local-dev oriented.**
   - Rill documents external DuckDB / live DuckDB usage as **not recommended for production use** and mainly for local testing.

2. **Rill Developer is the local build environment.**
   - Rill documents **Rill Developer** as the local development tool and **Rill Cloud** as the collaboration/deployment layer.

3. **Local-file deployment to Rill Cloud has packaging limits.**
   - Files need to be inside the project context and large local files are a poor fit for Cloud deployment.

4. **Windows usage goes through WSL.**
   - Current Rill install docs explicitly describe Windows usage through **WSL**, not native PowerShell-first execution.

5. **Metrics views expect one model/table.**
   - Rill's core semantic object is a metrics view powered by a **single model or table**, which strongly favors a denormalized "one big table per use case" contract.

**Inference:** Rill should **not** use `olap.duckdb` as the long-term production contract in this repo. It is acceptable for a local spike, but it is the wrong stable boundary for production integration.

## 5. Recommended Architecture

### 5.1 High-level topology

```text
dbt marts
  -> rolling parquet snapshots
     -> serving bootstrap -> serving/olap.duckdb -> Metabase
     -> rill publish step -> export/rill/current/*.parquet -> Rill managed DuckDB -> metrics views / dashboards / reports
```

### 5.2 Why this is the recommended boundary

Using a dedicated **Rill publish contract** is safer than reading `olap.duckdb` directly:

- it keeps **Metabase and Rill decoupled**
- it preserves the existing **dual-DuckDB** design
- it avoids coupling Rill to a **serving-specific view DB**
- it keeps Rill on **immutable Parquet snapshots**, which fits the current architecture
- it makes Rill inputs **versionable, curated, and replaceable**
- it creates room for **Rill-specific denormalized models** without polluting Metabase contracts

### 5.3 Docker Compose topology

With the new assumption that Rill runs inside the same `docker-compose.yml`, treat it as a sibling service to `data_platform` and `metabase`:

- join the same `caddy_net`
- mount the Rill project folder at `/app/rill`
- mount `./app_data/data_lake` at `/app/data_lake`
- persist Rill runtime state in a dedicated host path such as `./app_data/rill`
- expose it behind a separate host such as `rill.local`

Recommended ownership:

- **Dagster remains the freshness owner**
- **Rill remains the semantic and presentation owner for its own project**

That means:

- dbt + Dagster decide when curated data is ready
- a publish step updates `export/rill/current/`
- Dagster then triggers a targeted Rill refresh for changed models

Preferred refresh control when Rill is part of the same stack:

```text
dbt/dagster -> publish_rill_assets -> docker compose exec rill rill project refresh --local --model <model_name>
```

Rill's own cron refreshes should be a fallback, not the primary orchestration path, because this repo already has Dagster schedules.

## 6. Data Contract For Rill

### 6.1 Ownership rule

Keep the existing rule:

- **business logic lives in dbt**
- **Rill aggregates curated columns**
- **Rill does not become the place where finance formulas are invented**

In practice:

- if `net_revenue`, `gross_revenue`, `same_day_ship_rate`, `time_to_complete_hours` are core definitions, create or finalize them in dbt first
- in Rill, measures should mostly be `sum(...)`, `count(...)`, `avg(...)`, filtered measures, or light metric combinations

### 6.2 What Rill should own itself

Rill should own only the **last-mile semantic layer**:

- source models over published Parquet assets
- SQL models that denormalize curated marts into one-big-table shapes
- metrics views
- derived metrics views
- canvas dashboards, reports, and alerts

Rill should **not** own:

- raw ingestion cleanup
- cross-channel reconciliation logic
- warehouse-grade historical logic
- core finance definitions that already belong in dbt

### 6.3 Published inputs that Rill should read

The first implementation should publish the current version of these curated marts into:

```text
data_lake/export/rill/current/
```

Recommended published files:

| Published file | Current repo source | Why Rill needs it |
|---|---|---|
| `fact_orders.parquet` | `fact_orders` | Core order metrics |
| `fact_sales.parquet` | `fact_sales` | Product and item analysis |
| `fact_marketing_spend.parquet` | `fact_marketing_spend` | Spend and acquisition-side metrics |
| `fact_targets.parquet` | `fact_targets` | Actual vs target reporting |
| `dim_channels.parquet` | `dim_channels` | Human-readable channel attributes |
| `dim_branch_location.parquet` | `dim_branch_location` | Branch labels |
| `dim_geography.parquet` | `dim_geography` | Province/district slicing |
| `dim_staff.parquet` | `dim_staff` | Staff/operator slicing |
| `dim_products.parquet` | `dim_products` | Product, brand, SKU slicing |
| `dim_order_status.parquet` | `dim_order_status` | Human-readable order status labels |

This keeps the Rill contract stable while still letting Rill own its own denormalized models.

### 6.4 Detailed Rill models that should be built inside the Rill project

These are the models that Rill itself should build.

#### Model 1: `orders_enriched`

- **Type:** SQL model in Rill
- **Input:** `fact_orders`, `dim_channels`, `dim_branch_location`, `dim_geography`, `dim_staff`
- **Grain:** one row per order
- **Purpose:** parent model for executive and operations metrics

Rill-owned logic in this model:

- join surrogate keys to human-readable labels
- normalize time fields:
  - `order_date`
  - `order_hour`
  - `hour_start`
  - `day_of_week`
- derive convenience flags:
  - `is_completed`
  - `is_cancelled`
  - `is_open`
  - `is_sales_channel`
  - `is_fulfilled`
  - `is_partial_fulfillment`
- derive operational timing helpers:
  - `hours_to_first_ship`
  - `hours_to_complete`
  - `ship_same_day_flag`
  - `pending_gt_24h_flag`
  - `pending_gt_48h_flag`
- derive presentational buckets:
  - `first_ship_bucket`
  - `complete_time_bucket`
  - `order_size_band`

Logic that should stay in dbt, not in this Rill model:

- the definition of `gross_revenue`
- the definition of `net_revenue`
- the definition of `total_collected`
- source reconciliation and deduplication

#### Model 2: `sales_items_enriched`

- **Type:** SQL model in Rill
- **Input:** `fact_sales`, `dim_products`, `dim_channels`, `dim_branch_location`, `dim_geography`, `dim_staff`
- **Grain:** one row per order line item
- **Purpose:** product mix, SKU ranking, basket analysis

Rill-owned logic in this model:

- join product, channel, branch, geography, and staff labels
- derive time helpers:
  - `sale_date`
  - `sale_hour`
  - `day_of_week`
- derive presentational fields:
  - `brand_or_unknown`
  - `product_display_name`
  - `is_cancelled_order_line`
- derive convenience measures inputs:
  - `total_discount_amount = coalesce(discount_amount, 0) + coalesce(distributed_discount_amount, 0)`

#### Model 3: `marketing_spend_enriched`

- **Type:** SQL model in Rill
- **Input:** `fact_marketing_spend`, `dim_channels`, `dim_branch_location`
- **Grain:** one row per spend record
- **Purpose:** spend monitoring and acquisition-side reporting

Rill-owned logic in this model:

- join readable channel and branch labels
- derive time helpers:
  - `spend_date`
  - `week_start`
  - `month_start`
- derive convenience fields:
  - `has_clicks_flag`
  - `has_impressions_flag`
  - `channel_group`

Important constraint from current repo state:

- `fact_marketing_spend` has `campaign_id`
- `fact_orders` does **not** currently expose campaign attribution

Therefore this model can support:

- spend
- clicks
- impressions
- CPC
- CPM
- CTR

But it should **not** claim campaign-level:

- ROAS
- CAC
- attributed revenue
- attributed orders

until attribution data exists in the warehouse.

#### Model 4: `targets_enriched`

- **Type:** SQL model in Rill
- **Input:** `fact_targets`, `dim_channels`, `dim_branch_location`, `dim_staff`, `dim_products`
- **Grain:** one row per target row
- **Purpose:** reusable target lookup model for scorecards and actual-vs-target dashboards

Rill-owned logic in this model:

- join readable dimension labels
- normalize target dates:
  - `target_date`
  - `target_month`
  - `target_week`
- derive scope flags:
  - `has_branch_scope`
  - `has_staff_scope`
  - `has_channel_scope`
  - `has_product_scope`

#### Model 5: `actual_vs_target_daily`

- **Type:** SQL model in Rill
- **Input:** `orders_enriched`, `targets_enriched`
- **Grain:** `date x branch x channel x metric_code`
- **Purpose:** simple actual-vs-target scorecards

Rill-owned logic in this model:

- aggregate `orders_enriched` to daily actuals
- join to matching target rows
- compute:
  - `actual_value`
  - `target_value`
  - `achievement_rate`
  - `gap_value`

This model is a good fit for Rill because it is a **presentation-facing comparison table**, not a core warehouse fact.

### 6.5 Metrics views that Rill should own

Rill should define a **small number of parent metrics views** and then derive audience-specific views from them.

#### Parent metrics view: `orders_core_metrics`

- **Model:** `orders_enriched`
- **Timeseries:** `hour_start`
- **Why parent:** contains the superset of order dimensions and measures

Recommended dimensions:

- `channel_name`
- `channel_category`
- `platform`
- `branch_location_name`
- `province`
- `district`
- `staff_name`
- `status`
- `payment_status`
- `fulfillment_status`
- `day_of_week`
- `order_hour`
- `first_ship_bucket`
- `complete_time_bucket`
- `order_size_band`

Recommended measures:

- `orders_count = count(*)`
- `gross_revenue = sum(gross_revenue)`
- `net_revenue = sum(net_revenue)`
- `discount_amount = sum(discount_amount)`
- `tax_amount = sum(tax_amount)`
- `total_collected = sum(total_collected)`
- `avg_order_value = sum(net_revenue) / nullif(count(*), 0)`
- `completed_orders = count(*) filter (where is_completed)`
- `cancelled_orders = count(*) filter (where is_cancelled)`
- `open_orders = count(*) filter (where is_open)`
- `fulfilled_orders = count(*) filter (where is_fulfilled)`
- `eligible_orders = count(*) filter (where status != 'DRAFT')`
- `fulfillment_rate = fulfilled_orders / nullif(eligible_orders, 0)`
- `same_day_ship_orders = count(*) filter (where ship_same_day_flag)`
- `same_day_ship_rate = same_day_ship_orders / nullif(eligible_orders, 0)`
- `pending_gt_24h_orders = count(*) filter (where pending_gt_24h_flag)`
- `pending_gt_48h_orders = count(*) filter (where pending_gt_48h_flag)`
- `avg_hours_to_first_ship = avg(hours_to_first_ship)`
- `avg_hours_to_complete = avg(hours_to_complete)`
- `discount_rate = sum(discount_amount) / nullif(sum(gross_revenue), 0)`

Derived metrics views that should inherit from `orders_core_metrics`:

- `orders_exec_metrics`
  - expose only executive-safe measures and daily grain
- `orders_ops_metrics`
  - expose operational measures and hourly grain
- `orders_staff_metrics`
  - focus on staff ranking and operator comparisons

#### Parent metrics view: `sales_items_core_metrics`

- **Model:** `sales_items_enriched`
- **Timeseries:** `sale_date`
- **Purpose:** product and SKU exploration

Recommended dimensions:

- `product_name`
- `variant_name`
- `sku`
- `brand_name`
- `product_type`
- `channel_name`
- `branch_location_name`
- `province`
- `status`

Recommended measures:

- `order_lines = count(*)`
- `distinct_orders = count(distinct order_id)`
- `quantity_sold = sum(quantity)`
- `item_revenue = sum(revenue)`
- `direct_discount_amount = sum(discount_amount)`
- `allocated_discount_amount = sum(distributed_discount_amount)`
- `total_discount_amount = sum(total_discount_amount)`
- `avg_selling_price = sum(revenue) / nullif(sum(quantity), 0)`
- `avg_items_per_order = sum(quantity) / nullif(count(distinct order_id), 0)`

#### Parent metrics view: `marketing_spend_core_metrics`

- **Model:** `marketing_spend_enriched`
- **Timeseries:** `spend_date`
- **Purpose:** spend monitoring

Recommended dimensions:

- `channel_name`
- `channel_category`
- `branch_location_name`
- `campaign_id`
- `spend_code`
- `channel_group`

Recommended measures:

- `spend = sum(spend_amount)`
- `clicks = sum(clicks)`
- `impressions = sum(impressions)`
- `ctr = sum(clicks) / nullif(sum(impressions), 0)`
- `cpc = sum(spend_amount) / nullif(sum(clicks), 0)`
- `cpm = 1000 * sum(spend_amount) / nullif(sum(impressions), 0)`

#### Parent metrics view: `actual_vs_target_core_metrics`

- **Model:** `actual_vs_target_daily`
- **Timeseries:** `date`
- **Purpose:** scorecards and target pacing

Recommended dimensions:

- `metric_code`
- `channel_name`
- `branch_location_name`
- `scope_staff`

Recommended measures:

- `actual_value = sum(actual_value)`
- `target_value = sum(target_value)`
- `gap_value = sum(gap_value)`
- `achievement_rate = sum(actual_value) / nullif(sum(target_value), 0)`

### 6.6 When to move a Rill model back into dbt

Do **not** point Rill at:

- raw Parquet in `sapo_raw`
- `src_`, `stg_`, or `std_` models
- generic star-schema joins as the primary implementation path

Rill is best when fed curated, denormalized, business-readable inputs.

Start with the Rill-owned models above.

Move a model from Rill into dbt only if one of these becomes true:

- the SQL is reused by both Rill and Metabase
- the model needs data quality tests in the warehouse
- the join logic becomes business-critical
- performance requires pre-computation before Rill ingestion

## 7. Recommended Repo Placement

Create a separate Rill subproject when implementation starts:

```text
rill/
  rill.yaml
  connectors/
    duckdb.yaml
  models/
  metrics/
  dashboards/
  reports/
  .env.example
  README.md
```

This fits the monorepo cleanly and keeps Rill from leaking into Metabase or dbt folders.

If the team later deploys this through Rill Cloud from the monorepo, the documented pattern is:

```bash
rill project connect-github --subpath rill
```

## 8. Environment Strategy

Use Rill variables instead of hardcoded paths.

Recommended variables:

- `RILL_EXPORT_ROOT`
- `RILL_TIME_ZONE`

Example:

```yaml
# rill/rill.yaml
display_name: "Sapo Rill"
description: "Rill analytics companion for curated Sapo marts"

env:
  RILL_TIME_ZONE: "Asia/Ho_Chi_Minh"
```

Example `.env` values:

```text
# WSL development
RILL_EXPORT_ROOT=/mnt/d/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/export/rill/current

# Linux container / server
RILL_EXPORT_ROOT=/app/data_lake/export/rill/current
```

This is important because the current repo already has a Windows/Linux dual-path constraint.

## 9. Refresh Strategy

Add a new pipeline step after dbt/export completion:

```text
dbt marts complete
  -> bootstrap serving views
  -> publish_rill_assets
  -> Rill model refresh
```

### 9.1 What `publish_rill_assets` should do

This new step should:

- pick only the **approved Rill-facing datasets**
- write them to a stable path such as:

```text
data_lake/export/rill/current/<dataset>.parquet
```

- expose **one current file per dataset**
- avoid making Rill scan a large rolling history unless explicitly desired
- trigger targeted Rill refreshes for the changed models after the files are swapped

### 9.2 Why publish a current layer

It reduces:

- duplicate historical scans,
- filename-ranking logic inside Rill,
- Cloud packaging friction later,
- accidental ingestion of stale snapshots.

## 10. POC Path vs Production Path

### 10.1 Fast POC

For a quick spike, it is reasonable to do one of these locally:

- attach `data_lake/serving/olap.duckdb` as an external DuckDB connector
- attach `data_lake/sapo_warehouse.duckdb`
- read rolling Parquet directly and select the latest file in SQL

Use this only to validate:

- dashboard fit,
- metrics-view design,
- report usefulness,
- performance on real data.

### 10.2 Production recommendation

For production use in this repo, prefer:

- **Rill managed DuckDB**
- curated **Parquet publish contract**
- Rill-owned last-mile SQL models over curated marts

This is the most compatible path with the current architecture.

### 10.3 Shared/embedded deployment

If the goal is:

- shared dashboards,
- scheduled team reports,
- public URLs,
- authenticated embeds,

then the documented Rill path is **Rill Cloud**.

If the goal is **strictly on-prem shared production**, that needs separate validation. The docs reviewed for this design describe **Rill Developer + Rill Cloud** as the standard path, not a self-hosted shared runtime.

## 11. Role Split: Metabase vs Rill

| Need | Recommended Tool |
|------|------------------|
| Governed handbook-driven dashboards | Metabase |
| Existing analytics-as-code blueprints | Metabase |
| SQL questions / manual drilling / current team workflow | Metabase |
| Fast slice-dice KPI exploration | Rill Explore |
| Operational cockpit with strong time comparison | Rill Canvas |
| Scheduled digest / Slack-email report | Rill Reports |
| Embedded interactive metrics app | Rill |

### Decision rule

Use:

- **Metabase** when the output is a governed BI asset in the current handbook workflow
- **Rill** when the output is a focused interactive metrics/reporting experience with strong exploration and comparison needs

## 12. Proposed Rollout

### Phase 0: Validate fit

- run Rill in the same compose stack
- publish `fact_orders` + dimensions into `export/rill/current/`
- build `orders_enriched` and one Explore dashboard
- confirm performance, filters, and report value

### Phase 1: Stabilize data contract

- create `publish_rill_assets`
- expose `data_lake/export/rill/current/`
- add targeted Dagster-triggered Rill refresh

### Phase 2: Add Rill project to repo

- create `rill/` subproject
- define 4-5 Rill SQL models
- define 3-4 parent metrics views
- create 1 Explore dashboard
- create 1 Canvas dashboard
- create 1 scheduled report

### Phase 3: Decide distribution model

- if internal analyst tool only: keep local/internal workflow
- if shared product/report surface: evaluate Rill Cloud + embed/service tokens

## 13. Minimal Starter Skeleton

If a spike is implemented, a minimal starting point could look like this:

```yaml
# rill/models/src_fact_orders.yaml
type: model
connector: duckdb
materialize: true
sql: |
  SELECT *
  FROM read_parquet('{{ .env.RILL_EXPORT_ROOT }}/fact_orders.parquet')
```

Repeat the same source-model pattern for `src_dim_channels`, `src_dim_branch_location`, `src_dim_geography`, and `src_dim_staff`.

```yaml
# rill/models/orders_enriched.sql
SELECT
  o.order_id,
  o.order_timestamp,
  date_trunc('day', o.order_timestamp) AS order_date,
  date_trunc('hour', o.order_timestamp) AS hour_start,
  c.channel_name,
  c.channel_category,
  b.branch_location_name,
  g.province,
  g.district,
  s.full_name AS staff_name,
  o.status,
  o.payment_status,
  o.fulfillment_status,
  o.gross_revenue,
  o.net_revenue,
  o.discount_amount,
  o.tax_amount,
  o.total_collected,
  o.first_shipped_at,
  date_diff('hour', o.order_timestamp, o.first_shipped_at) AS hours_to_first_ship,
  o.time_to_complete_hours AS hours_to_complete,
  o.status = 'COMPLETED' AS is_completed,
  o.status = 'CANCELLED' AS is_cancelled,
  o.status = 'OPEN' AS is_open
FROM src_fact_orders o
LEFT JOIN src_dim_channels c ON o.channel_key = c.channel_key
LEFT JOIN src_dim_branch_location b ON o.branch_location_key = b.branch_location_key
LEFT JOIN src_dim_geography g ON o.shipping_geography_key = g.geography_key
LEFT JOIN src_dim_staff s ON o.staff_key = s.staff_key
```

```yaml
# rill/metrics/orders_core_metrics.yaml
version: 1
type: metrics_view
model: orders_enriched
timeseries: hour_start
smallest_time_grain: hour

dimensions:
  - column: channel_name
  - column: channel_category
  - column: branch_location_name
  - column: status
  - column: province
  - column: district
  - column: staff_name

measures:
  - name: orders_count
    display_name: Orders
    expression: count(*)
  - name: net_revenue
    display_name: Net Revenue
    expression: sum(net_revenue)
  - name: completed_orders
    display_name: Completed Orders
    expression: count(*) filter (where is_completed)
  - name: cancelled_orders
    display_name: Cancelled Orders
    expression: count(*) filter (where is_cancelled)
  - name: avg_order_value
    display_name: Average Order Value
    expression: sum(net_revenue) / nullif(count(*), 0)
```

This keeps Rill as a last-mile metrics/reporting layer, not a second transformation engine.

## 14. Non-Goals

This design does **not** recommend:

- replacing Metabase
- moving business logic from dbt into Rill
- pointing Rill at raw or staging data
- making `olap.duckdb` the long-term production dependency for both tools
- forcing Rill into the current Metabase blueprint/deploy workflow

## 15. Sources Read

Official Rill sources reviewed on **2026-04-10**:

- [Rill GitHub repository](https://github.com/rilldata/rill)
- [Get Started with Rill](https://docs.rilldata.com/)
- [How to Install Rill Developer](https://docs.rilldata.com/developers/get-started/install)
- [Rill Cloud vs Rill Developer](https://docs.rilldata.com/developers/deploy/cloud-vs-developer)
- [Deploy Dashboards](https://docs.rilldata.com/developers/deploy/deploy-dashboard)
- [Connect to your Data](https://docs.rilldata.com/developers/build/connectors)
- [External DuckDB](https://docs.rilldata.com/developers/build/connectors/data-source/duckdb)
- [Powering your Metrics View](https://docs.rilldata.com/developers/build/metrics-view/underlying-model)
- [Derived Metrics Views](https://docs.rilldata.com/developers/build/metrics-view/derived-metrics-views)
- [Create Dashboards](https://docs.rilldata.com/developers/build/dashboards)
- [Explore Dashboards](https://docs.rilldata.com/developers/build/dashboards/explore)
- [Canvas Dashboard YAML](https://docs.rilldata.com/reference/project-files/canvas-dashboards)
- [Metrics View YAML](https://docs.rilldata.com/reference/project-files/metrics-views)
- [Report YAML](https://docs.rilldata.com/reference/project-files/reports)
- [Who Can Access Your Data](https://docs.rilldata.com/developers/build/metrics-view/security)
- [Embed Iframe API](https://docs.rilldata.com/integrate/embed-iframe-api)

Local repo references:

- `AGENTS.md`
- `docs/decisions/005-dual-duckdb.md`
- `docs/decisions/008-analytics-as-code.md`
- `docs/architecture/overview.md`
- `scripts/provisioning/bootstrap_serving_views.py`
- `transformation/models/marts/sales/fact_orders.sql`
- `transformation/models/marts/schema.yml`
