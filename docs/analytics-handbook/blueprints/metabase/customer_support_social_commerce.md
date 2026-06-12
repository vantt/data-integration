---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - filter_social
  - net_revenue
  - orders_count
---

# Social Commerce Operations [Retail] Blueprint

**Design Spec**: [Social Commerce Operations](../designs/customer_support_social_commerce.md)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`filter_social`](../semantic/segments.md#filter_social) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`orders_count`](../semantic/metrics.md#orders_count)
## 📂 Collection: Operations > Daily Monitoring

### Dashboard: Social Commerce Operations [Retail]

**Description**: Theo dõi real-time doanh thu social commerce — KPIs với DoD, phân tích kênh, hiệu suất nhân viên, chi tiết đơn hàng.

---

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Monitor doanh thu Social real-time — đội social đang bán được bao nhiêu?

# Monitor doanh thu Social real-time — đội social đang bán được bao nhiêu?

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Social Revenue Today

Hero metric — Tổng doanh thu từ kênh Social hôm nay với DoD comparison.

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.ordered_at) = current_date THEN o.net_revenue END), 0) as "Doanh thu Social",
    COALESCE(SUM(CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.net_revenue END), 0) as "Hôm qua"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) >= current_date - INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu Social": {
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

#### Question: Social Orders Today

Số đơn từ kênh Social hôm nay với DoD comparison.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date THEN o.order_id END) as "Số đơn Social",
    COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.order_id END) as "Hôm qua"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) >= current_date - INTERVAL '1 day'
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

#### Question: Social AOV

Giá trị trung bình đơn Social hôm nay với DoD comparison.

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.ordered_at) = current_date THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date THEN o.order_id END), 0
         ) END as "AOV Social",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.order_id END), 0
         ) END as "Hôm qua"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) >= current_date - INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "AOV Social": {
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

#### Question: Social Share of Total

Tỷ lệ doanh thu Social / tổng doanh thu hôm nay.

```sql
WITH
total AS (
    SELECT COALESCE(SUM(net_revenue), 0) as total_rev
    FROM fact_orders
    WHERE date(ordered_at) = current_date
),
social AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as social_rev
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE c.channel_format = 'Social'
      AND date(o.ordered_at) = current_date
)
SELECT
    CASE WHEN t.total_rev = 0 THEN 0
         ELSE ROUND(s.social_rev * 100.0 / t.total_rev, 1)
    END as "% Social / Tổng"
FROM total t, social s
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "% Social / Tổng": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

#### 📝 Text: Xác định kênh drive doanh thu — Facebook vs Zalo vs Instagram đóng góp

# Xác định kênh drive doanh thu — Facebook vs Zalo vs Instagram đóng góp

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
```

#### Question: Revenue by Channel

Tỷ lệ đóng góp doanh thu theo kênh Social hôm nay — donut chart.

```sql
SELECT
    c.channel_name as "Kênh",
    COALESCE(SUM(o.net_revenue), 0) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) = current_date
GROUP BY c.channel_name
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Kênh",
    "pie.metric": "Doanh thu",
    "pie.colors": {
      "Facebook": "#509EE3",
      "Zalo": "#88BDE6",
      "Instagram": "#A989C5"
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
{"row": 7, "col":0, "size_x":6, "size_y":6}
```

#### Question: Revenue by Channel (7-day trend)

Xu hướng doanh thu theo kênh Social 7 ngày gần nhất — multi-line chart.

```sql
SELECT
    date(o.ordered_at) as "Ngày",
    c.channel_name as "Kênh",
    COALESCE(SUM(o.net_revenue), 0) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) >= current_date - INTERVAL '6 days'
GROUP BY date(o.ordered_at), c.channel_name
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngày", "Kênh"],
    "graph.metrics": ["Doanh thu"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Doanh thu",
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5"],
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
{"row": 7, "col":6, "size_x":12, "size_y":6}
```

#### 📝 Text: Đánh giá hiệu suất nhân viên — ranking và xử lý kịp thời

# Đánh giá hiệu suất nhân viên — ranking và xử lý kịp thời

```json metabase-pos
{"row": 13, "col":0, "size_x":18, "size_y":1}
```

#### Question: Top Agents by Revenue

Ranking nhân viên theo doanh thu Social hôm nay — horizontal bar.

```sql
SELECT
    s.full_name as "Nhân viên",
    COALESCE(SUM(o.net_revenue), 0) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) = current_date
GROUP BY s.full_name
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhân viên"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Doanh thu",
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{"row": 14, "col":0, "size_x":9, "size_y":6}
```

#### Question: Top Agents by Orders

Ranking nhân viên theo số đơn Social hôm nay — horizontal bar.

```sql
SELECT
    s.full_name as "Nhân viên",
    COUNT(DISTINCT o.order_id) as "Số đơn"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) = current_date
GROUP BY s.full_name
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhân viên"],
    "graph.metrics": ["Số đơn"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Số đơn"
  }
}
```

```json metabase-pos
{"row": 14, "col":9, "size_x":9, "size_y":6}
```

#### 📝 Text: Review chi tiết nhân viên — xác định ai cần hỗ trợ thêm

# Review chi tiết nhân viên — xác định ai cần hỗ trợ thêm

```json metabase-pos
{"row": 20, "col":0, "size_x":18, "size_y":1}
```

#### Question: Agent Performance Table

Chi tiết hiệu suất nhân viên Social với DoD comparison — conditional formatting trên cột thay đổi %.

```sql
WITH
today AS (
    SELECT
        s.full_name,
        COALESCE(SUM(o.net_revenue), 0) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    JOIN dim_staff s ON o.seller_staff_key = s.staff_key
    WHERE c.channel_format = 'Social'
      AND date(o.ordered_at) = current_date
    GROUP BY s.full_name
),
yesterday AS (
    SELECT
        s.full_name,
        COALESCE(SUM(o.net_revenue), 0) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    JOIN dim_staff s ON o.seller_staff_key = s.staff_key
    WHERE c.channel_format = 'Social'
      AND date(o.ordered_at) = current_date - INTERVAL '1 day'
    GROUP BY s.full_name
)
SELECT
    COALESCE(t.full_name, y.full_name) as "Nhân viên",
    COALESCE(t.revenue, 0) as "Doanh thu",
    COALESCE(t.orders, 0) as "Số đơn",
    CASE WHEN COALESCE(t.orders, 0) = 0 THEN 0
         ELSE ROUND(COALESCE(t.revenue, 0) * 1.0 / t.orders, 0)
    END as "AOV",
    COALESCE(y.revenue, 0) as "DT hôm qua",
    CASE WHEN COALESCE(y.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(t.revenue, 0) - y.revenue) * 100.0 / y.revenue, 1)
    END as "Thay đổi DT %"
FROM today t
FULL OUTER JOIN yesterday y ON t.full_name = y.full_name
ORDER BY COALESCE(t.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.columns": [
      { "name": "Nhân viên", "enabled": true },
      { "name": "Doanh thu", "enabled": true },
      { "name": "Số đơn", "enabled": true },
      { "name": "AOV", "enabled": true },
      { "name": "DT hôm qua", "enabled": true },
      { "name": "Thay đổi DT %", "enabled": true }
    ],
    "table.column_formatting": [
      {
        "columns": ["Thay đổi DT %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Thay đổi DT %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
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
      },
      "DT hôm qua": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Thay đổi DT %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 21, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Kiểm tra đơn hàng mới nhất — xác nhận pipeline real-time

# Kiểm tra đơn hàng mới nhất — xác nhận pipeline real-time

```json metabase-pos
{"row": 27, "col":0, "size_x":18, "size_y":1}
```

#### Question: Recent Social Orders

20 đơn hàng Social mới nhất — kiểm tra real-time.

```sql
SELECT
    o.ordered_at as "Thời gian",
    o.order_code as "Mã đơn",
    c.channel_name as "Kênh",
    s.full_name as "Nhân viên",
    o.net_revenue as "Doanh thu",
    o.status as "Trạng thái"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
LEFT JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE c.channel_format = 'Social'
  AND date(o.ordered_at) = current_date
ORDER BY o.ordered_at DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.columns": [
      { "name": "Thời gian", "enabled": true },
      { "name": "Mã đơn", "enabled": true },
      { "name": "Kênh", "enabled": true },
      { "name": "Nhân viên", "enabled": true },
      { "name": "Doanh thu", "enabled": true },
      { "name": "Trạng thái", "enabled": true }
    ],
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Mã đơn\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Mã đơn}}"
        }
      }
    }
  }
}
```

```json metabase-pos
{"row": 28, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders · **Cadence:** daily · **Scope:** channel_format='Social'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

