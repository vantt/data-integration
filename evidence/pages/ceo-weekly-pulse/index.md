---
title: CEO Weekly Pulse — Doanh thu & Target
---

# CEO Weekly Pulse [All]

<a href="/ceo-weekly-pulse">Doanh thu & Target</a> · <a href="/ceo-weekly-pulse/channels">Kênh bán hàng</a> · <a href="/ceo-weekly-pulse/customers">Khách hàng & Cảnh báo</a>

> **Scope:** All sales channels (`is_sales_channel = true`) · Exclude CANCELLED/DRAFT · Cửa sổ: Mon-to-date vs WoW (tuần trước Mon–Sun)

---

## Doanh thu tuần này

```sql revenue_kpi
WITH
this_week AS (
    SELECT
        COALESCE(SUM(net_revenue), 0)      AS net_revenue,
        COALESCE(SUM(gross_revenue), 0)    AS gross_revenue,
        COUNT(DISTINCT order_id)           AS total_orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END AS aov
    FROM main_marts.fact_orders
    WHERE scope_sales AND is_active_order
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT
        COALESCE(SUM(net_revenue), 0)      AS net_revenue_lw,
        COALESCE(SUM(gross_revenue), 0)    AS gross_revenue_lw,
        COUNT(DISTINCT order_id)           AS total_orders_lw,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END AS aov_lw
    FROM main_marts.fact_orders
    WHERE scope_sales AND is_active_order
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
)
SELECT tw.*, lw.*
FROM this_week tw, last_week lw
```

<BigValue data={revenue_kpi} value="net_revenue"   comparison="net_revenue_lw"   comparisonTitle="Tuần trước" title="Net Revenue (₫)"   fmt="#,##0" />
<BigValue data={revenue_kpi} value="gross_revenue" comparison="gross_revenue_lw" comparisonTitle="Tuần trước" title="Gross Revenue (₫)" fmt="#,##0" />
<BigValue data={revenue_kpi} value="total_orders"  comparison="total_orders_lw"  comparisonTitle="Tuần trước" title="Đơn hàng" />
<BigValue data={revenue_kpi} value="aov"           comparison="aov_lw"           comparisonTitle="Tuần trước" title="AOV (₫)"            fmt="#,##0" />

---

## Tiến độ target tháng

```sql mtd_progress
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) AS mtd_gmv
    FROM main_marts.fact_orders
    WHERE scope_sales AND is_active_order
      AND ordered_at >= date_trunc('month', current_date)
      AND ordered_at < current_date
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) AS target_gmv
    FROM main_marts.fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date <= current_date
      AND cycle_end_date >= current_date
)
SELECT
    a.mtd_gmv,
    t.target_gmv,
    ROUND(a.mtd_gmv * 100.0 / NULLIF(t.target_gmv, 0), 1) AS target_pct,
    CASE WHEN t.target_gmv = 0 THEN NULL
         ELSE ROUND(
           a.mtd_gmv / (
             t.target_gmv
             * EXTRACT(DAY FROM current_date)
             / EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))
           ), 2)
    END AS pace_index
FROM mtd_actual a, monthly_target t
```

<BigValue data={mtd_progress} value="mtd_gmv"     title="MTD GMV (₫)"   fmt="#,##0" />
<BigValue data={mtd_progress} value="target_pct"  title="% of Target"   fmt="0.0" />
<BigValue data={mtd_progress} value="pace_index"  title="Pace Index"    fmt="0.00" />

> **Pace Index:** >1.0 = Ahead · 0.8–1.0 = On Track · {'<'}0.8 = Behind

---

## Xu hướng doanh thu 14 ngày

```sql daily_revenue
SELECT
    date(ordered_at) AS order_date,
    SUM(net_revenue) AS revenue
FROM main_marts.fact_orders
WHERE scope_sales AND is_active_order
  AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1
ORDER BY 1
```

<AreaChart
    data={daily_revenue}
    x="order_date"
    y="revenue"
    title="Net Revenue hàng ngày (14 ngày)"
    yAxisTitle="Revenue (₫)"
/>

---

## Danh sách đơn hàng tuần này

```sql orders_this_week
SELECT
    o.order_code                                                          AS "Mã đơn",
    strftime(o.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%d/%m %H:%M') AS "Thời gian",
    COALESCE(ch.channel_name, 'Unknown')                                  AS "Kênh",
    c.full_name                                                           AS "Khách hàng",
    o.status                                                              AS "Trạng thái",
    o.gross_revenue                                                       AS "Gross (₫)",
    o.discount_amount                                                     AS "Chiết khấu (₫)",
    o.net_revenue                                                         AS "Net Revenue (₫)"
FROM main_marts.fact_orders o
LEFT JOIN main_marts.dim_customers c  ON o.customer_key = c.customer_key
LEFT JOIN main_marts.dim_channels  ch ON o.channel_key  = ch.channel_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
ORDER BY o.ordered_at DESC
```

<DataTable data={orders_this_week} rows=25 />

---

```sql data_freshness
SELECT
    CASE WHEN MAX(ordered_at) < now() - INTERVAL '24 hours'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — ' ELSE '' END
    || '🕐 Đơn cuối: ' || strftime(timezone('Asia/Ho_Chi_Minh', MAX(ordered_at)), '%d/%m %H:%M')
    AS freshness_msg
FROM main_marts.fact_orders
WHERE scope_sales AND is_active_order
  AND ordered_at >= current_date - INTERVAL '1 day'
```

> <Value data={data_freshness} column="freshness_msg" />

**Source:** `fact_orders` · **Scope:** `is_sales_channel=true`, exclude CANCELLED/DRAFT · **MTD Target:** `fact_targets` (metric_code='gmv')
