---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L2
uses_concepts: [scope_sales, net_revenue, fulfillment_status]
---

# Logistics Operations Center Blueprint [All]

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` · Layer L2 `[All]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales)
> **Why:** Logistics operations covers fulfillment status for all orders regardless of customer segment — shipping performance applies equally to retail and B2B shipments.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`fulfillment_status`](../semantic/dimensions.md#fulfillment_status)

All SQL: `WHERE scope_sales`. Segment breakdown optional as a dimension.
## 📂 Collection: Operations > Logistics

### Dashboard: Logistics Operations Center [All]

**Description**: Real-time logistics monitoring — Fulfillment Rate gauge, order pipeline funnel, processing speed KPIs with DoD, hourly trends, stuck orders escalation, staff performance across 3 tabs.

---

### 📑 Tab: Tổng quan

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

#### 📝 Text: Monitor pipeline đơn hàng — trạng thái xử lý và fulfillment rate

# Monitor pipeline đơn hàng — trạng thái xử lý và fulfillment rate

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Fulfillment Rate

Tỷ lệ đơn đã xuất kho / tổng đơn eligible (không DRAFT, không CANCELLED). Gauge 3 zones.

```sql
SELECT ROUND(
    COUNT(CASE WHEN fulfillment_status = 'fulfilled' THEN 1 END) * 100.0
    / NULLIF(COUNT(*), 0), 1
) as "Fulfillment Rate"
FROM fact_orders
WHERE status NOT IN ('DRAFT', 'CANCELLED')
  AND date(ordered_at) = current_date
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 84, "color": "#EF8C8C", "label": "Báo động" },
      { "min": 84, "max": 94, "color": "#F9D45C", "label": "Chú ý" },
      { "min": 94, "max": 100, "color": "#84BB4C", "label": "Tốt" }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":6, "size_y":5}
```

#### Question: Tổng đơn hôm nay

Tổng đơn hàng hôm nay (trừ DRAFT) với DoD comparison.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(ordered_at) = current_date THEN order_id END) as "Tổng đơn",
    COUNT(DISTINCT CASE WHEN date(ordered_at) = current_date - INTERVAL '1 day' THEN order_id END) as "Hôm qua"
FROM fact_orders
WHERE status != 'DRAFT'
  AND date(ordered_at) >= current_date - INTERVAL '1 day'
  AND date(ordered_at) <= current_date
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

#### Question: Đơn đã xuất kho

Đơn đã fulfilled hôm nay với DoD comparison.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(ordered_at) = current_date AND fulfillment_status = 'fulfilled' THEN order_id END) as "Đã xuất kho",
    COUNT(DISTINCT CASE WHEN date(ordered_at) = current_date - INTERVAL '1 day' AND fulfillment_status = 'fulfilled' THEN order_id END) as "Hôm qua"
FROM fact_orders
WHERE status NOT IN ('DRAFT', 'CANCELLED')
  AND date(ordered_at) >= current_date - INTERVAL '1 day'
  AND date(ordered_at) <= current_date
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":10, "size_x":4, "size_y":3}
```

#### Question: Thời gian hoàn thành TB

Thời gian hoàn thành trung bình (giờ) hôm nay với DoD comparison. Lower = good (inverted).

```sql
SELECT
    ROUND(AVG(CASE WHEN date(updated_at) = current_date THEN time_to_complete_hours END), 1) as "TB hoàn thành (h)",
    ROUND(AVG(CASE WHEN date(updated_at) = current_date - INTERVAL '1 day' THEN time_to_complete_hours END), 1) as "Hôm qua"
FROM fact_orders
WHERE status = 'COMPLETED'
  AND time_to_complete_hours IS NOT NULL
  AND date(updated_at) >= current_date - INTERVAL '1 day'
  AND date(updated_at) <= current_date
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

---

#### 📝 Text: Kiểm tra phân bổ trạng thái — drop-off ở bước nào?

# Kiểm tra phân bổ trạng thái — drop-off ở bước nào?

```json metabase-pos
{"row": 8, "col":0, "size_x":18, "size_y":1}
```

#### Question: Phễu trạng thái đơn

Drop-off theo từng bước pipeline: OPEN → COMPLETED → CANCELLED → ARCHIVED.

```sql
SELECT status as "Trạng thái", COUNT(*) as "Số đơn"
FROM fact_orders
WHERE status != 'DRAFT'
  AND date(ordered_at) = current_date
GROUP BY status
ORDER BY CASE status
    WHEN 'OPEN' THEN 1
    WHEN 'COMPLETED' THEN 2
    WHEN 'CANCELLED' THEN 3
    WHEN 'ARCHIVED' THEN 4
END
```

```json metabase-viz
{
  "display": "funnel",
  "visualization_settings": {
    "graph.dimensions": ["Trạng thái"],
    "graph.metrics": ["Số đơn"]
  }
}
```

```json metabase-pos
{"row": 9, "col":0, "size_x":9, "size_y":6}
```

#### Question: Fulfillment Status Breakdown

Tỷ lệ fulfilled / unfulfilled / partial — donut chart.

```sql
SELECT
    fulfillment_status as "Trạng thái XK",
    COUNT(*) as "Số đơn"
FROM fact_orders
WHERE status NOT IN ('DRAFT', 'CANCELLED')
  AND date(ordered_at) = current_date
GROUP BY fulfillment_status
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{"row": 9, "col":9, "size_x":9, "size_y":6}
```

---

#### 📝 Text: Phân tích lượng đơn theo giờ — peak hours và pattern DoD

# Phân tích lượng đơn theo giờ — peak hours và pattern DoD

```json metabase-pos
{"row": 15, "col":0, "size_x":18, "size_y":1}
```

#### Question: Đơn hàng theo giờ (DoD)

So sánh lượng đơn theo giờ hôm nay vs hôm qua — peak hours, real-time pattern.

```sql
WITH current_orders AS (
    SELECT
        EXTRACT(HOUR FROM ordered_at) as hour_of_day,
        COUNT(*) as orders_today
    FROM fact_orders
    WHERE status NOT IN ('DRAFT', 'CANCELLED')
      AND date(ordered_at) = current_date
    GROUP BY 1
),
previous_orders AS (
    SELECT
        EXTRACT(HOUR FROM ordered_at) as hour_of_day,
        COUNT(*) as orders_yesterday
    FROM fact_orders
    WHERE status NOT IN ('DRAFT', 'CANCELLED')
      AND date(ordered_at) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(c.hour_of_day, p.hour_of_day) as "Giờ",
    COALESCE(c.orders_today, 0) as "Hôm nay",
    COALESCE(p.orders_yesterday, 0) as "Hôm qua"
FROM current_orders c
FULL OUTER JOIN previous_orders p ON c.hour_of_day = p.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Giờ"],
    "graph.metrics": ["Hôm nay", "Hôm qua"],
    "graph.colors": ["#509EE3", "#C2D2E9"],
    "graph.x_axis.title_text": "Giờ trong ngày",
    "graph.y_axis.title_text": "Số đơn"
  }
}
```

```json metabase-pos
{"row": 16, "col":0, "size_x":12, "size_y":6}
```

#### Question: Đơn hàng lũy kế (DoD)

Running total đơn hàng hôm nay vs hôm qua — cumulative comparison.

```sql
WITH hours AS (
    SELECT UNNEST(GENERATE_SERIES(0, 23)) as hour_of_day
),
current_orders AS (
    SELECT
        EXTRACT(HOUR FROM ordered_at) as hour_of_day,
        COUNT(*) as cnt
    FROM fact_orders
    WHERE status NOT IN ('DRAFT', 'CANCELLED')
      AND date(ordered_at) = current_date
    GROUP BY 1
),
previous_orders AS (
    SELECT
        EXTRACT(HOUR FROM ordered_at) as hour_of_day,
        COUNT(*) as cnt
    FROM fact_orders
    WHERE status NOT IN ('DRAFT', 'CANCELLED')
      AND date(ordered_at) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    h.hour_of_day as "Giờ",
    SUM(COALESCE(c.cnt, 0)) OVER (ORDER BY h.hour_of_day) as "Hôm nay",
    SUM(COALESCE(p.cnt, 0)) OVER (ORDER BY h.hour_of_day) as "Hôm qua"
FROM hours h
LEFT JOIN current_orders c ON h.hour_of_day = c.hour_of_day
LEFT JOIN previous_orders p ON h.hour_of_day = p.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Giờ"],
    "graph.metrics": ["Hôm nay", "Hôm qua"],
    "graph.colors": ["#7172AD", "#C2D2E9"],
    "graph.x_axis.title_text": "Giờ trong ngày",
    "graph.y_axis.title_text": "Lũy kế đơn"
  }
}
```

```json metabase-pos
{"row": 16, "col":12, "size_x":6, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_logistics · **Cadence:** daily · **Scope:** Active fulfillment · **Caveats:** Realtime + 7d trend
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Tốc độ xử lý


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') || '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Đánh giá tốc độ xử lý — time to ship và bottleneck

# Đánh giá tốc độ xử lý — time to ship và bottleneck

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: TB giờ đến xuất kho

Thời gian trung bình từ tạo đơn đến xuất kho đầu tiên. DoD comparison, lower = good.

```sql
SELECT
    ROUND(AVG(CASE
        WHEN date(first_shipped_at) = current_date
        THEN date_diff('hour', ordered_at, first_shipped_at)
    END), 1) as "TB giờ xuất kho",
    ROUND(AVG(CASE
        WHEN date(first_shipped_at) = current_date - INTERVAL '1 day'
        THEN date_diff('hour', ordered_at, first_shipped_at)
    END), 1) as "Hôm qua"
FROM fact_orders
WHERE first_shipped_at IS NOT NULL
  AND status NOT IN ('DRAFT', 'CANCELLED')
  AND date(first_shipped_at) >= current_date - INTERVAL '1 day'
  AND date(first_shipped_at) <= current_date
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 4 }
```

#### Question: Tỷ lệ xuất cùng ngày

Same-day ship rate hôm nay với DoD comparison.

```sql
SELECT
    ROUND(
        COUNT(CASE
            WHEN date(first_shipped_at) = current_date
             AND date(first_shipped_at) = date(ordered_at) THEN 1 END) * 100.0
        / NULLIF(COUNT(CASE
            WHEN date(first_shipped_at) = current_date THEN 1 END), 0), 1
    ) as "Xuất cùng ngày %",
    ROUND(
        COUNT(CASE
            WHEN date(first_shipped_at) = current_date - INTERVAL '1 day'
             AND date(first_shipped_at) = date(ordered_at) THEN 1 END) * 100.0
        / NULLIF(COUNT(CASE
            WHEN date(first_shipped_at) = current_date - INTERVAL '1 day' THEN 1 END), 0), 1
    ) as "Hôm qua"
FROM fact_orders
WHERE status NOT IN ('DRAFT', 'CANCELLED')
  AND first_shipped_at IS NOT NULL
  AND date(first_shipped_at) >= current_date - INTERVAL '1 day'
  AND date(first_shipped_at) <= current_date
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: Đơn chờ > 24h

Số đơn OPEN chưa fulfilled quá 24 giờ — escalation metric.

```sql
SELECT COUNT(*) as "Đơn kẹt"
FROM fact_orders
WHERE status = 'OPEN'
  AND fulfillment_status != 'fulfilled'
  AND date_diff('hour', ordered_at, current_timestamp) > 24
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Đơn kẹt": {
        "number_style": "decimal",
        "decimals": 0
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Đơn hoàn thành hôm nay

Số đơn COMPLETED hôm nay với DoD comparison.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(ordered_at) = current_date AND status = 'COMPLETED' THEN order_id END) as "Hoàn thành",
    COUNT(DISTINCT CASE WHEN date(ordered_at) = current_date - INTERVAL '1 day' AND status = 'COMPLETED' THEN order_id END) as "Hôm qua"
FROM fact_orders
WHERE status NOT IN ('DRAFT')
  AND date(ordered_at) >= current_date - INTERVAL '1 day'
  AND date(ordered_at) <= current_date
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Theo dõi tốc độ xử lý theo giờ — khi nào xử lý nhanh/chậm?

# Theo dõi tốc độ xử lý theo giờ — khi nào xử lý nhanh/chậm?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: TB giờ xử lý theo giờ (DoD)

Biến động thời gian xử lý trung bình theo giờ trong ngày — DoD overlay.

```sql
WITH current_speed AS (
    SELECT
        EXTRACT(HOUR FROM ordered_at) as hour_of_day,
        ROUND(AVG(date_diff('hour', ordered_at, first_shipped_at)), 1) as avg_hours_today
    FROM fact_orders
    WHERE status NOT IN ('DRAFT', 'CANCELLED')
      AND first_shipped_at IS NOT NULL
      AND date(ordered_at) = current_date
    GROUP BY 1
),
previous_speed AS (
    SELECT
        EXTRACT(HOUR FROM ordered_at) as hour_of_day,
        ROUND(AVG(date_diff('hour', ordered_at, first_shipped_at)), 1) as avg_hours_yesterday
    FROM fact_orders
    WHERE status NOT IN ('DRAFT', 'CANCELLED')
      AND first_shipped_at IS NOT NULL
      AND date(ordered_at) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(c.hour_of_day, p.hour_of_day) as "Giờ",
    COALESCE(c.avg_hours_today, 0) as "Hôm nay",
    COALESCE(p.avg_hours_yesterday, 0) as "Hôm qua"
FROM current_speed c
FULL OUTER JOIN previous_speed p ON c.hour_of_day = p.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Giờ"],
    "graph.metrics": ["Hôm nay", "Hôm qua"],
    "graph.colors": ["#509EE3", "#C2D2E9"],
    "graph.x_axis.title_text": "Giờ trong ngày",
    "graph.y_axis.title_text": "TB giờ xử lý"
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Heatmap xuất kho

Cường độ xuất kho theo ngày x giờ (7 ngày gần nhất). Design: heatmap → Metabase: pivot + conditional formatting gradient.

```sql
SELECT
    CASE EXTRACT(DOW FROM ordered_at)
        WHEN 0 THEN 'CN'
        WHEN 1 THEN 'T2'
        WHEN 2 THEN 'T3'
        WHEN 3 THEN 'T4'
        WHEN 4 THEN 'T5'
        WHEN 5 THEN 'T6'
        WHEN 6 THEN 'T7'
    END as "Ngày",
    EXTRACT(HOUR FROM ordered_at) as "Giờ",
    COUNT(CASE WHEN first_shipped_at IS NOT NULL THEN 1 END) as "Xuất kho"
FROM fact_orders
WHERE status NOT IN ('DRAFT', 'CANCELLED')
  AND date(ordered_at) >= current_date - INTERVAL '6 days'
  AND date(ordered_at) <= current_date
GROUP BY 1, 2,
    EXTRACT(DOW FROM ordered_at)
ORDER BY EXTRACT(DOW FROM ordered_at), 2
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "pivot_table.column_split": {
      "rows": ["Ngày"],
      "columns": ["Giờ"],
      "values": ["Xuất kho"]
    },
    "table.column_formatting": [
      {
        "columns": ["Xuất kho"],
        "type": "range",
        "colors": ["#FFFFFF", "#509EE3"],
        "min_type": "all",
        "max_type": "all"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Escalate đơn hàng bị nghẽn — OPEN > 24h cần xử lý ngay

# Escalate đơn hàng bị nghẽn — OPEN > 24h cần xử lý ngay

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Chi tiết đơn kẹt

Danh sách đơn OPEN quá 24h, sắp xếp theo thời gian chờ — escalation zone.

```sql
SELECT
    o.order_code as "Mã đơn",
    o.fulfillment_status as "TT xuất kho",
    o.payment_status as "TT thanh toán",
    s.full_name as "Nhân viên",
    bl.branch_location_name as "Chi nhánh",
    ROUND(date_diff('hour', o.ordered_at, current_timestamp), 1) as "Chờ (giờ)",
    o.ordered_at as "Thời gian tạo"
FROM fact_orders o
LEFT JOIN dim_staff s ON o.seller_staff_key = s.staff_key
LEFT JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.status = 'OPEN'
  AND o.fulfillment_status != 'fulfilled'
  AND date_diff('hour', o.ordered_at, current_timestamp) > 24
ORDER BY "Chờ (giờ)" DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Chờ (giờ)"],
        "type": "single",
        "operator": ">",
        "value": 24,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Chờ (giờ)"],
        "type": "single",
        "operator": ">",
        "value": 12,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 8 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_logistics · **Cadence:** daily · **Scope:** Active fulfillment · **Caveats:** Realtime + 7d trend
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Chi tiết & Nhân viên


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') || '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Đánh giá hiệu suất nhân viên — ranking volume và tốc độ

# Đánh giá hiệu suất nhân viên — ranking volume và tốc độ

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: NV — Số đơn xử lý

Ranking nhân viên theo số đơn xử lý hôm nay — horizontal bar.

```sql
SELECT
    s.full_name as "Nhân viên",
    COUNT(DISTINCT o.order_id) as "Đơn xử lý"
FROM fact_orders o
JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE o.status NOT IN ('DRAFT', 'CANCELLED')
  AND date(o.ordered_at) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhân viên"],
    "graph.metrics": ["Đơn xử lý"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Số đơn"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: NV — TB giờ xử lý

Ranking nhân viên theo tốc độ xử lý trung bình hôm nay — horizontal bar.

```sql
SELECT
    s.full_name as "Nhân viên",
    ROUND(AVG(date_diff('hour', o.ordered_at, o.first_shipped_at)), 1) as "TB giờ xử lý"
FROM fact_orders o
JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE o.status NOT IN ('DRAFT', 'CANCELLED')
  AND o.first_shipped_at IS NOT NULL
  AND date(o.ordered_at) = current_date
GROUP BY 1
ORDER BY 2 ASC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhân viên"],
    "graph.metrics": ["TB giờ xử lý"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Giờ"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Tra cứu chi tiết đơn hàng hôm nay — full data lookup

# Tra cứu chi tiết đơn hàng hôm nay — full data lookup

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Bảng chi tiết đơn hàng

Full detail đơn hàng hôm nay: mã đơn, trạng thái, fulfillment, thời gian, nhân viên, kênh bán — conditional formatting on status.

```sql
SELECT
    o.order_code as "Mã đơn",
    o.status as "Trạng thái",
    o.fulfillment_status as "TT xuất kho",
    o.payment_status as "TT thanh toán",
    ch.channel_name as "Kênh bán",
    s.full_name as "Nhân viên",
    bl.branch_location_name as "Chi nhánh",
    o.net_revenue as "Doanh thu",
    o.ordered_at as "Thời gian tạo",
    o.first_shipped_at as "Xuất kho lúc",
    CASE
        WHEN o.first_shipped_at IS NOT NULL
        THEN ROUND(date_diff('hour', o.ordered_at, o.first_shipped_at), 1)
        ELSE NULL
    END as "Giờ đến XK"
FROM fact_orders o
LEFT JOIN dim_staff s ON o.seller_staff_key = s.staff_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.status != 'DRAFT'
  AND date(o.ordered_at) = current_date
ORDER BY o.ordered_at DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Giờ đến XK"],
        "type": "single",
        "operator": ">",
        "value": 24,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ đến XK"],
        "type": "single",
        "operator": ">",
        "value": 12,
        "color": "#F9D45C",
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
{ "row": 10, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_logistics · **Cadence:** daily · **Scope:** Active fulfillment · **Caveats:** Realtime + 7d trend
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

