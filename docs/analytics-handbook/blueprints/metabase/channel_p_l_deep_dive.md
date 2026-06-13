---
primary_scope: scope_sales
scope_indicator: "[Cross]"
layer: L3
uses_concepts: [scope_sales, filter_has_cogs, net_revenue, gross_profit, channel_net_profit, cogs_amount, platform_fees]
---

# 📘 Blueprint: Channel P&L Deep Dive [Cross]

> **Target Collection:** `Phân tích của chúng tôi > Finance`
> **Captured from:** Metabase Dashboard ID 77
> **Captured at:** 2026-06-13

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md)
> **Scope:** `scope_sales` + `filter_has_cogs` · Layer L3 `[Cross]`
> **Concepts:** `scope_sales` · `filter_has_cogs` · `net_revenue` · `gross_profit` · `channel_net_profit` · `cogs_amount`
> **Why:** Channel P&L covers all sales channels to identify which channels are unprofitable after platform fees.

## 📂 Collection: Finance

Audience: Finance/Sales Director. Scope: Cross-segment, all channels. Câu hỏi: Channel nào lỗ sau khi trừ phí platform?

---

### 🖥️ Dashboard: Channel P&L Deep Dive [Cross]

**Description**: Audience: Finance/Sales Director. Scope: Cross-segment, all channels. Câu hỏi: Channel nào lỗ sau khi trừ phí platform?

#### Filter: Period


```json metabase-filter
{
  "name": "Period",
  "slug": "date_range",
  "type": "date/all-options",
  "default": "thismonth"
}
```

#### Filter: Channel


```json metabase-filter
{
  "name": "Channel",
  "slug": "channel",
  "type": "string/=",
  "default": null
}
```

---

### 📑 Tab: P&L Waterfall

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics
    WHERE has_cogs AND scope_sales
      [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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

#### 📝 Text: Dòng tiền P&L kênh — từ doanh thu gộp đến lợi nhuận ròng sau phí platform


Dòng tiền P&L kênh — từ doanh thu gộp đến lợi nhuận ròng sau phí platform

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: P&L Waterfall — All Channels

```sql
SELECT "Khoan muc", COALESCE("Gia tri", 0) AS "Gia tri"
FROM (
    VALUES
        ('Doanh thu gop',
            (SELECT SUM(gross_revenue)
             FROM fact_order_economics
             WHERE has_cogs AND scope_sales AND is_active_order
               [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
            )
        ),
        ('Chiet khau',
            (SELECT -SUM(ABS(discount_amount))
             FROM fact_order_economics
             WHERE has_cogs AND scope_sales AND is_active_order
               [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
            )
        ),
        ('Doanh thu thuan',
            (SELECT SUM(net_revenue)
             FROM fact_order_economics
             WHERE has_cogs AND scope_sales AND is_active_order
               [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
            )
        ),
        ('Gia von COGS',
            (SELECT -SUM(COALESCE(cogs_amount, 0))
             FROM fact_order_economics
             WHERE has_cogs AND scope_sales AND is_active_order
               [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
            )
        ),
        ('Phi platform',
            (SELECT SUM(
                 COALESCE(shopee_platform_fees,   0)
               + COALESCE(shopee_infra_fee,        0)
               + COALESCE(shopee_voucher_xtra_fee, 0)
               + COALESCE(shopee_taxes,            0)
             )
             FROM fact_order_economics
             WHERE has_cogs AND scope_sales AND is_active_order
               [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
            )
        ),
        ('Loi nhuan rong',
            (SELECT SUM(channel_net_profit)
             FROM fact_order_economics
             WHERE has_cogs AND scope_sales AND is_active_order
               [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
            )
        )
) AS t("Khoan muc", "Gia tri")
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": [
      "Khoan muc"
    ],
    "waterfall.increase_color": "#84BB4C",
    "waterfall.decrease_color": "#EF8C8C",
    "waterfall.total_color": "#509EE3",
    "column_settings": {
      "[\"name\",\"Gia tri\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Gia tri"
    ]
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 18,
  "size_y": 7
}
```

---

#### 📝 Text: **Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric


**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Channel Scorecard

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics
    WHERE has_cogs AND scope_sales
      [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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

#### 📝 Text: Bảng điểm kênh — Net Revenue, Gross Margin, Net Margin, Khối lượng đơn, Phí platform


Bảng điểm kênh — Net Revenue, Gross Margin, Net Margin, Khối lượng đơn, Phí platform

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Channel Scorecard Table

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics e
    WHERE e.has_cogs AND e.scope_sales
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),

actuals AS (
    SELECT
        c.channel_key,
        c.channel_name,
        COUNT(*)                                                                              AS order_count,
        COALESCE(SUM(e.net_revenue), 0)                                                       AS net_revenue,
        ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)                AS gross_margin_pct,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)          AS net_margin_pct,
        COALESCE(
            SUM(
                ABS(COALESCE(e.shopee_platform_fees, 0))
              + ABS(COALESCE(e.shopee_infra_fee, 0))
              + ABS(COALESCE(e.shopee_voucher_xtra_fee, 0))
            ),
            0
        )                                                                                     AS platform_fees
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key)
    WHERE e.has_cogs
      AND e.scope_sales
      AND e.is_active_order
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
    GROUP BY c.channel_key, c.channel_name
),

targets AS (
    SELECT
        t.channel_key,
        t.target_value AS target_margin_pct
    FROM dim_channel_targets t, filter_bounds
    WHERE t.metric_type = 'NET_MARGIN_PCT'
      AND t.target_source = 'BUDGET'
      AND t.period_month = date_trunc('month', filter_bounds.p_start)
)

SELECT
    a.channel_name                                                    AS "Kenh",
    a.order_count                                                     AS "So don",
    a.net_revenue                                                     AS "Net Revenue",
    a.gross_margin_pct                                                AS "Gross Margin %",
    a.net_margin_pct                                                  AS "Net Margin %",
    t.target_margin_pct                                               AS "Target %",
    ROUND(COALESCE(a.net_margin_pct, 0) - COALESCE(t.target_margin_pct, 0), 1) AS "Variance pp",
    a.platform_fees                                                   AS "Platform Fees"
FROM actuals a
LEFT JOIN targets t USING (channel_key)
ORDER BY a.net_margin_pct ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": [
          "Net Margin %"
        ],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": [
          "Net Margin %"
        ],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": [
          "Variance pp"
        ],
        "type": "single",
        "operator": "<",
        "value": -3,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Platform Fees\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Target %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Variance pp\"]": {
        "number_style": "decimal",
        "decimals": 1
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

#### 📝 Text: **Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric


**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Margin Heatmap

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics
    WHERE has_cogs AND scope_sales
      [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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

#### 📝 Text: Heatmap Net Margin % — kênh × tháng. Màu đỏ = lỗ, xanh = lãi tốt.


Heatmap Net Margin % — kênh × tháng. Màu đỏ = lỗ, xanh = lãi tốt.

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Net Margin Heatmap — Channel × Month

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics e
    WHERE e.has_cogs AND e.scope_sales
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
)
SELECT
    c.channel_name                                                                AS "Kenh",
    date_trunc('month', strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE)               AS "Thang",
    ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS "Net Margin %"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key), filter_bounds
WHERE e.has_cogs
  AND e.scope_sales
  AND e.is_active_order
  AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE >= filter_bounds.p_start
  AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE <= filter_bounds.p_end
  [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
GROUP BY c.channel_name,
         date_trunc('month', strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE)
ORDER BY "Thang", "Kenh"
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "pivot_table.column_split": {
      "rows": [
        "Kenh"
      ],
      "columns": [
        "Thang"
      ],
      "values": [
        "Net Margin %"
      ]
    },
    "table.column_formatting": [
      {
        "columns": [
          "Net Margin %"
        ],
        "type": "range",
        "colors": [
          "#EF8C8C",
          "#F9D45C",
          "#84BB4C"
        ],
        "min_type": "custom",
        "min_value": -20,
        "max_type": "custom",
        "max_value": 40
      }
    ],
    "column_settings": {
      "[\"name\",\"Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
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

#### 📝 Text: **Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric


**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Variance Analysis

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics
    WHERE has_cogs AND scope_sales
      [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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

#### 📝 Text: Biến động kênh — Net Revenue và Net Margin % so với kỳ trước (MoM)


Biến động kênh — Net Revenue và Net Margin % so với kỳ trước (MoM)

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Channel MoM Variance Table

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics e
    WHERE e.has_cogs AND e.scope_sales
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
cur AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)                                                           AS rev_cur,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS margin_cur
    FROM fact_order_economics e, filter_bounds
    WHERE e.has_cogs
      AND e.scope_sales
      AND e.is_active_order
      AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE >= filter_bounds.p_start
      AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE <= filter_bounds.p_end
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
    GROUP BY e.channel_key
),
prior AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)                                                           AS rev_prior,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS margin_prior
    FROM fact_order_economics e, filter_bounds
    WHERE e.has_cogs
      AND e.scope_sales
      AND e.is_active_order
      AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE <  filter_bounds.p_start
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
    GROUP BY e.channel_key
)
SELECT
    c.channel_name                                                                    AS "Kenh",
    COALESCE(cur.rev_cur, 0)                                                          AS "Rev Ky Nay",
    COALESCE(prior.rev_prior, 0)                                                      AS "Rev Ky Truoc",
    CASE
        WHEN COALESCE(prior.rev_prior, 0) = 0 THEN NULL
        ELSE ROUND((COALESCE(cur.rev_cur, 0) - prior.rev_prior) * 100.0 / prior.rev_prior, 1)
    END                                                                               AS "Delta Rev %",
    cur.margin_cur                                                                    AS "Margin Ky Nay %",
    prior.margin_prior                                                                AS "Margin Ky Truoc %",
    ROUND(COALESCE(cur.margin_cur, 0) - COALESCE(prior.margin_prior, 0), 1)           AS "Delta Margin pp"
FROM cur
LEFT JOIN prior USING (channel_key)
JOIN dim_channels c USING (channel_key)
ORDER BY "Delta Margin pp" ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": [
          "Delta Margin pp"
        ],
        "type": "single",
        "operator": "<",
        "value": -5,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": [
          "Delta Margin pp"
        ],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Rev Ky Nay\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Rev Ky Truoc\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Delta Rev %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Margin Ky Nay %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Margin Ky Truoc %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Delta Margin pp\"]": {
        "number_style": "decimal",
        "decimals": 1
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

#### ❓ Question: Net Margin Trend by Channel (with Budget Target)

```sql
-- Actual net margin per channel per month
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics e
    WHERE e.has_cogs AND e.scope_sales
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
actuals AS (
    SELECT
        c.channel_name                                                                AS channel_name,
        date_trunc('month', strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE)               AS period_month,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS net_margin_pct
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key), filter_bounds
    WHERE e.has_cogs
      AND e.scope_sales
      AND e.is_active_order
      AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE >= filter_bounds.p_start
      AND strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE <= filter_bounds.p_end
      [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
    GROUP BY c.channel_name,
             date_trunc('month', strptime(CAST(e.date_key AS VARCHAR), '%Y%m%d')::DATE)
),

-- Budget targets for the same window
budget AS (
    SELECT
        t.channel_name,
        t.period_month,
        t.target_value AS target_margin_pct
    FROM dim_channel_targets t, filter_bounds
    WHERE t.metric_type = 'NET_MARGIN_PCT'
      AND t.target_source = 'BUDGET'
      AND t.period_month >= date_trunc('month', filter_bounds.p_start)
      AND t.period_month <= date_trunc('month', filter_bounds.p_end)
)

SELECT
    a.channel_name              AS "Kenh",
    a.period_month              AS "Thang",
    a.net_margin_pct            AS "Net Margin %",
    b.target_margin_pct         AS "Budget Target %"
FROM actuals a
LEFT JOIN budget b USING (channel_name, period_month)
ORDER BY "Thang", "Kenh"
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": [
      "Thang",
      "Kenh"
    ],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Net Margin (%)",
    "graph.colors": [
      "#509EE3",
      "#88BDE6",
      "#A989C5",
      "#F2A86F",
      "#F9D45C"
    ],
    "series_settings": {
      "Budget Target %": {
        "line.style": "dashed",
        "color": "#EF8C8C",
        "show_series_values": false
      }
    },
    "column_settings": {
      "[\"name\",\"Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Budget Target %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    },
    "graph.metrics": [
      "Net Margin %",
      "Budget Target %"
    ]
  }
}
```

```json metabase-pos
{
  "row": 11,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric


**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Loss-Leader Alert

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_start,
           MAX(strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS p_end
    FROM fact_order_economics
    WHERE has_cogs AND scope_sales
      [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
      [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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

#### 📝 Text: Cảnh báo loss-leader — kênh có Net Margin % âm sau khi trừ phí platform


Cảnh báo loss-leader — kênh có Net Margin % âm sau khi trừ phí platform

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### ❓ Question: Loss Leader Channel Count

```sql
SELECT COUNT(*) AS "So kenh lo"
FROM (
    SELECT
        e.channel_key,
        SUM(e.channel_net_profit) AS total_net_profit
    FROM fact_order_economics e
    WHERE e.has_cogs
      AND e.scope_sales
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
    GROUP BY e.channel_key
    HAVING SUM(e.channel_net_profit) < 0
) loss_channels
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"So kenh lo\"]": {
        "number_style": "decimal",
        "decimals": 0
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Total Loss Exposure

```sql
SELECT COALESCE(SUM(net_loss), 0) AS "Tong lo"
FROM (
    SELECT
        e.channel_key,
        SUM(e.channel_net_profit) AS net_loss
    FROM fact_order_economics e
    WHERE e.has_cogs
      AND e.scope_sales
      AND e.is_active_order
      [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
    GROUP BY e.channel_key
    HAVING SUM(e.channel_net_profit) < 0
) loss_channels
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Tong lo\"]": {
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
  "row": 3,
  "col": 4,
  "size_x": 6,
  "size_y": 3
}
```

---

#### ❓ Question: Loss Leader Detail Table

```sql
SELECT
    c.channel_name                                                                        AS "Kenh",
    COALESCE(SUM(e.net_revenue), 0)                                                       AS "Net Revenue",
    COALESCE(SUM(e.gross_profit), 0)                                                      AS "Gross Profit",
    COALESCE(SUM(e.channel_net_profit), 0)                                                AS "Net Profit",
    ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)          AS "Net Margin %",
    COALESCE(
        SUM(
            ABS(COALESCE(e.shopee_platform_fees, 0))
          + ABS(COALESCE(e.shopee_infra_fee, 0))
          + ABS(COALESCE(e.shopee_voucher_xtra_fee, 0))
          + ABS(COALESCE(e.shopee_taxes, 0))
        ),
        0
    )                                                                                     AS "Platform Fees",
    COUNT(*)                                                                              AS "So don"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key)
WHERE e.has_cogs
  AND e.scope_sales
  AND e.is_active_order
  [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
GROUP BY c.channel_name
HAVING SUM(e.channel_net_profit) < 0
ORDER BY "Net Margin %" ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": [
          "Net Margin %"
        ],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Profit\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Net Profit\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Platform Fees\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```

---

#### 📝 Text: **Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric


**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Core vs Marketplace

#### 📝 Text: Core vs Marketplace — split doanh thu và biên lợi nhuận theo nhóm kênh (Core = tất cả trừ Marketplace + CrossBorder Fulfillment)

Core vs Marketplace — split doanh thu và biên lợi nhuận theo nhóm kênh. **Core** = tất cả kênh trừ Marketplace (Shopee, Lazada, Tiki, TikTok Shop, CrossBorder Fulfillment). Nguồn: `dim_channels.is_marketplace`.

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### ❓ Question: Core vs Marketplace — Revenue & Margin Summary

```sql
SELECT
    CASE WHEN dc.is_marketplace THEN 'Marketplace' ELSE 'Core' END AS "Nhom kenh",
    SUM(e.net_revenue)                                              AS "Net Revenue",
    ROUND(SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)         AS "Gross Margin %",
    ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1)   AS "Net Margin %",
    COUNT(*)                                                        AS "So don"
FROM main_marts.fact_order_economics e
JOIN main_marts.dim_channels dc USING (channel_key)
WHERE e.has_cogs
  AND e.scope_sales
  AND e.is_active_order
  [[AND e.date_key IN (SELECT date_key FROM main_marts.dim_date WHERE {{date_range}})]]
  [[AND e.channel_key IN (SELECT channel_key FROM main_marts.dim_channels WHERE {{channel}})]]
GROUP BY 1
ORDER BY "Net Revenue" DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Net Margin %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Net Margin %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 5
}
```

---

#### ❓ Question: Core vs Marketplace — Revenue Bar

```sql
SELECT
    CASE WHEN dc.is_marketplace THEN 'Marketplace' ELSE 'Core' END AS "Nhom kenh",
    SUM(e.net_revenue)                                              AS "Net Revenue"
FROM main_marts.fact_order_economics e
JOIN main_marts.dim_channels dc USING (channel_key)
WHERE e.has_cogs
  AND e.scope_sales
  AND e.is_active_order
  [[AND e.date_key IN (SELECT date_key FROM main_marts.dim_date WHERE {{date_range}})]]
  [[AND e.channel_key IN (SELECT channel_key FROM main_marts.dim_channels WHERE {{channel}})]]
GROUP BY 1
ORDER BY "Net Revenue" DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Nhom kenh"],
    "graph.metrics": ["Net Revenue"],
    "graph.colors": ["#509EE3", "#A989C5"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Net Revenue (VND)",
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
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
  "row": 7,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

---

#### ❓ Question: Core vs Marketplace — Net Margin % Bar

```sql
SELECT
    CASE WHEN dc.is_marketplace THEN 'Marketplace' ELSE 'Core' END AS "Nhom kenh",
    ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS "Net Margin %"
FROM main_marts.fact_order_economics e
JOIN main_marts.dim_channels dc USING (channel_key)
WHERE e.has_cogs
  AND e.scope_sales
  AND e.is_active_order
  [[AND e.date_key IN (SELECT date_key FROM main_marts.dim_date WHERE {{date_range}})]]
  [[AND e.channel_key IN (SELECT channel_key FROM main_marts.dim_channels WHERE {{channel}})]]
GROUP BY 1
ORDER BY "Net Margin %" DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Nhom kenh"],
    "graph.metrics": ["Net Margin %"],
    "graph.colors": ["#84BB4C", "#F2A86F"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Net Margin (%)",
    "column_settings": {
      "[\"name\",\"Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_order_economics JOIN dim_channels · **Split:** dim_channels.is_marketplace · **Scope:** has_cogs + scope_sales + is_active_order

**Source:** fact_order_economics JOIN dim_channels · **Split:** `dim_channels.is_marketplace` (TRUE = Shopee/Lazada/Tiki/TikTok/CrossBorder Fulfillment) · **Scope:** has_cogs + scope_sales + is_active_order

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---
