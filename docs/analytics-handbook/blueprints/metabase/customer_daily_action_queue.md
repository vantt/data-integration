---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - next_purchase_signal
---

# 📘 Blueprint: Daily · Customer Action Queue [Retail]

> **Database:** `Sapo`
> **Collection ID:** 99
> **Role:** Customer Success, Sales
> **Archetype:** Operational Dispatch Board (daily cadence, 2 tabs)
> **Source blueprints:** customer_action_queue.md (#99), customer_operational_dashboard.md (#48 tab3), retail_activation_cockpit.md (#102 tab1)

Consolidation board — "Who do I contact TODAY?" Single daily dispatch for CS/Sales. Combines call-queue, watchlists, and contactable activation signals from 3 existing boards.

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md)
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`next_purchase_signal`](../domains/customer.md)

## 📂 Collection: Marketing & Customers > 👥 Customer

---

### 🖥️ Dashboard: Daily · Customer Action Queue [Retail]

**Description**: Daily outreach dispatch board for CS/Sales — call queue (CALL_NOW, REORDER_NUDGE, REORDER_PREEMPT, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK), contactable activation signals, and watchlists (VIP, At-Risk, Churned, Cancel-Risk). Refreshes daily. Consolidates #99, #48 tab3, #102 tab1.

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

#### Filter: Contactable


```json metabase-filter
{
  "slug": "is_contactable",
  "type": "string/=",
  "field_id": 1661,
  "default": "true"
}
```

#### Filter: Next Purchase Signal


```json metabase-filter
{
  "slug": "next_purchase_signal",
  "type": "string/=",
  "field_id": 760
}
```

---

### 📑 Tab: 🎯 Hành động hôm nay

#### ❓ Question: Chu ky bao cao


Queue snapshot — shows today's date and when action queue was last generated.

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
    "dashcard.background": false
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### 📝 Text: Hàng đợi outreach hôm nay — theo thứ tự ưu tiên và giá trị

# Hàng đợi outreach hôm nay — theo thứ tự ưu tiên và giá trị
---

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: CALL_NOW — Goi ngay


VIP/Gold/Silver khách at-risk — ưu tiên cao nhất, gọi ngay.

```sql
SELECT COUNT(*) AS "📞 Gọi ngay"
FROM mart_customer_action_queue
WHERE action_type = 'CALL_NOW'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 6,
  "size_y": 3
}
```

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
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 3,
  "col": 6,
  "size_x": 6,
  "size_y": 3
}
```

#### ❓ Question: REORDER_PREEMPT — Nhac truoc


Khách sắp đến hạn tái mua — nhắc trước khi trễ.

```sql
SELECT COUNT(*) AS "⏰ Nhắc trước"
FROM mart_customer_action_queue
WHERE action_type = 'REORDER_PREEMPT'
[[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 3,
  "col": 12,
  "size_x": 6,
  "size_y": 3
}
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
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 6,
  "size_y": 3
}
```

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
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 6,
  "col": 6,
  "size_x": 6,
  "size_y": 3
}
```

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
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 6,
  "col": 12,
  "size_x": 6,
  "size_y": 3
}
```

---

#### 📝 Text: Contactable activation — OVERDUE và DUE_SOON có số điện thoại

# Contactable activation — OVERDUE và DUE_SOON có số điện thoại
---

```json metabase-pos
{
  "row": 9,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Contactable — OVERDUE va DUE_SOON


Retail customers with phone, past their expected repurchase window.

```sql
SELECT COUNT(*) AS "Contactable Due/Overdue"
FROM mart_customer_action_queue
WHERE is_contactable = true
  AND next_purchase_signal IN ('OVERDUE', 'DUE_SOON')
  [[AND {{action_type}}]]
  [[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 10,
  "col": 0,
  "size_x": 6,
  "size_y": 3
}
```

#### ❓ Question: LTV at Stake (Contactable)


Total lifetime value of contactable OVERDUE/DUE_SOON customers.

```sql
SELECT SUM(lifetime_value) AS "LTV at Stake"
FROM mart_customer_action_queue
WHERE is_contactable = true
  AND next_purchase_signal IN ('OVERDUE', 'DUE_SOON')
  [[AND {{action_type}}]]
  [[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"LTV at Stake\"]": {
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
{
  "row": 10,
  "col": 6,
  "size_x": 6,
  "size_y": 3
}
```

#### ❓ Question: Value at Stake (Contactable)


Total reactivation value in the contactable queue.

```sql
SELECT SUM(value_at_stake) AS "Value at Stake"
FROM mart_customer_action_queue
WHERE is_contactable = true
  [[AND {{action_type}}]]
  [[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Value at Stake\"]": {
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
{
  "row": 10,
  "col": 12,
  "size_x": 6,
  "size_y": 3
}
```

---

#### 📝 Text: Danh sách outreach — sắp xếp theo ưu tiên và CLV

# Danh sách outreach — sắp xếp theo ưu tiên và CLV
---

```json metabase-pos
{
  "row": 13,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

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
        WHEN 'REORDER_PREEMPT'  THEN '⏰ Nhắc trước'
        WHEN 'WIN_BACK'         THEN '🔙 Win-back'
        WHEN 'SECOND_ORDER'     THEN '🆕 Đơn 2'
        WHEN 'HIGH_CANCEL_RISK' THEN '⚠️ Rủi ro huỷ'
    END                            AS "Hành động",
    full_name                      AS "Tên khách",
    phone                          AS "SĐT",
    last_purchased_product         AS "SP cuối mua",
    top_affinity_product           AS "SP hay mua nhất",
    second_affinity_product        AS "SP hay mua #2",
    is_contactable                 AS "Liên lạc được",
    value_group                    AS "Nhóm",
    action_rationale               AS "Lý do",
    value_at_stake                 AS "Giá trị",
    lifetime_value                 AS "CLV",
    lifetime_contribution_margin   AS "Biên đóng góp",
    is_margin_negative             AS "Âm biên",
    recency_days                   AS "Ngày vắng",
    last_order_date                AS "Đơn cuối",
    predicted_next_purchase_date   AS "Dự kiến mua lại"
FROM mart_customer_action_queue
WHERE 1=1
[[AND {{action_type}}]]
[[AND {{value_group}}]]
[[AND {{is_contactable}}]]
[[AND {{next_purchase_signal}}]]
ORDER BY priority_rank, lifetime_value DESC
LIMIT 500
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.columns": [
      {
        "name": "P",
        "enabled": true
      },
      {
        "name": "Mã KH",
        "enabled": true
      },
      {
        "name": "customer_id",
        "enabled": false
      },
      {
        "name": "Hành động",
        "enabled": true
      },
      {
        "name": "Tên khách",
        "enabled": true
      },
      {
        "name": "SĐT",
        "enabled": true
      },
      {
        "name": "SP cuối mua",
        "enabled": true
      },
      {
        "name": "SP hay mua nhất",
        "enabled": true
      },
      {
        "name": "SP hay mua #2",
        "enabled": true
      },
      {
        "name": "Liên lạc được",
        "enabled": true
      },
      {
        "name": "Nhóm",
        "enabled": true
      },
      {
        "name": "Lý do",
        "enabled": true
      },
      {
        "name": "Giá trị",
        "enabled": true
      },
      {
        "name": "CLV",
        "enabled": true
      },
      {
        "name": "Biên đóng góp",
        "enabled": true
      },
      {
        "name": "Âm biên",
        "enabled": true
      },
      {
        "name": "Ngày vắng",
        "enabled": true
      },
      {
        "name": "Đơn cuối",
        "enabled": true
      },
      {
        "name": "Dự kiến mua lại",
        "enabled": true
      }
    ],
    "table.column_formatting": [
      {
        "columns": [
          "Giá trị"
        ],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": [
          "Ngày vắng"
        ],
        "type": "single",
        "operator": ">",
        "value": 60,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": [
          "Âm biên"
        ],
        "type": "single",
        "operator": "=",
        "value": true,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Mã KH\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/customers/{{customer_id}}?tab=actions"
        }
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 14,
  "col": 0,
  "size_x": 18,
  "size_y": 10
}
```

---

#### 📝 Text: Phân bổ giá trị và số lượng theo loại hành động

# Phân bổ giá trị và số lượng theo loại hành động
---

```json metabase-pos
{
  "row": 24,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Gia tri rui ro theo loai hanh dong


Tổng value at stake (estimate revenue) per action type — prioritize where money is.

```sql
SELECT
    CASE action_type
        WHEN 'CALL_NOW'         THEN '1. Gọi ngay 📞'
        WHEN 'REORDER_NUDGE'    THEN '2. Tái mua 🔄'
        WHEN 'REORDER_PREEMPT'  THEN '3. Nhắc trước ⏰'
        WHEN 'WIN_BACK'         THEN '4. Win-back 🔙'
        WHEN 'SECOND_ORDER'     THEN '5. Đơn 2 🆕'
        WHEN 'HIGH_CANCEL_RISK' THEN '6. Rủi ro huỷ ⚠️'
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
    "graph.dimensions": [
      "Loại hành động"
    ],
    "graph.colors": [
      "#509EE3"
    ],
    "graph.x_axis.title_text": "VND",
    "column_settings": {
      "[\"name\",\"Giá trị (VND)\"]": {
        "number_style": "currency",
        "currency": "VND",
        "currency_style": "symbol",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Giá trị (VND)"
    ]
  }
}
```

```json metabase-pos
{
  "row": 25,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

#### ❓ Question: So luong khach theo loai hanh dong


Số khách trong queue per action type.

```sql
SELECT
    CASE action_type
        WHEN 'CALL_NOW'         THEN '1. Gọi ngay 📞'
        WHEN 'REORDER_NUDGE'    THEN '2. Tái mua 🔄'
        WHEN 'REORDER_PREEMPT'  THEN '3. Nhắc trước ⏰'
        WHEN 'WIN_BACK'         THEN '4. Win-back 🔙'
        WHEN 'SECOND_ORDER'     THEN '5. Đơn 2 🆕'
        WHEN 'HIGH_CANCEL_RISK' THEN '6. Rủi ro huỷ ⚠️'
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
    "graph.dimensions": [
      "Loại hành động"
    ],
    "graph.colors": [
      "#88BDE6"
    ],
    "graph.x_axis.title_text": "Khách",
    "graph.metrics": [
      "Số khách"
    ]
  }
}
```

```json metabase-pos
{
  "row": 25,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: Dự báo mua hàng — khách sắp mua tuần này và tháng này

# Dự báo mua hàng — khách sắp mua tuần này và tháng này
---

```json metabase-pos
{
  "row": 31,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Upcoming Predicted Purchases — This Week


Retail customers whose `predicted_next_purchase_date` falls within the next 7 days — proactive engagement window.

```sql
SELECT
    COUNT(*) AS "Purchasing This Week",
    SUM(lifetime_value) AS "Total LTV",
    ROUND(AVG(avg_order_spend), 0) AS "Expected Avg Order Value"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND predicted_next_purchase_date IS NOT NULL
  AND predicted_next_purchase_date BETWEEN current_date AND current_date + INTERVAL '7 days'
  [[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Purchasing This Week\"]": {},
      "[\"name\",\"Total LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      },
      "[\"name\",\"Expected Avg Order Value\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 32,
  "col": 0,
  "size_x": 9,
  "size_y": 3
}
```

#### ❓ Question: Upcoming Predicted Purchases — This Month


Retail customers whose `predicted_next_purchase_date` falls within the next 30 days — pipeline visibility for the month.

```sql
SELECT
    COUNT(*) AS "Purchasing This Month",
    SUM(lifetime_value) AS "Total LTV",
    ROUND(AVG(avg_order_spend), 0) AS "Expected Avg Order Value"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND predicted_next_purchase_date IS NOT NULL
  AND predicted_next_purchase_date BETWEEN current_date AND current_date + INTERVAL '30 days'
  [[AND {{value_group}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Purchasing This Month\"]": {},
      "[\"name\",\"Total LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      },
      "[\"name\",\"Expected Avg Order Value\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 32,
  "col": 9,
  "size_x": 9,
  "size_y": 3
}
```

---

#### 📝 Text: Source: mart_customer_action_queue · Daily snapshot · **Scope: RETAIL, action_type IS NOT NULL** · Ranked by priority_rank → lifetime_value DESC · Max 500 rows · Filter "Liên lạc được = true" mặc định — bỏ chọn để xem cả khách không liên lạc được · "Âm biên" = biên đóng góp âm, cân nhắc bỏ khỏi high-touch

Source: mart_customer_action_queue · Daily snapshot · **Scope: RETAIL, action_type IS NOT NULL** · Ranked by priority_rank → lifetime_value DESC · Max 500 rows · Filter "Liên lạc được = true" mặc định — bỏ chọn để xem cả khách không liên lạc được · "Âm biên" = biên đóng góp âm, cân nhắc bỏ khỏi high-touch
---

```json metabase-pos
{
  "row": 35,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: 👀 Watchlists

#### ❓ Question: Chu ky bao cao watchlist


Snapshot label for watchlist tab.

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "dashcard.background": false
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### 📝 Text: Ưu tiên chăm sóc VIP — khách nào sắp mất? Gọi ngay!

# Ưu tiên chăm sóc VIP — khách nào sắp mất? Gọi ngay!
---

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: VIP Customer Watchlist


VIP customers sorted by recency — prioritize outreach for those becoming inactive.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    order_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Since Last Order",
    customer_status as "Status",
    last_order_date as "Last Order"
FROM dim_customers
WHERE value_group = 'VALUE_VIP'
  AND customer_id != 'Unknown'
ORDER BY recency_days DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": [
          "Days Since Last Order"
        ],
        "type": "single",
        "operator": ">",
        "value": 60,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": [
          "Days Since Last Order"
        ],
        "type": "single",
        "operator": ">",
        "value": 30,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```

---

#### 📝 Text: Sắp xếp ưu tiên reactivation — khách giá trị cao cần giữ trước

# Sắp xếp ưu tiên reactivation — khách giá trị cao cần giữ trước
---

```json metabase-pos
{
  "row": 11,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: At-Risk Reactivation Priority


At-risk customers ranked by lifetime value — highest value = highest reactivation priority.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    email as "Email",
    value_group as "Segment",
    order_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Inactive",
    last_order_date as "Last Order"
FROM dim_customers
WHERE customer_status = 'At Risk'
  AND customer_id != 'Unknown'
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": [
          "LTV"
        ],
        "type": "single",
        "operator": ">=",
        "value": 5000000,
        "color": "#7172AD",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "[\"name\",\"LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 12,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```

---

#### 📝 Text: Xác định cơ hội recovery — khách churned giá trị cao cần win-back

# Xác định cơ hội recovery — khách churned giá trị cao cần win-back
---

```json metabase-pos
{
  "row": 20,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Churned High-Value Customers


Recently churned customers (91-180 days) with high LTV — recovery campaign candidates.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    email as "Email",
    value_group as "Segment",
    order_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Inactive",
    last_order_date as "Last Order"
FROM dim_customers
WHERE customer_status = 'Churned'
  AND customer_id != 'Unknown'
  AND recency_days <= 180
  AND lifetime_value >= 1000000
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": [
          "LTV"
        ],
        "type": "single",
        "operator": ">=",
        "value": 5000000,
        "color": "#7172AD",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "[\"name\",\"LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 21,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```

---

#### 📝 Text: High cancel rate customers — rủi ro huỷ đơn

# High cancel rate customers — rủi ro huỷ đơn
---

```json metabase-pos
{
  "row": 29,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: High Cancel Rate Customers


Count of retail customers with cancel_rate above 30% — flag accounts requiring CS attention.

```sql
SELECT
    CASE
        WHEN cancel_rate >= 0.5  THEN '>= 50% (Very High)'
        WHEN cancel_rate >= 0.3  THEN '30-49% (High)'
        WHEN cancel_rate >= 0.1  THEN '10-29% (Moderate)'
        ELSE '< 10% (Low)'
    END AS "Cancel Rate Band",
    value_group AS "Segment",
    COUNT(*) AS "Customers"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND cancel_rate IS NOT NULL
GROUP BY 1, 2
ORDER BY
    MIN(CASE
        WHEN cancel_rate >= 0.5  THEN 1
        WHEN cancel_rate >= 0.3  THEN 2
        WHEN cancel_rate >= 0.1  THEN 3
        ELSE 4
    END),
    CASE value_group
        WHEN 'VALUE_VIP'    THEN 1
        WHEN 'VALUE_GOLD'   THEN 2
        WHEN 'VALUE_SILVER' THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": [
      "Cancel Rate Band",
      "Segment"
    ],
    "series_settings": {
      "VALUE_VIP": {
        "color": "#7172AD"
      },
      "VALUE_GOLD": {
        "color": "#509EE3"
      },
      "VALUE_SILVER": {
        "color": "#88BDE6"
      },
      "VALUE_BRONZE": {
        "color": "#C2D2E9"
      }
    },
    "graph.x_axis.title_text": "Cancel Rate Band",
    "graph.y_axis.title_text": "Customers",
    "graph.metrics": [
      "Customers"
    ]
  }
}
```

```json metabase-pos
{
  "row": 30,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### 📝 Text: Next purchase signal breakdown — ai đang OVERDUE và DUE_SOON?

# Next purchase signal breakdown — ai đang OVERDUE và DUE_SOON?
---

```json metabase-pos
{
  "row": 36,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Next Purchase Signal Breakdown


Count of retail customers by next_purchase_signal and value_group — identify who needs outreach now.

```sql
SELECT
    COALESCE(next_purchase_signal, 'N/A (1-time buyer)') AS "Signal",
    value_group AS "Segment",
    COUNT(*) AS "Customers"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY
    CASE COALESCE(next_purchase_signal, 'N/A (1-time buyer)')
        WHEN 'OVERDUE'   THEN 1
        WHEN 'DUE_SOON'  THEN 2
        WHEN 'ON_TRACK'  THEN 3
        ELSE 4
    END,
    CASE value_group
        WHEN 'VALUE_VIP'    THEN 1
        WHEN 'VALUE_GOLD'   THEN 2
        WHEN 'VALUE_SILVER' THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": [
          "Signal"
        ],
        "type": "single",
        "operator": "=",
        "value": "OVERDUE",
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": [
          "Signal"
        ],
        "type": "single",
        "operator": "=",
        "value": "DUE_SOON",
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{
  "row": 37,
  "col": 0,
  "size_x": 9,
  "size_y": 8
}
```

#### ❓ Question: Reactivation Mine — SILVER GOLD VIP


High-touch reactivation targets (SILVER/GOLD/VIP At-Risk and Churned). Includes all, not just contactable.

```sql
SELECT
  value_group                               AS "Tier",
  customer_status                           AS "Status",
  COUNT(*)                                  AS "Khách hàng",
  COUNT(CASE WHEN is_contactable THEN 1 END) AS "Có SĐT",
  SUM(lifetime_value)                       AS "Total LTV",
  ROUND(AVG(lifetime_contribution_margin) / 1000.0, 0) AS "Avg Contrib. (K)"
FROM mart_customer_action_queue
WHERE value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER')
  AND customer_status IN ('At Risk', 'Churned')
GROUP BY 1, 2
ORDER BY
  CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 ELSE 3 END,
  CASE customer_status WHEN 'Churned' THEN 1 ELSE 2 END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": [
          "Có SĐT"
        ],
        "type": "range",
        "colors": [
          "#EF8C8C",
          "#84BB4C"
        ],
        "min_type": "all",
        "max_type": "all",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Total LTV\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Avg Contrib. (K)\"]": {
        "suffix": "K VND"
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 37,
  "col": 9,
  "size_x": 9,
  "size_y": 8
}
```

---

#### 📝 Text: Source: dim_customers + mart_customer_action_queue · **Scope: RETAIL** · Daily snapshot · VIP/At-Risk/Churned from dim_customers (all-time) · Reactivation Mine from mart_customer_action_queue (daily queue) · Cancel rate from dim_customers

Source: dim_customers + mart_customer_action_queue · **Scope: RETAIL** · Daily snapshot · VIP/At-Risk/Churned from dim_customers (all-time) · Reactivation Mine from mart_customer_action_queue (daily queue) · Cancel rate from dim_customers

```json metabase-pos
{
  "row": 45,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---
