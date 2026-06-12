---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L1.5
uses_concepts: [scope_sales, net_revenue, gross_revenue]
---

# Order Revenue Explorer Blueprint

**Layer**: Audit / Reconciliation
**Purpose**: Drill-down để kiểm tra cách tính gross_revenue / net_revenue / total_collected. Chọn date-range (+ kênh) → xem chính xác từng đơn đóng góp, và 3 KPI tổng = đúng tổng các cột trong bảng. Dùng khi một dashboard khác ra số nghi ngờ sai và cần truy ngược tới từng dòng.

> **Database:** Sapo

Bảng đơn hàng + KPI dùng CHUNG một tập order (mọi status, không loại CANCELLED/Voided) trong cùng date-range + channel filter → KPI cộng đúng những gì hiển thị trong bảng.

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` · Layer L1.5 `[All]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales)
> **Why:** Revenue explorer is an audit tool covering all valid sales orders. Users can optionally filter further by segment via dashboard filters.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`gross_revenue`](../semantic/metrics.md#gross_revenue)

Base SQL: `WHERE scope_sales`. Segment drill-down via dashboard filter, not hardcoded SQL.
## 📂 Collection: Analytics

### Dashboard: Order Revenue Explorer

**Description**: Audit tool — chọn date-range + kênh, xem từng đơn và 3 số đo gross/net/collected. KPI tổng = tổng cột bảng dưới (cùng tập đơn, mọi status). Số hiển thị full, không rút gọn (compact) để đối chiếu chính xác.

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "thismonth",
  "field_id": 848
}
```

#### Filter: Channel

```json metabase-filter
{
  "slug": "channel",
  "type": "string/=",
  "field_id": 179
}
```

---

#### ❓ Question: Chu kỳ đã chọn

```sql
WITH filter_bounds AS (
    SELECT
        MIN(ordered_at)::DATE AS p_start,
        MAX(ordered_at)::DATE AS p_end,
        COUNT(*) AS n
    FROM fact_orders
    LEFT JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
    WHERE 1=1
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
)
SELECT
    '📅 Kỳ đã chọn: ' ||
    COALESCE(strftime(p_start, '%d/%m/%Y'), '—') || ' – ' ||
    COALESCE(strftime(p_end, '%d/%m/%Y'), '—') ||
    '  ·  ' || n || ' đơn (mọi status)'
    AS "Chu kỳ"
FROM filter_bounds
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Số đo tổng hợp — cộng dồn trên đúng tập đơn ở bảng dưới

# Số đo tổng hợp — cộng dồn trên đúng tập đơn ở bảng dưới

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Order Count

Tổng số đơn trong date-range + kênh đã chọn (mọi status). = số dòng bảng dưới.

```sql
SELECT COUNT(*) AS "Số đơn"
FROM fact_orders
LEFT JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
WHERE 1=1
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 3, "size_y": 3 }
```

#### Question: Gross Revenue

Tổng `gross_revenue` của đúng tập đơn ở bảng dưới.

```sql
SELECT COALESCE(SUM(gross_revenue), 0) AS "Gross Revenue"
FROM fact_orders
LEFT JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
WHERE 1=1
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Gross Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0 }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 3, "size_x": 5, "size_y": 3 }
```

#### Question: Net Revenue

Tổng `net_revenue` của đúng tập đơn ở bảng dưới.

```sql
SELECT COALESCE(SUM(net_revenue), 0) AS "Net Revenue"
FROM fact_orders
LEFT JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
WHERE 1=1
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0 }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 8, "size_x": 5, "size_y": 3 }
```

#### Question: Total Collected

Tổng `total_collected` của đúng tập đơn ở bảng dưới.

```sql
SELECT COALESCE(SUM(total_collected), 0) AS "Total Collected"
FROM fact_orders
LEFT JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
WHERE 1=1
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Total Collected": { "number_style": "currency", "currency": "VND", "decimals": 0 }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 13, "size_x": 5, "size_y": 3 }
```

#### 📝 Text: Chi tiết từng đơn — các cột Gross / Net / Collected cộng dồn = KPI ở trên

# Chi tiết từng đơn — các cột Gross / Net / Collected cộng dồn = KPI ở trên

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Order Detail

Từng đơn trong date-range + kênh đã chọn (mọi status). Hiển thị Gross → Discount → Tax → Net → Collected để thấy rõ cách suy ra net_revenue và total_collected. Số full, không rút gọn.

```sql
SELECT
    fact_orders.order_id AS "order_id",
    fact_orders.order_code AS "Mã đơn",
    strftime(fact_orders.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%d/%m/%Y %H:%M') AS "Thời gian",
    COALESCE(dim_channels.channel_name, 'Unknown') AS "Kênh",
    fact_orders.status AS "Trạng thái",
    fact_orders.gross_revenue AS "Gross Revenue",
    fact_orders.discount_amount AS "Discount",
    fact_orders.vat_amount AS "Tax (VAT)",
    fact_orders.net_revenue AS "Net Revenue",
    fact_orders.total_collected AS "Total Collected"
FROM fact_orders
LEFT JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
WHERE 1=1
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
ORDER BY fact_orders.ordered_at DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "table.columns": [
      {"name": "order_id", "enabled": false}
    ],
    "column_settings": {
      "Gross Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Discount": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Tax (VAT)": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Total Collected": { "number_style": "currency", "currency": "VND", "decimals": 0 },
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
{ "row": 7, "col": 0, "size_x": 18, "size_y": 12 }
```

---

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_channels · **Scope:** date-range + channel filter, **mọi status** (gồm CANCELLED/Voided) · **Mục đích:** audit/đối chiếu cách tính gross/net/collected · **Lưu ý:** bảng hiển thị tối đa ~2000 dòng (giới hạn Metabase) — thu hẹp date-range nếu cần đối chiếu đủ; KPI luôn cộng toàn bộ tập đơn.
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```
