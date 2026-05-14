# Daily Sales Performance Blueprint [Retail]

**Design Spec**: [Daily Sales Dashboard (Redesign)](../designs/sales_daily_operation.md)
**Playbook**: [Daily Sales Operations](../playbooks/sales_daily_operation.md)
**Scope**: scope_retail (`customer_type = 'RETAIL'` + `is_sales_channel = true`)
**Layer**: L2 - Retail Operations

> **⚠️ SCOPE CHANGE (2026-04-19):** Dashboard này chỉ hiển thị **retail sales orders** (`customer_type = 'RETAIL'` + `is_sales_channel = true`).
> Excludes: B2B orders, US CrossBorder, System, Internal orders.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Redesigned dashboard with integrated DoD comparisons, gauge health score, section headings, and improved viz choices. Real-time monitoring — data for today, compared with yesterday. **Chỉ bao gồm retail customers.**

## 📂 Collection: Operations > Daily Monitoring

### Dashboard: Daily Sales [Retail]

**Description**: Real-time monitoring of today's **retail** sales — Health Score gauge, KPIs with integrated DoD trends, hourly patterns, channel/product/customer breakdowns across 4 tabs.

> **Database:** Sapo

---

### 📑 Tab: Tổng quan

#### 📝 Text: Đánh giá sức khỏe kinh doanh — điểm tổng hợp từ Revenue, Orders, Loyalty, AOV

# Đánh giá sức khỏe kinh doanh — điểm tổng hợp từ Revenue, Orders, Loyalty, AOV

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Review kết quả real-time — doanh thu, đơn hàng, AOV so với hôm qua

# Review kết quả real-time — doanh thu, đơn hàng, AOV so với hôm qua

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Theo dõi chỉ số hỗ trợ — khách hàng, hoàn trả, thu tiền, chiết khấu

# Theo dõi chỉ số hỗ trợ — khách hàng, hoàn trả, thu tiền, chiết khấu

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phân tích doanh thu theo giờ — peak hours và so sánh real-time

# Phân tích doanh thu theo giờ — peak hours và so sánh real-time

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Health Score

Điểm sức khỏe kinh doanh (0-100) dựa trên 4 chỉ số: Revenue Momentum, Order Momentum, Customer Loyalty, AOV Stability. So sánh 7 ngày gần nhất (kể cả hôm nay) vs 7 ngày trước đó. **Scope: Retail only.**

```sql
WITH
recent AS (
    SELECT
        COALESCE(SUM(o.net_revenue), 0) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
previous AS (
    SELECT
        COALESCE(SUM(o.net_revenue), 0) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '13 days' AND current_date - INTERVAL '7 days'
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
customer_loyalty AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '6 days' THEN o.customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
        ) as returning_rate
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
scores AS (
    SELECT
        CASE WHEN p.revenue = 0 THEN 0 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 5 THEN 25 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 0 THEN 20 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -10 THEN 15 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -25 THEN 8 ELSE 0 END as revenue_score,
        CASE WHEN p.orders = 0 THEN 0 WHEN (r.orders-p.orders)*100.0/p.orders >= 5 THEN 25 WHEN (r.orders-p.orders)*100.0/p.orders >= 0 THEN 20 WHEN (r.orders-p.orders)*100.0/p.orders >= -10 THEN 15 WHEN (r.orders-p.orders)*100.0/p.orders >= -25 THEN 8 ELSE 0 END as orders_score,
        CASE WHEN cl.returning_rate >= 50 THEN 25 WHEN cl.returning_rate >= 35 THEN 20 WHEN cl.returning_rate >= 20 THEN 12 ELSE 5 END as loyalty_score,
        CASE WHEN p.aov = 0 THEN 12 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -5 AND 15 THEN 25 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -15 AND -5 THEN 15 WHEN (r.aov-p.aov)*100.0/p.aov > 15 THEN 20 ELSE 5 END as aov_score
    FROM recent r, previous p, customer_loyalty cl
)
SELECT revenue_score + orders_score + loyalty_score + aov_score as "Health Score"
FROM scores
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 49, "color": "#EF8C8C", "label": "Báo động" },
      { "min": 49, "max": 74, "color": "#F9D45C", "label": "Chú ý" },
      { "min": 74, "max": 100, "color": "#84BB4C", "label": "Khỏe mạnh" }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 5 }
```

#### Question: Health Breakdown

Chi tiết từng thành phần của Health Score với conditional formatting.

```sql
WITH
recent AS (
    SELECT
        COALESCE(SUM(o.net_revenue), 0) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
previous AS (
    SELECT
        COALESCE(SUM(o.net_revenue), 0) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '13 days' AND current_date - INTERVAL '7 days'
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
customer_loyalty AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '6 days' THEN o.customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
        ) as returning_rate
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
),
raw_scores AS (
    SELECT
        CASE WHEN p.revenue = 0 THEN NULL ELSE ROUND((r.revenue - p.revenue) * 100.0 / p.revenue, 1) END as rev_wow,
        CASE WHEN p.orders = 0 THEN NULL ELSE ROUND((r.orders - p.orders) * 100.0 / p.orders, 1) END as ord_wow,
        cl.returning_rate,
        CASE WHEN p.aov = 0 THEN NULL ELSE ROUND((r.aov - p.aov) * 100.0 / p.aov, 1) END as aov_wow,
        CASE WHEN p.revenue = 0 THEN 0 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 5 THEN 25 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 0 THEN 20 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -10 THEN 15 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -25 THEN 8 ELSE 0 END as rev_sc,
        CASE WHEN p.orders = 0 THEN 0 WHEN (r.orders-p.orders)*100.0/p.orders >= 5 THEN 25 WHEN (r.orders-p.orders)*100.0/p.orders >= 0 THEN 20 WHEN (r.orders-p.orders)*100.0/p.orders >= -10 THEN 15 WHEN (r.orders-p.orders)*100.0/p.orders >= -25 THEN 8 ELSE 0 END as ord_sc,
        CASE WHEN cl.returning_rate >= 50 THEN 25 WHEN cl.returning_rate >= 35 THEN 20 WHEN cl.returning_rate >= 20 THEN 12 ELSE 5 END as loy_sc,
        CASE WHEN p.aov = 0 THEN 12 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -5 AND 15 THEN 25 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -15 AND -5 THEN 15 WHEN (r.aov-p.aov)*100.0/p.aov > 15 THEN 20 ELSE 5 END as aov_sc
    FROM recent r, previous p, customer_loyalty cl
)
SELECT * FROM (
    SELECT 1 as sort, 'Doanh thu (WoW)' as "Thành phần", rev_wow as "Thay đổi %", rev_sc as "Điểm",
        CASE WHEN rev_sc >= 20 THEN 'OK' WHEN rev_sc >= 15 THEN 'Chú ý' ELSE 'Báo động' END as "Status"
    FROM raw_scores
    UNION ALL
    SELECT 2, 'Đơn hàng (WoW)', ord_wow, ord_sc,
        CASE WHEN ord_sc >= 20 THEN 'OK' WHEN ord_sc >= 15 THEN 'Chú ý' ELSE 'Báo động' END
    FROM raw_scores
    UNION ALL
    SELECT 3, 'Khách quay lại', returning_rate, loy_sc,
        CASE WHEN loy_sc >= 20 THEN 'OK' WHEN loy_sc >= 12 THEN 'Chú ý' ELSE 'Báo động' END
    FROM raw_scores
    UNION ALL
    SELECT 4, 'AOV ổn định', aov_wow, aov_sc,
        CASE WHEN aov_sc >= 20 THEN 'OK' WHEN aov_sc >= 15 THEN 'Chú ý' ELSE 'Báo động' END
    FROM raw_scores
) t ORDER BY sort
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.columns": [
      { "name": "Thành phần", "enabled": true },
      { "name": "Thay đổi %", "enabled": true },
      { "name": "Điểm", "enabled": true },
      { "name": "Status", "enabled": true },
      { "name": "sort", "enabled": false }
    ],
    "table.column_formatting": [
      {
        "columns": ["Điểm"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": true
      },
      {
        "columns": ["Điểm"],
        "type": "single",
        "operator": "<",
        "value": 12,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 12, "size_y": 5 }
```

---

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Hero metric with DoD comparison vs yesterday. **Scope: Retail only.**

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.net_revenue END), 0) as "Hôm qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hôm qua",
        "label": "vs hôm qua"
      }
    ],
    "column_settings": {
      "Net Revenue": {
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
{ "row": 7, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Gross Revenue

**Domain Reference**: [Gross Revenue (GMV)](../domains/sales.md#1-gross-revenue-gmv) — Supporting KPI with DoD. **Scope: Retail only.**

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.gross_revenue END), 0) as "Gross Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.gross_revenue END), 0) as "Hôm qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hôm qua",
        "label": "vs hôm qua"
      }
    ],
    "column_settings": {
      "Gross Revenue": {
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
{"row":8, "col":6, "size_x":4, "size_y":3}
```

#### Question: Total Orders

Supporting KPI with DoD comparison. **Scope: Retail only.**

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END) as "Total Orders",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END) as "Hôm qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hôm qua",
        "label": "vs hôm qua"
      }
    ]
  }
}
```

```json metabase-pos
{"row":8, "col":10, "size_x":4, "size_y":3}
```

#### Question: AOV

Supporting KPI with DoD comparison. **Scope: Retail only.**

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END), 0
         ) END as "AOV",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END), 0
         ) END as "Hôm qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hôm qua",
        "label": "vs hôm qua"
      }
    ],
    "column_settings": {
      "AOV": {
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
{"row":8, "col":14, "size_x":4, "size_y":3}
```

---

#### Question: New Customers

**Scope: Retail only.**

```sql
SELECT COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND date(c.first_order_date) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row":12, "col":0, "size_x":3, "size_y":3}
```

#### Question: Returning Customers

**Scope: Retail only.**

```sql
SELECT COUNT(DISTINCT o.customer_key) as "Returning Customers"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND date(c.first_order_date) < current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row":12, "col":3, "size_x":3, "size_y":3}
```

#### Question: Returns

```sql
SELECT COUNT(DISTINCT o.order_id) as "Returns"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND o.fulfillment_status = 'RETURNED'
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row":12, "col":6, "size_x":3, "size_y":3}
```

#### Question: Total Collected

**Domain Reference**: [Total Collected](../domains/sales.md#2b-total-collected)

```sql
SELECT COALESCE(SUM(o.total_collected), 0) as "Total Collected"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Total Collected": {
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
{"row":12, "col":9, "size_x":3, "size_y":3}
```

#### Question: Discount Rate

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1
    ) as "Discount Rate %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row":12, "col":12, "size_x":3, "size_y":3}
```

#### Question: Items per Order

```sql
SELECT ROUND(
    SUM(s.quantity)::FLOAT / NULLIF(COUNT(DISTINCT s.order_id), 0), 1
) as "Items/Order"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(s.sol_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row":12, "col":15, "size_x":3, "size_y":3}
```

---

#### Question: Hourly Sales Trend

Compare today's hourly performance with yesterday — real-time.

**Domain Reference**: [Hourly Sales Trend](../domains/sales.md#6-hourly-sales-trend)

```sql
WITH current_sales AS (
    SELECT
        EXTRACT(HOUR FROM o.order_timestamp) as hour_of_day,
        SUM(o.net_revenue) as sales_today
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
    GROUP BY 1
),
previous_sales AS (
    SELECT
        EXTRACT(HOUR FROM o.order_timestamp) as hour_of_day,
        SUM(o.net_revenue) as sales_yesterday
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
    GROUP BY 1
)
SELECT
    COALESCE(cs.hour_of_day, ps.hour_of_day) as "Hour",
    COALESCE(cs.sales_today, 0) as "Hôm nay",
    COALESCE(ps.sales_yesterday, 0) as "Hôm qua"
FROM current_sales cs
FULL OUTER JOIN previous_sales ps ON cs.hour_of_day = ps.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Hour"],
    "graph.metrics": ["Hôm nay", "Hôm qua"],
    "graph.colors": ["#509EE3", "#C2D2E9"],
    "graph.x_axis.title_text": "Giờ trong ngày",
    "graph.y_axis.title_text": "Doanh thu"
  }
}
```

```json metabase-pos
{"row":16, "col":0, "size_x":12, "size_y":6}
```

#### Question: Cumulative Revenue

Running total — today vs yesterday, real-time.

```sql
WITH hours AS (
    SELECT UNNEST(GENERATE_SERIES(0, 23)) as hour_of_day
),
today_hourly AS (
    SELECT
        EXTRACT(HOUR FROM o.order_timestamp) as hour_of_day,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
    GROUP BY 1
),
yesterday_hourly AS (
    SELECT
        EXTRACT(HOUR FROM o.order_timestamp) as hour_of_day,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
    GROUP BY 1
)
SELECT
    h.hour_of_day as "Hour",
    COALESCE(SUM(t.revenue) OVER (ORDER BY h.hour_of_day), 0) as "Hôm nay (Lũy kế)",
    COALESCE(SUM(y.revenue) OVER (ORDER BY h.hour_of_day), 0) as "Hôm qua (Lũy kế)"
FROM hours h
LEFT JOIN today_hourly t ON h.hour_of_day = t.hour_of_day
LEFT JOIN yesterday_hourly y ON h.hour_of_day = y.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Hour"],
    "graph.metrics": ["Hôm nay (Lũy kế)", "Hôm qua (Lũy kế)"],
    "graph.colors": ["#88BF4D", "#C2D2E9"],
    "graph.x_axis.title_text": "Giờ trong ngày",
    "graph.y_axis.title_text": "Doanh thu lũy kế"
  }
}
```

```json metabase-pos
{"row":16, "col":12, "size_x":6, "size_y":6}
```

---

### 📑 Tab: Kênh bán hàng

#### 📝 Text: Xác định kênh bán hàng hiệu quả — ranking doanh thu và volume

# Xác định kênh bán hàng hiệu quả — ranking doanh thu và volume

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: So sánh hiệu suất kênh DoD — highlight kênh tăng/giảm mạnh

# So sánh hiệu suất kênh DoD — highlight kênh tăng/giảm mạnh

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phân bổ doanh thu chi nhánh — xác định nơi cần tăng cường

# Phân bổ doanh thu chi nhánh — xác định nơi cần tăng cường

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Revenue by Channel

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Horizontal bar for ranking. **Scope: Retail only.**

```sql
SELECT
    ch.channel_name as "Kênh",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kênh"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Doanh thu": {
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
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Revenue by Channel Category

Online vs Offline vs Internal breakdown.

```sql
SELECT
    ch.channel_category as "Loại kênh",
    SUM(o.net_revenue) as "Doanh thu",
    COUNT(DISTINCT o.order_id) as "Đơn hàng"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Loại kênh"],
    "graph.metrics": ["Doanh thu", "Đơn hàng"],
    "graph.colors": ["#509EE3", "#A989C5"]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

#### Question: Channel Performance vs Yesterday

DoD comparison by channel with conditional formatting on change %.

```sql
WITH today AS (
    SELECT
        ch.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(o.net_revenue), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels ch ON o.channel_key = ch.channel_key
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
    GROUP BY 1
),
yesterday AS (
    SELECT
        ch.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(o.net_revenue), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels ch ON o.channel_key = ch.channel_key
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
      AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
    GROUP BY 1
)
SELECT
    COALESCE(t.channel_name, y.channel_name) as "Kênh",
    COALESCE(t.orders, 0) as "Đơn hôm nay",
    COALESCE(y.orders, 0) as "Đơn hôm qua",
    COALESCE(t.revenue, 0) as "DT hôm nay",
    COALESCE(y.revenue, 0) as "DT hôm qua",
    CASE WHEN COALESCE(y.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(t.revenue, 0) - y.revenue) * 100.0 / y.revenue, 1) END as "Thay đổi %"
FROM today t
FULL OUTER JOIN yesterday y ON t.channel_name = y.channel_name
ORDER BY COALESCE(t.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Thay đổi %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Thay đổi %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "DT hôm nay": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "DT hôm qua": {
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```

#### Question: Sales by Branch

**Scope: Retail only.**

```sql
SELECT
    bl.branch_location_name as "Chi nhánh",
    COUNT(DISTINCT o.order_id) as "Đơn hàng",
    COALESCE(SUM(o.net_revenue), 0) as "Doanh thu",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "AOV": {
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Sản phẩm

#### 📝 Text: Xác định sản phẩm bán chạy nhất — doanh thu và số lượng

# Xác định sản phẩm bán chạy nhất — doanh thu và số lượng

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phân tích đóng góp theo loại sản phẩm

# Phân tích đóng góp theo loại sản phẩm

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top 10 Products by Revenue

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products) — Horizontal bar for visual ranking. **Scope: Retail only.**

```sql
SELECT
    p.product_name as "Sản phẩm",
    SUM(s.revenue) as "Doanh thu"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
JOIN dim_customers c ON s.customer_key = c.customer_key
WHERE date(s.sol_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Sản phẩm"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Doanh thu": {
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
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Top 10 Products by Quantity

Horizontal bar for quantity ranking. **Scope: Retail only.**

```sql
SELECT
    p.product_name as "Sản phẩm",
    SUM(s.quantity) as "Số lượng"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
JOIN dim_customers c ON s.customer_key = c.customer_key
WHERE date(s.sol_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Sản phẩm"],
    "graph.metrics": ["Số lượng"],
    "graph.colors": ["#88BDE6"]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

#### Question: Revenue by Product Type

Horizontal bar replacing pie chart. **Scope: Retail only.**

```sql
SELECT
    COALESCE(p.product_type, 'Unknown') as "Loại SP",
    SUM(s.revenue) as "Doanh thu"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
JOIN dim_customers c ON s.customer_key = c.customer_key
WHERE date(s.sol_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loại SP"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#A989C5"],
    "column_settings": {
      "Doanh thu": {
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
{ "row": 8, "col": 0, "size_x": 9, "size_y": 8 }
```

#### Question: Product Performance Table

Full detail with Qty, Revenue, Avg Price. **Scope: Retail only.**

```sql
SELECT
    p.product_name as "Sản phẩm",
    COALESCE(p.product_type, 'Unknown') as "Loại",
    SUM(s.quantity) as "SL",
    SUM(s.revenue) as "Doanh thu",
    ROUND(SUM(s.revenue) / NULLIF(SUM(s.quantity), 0), 0) as "Giá TB"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
JOIN dim_customers c ON s.customer_key = c.customer_key
WHERE date(s.sol_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1, 2
ORDER BY 4 DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Giá TB": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0
      }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 9, "size_x": 9, "size_y": 8 }
```

---

### 📑 Tab: Khách hàng & Thanh toán

#### 📝 Text: Đánh giá chân dung khách hàng — new vs returning, segment

# Đánh giá chân dung khách hàng — new vs returning, segment

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiểm tra phân bổ thanh toán và mức độ chiết khấu

# Kiểm tra phân bổ thanh toán và mức độ chiết khấu

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Returning Customer Rate

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date THEN o.customer_key END) * 100.0
        / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
    ) as "Returning Rate %"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 3, "size_y": 3 }
```

#### Question: At Risk Customers

```sql
SELECT COUNT(*) as "At Risk Customers"
FROM dim_customers
WHERE customer_status = 'At Risk'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 1, "col": 3, "size_x": 3, "size_y": 3 }
```

#### Question: New vs Returning Customers

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    CASE
        WHEN date(c.first_order_date) = current_date THEN 'Khách mới'
        ELSE 'Khách quay lại'
    END as "Loại KH",
    COUNT(DISTINCT o.order_id) as "Đơn hàng",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Loại KH"],
    "graph.metrics": ["Đơn hàng", "Doanh thu"],
    "graph.colors": ["#509EE3", "#88BF4D"],
    "column_settings": {
      "Doanh thu": {
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
{ "row": 1, "col": 6, "size_x": 12, "size_y": 3 }
```

#### Question: Revenue by Customer Segment

Breakdown by RFM-based customer segments.

```sql
SELECT
    COALESCE(c.value_group, 'Unknown') as "Phân khúc",
    COUNT(DISTINCT o.order_id) as "Đơn hàng",
    SUM(o.net_revenue) as "Doanh thu",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Phân khúc"],
    "graph.metrics": ["Doanh thu", "Đơn hàng"],
    "graph.colors": ["#509EE3", "#A989C5"],
    "column_settings": {
      "Doanh thu": {
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
{ "row": 4, "col": 0, "size_x": 18, "size_y": 6 }
```

#### Question: Orders by Status

```sql
SELECT
    o.status as "Trạng thái",
    COUNT(DISTINCT o.order_id) as "Đơn hàng"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": ["Trạng thái"],
    "pie.metric": "Đơn hàng"
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Payment Method Distribution

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "PTTT",
    COUNT(*) as "Giao dịch",
    COALESCE(SUM(p.amount), 0) as "Số tiền"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
JOIN fact_orders o ON p.order_id = o.order_id
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(p.payment_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": ["PTTT"],
    "pie.metric": "Giao dịch"
  }
}
```

```json metabase-pos
{ "row": 11, "col": 9, "size_x": 9, "size_y": 6 }
```

#### Question: Discount Impact

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact) — **⚠️ BẮT BUỘC scope_retail để tránh trộn lẫn với giá sỉ.**

```sql
SELECT
    COUNT(DISTINCT o.order_id) as "Tổng đơn",
    COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) as "Đơn có CK",
    ROUND(COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Tỷ lệ CK %",
    SUM(COALESCE(o.discount_amount, 0)) as "Tổng CK",
    ROUND(AVG(CASE WHEN o.discount_amount > 0
        THEN o.discount_amount * 100.0 / NULLIF(o.gross_revenue, 0) END), 1) as "TB CK %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Tổng CK": {
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
{ "row": 17, "col": 0, "size_x": 18, "size_y": 3 }
```

#### 📝 Text: Source & Freshness

Source: fact_orders · Updated real-time · **Scope: Retail only (customer_type = 'RETAIL')** · Excludes cancelled/voided orders

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```

---

> **Scope Note:** Tất cả queries trong blueprint này filter `customer_type = 'RETAIL'`. B2B orders (WHOLESALE, PARTNER) được track trong **B2B Daily Sales [B2B]** blueprint.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)
