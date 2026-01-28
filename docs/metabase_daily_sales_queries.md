# Daily Sales Performance Dashboard - Setup Guide

Since the programmatic creation of dashboard elements is currently unavailable, please use the following SQL queries to create the "**Daily Sales Performance**" dashboard content in Metabase.

> **Note**: These queries use `current_date` to show data for "Today". If your data is not up-to-date (e.g. testing with past data), replace `current_date` with a specific date like `'2026-01-26'` or use a Metabase Date Filter `{{date}}`.

## 1. Daily Metrics (Review, Orders, AOV, Customers)

**Visualization**: Number or Scalar
**SQL**:

```sql
SELECT
    count(distinct o.order_id) as "Total Orders",
    coalesce(sum(o.gmv), 0) as "Total Revenue",
    case when count(distinct o.order_id) = 0 then 0
         else sum(o.gmv) / count(distinct o.order_id) end as "AOV",
    count(distinct case when date(c.first_order_date) = current_date then o.customer_key end) as "New Customers",
    count(distinct case when date(c.first_order_date) < current_date then o.customer_key end) as "Return Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
```

## 2. Hourly Metrics (Today vs Yesterday)

**Visualization**: Line Chart

- **X-axis**: `hour_of_day`
- **Y-axis**: `sales_today`, `sales_yesterday`
  **SQL**:

```sql
WITH current_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_today
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
    GROUP BY 1
),
previous_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_yesterday
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(c.hour_of_day, p.hour_of_day) as hour_of_day,
    COALESCE(c.sales_today, 0) as sales_today,
    COALESCE(p.sales_yesterday, 0) as sales_yesterday
FROM current_sales c
FULL OUTER JOIN previous_sales p ON c.hour_of_day = p.hour_of_day
ORDER BY 1
```

## 3. Top Selling Channels (Today)

**Visualization**: Table or Bar Chart
**SQL**:

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

## 4. Top Selling Products (Today)

**Visualization**: Table
**SQL**:

```sql
SELECT
    p.product_name as "Product",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20
```
