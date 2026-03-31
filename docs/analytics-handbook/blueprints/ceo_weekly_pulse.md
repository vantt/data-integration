# 📘 Blueprint: CEO Weekly Pulse

**Playbook**: [CEO Weekly Pulse](../playbooks/ceo_weekly_pulse.md)

> **Target Collection:** `Executive`
> **Role:** CEO, Co-Founders
> **Archetype:** Executive Pulse
> **Captured from:** Metabase Dashboard ID 11 (2026-03-31)

## 📂 Collection: Executive

Strategic dashboards for leadership — company performance, targets, and high-level KPIs.

---

### 🖥️ Dashboard: CEO Weekly Pulse

**Description**: 5-minute Monday morning check-in — revenue pace, channel shifts, customer health, and operational flags.

> **Filter mặc định:** Loại bỏ đơn kênh `US` (Export/B2B, 100% discount nội bộ) khỏi tất cả metrics.

---

#### ❓ Question: Report Period

```sql
SELECT
    strftime(date_trunc('week', current_date) - INTERVAL '7 days', '%d/%m') || ' — ' ||
    strftime(date_trunc('week', current_date) - INTERVAL '1 day', '%d/%m/%Y') as "Period"
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### ❓ Question: Weekly Gross Revenue


Tổng giá trị hàng hóa (trước chiết khấu) tuần qua.

**Domain Reference**: [Revenue](../domains/sales.md#1-gross-revenue-gmv)

```sql
SELECT
    SUM(gross_revenue) as "Gross Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Gross Revenue": {
        "number_style": "currency",
        "currency": "VND"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 5,
  "size_y": 3
}
```

#### ❓ Question: Weekly Net Revenue


Doanh thu thuần (sau chiết khấu, trước thuế) tuần qua.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT
    SUM(net_revenue) as "Weekly Net Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Weekly Net Revenue": {
        "number_style": "currency",
        "currency": "VND"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 2,
  "col": 5,
  "size_x": 5,
  "size_y": 3
}
```

#### ❓ Question: Weekly Total Orders


Order count for the last 7 days.

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders)

```sql
SELECT
    COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 2,
  "col": 10,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Weekly AOV


Average order value for the last 7 days.

**Domain Reference**: [AOV](../domains/sales.md#5-aov-average-order-value)

```sql
SELECT
    CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
         ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as "AOV"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "AOV": {
        "number_style": "currency",
        "currency": "VND"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 2,
  "col": 14,
  "size_x": 4,
  "size_y": 3
}
```

---

#### ❓ Question: Cancelled Orders

```sql
SELECT
    COUNT(DISTINCT order_id) as "Cancelled Orders"
FROM fact_orders
WHERE status = 'CANCELLED'
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 5,
  "col": 0,
  "size_x": 5,
  "size_y": 3
}
```

#### ❓ Question: Return Count

```sql
SELECT
    COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns"
FROM fact_orders
WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 5,
  "col": 5,
  "size_x": 5,
  "size_y": 3
}
```

#### ❓ Question: New Customers This Week

```sql
SELECT
    COUNT(DISTINCT customer_key) as "New Customers"
FROM dim_customers
WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(first_order_date) < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 5,
  "col": 10,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Returning Customer Revenue %

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
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Returning Revenue %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 5,
  "col": 14,
  "size_x": 4,
  "size_y": 3
}
```

---

#### ❓ Question: MTD Revenue vs Target Pace


Month-to-date revenue with expected pace toward monthly target.

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate)

```sql
WITH mtd_actual AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as mtd_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date)
      AND order_timestamp < current_date
),
monthly_target AS (
    SELECT
        COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date <= current_date
      AND cycle_end_date >= current_date
)
SELECT
    a.mtd_revenue as "MTD Revenue",
    t.target_revenue as "Monthly Target",
    CASE WHEN t.target_revenue = 0 THEN NULL
         ELSE ROUND(a.mtd_revenue * 100.0 / t.target_revenue, 1) END as "Achievement %",
    CASE WHEN t.target_revenue = 0 THEN NULL
         ELSE ROUND(a.mtd_revenue / (t.target_revenue * EXTRACT(DAY FROM current_date) / EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))), 2) END as "Pace Index"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "MTD Revenue": {
        "number_style": "currency",
        "currency": "VND"
      },
      "Monthly Target": {
        "number_style": "currency",
        "currency": "VND"
      },
      "Achievement %": {
        "number_style": "percent",
        "decimals": 1
      },
      "Pace Index": {
        "decimals": 2
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 8,
  "col": 0,
  "size_x": 18,
  "size_y": 4
}
```

---

#### ❓ Question: Daily Revenue Trend (14 Days)


Revenue by day for the last 14 days — current week vs previous week side-by-side.

**Domain Reference**: [Revenue](../domains/sales.md#1-gmv-gross-merchandise-value)

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
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": [
      "order_date"
    ],
    "graph.metrics": [
      "revenue"
    ],
    "graph.colors": [
      "#509EE3"
    ],
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{
  "row": 12,
  "col": 0,
  "size_x": 18,
  "size_y": 7
}
```

---

#### ❓ Question: Revenue by Channel Category


Revenue split by Ecommerce / Offline / Internal with WoW comparison.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

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
    COALESCE(tw.channel_category, lw.channel_category) as "Channel Category",
    COALESCE(tw.revenue, 0) as "This Week",
    COALESCE(lw.revenue, 0) as "Last Week",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.revenue, 0) - lw.revenue) * 100.0 / lw.revenue, 1) END as "WoW %"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_category = lw.channel_category
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "This Week": {
        "number_style": "currency",
        "currency": "VND"
      },
      "Last Week": {
        "number_style": "currency",
        "currency": "VND"
      },
      "WoW %": {
        "number_style": "percent"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 19,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### ❓ Question: New vs Returning Daily Trend


Daily breakdown of orders by new vs returning customers over 14 days.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

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
    "graph.dimensions": [
      "order_date"
    ],
    "graph.metrics": [
      "orders"
    ],
    "stackable.stack_type": "stacked",
    "series_settings": {
      "New": {
        "color": "#88BDE6"
      },
      "Returning": {
        "color": "#509EE3"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 25,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Discount Rate


Discount as percentage of Gross Revenue this week.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

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
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Discount Rate %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 25,
  "col": 12,
  "size_x": 6,
  "size_y": 3
}
```
