# Sales Analytics Playbook

## 🎯 Overview

Playbook này cover toàn bộ analytics ecosystem cho Sales domain, bao gồm:

- **Daily Operations** → [sales-blueprint-daily.md]
- **Monthly Reporting** → [sales-blueprint-monthly.md] _(coming soon)_
- **Executive KPIs** → [sales-blueprint-executive.md] _(coming soon)_

## 📊 Business Context

### Target Users

- **Store Managers**: Cần theo dõi daily performance và operations
- **Sales Team**: Cần insights về trends và opportunities
- **Executives**: Cần high-level KPIs và strategic metrics
- **Finance**: Cần revenue tracking và reconciliation

### Update Frequency

- **Real-time**: Order tracking, inventory status
- **Hourly**: Sales performance, conversion rates
- **Daily**: Full metrics refresh, trend analysis
- **Monthly**: Strategic reports, YoY comparisons

## 🎯 Key Performance Indicators

### Revenue Metrics

| Metric                   | Formula                    | Business Rule                | Target          |
| ------------------------ | -------------------------- | ---------------------------- | --------------- |
| **GMV**                  | SUM(order_total)           | Include all confirmed orders | Growth >15% YoY |
| **Net Revenue**          | GMV - Returns - Discounts  | Actual money received        | >90% of GMV     |
| **AOV**                  | Revenue / Orders           | Track pricing power          | >$80            |
| **Revenue per Customer** | Revenue / Unique Customers | Customer value               | >$200/year      |

📘 **Blueprint Implementation**: [sales-blueprint-daily.md#revenue-section]

### Conversion Metrics

| Metric                   | Formula                         | Business Rule      | Target   |
| ------------------------ | ------------------------------- | ------------------ | -------- |
| **Conversion Rate**      | Orders / Visitors × 100%        | From GA4/tracking  | >2.5%    |
| **Cart Abandonment**     | Abandoned / Created × 100%      | Draft vs Confirmed | <30%     |
| **Items per Order**      | Total Items / Orders            | Basket size        | >3 items |
| **Repeat Purchase Rate** | Repeat Customers / Total × 100% | Within 90 days     | >40%     |

📘 **Blueprint Implementation**: [sales-blueprint-daily.md#conversion-section]

## 📈 Dashboard Designs

### 1. Daily Sales Dashboard

**Purpose**: Real-time monitoring for store operations

**Layout**:

```
┌─────────────────────────┬─────────────────────────┐
│ Revenue Today (Scalar)  │ Orders Today (Scalar)   │
├─────────────────────────┴─────────────────────────┤
│ Hourly Sales Trend (Line Chart)                   │
├───────────────────────────────────────────────────┤
│ Sales by Channel (Pie)  │ Top Products (Table)    │
└─────────────────────────┴─────────────────────────┘
```

**Key Features**:

- Auto-refresh every 15 minutes
- Mobile-responsive design
- Drill-down to order details
- Alert thresholds for anomalies

### 2. Monthly Executive Dashboard

**Purpose**: Strategic overview for leadership

**Layout**:

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ MTD Revenue │ MTD Growth  │ MTD Orders  │ Avg AOV     │
├─────────────┴─────────────┴─────────────┴─────────────┤
│ Monthly Trend vs Last Year (Combo Chart)              │
├─────────────────────────┬─────────────────────────────┤
│ Revenue by Region (Map) │ Channel Performance (Table) │
└─────────────────────────┴─────────────────────────────┘
```

## 💾 Data Requirements

### Source Tables

| Table           | Update Frequency | Key Fields                           | Data Quality Checks |
| --------------- | ---------------- | ------------------------------------ | ------------------- |
| `fact_orders`   | Real-time        | order_id, total, status, created_on  | No nulls in total   |
| `dim_customers` | Daily            | customer_id, segment, lifetime_value | Valid email format  |
| `dim_products`  | Daily            | product_id, category, price          | Price > 0           |
| `dim_locations` | Weekly           | location_id, type, region            | Valid coordinates   |

### Data Freshness SLA

- Orders: < 5 minutes delay
- Customer data: < 1 hour delay
- Product catalog: < 24 hours delay

## 🔧 SQL Library

### Daily Revenue Query

```sql
-- Tested on DuckDB, ~200ms for 1M rows
WITH daily_metrics AS (
    SELECT
        DATE(created_on) as order_date,
        COUNT(*) as order_count,
        SUM(total) as gross_revenue,
        SUM(total - COALESCE(discount_amount, 0)) as net_revenue,
        AVG(total) as avg_order_value,
        COUNT(DISTINCT customer_id) as unique_customers,
        SUM(total_tax) as tax_collected,
        SUM(total_discount) as discounts_given
    FROM fact_orders
    WHERE status = 'confirmed'
        AND created_on >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(created_on)
)
SELECT
    order_date,
    order_count,
    gross_revenue,
    net_revenue,
    avg_order_value,
    unique_customers,
    tax_collected,
    discounts_given,
    -- Add running totals
    SUM(net_revenue) OVER (
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as running_total
FROM daily_metrics
ORDER BY order_date DESC;
```

### Top Products of the Day

```sql
SELECT
    p.product_name,
    SUM(oli.quantity) as units_sold,
    SUM(oli.line_amount) as revenue
FROM order_line_items oli
JOIN products p ON oli.product_id = p.product_id
JOIN orders o ON oli.order_id = o.order_id
WHERE DATE(o.created_on) = CURRENT_DATE - INTERVAL '1 day'
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 10
```

### Hourly Pattern Analysis

```sql
-- Heatmap data for operational planning
SELECT
    EXTRACT(HOUR FROM created_on) as hour_of_day,
    CASE EXTRACT(DOW FROM created_on)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_of_week,
    COUNT(*) as order_count,
    SUM(total) as revenue,
    AVG(total) as avg_order_value
FROM fact_orders
WHERE created_on >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY hour_of_day, EXTRACT(DOW FROM created_on)
ORDER BY EXTRACT(DOW FROM created_on), hour_of_day;
```

### Monthly Business Review (KPIs)

```sql
SELECT
    DATE_TRUNC('month', created_on) as month,
    COUNT(*) as total_orders,
    SUM(total) as revenue,
    COUNT(DISTINCT customer_id) as customers,
    AVG(total) as aov,
    SUM(total_discount) as discounts,
    COUNT(CASE WHEN return_status != 'unreturned' THEN 1 END) as returns
FROM fact_orders
WHERE created_on >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')
GROUP BY month
ORDER BY month
```

### Channel Performance

```sql
-- Compare channel effectiveness
WITH channel_metrics AS (
    SELECT
        source_channel,
        COUNT(DISTINCT order_id) as orders,
        COUNT(DISTINCT customer_id) as customers,
        SUM(total) as revenue,
        AVG(total) as aov
    FROM fact_orders
    WHERE created_on >= DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY source_channel
)
SELECT
    source_channel,
    orders,
    customers,
    revenue,
    aov,
    ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2) as revenue_pct,
    ROUND(orders::FLOAT / customers, 2) as orders_per_customer
FROM channel_metrics
ORDER BY revenue DESC;
```

### Sales by Location

```sql
-- Revenue by Region/Store
SELECT
    l.region,
    l.location_name,
    COUNT(DISTINCT o.order_id) as orders,
    SUM(o.total) as revenue,
    AVG(o.total) as aov
FROM fact_orders o
JOIN dim_locations l ON o.location_id = l.location_id
GROUP BY l.region, l.location_name
ORDER BY revenue DESC
```

### Detailed Revenue by Location (Map)

```sql
SELECT
    l.location_name,
    l.city,
    l.district,
    COUNT(o.order_id) as orders,
    SUM(o.total) as revenue
FROM orders o
JOIN locations l ON o.location_id = l.location_id
GROUP BY l.location_id, l.location_name, l.city, l.district
```

### Payment Analysis

```sql
-- Payment Methods Distribution
SELECT
    pm.payment_method_name,
    COUNT(*) as transaction_count,
    SUM(p.amount) as total_amount
FROM payments p
JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
WHERE p.status = 'completed'
GROUP BY pm.payment_method_name
```

```sql
-- Payment Status Tracking
SELECT
    payment_status,
    COUNT(*) as order_count,
    SUM(total) as total_amount,
    AVG(total) as avg_order_value
FROM orders
GROUP BY payment_status
```

### Discount & Promotion Analysis

```sql
-- Discount Impact Over Time
SELECT
    DATE_TRUNC('day', created_on) as date,
    COUNT(*) as total_orders,
    SUM(CASE WHEN total_discount > 0 THEN 1 ELSE 0 END) as discounted_orders,
    SUM(total_discount) as total_discounts,
    AVG(total_discount * 100.0 / NULLIF(total, 0)) as avg_discount_pct
FROM orders
GROUP BY date
ORDER BY date
```

```sql
-- Promotion Performance
SELECT
    pr.promotion_name,
    COUNT(DISTINCT o.order_id) as orders_used,
    SUM(pr.discount_amount) as total_discount,
    SUM(o.total) as revenue_with_promo,
    AVG(pr.discount_amount) as avg_discount_per_order
FROM orders o
JOIN promotion_redemptions pr ON o.order_id = pr.order_id
GROUP BY pr.promotion_id, pr.promotion_name
ORDER BY total_discount DESC
```

## 🚀 Implementation Notes

### Best Practices

1. **Caching**: Enable 1-hour cache for executive dashboards
2. **Permissions**: Use Collection-based access control
3. **Filters**: Always include date range and location filters
4. **Mobile**: Test all dashboards on mobile devices

### Common Pitfalls

- Don't aggregate GMV and Net Revenue (they measure different things)
- Always filter by order status (exclude cancelled/draft)
- Use proper timezone conversion for global operations
- Consider currency conversion for multi-country

### Performance Tips

- Pre-aggregate daily/monthly data in dbt models
- Use incremental refresh for large fact tables
- Index on created_on, customer_id, location_id
- Partition by month for historical data

## 📚 Related Resources

- [Financial Analytics Playbook](finance-playbook.md)
- [Customer Analytics Playbook](customer-playbook.md)
- [Metabase Best Practices](guides/metabase-concepts.md)
- [SQL Style Guide](guides/sql-style-guide.md)

## 🔄 Change Log

- 2024-01: Initial version
- 2024-02: Added hourly pattern analysis
- 2024-03: Updated for DuckDB migration
