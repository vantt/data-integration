# 📘 Blueprint: Customer Intelligence Monthly

> **Target Collection:** `Marketing & Customers`
> **Role:** CEO, Marketing Manager, Sales Ops
> **Archetype:** Operational Cockpit + Analytical

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Intelligence Monthly

**Description**: Monthly deep-dive — customer value analysis, segment migration, purchase behavior, channel effectiveness by customer type, product affinity, and a comprehensive customer health scorecard.

---

#### ❓ Question: Total Customers (With Orders)

Total customers who have placed at least one order.

```sql
SELECT COUNT(*) as "Total Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Customer LTV

Cumulative lifetime value across all customers.

```sql
SELECT SUM(lifetime_value) as "Total LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total LTV": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 3, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Avg LTV per Customer

Average lifetime value per customer.

```sql
SELECT ROUND(AVG(lifetime_value), 0) as "Avg LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Avg LTV": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: New Customers (Last Month)

Customers acquired in the previous calendar month.

```sql
SELECT COUNT(*) as "New (Last Month)"
FROM dim_customers
WHERE created_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND created_at < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Revenue from Top 20% Customers

Revenue concentration — what % of revenue comes from top 20% of customers by LTV?

```sql
WITH ranked AS (
    SELECT
        lifetime_value,
        NTILE(5) OVER (ORDER BY lifetime_value DESC) as quintile
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
)
SELECT
    ROUND(
        SUM(CASE WHEN quintile = 1 THEN lifetime_value ELSE 0 END) * 100.0
        / NULLIF(SUM(lifetime_value), 0), 1
    ) as "Top 20% Revenue Share %"
FROM ranked
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Top 20% Revenue Share %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: One-Time Buyer Rate

Percentage of customers who only ever placed 1 order — conversion opportunity.

```sql
SELECT
    ROUND(
        COUNT(CASE WHEN total_orders_count = 1 THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    ) as "One-Time %"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "One-Time %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Customer Value Distribution

Histogram of customer lifetime value — understand the shape of your customer base.

```sql
SELECT
    CASE
        WHEN lifetime_value = 0 THEN '0 (No Revenue)'
        WHEN lifetime_value < 500000 THEN '< 500K'
        WHEN lifetime_value < 1000000 THEN '500K - 1M'
        WHEN lifetime_value < 2000000 THEN '1M - 2M'
        WHEN lifetime_value < 5000000 THEN '2M - 5M'
        WHEN lifetime_value < 10000000 THEN '5M - 10M'
        ELSE '10M+'
    END as "LTV Range",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total LTV",
    ROUND(
        COUNT(*) * 100.0 / NULLIF(
            (SELECT COUNT(*) FROM dim_customers WHERE customer_id != 'Unknown' AND total_orders_count > 0), 0
        ), 1
    ) as "% of Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
GROUP BY 1
ORDER BY MIN(lifetime_value)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["LTV Range"],
    "graph.metrics": ["Customers"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Customer Segment Revenue Contribution

Revenue share by customer segment — understand value concentration.

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total Revenue",
    ROUND(
        SUM(lifetime_value) * 100.0 / NULLIF(
            (SELECT SUM(lifetime_value) FROM dim_customers WHERE customer_id != 'Unknown'), 0
        ), 1
    ) as "Revenue %",
    ROUND(AVG(total_orders_count), 1) as "Avg Orders",
    ROUND(AVG(recency_days), 0) as "Avg Recency"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Total Revenue": { "number_style": "currency", "currency": "VND" },
      "Revenue %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Monthly Customer Acquisition vs Churn (6M)

Net customer growth — new customers acquired vs customers entering churned state each month.

```sql
WITH new_customers AS (
    SELECT
        date_trunc('month', created_at)::date as month,
        COUNT(*) as acquired
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND created_at < date_trunc('month', current_date)
      AND customer_id != 'Unknown'
    GROUP BY 1
),
churned_customers AS (
    SELECT
        date_trunc('month', last_order_date + INTERVAL '90' DAY)::date as month,
        COUNT(*) as churned
    FROM dim_customers
    WHERE customer_status = 'Churned'
      AND (last_order_date + INTERVAL '90' DAY) >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND (last_order_date + INTERVAL '90' DAY) < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(n.month, c.month) as month,
    COALESCE(n.acquired, 0) as "Acquired",
    COALESCE(c.churned, 0) as "Churned",
    COALESCE(n.acquired, 0) - COALESCE(c.churned, 0) as "Net Growth"
FROM new_customers n
FULL OUTER JOIN churned_customers c ON n.month = c.month
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Acquired", "Churned", "Net Growth"],
    "graph.colors": ["#84BB4C", "#EF8C8C", "#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Customer Channel Preference Matrix

Which channels do different customer segments prefer? Helps target marketing spend.

```sql
SELECT
    cust.customer_segment as "Segment",
    ch.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.net_revenue) as "Revenue",
    COUNT(DISTINCT o.customer_key) as "Unique Customers"
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY
    CASE cust.customer_segment WHEN 'VIP' THEN 1 WHEN 'Loyal' THEN 2 ELSE 3 END,
    4 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": true,
    "table.pivot_column": "Channel",
    "table.cell_column": "Revenue",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Top Products by Customer Segment (VIP)

What do VIP customers buy most? Guide product strategy and VIP exclusive offers.

```sql
SELECT
    p.product_name as "Product",
    COUNT(DISTINCT s.order_id) as "Orders",
    SUM(s.quantity) as "Units Sold",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
JOIN dim_customers cust ON o.customer_key = cust.customer_key
JOIN dim_products p ON s.product_key = p.product_key
WHERE cust.customer_segment = 'VIP'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 4 DESC
LIMIT 15
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top Products for First-Time Buyers

What products do new customers buy first? Guide acquisition funnels and landing pages.

```sql
SELECT
    p.product_name as "Product",
    COUNT(DISTINCT s.order_id) as "First Orders",
    SUM(s.quantity) as "Units",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
JOIN dim_customers cust ON o.customer_key = cust.customer_key
JOIN dim_products p ON s.product_key = p.product_key
WHERE date_trunc('month', o.order_timestamp) = date_trunc('month', cust.first_order_date)
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 21, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Customer AOV by Segment Trend (6M)

How does average order value trend across segments? Detect upsell opportunities or spending decline.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as month,
    cust.customer_segment as segment,
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
  AND cust.total_orders_count > 0
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["aov"],
    "graph.group_by": ["segment"],
    "graph.colors": ["#EF8C8C", "#F9A825", "#84BB4C"]
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New Customer Quality Trend (6M)

Are new customers getting better or worse? Track first-order AOV and 30-day repeat rate by cohort.

```sql
WITH first_orders AS (
    SELECT
        date_trunc('month', c.first_order_date)::date as cohort_month,
        c.customer_key,
        o.net_revenue as first_order_value
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
        AND o.order_timestamp = c.first_order_date
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND c.first_order_date < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      AND o.status NOT IN ('CANCELLED', 'Voided')
),
repeat_30d AS (
    SELECT
        fo.cohort_month,
        fo.customer_key
    FROM first_orders fo
    JOIN fact_orders o2 ON fo.customer_key = o2.customer_key
        AND o2.order_timestamp > (SELECT MIN(first_order_date) FROM dim_customers WHERE customer_key = fo.customer_key)
        AND o2.order_timestamp <= (SELECT MIN(first_order_date) + INTERVAL '30 days' FROM dim_customers WHERE customer_key = fo.customer_key)
        AND o2.status NOT IN ('CANCELLED', 'Voided')
)
SELECT
    fo.cohort_month as month,
    COUNT(DISTINCT fo.customer_key) as "New Customers",
    ROUND(AVG(fo.first_order_value), 0) as "Avg First Order",
    ROUND(
        COUNT(DISTINCT r.customer_key) * 100.0 / NULLIF(COUNT(DISTINCT fo.customer_key), 0), 1
    ) as "30-day Repeat %"
FROM first_orders fo
LEFT JOIN repeat_30d r ON fo.customer_key = r.customer_key AND fo.cohort_month = r.cohort_month
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Avg First Order": { "number_style": "currency", "currency": "VND" },
      "30-day Repeat %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 27, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Customer Health Scorecard

Comprehensive health view per segment: active rate, repeat rate, avg LTV, avg orders, churn risk.

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Customers",
    ROUND(COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Active %",
    ROUND(COUNT(CASE WHEN customer_status = 'At Risk' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "At Risk %",
    ROUND(COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Churned %",
    ROUND(COUNT(CASE WHEN total_orders_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Repeat %",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(total_orders_count), 1) as "Avg Orders",
    ROUND(AVG(recency_days), 0) as "Avg Recency",
    ROUND(AVG(lifespan_days), 0) as "Avg Lifespan"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
GROUP BY 1
ORDER BY
    CASE customer_segment WHEN 'VIP' THEN 1 WHEN 'Loyal' THEN 2 ELSE 3 END
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Avg LTV": { "number_style": "currency", "currency": "VND" },
      "Active %": { "suffix": "%" },
      "At Risk %": { "suffix": "%" },
      "Churned %": { "suffix": "%" },
      "Repeat %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### ❓ Question: Customer Loyalty Point Distribution

Loyalty points balance across customer segments — identify engagement levels.

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Customers",
    SUM(loyalty_point) as "Total Points",
    ROUND(AVG(loyalty_point), 0) as "Avg Points",
    MAX(loyalty_point) as "Max Points"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND loyalty_point > 0
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 38, "col": 0, "size_x": 9, "size_y": 5 }
```

#### ❓ Question: Customer Gender Distribution by Segment

Demographic breakdown to inform marketing persona targeting.

```sql
SELECT
    customer_segment as "Segment",
    COALESCE(NULLIF(sex, ''), 'Unknown') as "Gender",
    COUNT(*) as "Customers",
    ROUND(
        COUNT(*) * 100.0 / NULLIF(
            SUM(COUNT(*)) OVER (PARTITION BY customer_segment), 0
        ), 1
    ) as "% of Segment"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
GROUP BY 1, 2
ORDER BY
    CASE customer_segment WHEN 'VIP' THEN 1 WHEN 'Loyal' THEN 2 ELSE 3 END,
    3 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "% of Segment": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 38, "col": 9, "size_x": 9, "size_y": 5 }
```
