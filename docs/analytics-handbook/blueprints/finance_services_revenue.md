# 📘 Blueprint: Finance Services Revenue

**Playbook**: [Finance Services Revenue](../playbooks/finance_services_revenue.md)

> **Requires:** `is_service_line` flag in `int_misa_sales_lines` (P0 implementation — not yet deployed)
> **Target Collection:** `Finance`
> **Role:** CFO, Finance Manager
> **Archetype:** Operational Cockpit

---

```yaml
---
dashboard_name: Finance Services Revenue
collection: Finance
database: Sapo DuckDB
description: "Track services revenue (DV* + CPBH codes) separately from products P&L — 2.4B VND/năm"
audience: CFO, Finance Manager
cadence: Monthly
status: ACTIVE
requires_flag: is_service_line in int_misa_sales_lines
---
```

> **Database:** Sapo DuckDB

## 📂 Collection: Finance

Theo dõi doanh thu dịch vụ (DV* + CPBH) riêng biệt khỏi P&L hàng hóa — phục vụ CFO trong buổi MBR hàng tháng.

### 🖥️ Dashboard: Finance Services Revenue

**Description**: Dashboard doanh thu dịch vụ (DVCCNS US HR + các DV* codes) — hiển thị 2.4B VND/năm riêng biệt khỏi hàng hóa để CFO nắm rõ cơ cấu doanh thu.

---

### 📑 Tab: Tổng Quan

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' → ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Header

**Services Revenue Dashboard** — Doanh thu dịch vụ (DV* + CPBH) 2.4B VND/năm, hiển thị riêng biệt khỏi doanh thu hàng hóa. Nguồn: MISA `int_misa_sales_lines` WHERE `is_service_line = true`.

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 2 }
```

#### ❓ Question: Doanh Thu Dịch Vụ MTD

**Domain Reference**: [S1. Services Revenue](../domains/finance.md#s1-services-revenue)

Hero metric — doanh thu dịch vụ tháng này vs tháng trước vs cùng kỳ năm ngoái.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE is_service_line = true
      AND posting_date >= date_trunc('month', current_date)
      AND posting_date <  current_date + INTERVAL '1 day'
),
prev_month AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE is_service_line = true
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND posting_date <  date_trunc('month', current_date)
),
prev_year AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE is_service_line = true
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND posting_date <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    t.val                                                                   AS "Doanh thu DV tháng này",
    p.val                                                                   AS "Tháng trước",
    py.val                                                                  AS "Cùng kỳ năm ngoái",
    ROUND((t.val - p.val)  * 100.0 / NULLIF(p.val,  0), 1)                 AS "MoM %",
    ROUND((t.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)                 AS "YoY %"
FROM this_month t, prev_month p, prev_year py
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu DV tháng này": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Tháng trước":            { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Cùng kỳ năm ngoái":     { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "MoM %":                  { "suffix": "%", "decimals": 1 },
      "YoY %":                  { "suffix": "%", "decimals": 1 }
    },
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["MoM %"], "type": "single", "operator": ">=", "value":  5, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["MoM %"], "type": "single", "operator": "<",  "value": -5, "color": "#EF8C8C", "highlight_row": false },
      { "columns": ["YoY %"], "type": "single", "operator": ">=", "value": 10, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["YoY %"], "type": "single", "operator": "<",  "value":-10, "color": "#EF8C8C", "highlight_row": false }
    ]
  }
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 14, "size_y": 4 }
```

#### ❓ Question: Dịch Vụ Active (Số lượng)

Supporting scalar — số service codes có giao dịch trong tháng này.

```sql
SELECT COUNT(DISTINCT product_code) AS "Dịch vụ đang hoạt động"
FROM int_misa_sales_lines
WHERE is_service_line = true
  AND posting_date >= date_trunc('month', current_date)
  AND posting_date <  current_date + INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Dịch vụ hoạt động tháng này"
  }
}
```

```json metabase-pos
{ "row": 4, "col": 14, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Dịch Vụ YTD

Supporting metric — doanh thu dịch vụ lũy kế từ đầu năm.

```sql
SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS "Doanh thu DV YTD"
FROM int_misa_sales_lines
WHERE is_service_line = true
  AND posting_date >= date_trunc('year', current_date)
  AND posting_date <  current_date + INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "card.title": "Doanh thu dịch vụ YTD",
    "column_settings": {
      "Doanh thu DV YTD": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Dịch Vụ % Tổng Doanh Thu

**Domain Reference**: [S2. Services as % of Total Revenue](../domains/finance.md#s2-services-as--of-total-revenue)

Gauge — tỷ lệ doanh thu dịch vụ / tổng doanh thu (DV + hàng hóa). Đo mức độ đóng góp.

```sql
WITH
services AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE is_service_line = true
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND posting_date <  date_trunc('month', current_date)
),
total AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE posting_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND posting_date <  date_trunc('month', current_date)
)
SELECT
    ROUND(s.val * 100.0 / NULLIF(t.val, 0), 1) AS "DV % Tổng DT (tháng trước)"
FROM services s, total t
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,  "max": 5,   "color": "#F9D45C", "label": "Thấp" },
      { "min": 5,  "max": 15,  "color": "#84BB4C", "label": "Bình thường" },
      { "min": 15, "max": 100, "color": "#509EE3", "label": "Cao" }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 6, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Xu Hướng Doanh Thu Dịch Vụ 12 Tháng

**Domain Reference**: [S1. Services Revenue](../domains/finance.md#s1-services-revenue)

Line chart — doanh thu dịch vụ theo tháng 12 tháng gần nhất. Phát hiện sụt giảm hoặc tăng đột biến.

```sql
SELECT
    date_trunc('month', posting_date) AS "Tháng",
    COALESCE(SUM(revenue_net_of_discount), 0) AS "Doanh thu dịch vụ"
FROM int_misa_sales_lines
WHERE is_service_line = true
  AND posting_date >= current_date - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Tháng"],
    "graph.metrics": ["Doanh thu dịch vụ"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Doanh thu dịch vụ": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Phân Bổ Doanh Thu Theo Loại Dịch Vụ

**Domain Reference**: [S3. Service Type Breakdown](../domains/finance.md#s3-service-type-breakdown)

Pie chart — tỷ lệ doanh thu từng service code trong tháng gần nhất (tháng trước).

```sql
SELECT
    product_code                                 AS "Mã dịch vụ",
    product_name                                 AS "Tên dịch vụ",
    COALESCE(SUM(revenue_net_of_discount), 0)   AS "Doanh thu"
FROM int_misa_sales_lines
WHERE is_service_line = true
  AND posting_date >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND posting_date <  date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Mã dịch vụ",
    "pie.metric": "Doanh thu",
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 5 Dịch Vụ Tháng Này

Table — top 5 service codes theo doanh thu MTD + MoM delta. CFO scan nhanh.

```sql
WITH
this_month AS (
    SELECT
        product_code,
        product_name,
        COALESCE(SUM(revenue_net_of_discount), 0) AS rev_this
    FROM int_misa_sales_lines
    WHERE is_service_line = true
      AND posting_date >= date_trunc('month', current_date)
      AND posting_date <  current_date + INTERVAL '1 day'
    GROUP BY 1, 2
),
prev_month AS (
    SELECT
        product_code,
        COALESCE(SUM(revenue_net_of_discount), 0) AS rev_prev
    FROM int_misa_sales_lines
    WHERE is_service_line = true
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND posting_date <  date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    t.product_code                                                           AS "Mã",
    t.product_name                                                           AS "Tên dịch vụ",
    t.rev_this                                                               AS "Tháng này",
    COALESCE(p.rev_prev, 0)                                                  AS "Tháng trước",
    ROUND((t.rev_this - COALESCE(p.rev_prev, 0)) * 100.0
          / NULLIF(COALESCE(p.rev_prev, 0), 0), 1)                          AS "MoM %"
FROM this_month t
LEFT JOIN prev_month p USING (product_code)
ORDER BY t.rev_this DESC
LIMIT 5
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Tháng này":    { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Tháng trước":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "MoM %":        { "suffix": "%", "decimals": 1 }
    },
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["MoM %"], "type": "single", "operator": ">=", "value":  5, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["MoM %"], "type": "single", "operator": "<",  "value": -5, "color": "#EF8C8C", "highlight_row": false }
    ]
  }
}
```

```json metabase-pos
{ "row": 14, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Nguồn:** `int_misa_sales_lines` WHERE `is_service_line = true` · **Cadence:** Monthly · **Caveats:** Dịch vụ không có COGS → không so sánh margin với hàng hóa · **Requires P0:** `is_service_line` flag

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: US HR Services

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' → ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: US HR Note

**US HR Services (DVCCNS + DVCCNS1)** — Phí dịch vụ cung cấp nhân sự cho đối tác Mỹ (FGO). Recurring contract revenue, **không có COGS** — 100% contribution margin. DVCCNS1 = biến thể mới từ 2024+, cùng tính chất với DVCCNS. Không so sánh margin % với hàng hóa.

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 2 }
```

#### ❓ Question: US HR Revenue MTD (DVCCNS + DVCCNS1)

Hero metric — tổng DVCCNS + DVCCNS1 tháng này vs tháng trước vs cùng kỳ năm ngoái.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE product_code IN ('DVCCNS', 'DVCCNS1')
      AND posting_date >= date_trunc('month', current_date)
      AND posting_date <  current_date + INTERVAL '1 day'
),
prev_month AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE product_code IN ('DVCCNS', 'DVCCNS1')
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND posting_date <  date_trunc('month', current_date)
),
prev_year AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE product_code IN ('DVCCNS', 'DVCCNS1')
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND posting_date <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    t.val                                                                   AS "US HR Revenue tháng này",
    p.val                                                                   AS "Tháng trước",
    py.val                                                                  AS "Cùng kỳ năm ngoái",
    ROUND((t.val - p.val)  * 100.0 / NULLIF(p.val,  0), 1)                 AS "MoM %",
    ROUND((t.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)                 AS "YoY %"
FROM this_month t, prev_month p, prev_year py
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "US HR Revenue tháng này": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Tháng trước":             { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Cùng kỳ năm ngoái":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "MoM %":                   { "suffix": "%", "decimals": 1 },
      "YoY %":                   { "suffix": "%", "decimals": 1 }
    },
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["MoM %"], "type": "single", "operator": ">=", "value":  5, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["MoM %"], "type": "single", "operator": "<",  "value": -5, "color": "#EF8C8C", "highlight_row": false },
      { "columns": ["YoY %"], "type": "single", "operator": ">=", "value": 10, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["YoY %"], "type": "single", "operator": "<",  "value":-10, "color": "#EF8C8C", "highlight_row": false }
    ]
  }
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 4 }
```

#### ❓ Question: Xu Hướng DVCCNS + DVCCNS1 — 24 Tháng

Multi-line — DVCCNS vs DVCCNS1 theo tháng trong 24 tháng. Thấy rõ shift từ DVCCNS sang DVCCNS1.

```sql
SELECT
    date_trunc('month', posting_date)          AS "Tháng",
    product_code                               AS "Mã dịch vụ",
    COALESCE(SUM(revenue_net_of_discount), 0)  AS "Doanh thu"
FROM int_misa_sales_lines
WHERE product_code IN ('DVCCNS', 'DVCCNS1')
  AND posting_date >= current_date - INTERVAL '24 months'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Tháng", "Mã dịch vụ"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3", "#88BDE6"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: DVCCNS vs DVCCNS1 — Breakdown

Table — số dòng, doanh thu, ngày xuất hóa đơn cuối cùng per code. Giúp CFO confirm contract đang active.

```sql
SELECT
    product_code                                        AS "Mã dịch vụ",
    product_name                                        AS "Tên",
    COUNT(*)                                            AS "Số dòng (12M)",
    COALESCE(SUM(revenue_net_of_discount), 0)           AS "Doanh thu 12M",
    MAX(posting_date)                                   AS "Hóa đơn cuối"
FROM int_misa_sales_lines
WHERE product_code IN ('DVCCNS', 'DVCCNS1')
  AND posting_date >= current_date - INTERVAL '12 months'
GROUP BY 1, 2
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu 12M": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    },
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Nguồn:** `int_misa_sales_lines` WHERE `product_code IN ('DVCCNS','DVCCNS1')` · **Cadence:** Monthly · **Caveats:** Revenue = 100% contribution margin (zero COGS) — không dùng gross margin % · **Requires P0:** `is_service_line` flag

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: Kiểm Tra Dịch Vụ Khác

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' → ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS " "
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### ❓ Question: Danh Sách Dịch Vụ Active/Inactive

**Domain Reference**: [S3. Service Type Breakdown](../domains/finance.md#s3-service-type-breakdown)

Table — tất cả service codes, last invoice date, tổng 12M revenue, trạng thái. Compliance check.

```sql
SELECT
    product_code                                        AS "Mã",
    product_name                                        AS "Tên dịch vụ",
    MAX(posting_date)                                   AS "Hóa đơn cuối",
    COALESCE(SUM(CASE WHEN posting_date >= current_date - INTERVAL '12 months'
                      THEN revenue_net_of_discount END), 0) AS "Doanh thu 12M",
    CASE
        WHEN MAX(posting_date) >= current_date - INTERVAL '3 months'  THEN 'ACTIVE'
        WHEN MAX(posting_date) >= current_date - INTERVAL '12 months' THEN 'Low Activity'
        ELSE 'DISCONTINUED'
    END                                                 AS "Trạng thái"
FROM int_misa_sales_lines
WHERE is_service_line = true
GROUP BY 1, 2
ORDER BY MAX(posting_date) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu 12M": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    },
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["Trạng thái"], "type": "single", "operator": "=", "value": "ACTIVE",       "color": "#84BB4C", "highlight_row": false },
      { "columns": ["Trạng thái"], "type": "single", "operator": "=", "value": "DISCONTINUED", "color": "#EF8C8C", "highlight_row": false }
    ]
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 12, "size_y": 7 }
```

#### 📝 Text: Dịch Vụ Ngừng Hoạt Động

**Dịch vụ đã ngừng (2022):** DVRENTAL · DVDIEN · DVGX · DVQL · DVNUOC · DVVS (văn phòng/tiện ích — 788M tổng) · DVDT1 (thiết bị phóng cao áp — 1.29B one-off). Các mã này không còn phát sinh từ cuối 2022. Nếu tái xuất hiện → cần xác nhận với kế toán.

```json metabase-pos
{ "row": 2, "col": 12, "size_x": 6, "size_y": 7 }
```

#### ❓ Question: Điều Chỉnh CPBH Theo Tháng

Table — các dòng CPBH (chi phí bán hàng âm — điều chỉnh refund) theo tháng. Tăng đột biến = investigate.

```sql
SELECT
    date_trunc('month', posting_date)          AS "Tháng",
    COUNT(*)                                   AS "Số dòng",
    COALESCE(SUM(revenue_net_of_discount), 0)  AS "Điều chỉnh CPBH (VND)"
FROM int_misa_sales_lines
WHERE product_code LIKE 'CPBH%'
  AND posting_date >= current_date - INTERVAL '24 months'
GROUP BY 1
ORDER BY 1 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Điều chỉnh CPBH (VND)": { "number_style": "currency", "currency": "VND", "decimals": 0 }
    },
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["Điều chỉnh CPBH (VND)"], "type": "single", "operator": "<", "value": -100000000, "color": "#EF8C8C", "highlight_row": true }
    ]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 9, "size_y": 5 }
```

#### 📝 Text: Action Triggers

**Ngưỡng cần xem xét:**
- CPBH tháng > -100M VND → tìm nguyên nhân điều chỉnh, báo CFO
- Bất kỳ DV* discontinued tái xuất hiện → xác nhận với kế toán
- DVVC (vận chuyển) tháng > 10M VND → verify có hợp đồng mới không?

```json metabase-pos
{ "row": 9, "col": 9, "size_x": 9, "size_y": 5 }
```

#### 📝 Text: Source & Freshness

**Nguồn:** `int_misa_sales_lines` WHERE `is_service_line = true` · **Cadence:** Monthly · **Scope:** Tất cả DV* + CPBH codes · **Requires P0:** `is_service_line` flag

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```
