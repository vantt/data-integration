# Customer Operational Dashboard Blueprint [Retail]

**Design Spec**: [Customer Operational Dashboard (Redesign)](../designs/customer_operational_dashboard.md)
**Playbook**: [Customer Operational Dashboard](../playbooks/customer_operational_dashboard.md)
**Scope**: scope_retail (`customer_type = 'RETAIL'` + `is_sales_channel = true`)
**Layer**: L2 - Marketing & Customers

> **SCOPE (2026-04-19):** Dashboard này focus vào **retail customers** (`customer_type = 'RETAIL'`).
> Customer ops metrics (MAU, Retention, Churn, At Risk) áp dụng cho B2C customers.
> B2B customer management có logic khác (contract-based, credit terms).
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Redesigned dashboard with 3 tabs, integrated MoM comparisons, donuts for composition, gauge for active rate, conditional formatting on watchlists, combo chart for acquisition. Daily operational cockpit for Customer Success / Sales Ops. **Focus: Retail customers only.**

## 📂 Collection: Marketing & Customers

> **Database:** Sapo

### 🖥️ Dashboard: Customer Operational [Retail]

**Description**: Daily operational cockpit for **retail customers** — customer health KPIs with rolling comparisons, segment & status composition, acquisition trends with MoM growth, channel & geographic analysis, and actionable watchlists for VIP care, churn prevention, and recovery campaigns. 3 tabs: Tong quan, Kenh & Dia ly, Watchlist & Hanh dong.

---

### 📑 Tab: Tong quan

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 30 ngày gần nhất: ' ||
  strftime(current_date - 29, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  So sánh: ' ||
  strftime(current_date - 59, '%d/%m/%Y') || ' – ' || strftime(current_date - 30, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Danh gia suc khoe customer base — MAU, acquisition, at-risk, churn

# Danh gia suc khoe customer base — MAU, acquisition, at-risk, churn

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Kiem tra phan bo trang thai va segment — dau la diem nong?

# Kiem tra phan bo trang thai va segment — dau la diem nong?

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Theo doi xu huong 6 thang — growth quality va MAU trajectory

# Theo doi xu huong 6 thang — growth quality va MAU trajectory

```json metabase-pos
{"row": 13, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: MAU (Monthly Active Customers)

**Domain Reference**: [MAU](../domains/customer.md#4-monthly-active-users-mau) — Hero metric with rolling 30-day comparison. **Scope: Retail only.**

```sql
WITH
current_mau AS (
    SELECT COUNT(DISTINCT o.customer_key) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
prev_mau AS (
    SELECT COUNT(DISTINCT o.customer_key) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
)
SELECT cm.val as "MAU", pm.val as "30 ngay truoc"
FROM current_mau cm, prev_mau pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":6, "size_y":3}
```

#### ❓ Question: New Customers (MTD)

Supporting KPI — new customers this month vs last month.

```sql
WITH
this_month AS (
    SELECT COUNT(*) as val
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date)
      AND customer_id != 'Unknown'
),
last_month AS (
    SELECT COUNT(*) as val
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND created_at < date_trunc('month', current_date)
      AND customer_id != 'Unknown'
)
SELECT tm.val as "New Customers", lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":6, "size_x":4, "size_y":3}
```

#### ❓ Question: At Risk Customers

Supporting KPI — customers with no purchase in 31-90 days.

```sql
SELECT COUNT(*) as "At Risk"
FROM dim_customers
WHERE customer_status = 'At Risk'
  AND customer_id != 'Unknown'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row": 3, "col":10, "size_x":4, "size_y":3}
```

#### ❓ Question: Churned Customers

Supporting KPI — customers with no purchase for over 90 days.

```sql
SELECT COUNT(*) as "Churned"
FROM dim_customers
WHERE customer_status = 'Churned'
  AND customer_id != 'Unknown'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

#### ❓ Question: Customer Status Distribution

Donut — Active / At Risk / Churned composition.

```sql
SELECT
    customer_status as "Status",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND customer_status IN ('Active', 'At Risk', 'Churned')
GROUP BY 1
ORDER BY
    CASE customer_status
        WHEN 'Active' THEN 1
        WHEN 'At Risk' THEN 2
        WHEN 'Churned' THEN 3
    END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_data_labels": true,
    "pie.colors": {
      "Active": "#84BB4C",
      "At Risk": "#F9D45C",
      "Churned": "#EF8C8C"
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":0, "size_x":6, "size_y":6}
```

#### ❓ Question: Customer Segment Distribution

Donut — VALUE_VIP / GOLD / SILVER / BRONZE value composition.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY
    CASE value_group
        WHEN 'VALUE_VIP' THEN 1
        WHEN 'VALUE_GOLD' THEN 2
        WHEN 'VALUE_BRONZE' THEN 3
    END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_data_labels": true,
    "pie.colors": {
      "VALUE_VIP": "#7172AD",
      "VALUE_GOLD": "#509EE3",
      "VALUE_SILVER": "#88BDE6",
      "VALUE_BRONZE": "#C2D2E9"
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":6, "size_x":6, "size_y":6}
```

#### ❓ Question: Active Rate

Gauge — percentage of customers that are Active. Target > 30%.

```sql
SELECT
    ROUND(
        COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    ) as "Active Rate %"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND customer_status IN ('Active', 'At Risk', 'Churned')
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 15, "color": "#EF8C8C", "label": "Low" },
      { "min": 15, "max": 30, "color": "#F9D45C", "label": "Fair" },
      { "min": 30, "max": 100, "color": "#84BB4C", "label": "Healthy" }
    ]
  }
}
```

```json metabase-pos
{"row": 7, "col":12, "size_x":6, "size_y":6}
```

#### ❓ Question: New vs Returning Customers (6M)

Stacked area — growth quality: how many monthly customers are new vs returning?

```sql
WITH monthly_customers AS (
    SELECT DISTINCT
        date_trunc('month', o.order_timestamp)::date as month,
        o.customer_key,
        c.first_order_date
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.order_timestamp < date_trunc('month', current_date)
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.customer_id != 'Unknown'
)
SELECT
    month as "Month",
    COUNT(CASE WHEN date_trunc('month', first_order_date)::date = month THEN 1 END) as "New",
    COUNT(CASE WHEN date_trunc('month', first_order_date)::date < month THEN 1 END) as "Returning"
FROM monthly_customers
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Month"],
    "graph.metrics": ["New", "Returning"],
    "graph.colors": ["#509EE3", "#88BDE6"],
    "graph.y_axis.title_text": "Customers"
  }
}
```

```json metabase-pos
{"row": 14, "col":0, "size_x":9, "size_y":6}
```

#### ❓ Question: Monthly Active Customers Trend (6M)

Line chart — MAU trend over 6 months showing momentum.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as "Month",
    COUNT(DISTINCT o.customer_key) as "Active Customers"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Month"],
    "graph.metrics": ["Active Customers"],
    "graph.colors": ["#509EE3"],
    "graph.y_axis.title_text": "Customers"
  }
}
```

```json metabase-pos
{"row": 14, "col":9, "size_x":9, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** rolling-30d · **Scope:** customer_type='RETAIL' · **Caveats:** MAU window
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Kenh & Dia ly

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Phan tich acquisition trend 6 thang — momentum tang hay giam?

# Phan tich acquisition trend 6 thang — momentum tang hay giam?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Xac dinh kenh acquisition hieu qua — volume va revenue don dau

# Xac dinh kenh acquisition hieu qua — volume va revenue don dau

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phan tich phan bo dia ly — tinh nao co khach gia tri cao?

# Phan tich phan bo dia ly — tinh nao co khach gia tri cao?

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Customer Acquisition Trend (6M)

Combo chart — monthly new customers (bar) + MoM growth % (line).

```sql
WITH monthly AS (
    SELECT
        date_trunc('month', created_at)::date as month,
        COUNT(*) as new_customers
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND created_at < date_trunc('month', current_date)
      AND customer_id != 'Unknown'
    GROUP BY 1
)
SELECT
    month as "Month",
    new_customers as "New Customers",
    ROUND(
        (new_customers - LAG(new_customers) OVER (ORDER BY month))
        * 100.0 / NULLIF(LAG(new_customers) OVER (ORDER BY month), 0)
    , 1) as "MoM %"
FROM monthly
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Month"],
    "graph.metrics": ["New Customers", "MoM %"],
    "series_settings": {
      "New Customers": { "display": "bar", "color": "#509EE3" },
      "MoM %": { "display": "line", "color": "#7172AD", "line.style": "dashed" }
    },
    "graph.y_axis.title_text": "New Customers"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: New Customers by Channel

Horizontal bar — ranking channels by new customer volume (last month).

```sql
WITH first_orders AS (
    SELECT
        o.customer_key,
        o.channel_key,
        ROW_NUMBER() OVER (PARTITION BY o.customer_key ORDER BY o.order_timestamp) as rn
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE cust.created_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cust.created_at < date_trunc('month', current_date)
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND cust.customer_id != 'Unknown'
)
SELECT
    COALESCE(c.channel_name, 'Unknown') as "Channel",
    COUNT(*) as "New Customers"
FROM first_orders fo
JOIN dim_channels c ON fo.channel_key = c.channel_key
WHERE fo.rn = 1
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
{ "row": 10, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: First-Order Revenue by Channel

Horizontal bar — ranking channels by first-order revenue (last month).

```sql
WITH first_orders AS (
    SELECT
        o.customer_key,
        o.channel_key,
        o.net_revenue,
        ROW_NUMBER() OVER (PARTITION BY o.customer_key ORDER BY o.order_timestamp) as rn
    FROM fact_orders o
    JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE cust.created_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cust.created_at < date_trunc('month', current_date)
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND cust.customer_id != 'Unknown'
)
SELECT
    COALESCE(c.channel_name, 'Unknown') as "Channel",
    SUM(fo.net_revenue) as "First-Order Revenue"
FROM first_orders fo
JOIN dim_channels c ON fo.channel_key = c.channel_key
WHERE fo.rn = 1
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["First-Order Revenue"],
    "graph.colors": ["#88BDE6"],
    "column_settings": {
      "First-Order Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 9, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 15 Provinces by Customers

Horizontal bar — ranking provinces by customer count.

```sql
SELECT
    COALESCE(NULLIF(province, ''), 'Unknown') as "Province",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Province"],
    "graph.metrics": ["Customers"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 9, "size_y": 8 }
```

#### ❓ Question: Top 15 Provinces by LTV

Horizontal bar — ranking provinces by total lifetime value.

```sql
SELECT
    COALESCE(NULLIF(province, ''), 'Unknown') as "Province",
    SUM(lifetime_value) as "Total LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Province"],
    "graph.metrics": ["Total LTV"],
    "graph.colors": ["#7172AD"],
    "column_settings": {
      "Total LTV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 17, "col": 9, "size_x": 9, "size_y": 8 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** rolling-30d · **Scope:** customer_type='RETAIL' · **Caveats:** MAU window
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Watchlist & Hanh dong


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Review ma tran suc khoe segment — xac dinh diem nong can hanh dong

# Review ma tran suc khoe segment — xac dinh diem nong can hanh dong

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Uu tien cham soc VIP — khach nao sap mat? Goi ngay!

# Uu tien cham soc VIP — khach nao sap mat? Goi ngay!

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Sap xep uu tien reactivation — khach gia tri cao can giu truoc

# Sap xep uu tien reactivation — khach gia tri cao can giu truoc

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Xac dinh co hoi recovery — khach churned gia tri cao can win-back

# Xac dinh co hoi recovery — khach churned gia tri cao can win-back

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Segment x Status Health Matrix

Cross-tabulation of segment x status with Active % and At-Risk LTV.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Total",
    COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) as "Active",
    COUNT(CASE WHEN customer_status = 'At Risk' THEN 1 END) as "At Risk",
    COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) as "Churned",
    ROUND(
        COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    ) as "Active %",
    SUM(CASE WHEN customer_status = 'At Risk' THEN lifetime_value ELSE 0 END) as "At-Risk LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 WHEN 'VALUE_SILVER' THEN 3 ELSE 4 END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "At-Risk LTV": { "number_style": "currency", "currency": "VND", "compact": true },
      "Active %": { "suffix": "%" }
    },
    "table.column_formatting": [
      {
        "columns": ["Active %"],
        "type": "single",
        "operator": "<",
        "value": 50,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Active %"],
        "type": "single",
        "operator": ">=",
        "value": 50,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 5 }
```

#### ❓ Question: VIP Customer Watchlist

VIP customers sorted by recency — prioritize outreach for those becoming inactive. Conditional formatting on days since last order.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    total_orders_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Since Last Order",
    customer_status as "Status",
    last_order_date as "Last Order"
FROM dim_customers
WHERE value_group = 'VALUE_VIP'
  AND customer_id != 'Unknown'
ORDER BY recency_days DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "LTV": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Days Since Last Order"],
        "type": "single",
        "operator": ">",
        "value": 60,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Days Since Last Order"],
        "type": "single",
        "operator": ">",
        "value": 30,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 8 }
```

#### ❓ Question: At-Risk Reactivation Priority

At-risk customers ranked by lifetime value — highest value = highest reactivation priority.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    email as "Email",
    value_group as "Segment",
    total_orders_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Inactive",
    last_order_date as "Last Order"
FROM dim_customers
WHERE customer_status = 'At Risk'
  AND customer_id != 'Unknown'
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "LTV": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["LTV"],
        "type": "single",
        "operator": ">=",
        "value": 5000000,
        "color": "#7172AD",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 8 }
```

#### ❓ Question: Churned High-Value Customers

Recently churned customers (91-180 days) with high LTV — recovery campaign candidates.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    email as "Email",
    value_group as "Segment",
    total_orders_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Inactive",
    last_order_date as "Last Order"
FROM dim_customers
WHERE customer_status = 'Churned'
  AND customer_id != 'Unknown'
  AND recency_days <= 180
  AND lifetime_value >= 1000000
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "LTV": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["LTV"],
        "type": "single",
        "operator": ">=",
        "value": 5000000,
        "color": "#7172AD",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** rolling-30d · **Scope:** customer_type='RETAIL' · **Caveats:** MAU window
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

