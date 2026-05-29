# US CrossBorder Operations Blueprint [US]

**Scope**: scope_us (`channel_name = 'US'` / `channel_format = 'CrossBorder Fulfillment'`)
**Layer**: L2 - CrossBorder Operations

> **NEW (2026-04-19):** Dashboard rieng cho don US CrossBorder Fulfillment.
> Tach biet hoan toan khoi bao cao Sales vi day la don export/arrangement, khong phai sales thuong.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Daily monitoring for US CrossBorder fulfillment orders — export arrangements, order tracking, fulfillment status. Special operations for international orders.

## 📂 Collection: Operations > US CrossBorder

> **Database:** Sapo

### Dashboard: US CrossBorder Daily [US]

**Description**: Daily monitoring of US CrossBorder orders — revenue tracking, order status, fulfillment pipeline. 2 tabs: Tong quan, Chi tiet don hang.

---

### 📑 Tab: Tong quan

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y')
  AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Don US CrossBorder hom nay — export va arrangement

# Don US CrossBorder hom nay — export va arrangement

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Net Revenue (US)

US CrossBorder revenue today vs yesterday.

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.net_revenue END), 0) as "Hom qua"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
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
{"row": 3, "col":0, "size_x":6, "size_y":3}
```

#### Question: Total Orders (US)

US CrossBorder order count today vs yesterday.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END) as "Total Orders",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END) as "Hom qua"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{"row": 3, "col":6, "size_x":4, "size_y":3}
```

#### Question: AOV (US)

Average order value for US CrossBorder.

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.net_revenue END) /
              COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END), 0) END as "AOV",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.net_revenue END) /
              COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END), 0) END as "Hom qua"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
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
{"row": 3, "col":10, "size_x":4, "size_y":3}
```

#### Question: Unique Customers (US)

Distinct customers ordering via US channel today.

```sql
SELECT
    COUNT(DISTINCT o.customer_key) as "Khach hang"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

#### 📝 Text: Trang thai don va fulfillment

# Trang thai don va fulfillment

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
```

#### Question: Orders by Status (US)

Distribution of order statuses for US CrossBorder.

```sql
SELECT
    o.status as "Trang thai",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date
  AND ch.channel_name = 'US'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Trang thai"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{"row": 7, "col":0, "size_x":9, "size_y":5}
```

#### Question: Fulfillment Status (US)

Distribution of fulfillment statuses for US CrossBorder.

```sql
SELECT
    COALESCE(o.fulfillment_status, 'Unknown') as "Fulfillment",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date
  AND ch.channel_name = 'US'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Fulfillment"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#88BF4D"]
  }
}
```

```json metabase-pos
{"row": 7, "col":9, "size_x":9, "size_y":5}
```

#### 📝 Text: Xu huong 7 ngay

# Xu huong 7 ngay

```json metabase-pos
{"row": 12, "col":0, "size_x":18, "size_y":1}
```

#### Question: US Revenue Trend (7 Days)

Daily revenue trend for US CrossBorder over last 7 days.

```sql
SELECT
    date(o.order_timestamp) as "Ngay",
    SUM(o.net_revenue) as "Doanh thu",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '6 days'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Doanh thu", "So don"],
    "graph.colors": ["#509EE3", "#EF8C8C"],
    "series_settings": {
      "Doanh thu": { "display": "bar" },
      "So don": { "display": "line", "axis": "right" }
    },
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
{"row": 13, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Danh sach don US hom nay

# Danh sach don US hom nay

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: US Orders List

Detailed list of US CrossBorder orders today.

```sql
SELECT
    o.order_code as "Ma don",
    date(o.order_timestamp) as "Ngay",
    COALESCE(c.full_name, 'Unknown') as "Khach hang",
    o.status as "Trang thai",
    o.fulfillment_status as "Fulfillment",
    o.payment_status as "Thanh toan"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND ch.channel_name = 'US'
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": { "table.pivot": false }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 12 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders · **Cadence:** daily · **Scope:** channel='US CrossBorder' · **Caveats:** Export arrangement
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Tuan nay

#### ❓ Question: Chu kỳ báo cáo (Weekly)

```sql
SELECT
  '📅 Tuần này: ' || strftime(date_trunc('week', current_date), '%d/%m/%Y') ||
  ' → ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Tuần trước: ' || strftime(date_trunc('week', current_date) - INTERVAL '7 days', '%d/%m/%Y') ||
  ' → ' || strftime(date_trunc('week', current_date) - INTERVAL '1 day', '%d/%m/%Y')
  AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Don US CrossBorder tuan nay

# Don US CrossBorder tuan nay

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Net Revenue (Weekly)

US CrossBorder net revenue this week vs last week.

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date)
                       AND date(o.order_timestamp) <= current_date THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
                       AND date(o.order_timestamp) <  date_trunc('week', current_date) THEN o.net_revenue END), 0) as "Tuan truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Total Orders (Weekly)

US CrossBorder order count this week vs last week.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date)
                          AND date(o.order_timestamp) <= current_date THEN o.order_id END) as "Total Orders",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
                          AND date(o.order_timestamp) <  date_trunc('week', current_date) THEN o.order_id END) as "Tuan truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: AOV (Weekly)

Average order value for US CrossBorder this week vs last week.

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date)
                                    AND date(o.order_timestamp) <= current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date)
                              AND date(o.order_timestamp) <= current_date THEN o.net_revenue END) /
              COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date)
                                    AND date(o.order_timestamp) <= current_date THEN o.order_id END), 0) END as "AOV",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
                                    AND date(o.order_timestamp) <  date_trunc('week', current_date) THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
                              AND date(o.order_timestamp) <  date_trunc('week', current_date) THEN o.net_revenue END) /
              COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
                                    AND date(o.order_timestamp) <  date_trunc('week', current_date) THEN o.order_id END), 0) END as "Tuan truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Unique Customers (Weekly)

Distinct customers this week vs last week.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date)
                          AND date(o.order_timestamp) <= current_date THEN o.customer_key END) as "Khach hang",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
                          AND date(o.order_timestamp) <  date_trunc('week', current_date) THEN o.customer_key END) as "Tuan truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
```

#### 📝 Text: Phan phoi trang thai (Weekly)

# Phan phoi trang thai

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Status (Weekly)

Order status distribution this week.

```sql
SELECT
    o.status as "Trang thai",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Trang thai"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Fulfillment Status (Weekly)

Fulfillment status distribution this week.

```sql
SELECT
    COALESCE(o.fulfillment_status, 'Unknown') as "Fulfillment",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Fulfillment"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#88BF4D"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 9, "size_x": 9, "size_y": 5 }
```

#### 📝 Text: Xu huong tung ngay trong tuan

# Xu huong tung ngay trong tuan

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Daily Trend This Week (US)

Daily order count trend within the current calendar week.

```sql
SELECT
    date(o.order_timestamp) as "Ngay",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Danh sach don tuan nay

# Danh sach don tuan nay

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: US Orders List (Weekly)

List of US CrossBorder orders this week.

```sql
SELECT
    o.order_code as "Ma don",
    date(o.order_timestamp) as "Ngay",
    COALESCE(c.full_name, 'Unknown') as "Khach hang",
    o.status as "Trang thai",
    o.fulfillment_status as "Fulfillment",
    o.payment_status as "Thanh toan"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= date_trunc('week', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": { "table.pivot": false }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 12 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders · **Cadence:** daily · **Scope:** channel='US CrossBorder' · **Caveats:** Export arrangement
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Thang nay

#### ❓ Question: Chu kỳ báo cáo (Monthly)

```sql
SELECT
  '📅 Tháng này: ' || strftime(date_trunc('month', current_date), '%d/%m/%Y') ||
  ' → ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Tháng trước: ' || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') ||
  ' → ' || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y')
  AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Don US CrossBorder thang nay

# Don US CrossBorder thang nay

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Net Revenue (Monthly)

US CrossBorder net revenue this month vs last month.

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date)
                       AND date(o.order_timestamp) <= current_date THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
                       AND date(o.order_timestamp) <  date_trunc('month', current_date) THEN o.net_revenue END), 0) as "Thang truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Total Orders (Monthly)

US CrossBorder order count this month vs last month.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date)
                          AND date(o.order_timestamp) <= current_date THEN o.order_id END) as "Total Orders",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
                          AND date(o.order_timestamp) <  date_trunc('month', current_date) THEN o.order_id END) as "Thang truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: AOV (Monthly)

Average order value for US CrossBorder this month vs last month.

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date)
                                    AND date(o.order_timestamp) <= current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date)
                              AND date(o.order_timestamp) <= current_date THEN o.net_revenue END) /
              COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date)
                                    AND date(o.order_timestamp) <= current_date THEN o.order_id END), 0) END as "AOV",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
                                    AND date(o.order_timestamp) <  date_trunc('month', current_date) THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(SUM(CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
                              AND date(o.order_timestamp) <  date_trunc('month', current_date) THEN o.net_revenue END) /
              COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
                                    AND date(o.order_timestamp) <  date_trunc('month', current_date) THEN o.order_id END), 0) END as "Thang truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Unique Customers (Monthly)

Distinct customers this month vs last month.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date)
                          AND date(o.order_timestamp) <= current_date THEN o.customer_key END) as "Khach hang",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
                          AND date(o.order_timestamp) <  date_trunc('month', current_date) THEN o.customer_key END) as "Thang truoc"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
```

#### 📝 Text: Phan phoi trang thai (Monthly)

# Phan phoi trang thai

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Status (Monthly)

Order status distribution this month.

```sql
SELECT
    o.status as "Trang thai",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Trang thai"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Fulfillment Status (Monthly)

Fulfillment status distribution this month.

```sql
SELECT
    COALESCE(o.fulfillment_status, 'Unknown') as "Fulfillment",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Fulfillment"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#88BF4D"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 9, "size_x": 9, "size_y": 5 }
```

#### 📝 Text: Xu huong tung tuan trong thang

# Xu huong tung tuan trong thang

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Weekly Trend This Month (US)

Weekly order count within the current calendar month.

```sql
SELECT
    date_trunc('week', date(o.order_timestamp)) as "Tuan",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Tuan"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Danh sach don thang nay

# Danh sach don thang nay

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: US Orders List (Monthly)

List of US CrossBorder orders this month.

```sql
SELECT
    o.order_code as "Ma don",
    date(o.order_timestamp) as "Ngay",
    COALESCE(c.full_name, 'Unknown') as "Khach hang",
    o.status as "Trang thai",
    o.fulfillment_status as "Fulfillment",
    o.payment_status as "Thanh toan"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= date_trunc('month', current_date)
  AND date(o.order_timestamp) <= current_date
  AND ch.channel_name = 'US'
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": { "table.pivot": false }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 12 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders · **Cadence:** daily · **Scope:** channel='US CrossBorder' · **Caveats:** Export arrangement
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

