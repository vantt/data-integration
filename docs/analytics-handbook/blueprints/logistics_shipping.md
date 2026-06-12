---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L2
uses_concepts: [scope_sales]
---

# 📘 Blueprint: Logistics Shipping & Carrier Performance [All]

> **Target Collection:** `Operations > Logistics`
> **Design Spec:** `designs/logistics_shipping.md`
> **Role:** Warehouse Manager, Operations Manager, CS
> **Archetype:** Operational Report — Carrier Performance

<!-- SETUP: Resolve field_ids for shipped_at and carrier_id after first Metabase sync of fact_fulfillments -->

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` · Layer L2 `[All]` · All shipments regardless of sales channel/segment.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales)

## 📂 Collection: Operations > Logistics

---

### 🖥️ Dashboard: Logistics Shipping & Carrier Performance [All]

**Description**: Carrier performance and shipment tracking — delivery rate by carrier, avg delivery time, COD totals, shipment status breakdown, and detail table for delayed/undelivered shipments. Source: `fact_fulfillments`.

---

#### Filter: Date Range (shipped_at)

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "last30days",
  "field_id": null
}
```

<!-- TODO: Replace null with field_id for fact_fulfillments.shipped_at -->

#### Filter: Carrier

```json metabase-filter
{
  "slug": "carrier",
  "type": "string/=",
  "field_id": null
}
```

<!-- TODO: Replace null with field_id for fact_fulfillments.carrier_id -->

---

#### 📝 Text: Chu ky bao cao

# Hiệu suất vận chuyển & nhà vận chuyển

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Tong chuyen hang

```sql
SELECT COUNT(*) AS "Tổng chuyến"
FROM fact_fulfillments
WHERE shipped_at IS NOT NULL
[[AND {{date_range}}]]
[[AND {{carrier}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Đã giao cho nhà vận chuyển"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Da giao thanh cong

```sql
SELECT COUNT(*) AS "Đã giao thành công"
FROM fact_fulfillments
WHERE is_delivered = true
[[AND {{date_range}}]]
[[AND {{carrier}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "status = DELIVERED"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 3, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Ty le giao thanh cong

```sql
SELECT ROUND(
  100.0 * COUNT(*) FILTER (WHERE is_delivered = true)
  / NULLIF(COUNT(*) FILTER (WHERE shipped_at IS NOT NULL), 0),
  1
) AS "Tỷ lệ giao thành công (%)"
FROM fact_fulfillments
WHERE shipped_at IS NOT NULL
[[AND {{date_range}}]]
[[AND {{carrier}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Delivered / Shipped"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Thoi gian giao trung binh

```sql
SELECT ROUND(AVG(days_to_deliver), 1) AS "Avg ngày giao"
FROM fact_fulfillments
WHERE is_delivered = true
[[AND {{date_range}}]]
[[AND {{carrier}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Từ shipped_at đến delivered_at"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 9, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Tong COD

```sql
SELECT COALESCE(SUM(cod_amount), 0) AS "Tổng COD (VND)"
FROM fact_fulfillments
WHERE shipped_at IS NOT NULL
[[AND {{date_range}}]]
[[AND {{carrier}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tổng COD (VND)": {
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
{ "row": 1, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### 📝 Text: Hieu suat theo nha van chuyen

# Hiệu suất theo nhà vận chuyển

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Ty le giao thanh cong theo carrier

```sql
SELECT
    COALESCE(carrier_id, 'Unknown') AS "Nhà vận chuyển",
    COUNT(*) AS "Tổng chuyến",
    COUNT(*) FILTER (WHERE is_delivered = true) AS "Đã giao",
    ROUND(
      100.0 * COUNT(*) FILTER (WHERE is_delivered = true)
      / NULLIF(COUNT(*), 0),
      1
    ) AS "Tỷ lệ giao (%)"
FROM fact_fulfillments
WHERE shipped_at IS NOT NULL
[[AND {{date_range}}]]
[[AND {{carrier}}]]
GROUP BY carrier_id
ORDER BY "Tỷ lệ giao (%)" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhà vận chuyển"],
    "graph.metrics": ["Tỷ lệ giao (%)"],
    "graph.colors": ["#84BB4C"],
    "graph.x_axis.title_text": "%",
    "graph.goal_value": 95,
    "graph.show_goal": true
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Thoi gian giao trung binh theo carrier

```sql
SELECT
    COALESCE(carrier_id, 'Unknown') AS "Nhà vận chuyển",
    ROUND(AVG(days_to_deliver), 1) AS "Avg ngày giao"
FROM fact_fulfillments
WHERE is_delivered = true
[[AND {{date_range}}]]
[[AND {{carrier}}]]
GROUP BY carrier_id
ORDER BY "Avg ngày giao" ASC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhà vận chuyển"],
    "graph.metrics": ["Avg ngày giao"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Ngày"
  }
}
```

```json metabase-pos
{ "row": 5, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Phan bo trang thai lo hang

```sql
SELECT
    COALESCE(shipment_status, status, 'Unknown') AS "Trạng thái",
    COUNT(*) AS "Số chuyến"
FROM fact_fulfillments
WHERE shipped_at IS NOT NULL
[[AND {{date_range}}]]
[[AND {{carrier}}]]
GROUP BY shipment_status, status
ORDER BY "Số chuyến" DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Trạng thái",
    "pie.metric": "Số chuyến"
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 6, "size_y": 6 }
```

---

#### ❓ Question: Phan bo so ngay giao

```sql
SELECT
    CASE
        WHEN days_to_deliver <= 1 THEN '≤1 ngày'
        WHEN days_to_deliver <= 2 THEN '2 ngày'
        WHEN days_to_deliver <= 3 THEN '3 ngày'
        WHEN days_to_deliver <= 5 THEN '4-5 ngày'
        WHEN days_to_deliver <= 7 THEN '6-7 ngày'
        ELSE '> 7 ngày'
    END AS "Khoảng thời gian",
    COUNT(*) AS "Số chuyến"
FROM fact_fulfillments
WHERE is_delivered = true
[[AND {{date_range}}]]
[[AND {{carrier}}]]
GROUP BY 1
ORDER BY MIN(days_to_deliver)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Khoảng thời gian"],
    "graph.metrics": ["Số chuyến"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 11, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### 📝 Text: Chi tiet chuyen hang

# Chi tiết chuyến hàng

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Bang chi tiet chuyen hang

```sql
SELECT
    order_code                  AS "Mã đơn",
    fulfillment_code            AS "Mã fulfillment",
    tracking_code               AS "Tracking",
    COALESCE(carrier_id, '-')   AS "Nhà VC",
    shipping_service            AS "Dịch vụ",
    COALESCE(shipment_status, status) AS "Trạng thái",
    strftime(shipped_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%d/%m/%Y') AS "Ngày giao VC",
    strftime(delivered_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%d/%m/%Y') AS "Ngày giao KH",
    days_to_deliver             AS "Số ngày",
    cod_amount                  AS "COD"
FROM fact_fulfillments
WHERE shipped_at IS NOT NULL
[[AND {{date_range}}]]
[[AND {{carrier}}]]
ORDER BY shipped_at DESC
LIMIT 1000
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "COD": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      },
      "Số ngày": {
        "number_style": "number",
        "decimals": 0
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Số ngày"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Source and Freshness

Source: fact_fulfillments · Filter on shipped_at · **Scope: ALL shipments** · Days > 5 highlighted red · Max 1000 rows — narrow date range if needed

```json metabase-pos
{ "row": 28, "col": 0, "size_x": 18, "size_y": 1 }
```
