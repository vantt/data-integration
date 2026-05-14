# 📘 Blueprint: Sales Monthly Business Review

**Design Spec**: [Sales Monthly Business Review](../designs/sales_monthly_review.md)

> **Target Collection:** `Executive`
> **Role:** Sales Director, CFO, Regional Managers
> **Archetype:** Executive Pulse (4 tabs)

Monthly Business Review dashboard — 4 tabs: Tong quan (KPIs + target progress + 12-month trend), Hieu suat tai chinh (branch target achievement + variance), Dong luc tang truong (channels + segments), Suc khoe van hanh (discounts + returns + products). All KPIs have MoM comparison.

## 📂 Collection: Executive

Strategic dashboards for leadership — company performance, targets, and high-level KPIs.

---

### 🖥️ Dashboard: Sales Monthly Business Review

**Description**: Bao cao MBR hang thang — 4 tabs: Tong quan, Hieu suat tai chinh, Dong luc tang truong, Suc khoe van hanh. MoM + vs Target comparison tren tat ca KPI.

---

### 📑 Tab: Tong quan

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Tháng trước: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') ||
  '  ·  MoM: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Review kết quả kinh doanh tháng — doanh thu vs target, gap analysis

# Review kết quả kinh doanh tháng — doanh thu vs target, gap analysis

```json metabase-pos
{"row":1, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Net Revenue vs Target

Hero metric — doanh thu thuan vs muc tieu thang, hien thi progress bar.

```sql
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(net_revenue), 0) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    a.actual_revenue as "Net Revenue"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "progress",
  "visualization_settings": {
    "progress.color": "#84BB4C"
  }
}
```

```json metabase-pos
{"row":2, "col":0, "size_x":6, "size_y":6}
```

#### ❓ Question: Net Revenue

Gia tri tuyet doi doanh thu thuan voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Net Revenue",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
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
{"row":2, "col":6, "size_x":4, "size_y":3}
```

#### ❓ Question: Total Orders

Volume don hang voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Total Orders",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{"row":2, "col":10, "size_x":4, "size_y":3}
```

#### ❓ Question: AOV

Gia tri trung binh moi don hang voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "AOV",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
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
{"row":2, "col":14, "size_x":4, "size_y":3}
```

#### 📝 Text: Kiểm tra chỉ số phụ — gross revenue, thu tiền, khách hàng, hoàn trả

## Kiểm tra chỉ số phụ — gross revenue, thu tiền, khách hàng, hoàn trả

```json metabase-pos
{"row":5, "col":6, "size_x":12, "size_y":1}
```

#### ❓ Question: Gross Revenue

Tong doanh thu gop voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Gross Revenue",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
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
{"row":6, "col":6, "size_x":3, "size_y":3}
```

#### ❓ Question: Total Collected

Tong thu gom VAT voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Total Collected",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ],
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
{"row":6, "col":9, "size_x":3, "size_y":3}
```

#### ❓ Question: Variance to Target

Gap tuyet doi giua doanh thu thuc va target.

```sql
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(net_revenue), 0) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    a.actual_revenue - t.target_revenue as "Variance"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Variance": {
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
{"row":6, "col":12, "size_x":3, "size_y":3}
```

#### ❓ Question: New Customers

Khach moi trong thang voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT fo.customer_key) as val
    FROM fact_orders fo
    JOIN dim_customers dc ON fo.customer_key = dc.customer_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fo.order_timestamp < date_trunc('month', current_date)
      AND dc.first_order_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND dc.first_order_date < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT fo.customer_key) as val
    FROM fact_orders fo
    JOIN dim_customers dc ON fo.customer_key = dc.customer_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND fo.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      AND dc.first_order_date >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND dc.first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "New Customers",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{"row":6, "col":15, "size_x":3, "size_y":3}
```

#### ❓ Question: Returning Customers

Khach quay lai trong thang voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT fo.customer_key) as val
    FROM fact_orders fo
    JOIN dim_customers dc ON fo.customer_key = dc.customer_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fo.order_timestamp < date_trunc('month', current_date)
      AND dc.first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
),
prev_month AS (
    SELECT COUNT(DISTINCT fo.customer_key) as val
    FROM fact_orders fo
    JOIN dim_customers dc ON fo.customer_key = dc.customer_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND fo.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      AND dc.first_order_date < date_trunc('month', current_date) - INTERVAL '2 months'
)
SELECT
    tm.val as "Returning Customers",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{"row":9, "col":6, "size_x":3, "size_y":3}
```

#### ❓ Question: Return Count

Don tra hang voi MoM comparison — negative khi tang.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE fulfillment_status = 'RETURNED'
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE fulfillment_status = 'RETURNED'
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Return Count",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{"row":9, "col":9, "size_x":3, "size_y":3}
```

#### 📝 Text: Theo dõi trajectory doanh thu 12 tháng — momentum và target pace

## Theo dõi trajectory doanh thu 12 tháng — momentum và target pace

```json metabase-pos
{"row":12, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: 12-Month Revenue Trend

Trajectory doanh thu 12 thang voi target line overlay.

```sql
WITH monthly_actuals AS (
    SELECT
        date_trunc('month', order_timestamp)::date as month_start,
        SUM(net_revenue) as net_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
monthly_targets AS (
    SELECT
        cycle_start_date::date as month_start,
        SUM(target_val) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND cycle_start_date < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    a.month_start as "Thang",
    a.net_revenue as "Net Revenue",
    COALESCE(t.target_revenue, 0) as "Target"
FROM monthly_actuals a
LEFT JOIN monthly_targets t ON a.month_start = t.month_start
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Net Revenue", "Target"],
    "series_settings": {
      "Net Revenue": { "display": "bar", "color": "#509EE3" },
      "Target": { "display": "line", "color": "#EF8C8C", "line.style": "dashed" }
    },
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{"row":13, "col":0, "size_x":12, "size_y":6}
```

#### ❓ Question: Achievement Rate by Month

Ty le dat target qua 12 thang — 100% benchmark line.

```sql
WITH monthly_actuals AS (
    SELECT
        date_trunc('month', order_timestamp)::date as month_start,
        SUM(net_revenue) as net_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
monthly_targets AS (
    SELECT
        cycle_start_date::date as month_start,
        SUM(target_val) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND cycle_start_date < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    a.month_start as "Thang",
    CASE WHEN COALESCE(t.target_revenue, 0) = 0 THEN 0
         ELSE ROUND(a.net_revenue * 100.0 / t.target_revenue, 1) END as "Achievement %"
FROM monthly_actuals a
LEFT JOIN monthly_targets t ON a.month_start = t.month_start
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Achievement %"],
    "series_settings": {
      "Achievement %": { "color": "#509EE3" }
    },
    "graph.y_axis.title_text": "Achievement %",
    "graph.x_axis.title_text": "",
    "graph.goal_value": 100,
    "graph.goal_label": "Target 100%",
    "graph.show_goal": true
  }
}
```

```json metabase-pos
{"row":13, "col":12, "size_x":6, "size_y":6}
```

---

### 📑 Tab: Hieu suat tai chinh
#### 📝 Text: Đánh giá target achievement chi nhánh — xác định nơi cần hỗ trợ

# Đánh giá target achievement chi nhánh — xác định nơi cần hỗ trợ

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Target Achievement by Branch

Ranking chi nhanh theo % dat target — 100% reference line.

```sql
WITH branch_actuals AS (
    SELECT
        bl.branch_location_name as branch_name,
        SUM(fo.net_revenue) as actual_revenue
    FROM fact_orders fo
    JOIN dim_branch_location bl ON fo.branch_location_key = bl.branch_location_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fo.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
branch_targets AS (
    SELECT
        bl.branch_location_name as branch_name,
        SUM(ft.target_val) as target_revenue
    FROM fact_targets ft
    JOIN dim_branch_location bl ON ft.branch_location_key = bl.branch_location_key
    WHERE ft.cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ft.cycle_end_date < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    a.branch_name as "Chi nhanh",
    CASE WHEN COALESCE(t.target_revenue, 0) = 0 THEN 0
         ELSE ROUND(a.actual_revenue * 100.0 / t.target_revenue, 1) END as "Achievement %"
FROM branch_actuals a
LEFT JOIN branch_targets t ON a.branch_name = t.branch_name
ORDER BY "Achievement %" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Chi nhanh"],
    "graph.metrics": ["Achievement %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Achievement %",
    "graph.goal_value": 100,
    "graph.goal_label": "Target 100%",
    "graph.show_goal": true
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Phân tích variance — yếu tố nào đóng góp chênh lệch target?

## Phân tích variance — yếu tố nào đóng góp chênh lệch target?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Variance Waterfall

Yeu to nao dong gop chenh lech target — waterfall theo chi nhanh.

```sql
WITH branch_variance AS (
    SELECT
        bl.branch_location_name as branch_name,
        SUM(fo.net_revenue) as actual_revenue,
        COALESCE(
            (SELECT SUM(ft.target_val)
             FROM fact_targets ft
             WHERE ft.branch_location_key = bl.branch_location_key
               AND ft.cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
               AND ft.cycle_end_date < date_trunc('month', current_date)),
            0
        ) as target_revenue
    FROM fact_orders fo
    JOIN dim_branch_location bl ON fo.branch_location_key = bl.branch_location_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fo.order_timestamp < date_trunc('month', current_date)
    GROUP BY bl.branch_location_name, bl.branch_location_key
)
SELECT
    branch_name as "Chi nhanh",
    actual_revenue - target_revenue as "Variance"
FROM branch_variance
ORDER BY "Variance" ASC
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": ["Chi nhanh"],
    "graph.metrics": ["Variance"],
    "graph.show_values": true,
    "column_settings": {
      "Variance": {
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
{ "row": 8, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: MoM Revenue Change

Thay doi doanh thu so thang truoc — prominent scalar.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val - pm.val as "MoM Change",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ],
    "column_settings": {
      "MoM Change": {
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
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Review chi tiết chi nhánh — revenue, target, achievement, MoM

## Review chi tiết chi nhánh — revenue, target, achievement, MoM

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Branch Performance Table

Revenue, Target, Achievement %, Variance, MoM% theo chi nhanh — conditional formatting.

```sql
WITH
this_month AS (
    SELECT
        bl.branch_location_name as branch_name,
        SUM(fo.net_revenue) as revenue
    FROM fact_orders fo
    JOIN dim_branch_location bl ON fo.branch_location_key = bl.branch_location_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fo.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
prev_month AS (
    SELECT
        bl.branch_location_name as branch_name,
        SUM(fo.net_revenue) as revenue
    FROM fact_orders fo
    JOIN dim_branch_location bl ON fo.branch_location_key = bl.branch_location_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND fo.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
),
targets AS (
    SELECT
        bl.branch_location_name as branch_name,
        SUM(ft.target_val) as target_revenue
    FROM fact_targets ft
    JOIN dim_branch_location bl ON ft.branch_location_key = bl.branch_location_key
    WHERE ft.cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ft.cycle_end_date < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    tm.branch_name as "Chi nhanh",
    tm.revenue as "Revenue",
    COALESCE(tg.target_revenue, 0) as "Target",
    CASE WHEN COALESCE(tg.target_revenue, 0) = 0 THEN 0
         ELSE ROUND(tm.revenue * 100.0 / tg.target_revenue, 1) END as "Achievement %",
    tm.revenue - COALESCE(tg.target_revenue, 0) as "Variance",
    CASE WHEN COALESCE(pm.revenue, 0) = 0 THEN 0
         ELSE ROUND((tm.revenue - pm.revenue) * 100.0 / pm.revenue, 1) END as "MoM %"
FROM this_month tm
LEFT JOIN prev_month pm ON tm.branch_name = pm.branch_name
LEFT JOIN targets tg ON tm.branch_name = tg.branch_name
ORDER BY tm.revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Achievement %"],
        "type": "single",
        "operator": ">=",
        "value": 100,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Achievement %"],
        "type": "single",
        "operator": "<",
        "value": 100,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Target": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Variance": {
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 9 }
```

---

### 📑 Tab: Dong luc tang truong

#### 📝 Text: Xác định kênh drive revenue — ranking và so sánh MoM

# Xác định kênh drive revenue — ranking và so sánh MoM

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Revenue by Channel

Ranking kenh theo doanh thu thang — horizontal bar.

```sql
SELECT
    dc.channel_name as "Kenh",
    SUM(fo.net_revenue) as "Net Revenue"
FROM fact_orders fo
JOIN dim_channels dc ON fo.channel_key = dc.channel_key
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fo.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY "Net Revenue" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Net Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Net Revenue (VND)",
    "column_settings": {
      "Net Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Channel Mix MoM

So sanh truc tiep kenh MoM — grouped bar.

```sql
WITH
this_month AS (
    SELECT
        dc.channel_name as channel_name,
        SUM(fo.net_revenue) as revenue
    FROM fact_orders fo
    JOIN dim_channels dc ON fo.channel_key = dc.channel_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fo.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
prev_month AS (
    SELECT
        dc.channel_name as channel_name,
        SUM(fo.net_revenue) as revenue
    FROM fact_orders fo
    JOIN dim_channels dc ON fo.channel_key = dc.channel_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND fo.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    COALESCE(tm.channel_name, pm.channel_name) as "Kenh",
    COALESCE(tm.revenue, 0) as "Thang nay",
    COALESCE(pm.revenue, 0) as "Thang truoc"
FROM this_month tm
FULL OUTER JOIN prev_month pm ON tm.channel_name = pm.channel_name
ORDER BY COALESCE(tm.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Thang nay", "Thang truoc"],
    "series_settings": {
      "Thang nay": { "color": "#509EE3" },
      "Thang truoc": { "color": "#88BDE6" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Theo dõi structural shift kênh 6 tháng — Online đang chiếm ưu thế?

## Theo dõi structural shift kênh 6 tháng — Online đang chiếm ưu thế?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Revenue Trend (6M)

Cau thanh doanh thu thay doi theo thang — stacked bar 6 thang.

```sql
SELECT
    date_trunc('month', fo.order_timestamp)::date as "Thang",
    dc.channel_name as "Kenh",
    SUM(fo.net_revenue) as "Net Revenue"
FROM fact_orders fo
JOIN dim_channels dc ON fo.channel_key = dc.channel_key
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND fo.order_timestamp < date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Thang", "Kenh"],
    "graph.metrics": ["Net Revenue"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)"
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Online vs Offline Share

Ty le Online/Offline hien tai — donut chart.

```sql
SELECT
    dc.channel_format as "Nhom",
    SUM(fo.net_revenue) as "Net Revenue"
FROM fact_orders fo
JOIN dim_channels dc ON fo.channel_key = dc.channel_key
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fo.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY "Net Revenue" DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "column_settings": {
      "Net Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Đánh giá phân khúc khách hàng — VIP contribution và growth

## Đánh giá phân khúc khách hàng — VIP contribution và growth

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Revenue by Customer Segment

VALUE_VIP/GOLD/SILVER/BRONZE dong gop — vertical bar.

```sql
WITH value_groups AS (
    SELECT
        dc.customer_key,
        CASE
            WHEN COUNT(DISTINCT fo.order_id) >= 10 THEN 'VALUE_VIP'
            WHEN COUNT(DISTINCT fo.order_id) >= 3 THEN 'VALUE_GOLD'
            ELSE 'VALUE_BRONZE'
        END as segment
    FROM fact_orders fo
    JOIN dim_customers dc ON fo.customer_key = dc.customer_key
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    cs.segment as "Phan khuc",
    SUM(fo.net_revenue) as "Net Revenue"
FROM fact_orders fo
JOIN value_groups cs ON fo.customer_key = cs.customer_key
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fo.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY "Net Revenue" DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Phan khuc"],
    "graph.metrics": ["Net Revenue"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)"
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New vs Returning Revenue Share

Khach moi vs khach cu dong gop — stacked bar.

```sql
SELECT
    CASE
        WHEN dc.first_order_date >= date_trunc('month', current_date) - INTERVAL '1 month'
             AND dc.first_order_date < date_trunc('month', current_date)
        THEN 'Khach moi'
        ELSE 'Khach cu'
    END as "Loai khach",
    SUM(fo.net_revenue) as "Net Revenue"
FROM fact_orders fo
JOIN dim_customers dc ON fo.customer_key = dc.customer_key
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fo.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Loai khach"],
    "graph.metrics": ["Net Revenue"],
    "series_settings": {
      "Khach moi": { "color": "#509EE3" },
      "Khach cu": { "color": "#88BDE6" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)"
  }
}
```

```json metabase-pos
{ "row": 15, "col": 9, "size_x": 9, "size_y": 6 }
```

---

### 📑 Tab: Suc khoe van hanh

#### 📝 Text: Kiểm soát chiết khấu — có vượt ngưỡng 15% GMV?

# Kiểm soát chiết khấu — có vượt ngưỡng 15% GMV?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Rate %

Ty le chiet khau tren GMV — gauge voi zones 0-10/10-15/15+.

```sql
SELECT
    CASE WHEN SUM(gross_revenue) = 0 THEN 0
         ELSE ROUND(SUM(discount_amount) * 100.0 / SUM(gross_revenue), 1) END as "Discount Rate %"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 10, "color": "#84BB4C", "label": "Tot" },
      { "min": 10, "max": 15, "color": "#F9D45C", "label": "Canh bao" },
      { "min": 15, "max": 30, "color": "#EF8C8C", "label": "Vuot nguong" }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Total Discount Amount

Gia tri chiet khau tuyet doi voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Total Discount",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ],
    "column_settings": {
      "Total Discount": {
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
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Discounted Orders %

Ty le don co chiet khau voi MoM comparison.

```sql
WITH
this_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
                        / COUNT(DISTINCT order_id), 1) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
                        / COUNT(DISTINCT order_id), 1) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Discounted Orders %",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ],
    "column_settings": {
      "Discounted Orders %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Return Rate

Ty le tra hang voi MoM comparison — negative khi tang.

```sql
WITH
this_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN fulfillment_status = 'RETURNED' THEN order_id END) * 100.0
                        / COUNT(DISTINCT order_id), 1) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN fulfillment_status = 'RETURNED' THEN order_id END) * 100.0
                        / COUNT(DISTINCT order_id), 1) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Return Rate %",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs tháng trước"
      }
    ],
    "column_settings": {
      "Return Rate %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

#### 📝 Text: Xác định top sản phẩm bán chạy và sản phẩm bị trả nhiều

## Xác định top sản phẩm bán chạy và sản phẩm bị trả nhiều

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 12, "size_y": 1 }
```

#### ❓ Question: Top 10 Products by Revenue

San pham ban chay nhat — horizontal bar.

```sql
SELECT
    dp.product_name as "San pham",
    SUM(fs.revenue) as "Revenue"
FROM fact_sales fs
JOIN dim_products dp ON fs.product_key = dp.product_key
WHERE fs.sol_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fs.sol_timestamp < date_trunc('month', current_date)
  AND fs.order_id IN (
      SELECT order_id FROM fact_orders
      WHERE status NOT IN ('CANCELLED', 'Voided')
  )
GROUP BY 1
ORDER BY "Revenue" DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 5 Returned Products

San pham bi tra nhieu nhat — horizontal bar (negative color).

```sql
SELECT
    dp.product_name as "San pham",
    SUM(fs.quantity) as "So luong tra"
FROM fact_sales fs
JOIN dim_products dp ON fs.product_key = dp.product_key
JOIN fact_orders fo ON fs.order_id = fo.order_id
WHERE fo.fulfillment_status = 'RETURNED'
  AND fs.sol_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fs.sol_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY "So luong tra" DESC
LIMIT 5
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["So luong tra"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "So luong tra"
  }
}
```

```json metabase-pos
{ "row": 5, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Review chi tiết sản phẩm — revenue, quantity, MoM theo loại

## Review chi tiết sản phẩm — revenue, quantity, MoM theo loại

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Revenue by Product Type

Loai SP dong gop doanh thu — horizontal bar.

```sql
SELECT
    dpt.product_type_name as "Loai san pham",
    SUM(fs.revenue) as "Revenue"
FROM fact_sales fs
JOIN dim_product_types dpt ON fs.product_type_key = dpt.product_type_key
WHERE fs.sol_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND fs.sol_timestamp < date_trunc('month', current_date)
  AND fs.order_id IN (
      SELECT order_id FROM fact_orders
      WHERE status NOT IN ('CANCELLED', 'Voided')
  )
GROUP BY 1
ORDER BY "Revenue" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loai san pham"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Product Performance Table

Revenue, Qty, MoM%, Return% theo san pham — conditional formatting.

```sql
WITH
this_month AS (
    SELECT
        dp.product_name as product_name,
        SUM(fs.revenue) as revenue,
        SUM(fs.quantity) as quantity
    FROM fact_sales fs
    JOIN dim_products dp ON fs.product_key = dp.product_key
    WHERE fs.sol_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fs.sol_timestamp < date_trunc('month', current_date)
      AND fs.order_id IN (
          SELECT order_id FROM fact_orders
          WHERE status NOT IN ('CANCELLED', 'Voided')
      )
    GROUP BY 1
),
prev_month AS (
    SELECT
        dp.product_name as product_name,
        SUM(fs.revenue) as revenue
    FROM fact_sales fs
    JOIN dim_products dp ON fs.product_key = dp.product_key
    WHERE fs.sol_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND fs.sol_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      AND fs.order_id IN (
          SELECT order_id FROM fact_orders
          WHERE status NOT IN ('CANCELLED', 'Voided')
      )
    GROUP BY 1
),
returns AS (
    SELECT
        dp.product_name as product_name,
        SUM(fs.quantity) as returned_qty
    FROM fact_sales fs
    JOIN dim_products dp ON fs.product_key = dp.product_key
    JOIN fact_orders fo ON fs.order_id = fo.order_id
    WHERE fo.fulfillment_status = 'RETURNED'
      AND fs.sol_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND fs.sol_timestamp < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    tm.product_name as "San pham",
    tm.revenue as "Revenue",
    tm.quantity as "So luong",
    CASE WHEN COALESCE(pm.revenue, 0) = 0 THEN 0
         ELSE ROUND((tm.revenue - pm.revenue) * 100.0 / pm.revenue, 1) END as "MoM %",
    CASE WHEN tm.quantity = 0 THEN 0
         ELSE ROUND(COALESCE(r.returned_qty, 0) * 100.0 / tm.quantity, 1) END as "Return %"
FROM this_month tm
LEFT JOIN prev_month pm ON tm.product_name = pm.product_name
LEFT JOIN returns r ON tm.product_name = r.product_name
ORDER BY tm.revenue DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Return %"],
        "type": "single",
        "operator": ">=",
        "value": 10,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": {
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
{ "row": 12, "col": 9, "size_x": 9, "size_y": 9 }
```

#### 📝 Text: Footer

Source: fact_orders · dim_customers · Closed month data · Completed orders only

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 1 }
```
