---
dashboard_name: Product Inventory Health
collection: Operations > Logistics
database: Sapo DuckDB
description: "Daily inventory snapshots: OOS, slow-mover, days-of-supply, capital tied up"
audience: Inventory Manager, Ops Manager
cadence: Daily
status: ACTIVE
---

# Product Inventory Health Blueprint

**Playbook**: [Inventory Health](../playbooks/product_inventory.md)

Dashboard kiểm tra tồn kho hàng ngày — OOS alerts, slow-mover exposure, stock value theo location. 3 tabs: Current Stock / Slow-Mover & Dead Stock / Inventory Trend.

> **Database:** Sapo DuckDB

## 📂 Collection: Operations > Logistics

### Dashboard: Product Inventory Health [All]

**Description**: Daily inventory check — OOS count, low-stock alerts, slow-mover capital exposure, stock trend by location. Audience: Inventory Manager, Ops Manager.

---

#### Filter: Snapshot Date

```json metabase-filter
{
  "slug": "snapshot_date",
  "type": "date/all-options",
  "default": "yesterday"
}
```

#### Filter: Location

```json metabase-filter
{
  "slug": "location_name",
  "type": "string/="
}
```

#### Filter: Category

```json metabase-filter
{
  "slug": "category",
  "type": "string/="
}
```

---

### 📑 Tab: Current Stock

#### 📝 Text: Tình trạng tồn kho hôm nay — OOS, low-stock, và giá trị vốn tồn theo location

# Tình trạng tồn kho hôm nay — OOS, low-stock, và giá trị vốn tồn theo location

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 24, "size_y": 1 }
```

#### Question: OOS SKUs

Số SKU đang hết hàng (on_hand ≤ 0) theo snapshot gần nhất.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Hết Hàng"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_oos = true
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 0, "size_x": 4, "size_y": 3 }
```

#### Question: Low Stock SKUs

Số SKU cảnh báo sắp hết (on_hand > 0 và ≤ min_value).

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Sắp Hết"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_low_stock = true
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 4, "size_x": 4, "size_y": 3 }
```

#### Question: Tổng Giá Trị Tồn Kho

Tổng giá trị tồn kho theo MAC (Moving Average Cost).

```sql
SELECT ROUND(SUM(stock_value_at_mac) / 1e6, 1) AS "Giá Trị Tồn Kho (triệu VND)"
FROM fact_inventory_snapshot
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_inventory_snapshot)
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 8, "size_x": 4, "size_y": 3 }
```

#### Question: Tổng SKU Có Hàng

Tổng số SKU đang có hàng trên tất cả locations.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Có Hàng"
FROM fact_inventory_snapshot
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_inventory_snapshot)
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 12, "size_x": 4, "size_y": 3 }
```

#### Question: Giá Trị Tồn Kho Theo Location

Breakdown giá trị tồn kho và số SKU theo từng kho.

```sql
SELECT
    location_name                                     AS "Kho",
    COUNT(DISTINCT sku)                               AS "Số SKU",
    ROUND(SUM(on_hand), 0)                            AS "Tổng Tồn (units)",
    ROUND(SUM(stock_value_at_mac) / 1e6, 2)           AS "Giá Trị (triệu VND)",
    COUNT(DISTINCT CASE WHEN on_hand <= 0 THEN sku END) AS "SKU OOS"
FROM fact_inventory_snapshot
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_inventory_snapshot)
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 4, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Top 20 SKU Theo Giá Trị Tồn Kho

Top 20 SKU chiếm giá trị vốn tồn cao nhất — snapshot gần nhất.

```sql
SELECT
    sku                                               AS "SKU",
    product_name                                      AS "Tên Sản Phẩm",
    location_name                                     AS "Kho",
    ROUND(on_hand, 0)                                 AS "Tồn (units)",
    ROUND(mac, 0)                                     AS "MAC (VND/unit)",
    ROUND(stock_value_at_mac / 1e6, 2)                AS "Giá Trị (triệu VND)",
    bin_location                                      AS "Vị Trí Kệ"
FROM fact_inventory_snapshot
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_inventory_snapshot)
  AND on_hand > 0
  AND mac IS NOT NULL
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
ORDER BY stock_value_at_mac DESC NULLS LAST
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
{ "row": 4, "col": 12, "size_x": 12, "size_y": 6 }
```

#### Question: Danh Sách SKU OOS

Chi tiết các SKU đang hết hàng — để gửi reorder alert.

```sql
SELECT
    sku                                               AS "SKU",
    product_name                                      AS "Tên Sản Phẩm",
    location_name                                     AS "Kho",
    ROUND(on_hand, 0)                                 AS "Tồn (units)",
    ROUND(committed, 0)                               AS "Committed",
    ROUND(incoming, 0)                                AS "Đang Về",
    ROUND(days_of_supply, 0)                          AS "Days of Supply (trước OOS)"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_oos = true
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
ORDER BY sku, location_name
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
{ "row": 10, "col": 0, "size_x": 24, "size_y": 6 }
```

---

### 📑 Tab: Slow-Mover & Dead Stock

#### 📝 Text: Hàng tồn chậm và tồn chết — vốn bị chôn vùi cần xử lý

# Hàng tồn chậm và tồn chết — vốn bị chôn vùi cần xử lý

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 24, "size_y": 1 }
```

#### Question: Slow-Mover Value At Risk

Tổng giá trị vốn trong hàng tồn chậm (không bán > 30 ngày hoặc days_of_supply > 90).

```sql
SELECT ROUND(SUM(slow_mover_value_at_risk) / 1e6, 1) AS "Giá Trị Slow-Mover (triệu VND)"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_slow_mover = true
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Dead Stock Value At Risk

Tổng giá trị vốn trong hàng tồn chết (không bán > 90 ngày).

```sql
SELECT ROUND(SUM(dead_stock_value_at_risk) / 1e6, 1) AS "Giá Trị Dead Stock (triệu VND)"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_dead_stock = true
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Slow-Mover SKU Count

Số SKU đang là hàng chậm.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Hàng Chậm"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_slow_mover = true
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 12, "size_x": 6, "size_y": 3 }
```

#### Question: Dead Stock SKU Count

Số SKU đang là hàng tồn chết.

```sql
SELECT COUNT(DISTINCT sku) AS "SKU Hàng Chết"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_dead_stock = true
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 18, "size_x": 6, "size_y": 3 }
```

#### Question: Danh Sách Slow-Mover Chi Tiết

Chi tiết SKU hàng chậm — vốn bị chôn, days_of_supply, ngày bán gần nhất.

```sql
SELECT
    h.sku                                                     AS "SKU",
    h.product_name                                            AS "Tên Sản Phẩm",
    h.category                                                AS "Nhóm",
    h.location_name                                           AS "Kho",
    ROUND(h.on_hand, 0)                                       AS "Tồn (units)",
    ROUND(h.days_of_supply, 0)                                AS "Days of Supply",
    ROUND(h.slow_mover_value_at_risk / 1e6, 2)                AS "Vốn Bị Chôn (triệu)",
    h.velocity_month                                          AS "Tháng Velocity",
    ROUND(h.daily_velocity, 2)                                AS "Velocity (units/ngày)",
    h.is_dead_stock                                           AS "Tồn Chết?"
FROM mart_inventory_health h
WHERE h.snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND h.is_slow_mover = true
  AND h.on_hand > 0
  [[AND h.location_name = {{location_name}}]]
  [[AND h.category = {{category}}]]
ORDER BY h.slow_mover_value_at_risk DESC NULLS LAST
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
{ "row": 4, "col": 0, "size_x": 24, "size_y": 8 }
```

#### Question: Slow-Mover Value Theo Category

Phân bổ vốn hàng chậm theo nhóm sản phẩm.

```sql
SELECT
    COALESCE(category, 'Không phân loại')             AS "Nhóm Sản Phẩm",
    COUNT(DISTINCT sku)                                AS "Số SKU",
    ROUND(SUM(slow_mover_value_at_risk) / 1e6, 2)     AS "Giá Trị (triệu VND)"
FROM mart_inventory_health
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM mart_inventory_health)
  AND is_slow_mover = true
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
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
{ "row": 12, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Committed Value At Risk

Giá trị hàng đã committed nhưng chưa xuất kho — vốn đang treo.

```sql
SELECT
    sku                                               AS "SKU",
    product_name                                      AS "Tên Sản Phẩm",
    location_name                                     AS "Kho",
    ROUND(committed, 0)                               AS "Committed (units)",
    ROUND(committed_value_at_mac / 1e6, 2)            AS "Giá Trị Committed (triệu VND)"
FROM fact_inventory_snapshot
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM fact_inventory_snapshot)
  AND committed > 0
  AND mac IS NOT NULL
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
ORDER BY committed_value_at_mac DESC NULLS LAST
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "card.title": "Top 20 SKU Có Committed Value Cao",
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 12, "col": 12, "size_x": 12, "size_y": 6 }
```

---

### 📑 Tab: Inventory Trend

#### 📝 Text: Xu hướng tồn kho — giá trị, OOS rate, và so sánh location

# Xu hướng tồn kho — giá trị, OOS rate, và so sánh location

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 24, "size_y": 1 }
```

#### Question: Stock Value Trend 90 Ngày

Xu hướng tổng giá trị tồn kho 90 ngày gần nhất.

```sql
SELECT
    snapshot_date                                     AS "Ngày",
    ROUND(SUM(stock_value_at_mac) / 1e6, 2)          AS "Giá Trị Tồn (triệu VND)"
FROM fact_inventory_snapshot
WHERE snapshot_date >= current_date - INTERVAL '90 days'
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 0, "size_x": 16, "size_y": 6 }
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
FROM mart_inventory_health
WHERE snapshot_date >= current_date - INTERVAL '90 days'
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 1, "col": 16, "size_x": 8, "size_y": 6 }
```

#### Question: Stock Value Trend Theo Location 30 Ngày

So sánh giá trị tồn kho từng kho theo ngày — 30 ngày gần nhất.

```sql
SELECT
    snapshot_date                                     AS "Ngày",
    location_name                                     AS "Kho",
    ROUND(SUM(stock_value_at_mac) / 1e6, 2)          AS "Giá Trị (triệu VND)"
FROM fact_inventory_snapshot
WHERE snapshot_date >= current_date - INTERVAL '30 days'
  AND on_hand > 0
  AND mac IS NOT NULL
  [[AND category = {{category}}]]
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
{ "row": 7, "col": 0, "size_x": 16, "size_y": 6 }
```

#### Question: Slow-Mover Value Trend 90 Ngày

Xu hướng giá trị hàng chậm — phát hiện tích tụ slow-mover theo thời gian.

```sql
SELECT
    snapshot_date                                     AS "Ngày",
    ROUND(SUM(slow_mover_value_at_risk) / 1e6, 2)    AS "Slow-Mover (triệu VND)",
    ROUND(SUM(dead_stock_value_at_risk) / 1e6, 2)    AS "Dead Stock (triệu VND)"
FROM mart_inventory_health
WHERE snapshot_date >= current_date - INTERVAL '90 days'
  AND on_hand > 0
  [[AND location_name = {{location_name}}]]
  [[AND category = {{category}}]]
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
{ "row": 7, "col": 16, "size_x": 8, "size_y": 6 }
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
    FROM fact_inventory_snapshot
    WHERE snapshot_date >= current_date - INTERVAL '12 months'
      AND on_hand > 0
      [[AND location_name = {{location_name}}]]
      [[AND category = {{category}}]]
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
{ "row": 13, "col": 0, "size_x": 24, "size_y": 6 }
```
