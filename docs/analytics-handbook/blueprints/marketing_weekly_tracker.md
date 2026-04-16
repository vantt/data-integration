# 📘 Blueprint: Marketing Weekly Tracker

**Playbook**: [Marketing Weekly Tracker](../playbooks/marketing_weekly_tracker.md)
**Design Spec**: [Marketing Weekly Tracker (Redesign)](../designs/marketing_weekly_tracker.md)

> **Target Collection:** `Marketing & Customers`
> **Role:** Marketing Manager, Brand Manager
> **Archetype:** Operational Cockpit

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Marketing Weekly Tracker

**Description**: Weekly channel performance, customer acquisition, promotions, and social commerce — 3 tabs for focused analysis.

#### Filter: Date Range

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past7days"
}
```

#### Filter: Channel Category

```json metabase-filter
{
  "slug": "channel_category",
  "type": "string/=",
  "default": null
}
```

#### Filter: Brand

```json metabase-filter
{
  "slug": "channel_brand",
  "type": "string/=",
  "default": null
}
```

---

### 📑 Tab: Hieu suat Kenh

#### 📝 Text: Đánh giá hiệu suất kênh tuần — kênh nào hiệu quả, kênh nào cần điều chỉnh?

# Đánh giá hiệu suất kênh tuần — kênh nào hiệu quả, kênh nào cần điều chỉnh?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Weekly Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
WITH this_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND c.channel_category = {{channel_category}}]]
      [[AND c.channel_brand = {{channel_brand}}]]
),
last_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND c.channel_category = {{channel_category}}]]
      [[AND c.channel_brand = {{channel_brand}}]]
)
SELECT
    tw.value as "Weekly Revenue",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Weekly Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Online-Ecom Revenue

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
WITH this_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_category = 'Online-Ecommerce'
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND c.channel_brand = {{channel_brand}}]]
),
last_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_category = 'Online-Ecommerce'
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND c.channel_brand = {{channel_brand}}]]
)
SELECT
    tw.value as "Online-Ecom Revenue",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Online-Ecom Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Offline Revenue

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
WITH this_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_category = 'Offline'
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND c.channel_brand = {{channel_brand}}]]
),
last_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_category = 'Offline'
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND c.channel_brand = {{channel_brand}}]]
)
SELECT
    tw.value as "Offline Revenue",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Offline Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Online-Ecom Share %

```sql
WITH this_week AS (
    SELECT
        ROUND(SUM(CASE WHEN c.channel_category = 'Online-Ecommerce' THEN o.net_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(o.net_revenue), 0), 1) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND c.channel_brand = {{channel_brand}}]]
),
last_week AS (
    SELECT
        ROUND(SUM(CASE WHEN c.channel_category = 'Online-Ecommerce' THEN o.net_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(o.net_revenue), 0), 1) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND c.channel_brand = {{channel_brand}}]]
)
SELECT
    tw.value as "Online-Ecom Share %",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Online-Ecom Share %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 4 }
```

---

#### 📝 Text: Theo dõi xu hướng Online-Ecom vs Offline — momentum và crossover

# Theo dõi xu hướng Online-Ecom vs Offline — momentum và crossover

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Online-Ecom vs Offline Trend

Daily revenue, 2 lines: Online-Ecom vs Offline over 14 days.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    date(o.order_timestamp) as "Date",
    SUM(CASE WHEN c.channel_category = 'Online-Ecommerce' THEN o.net_revenue ELSE 0 END) as "Online-Ecom",
    SUM(CASE WHEN c.channel_category = 'Offline' THEN o.net_revenue ELSE 0 END) as "Offline"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= current_date - INTERVAL '14 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  [[AND c.channel_brand = {{channel_brand}}]]
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Date"],
    "graph.metrics": ["Online-Ecom", "Offline"],
    "graph.colors": ["#509EE3", "#F2A86F"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Online-Ecom": { "number_style": "currency", "currency": "VND", "compact": true },
      "Offline": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Revenue by Brand

Revenue by channel brand (JPC, Fine Japan, The Healthy Us, etc.).

```sql
SELECT
    COALESCE(c.channel_brand, 'Other') as "Brand",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  [[AND c.channel_category = {{channel_category}}]]
GROUP BY 1
ORDER BY 2 DESC
LIMIT 5
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Brand",
    "pie.metric": "Revenue",
    "pie.show_legend": true,
    "pie.colors": { "JPC": "#509EE3", "Fine Japan": "#88BDE6", "The Healthy Us": "#A989C5", "Other": "#F2A86F" },
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Xác định platform hiệu quả — ranking doanh thu và volume

# Xác định platform hiệu quả — ranking doanh thu và volume

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Revenue by Platform

Ranking platforms by revenue.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.platform as "Platform",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  [[AND c.channel_category = {{channel_category}}]]
  [[AND c.channel_brand = {{channel_brand}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Platform"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Orders by Platform

Ranking platforms by order count.

```sql
SELECT
    c.platform as "Platform",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  [[AND c.channel_category = {{channel_category}}]]
  [[AND c.channel_brand = {{channel_brand}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Platform"],
    "graph.metrics": ["Orders"],
    "graph.colors": ["#88BDE6"]
  }
}
```

```json metabase-pos
{ "row": 13, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: So sánh chi tiết kênh WoW — highlight biến động > 20%

# So sánh chi tiết kênh WoW — highlight biến động > 20%

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Performance Table

Detailed channel breakdown with WoW comparison.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
WITH this_week AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        SUM(o.net_revenue) as revenue,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND c.channel_category = {{channel_category}}]]
      [[AND c.channel_brand = {{channel_brand}}]]
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND c.channel_category = {{channel_category}}]]
      [[AND c.channel_brand = {{channel_brand}}]]
    GROUP BY 1
)
SELECT
    tw.channel_name as "Channel",
    tw.orders as "Orders",
    tw.revenue as "Revenue",
    tw.aov as "AOV",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tw.revenue - COALESCE(lw.revenue, 0)) * 100.0 / lw.revenue, 1) END as "WoW Revenue %",
    CASE WHEN COALESCE(lw.orders, 0) = 0 THEN NULL
         ELSE ROUND((tw.orders - COALESCE(lw.orders, 0)) * 100.0 / lw.orders, 1) END as "WoW Orders %"
FROM this_week tw
LEFT JOIN last_week lw ON tw.channel_name = lw.channel_name
ORDER BY tw.revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["WoW Revenue %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["WoW Revenue %"],
        "type": "single",
        "operator": "<=",
        "value": -20,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["WoW Orders %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["WoW Orders %"],
        "type": "single",
        "operator": "<=",
        "value": -20,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true },
      "WoW Revenue %": { "suffix": "%" },
      "WoW Orders %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 8 }
```

---

### 📑 Tab: Khach hang & Acquisition

#### 📝 Text: Đánh giá acquisition tuần — bao nhiêu khách mới và từ đâu?

# Đánh giá acquisition tuần — bao nhiêu khách mới và từ đâu?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: New Customers

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
WITH this_week AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(first_order_date) < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND date(first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "New Customers",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Returning Customers

```sql
WITH this_week AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      AND date(cust.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
),
last_week AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(cust.first_order_date) < date_trunc('week', current_date) - INTERVAL '14 days'
)
SELECT
    tw.value as "Returning Customers",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: New Customer Revenue

```sql
WITH this_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      AND date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(cust.first_order_date) < date_trunc('week', current_date)
),
last_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND date(cust.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "New Customer Revenue",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "New Customer Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: New Customer Share %

```sql
WITH this_week AS (
    SELECT
        ROUND(SUM(CASE WHEN date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
                        AND date(cust.first_order_date) < date_trunc('week', current_date)
                       THEN o.net_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(o.net_revenue), 0), 1) as value
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT
        ROUND(SUM(CASE WHEN date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '14 days'
                        AND date(cust.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
                       THEN o.net_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(o.net_revenue), 0), 1) as value
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "New Customer Share %",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "New Customer Share %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 4 }
```

---

#### 📝 Text: Xác định kênh acquisition hiệu quả nhất

# Xác định kênh acquisition hiệu quả nhất

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: New Customers by Channel

Which channels bring in the most new customers this week?

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(cust.first_order_date) < date_trunc('week', current_date)
  AND date(cust.first_order_date) = date(o.order_timestamp)
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  [[AND c.channel_category = {{channel_category}}]]
  [[AND c.channel_brand = {{channel_brand}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["New Customers"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New vs Returning Revenue

Daily stacked bar showing revenue contribution from new vs returning customers.

```sql
SELECT
    date(o.order_timestamp) as "Date",
    SUM(CASE WHEN date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
                  AND date(cust.first_order_date) < date_trunc('week', current_date)
             THEN o.net_revenue ELSE 0 END) as "New",
    SUM(CASE WHEN date(cust.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
             THEN o.net_revenue ELSE 0 END) as "Returning"
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  [[AND EXISTS (SELECT 1 FROM dim_channels c WHERE c.channel_key = o.channel_key AND c.channel_category = {{channel_category}})]]
  [[AND EXISTS (SELECT 1 FROM dim_channels c WHERE c.channel_key = o.channel_key AND c.channel_brand = {{channel_brand}})]]
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Date"],
    "graph.metrics": ["New", "Returning"],
    "graph.colors": ["#7172AD", "#C2D2E9"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "New": { "number_style": "currency", "currency": "VND", "compact": true },
      "Returning": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Theo dõi xu hướng acquisition 14 ngày — volume và chất lượng

# Theo dõi xu hướng acquisition 14 ngày — volume và chất lượng

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: New Customer Acquisition Trend

Daily new customer count over 14 days with AOV line.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
WITH daily_new AS (
    SELECT
        date(first_order_date) as "Date",
        COUNT(DISTINCT customer_key) as "New Customers"
    FROM dim_customers
    WHERE date(first_order_date) >= current_date - INTERVAL '14 days'
      AND date(first_order_date) < date_trunc('week', current_date)
    GROUP BY 1
),
daily_aov AS (
    SELECT
        date(o.order_timestamp) as "Date",
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id)) END as "New Customer AOV"
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND date(cust.first_order_date) = date(o.order_timestamp)
      AND o.order_timestamp >= current_date - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date)
    GROUP BY 1
)
SELECT
    dn."Date",
    dn."New Customers",
    COALESCE(da."New Customer AOV", 0) as "New Customer AOV"
FROM daily_new dn
LEFT JOIN daily_aov da ON dn."Date" = da."Date"
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Date"],
    "graph.metrics": ["New Customers", "New Customer AOV"],
    "series_settings": {
      "New Customers": { "display": "bar", "color": "#509EE3" },
      "New Customer AOV": { "display": "line", "color": "#7172AD" }
    },
    "graph.x_axis.title_text": "",
    "column_settings": {
      "New Customer AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Customer Type Split

New vs Returning customer count this week.

```sql
SELECT
    CASE WHEN date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
              AND date(cust.first_order_date) < date_trunc('week', current_date)
         THEN 'New' ELSE 'Returning' END as "Type",
    COUNT(DISTINCT o.customer_key) as "Customers"
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Type",
    "pie.metric": "Customers",
    "pie.show_legend": true,
    "pie.colors": { "New": "#7172AD", "Returning": "#C2D2E9" }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 12, "size_x": 6, "size_y": 6 }
```

---

### 📑 Tab: Promotion & Social

#### 📝 Text: Kiểm soát chi phí khuyến mãi — discount có hợp lý?

# Kiểm soát chi phí khuyến mãi — discount có hợp lý?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Rate %

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as "Discount Rate %"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 10, "color": "#84BB4C", "label": "Healthy" },
      { "min": 10, "max": 15, "color": "#F9D45C", "label": "Watch" },
      { "min": 15, "max": 30, "color": "#EF8C8C", "label": "High" }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Discounted Orders %

```sql
WITH this_week AS (
    SELECT ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
                 / NULLIF(COUNT(DISTINCT order_id), 0), 1) as value
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
                 / NULLIF(COUNT(DISTINCT order_id), 0), 1) as value
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "Discounted Orders %",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Discounted Orders %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Avg Discount Amount

```sql
WITH this_week AS (
    SELECT ROUND(AVG(CASE WHEN discount_amount > 0 THEN discount_amount END)) as value
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT ROUND(AVG(CASE WHEN discount_amount > 0 THEN discount_amount END)) as value
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "Avg Discount Amount",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Avg Discount Amount": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Total Discount Given

```sql
WITH this_week AS (
    SELECT COALESCE(SUM(discount_amount), 0) as value
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COALESCE(SUM(discount_amount), 0) as value
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "Total Discount Given",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Total Discount Given": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 4 }
```

---

#### 📝 Text: Đánh giá hiệu suất promotion — promo nào mang lại giá trị?

# Đánh giá hiệu suất promotion — promo nào mang lại giá trị?

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discounted vs Full Price

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    CASE WHEN discount_amount > 0 THEN 'Discounted' ELSE 'Full Price' END as "Type",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
GROUP BY 1
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Type",
    "pie.metric": "Orders",
    "pie.show_legend": true,
    "pie.colors": { "Full Price": "#509EE3", "Discounted": "#F9D45C" }
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Promotion Leaderboard

Top 10 active promotions this week.

**Domain Reference**: [Promotion Performance](../domains/sales.md#14-promotion-performance)

```sql
SELECT
    COALESCE(p.promotion_code, 'Unknown') as "Promo Code",
    COUNT(DISTINCT o.order_id) as "Usage Count",
    SUM(o.net_revenue) as "Revenue",
    ROUND(AVG(COALESCE(o.discount_amount, 0) * 100.0 / NULLIF(o.gross_revenue, 0)), 1) as "Avg Discount %"
FROM fact_orders o
JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND p.promotion_code IS NOT NULL
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 3 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Avg Discount %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "Avg Discount %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 7, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### 📝 Text: Theo dõi hiệu suất Social Commerce — Facebook vs Zalo

# Theo dõi hiệu suất Social Commerce — Facebook vs Zalo

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Social Revenue

Revenue from social commerce channels this week.

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume)

```sql
WITH this_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "Social Revenue",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Social Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Social Orders

```sql
WITH this_week AS (
    SELECT COUNT(DISTINCT o.order_id) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(DISTINCT o.order_id) as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "Social Orders",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 14, "col": 6, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Social AOV

```sql
WITH this_week AS (
    SELECT CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
                ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id)) END as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
                ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id)) END as value
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.value as "Social AOV",
    lw.value as "Previous Week"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Previous Week",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "Social AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 12, "size_x": 6, "size_y": 4 }
```

---

#### ❓ Question: Social Revenue by Platform

Facebook vs Zalo revenue breakdown.

```sql
SELECT
    c.channel_format as "Platform",
    SUM(o.net_revenue) as "Revenue",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_format IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Platform"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3", "#88BDE6"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 10 Products This Week

Best selling products this week.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.product_name as "Product",
    p.brand_name as "Brand",
    SUM(s.quantity) as "Units",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(s.sol_timestamp) < date_trunc('week', current_date)
GROUP BY 1, 2
ORDER BY 4 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Revenue"],
        "type": "range",
        "colors": ["#FFFFFF", "#509EE3"],
        "min_type": "all",
        "max_type": "all",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Footer

Source: fact_orders, dim_channels, dim_customers, dim_promotions · Updated daily · Excludes CANCELLED & Voided

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```
