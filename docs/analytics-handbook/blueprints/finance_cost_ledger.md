# Blueprint: Cost Ledger Analyzer [All]

**Playbook**: [Cost Ledger Analyzer](../playbooks/finance_cost_ledger.md)

> **Target Collection:** `Finance`
> **Database:** Sapo
> **Role:** CFO, Accounting Manager
> **Archetype:** Operational Cockpit
> **Description:** Audience: CFO/Accounting. Scope: All sales channels. Câu hỏi: Tiền đi đâu? Breakdown costs by channel + cost type.

## 📂 Collection: Finance

Dashboard phân tích cơ cấu chi phí theo order — COGS, phí sàn, thuế, vận chuyển, chiết khấu. Giúp CFO và Kế toán trả lời "Tiền của tôi đi đâu?" theo kênh và loại chi phí.

---

### 🖥️ Dashboard: Cost Ledger Analyzer [All]

**Description**: Phân tích cơ cấu chi phí đơn hàng: COGS, phí sàn Shopee, thuế, vận chuyển và chiết khấu — breakdown theo kênh và thời gian. Scope: tất cả kênh bán hàng (is_sales_channel = true, loại trừ đơn CANCELLED/Voided).

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "thismonth"
}
```

---

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date), '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') || ' → ' || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### ❓ Question: Total Costs MTD

Tổng chi phí tháng này — tất cả loại: COGS + phí sàn + thuế + vận chuyển + chiết khấu.

**Domain Reference**: [Total Costs](../domains/finance.md#1-total-costs-tổng-chi-phí)

```sql
WITH this_period AS (
    SELECT COALESCE(SUM(fc.amount), 0) AS val
    FROM fact_order_costs fc
    JOIN fact_orders fo ON fc.order_id = fo.order_id
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.is_sales_channel = true
      AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
),
prev_period AS (
    SELECT COALESCE(SUM(fc.amount), 0) AS val
    FROM fact_order_costs fc
    JOIN fact_orders fo ON fc.order_id = fo.order_id
    WHERE fo.status NOT IN ('CANCELLED', 'Voided')
      AND fo.is_sales_channel = true
      AND fc.date_key >= CAST(date_trunc('month', current_date) - INTERVAL '1 month' AS INTEGER)
      AND fc.date_key < CAST(date_trunc('month', current_date) AS INTEGER)
)
SELECT
    t.val AS "Tong chi phi",
    p.val AS "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong chi phi": {
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
{ "row": 2, "col": 0, "size_x": 5, "size_y": 3 }
```

---

#### ❓ Question: COGS Ratio MTD

Tỷ lệ COGS / tổng chi phí tháng này — COGS chiếm bao nhiêu % "tiền ra"?

**Domain Reference**: [COGS Ratio — Cost Ledger](../domains/finance.md#2-cogs-ratio--cost-ledger-tỷ-lệ-giá-vốn--tổng-chi-phí)

```sql
SELECT
    ROUND(
        SUM(CASE WHEN fc.cost_category = 'COGS' THEN fc.amount ELSE 0 END) * 100.0
        / NULLIF(SUM(fc.amount), 0),
        1
    ) AS "COGS %"
FROM fact_order_costs fc
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "COGS %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 5, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Platform Fees Ratio MTD

Tỷ lệ phí sàn (Shopee) / tổng chi phí tháng này.

**Domain Reference**: [Platform Fees Ratio](../domains/finance.md#3-platform-fees-ratio-tỷ-lệ-phí-sàn--tổng-chi-phí)

```sql
SELECT
    ROUND(
        SUM(CASE WHEN fc.cost_category = 'PLATFORM_FEE' THEN fc.amount ELSE 0 END) * 100.0
        / NULLIF(SUM(fc.amount), 0),
        1
    ) AS "Phi san %"
FROM fact_order_costs fc
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Phi san %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 9, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Voucher Subsidy Ratio MTD

Tỷ lệ chiết khấu / voucher / tổng chi phí tháng này.

**Domain Reference**: [Voucher / Discount Ratio](../domains/finance.md#4-voucher--discount-ratio-tỷ-lệ-chiết-khấu--tổng-chi-phí)

```sql
SELECT
    ROUND(
        SUM(CASE WHEN fc.cost_category = 'DISCOUNT' THEN fc.amount ELSE 0 END) * 100.0
        / NULLIF(SUM(fc.amount), 0),
        1
    ) AS "Chiet khau %"
FROM fact_order_costs fc
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Chiet khau %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 13, "size_x": 5, "size_y": 3 }
```

---

#### ❓ Question: Cost Composition by Month

Stacked bar — cơ cấu chi phí theo tháng: COGS / Phí sàn / Thuế / Vận chuyển / Chiết khấu. 12 tháng gần nhất.

**Domain Reference**: [Cost Composition by Month](../domains/finance.md#5-cost-composition-by-month-cơ-cấu-chi-phí-theo-tháng)

```sql
SELECT
    date_trunc('month', CAST(CAST(fc.date_key AS VARCHAR) AS DATE)) AS "Thang",
    CASE fc.cost_category
        WHEN 'COGS'         THEN 'Gia von (COGS)'
        WHEN 'PLATFORM_FEE' THEN 'Phi san'
        WHEN 'TAX'          THEN 'Thue'
        WHEN 'SHIPPING'     THEN 'Van chuyen'
        WHEN 'DISCOUNT'     THEN 'Chiet khau / Voucher'
        ELSE fc.cost_category
    END                                                              AS "Loai chi phi",
    COALESCE(SUM(fc.amount), 0)                                      AS "So tien"
FROM fact_order_costs fc
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) - INTERVAL '11 months' AS INTEGER)
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Thang", "Loai chi phi"],
    "graph.metrics": ["So tien"],
    "stackable.stack_type": "stacked",
    "series_settings": {
      "Gia von (COGS)":       { "color": "#509EE3" },
      "Phi san":               { "color": "#EF8C8C" },
      "Thue":                  { "color": "#F9D45C" },
      "Van chuyen":            { "color": "#A989C5" },
      "Chiet khau / Voucher":  { "color": "#F2A86F" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "So tien": {
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
{ "row": 5, "col": 0, "size_x": 12, "size_y": 7 }
```

---

#### ❓ Question: Platform Fees Ratio Trend (6 Months)

Line chart — xu hướng tỷ lệ phí sàn (%) qua 6 tháng gần nhất. Alert nếu > 12%.

**Domain Reference**: [Platform Fees Ratio](../domains/finance.md#3-platform-fees-ratio-tỷ-lệ-phí-sàn--tổng-chi-phí)

```sql
SELECT
    date_trunc('month', CAST(CAST(fc.date_key AS VARCHAR) AS DATE)) AS "Thang",
    ROUND(
        SUM(CASE WHEN fc.cost_category = 'PLATFORM_FEE' THEN fc.amount ELSE 0 END) * 100.0
        / NULLIF(SUM(fc.amount), 0),
        1
    ) AS "Ty le phi san %"
FROM fact_order_costs fc
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) - INTERVAL '5 months' AS INTEGER)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Ty le phi san %"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Platform Fee Ratio (%)",
    "column_settings": {
      "Ty le phi san %": {
        "suffix": "%",
        "decimals": 1
      }
    },
    "graph.goal_value": 12,
    "graph.show_goal": true,
    "graph.goal_label": "Alert threshold (12%)"
  }
}
```

```json metabase-pos
{ "row": 5, "col": 12, "size_x": 6, "size_y": 7 }
```

---

#### ❓ Question: Top 20 Channels by Total Cost

Table — top 20 kênh theo tổng chi phí với % breakdown từng loại. Sort descending by total cost.

**Domain Reference**: [Top Channels by Total Cost](../domains/finance.md#6-top-channels-by-total-cost-kênh-tốn-nhiều-chi-phí-nhất)

```sql
SELECT
    COALESCE(c.channel_name, 'Unknown') AS "Kenh ban hang",
    COALESCE(SUM(fc.amount), 0)         AS "Tong chi phi",
    ROUND(SUM(CASE WHEN fc.cost_category = 'COGS'         THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS "COGS %",
    ROUND(SUM(CASE WHEN fc.cost_category = 'PLATFORM_FEE' THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS "Phi san %",
    ROUND(SUM(CASE WHEN fc.cost_category = 'DISCOUNT'     THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS "Chiet khau %",
    ROUND(SUM(CASE WHEN fc.cost_category = 'TAX'          THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS "Thue %",
    ROUND(SUM(CASE WHEN fc.cost_category = 'SHIPPING'     THEN fc.amount ELSE 0 END) * 100.0 / NULLIF(SUM(fc.amount), 0), 1) AS "Van chuyen %"
FROM fact_order_costs fc
LEFT JOIN dim_channels c ON fc.channel_key = c.channel_key
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
GROUP BY c.channel_name
ORDER BY "Tong chi phi" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Tong chi phi": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "COGS %":       { "suffix": "%", "decimals": 1 },
      "Phi san %":    { "suffix": "%", "decimals": 1 },
      "Chiet khau %": { "suffix": "%", "decimals": 1 },
      "Thue %":       { "suffix": "%", "decimals": 1 },
      "Van chuyen %": { "suffix": "%", "decimals": 1 }
    },
    "table.column_formatting": [
      {
        "columns": ["Phi san %"],
        "type": "single",
        "operator": ">",
        "value": 12,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 7 }
```

---

#### ❓ Question: Cost Breakdown Donut MTD

Donut — tổng chi phí tháng này phân theo cost_category.

```sql
SELECT
    CASE fc.cost_category
        WHEN 'COGS'         THEN 'Gia von (COGS)'
        WHEN 'PLATFORM_FEE' THEN 'Phi san'
        WHEN 'TAX'          THEN 'Thue'
        WHEN 'SHIPPING'     THEN 'Van chuyen'
        WHEN 'DISCOUNT'     THEN 'Chiet khau / Voucher'
        ELSE fc.cost_category
    END                         AS "Loai chi phi",
    COALESCE(SUM(fc.amount), 0) AS "So tien"
FROM fact_order_costs fc
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
GROUP BY fc.cost_category
ORDER BY "So tien" DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Loai chi phi",
    "pie.metric": "So tien",
    "pie.colors": {
      "Gia von (COGS)":      "#509EE3",
      "Phi san":              "#EF8C8C",
      "Thue":                 "#F9D45C",
      "Van chuyen":           "#A989C5",
      "Chiet khau / Voucher": "#F2A86F"
    },
    "pie.show_legend": true,
    "column_settings": {
      "So tien": {
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
{ "row": 19, "col": 0, "size_x": 6, "size_y": 6 }
```

---

#### ❓ Question: Cost by Channel Category — Stacked Bar

Horizontal stacked bar — tổng chi phí + breakdown theo cost_category cho từng kênh. Top 10 kênh theo tổng chi phí.

```sql
SELECT
    COALESCE(c.channel_name, 'Unknown') AS "Kenh ban hang",
    CASE fc.cost_category
        WHEN 'COGS'         THEN 'Gia von (COGS)'
        WHEN 'PLATFORM_FEE' THEN 'Phi san'
        WHEN 'TAX'          THEN 'Thue'
        WHEN 'SHIPPING'     THEN 'Van chuyen'
        WHEN 'DISCOUNT'     THEN 'Chiet khau / Voucher'
        ELSE fc.cost_category
    END                                 AS "Loai chi phi",
    COALESCE(SUM(fc.amount), 0)         AS "So tien"
FROM fact_order_costs fc
LEFT JOIN dim_channels c ON fc.channel_key = c.channel_key
JOIN fact_orders fo ON fc.order_id = fo.order_id
WHERE fo.status NOT IN ('CANCELLED', 'Voided')
  AND fo.is_sales_channel = true
  AND fc.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
  AND c.channel_name IN (
      SELECT COALESCE(c2.channel_name, 'Unknown')
      FROM fact_order_costs fc2
      LEFT JOIN dim_channels c2 ON fc2.channel_key = c2.channel_key
      JOIN fact_orders fo2 ON fc2.order_id = fo2.order_id
      WHERE fo2.status NOT IN ('CANCELLED', 'Voided') AND fo2.is_sales_channel = true
        AND fc2.date_key >= CAST(date_trunc('month', current_date) AS INTEGER)
      GROUP BY c2.channel_name
      ORDER BY SUM(fc2.amount) DESC
      LIMIT 10
  )
GROUP BY c.channel_name, fc.cost_category
ORDER BY SUM(fc.amount) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Kenh ban hang", "Loai chi phi"],
    "graph.metrics": ["So tien"],
    "stackable.stack_type": "stacked",
    "graph.x_axis.scale": "ordinal",
    "series_settings": {
      "Gia von (COGS)":       { "color": "#509EE3" },
      "Phi san":               { "color": "#EF8C8C" },
      "Thue":                  { "color": "#F9D45C" },
      "Van chuyen":            { "color": "#A989C5" },
      "Chiet khau / Voucher":  { "color": "#F2A86F" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "So tien": {
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
{ "row": 19, "col": 6, "size_x": 12, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_order_costs · **Cadence:** monthly · **Scope:** is_sales_channel=true · **Caveats:** Long-format cost ledger
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

