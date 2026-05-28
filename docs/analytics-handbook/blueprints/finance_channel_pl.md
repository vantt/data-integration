# Blueprint: Channel P&L Deep Dive [Cross]

**Playbook**: [Channel P&L Deep Dive](../playbooks/finance_channel_pl.md)

> **Database:** `Sapo`
> **Target Collection:** `Finance`
> **Collection ID:** 92
> **Audience:** Finance Director, Sales Director
> **Scope:** Cross-segment, all sales channels (is_sales_channel = true)
> **Description:** Audience: Finance/Sales Director. Scope: Cross-segment, all channels. Câu hỏi: Channel nào lỗ sau khi trừ phí platform?
> **Domain:** [Channel P&L Waterfall & Loss-Leader Detection](../domains/finance.md#context-channel-pl-waterfall--loss-leader-detection)
> **Mart source:** `fact_order_economics` + `int_misa_sales_lines` (2026-05-27)
> **Target source:** `dim_channel_targets` seed CSV (manually maintained; `dbt seed --select dim_channel_targets` to refresh)

Dashboard phân tích lợi nhuận theo kênh bán hàng — waterfall từ doanh thu gộp đến lợi nhuận ròng sau phí platform, bảng điểm kênh, heatmap margin theo tháng, bảng biến động so kỳ trước, và cảnh báo loss-leader. Dành cho Finance Director và Sales Director trong MBR hàng tháng.

## 📂 Collection: Finance

### 🖥️ Dashboard: Channel P&L Deep Dive [Cross]

**Description**: Audience: Finance/Sales Director. Scope: Cross-segment, all channels. Câu hỏi: Channel nào lỗ sau khi trừ phí platform?

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "thismonth"
}
```

#### Filter: Channel

```json metabase-filter
{
  "slug": "channel",
  "type": "string/="
}
```

---

### 📑 Tab: P&L Waterfall

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


#### 📝 Text: Waterfall Heading

Dòng tiền P&L kênh — từ doanh thu gộp đến lợi nhuận ròng sau phí platform

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: P&L Waterfall — All Channels

Waterfall toàn kênh: Gross Revenue → Chiết khấu → Net Revenue → COGS → Platform Fees → Net Profit. Chỉ bao gồm đơn có COGS từ MISA (has_cogs = true).

**Domain Reference**: [CPL4 — Waterfall Components](../domains/finance.md#cpl4-waterfall-components-thành-phần-thác-nước-pl)

```sql
SELECT "Khoan muc", COALESCE("Gia tri", 0) AS "Gia tri"
FROM (
    VALUES
        ('Doanh thu gop',
            (SELECT SUM(gross_revenue)
             FROM fact_order_economics
             WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')
               [[AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
            )
        ),
        ('Chiet khau',
            (SELECT -SUM(ABS(discount_amount))
             FROM fact_order_economics
             WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')
               [[AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
            )
        ),
        ('Doanh thu thuan',
            (SELECT SUM(net_revenue)
             FROM fact_order_economics
             WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')
               [[AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
            )
        ),
        ('Gia von COGS',
            (SELECT -SUM(COALESCE(cogs_amount, 0))
             FROM fact_order_economics
             WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')
               [[AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
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
             WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')
               [[AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
            )
        ),
        ('Loi nhuan rong',
            (SELECT SUM(channel_net_profit)
             FROM fact_order_economics
             WHERE has_cogs AND status NOT IN ('CANCELLED','Voided')
               [[AND CAST(CAST(date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
               [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
            )
        )
) AS t("Khoan muc", "Gia tri")
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": ["Khoan muc"],
    "graph.metrics": ["Gia tri"],
    "waterfall.increase_color": "#84BB4C",
    "waterfall.decrease_color": "#EF8C8C",
    "waterfall.total_color": "#509EE3",
    "column_settings": {
      "Gia tri": {
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
{"row": 3, "col":0, "size_x":18, "size_y":7}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Channel Scorecard

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


#### 📝 Text: Scorecard Heading

Bảng điểm kênh — Net Revenue, Gross Margin, Net Margin, Khối lượng đơn, Phí platform

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Channel Scorecard Table

Một dòng/kênh: Net Revenue, Gross Margin %, Net Margin %, Target %, Variance pp, Số đơn, Platform Fees. Target kéo từ dim_channel_targets (metric_type='NET_MARGIN_PCT', tháng hiện tại). Sắp xếp Net Margin % tăng dần (kênh lỗ nhất lên đầu). Conditional formatting: Net Margin % < 0 = đỏ, ≥ 20% = xanh; Variance pp < -3 = đỏ nhạt.

**Domain Reference**: [CPL5 — Channel Scorecard](../domains/finance.md#cpl5-channel-scorecard-bảng-điểm-kênh)

```sql
WITH actuals AS (
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
      AND e.status NOT IN ('CANCELLED', 'Voided')
      AND c.is_sales_channel
      [[AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
      [[AND c.channel_name = {{channel}}]]
    GROUP BY c.channel_key, c.channel_name
),

targets AS (
    SELECT
        channel_key,
        target_value AS target_margin_pct
    FROM dim_channel_targets
    WHERE metric_type = 'NET_MARGIN_PCT'
      AND target_source = 'BUDGET'
      AND period_month = date_trunc('month', current_date)
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
      },
      {
        "columns": ["Variance pp"],
        "type": "single",
        "operator": "<",
        "value": -3,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Net Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Platform Fees": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gross Margin %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Net Margin %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Target %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Variance pp": {
        "number_style": "decimal",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":18, "size_y":8}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Margin Heatmap

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


#### 📝 Text: Heatmap Heading

Heatmap Net Margin % — kênh × tháng. Màu đỏ = lỗ, xanh = lãi tốt.

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Net Margin Heatmap — Channel × Month

Heatmap: Channel (row) × Month (col), giá trị = Net Margin %. Dùng pivot table với conditional coloring. Chỉ kênh có has_cogs. Tối đa 12 tháng gần nhất.

**Domain Reference**: [CPL6 — Net Margin % Heatmap](../domains/finance.md#cpl6-net-margin--heatmap--channel--month)

```sql
SELECT
    c.channel_name                                                                AS "Kenh",
    date_trunc('month', CAST(CAST(e.date_key AS VARCHAR) AS DATE))               AS "Thang",
    ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS "Net Margin %"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key)
WHERE e.has_cogs
  AND e.status NOT IN ('CANCELLED', 'Voided')
  AND c.is_sales_channel
  AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= (current_date - INTERVAL '12 months')
  [[AND c.channel_name = {{channel}}]]
GROUP BY c.channel_name,
         date_trunc('month', CAST(CAST(e.date_key AS VARCHAR) AS DATE))
ORDER BY "Thang", "Kenh"
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "pivot_table.column_split": {
      "rows": ["Kenh"],
      "columns": ["Thang"],
      "values": ["Net Margin %"]
    },
    "column_settings": {
      "Net Margin %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Net Margin %"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": -20,
        "max_type": "custom",
        "max_value": 40
      }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":18, "size_y":8}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Variance Analysis

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


#### 📝 Text: Variance Heading

Biến động kênh — Net Revenue và Net Margin % so với kỳ trước (MoM)

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Channel MoM Variance Table

Bảng biến động MoM: 1 row/channel × (Rev hiện tại, Rev trước, Δ Rev %, Margin hiện tại, Margin trước, Δ Margin pp). Sắp xếp theo Δ Margin pp tăng dần (suy giảm nhiều nhất lên đầu).

**Domain Reference**: [CPL3 — Channel Variance vs Prior Period](../domains/finance.md#cpl3-channel-variance-vs-prior-period-biến-động-so-với-kỳ-trước)

```sql
WITH cur AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)                                                         AS rev_cur,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS margin_cur
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key)
    WHERE e.has_cogs
      AND e.status NOT IN ('CANCELLED', 'Voided')
      AND c.is_sales_channel
      AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= date_trunc('month', current_date)
      AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) <  current_date
    GROUP BY e.channel_key
),
prior AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)                                                         AS rev_prior,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS margin_prior
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key)
    WHERE e.has_cogs
      AND e.status NOT IN ('CANCELLED', 'Voided')
      AND c.is_sales_channel
      AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) <  date_trunc('month', current_date)
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
WHERE c.is_sales_channel
ORDER BY "Delta Margin pp" ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Delta Margin pp"],
        "type": "single",
        "operator": "<",
        "value": -5,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Delta Margin pp"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Rev Ky Nay": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Rev Ky Truoc": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Delta Rev %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Margin Ky Nay %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Margin Ky Truoc %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Delta Margin pp": {
        "number_style": "decimal",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":18, "size_y":8}
```

#### ❓ Question: Net Margin Trend by Channel (with Budget Target)

Multi-line: Net Margin % theo tháng × kênh. Overlay "Budget Target %" từ dim_channel_targets (metric_type='NET_MARGIN_PCT'). Xem xu hướng 12 tháng so với kế hoạch.

```sql
-- Actual net margin per channel per month
WITH actuals AS (
    SELECT
        c.channel_name                                                                AS channel_name,
        date_trunc('month', CAST(CAST(e.date_key AS VARCHAR) AS DATE))               AS period_month,
        ROUND(SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0), 1) AS net_margin_pct
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key)
    WHERE e.has_cogs
      AND e.status NOT IN ('CANCELLED', 'Voided')
      AND c.is_sales_channel
      AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= (current_date - INTERVAL '12 months')
      [[AND c.channel_name = {{channel}}]]
    GROUP BY c.channel_name,
             date_trunc('month', CAST(CAST(e.date_key AS VARCHAR) AS DATE))
),

-- Budget targets for the same window
budget AS (
    SELECT
        channel_name,
        period_month,
        target_value AS target_margin_pct
    FROM dim_channel_targets
    WHERE metric_type = 'NET_MARGIN_PCT'
      AND target_source = 'BUDGET'
      AND period_month >= (current_date - INTERVAL '12 months')
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
    "graph.dimensions": ["Thang", "Kenh"],
    "graph.metrics": ["Net Margin %", "Budget Target %"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Net Margin (%)",
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#F2A86F", "#F9D45C"],
    "series_settings": {
      "Budget Target %": {
        "line.style": "dashed",
        "color": "#EF8C8C",
        "show_series_values": false
      }
    },
    "column_settings": {
      "Net Margin %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Budget Target %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 11, "col":0, "size_x":18, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Loss-Leader Alert

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


#### 📝 Text: Loss Alert Heading

Cảnh báo loss-leader — kênh có Net Margin % âm sau khi trừ phí platform

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Loss Leader Channel Count

Số kênh đang lỗ (Net Margin % < 0) trong kỳ hiện tại. Scalar KPI — đỏ nếu > 0.

**Domain Reference**: [CPL2 — Loss Leader Flag](../domains/finance.md#cpl2-loss-leader-flag-cờ-kênh-lỗ)

```sql
SELECT COUNT(*) AS "So kenh lo"
FROM (
    SELECT
        e.channel_key,
        SUM(e.channel_net_profit) AS total_net_profit
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key)
    WHERE e.has_cogs
      AND e.status NOT IN ('CANCELLED', 'Voided')
      AND c.is_sales_channel
      [[AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
    GROUP BY e.channel_key
    HAVING SUM(e.channel_net_profit) < 0
) loss_channels
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "So kenh lo": {
        "number_style": "decimal",
        "decimals": 0
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":4, "size_y":3}
```

#### ❓ Question: Total Loss Exposure

Tổng giá trị lỗ (channel_net_profit < 0, tính toàn bộ) trong kỳ — đo mức độ rủi ro tài chính.

```sql
SELECT COALESCE(SUM(net_loss), 0) AS "Tong lo"
FROM (
    SELECT
        e.channel_key,
        SUM(e.channel_net_profit) AS net_loss
    FROM fact_order_economics e
    JOIN dim_channels c USING (channel_key)
    WHERE e.has_cogs
      AND e.status NOT IN ('CANCELLED', 'Voided')
      AND c.is_sales_channel
      [[AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
    GROUP BY e.channel_key
    HAVING SUM(e.channel_net_profit) < 0
) loss_channels
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong lo": {
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
{"row": 3, "col":4, "size_x":6, "size_y":3}
```

#### ❓ Question: Loss Leader Detail Table

Danh sách kênh đang lỗ với đầy đủ thông tin: Net Revenue, Net Profit, Net Margin %, Platform Fees. Highlight đỏ toàn dòng.

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
  AND e.status NOT IN ('CANCELLED', 'Voided')
  AND c.is_sales_channel
  [[AND CAST(CAST(e.date_key AS VARCHAR) AS DATE) >= {{date_range}}]]
  [[AND c.channel_name = {{channel}}]]
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
        "columns": ["Net Margin %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Net Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gross Profit": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Net Profit": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Platform Fees": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Net Margin %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":8}
```

#### 📝 Text: Source & Freshness

**Source:** fact_order_economics + int_misa_sales_lines · **Cadence:** custom · **Scope:** has_cogs, is_sales_channel · **Caveats:** Period filter parametric
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

