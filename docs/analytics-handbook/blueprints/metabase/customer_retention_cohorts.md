---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - is_active_order
---

# 📘 Blueprint: Weekly · Customer Retention & Cohorts [Retail]

> **Target Collection:** `Marketing & Customers > 👥 Customer`
> **Design Spec:** `designs/customer_retention_lifecycle.md`
> **Role:** Marketing Manager, Customer Success, CEO
> **Archetype:** Analytical (3 tabs) — weekly cadence
> **Database:** Sapo

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail)
## 📂 Collection: Marketing & Customers > 👥 Customer

Retention analytics — are customers coming back? Cohort, waterfall, lifecycle, and purchase frequency.

---

### 🖥️ Dashboard: Weekly · Customer Retention & Cohorts [Retail]

**Description**: Weekly retention analytics — repeat purchase rates, churn trends, cohort retention heatmap, revenue layer cake, purchase frequency distribution, and reactivation tracking. 3 tabs: Suc khoe Retention, Phan tich Cohort, Hanh vi & Reactivation.

---

#### Filter: Segment




```json metabase-filter
{
  "slug": "segment",
  "type": "string/="
}
```

#### Filter: Phân khúc giá trị


CategoryDrop field filter for waterfall cards (Churn Rate, Active Rate, Waterfall Trend). Values: VALUE_VIP / VALUE_GOLD / VALUE_SILVER / VALUE_BRONZE. field_id=1822 on mart_retention_waterfall_monthly (schema main_marts, db_id=2).

```json metabase-filter
{
  "slug": "value_group",
  "type": "string/=",
  "field_id": 1822
}
```

---

### 📑 Tab: Suc khoe Retention

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Reactivation 6 tháng: ' ||
  strftime((current_date - INTERVAL '6 months')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Dự báo: tuần ' || strftime(current_date, '%W/%Y') || ' & tháng ' || strftime(current_date, '%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "dashcard.background": false
  }
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

#### 📝 Text: Monitor retention health — repeat rate, churn, and lifecycle status




# Monitor retention health — repeat rate, churn, and lifecycle status

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Repeat Purchase Rate




Hero metric — percentage of customers who have made more than one purchase, with MoM comparison.

```sql
-- Point-in-time MoM from fact_orders: counts customers with >=2 orders as-of each month-end.
-- Avoids survivorship bias in mart_customer_status_snapshot_monthly (orders_to_date = current value).
-- current_month_end = last day of previous calendar month (most recent closed month).
-- prev_month_end    = last day of the month before that.
-- base = all retail customers (non-cancelled, non-draft, customer_type=RETAIL, customer_id != Unknown)
--        who had at least one order on or before the snapshot date.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
valid_orders AS (
    SELECT o.customer_key, o.ordered_at::date AS order_date
    FROM fact_orders o
    JOIN dim_customers c USING (customer_key)
    WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
      AND c.customer_type = 'RETAIL'
      AND c.customer_id <> 'Unknown'
),
current_period AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN order_cnt > 1 THEN customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT customer_key), 0), 1
        ) AS value
    FROM (
        SELECT customer_key, COUNT(*) AS order_cnt
        FROM valid_orders, month_ends m
        WHERE order_date <= m.current_month_end
        GROUP BY customer_key
    ) pit
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN order_cnt > 1 THEN customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT customer_key), 0), 1
        ) AS value
    FROM (
        SELECT customer_key, COUNT(*) AS order_cnt
        FROM valid_orders, month_ends m
        WHERE order_date <= m.prev_month_end
        GROUP BY customer_key
    ) pit
)
SELECT
    c.value AS "Repeat Rate %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Repeat Rate %\"]": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 5,
  "size_y": 3
}
```

#### ❓ Question: Churn Rate




Percentage of customers churned (90+ days inactive), with MoM comparison. Lower is better.
Optional value_group filter — when set, numerator and denominator are both restricted to that segment so the rate stays correct within the segment.

```sql
-- Point-in-time MoM from mart_retention_waterfall_monthly.
-- Grain-agnostic: SUM(customer_count) aggregates across segment dims.
-- value_group filter applied to BOTH current and previous periods so
-- numerator (CHURNED count) and denominator (total) stay consistent within the segment.
-- No filter → all segments summed → same result as before.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            SUM(CASE WHEN status = 'CHURNED' THEN customer_count ELSE 0 END) * 100.0
            / NULLIF(SUM(customer_count), 0), 1
        ) AS value
    FROM main_marts.mart_retention_waterfall_monthly w, month_ends m
    WHERE w.snapshot_month = m.current_month_end
      [[AND {{value_group}}]]
),
previous_period AS (
    SELECT
        ROUND(
            SUM(CASE WHEN status = 'CHURNED' THEN customer_count ELSE 0 END) * 100.0
            / NULLIF(SUM(customer_count), 0), 1
        ) AS value
    FROM main_marts.mart_retention_waterfall_monthly w, month_ends m
    WHERE w.snapshot_month = m.prev_month_end
      [[AND {{value_group}}]]
)
SELECT
    c.value AS "Churn Rate %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Churn Rate %\"]": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 5,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Avg Order Value




Average revenue per order for repeat customers (LTV ÷ orders), with MoM comparison.

```sql
-- Snapshot-driven MoM: avg days_since_last_order for customers active (not churned)
-- as-of each month-end. Proxy for lifespan using snapshot recency.
-- For repeat customers only (orders_to_date > 1).
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT ROUND(AVG(lifetime_value_to_date / NULLIF(orders_to_date, 0)), 0) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      AND s.orders_to_date > 1
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT ROUND(AVG(lifetime_value_to_date / NULLIF(orders_to_date, 0)), 0) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      AND s.orders_to_date > 1
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "Avg Order Value",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Avg Order Value\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 9,
  "size_x": 5,
  "size_y": 3
}
```

#### ❓ Question: Active Customer Rate




Percentage of paying customers active in last 30 days, with MoM comparison.
Optional value_group filter — when set, numerator and denominator are both restricted to that segment so the rate stays correct within the segment.

```sql
-- Point-in-time MoM from mart_retention_waterfall_monthly.
-- Grain-agnostic: SUM(customer_count) aggregates across segment dims.
-- value_group filter applied to BOTH current and previous periods so
-- numerator (ACTIVE count) and denominator (total) stay consistent within the segment.
-- No filter → all segments summed → same result as before.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            SUM(CASE WHEN status = 'ACTIVE' THEN customer_count ELSE 0 END) * 100.0
            / NULLIF(SUM(customer_count), 0), 1
        ) AS value
    FROM main_marts.mart_retention_waterfall_monthly w, month_ends m
    WHERE w.snapshot_month = m.current_month_end
      [[AND {{value_group}}]]
),
previous_period AS (
    SELECT
        ROUND(
            SUM(CASE WHEN status = 'ACTIVE' THEN customer_count ELSE 0 END) * 100.0
            / NULLIF(SUM(customer_count), 0), 1
        ) AS value
    FROM main_marts.mart_retention_waterfall_monthly w, month_ends m
    WHERE w.snapshot_month = m.prev_month_end
      [[AND {{value_group}}]]
)
SELECT
    c.value AS "Active Rate %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Active Rate %\"]": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 14,
  "size_x": 4,
  "size_y": 3
}
```

---

#### 📝 Text: Assess lifecycle distribution — where are customers concentrating?




# Assess lifecycle distribution — where are customers concentrating?

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Customer Lifecycle Distribution



<!-- Layout: all 3 lifecycle cards start at row 7 for a uniform row -->

Donut chart showing Active / At Risk / Churned distribution.

```sql
SELECT
    customer_status as "Status",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
  AND customer_status IN ('Active', 'At Risk', 'Churned')
  [[AND value_group = {{segment}}]]
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
    "pie.dimension": [
      "Status"
    ],
    "pie.metric": "Customers",
    "pie.colors": {
      "Active": "#509EE3",
      "At Risk": "#F9D45C",
      "Churned": "#EF8C8C"
    },
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 0,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Revenue by Lifecycle Status




Total lifetime value concentrated in each lifecycle status.

```sql
SELECT
    customer_status as "Status",
    SUM(lifetime_value) as "Total LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
  AND customer_status IN ('Active', 'At Risk', 'Churned')
  [[AND value_group = {{segment}}]]
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
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": [
      "Status"
    ],
    "graph.colors": [
      "#509EE3",
      "#F9D45C",
      "#EF8C8C"
    ],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Lifetime Value (VND)",
    "column_settings": {
      "[\"name\",\"Total LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Total LTV"
    ]
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 6,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Segment x Status Matrix




Stacked bar showing lifecycle status distribution within each customer segment.

```sql
SELECT
    value_group as "Segment",
    customer_status as "Status",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
  AND customer_status IN ('Active', 'At Risk', 'Churned')
  [[AND value_group = {{segment}}]]
GROUP BY 1, 2
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 ELSE 3 END,
    CASE customer_status WHEN 'Active' THEN 1 WHEN 'At Risk' THEN 2 ELSE 3 END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": [
      "Segment"
    ],
    "graph.group_by": [
      "Status"
    ],
    "stackable.stack_type": "stacked",
    "graph.colors": [
      "#509EE3",
      "#F9D45C",
      "#EF8C8C"
    ],
    "graph.metrics": [
      "Customers"
    ]
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 12,
  "size_x": 6,
  "size_y": 6
}
```

---

#### 📝 Text: Track retention and churn trends — are we improving toward target?




# Track retention and churn trends — are we improving toward target?

```json metabase-pos
{
  "row": 13,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Retention Waterfall Trend (6M)




Point-in-time lifecycle status counts per month — ACTIVE / AT_RISK / CHURNED from survivorship-free waterfall model.
Optional value_group filter restricts all statuses to that segment — omitting it aggregates all segments (unchanged behavior).

```sql
-- Point-in-time trend from mart_retention_waterfall_monthly.
-- Grain-agnostic: SUM + GROUP BY snapshot_month, status collapses segment dims.
-- value_group filter is optional — omitting it gives all-segment totals (same as before).
SELECT
    snapshot_month AS month,
    status AS "Status",
    SUM(customer_count) AS "Customers"
FROM main_marts.mart_retention_waterfall_monthly
WHERE snapshot_month >= (date_trunc('month', current_date) - INTERVAL '6 months')::date
  [[AND {{value_group}}]]
GROUP BY snapshot_month, status
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": [
      "month"
    ],
    "graph.group_by": [
      "Status"
    ],
    "stackable.stack_type": "stacked",
    "graph.colors": [
      "#509EE3",
      "#F9D45C",
      "#EF8C8C"
    ],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Customers",
    "graph.metrics": [
      "Customers"
    ]
  }
}
```

```json metabase-pos
{
  "row": 14,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

#### ❓ Question: Repeat Purchase Rate Trend (6M)




Monthly trend of repeat purchase rate among buyers each month.

```sql
WITH monthly_buyers AS (
    SELECT
        date_trunc('month', o.ordered_at)::date as month,
        o.customer_key,
        COUNT(DISTINCT o.order_id) as orders_in_month
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.ordered_at < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
    GROUP BY 1, 2
)
SELECT
    month,
    COUNT(*) as "Total Buyers",
    COUNT(CASE WHEN orders_in_month > 1 THEN 1 END) as "Repeat Buyers",
    ROUND(
        COUNT(CASE WHEN orders_in_month > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) as "Repeat %"
FROM monthly_buyers
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": [
      "month"
    ],
    "graph.colors": [
      "#84BB4C"
    ],
    "graph.y_axis.title_text": "Repeat %",
    "graph.metrics": [
      "Repeat %"
    ]
  }
}
```

```json metabase-pos
{
  "row": 14,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: Review retention scorecard — flag segments with weak retention




# Review retention scorecard — flag segments with weak retention

```json metabase-pos
{
  "row": 20,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Retention Health Scorecard




Per-segment retention vitals with conditional formatting.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Customers",
    ROUND(COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Active %",
    ROUND(COUNT(CASE WHEN customer_status = 'At Risk' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "At Risk %",
    ROUND(COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Churned %",
    ROUND(COUNT(CASE WHEN order_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Repeat Rate %",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(recency_days), 0) as "Avg Recency (days)"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 ELSE 3 END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": [
          "Active %"
        ],
        "type": "range",
        "colors": [
          "#EF8C8C",
          "#F9D45C",
          "#84BB4C"
        ],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      },
      {
        "columns": [
          "Churned %"
        ],
        "type": "range",
        "colors": [
          "#84BB4C",
          "#F9D45C",
          "#EF8C8C"
        ],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      }
    ],
    "column_settings": {
      "[\"name\",\"Avg LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Active %\"]": {
        "suffix": "%"
      },
      "[\"name\",\"At Risk %\"]": {
        "suffix": "%"
      },
      "[\"name\",\"Churned %\"]": {
        "suffix": "%"
      },
      "[\"name\",\"Repeat Rate %\"]": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 21,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### ❓ Question: MAU vs Repeat-Buyer MAU (12M)




Dual-line chart — MAU total vs repeat-buyer MAU (≥2 lifetime orders) over 12 months. Gap between lines = one-time buyer volume; narrowing gap = improving engagement quality.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date AS "Month",
    COUNT(DISTINCT o.customer_key) AS "MAU",
    COUNT(DISTINCT CASE WHEN c.order_count >= 2 THEN o.customer_key END) AS "MAU Repeat"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.ordered_at >= date_trunc('month', current_date) - INTERVAL '12 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND o.scope_retail
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": [
      "Month"
    ],
    "graph.colors": [
      "#509EE3",
      "#7172AD"
    ],
    "graph.y_axis.title_text": "Customers",
    "graph.x_axis.title_text": "Month",
    "graph.metrics": [
      "MAU",
      "MAU Repeat"
    ]
  }
}
```

```json metabase-pos
{
  "row": 28,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_orders + dim_customers · **Cadence:** weekly · **Scope:** scope_retail · **Caveats:** Cohort rolling



**Source:** fact_orders + dim_customers · **Cadence:** weekly · **Scope:** scope_retail · **Caveats:** Cohort rolling

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Phan tich Cohort

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Reactivation 6 tháng: ' ||
  strftime((current_date - INTERVAL '6 months')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Dự báo: tuần ' || strftime(current_date, '%W/%Y') || ' & tháng ' || strftime(current_date, '%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "dashcard.background": false
  }
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

#### 📝 Text: Analyze cohort retention — which cohorts stick, which churn early?




# Analyze cohort retention — which cohorts stick, which churn early?

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Avg Month-1 Retention




Average M1 retention rate across recent cohorts — early lifecycle health indicator.

```sql
WITH cohort_sizes AS (
    SELECT
        date_trunc('month', first_order_date) as cohort_month,
        COUNT(DISTINCT customer_id) as original_size
    FROM dim_customers
    WHERE first_order_date >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND customer_id != 'Unknown'
    GROUP BY 1
),
m1_retention AS (
    SELECT
        date_trunc('month', c.first_order_date) as cohort_month,
        COUNT(DISTINCT c.customer_id) as retained
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND c.first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('month', c.first_order_date, o.ordered_at) = 1
      AND o.scope_sales
    GROUP BY 1
)
SELECT
    ROUND(AVG(CAST(r.retained AS FLOAT) / s.original_size * 100), 1) as "Avg M1 Retention %"
FROM cohort_sizes s
LEFT JOIN m1_retention r ON s.cohort_month = r.cohort_month
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Avg M1 Retention %\"]": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 6,
  "size_y": 3
}
```

#### ❓ Question: Best Cohort (M1 Retention)




Which acquisition month had the highest Month-1 retention rate.

```sql
WITH cohort_sizes AS (
    SELECT
        date_trunc('month', first_order_date) as cohort_month,
        COUNT(DISTINCT customer_id) as original_size
    FROM dim_customers
    WHERE first_order_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND customer_id != 'Unknown'
    GROUP BY 1
),
m1_retention AS (
    SELECT
        date_trunc('month', c.first_order_date) as cohort_month,
        COUNT(DISTINCT c.customer_id) as retained
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND c.first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('month', c.first_order_date, o.ordered_at) = 1
      AND o.scope_sales
    GROUP BY 1
)
SELECT
    strftime(s.cohort_month, '%Y-%m') as "Best Cohort",
    ROUND(CAST(r.retained AS FLOAT) / s.original_size * 100, 1) as "M1 %"
FROM cohort_sizes s
LEFT JOIN m1_retention r ON s.cohort_month = r.cohort_month
ORDER BY 2 DESC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"M1 %\"]": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 6,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Avg Orders per Customer




Average number of orders among paying customers, with MoM comparison.

```sql
WITH current_period AS (
    SELECT ROUND(AVG(order_count), 1) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND order_count > 0
),
previous_period AS (
    SELECT ROUND(AVG(order_count), 1) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND order_count > 0
      AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    c.value as "Avg Orders",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 3,
  "col": 10,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Returning Revenue Ratio




Percentage of total revenue coming from returning customers.

```sql
SELECT
    ROUND(
        SUM(CASE
            WHEN date_trunc('month', o.ordered_at) != date_trunc('month', c.first_order_date)
            THEN o.net_revenue ELSE 0
        END) * 100.0 / NULLIF(SUM(o.net_revenue), 0), 1
    ) as "Returning Revenue %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Returning Revenue %\"]": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 14,
  "size_x": 4,
  "size_y": 3
}
```

---

#### 📝 Text: Examine cohort retention matrix — identify drop-off patterns




# Examine cohort retention matrix — identify drop-off patterns

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Cohort Retention Heatmap




Percentage of customers returning in subsequent months after first purchase (12-month lookback). Pre-pivoted in SQL — native SQL cards don't support display:pivot.

```sql
WITH cohort_first_orders AS (
    -- First scope_sales order per customer — ensures M0 is always 100%
    SELECT
        customer_key,
        date_trunc('month', MIN(ordered_at))::date AS cohort_month
    FROM fact_orders
    WHERE scope_sales
      AND customer_key IS NOT NULL
    GROUP BY 1
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_key) AS original_size
    FROM cohort_first_orders
    WHERE cohort_month >= (date_trunc('month', current_date) - INTERVAL '12 months')::date
    GROUP BY 1
),
retention_activity AS (
    SELECT
        co.cohort_month,
        date_diff('month', co.cohort_month, date_trunc('month', o.ordered_at)::date) AS month_number,
        COUNT(DISTINCT co.customer_key) AS active_customers
    FROM cohort_first_orders co
    JOIN fact_orders o ON co.customer_key = o.customer_key
    WHERE co.cohort_month >= (date_trunc('month', current_date) - INTERVAL '12 months')::date
      AND o.scope_sales
      AND date_trunc('month', o.ordered_at)::date >= co.cohort_month
    GROUP BY 1, 2
),
retention_pct AS (
    SELECT
        strftime(r.cohort_month, '%Y-%m') AS cohort,
        r.month_number,
        ROUND(CAST(r.active_customers AS FLOAT) / s.original_size * 100, 1) AS ret_pct
    FROM retention_activity r
    JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
    WHERE r.month_number BETWEEN 0 AND 11
)
SELECT
    cohort                                              AS "Cohort",
    MAX(CASE WHEN month_number = 0  THEN ret_pct END)  AS "M0",
    MAX(CASE WHEN month_number = 1  THEN ret_pct END)  AS "M1",
    MAX(CASE WHEN month_number = 2  THEN ret_pct END)  AS "M2",
    MAX(CASE WHEN month_number = 3  THEN ret_pct END)  AS "M3",
    MAX(CASE WHEN month_number = 4  THEN ret_pct END)  AS "M4",
    MAX(CASE WHEN month_number = 5  THEN ret_pct END)  AS "M5",
    MAX(CASE WHEN month_number = 6  THEN ret_pct END)  AS "M6",
    MAX(CASE WHEN month_number = 7  THEN ret_pct END)  AS "M7",
    MAX(CASE WHEN month_number = 8  THEN ret_pct END)  AS "M8",
    MAX(CASE WHEN month_number = 9  THEN ret_pct END)  AS "M9",
    MAX(CASE WHEN month_number = 10 THEN ret_pct END)  AS "M10",
    MAX(CASE WHEN month_number = 11 THEN ret_pct END)  AS "M11"
FROM retention_pct
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": [
          "M0",
          "M1",
          "M2",
          "M3",
          "M4",
          "M5",
          "M6",
          "M7",
          "M8",
          "M9",
          "M10",
          "M11"
        ],
        "type": "range",
        "colors": [
          "#EF8C8C",
          "#F9D45C",
          "#84BB4C"
        ],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      }
    ]
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 0,
  "size_x": 18,
  "size_y": 9
}
```

---

#### 📝 Text: Track revenue by cohort — are recent cohorts contributing enough?




# Track revenue by cohort — are recent cohorts contributing enough?

```json metabase-pos
{
  "row": 16,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Revenue by Cohort (Layer Cake)




Total revenue by acquisition cohort over time — shows legacy vs new contribution.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as revenue_month,
    strftime(date_trunc('month', c.first_order_date), '%Y-%m') as cohort,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '12 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": [
      "revenue_month"
    ],
    "graph.group_by": [
      "cohort"
    ],
    "stackable.stack_type": "stacked",
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "[\"name\",\"revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "revenue"
    ]
  }
}
```

```json metabase-pos
{
  "row": 17,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### 📝 Text: Compare new vs returning — revenue dependency and growth quality




# Compare new vs returning — revenue dependency and growth quality

```json metabase-pos
{
  "row": 23,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: New vs Returning Revenue (6M)




Monthly revenue split by new customers (first order month) vs returning customers.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as month,
    CASE
        WHEN date_trunc('month', o.ordered_at) = date_trunc('month', c.first_order_date)
        THEN 'New Customer'
        ELSE 'Returning Customer'
    END as customer_type,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": [
      "month"
    ],
    "graph.group_by": [
      "customer_type"
    ],
    "stackable.stack_type": "stacked",
    "graph.colors": [
      "#509EE3",
      "#84BB4C"
    ],
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "[\"name\",\"revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "revenue"
    ]
  }
}
```

```json metabase-pos
{
  "row": 24,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

#### ❓ Question: New vs Returning Customers (6M)




Monthly count of new vs returning purchasers.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as month,
    CASE
        WHEN date_trunc('month', o.ordered_at) = date_trunc('month', c.first_order_date)
        THEN 'New Customer'
        ELSE 'Returning Customer'
    END as customer_type,
    COUNT(DISTINCT c.customer_id) as customers
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": [
      "month"
    ],
    "graph.group_by": [
      "customer_type"
    ],
    "stackable.stack_type": "stacked",
    "graph.colors": [
      "#509EE3",
      "#84BB4C"
    ],
    "graph.y_axis.title_text": "Customers",
    "graph.metrics": [
      "customers"
    ]
  }
}
```

```json metabase-pos
{
  "row": 24,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_orders + dim_customers · **Cadence:** weekly · **Scope:** scope_retail · **Caveats:** Cohort rolling



**Source:** fact_orders + dim_customers · **Cadence:** weekly · **Scope:** scope_retail · **Caveats:** Cohort rolling

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Hanh vi & Reactivation

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Reactivation 6 tháng: ' ||
  strftime((current_date - INTERVAL '6 months')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Dự báo: tuần ' || strftime(current_date, '%W/%Y') || ' & tháng ' || strftime(current_date, '%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "dashcard.background": false
  }
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

#### 📝 Text: Analyze purchase behavior — timing signals and reactivation effectiveness




# Analyze purchase behavior — timing signals and reactivation effectiveness

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Avg Days Between Purchases




Hero metric — average inter-purchase gap for repeat customers, with MoM comparison.

```sql
WITH purchase_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.ordered_at) OVER (PARTITION BY o.customer_key ORDER BY o.ordered_at) AS DATE),
            CAST(o.ordered_at AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
),
current_val AS (
    SELECT ROUND(AVG(days_between), 0) as value
    FROM purchase_gaps
    WHERE days_between > 0
),
prev_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.ordered_at) OVER (PARTITION BY o.customer_key ORDER BY o.ordered_at) AS DATE),
            CAST(o.ordered_at AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND c.customer_id != 'Unknown'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND c.value_group = {{segment}}]]
),
prev_val AS (
    SELECT ROUND(AVG(days_between), 0) as value
    FROM prev_gaps
    WHERE days_between > 0
)
SELECT
    c.value as "Avg Gap (days)",
    p.value as "Prev Month"
FROM current_val c, prev_val p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Avg Gap (days)\"]": {
        "suffix": " days"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 6,
  "size_y": 3
}
```

#### ❓ Question: Reactivated Customers (Last Month)




Customers who returned after 30+ days gap, with MoM comparison.

```sql
WITH reactivated_current AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT customer_key, MAX(ordered_at) as prev_order
        FROM fact_orders
        WHERE scope_sales
          AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
        GROUP BY 1
    ) prev ON o.customer_key = prev.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      AND date_diff('day', CAST(prev.prev_order AS DATE), CAST(o.ordered_at AS DATE)) > 30
      [[AND c.value_group = {{segment}}]]
),
reactivated_prev AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT customer_key, MAX(ordered_at) as prev_order
        FROM fact_orders
        WHERE scope_sales
          AND ordered_at < date_trunc('month', current_date) - INTERVAL '2 months'
        GROUP BY 1
    ) prev ON o.customer_key = prev.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('day', CAST(prev.prev_order AS DATE), CAST(o.ordered_at AS DATE)) > 30
      [[AND c.value_group = {{segment}}]]
)
SELECT
    c.value as "Reactivated",
    p.value as "Prev Month"
FROM reactivated_current c, reactivated_prev p
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 3,
  "col": 6,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: One-Time Buyer Rate




Percentage of customers with exactly 1 order — conversion opportunity. Lower is better.

```sql
-- Snapshot-driven MoM: orders_to_date = 1 as-of each month-end snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN orders_to_date = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN orders_to_date = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "One-Time %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"One-Time %\"]": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 10,
  "size_x": 4,
  "size_y": 3
}
```

---

#### 📝 Text: Examine purchase frequency — distribution shape and conversion opportunity




# Examine purchase frequency — distribution shape and conversion opportunity

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Purchase Frequency Distribution




How many orders do customers typically place? Understand one-time vs repeat behavior.

```sql
WITH total AS (
    SELECT COUNT(*) AS cnt
    FROM dim_customers
    WHERE order_count > 0
      AND customer_id != 'Unknown'
      [[AND value_group = {{segment}}]]
)
SELECT
    CASE
        WHEN order_count = 1 THEN '1 order'
        WHEN order_count = 2 THEN '2 orders'
        WHEN order_count = 3 THEN '3 orders'
        WHEN order_count BETWEEN 4 AND 5 THEN '4-5 orders'
        WHEN order_count BETWEEN 6 AND 10 THEN '6-10 orders'
        ELSE '11+ orders'
    END as "Order Count",
    COUNT(*) as "Customers",
    ROUND(
        COUNT(*) * 100.0 / NULLIF((SELECT cnt FROM total), 0), 1
    ) as "% of Total"
FROM dim_customers
WHERE order_count > 0
  AND customer_id != 'Unknown'
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY MIN(order_count)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": [
      "Order Count"
    ],
    "graph.colors": [
      "#509EE3"
    ],
    "graph.x_axis.title_text": "Order Frequency",
    "graph.y_axis.title_text": "Customers",
    "graph.metrics": [
      "Customers"
    ]
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

#### ❓ Question: Days Between Purchases Distribution




For repeat customers, how long between purchases? Helps set reactivation timing.

```sql
WITH purchase_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.ordered_at) OVER (PARTITION BY o.customer_key ORDER BY o.ordered_at) AS DATE),
            CAST(o.ordered_at AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
)
SELECT
    CASE
        WHEN days_between <= 7 THEN '0-7 days'
        WHEN days_between <= 14 THEN '8-14 days'
        WHEN days_between <= 30 THEN '15-30 days'
        WHEN days_between <= 60 THEN '31-60 days'
        WHEN days_between <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END as "Gap",
    COUNT(*) as "Occurrences",
    ROUND(
        COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0), 1
    ) as "% of Total"
FROM purchase_gaps
WHERE days_between IS NOT NULL
  AND days_between > 0
GROUP BY 1
ORDER BY MIN(days_between)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": [
      "Gap"
    ],
    "graph.colors": [
      "#88BDE6"
    ],
    "graph.x_axis.title_text": "Days Between Purchases",
    "graph.y_axis.title_text": "Occurrences",
    "graph.metrics": [
      "Occurrences"
    ]
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: Track reactivation performance — is win-back ROI improving?




# Track reactivation performance — is win-back ROI improving?

```json metabase-pos
{
  "row": 13,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Reactivation Trend (6M)




Monthly count of reactivated customers (returned after 30+ day gap) with revenue contribution.

```sql
WITH reactivated AS (
    SELECT
        date_trunc('month', o.ordered_at)::date as month,
        o.customer_key,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT
            customer_key,
            ordered_at,
            LAG(ordered_at) OVER (PARTITION BY customer_key ORDER BY ordered_at) as prev_order
        FROM fact_orders
        WHERE scope_sales
    ) gaps ON o.customer_key = gaps.customer_key
        AND o.ordered_at = gaps.ordered_at
    WHERE o.scope_sales
      AND o.is_active_order
      AND gaps.prev_order IS NOT NULL
      AND date_diff('day', CAST(gaps.prev_order AS DATE), CAST(o.ordered_at AS DATE)) > 30
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.ordered_at < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
    GROUP BY 1, 2
)
SELECT
    month,
    COUNT(DISTINCT customer_key) as "Reactivated Customers",
    SUM(revenue) as "Reactivation Revenue"
FROM reactivated
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": [
      "month"
    ],
    "series_settings": {
      "Reactivated Customers": {
        "display": "bar",
        "color": "#84BB4C"
      },
      "Reactivation Revenue": {
        "display": "line",
        "color": "#7172AD"
      }
    },
    "graph.y_axis.title_text": "Customers",
    "column_settings": {
      "[\"name\",\"Reactivation Revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Reactivated Customers",
      "Reactivation Revenue"
    ]
  }
}
```

```json metabase-pos
{
  "row": 14,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_orders + dim_customers · **Cadence:** weekly · **Scope:** scope_retail · **Caveats:** Cohort rolling



**Source:** fact_orders + dim_customers · **Cadence:** weekly · **Scope:** scope_retail · **Caveats:** Cohort rolling

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---
