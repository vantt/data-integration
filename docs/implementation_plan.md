# Metabase Dashboard Implementation Plan

## Goal

Implement the **Sales Executive Dashboard** in Metabase to visualize the "Sales Metrics & Charts" requirements, including the newly available **Target** data.

## User Review Required

> [!NOTE]
> This plan uses the `metabase-server` MCP tools to programmatically create content. I will need the Metabase Server to be running and accessible via the MCP connection.

## Proposed Changes

### 1. Structure Setup

- **Create Collection**: `Sales Analytics` (to organize all related questions).

### 2. Questions (Cards) Creation

I will create the following Native SQL Questions in the `Sales Analytics` collection:

#### A. Overview & Targets

- **[Card] Daily Sales Trend**: Line chart showing Revenue, Orders, AOV by Day.
- **[Card] Monthly Actual vs Target**: Combo chart comparing `fact_orders` (Actual) vs `fact_targets` (Goal).
  - _Visualization_: Bar for Actual, Line for Target.
  - _SQL Logic_:
    ```sql
    WITH actuals AS (
        SELECT date_trunc('month', created_at) as month, sum(gmv) as actual
        FROM fact_orders
        GROUP BY 1
    ), targets AS (
        SELECT period_date as month, sum(target_val) as target
        FROM fact_targets
        WHERE metric_code = 'gmv' AND is_current = true
        GROUP BY 1
    )
    SELECT
        coalesce(a.month, t.month) as month,
        coalesce(a.actual, 0) as actual,
        coalesce(t.target, 0) as target
    FROM actuals a FULL OUTER JOIN targets t ON a.month = t.month
    ORDER BY month
    ```

#### B. Dimensions

- **[Card] Sales by Channel**: Pie chart of Revenue by Channel.
- **[Card] Top Performing Stores**: Table sorting Stores by Revenue.
- **[Card] Hourly Heatmap**: Pivot table of Orders by Hour vs Day of Week.

### 3. Dashboard Assembly

- **Create Dashboard**: `Sales Executive Dashboard`.
- **Add Cards**: Place the above cards onto the dashboard grid.

## Verification Plan

### Automated Verification

- Use `list_collections` to verify "Sales Analytics" exists.
- Use `list_cards` to verify questions were created.
- Use `get_dashboard_cards` to verify the dashboard is populated.

### Manual Verification

- User to open Metabase UI and check the "Sales Executive Dashboard".
- User to validate the data accuracy of "Actual vs Target".
