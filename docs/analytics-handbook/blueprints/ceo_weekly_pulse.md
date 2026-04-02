# CEO Weekly Pulse Blueprint (Redesign)

**Design Spec**: [CEO Weekly Pulse (Redesign)](../designs/ceo_weekly_pulse.md)
**Playbook**: [CEO Weekly Pulse](../playbooks/ceo_weekly_pulse.md)

Redesigned dashboard with 3 tabs: Doanh thu & Target, Kenh ban hang, Khach hang & Canh bao. Features WoW comparisons on all KPIs, progress-toward-goal for MTD target, donut + grouped bar for channels, gauge for health metrics, and conditional formatting. 5-minute Monday morning CEO check-in.

> **Business Constraint:** Exclude US channel (internal/B2B, 100% discount) from all metrics.

## Collection: Executive

### Dashboard: CEO Weekly Pulse

**Description**: 5-minute Monday morning check-in — revenue pace, channel shifts, customer health, and operational flags. 3 tabs for focused scanning.

---

### Tab: Doanh thu & Target

#### 📝 Text: CEO Weekly Pulse — Tuan qua kinh doanh co on-track khong?

# CEO Weekly Pulse — Tuan qua kinh doanh co on-track khong?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Tien do target thang

# Tien do target thang

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Xu huong doanh thu (14 ngay)

# Xu huong doanh thu (14 ngay)

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Hero metric with WoW comparison.

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "Net Revenue",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Gross Revenue

**Domain Reference**: [Gross Revenue](../domains/sales.md#1-gross-revenue-gmv) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "Gross Revenue",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "Gross Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "Total Orders",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: AOV

**Domain Reference**: [AOV](../domains/sales.md#5-aov-average-order-value) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "AOV",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### Question: MTD Revenue vs Target

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) — Progress bar showing % of monthly target achieved.

```sql
WITH mtd_actual AS (
    SELECT COALESCE(SUM(net_revenue), 0) as mtd_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date)
      AND order_timestamp < current_date
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date <= current_date
      AND cycle_end_date >= current_date
)
SELECT
    a.mtd_revenue as "MTD Revenue"
FROM mtd_actual a
```

```json metabase-viz
{
  "display": "progress",
  "visualization_settings": {
    "progress.goal": 4000000000,
    "progress.color": "#84BB4C",
    "column_settings": {
      "MTD Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 12, "size_y": 3 }
```

#### Question: Pace Index

Revenue pace indicator: MTD Actual vs expected pace. >1.0 = Ahead, <1.0 = Behind.

```sql
WITH mtd_actual AS (
    SELECT COALESCE(SUM(net_revenue), 0) as mtd_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date)
      AND order_timestamp < current_date
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date <= current_date
      AND cycle_end_date >= current_date
)
SELECT
    CASE WHEN t.target_revenue = 0 THEN NULL
         ELSE ROUND(
           a.mtd_revenue / (
             t.target_revenue
             * EXTRACT(DAY FROM current_date)
             / EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))
           ), 2)
    END as "Pace Index"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 0.8, "color": "#EF8C8C", "label": "Behind" },
      { "min": 0.8, "max": 1.0, "color": "#F9D45C", "label": "On Track" },
      { "min": 1.0, "max": 1.5, "color": "#84BB4C", "label": "Ahead" }
    ]
  }
}
```

```json metabase-pos
{ "row": 5, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### Question: Daily Net Revenue (14 Days)

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Area chart showing 14-day revenue trend.

```sql
SELECT
    date(order_timestamp) as order_date,
    SUM(net_revenue) as revenue
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= current_date - INTERVAL '14 days'
  AND order_timestamp < current_date
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["order_date"],
    "graph.metrics": ["revenue"],
    "graph.colors": ["#509EE3"],
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### Tab: Kenh ban hang

#### 📝 Text: Phan bo doanh thu theo kenh

# Phan bo doanh thu theo kenh

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Top kenh ban hang

# Top kenh ban hang

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Revenue by Channel Category

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Donut chart: Ecommerce / Offline / Internal split.

```sql
SELECT
    c.channel_category as "Channel Category",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Channel Category",
    "pie.metric": "Revenue",
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside",
    "pie.colors": {
      "Ecommerce": "#509EE3",
      "Offline": "#88BDE6",
      "Internal": "#A989C5"
    },
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Channel Category WoW Comparison

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Grouped bar: this week vs last week side-by-side.

```sql
WITH this_week AS (
    SELECT
        c.channel_category,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_category,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_category, lw.channel_category) as "Channel",
    COALESCE(tw.revenue, 0) as "This Week",
    COALESCE(lw.revenue, 0) as "Last Week"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_category = lw.channel_category
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["This Week", "Last Week"],
    "graph.colors": ["#509EE3", "#C2D2E9"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "This Week": { "number_style": "currency", "currency": "VND", "compact": true },
      "Last Week": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### Question: Top Channels by Revenue

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Horizontal bar ranking channels by revenue.

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 8
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```

#### Question: Channel Performance Table

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Detail table with WoW % change and conditional formatting.

```sql
WITH this_week AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_name, lw.channel_name) as "Channel",
    COALESCE(tw.orders, 0) as "Orders",
    COALESCE(tw.revenue, 0) as "Revenue",
    COALESCE(lw.orders, 0) as "LW Orders",
    COALESCE(lw.revenue, 0) as "LW Revenue",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.revenue, 0) - lw.revenue) * 100.0 / lw.revenue, 1) END as "Revenue WoW %"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_name = lw.channel_name
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Revenue WoW %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Revenue WoW %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "LW Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "Revenue WoW %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### Tab: Khach hang & Canh bao

#### 📝 Text: Suc khoe khach hang

# Suc khoe khach hang

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Xu huong New vs Returning (14 ngay)

# Xu huong New vs Returning (14 ngay)

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Canh bao van hanh

# Canh bao van hanh

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: New Customers

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) — Hero: new customer count with WoW.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(first_order_date) < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND date(first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "New Customers",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Returning Revenue %

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) — Gauge: % revenue from returning customers. Healthy > 60%.

```sql
SELECT
    ROUND(
        SUM(CASE WHEN date(c.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days' THEN o.net_revenue ELSE 0 END) * 100.0
        / NULLIF(SUM(o.net_revenue), 0), 1
    ) as "Returning Revenue %"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 40, "color": "#EF8C8C", "label": "Low" },
      { "min": 40, "max": 60, "color": "#F9D45C", "label": "Warning" },
      { "min": 60, "max": 100, "color": "#84BB4C", "label": "Healthy" }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Returning Customers

Count of returning customers this week with WoW comparison.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT o.customer_key) as val
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      AND date(c.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
),
last_week AS (
    SELECT COUNT(DISTINCT o.customer_key) as val
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(c.first_order_date) < date_trunc('week', current_date) - INTERVAL '14 days'
)
SELECT
    tw.val as "Returning Customers",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### Question: New vs Returning Orders (14 Days)

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) — Stacked bar: daily New vs Returning order count.

```sql
SELECT
    date(o.order_timestamp) as order_date,
    CASE
        WHEN date(c.first_order_date) = date(o.order_timestamp) THEN 'New'
        ELSE 'Returning'
    END as customer_type,
    COUNT(DISTINCT o.order_id) as orders
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND o.order_timestamp >= current_date - INTERVAL '14 days'
  AND o.order_timestamp < current_date
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["order_date", "customer_type"],
    "graph.metrics": ["orders"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Orders",
    "series_settings": {
      "New": { "color": "#88BDE6" },
      "Returning": { "color": "#509EE3" }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### Question: Cancelled Orders

Cancelled order count with WoW comparison. Flag if significant increase.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status = 'CANCELLED'
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status = 'CANCELLED'
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "Cancelled Orders",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Return Count

Return count with WoW comparison. Flag RED if > 2x previous week.

```sql
WITH
this_week AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "Returns",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Discount Rate

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact) — Gauge: discount as % of Gross Revenue. RED if > 15%.

```sql
SELECT
    ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as "Discount Rate %"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 10, "color": "#84BB4C", "label": "Normal" },
      { "min": 10, "max": 15, "color": "#F9D45C", "label": "High" },
      { "min": 15, "max": 30, "color": "#EF8C8C", "label": "Alert" }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 12, "size_x": 6, "size_y": 3 }
```
