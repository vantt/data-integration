# US CrossBorder Operations Blueprint [US]

**Scope**: scope_us (`channel_name = 'US'` / `channel_format = 'CrossBorder Fulfillment'`)
**Layer**: L2 - CrossBorder Operations

> **NEW (2026-04-19):** Dashboard rieng cho don US CrossBorder Fulfillment.
> Tach biet hoan toan khoi bao cao Sales vi day la don export/arrangement, khong phai sales thuong.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Daily monitoring for US CrossBorder fulfillment orders — export arrangements, order tracking, fulfillment status. Special operations for international orders.

## 📂 Collection: Operations > CrossBorder Operations

> **Database:** Sapo DuckDB

### Dashboard: US CrossBorder Daily [US]

**Description**: Daily monitoring of US CrossBorder orders — revenue tracking, order status, fulfillment pipeline. 2 tabs: Tong quan, Chi tiet don hang.

---

### 📑 Tab: Tong quan

#### 📝 Text: Don US CrossBorder hom nay — export va arrangement

# Don US CrossBorder hom nay — export va arrangement

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
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
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
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
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
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
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

#### 📝 Text: Trang thai don va fulfillment

# Trang thai don va fulfillment

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 5, "col": 0, "size_x": 9, "size_y": 5 }
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
{ "row": 5, "col": 9, "size_x": 9, "size_y": 5 }
```

#### 📝 Text: Xu huong 7 ngay

# Xu huong 7 ngay

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 11, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Chi tiet don hang

#### 📝 Text: Chu kỳ báo cáo

📅 **Chu kỳ báo cáo:** Hôm nay (rolling đến hiện tại, ICT) | **So sánh:** Hôm qua (D-1) | **Cập nhật:** Real-time
<!-- text-id:chu-ky-bao-cao -->

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh sach don US hom nay

# Danh sach don US hom nay

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: US Orders List

Detailed list of US CrossBorder orders today.

```sql
SELECT
    o.order_code as "Ma don",
    date(o.order_timestamp) as "Ngay",
    c.customer_name as "Khach hang",
    o.net_revenue as "Doanh thu",
    o.status as "Trang thai",
    o.fulfillment_status as "Fulfillment",
    o.payment_status as "Thanh toan"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND ch.channel_name = 'US'
ORDER BY o.order_timestamp DESC
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
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 18, "size_y": 12 }
```

#### 📝 Text: Source & Freshness

**Source**: fact_orders, dim_channels, dim_customers  
**Freshness**: Real-time (current_date filter)  
**Scope**: US channel only (CrossBorder Fulfillment)

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```
