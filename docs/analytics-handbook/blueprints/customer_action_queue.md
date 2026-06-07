---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
---

# 📘 Blueprint: Customer Action Queue [Retail]

> **Target Collection:** `Marketing & Customers`
> **Design Spec:** `designs/customer_action_queue.md`
> **Role:** Customer Success, Sales
> **Archetype:** Operational Dispatch Board (single view)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail)
## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Action Queue [Retail]

**Description**: Daily outreach queue — ranked list of retail customers needing contact today (CALL_NOW, REORDER_NUDGE, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK), with value at stake and action rationale. Refreshes daily from mart_customer_action_queue.

---

#### Filter: Action Type

```json metabase-filter
{
  "slug": "action_type",
  "type": "string/=",
  "field_id": 773
}
```

#### Filter: Value Group

```json metabase-filter
{
  "slug": "value_group",
  "type": "string/=",
  "field_id": 758
}
```

---

#### ❓ Question: Chu ky bao cao

Queue snapshot — shows when action queue was last generated.

```sql
SELECT
  '📅 Queue hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Cập nhật lúc: ' || strftime(MAX(queue_generated_at::TIMESTAMP), '%H:%M %d/%m/%Y')
  AS "Chu kỳ báo cáo"
FROM mart_customer_action_queue
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

#### 📝 Text: Hang doi outreach hom nay — theo thu tu uu tien va gia tri

# Hàng đợi outreach hôm nay — theo thứ tự ưu tiên và giá trị

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: CALL_NOW — Goi ngay

VIP/Gold khách at-risk — ưu tiên cao nhất, gọi ngay.

```sql
SELECT COUNT(*) AS "📞 Gọi ngay"
FROM mart_customer_action_queue
WHERE action_type = 'CALL_NOW'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "VIP/Gold đang At Risk"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: REORDER_NUDGE — Nhac tai mua

Khách quá hạn tái mua — nhắn tin hoặc gọi nhắc.

```sql
SELECT COUNT(*) AS "🔄 Nhắn tái mua"
FROM mart_customer_action_queue
WHERE action_type = 'REORDER_NUDGE'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Quá hạn chu kỳ tái mua"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 4, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: WIN_BACK — Lay lai khach

Khách đã churn — cần offer win-back.

```sql
SELECT COUNT(*) AS "🔙 Win-back"
FROM mart_customer_action_queue
WHERE action_type = 'WIN_BACK'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Churned, cần offer đặc biệt"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 8, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: SECOND_ORDER — Push don 2

Khách mua 1 lần, chưa quay lại — push đơn thứ 2.

```sql
SELECT COUNT(*) AS "🆕 Push đơn 2"
FROM mart_customer_action_queue
WHERE action_type = 'SECOND_ORDER'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "1 đơn, 15-45 ngày chưa mua lại"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: HIGH_CANCEL_RISK — Rui ro huy

Tỷ lệ huỷ cao — cần xác nhận đơn chủ động.

```sql
SELECT COUNT(*) AS "⚠️ Rủi ro huỷ"
FROM mart_customer_action_queue
WHERE action_type = 'HIGH_CANCEL_RISK'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.description": "Cancel rate > 50%"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### 📝 Text: Phan bo gia tri va so luong theo loai hanh dong

# Phân bổ giá trị và số lượng theo loại hành động

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Gia tri rui ro theo loai hanh dong

Tổng value at stake (estimate revenue) per action type — prioritize where money is.

```sql
SELECT
    CASE action_type
        WHEN 'CALL_NOW'         THEN '1. Gọi ngay 📞'
        WHEN 'REORDER_NUDGE'    THEN '2. Tái mua 🔄'
        WHEN 'WIN_BACK'         THEN '3. Win-back 🔙'
        WHEN 'SECOND_ORDER'     THEN '4. Đơn 2 🆕'
        WHEN 'HIGH_CANCEL_RISK' THEN '5. Rủi ro huỷ ⚠️'
    END AS "Loại hành động",
    SUM(value_at_stake) AS "Giá trị (VND)"
FROM mart_customer_action_queue
WHERE 1=1
[[AND {{action_type}}]]
[[AND {{value_group}}]]
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
{ "row": 7, "col": 0, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: So luong khach theo loai hanh dong

Số khách trong queue per action type.

```sql
SELECT
    CASE action_type
        WHEN 'CALL_NOW'         THEN '1. Gọi ngay 📞'
        WHEN 'REORDER_NUDGE'    THEN '2. Tái mua 🔄'
        WHEN 'WIN_BACK'         THEN '3. Win-back 🔙'
        WHEN 'SECOND_ORDER'     THEN '4. Đơn 2 🆕'
        WHEN 'HIGH_CANCEL_RISK' THEN '5. Rủi ro huỷ ⚠️'
    END AS "Loại hành động",
    COUNT(*) AS "Số khách"
FROM mart_customer_action_queue
WHERE 1=1
[[AND {{action_type}}]]
[[AND {{value_group}}]]
GROUP BY action_type
ORDER BY MIN(priority_rank)
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loại hành động"],
    "graph.metrics": ["Số khách"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Khách"
  }
}
```

```json metabase-pos
{ "row": 7, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Danh sach khach can lien he — sap xep theo uu tien va CLV

# Danh sách khách cần liên hệ — sắp xếp theo ưu tiên và CLV

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Queue — Danh sach outreach

Ranked customer action list — top 500 by priority_rank then lifetime_value DESC.

```sql
SELECT
    priority_rank                  AS "P",
    customer_code                  AS "Mã KH",
    customer_id                    AS "customer_id",
    CASE action_type
        WHEN 'CALL_NOW'         THEN '📞 Gọi ngay'
        WHEN 'REORDER_NUDGE'    THEN '🔄 Tái mua'
        WHEN 'WIN_BACK'         THEN '🔙 Win-back'
        WHEN 'SECOND_ORDER'     THEN '🆕 Đơn 2'
        WHEN 'HIGH_CANCEL_RISK' THEN '⚠️ Rủi ro huỷ'
    END                            AS "Hành động",
    full_name                      AS "Tên khách",
    phone                          AS "SĐT",
    value_group                    AS "Nhóm",
    action_rationale               AS "Lý do",
    value_at_stake                 AS "Giá trị",
    lifetime_value                 AS "CLV",
    recency_days                   AS "Ngày vắng",
    last_order_date                AS "Đơn cuối",
    predicted_next_purchase_date   AS "Dự kiến mua lại"
FROM mart_customer_action_queue
WHERE 1=1
[[AND {{action_type}}]]
[[AND {{value_group}}]]
ORDER BY priority_rank, lifetime_value DESC
LIMIT 500
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.columns": [
      { "name": "P",                    "enabled": true },
      { "name": "Mã KH",               "enabled": true },
      { "name": "customer_id",          "enabled": false },
      { "name": "Hành động",            "enabled": true },
      { "name": "Tên khách",            "enabled": true },
      { "name": "SĐT",                 "enabled": true },
      { "name": "Nhóm",                "enabled": true },
      { "name": "Lý do",               "enabled": true },
      { "name": "Giá trị",             "enabled": true },
      { "name": "CLV",                 "enabled": true },
      { "name": "Ngày vắng",           "enabled": true },
      { "name": "Đơn cuối",            "enabled": true },
      { "name": "Dự kiến mua lại",     "enabled": true }
    ],
    "column_settings": {
      "Mã KH": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/customers/{{customer_id}}?tab=actions"
        }
      },
      "Giá trị": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      },
      "CLV": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Giá trị"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Ngày vắng"],
        "type": "single",
        "operator": ">",
        "value": 60,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Source and Freshness

Source: mart_customer_action_queue · Daily snapshot · **Scope: RETAIL, action_type IS NOT NULL** · Ranked by priority_rank → lifetime_value DESC · Max 500 rows displayed

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```
