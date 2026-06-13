---
title: CEO Weekly Pulse — Kênh bán hàng
---

# CEO Weekly Pulse [All]

<a href="/ceo-weekly-pulse">Doanh thu & Target</a> · <a href="/ceo-weekly-pulse/channels">Kênh bán hàng</a> · <a href="/ceo-weekly-pulse/customers">Khách hàng & Cảnh báo</a>

> **Scope:** All sales channels · Tuần này (Mon-to-date) vs WoW

---

## Cơ cấu kênh bán hàng

```sql channel_mix
SELECT
    c.channel_category                                    AS channel_category,
    SUM(o.net_revenue)                                    AS revenue,
    ROUND(SUM(o.net_revenue) * 100.0 / SUM(SUM(o.net_revenue)) OVER (), 1) AS revenue_pct
FROM main_marts.fact_orders o
JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales AND o.is_active_order
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
```

<BarChart
    data={channel_mix}
    x="channel_category"
    y="revenue"
    title="Revenue by Channel Category (₫)"
    labels=true
/>

<DataTable data={channel_mix} />

---

## WoW so sánh kênh

```sql channel_wow
WITH this_week AS (
    SELECT c.channel_category, SUM(o.net_revenue) AS revenue
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY 1
),
last_week AS (
    SELECT c.channel_category, SUM(o.net_revenue) AS revenue
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_category, lw.channel_category) AS channel,
    COALESCE(tw.revenue, 0)                            AS this_week,
    COALESCE(lw.revenue, 0)                            AS last_week
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_category = lw.channel_category
ORDER BY COALESCE(tw.revenue, 0) DESC
```

<BarChart
    data={channel_wow}
    x="channel"
    y={["this_week", "last_week"]}
    title="Revenue by Channel — This Week vs Last Week (₫)"
    type="grouped"
    yAxisTitle="Revenue (₫)"
/>

---

## Top kênh bán hàng

```sql top_channels
SELECT
    c.channel_name AS channel,
    SUM(o.net_revenue) AS revenue
FROM main_marts.fact_orders o
JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales AND o.is_active_order
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 8
```

<BarChart
    data={top_channels}
    x="channel"
    y="revenue"
    title="Top 8 Channels by Revenue (₫)"
    swapXY=true
    yAxisTitle="Revenue (₫)"
/>

---

## Chi tiết hiệu suất kênh (WoW)

```sql channel_performance
WITH this_week AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue)         AS revenue,
        COUNT(DISTINCT o.order_id) AS orders
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue)         AS revenue,
        COUNT(DISTINCT o.order_id) AS orders
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_name, lw.channel_name)                                      AS "Kênh",
    COALESCE(tw.orders, 0)                                                           AS "Đơn (TN)",
    COALESCE(tw.revenue, 0)                                                          AS "Revenue TN (₫)",
    COALESCE(lw.orders, 0)                                                           AS "Đơn (TT)",
    COALESCE(lw.revenue, 0)                                                          AS "Revenue TT (₫)",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.revenue, 0) - lw.revenue) * 100.0 / lw.revenue, 1)
    END                                                                              AS "WoW %"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_name = lw.channel_name
ORDER BY COALESCE(tw.revenue, 0) DESC
```

<DataTable data={channel_performance} rows=20 />

---

**Source:** `fact_orders` + `dim_channels` · **Scope:** `is_sales_channel=true`, exclude CANCELLED/DRAFT
