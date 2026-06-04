# Order Detail Blueprint [Retail]

**Design Spec**: [Order Detail View](../designs/order_detail_view.md)

Chi tiet don hang — header, economics (margin/COGS/fees), line items, payments. Nhan order_id tu URL parameter.

## 📂 Collection: Operations > Order Management

### 🖥️ Dashboard: Order Detail [Retail]

**Description**: Chi tiet 1 don hang — thong tin don, tai chinh (P&L), san pham, thanh toan. Truy cap tu Order Listing.

---

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Chu kỳ: Theo filter được chọn (không cố định)'
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### Filter: Order ID

```json metabase-filter
{
  "slug": "order_id",
  "type": "number/="
}
```

---

#### 📝 Text: Order Summary

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Order Header

Thong tin chinh cua don hang.

```sql
SELECT
    o.order_code AS "Ma Don",
    o.order_timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh' AS "Ngay Dat",
    os.status_code AS "Trang Thai",
    o.payment_status AS "Thanh Toan",
    o.fulfillment_status AS "Van Chuyen",
    c.channel_name AS "Kenh Ban",
    b.branch_location_name AS "Chi Nhanh",
    s.full_name AS "Nhan Vien",
    g.province AS "Tinh",
    g.district AS "Quan/Huyen",
    o.first_shipped_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS "Ngay Xuat Kho",
    CASE
        WHEN o.first_shipped_at IS NULL THEN NULL
        ELSE ROUND(date_diff('minute', o.order_timestamp, o.first_shipped_at) / 60.0, 1)
    END AS "Gio Toi Xuat Kho",
    CASE
        WHEN o.time_to_complete_hours IS NULL THEN NULL
        ELSE ROUND(o.time_to_complete_hours, 1)
    END AS "Gio Hoan Thanh"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
LEFT JOIN dim_branch_location b ON o.branch_location_key = b.branch_location_key
LEFT JOIN dim_order_status os ON o.status_key = os.status_key
LEFT JOIN dim_staff s ON o.seller_staff_key = s.staff_key
LEFT JOIN dim_geography g ON o.shipping_geography_key = g.geography_key
WHERE o.order_id = {{order_id}}
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": true,
    "table.pivot_column": null,
    "table.cell_column": null,
    "column_settings": {
      "[\"name\",\"Ngay Dat\"]": {"date_style": "D/M/YYYY, h:mm A"},
      "[\"name\",\"Ngay Xuat Kho\"]": {"date_style": "D/M/YYYY, h:mm A"},
      "[\"name\",\"Ma Don\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Ma Don}}"
        }
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":18, "size_y":4}
```

#### 📝 Text: Financials

```json metabase-pos
{"row": 7, "col":0, "size_x":18, "size_y":1}
```

#### Question: Order Economics

Metrics tai chinh — revenue waterfall, COGS, margin, Shopee fees.

```sql
SELECT
    o.gross_revenue AS "Doanh Thu Gop",
    o.discount_amount AS "Chiet Khau",
    CASE
        WHEN o.gross_revenue = 0 THEN NULL
        ELSE ROUND(o.discount_amount * 100.0 / o.gross_revenue, 1)
    END AS "Ty Le CK %",
    o.net_revenue AS "Doanh Thu Thuan",
    o.vat_amount AS "Thue",
    o.total_collected AS "Tong Thu",
    e.cogs_amount AS "Gia Von (MISA)",
    e.gross_profit AS "Lai Gop",
    ROUND(e.gross_margin_pct * 100, 1) AS "Bien Lai Gop %",
    e.shopee_platform_fees AS "Phi San Shopee",
    e.shopee_net_settlement AS "Shopee Chuyen Ve",
    e.channel_net_profit AS "Lai Rong Kenh",
    ROUND(e.channel_net_margin_pct * 100, 1) AS "Bien Rong Kenh %"
FROM fact_orders o
LEFT JOIN fact_order_economics e ON o.order_id = e.order_id
WHERE o.order_id = {{order_id}}
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": true,
    "column_settings": {
      "[\"name\",\"Doanh Thu Gop\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Chiet Khau\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Doanh Thu Thuan\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Thue\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Tong Thu\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Gia Von (MISA)\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Lai Gop\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Phi San Shopee\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Shopee Chuyen Ve\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Lai Rong Kenh\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false}
    }
  }
}
```

```json metabase-pos
{"row": 8, "col":0, "size_x":18, "size_y":4}
```

#### 📝 Text: Line Items

```json metabase-pos
{"row": 12, "col":0, "size_x":18, "size_y":1}
```

#### Question: Line Items

Danh sach san pham trong don.

```sql
SELECT
    p.product_name AS "San Pham",
    p.variant_name AS "Phien Ban",
    p.sku AS "SKU",
    s.quantity AS "SL",
    CASE
        WHEN s.quantity = 0 THEN NULL
        ELSE ROUND(s.revenue / s.quantity, 0)
    END AS "Don Gia",
    s.revenue AS "Doanh Thu",
    s.discount_amount AS "CK Truc Tiep",
    s.distributed_discount_amount AS "CK Phan Bo",
    COALESCE(s.discount_amount, 0) + COALESCE(s.distributed_discount_amount, 0) AS "Tong CK",
    s.weight_grams AS "Can Nang (g)"
FROM fact_sales s
LEFT JOIN dim_products p ON s.product_key = p.product_key
WHERE s.order_id = {{order_id}}
ORDER BY s.order_line_id
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"Don Gia\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Doanh Thu\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"CK Truc Tiep\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"CK Phan Bo\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Tong CK\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false}
    }
  }
}
```

```json metabase-pos
{"row": 13, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Payments

```json metabase-pos
{"row": 19, "col":0, "size_x":18, "size_y":1}
```

#### Question: Payments

Cac giao dich thanh toan cua don.

```sql
SELECT
    pm.payment_method_name AS "Phuong Thuc",
    fp.amount AS "So Tien",
    fp.status AS "Trang Thai",
    fp.payment_timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh' AS "Thoi Gian Tao",
    fp.paid_on AT TIME ZONE 'Asia/Ho_Chi_Minh' AS "Thoi Gian Thanh Toan"
FROM fact_payments fp
LEFT JOIN dim_payment_methods pm ON fp.payment_method_key = pm.payment_method_key
WHERE fp.order_id = {{order_id}}
ORDER BY fp.payment_timestamp
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"So Tien\"]": {"number_style": "currency", "currency": "VND", "currency_in_header": false},
      "[\"name\",\"Thoi Gian Tao\"]": {"date_style": "D/M/YYYY, h:mm A"},
      "[\"name\",\"Thoi Gian Thanh Toan\"]": {"date_style": "D/M/YYYY, h:mm A"}
    }
  }
}
```

```json metabase-pos
{"row": 20, "col":0, "size_x":18, "size_y":4}
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_items · **Cadence:** single-order · **Scope:** selected order_code · **Caveats:** Single order detail
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

