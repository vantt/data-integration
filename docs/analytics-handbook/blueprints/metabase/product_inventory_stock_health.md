---
dashboard_name: Product Inventory & Stock Health [All]
collection: Merchandising & Product
database: Sapo
description: "Daily inventory check: OOS, low-stock, dead-stock capital, days-of-supply, stock by location. Enriched with mart_product_health velocity signals."
audience: Inventory Manager, Ops Manager
cadence: Daily
status: ACTIVE
primary_scope: none
scope_indicator: "[Internal]"
layer: L2
uses_concepts: [inventory_quantity, inventory_value, oos_risk, health_class]
---

# Product Inventory & Stock Health [All] Blueprint

**Playbook**: [Inventory Health](../playbooks/product_inventory.md)

Daily inventory check — OOS alerts, low-stock, dead-stock capital exposure, days-of-supply, stock by location. Enriched with `mart_product_health` velocity × health signals (oos_risk, health_class) so inventory decisions consider velocity (e.g. dead-stock that's DOG = strong delist signal).

> **Database:** Sapo

## Semantic Contract

> **Scope:** N/A — Inventory mart (`fact_inventory_snapshots` / `mart_inventory_health`); no order-level scope filter.
> **Concepts used:** `inventory_quantity` · `inventory_value` · `oos_risk` · `health_class`

Inventory queries do not use `scope_sales`, `scope_retail`, or any order filter.

## 📂 Collection: Merchandising & Product

### Dashboard: Product Inventory & Stock Health [All]

**Description**: Daily inventory check — OOS count, low-stock alerts, slow-mover capital exposure, stock trend by location. Enriched with product health velocity signals. Audience: Inventory Manager, Ops Manager.

---

#### Filter: Location

```json metabase-filter
{
  "slug": "location_name",
  "type": "category",
  "field_id": 1106
}
```

#### Filter: Category

```json metabase-filter
{
  "slug": "category",
  "type": "category",
  "field_id": 1102
}
```

---

### 📑 Tab: Current Stock

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Snapshot: ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Tình trạng tồn kho hôm nay — OOS, low-stock, và giá trị vốn tồn theo location

# Tình trạng tồn kho hôm nay — OOS, low-stock, và giá trị vốn tồn theo location

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 24, "size_y": 1 }
```

#### Question: OOS SKUs

Số SKU đang hết hàng (on_hand ≤ 0) theo snapshot gần nhất.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Hết Hàng"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_oos = true
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "SKU Hết Hàng (OOS)",
    "scalar.field": "SKU Hết Hàng"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 4, "size_y": 3 }
```

#### Question: Low Stock SKUs

Số SKU cảnh báo sắp hết (on_hand > 0 và ≤ min_value).

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Sắp Hết"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_low_stock = true
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "SKU Sắp Hết Hàng (Low Stock)",
    "scalar.field": "SKU Sắp Hết"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 4, "size_x": 4, "size_y": 3 }
```

#### Question: Tổng Giá Trị Tồn Kho

Tổng giá trị tồn kho theo MAC (Moving Average Cost).

```sql
SELECT ROUND(SUM(stock_value_at_mac) / 1e6, 1) AS "Giá Trị Tồn Kho (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Tổng Giá Trị Tồn Kho",
    "scalar.field": "Giá Trị Tồn Kho (triệu VND)"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 8, "size_x": 4, "size_y": 3 }
```

#### Question: Tổng SKU Có Hàng

Tổng số SKU đang có hàng trên tất cả locations.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Có Hàng"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Tổng SKU Có Hàng",
    "scalar.field": "SKU Có Hàng"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 4, "size_y": 3 }
```

#### Question: OOS Risk SKUs (High-Velocity + Low Stock)

SKU bán chạy nhưng sắp/đã hết hàng — ưu tiên nhập. Nguồn: mart_product_health.oos_risk (velocity cao + is_oos/is_low_stock/days_of_supply<14).

```sql
SELECT COUNT(DISTINCT mart_inventory_health.sku) AS "SKU OOS Risk"
FROM main_marts.mart_inventory_health
LEFT JOIN main_marts.mart_product_health ON mart_inventory_health.sku = mart_product_health.sku
WHERE mart_inventory_health.snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND mart_product_health.oos_risk = true
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "SKU OOS Risk (Bán Chạy + Sắp Hết)",
    "scalar.field": "SKU OOS Risk"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 16, "size_x": 4, "size_y": 3 }
```

#### Question: Giá Trị Tồn Kho Theo Location

Breakdown giá trị tồn kho và số SKU theo từng kho.

```sql
SELECT
    location_name                                     AS "Kho",
    COUNT(DISTINCT sku)                               AS "Số SKU",
    ROUND(SUM(on_hand), 0)                            AS "Tổng Tồn (units)",
    ROUND(SUM(stock_value_at_mac) / 1e6, 2)           AS "Giá Trị (triệu VND)",
    COUNT(DISTINCT CASE WHEN is_oos THEN sku END)     AS "SKU OOS",
    COUNT(DISTINCT CASE WHEN is_low_stock THEN sku END) AS "SKU Low Stock"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  [[AND {{location_name}}]]
  [[AND {{category}}]]
GROUP BY location_name
ORDER BY SUM(stock_value_at_mac) DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Giá Trị Tồn Kho Theo Kho",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Top 20 SKU Theo Giá Trị Tồn Kho

Top 20 SKU chiếm giá trị vốn tồn cao nhất — snapshot gần nhất, enriched với health_class từ mart_product_health.

```sql
SELECT
    mart_inventory_health.sku                                                     AS "SKU",
    mart_inventory_health.product_name                                            AS "Tên Sản Phẩm",
    mart_inventory_health.location_name                                           AS "Kho",
    ROUND(mart_inventory_health.on_hand, 0)                                       AS "Tồn (units)",
    ROUND(mart_inventory_health.mac, 0)                                           AS "MAC (VND/unit)",
    ROUND(mart_inventory_health.stock_value_at_mac / 1e6, 2)                      AS "Giá Trị (triệu VND)",
    mart_inventory_health.bin_location                                            AS "Vị Trí Kệ",
    COALESCE(p.health_class, '-')                             AS "Health Class",
    COALESCE(p.abc_class, '-')                                AS "ABC"
FROM main_marts.mart_inventory_health
LEFT JOIN main_marts.mart_product_health p ON mart_inventory_health.sku = p.sku
WHERE mart_inventory_health.snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND mart_inventory_health.on_hand > 0
  AND mart_inventory_health.mac IS NOT NULL
  [[AND {{location_name}}]]
  [[AND {{category}}]]
ORDER BY mart_inventory_health.stock_value_at_mac DESC NULLS LAST
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Top 20 SKU Theo Giá Trị Tồn",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 12, "size_y": 6 }
```

#### Question: Danh Sách SKU OOS

Chi tiết các SKU đang hết hàng — để gửi reorder alert. Enriched với health_class và abc_class.

```sql
SELECT
    mart_inventory_health.sku                                                     AS "SKU",
    mart_inventory_health.product_name                                            AS "Tên Sản Phẩm",
    mart_inventory_health.location_name                                           AS "Kho",
    ROUND(mart_inventory_health.on_hand, 0)                                       AS "Tồn (units)",
    ROUND(mart_inventory_health.committed, 0)                                     AS "Committed",
    ROUND(mart_inventory_health.incoming, 0)                                      AS "Đang Về",
    ROUND(mart_inventory_health.days_of_supply, 0)                                AS "Days of Supply",
    COALESCE(p.health_class, '-')                             AS "Health Class",
    COALESCE(p.abc_class, '-')                                AS "ABC",
    CASE WHEN p.oos_risk THEN '🚨' ELSE '' END                AS "OOS Risk"
FROM main_marts.mart_inventory_health
LEFT JOIN main_marts.mart_product_health p ON mart_inventory_health.sku = p.sku
WHERE mart_inventory_health.snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND mart_inventory_health.is_oos = true
  [[AND {{location_name}}]]
  [[AND {{category}}]]
ORDER BY mart_inventory_health.sku, mart_inventory_health.location_name
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Danh Sách SKU Hết Hàng (OOS)",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 24, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Source:** `mart_inventory_health` · `mart_product_health` · **Cadence:** daily · **Scope:** snapshot_date = latest available
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 24, "size_y": 1 }
```

---

### 📑 Tab: Slow-Mover & Dead Stock

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Snapshot: ' || strftime(current_date, '%d/%m/%Y') || '  ·  Lookback: ' || strftime(current_date - 90, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Hàng tồn chậm và tồn chết — vốn bị chôn vùi cần xử lý

# Hàng tồn chậm và tồn chết — vốn bị chôn vùi cần xử lý

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 24, "size_y": 1 }
```

#### Question: Slow-Mover Value At Risk

Tổng giá trị vốn trong hàng tồn chậm (không bán > 30 ngày hoặc days_of_supply > 90).

```sql
SELECT ROUND(SUM(slow_mover_value_at_risk) / 1e6, 1) AS "Giá Trị Slow-Mover (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_slow_mover = true
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Vốn Hàng Chậm (Slow-Mover)",
    "scalar.field": "Giá Trị Slow-Mover (triệu VND)"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Dead Stock Value At Risk

Tổng giá trị vốn trong hàng tồn chết (không bán > 90 ngày).

```sql
SELECT ROUND(SUM(dead_stock_value_at_risk) / 1e6, 1) AS "Giá Trị Dead Stock (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_dead_stock = true
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Vốn Hàng Chết (Dead Stock)",
    "scalar.field": "Giá Trị Dead Stock (triệu VND)"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Slow-Mover SKU Count

Số SKU đang là hàng chậm.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Hàng Chậm"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_slow_mover = true
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Số SKU Hàng Chậm",
    "scalar.field": "SKU Hàng Chậm"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 3 }
```

#### Question: Dead Stock SKU Count

Số SKU đang là hàng tồn chết.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Hàng Chết"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_dead_stock = true
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Số SKU Hàng Chết (>90 ngày)",
    "scalar.field": "SKU Hàng Chết"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 18, "size_x": 6, "size_y": 3 }
```

#### Question: Danh Sách Slow-Mover Chi Tiết

Chi tiết SKU hàng chậm — vốn bị chôn, days_of_supply, enriched với health_class (DOG = strong delist signal).

```sql
SELECT
    mart_inventory_health.sku                                                     AS "SKU",
    mart_inventory_health.product_name                                            AS "Tên Sản Phẩm",
    mart_inventory_health.category                                                AS "Nhóm",
    mart_inventory_health.location_name                                           AS "Kho",
    ROUND(mart_inventory_health.on_hand, 0)                                       AS "Tồn (units)",
    ROUND(mart_inventory_health.days_of_supply, 0)                                AS "Days of Supply",
    ROUND(mart_inventory_health.slow_mover_value_at_risk / 1e6, 2)                AS "Vốn Bị Chôn (triệu)",
    mart_inventory_health.velocity_month                                          AS "Tháng Velocity",
    ROUND(mart_inventory_health.daily_velocity, 2)                                AS "Velocity (units/ngày)",
    mart_inventory_health.is_dead_stock                                           AS "Tồn Chết?",
    COALESCE(p.health_class, '-')                             AS "Health Class",
    COALESCE(p.abc_class, '-')                                AS "ABC",
    COALESCE(p.velocity_momentum, '-')                        AS "Momentum"
FROM main_marts.mart_inventory_health
LEFT JOIN main_marts.mart_product_health p ON mart_inventory_health.sku = p.sku
WHERE mart_inventory_health.snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND mart_inventory_health.is_slow_mover = true
  AND mart_inventory_health.on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
ORDER BY mart_inventory_health.slow_mover_value_at_risk DESC NULLS LAST
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Chi Tiết SKU Hàng Chậm (Top 50 Theo Giá Trị)",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 24, "size_y": 8 }
```

#### Question: Dead Stock Theo Health Class

Phân bổ dead stock theo health_class — DOG + DEAD = ưu tiên thanh lý cao nhất.

```sql
SELECT
    COALESCE(p.health_class, 'N/A (No COGS)')             AS "Health Class",
    COUNT(DISTINCT mart_inventory_health.sku)                                   AS "Số SKU",
    ROUND(SUM(mart_inventory_health.dead_stock_value_at_risk) / 1e6, 2)         AS "Vốn Dead Stock (triệu VND)"
FROM main_marts.mart_inventory_health
LEFT JOIN main_marts.mart_product_health p ON mart_inventory_health.sku = p.sku
WHERE mart_inventory_health.snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND mart_inventory_health.is_dead_stock = true
  AND mart_inventory_health.on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
GROUP BY p.health_class
ORDER BY SUM(mart_inventory_health.dead_stock_value_at_risk) DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Dead Stock Theo Health Class (DOG = Ưu Tiên Delist)",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Slow-Mover Value Theo Category

Phân bổ vốn hàng chậm theo nhóm sản phẩm.

```sql
SELECT
    COALESCE(category, 'Không phân loại')             AS "Nhóm Sản Phẩm",
    COUNT(DISTINCT sku)                                AS "Số SKU",
    ROUND(SUM(slow_mover_value_at_risk) / 1e6, 2)     AS "Giá Trị (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM main_marts.mart_inventory_health)
  AND is_slow_mover = true
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
GROUP BY category
ORDER BY SUM(slow_mover_value_at_risk) DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Vốn Hàng Chậm Theo Nhóm SP",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 14, "col": 12, "size_x": 12, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Source:** `mart_inventory_health` · `mart_product_health` · **Cadence:** daily · **Scope:** snapshot_date = latest available
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 24, "size_y": 1 }
```

---

### 📑 Tab: Inventory Trend

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Trend 90 ngày: ' || strftime(current_date - 90, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Xu hướng tồn kho — giá trị, OOS rate, và so sánh location

# Xu hướng tồn kho — giá trị, OOS rate, và so sánh location

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 24, "size_y": 1 }
```

#### Question: Stock Value Trend 90 Ngày

Xu hướng tổng giá trị tồn kho 90 ngày gần nhất.

```sql
SELECT
    snapshot_date                                     AS "Ngày",
    ROUND(SUM(stock_value_at_mac) / 1e6, 2)          AS "Giá Trị Tồn (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date >= current_date - INTERVAL '90 days'
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
GROUP BY snapshot_date
ORDER BY snapshot_date
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "card.title": "Xu Hướng Giá Trị Tồn Kho 90 Ngày",
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Triệu VND",
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["Giá Trị Tồn (triệu VND)"]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 16, "size_y": 6 }
```

#### Question: OOS Rate Trend 90 Ngày

Tỷ lệ SKU OOS theo ngày trong 90 ngày gần nhất.

```sql
SELECT
    snapshot_date                                                         AS "Ngày",
    ROUND(
        COUNT(DISTINCT CASE WHEN is_oos THEN sku END) * 100.0
        / NULLIF(COUNT(DISTINCT sku), 0),
        1
    )                                                                     AS "OOS Rate (%)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date >= current_date - INTERVAL '90 days'
  [[AND {{location_name}}]]
  [[AND {{category}}]]
GROUP BY snapshot_date
ORDER BY snapshot_date
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "card.title": "Tỷ Lệ OOS 90 Ngày (%)",
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "% SKU OOS",
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["OOS Rate (%)"]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 16, "size_x": 8, "size_y": 6 }
```

#### Question: Stock Value Trend Theo Location 30 Ngày

So sánh giá trị tồn kho từng kho theo ngày — 30 ngày gần nhất.

```sql
SELECT
    snapshot_date                                     AS "Ngày",
    location_name                                     AS "Kho",
    ROUND(SUM(stock_value_at_mac) / 1e6, 2)          AS "Giá Trị (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date >= current_date - INTERVAL '30 days'
  AND on_hand > 0
  AND mac IS NOT NULL
  [[AND {{category}}]]
GROUP BY snapshot_date, location_name
ORDER BY snapshot_date, location_name
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "card.title": "Giá Trị Tồn Kho Theo Kho (30 Ngày)",
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Triệu VND",
    "graph.dimensions": ["Ngày", "Kho"],
    "graph.metrics": ["Giá Trị (triệu VND)"]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 16, "size_y": 6 }
```

#### Question: Slow-Mover Value Trend 90 Ngày

Xu hướng giá trị hàng chậm — phát hiện tích tụ slow-mover theo thời gian.

```sql
SELECT
    snapshot_date                                     AS "Ngày",
    ROUND(SUM(slow_mover_value_at_risk) / 1e6, 2)    AS "Slow-Mover (triệu VND)",
    ROUND(SUM(dead_stock_value_at_risk) / 1e6, 2)    AS "Dead Stock (triệu VND)"
FROM main_marts.mart_inventory_health
WHERE snapshot_date >= current_date - INTERVAL '90 days'
  AND on_hand > 0
  [[AND {{location_name}}]]
  [[AND {{category}}]]
GROUP BY snapshot_date
ORDER BY snapshot_date
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "card.title": "Xu Hướng Vốn Hàng Chậm & Chết 90 Ngày",
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Triệu VND",
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["Slow-Mover (triệu VND)", "Dead Stock (triệu VND)"]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 16, "size_x": 8, "size_y": 6 }
```

#### Question: Monthly Stock Value Summary

Tổng hợp giá trị tồn kho theo tháng — 12 tháng gần nhất.

```sql
SELECT
    DATE_TRUNC('month', snapshot_date)::date          AS "Tháng",
    ROUND(AVG(daily_total) / 1e6, 2)                  AS "Avg Giá Trị/Ngày (triệu VND)",
    ROUND(MAX(daily_total) / 1e6, 2)                  AS "Max Giá Trị (triệu VND)",
    ROUND(MIN(daily_total) / 1e6, 2)                  AS "Min Giá Trị (triệu VND)"
FROM (
    SELECT
        snapshot_date,
        SUM(stock_value_at_mac) AS daily_total
    FROM main_marts.mart_inventory_health
    WHERE snapshot_date >= current_date - INTERVAL '12 months'
      AND on_hand > 0
      [[AND {{location_name}}]]
      [[AND {{category}}]]
    GROUP BY snapshot_date
) daily
GROUP BY DATE_TRUNC('month', snapshot_date)::date
ORDER BY 1 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Tổng Hợp Giá Trị Tồn Kho Theo Tháng",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 24, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Source:** `mart_inventory_health` · **Cadence:** daily · **Scope:** snapshot_date = latest available
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 24, "size_y": 1 }
```
