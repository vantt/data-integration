---
title: CEO Weekly Pulse
---

# CEO Weekly Pulse

> **Scope:** All sales channels · Exclude CANCELLED/DRAFT · Mon-to-date vs tuần trước (Mon–Sun)

```sql revenue_kpi
WITH
tw AS (
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
lw AS (
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
SELECT tw.*, lw.* FROM tw, lw
```

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
         ELSE ROUND(a.mtd_gmv / (
             t.target_gmv
             * EXTRACT(DAY FROM current_date)
             / EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))
         ), 2)
    END AS pace_index
FROM mtd_actual a, monthly_target t
```

```sql daily_revenue
SELECT
    date(ordered_at) AS order_date,
    SUM(net_revenue) AS revenue
FROM main_marts.fact_orders
WHERE scope_sales AND is_active_order
  AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1 ORDER BY 1
```

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

```sql channel_mix
SELECT
    c.channel_category AS channel_category,
    SUM(o.net_revenue) AS revenue,
    ROUND(SUM(o.net_revenue) * 100.0 / SUM(SUM(o.net_revenue)) OVER (), 1) AS revenue_pct
FROM main_marts.fact_orders o
JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales AND o.is_active_order
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1 ORDER BY 2 DESC
```

```sql channel_wow
WITH tw AS (
    SELECT c.channel_category, SUM(o.net_revenue) AS revenue
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY 1
),
lw AS (
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
    COALESCE(tw.revenue, 0) AS this_week,
    COALESCE(lw.revenue, 0) AS last_week
FROM tw FULL OUTER JOIN lw ON tw.channel_category = lw.channel_category
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```sql channel_performance
WITH tw AS (
    SELECT c.channel_name, SUM(o.net_revenue) AS revenue, COUNT(DISTINCT o.order_id) AS orders
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY 1
),
lw AS (
    SELECT c.channel_name, SUM(o.net_revenue) AS revenue, COUNT(DISTINCT o.order_id) AS orders
    FROM main_marts.fact_orders o
    JOIN main_marts.dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_name, lw.channel_name)                                   AS "Kênh",
    COALESCE(tw.orders, 0)                                                        AS "Đơn (TN)",
    COALESCE(tw.revenue, 0)                                                       AS "Revenue TN (₫)",
    COALESCE(lw.orders, 0)                                                        AS "Đơn (TT)",
    COALESCE(lw.revenue, 0)                                                       AS "Revenue TT (₫)",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.revenue, 0) - lw.revenue) * 100.0 / lw.revenue, 1)
    END                                                                           AS "WoW %"
FROM tw FULL OUTER JOIN lw ON tw.channel_name = lw.channel_name
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```sql customer_kpi
WITH
new_tw      AS (SELECT COUNT(DISTINCT customer_key) AS val FROM main_marts.dim_customers
                WHERE date(first_order_date) >= date_trunc('week', current_date)
                  AND date(first_order_date) <= current_date),
new_lw      AS (SELECT COUNT(DISTINCT customer_key) AS val FROM main_marts.dim_customers
                WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
                  AND date(first_order_date) < date_trunc('week', current_date)),
ret_tw      AS (SELECT COUNT(DISTINCT o.customer_key) AS val
                FROM main_marts.fact_orders o
                LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
                WHERE o.scope_sales
                  AND o.ordered_at >= date_trunc('week', current_date)
                  AND o.ordered_at < current_date + INTERVAL '1 day'
                  AND date(c.first_order_date) < date_trunc('week', current_date)),
ret_lw      AS (SELECT COUNT(DISTINCT o.customer_key) AS val
                FROM main_marts.fact_orders o
                LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
                WHERE o.scope_sales
                  AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
                  AND o.ordered_at < date_trunc('week', current_date)
                  AND date(c.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'),
ret_rev     AS (SELECT
                    ROUND(SUM(CASE WHEN date(c.first_order_date) < date_trunc('week', current_date)
                                   THEN o.net_revenue ELSE 0 END) * 100.0
                          / NULLIF(SUM(o.net_revenue), 0), 1) AS returning_rev_pct
                FROM main_marts.fact_orders o
                LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
                WHERE o.scope_sales AND o.is_active_order
                  AND o.ordered_at >= date_trunc('week', current_date)
                  AND o.ordered_at < current_date + INTERVAL '1 day')
SELECT ntw.val AS new_customers, nlw.val AS new_customers_lw,
       rtw.val AS returning_customers, rlw.val AS returning_customers_lw,
       rr.returning_rev_pct
FROM new_tw ntw, new_lw nlw, ret_tw rtw, ret_lw rlw, ret_rev rr
```

```sql new_vs_returning_trend
SELECT
    date(o.ordered_at) AS order_date,
    CASE WHEN date(c.first_order_date) = date(o.ordered_at) THEN 'New' ELSE 'Returning' END AS customer_type,
    COUNT(DISTINCT o.order_id) AS orders
FROM main_marts.fact_orders o
LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1, 2 ORDER BY 1, 2
```

```sql ops_and_profit
WITH
cancelled_tw AS (SELECT COUNT(DISTINCT order_id) AS val FROM main_marts.fact_orders
                 WHERE NOT is_active_order AND scope_sales
                   AND ordered_at >= date_trunc('week', current_date)
                   AND ordered_at < current_date + INTERVAL '1 day'),
cancelled_lw AS (SELECT COUNT(DISTINCT order_id) AS val FROM main_marts.fact_orders
                 WHERE NOT is_active_order AND scope_sales
                   AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
                   AND ordered_at < date_trunc('week', current_date)),
returns_tw   AS (SELECT COUNT(DISTINCT r.return_id) AS val
                 FROM main_marts.fact_order_returns r
                 JOIN main_marts.dim_channels c ON r.channel_key = c.channel_key
                 WHERE c.is_sales_channel AND r.return_status = 'returned'
                   AND r.returned_at >= date_trunc('week', current_date)
                   AND r.returned_at < current_date + INTERVAL '1 day'),
returns_lw   AS (SELECT COUNT(DISTINCT r.return_id) AS val
                 FROM main_marts.fact_order_returns r
                 JOIN main_marts.dim_channels c ON r.channel_key = c.channel_key
                 WHERE c.is_sales_channel AND r.return_status = 'returned'
                   AND r.returned_at >= date_trunc('week', current_date) - INTERVAL '7 days'
                   AND r.returned_at < date_trunc('week', current_date)),
discount     AS (SELECT ROUND(SUM(COALESCE(discount_amount,0))*100.0 / NULLIF(SUM(gross_revenue),0), 1) AS discount_rate_pct
                 FROM main_marts.fact_orders
                 WHERE scope_sales AND is_active_order
                   AND ordered_at >= date_trunc('week', current_date)
                   AND ordered_at < current_date + INTERVAL '1 day'),
profit_tw    AS (SELECT
                     COALESCE(SUM(e.channel_net_profit), 0) AS net_profit,
                     ROUND(SUM(e.gross_profit)*100.0 / NULLIF(SUM(e.net_revenue),0), 1) AS gross_margin_pct
                 FROM main_marts.fact_order_economics e
                 JOIN main_marts.fact_orders o ON e.order_id = o.order_id
                 WHERE e.scope_sales AND e.has_cogs AND e.is_active_order
                   AND o.ordered_at >= date_trunc('week', current_date)
                   AND o.ordered_at < current_date + INTERVAL '1 day'),
profit_lw    AS (SELECT
                     COALESCE(SUM(e.channel_net_profit), 0) AS net_profit_lw,
                     ROUND(SUM(e.gross_profit)*100.0 / NULLIF(SUM(e.net_revenue),0), 1) AS gross_margin_pct_lw
                 FROM main_marts.fact_order_economics e
                 JOIN main_marts.fact_orders o ON e.order_id = o.order_id
                 WHERE e.scope_sales AND e.has_cogs AND e.is_active_order
                   AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
                   AND o.ordered_at < date_trunc('week', current_date)),
loss_ch      AS (SELECT COUNT(*) AS kenh_lo FROM (
                     SELECT e.channel_key FROM main_marts.fact_order_economics e
                     JOIN main_marts.fact_orders o ON e.order_id = o.order_id
                     WHERE e.scope_sales AND e.has_cogs AND o.is_active_order
                       AND o.ordered_at >= date_trunc('week', current_date)
                       AND o.ordered_at < current_date + INTERVAL '1 day'
                     GROUP BY e.channel_key HAVING SUM(e.channel_net_profit) < 0
                 ) lc)
SELECT ctw.val AS cancelled_orders, clw.val AS cancelled_orders_lw,
       rtw.val AS returns, rlw.val AS returns_lw,
       d.discount_rate_pct,
       pt.net_profit, pl.net_profit_lw,
       pt.gross_margin_pct, pl.gross_margin_pct_lw,
       lc.kenh_lo
FROM cancelled_tw ctw, cancelled_lw clw, returns_tw rtw, returns_lw rlw,
     discount d, profit_tw pt, profit_lw pl, loss_ch lc
```

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

<Tabs id="pulse">

<Tab label="📊 Doanh thu">

<Grid cols={4}>
  <BigValue data={revenue_kpi} value="net_revenue"   comparison="net_revenue_lw"   comparisonTitle="Tuần trước" title="Net Revenue (₫)"   fmt="#,##0" />
  <BigValue data={revenue_kpi} value="gross_revenue" comparison="gross_revenue_lw" comparisonTitle="Tuần trước" title="Gross Revenue (₫)" fmt="#,##0" />
  <BigValue data={revenue_kpi} value="total_orders"  comparison="total_orders_lw"  comparisonTitle="Tuần trước" title="Đơn hàng" />
  <BigValue data={revenue_kpi} value="aov"           comparison="aov_lw"           comparisonTitle="Tuần trước" title="AOV (₫)"            fmt="#,##0" />
</Grid>

---

<Grid cols={2}>
  <div style="border:1px solid #e5e7eb; border-radius:0.5rem; padding:1rem;">
    <p style="font-weight:600; font-size:0.875rem; margin-bottom:0.75rem;">🎯 Tiến độ target tháng</p>
    <Grid cols={3} gapSize="sm">
      <BigValue data={mtd_progress} value="mtd_gmv"    title="MTD GMV (₫)"  fmt="#,##0" />
      <BigValue data={mtd_progress} value="target_pct" title="% of Target"  fmt="0.0" />
      <BigValue data={mtd_progress} value="pace_index" title="Pace Index"   fmt="0.00" />
    </Grid>
    <p style="font-size:0.75rem; color:#888; margin-top:0.5rem;">Pace Index: >1.0 Ahead · 0.8–1.0 On Track · &lt;0.8 Behind</p>
  </div>
  <AreaChart
      data={daily_revenue}
      x="order_date"
      y="revenue"
      title="Net Revenue 14 ngày (₫)"
      yAxisTitle="Revenue"
  />
</Grid>

---

<DataTable data={orders_this_week} rows=20 title="Đơn hàng tuần này" />

> <Value data={data_freshness} column="freshness_msg" />

</Tab>

<Tab label="🛒 Kênh bán hàng">

<Grid cols={2}>
  <BarChart
      data={channel_mix}
      x="channel_category"
      y="revenue"
      title="Revenue by Channel Category (₫)"
      labels=true
  />
  <BarChart
      data={channel_wow}
      x="channel"
      y={["this_week", "last_week"]}
      title="Channel Revenue — TN vs TT (₫)"
      type="grouped"
      yAxisTitle="Revenue (₫)"
  />
</Grid>

---

<DataTable data={channel_performance} rows=20 title="Chi tiết hiệu suất kênh (WoW)" />

</Tab>

<Tab label="👥 Khách hàng">

<Grid cols={3}>
  <BigValue data={customer_kpi} value="new_customers"       comparison="new_customers_lw"      comparisonTitle="Tuần trước" title="Khách hàng mới" />
  <BigValue data={customer_kpi} value="returning_customers" comparison="returning_customers_lw" comparisonTitle="Tuần trước" title="Khách quay lại" />
  <BigValue data={customer_kpi} value="returning_rev_pct"   title="Returning Revenue %"         fmt="0.0" />
</Grid>

<p style="font-size:0.75rem; color: #888;">Returning Revenue %: >60% Healthy · 40–60% Warning · &lt;40% Low retention</p>

---

<BarChart
    data={new_vs_returning_trend}
    x="order_date"
    y="orders"
    series="customer_type"
    title="New vs Returning Orders (14 ngày)"
    type="stacked"
    yAxisTitle="Đơn hàng"
/>

</Tab>

<Tab label="⚠️ Cảnh báo">

<Grid cols={2}>
  <div style="border:1px solid #e5e7eb; border-radius:0.5rem; padding:1rem;">
    <p style="font-weight:600; font-size:0.875rem; margin-bottom:0.75rem;">🚨 Vận hành</p>
    <Grid cols={3} gapSize="sm">
      <BigValue data={ops_and_profit} value="cancelled_orders"  comparison="cancelled_orders_lw" comparisonTitle="Tuần trước" title="Đơn bị hủy"  upIsGood=false />
      <BigValue data={ops_and_profit} value="returns"           comparison="returns_lw"          comparisonTitle="Tuần trước" title="Trả hàng"    upIsGood=false />
      <BigValue data={ops_and_profit} value="discount_rate_pct" title="Discount Rate %"          fmt="0.0" />
    </Grid>
    <p style="font-size:0.75rem; color:#888; margin-top:0.5rem;">Discount: &lt;10% Normal · 10–15% High · >15% Alert</p>
  </div>
  <div style="border:1px solid #e5e7eb; border-radius:0.5rem; padding:1rem;">
    <p style="font-weight:600; font-size:0.875rem; margin-bottom:0.75rem;">💰 Lợi nhuận tuần này</p>
    <Grid cols={3} gapSize="sm">
      <BigValue data={ops_and_profit} value="net_profit"       comparison="net_profit_lw"       comparisonTitle="Tuần trước" title="Net Profit (₫)"  fmt="#,##0" />
      <BigValue data={ops_and_profit} value="gross_margin_pct" comparison="gross_margin_pct_lw" comparisonTitle="Tuần trước" title="Gross Margin %"  fmt="0.0" />
      <BigValue data={ops_and_profit} value="kenh_lo"          title="Kênh đang lỗ"             upIsGood=false />
    </Grid>
    <p style="font-size:0.75rem; color:#888; margin-top:0.5rem;">Profitability chỉ tính đơn có COGS (~65% coverage)</p>
  </div>
</Grid>

</Tab>

</Tabs>

---

<p style="font-size:0.75rem; color: #888;">Source: fact_orders · dim_customers · dim_channels · fact_targets · fact_order_economics · fact_order_returns</p>
