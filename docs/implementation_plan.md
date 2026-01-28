# Metabase Dashboard Implementation Plan

## Goal

Implement the **Sales Executive Dashboard** in Metabase to visualize the "Sales Metrics & Charts" requirements, including the newly available **Target** data.

## User Review Required

> [!NOTE]
> This plan uses the `metabase` MCP tools to programmatically create content. I will need the Metabase Server to be running and accessible via the MCP connection.

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
        WHERE metric_code = 'gmv'
        -- Note: 'is_current' filter removed (Schema V1)
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

- Use the **Metabase Automation Skill** (`usage_example.js`) to verify connection and basic resource creation.
- Check Metadata in Metabase admin manually.

### Phase 4: Daily Sales Performance

Dashboard: `Daily Sales Performance`

#### 2.1 Metrics (Single Row / Multiple Cards)

- **Source**: `fact_orders` & `dim_customers`.
- **Filters**: `order_timestamp` = Today.
- **Metrics**:
  - Revenue (GMV)
  - Orders Count
  - AOV (GMV / Orders)
  - New Customers (First order today)
  - Return Customers (Active today but first order < today)

#### 2.2 Hourly Sales Trend (Line Chart)

- **Comparison**: Today vs Yesterday.
- **X-Axis**: Hour of Day (0-23).
- **Y-Axis**: GMV.
- **Series**: "Today", "Yesterday".

#### 2.3 Top Selling Tables

- **Channels**: Group by `channel_name` (from `dim_channels`), Sort by GMV DESC.
- **Products**: Group by `product_name` (from `dim_products`), Sort by Revenue DESC.

### Manual Verification

- User to open Metabase UI and check the "Sales Executive Dashboard".
- User to validate the data accuracy of "Actual vs Target".
