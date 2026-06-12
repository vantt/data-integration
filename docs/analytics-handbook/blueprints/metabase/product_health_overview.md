---
primary_scope: none
scope_indicator: "[Cross]"
layer: L1
uses_concepts:
  - product_health_classification
  - product_action_queue
---

# 📘 Blueprint: Product Health Overview [Cross]

> **Database:** `Sapo`
> **Collection ID:** 100
> **Role:** Merchandising, Inventory
> **Archetype:** Operational Health Board (daily snapshot, 2 tabs)

Centerpiece product health board — velocity × margin × inventory synthesis. Tab 1 shows health landscape; Tab 2 drives daily actions.

## Semantic Contract

> **Sources:** `mart_product_health` (1 row/product, current state) · `mart_product_action_queue` (daily action queue)
> **Coverage caveat:** health_class only for has_margin_data (~17-42 SKU with COGS); inventory/lifecycle signals cover all products.

## 📂 Collection: Merchandising & Product

---

### 🖥️ Dashboard: Product Health Overview [Cross]

**Description**: Daily product health board — velocity × margin × inventory synthesis. Tab 1: health classification landscape (STAR/WORKHORSE/QUESTION/DOG). Tab 2: action queue (RESTOCK_NOW/CLEAR_DEADSTOCK/PROMOTE/REVIEW_MARGIN). Source: mart_product_health + mart_product_action_queue.

---

#### Filter: Category

```json metabase-filter
{
  "slug": "category",
  "type": "string/=",
  "field_id": 1755
}
```

#### Filter: Health Class

```json metabase-filter
{
  "slug": "health_class",
  "type": "string/=",
  "field_id": 1759
}
```

#### Filter: ABC Class

```json metabase-filter
{
  "slug": "abc_class",
  "type": "string/=",
  "field_id": 1757
}
```

---

### 📑 Tab: 🩺 Sức khỏe sản phẩm

#### ❓ Question: Chu ky bao cao

Snapshot date — reflects latest mart_product_health run.

```sql
SELECT
  '📅 Cập nhật: ' || strftime(MAX(calculated_at::TIMESTAMP), '%H:%M %d/%m/%Y')
  AS "Chu kỳ báo cáo"
FROM mart_product_health
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "",
    "dashcard.background": false
  }
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

---

#### ❓ Question: Tong san pham

Total distinct products tracked.

```sql
SELECT COUNT(*) AS "🛒 Tổng SP"
FROM mart_product_health
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Tổng số sản phẩm trong mart"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: SP ngoi sao STAR

Products classified as STAR (high velocity + high margin).

```sql
SELECT COUNT(*) AS "⭐ STAR"
FROM mart_product_health
WHERE health_class = 'STAR'
[[AND {{category}}]]
[[AND {{abc_class}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Bán chạy + lãi cao"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 3, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: SP hang ton DEAD STOCK

Products with is_dead_stock = true (no sale in 90+ days, on_hand > 0).

```sql
SELECT COUNT(*) AS "🐌 Hàng tồn"
FROM mart_product_health
WHERE is_dead_stock = true
[[AND {{category}}]]
[[AND {{abc_class}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Không bán 90+ ngày, còn tồn kho"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 6, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Gia tri hang ton rui ro

Total capital at risk from dead stock (VND).

```sql
SELECT COALESCE(SUM(dead_stock_value_at_risk), 0) AS "💸 Giá trị tồn rủi ro"
FROM mart_product_health
WHERE is_dead_stock = true
[[AND {{category}}]]
[[AND {{abc_class}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "💸 Giá trị tồn rủi ro": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      }
    },
    "card.description": "Vốn tồn đọng trong dead stock"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 9, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: SP rui ro het hang OOS RISK

Products with oos_risk = true (fast-moving but low/zero stock).

```sql
SELECT COUNT(*) AS "🚨 Rủi ro hết hàng"
FROM mart_product_health
WHERE oos_risk = true
[[AND {{category}}]]
[[AND {{abc_class}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Bán chạy, sắp/đã hết hàng"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 13, "size_x": 5, "size_y": 3 }
```

---

#### 📝 Text: Phan loai suc khoe san pham

# Phân loại sức khỏe sản phẩm

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Phan bo health class

Health classification distribution — BCG-style velocity × margin matrix.

```sql
SELECT
  COALESCE(health_class, 'N/A (thiếu COGS)') AS "Health Class",
  COUNT(*) AS "Số SP"
FROM mart_product_health
WHERE 1=1
[[AND {{category}}]]
[[AND {{abc_class}}]]
GROUP BY 1
ORDER BY
  CASE COALESCE(health_class, 'N/A (thiếu COGS)')
    WHEN 'STAR'      THEN 1
    WHEN 'WORKHORSE' THEN 2
    WHEN 'QUESTION'  THEN 3
    WHEN 'BALANCED'  THEN 4
    WHEN 'DOG'       THEN 5
    ELSE 6
  END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Health Class",
    "pie.metric": "Số SP",
    "series_settings": {
      "STAR":                   { "color": "#84BB4C" },
      "WORKHORSE":              { "color": "#509EE3" },
      "QUESTION":               { "color": "#F9D45C" },
      "BALANCED":               { "color": "#98D9D9" },
      "DOG":                    { "color": "#EF8C8C" },
      "N/A (thiếu COGS)":       { "color": "#C2D2E9" }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 6, "size_y": 6 }
```

---

#### ❓ Question: Phan bo ABC class

ABC Pareto class distribution — revenue contribution tiers.

```sql
SELECT
  COALESCE(abc_class, 'N/A') AS "ABC Class",
  COUNT(*) AS "Số SP"
FROM mart_product_health
WHERE 1=1
[[AND {{category}}]]
[[AND {{health_class}}]]
GROUP BY 1
ORDER BY
  CASE COALESCE(abc_class, 'N/A')
    WHEN 'A' THEN 1
    WHEN 'B' THEN 2
    WHEN 'C' THEN 3
    ELSE 4
  END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "ABC Class",
    "pie.metric": "Số SP",
    "series_settings": {
      "A": { "color": "#7172AD" },
      "B": { "color": "#88BDE6" },
      "C": { "color": "#C2D2E9" }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 6, "size_x": 6, "size_y": 6 }
```

---

#### ❓ Question: Phan bo lifecycle stage

Lifecycle stage distribution — NEW/GROWING/MATURE/DECLINING/DORMANT.

```sql
SELECT
  COALESCE(lifecycle_stage, 'N/A') AS "Lifecycle Stage",
  COUNT(*) AS "Số SP"
FROM mart_product_health
WHERE 1=1
[[AND {{category}}]]
[[AND {{health_class}}]]
[[AND {{abc_class}}]]
GROUP BY 1
ORDER BY
  CASE COALESCE(lifecycle_stage, 'N/A')
    WHEN 'NEW'       THEN 1
    WHEN 'GROWING'   THEN 2
    WHEN 'MATURE'    THEN 3
    WHEN 'DECLINING' THEN 4
    WHEN 'DORMANT'   THEN 5
    ELSE 6
  END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Lifecycle Stage"],
    "graph.metrics": ["Số SP"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Stage",
    "graph.y_axis.title_text": "Số SP"
  }
}
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Bang danh sach suc khoe san pham

# Danh sách sức khỏe sản phẩm — sắp xếp theo đóng góp doanh thu

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Bang suc khoe san pham

Full health table — all products ranked by revenue share.

```sql
SELECT
  sku                   AS "SKU",
  product_name          AS "Sản phẩm",
  category              AS "Danh mục",
  COALESCE(health_class, 'N/A')  AS "Health",
  COALESCE(abc_class, 'N/A')     AS "ABC",
  COALESCE(lifecycle_stage, 'N/A') AS "Lifecycle",
  ROUND(velocity_90d, 1)         AS "Velocity 90d",
  ROUND(realized_margin_pct, 1)  AS "Margin %",
  ROUND(days_of_supply, 0)       AS "Ngày tồn",
  is_dead_stock                  AS "Tồn chết",
  oos_risk                       AS "Rủi ro HH",
  ROUND(revenue_share_pct, 2)    AS "Revenue Share %"
FROM mart_product_health
WHERE 1=1
[[AND {{category}}]]
[[AND {{health_class}}]]
[[AND {{abc_class}}]]
ORDER BY revenue_share_pct DESC NULLS LAST
LIMIT 200
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.columns": [
      { "name": "SKU",            "enabled": true },
      { "name": "Sản phẩm",       "enabled": true },
      { "name": "Danh mục",       "enabled": true },
      { "name": "Health",         "enabled": true },
      { "name": "ABC",            "enabled": true },
      { "name": "Lifecycle",      "enabled": true },
      { "name": "Velocity 90d",   "enabled": true },
      { "name": "Margin %",       "enabled": true },
      { "name": "Ngày tồn",       "enabled": true },
      { "name": "Tồn chết",       "enabled": true },
      { "name": "Rủi ro HH",      "enabled": true },
      { "name": "Revenue Share %","enabled": true }
    ],
    "table.column_formatting": [
      {
        "columns": ["Health"],
        "type": "single",
        "operator": "=",
        "value": "STAR",
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Health"],
        "type": "single",
        "operator": "=",
        "value": "DOG",
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Tồn chết"],
        "type": "single",
        "operator": "=",
        "value": true,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Rủi ro HH"],
        "type": "single",
        "operator": "=",
        "value": true,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Source Freshness Tab1

Source: mart_product_health · Daily snapshot · **Scope: tất cả sản phẩm (không lọc kênh/scope)** · health_class chỉ cho ~17-42 SKU có COGS từ MISA (has_margin_data=true); tất cả SP còn lại có inventory/lifecycle signal · velocity_90d = đơn vị SP/ngày trong 90 ngày gần nhất

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: 🎯 Hành động

#### ❓ Question: Chu ky bao cao tab2

Action queue snapshot date.

```sql
SELECT
  '📅 Queue: ' || strftime(MAX(queue_generated_at::TIMESTAMP), '%H:%M %d/%m/%Y')
  AS "Chu kỳ báo cáo"
FROM mart_product_action_queue
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "",
    "dashcard.background": false
  }
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

---

#### ❓ Question: RESTOCK NOW count

Products needing immediate restocking (fast-moving, low stock).

```sql
SELECT COUNT(*) AS "🚨 Nhập ngay"
FROM mart_product_action_queue
WHERE action_type = 'RESTOCK_NOW'
[[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Bán chạy, sắp hết hàng"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: CLEAR DEADSTOCK count

Dead stock needing clearance to free capital.

```sql
SELECT COUNT(*) AS "🐌 Thanh lý tồn"
FROM mart_product_action_queue
WHERE action_type = 'CLEAR_DEADSTOCK'
[[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Tồn chết, cần thanh lý"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 4, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: REVIEW MARGIN count

Products with margin anomaly requiring price/COGS review.

```sql
SELECT COUNT(*) AS "📉 Review margin"
FROM mart_product_action_queue
WHERE action_type = 'REVIEW_MARGIN'
[[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Margin bất thường"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 8, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: PROMOTE count

High margin but low velocity — needs promotion push.

```sql
SELECT COUNT(*) AS "📣 Đẩy bán"
FROM mart_product_action_queue
WHERE action_type = 'PROMOTE'
[[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Lãi cao nhưng bán chậm"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 11, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: DELIST count

Dogs + dead stock candidates for delisting.

```sql
SELECT COUNT(*) AS "🗑️ Cân nhắc delist"
FROM mart_product_action_queue
WHERE action_type = 'DELIST'
[[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "DOG + DEAD + value thấp"
  }
}
```

```json metabase-pos
{ "row": 2, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Phan bo gia tri theo loai hanh dong

# Phân bổ giá trị rủi ro theo loại hành động

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Gia tri theo action type

Value at stake distribution by action type — bar chart.

```sql
SELECT
  CASE action_type
    WHEN 'RESTOCK_NOW'      THEN '1. 🚨 Nhập ngay'
    WHEN 'CLEAR_DEADSTOCK'  THEN '2. 🐌 Thanh lý tồn'
    WHEN 'REVIEW_MARGIN'    THEN '3. 📉 Review margin'
    WHEN 'PROMOTE'          THEN '4. 📣 Đẩy bán'
    WHEN 'DELIST'           THEN '5. 🗑️ Delist'
    ELSE action_type
  END AS "Loại hành động",
  COALESCE(SUM(value_at_stake), 0) AS "Giá trị (VND)"
FROM mart_product_action_queue
WHERE 1=1
[[AND {{category}}]]
GROUP BY action_type
ORDER BY MIN(priority_rank)
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loại hành động"],
    "graph.metrics": ["Giá trị (VND)"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "VND",
    "column_settings": {
      "Giá trị (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: So luong SP theo action type

Product count per action type.

```sql
SELECT
  CASE action_type
    WHEN 'RESTOCK_NOW'      THEN '1. 🚨 Nhập ngay'
    WHEN 'CLEAR_DEADSTOCK'  THEN '2. 🐌 Thanh lý tồn'
    WHEN 'REVIEW_MARGIN'    THEN '3. 📉 Review margin'
    WHEN 'PROMOTE'          THEN '4. 📣 Đẩy bán'
    WHEN 'DELIST'           THEN '5. 🗑️ Delist'
    ELSE action_type
  END AS "Loại hành động",
  COUNT(*) AS "Số SP"
FROM mart_product_action_queue
WHERE 1=1
[[AND {{category}}]]
GROUP BY action_type
ORDER BY MIN(priority_rank)
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loại hành động"],
    "graph.metrics": ["Số SP"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Số SP"
  }
}
```

```json metabase-pos
{ "row": 6, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Hang doi hanh dong

# Hàng đợi hành động — sắp xếp theo mức độ ưu tiên

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Action queue table

Full action queue ranked by priority_rank.

```sql
SELECT
  priority_rank         AS "P",
  sku                   AS "SKU",
  product_name          AS "Sản phẩm",
  CASE action_type
    WHEN 'RESTOCK_NOW'      THEN '🚨 Nhập ngay'
    WHEN 'CLEAR_DEADSTOCK'  THEN '🐌 Thanh lý tồn'
    WHEN 'REVIEW_MARGIN'    THEN '📉 Review margin'
    WHEN 'PROMOTE'          THEN '📣 Đẩy bán'
    WHEN 'DELIST'           THEN '🗑️ Delist'
    ELSE action_type
  END                   AS "Hành động",
  action_rationale      AS "Lý do",
  value_at_stake        AS "Giá trị",
  abc_class             AS "ABC",
  COALESCE(health_class, 'N/A') AS "Health",
  ROUND(days_of_supply, 0) AS "Ngày tồn",
  ROUND(realized_margin_pct, 1) AS "Margin %"
FROM mart_product_action_queue
WHERE 1=1
[[AND {{category}}]]
ORDER BY priority_rank ASC
LIMIT 200
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.columns": [
      { "name": "P",          "enabled": true },
      { "name": "SKU",        "enabled": true },
      { "name": "Sản phẩm",   "enabled": true },
      { "name": "Hành động",  "enabled": true },
      { "name": "Lý do",      "enabled": true },
      { "name": "Giá trị",    "enabled": true },
      { "name": "ABC",        "enabled": true },
      { "name": "Health",     "enabled": true },
      { "name": "Ngày tồn",   "enabled": true },
      { "name": "Margin %",   "enabled": true }
    ],
    "column_settings": {
      "Giá trị": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Hành động"],
        "type": "single",
        "operator": "=",
        "value": "🚨 Nhập ngay",
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Hành động"],
        "type": "single",
        "operator": "=",
        "value": "🐌 Thanh lý tồn",
        "color": "#F9D45C",
        "highlight_row": false
      },
      {
        "columns": ["Giá trị"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Source Freshness Tab2

Source: mart_product_action_queue · Daily snapshot · **Scope: tất cả sản phẩm** · Xếp hạng theo priority_rank (RESTOCK_NOW → CLEAR_DEADSTOCK → PROMOTE → REVIEW_MARGIN → DELIST) · value_at_stake = giá trị tồn kho tại rủi ro (dead_stock_value_at_risk) hoặc ước tính doanh thu lost

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 1 }
```
