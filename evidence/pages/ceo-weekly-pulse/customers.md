---
title: CEO Weekly Pulse — Khách hàng & Cảnh báo
---

# CEO Weekly Pulse [All]

<a href="/ceo-weekly-pulse">Doanh thu & Target</a> · <a href="/ceo-weekly-pulse/channels">Kênh bán hàng</a> · <a href="/ceo-weekly-pulse/customers">Khách hàng & Cảnh báo</a>

> **Scope:** All sales channels · Tuần này (Mon-to-date) vs WoW

---

## Sức khỏe khách hàng

```sql customer_kpi
WITH
new_tw AS (
    SELECT COUNT(DISTINCT customer_key) AS val
    FROM main_marts.dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date)
      AND date(first_order_date) <= current_date
),
new_lw AS (
    SELECT COUNT(DISTINCT customer_key) AS val
    FROM main_marts.dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(first_order_date) < date_trunc('week', current_date)
),
returning_tw AS (
    SELECT COUNT(DISTINCT o.customer_key) AS val
    FROM main_marts.fact_orders o
    LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
      AND date(c.first_order_date) < date_trunc('week', current_date)
),
returning_lw AS (
    SELECT COUNT(DISTINCT o.customer_key) AS val
    FROM main_marts.fact_orders o
    LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
      AND date(c.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
),
returning_rev AS (
    SELECT
        ROUND(
            SUM(CASE WHEN date(c.first_order_date) < date_trunc('week', current_date)
                     THEN o.net_revenue ELSE 0 END) * 100.0
            / NULLIF(SUM(o.net_revenue), 0), 1
        ) AS returning_rev_pct
    FROM main_marts.fact_orders o
    LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
)
SELECT
    ntw.val  AS new_customers,
    nlw.val  AS new_customers_lw,
    rtw.val  AS returning_customers,
    rlw.val  AS returning_customers_lw,
    rr.returning_rev_pct
FROM new_tw ntw, new_lw nlw, returning_tw rtw, returning_lw rlw, returning_rev rr
```

<BigValue data={customer_kpi} value="new_customers"       comparison="new_customers_lw"       comparisonTitle="Tuần trước" title="Khách hàng mới" />
<BigValue data={customer_kpi} value="returning_customers" comparison="returning_customers_lw"  comparisonTitle="Tuần trước" title="Khách hàng quay lại" />
<BigValue data={customer_kpi} value="returning_rev_pct"   title="Returning Revenue %" fmt="0.0" />

> **Returning Revenue %:** >60% = Healthy · 40–60% = Warning · {'<'}40% = Low retention

---

## New vs Returning (14 ngày)

```sql new_vs_returning_trend
SELECT
    date(o.ordered_at)                                                              AS order_date,
    CASE WHEN date(c.first_order_date) = date(o.ordered_at) THEN 'New'
         ELSE 'Returning' END                                                       AS customer_type,
    COUNT(DISTINCT o.order_id)                                                      AS orders
FROM main_marts.fact_orders o
LEFT JOIN main_marts.dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1, 2
ORDER BY 1, 2
```

<BarChart
    data={new_vs_returning_trend}
    x="order_date"
    y="orders"
    series="customer_type"
    title="New vs Returning Orders (14 ngày)"
    type="stacked"
    yAxisTitle="Đơn hàng"
/>

---

## Cảnh báo vận hành

```sql ops_alerts
WITH
cancelled_tw AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM main_marts.fact_orders
    WHERE NOT is_active_order AND scope_sales
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
cancelled_lw AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM main_marts.fact_orders
    WHERE NOT is_active_order AND scope_sales
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
),
returns_tw AS (
    SELECT COUNT(DISTINCT r.return_id) AS val
    FROM main_marts.fact_order_returns r
    JOIN main_marts.dim_channels c ON r.channel_key = c.channel_key
    WHERE c.is_sales_channel AND r.return_status = 'returned'
      AND r.returned_at >= date_trunc('week', current_date)
      AND r.returned_at < current_date + INTERVAL '1 day'
),
returns_lw AS (
    SELECT COUNT(DISTINCT r.return_id) AS val
    FROM main_marts.fact_order_returns r
    JOIN main_marts.dim_channels c ON r.channel_key = c.channel_key
    WHERE c.is_sales_channel AND r.return_status = 'returned'
      AND r.returned_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND r.returned_at < date_trunc('week', current_date)
),
discount AS (
    SELECT ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) AS discount_rate_pct
    FROM main_marts.fact_orders
    WHERE scope_sales AND is_active_order
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
)
SELECT
    ctw.val  AS cancelled_orders,
    clw.val  AS cancelled_orders_lw,
    rtw.val  AS returns,
    rlw.val  AS returns_lw,
    d.discount_rate_pct
FROM cancelled_tw ctw, cancelled_lw clw, returns_tw rtw, returns_lw rlw, discount d
```

<BigValue data={ops_alerts} value="cancelled_orders" comparison="cancelled_orders_lw" comparisonTitle="Tuần trước" title="Đơn bị hủy"     upIsGood=false />
<BigValue data={ops_alerts} value="returns"          comparison="returns_lw"          comparisonTitle="Tuần trước" title="Trả hàng"       upIsGood=false />
<BigValue data={ops_alerts} value="discount_rate_pct" title="Discount Rate %" fmt="0.0" />

> **Discount Rate:** {'<'}10% Normal · 10–15% High · >15% Alert

---

## Lợi nhuận tuần này

```sql profitability
WITH
this_week AS (
    SELECT
        COALESCE(SUM(e.channel_net_profit), 0)                              AS net_profit,
        ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS gross_margin_pct
    FROM main_marts.fact_order_economics e
    JOIN main_marts.fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales AND e.has_cogs AND e.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT
        COALESCE(SUM(e.channel_net_profit), 0)                              AS net_profit_lw,
        ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS gross_margin_pct_lw
    FROM main_marts.fact_order_economics e
    JOIN main_marts.fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales AND e.has_cogs AND e.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
),
loss_channels AS (
    SELECT COUNT(*) AS kenh_lo
    FROM (
        SELECT e.channel_key
        FROM main_marts.fact_order_economics e
        JOIN main_marts.fact_orders o ON e.order_id = o.order_id
        WHERE e.scope_sales AND e.has_cogs AND o.is_active_order
          AND o.ordered_at >= date_trunc('week', current_date)
          AND o.ordered_at < current_date + INTERVAL '1 day'
        GROUP BY e.channel_key
        HAVING SUM(e.channel_net_profit) < 0
    ) lc
)
SELECT tw.*, lw.*, lc.kenh_lo
FROM this_week tw, last_week lw, loss_channels lc
```

<BigValue data={profitability} value="net_profit"       comparison="net_profit_lw"       comparisonTitle="Tuần trước" title="Net Profit (₫)"  fmt="#,##0" />
<BigValue data={profitability} value="gross_margin_pct" comparison="gross_margin_pct_lw"  comparisonTitle="Tuần trước" title="Gross Margin %"  fmt="0.0" />
<BigValue data={profitability} value="kenh_lo"          title="Kênh đang lỗ" upIsGood=false />

> **Lưu ý:** Profitability chỉ tính đơn có COGS (`has_cogs = true`, ~65% coverage). Đơn chưa có MISA không được tính.

---

**Source:** `fact_orders` + `dim_customers` + `fact_order_economics` + `fact_order_returns` · **Scope:** `is_sales_channel=true`, exclude CANCELLED/DRAFT
