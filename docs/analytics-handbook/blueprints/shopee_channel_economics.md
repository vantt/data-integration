---
primary_scope: scope_sales
scope_indicator: "[Cross]"
layer: L3
uses_concepts: [scope_sales, filter_has_cogs, net_revenue, gross_profit, service_fee_revenue, shopee_service_fee]
---

# Shopee Channel Economics [Cross] Blueprint

**Design Spec**: [Shopee Channel Economics](../designs/shopee_channel_economics.md)

Kiem tra chi phi ban hang Shopee — ty le tien thuc nhan sau phi san, phan tich co cau phi, xu huong MoM, va chi tiet don hang/san pham bi mat margin nhieu nhat.

## Segmentation Scope

> **Scope:** `scope_sales` filtered to Shopee channel · Layer 3 (Analytics) · Suffix `[Cross]`
> **Why:** Shopee channel economics analyzes all orders placed via Shopee platform regardless of customer type. Both retail and B2B customers may use Shopee. Channel filter: `channel_name ILIKE '%Shopee%'` or equivalent.
> **Ref:** [segments.md#scope_sales](../semantic/segments.md#scope_sales) · [rules.md#ShopeeServiceFee](../semantic/rules.md)

Base: `WHERE scope_sales AND <shopee_channel_filter>`. Margin: additionally `AND has_cogs`.

## 📂 Collection: Analytics

### Dashboard: Shopee Channel Economics [Cross]

**Description**: Audience: Operations Manager / Finance. Scope: Cross-segment Shopee channel deep-dive. Phan tich kinh te kenh Shopee — settlement margin, co cau phi san, xu huong theo thang, va chi tiet don hang/san pham co settlement thap nhat.

---

#### Filter: Payout Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days",
  "field_id": 287
}
```

#### Filter: Order Type

```json metabase-filter
{
  "slug": "order_type",
  "type": "string/=",
  "field_id": 288
}
```

---

### 📑 Tab: Settlement Overview

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{order_type}}]]
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
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Overview Heading

## Monitor chi phi ban hang Shopee — ty le tien thuc nhan sau phi san

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Settlement Margin %

Hero metric — % doanh thu thuc nhan sau khi tru het phi Shopee. Gauge voi 3 vung: <60% red, 60-75% yellow, >75% green.

```sql
SELECT
    ROUND(
        SUM(net_settlement) * 1.0 / NULLIF(SUM(gross_revenue), 0),
        4
    ) AS "Settlement Margin %"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,    "max": 0.6,  "color": "#EF8C8C", "label": "Nguy hiem (<60%)" },
      { "min": 0.6,  "max": 0.75, "color": "#F9D45C", "label": "Can theo doi (60-75%)" },
      { "min": 0.75, "max": 1.5,  "color": "#84BB4C", "label": "On track (>75%)" }
    ],
    "column_settings": {
      "Settlement Margin %": {
        "number_style": "percent",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":6, "size_y":5}
```

#### Question: Gross Revenue

Supporting KPI — tong doanh thu Shopee trong ky loc.

```sql
SELECT COALESCE(SUM(gross_revenue), 0) AS "Gross Revenue"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Gross Revenue": {
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
{"row": 3, "col":6, "size_x":4, "size_y":3}
```

#### Question: Net Settlement

Supporting KPI — tien thuc nhan tu Shopee trong ky loc.

```sql
SELECT COALESCE(SUM(net_settlement), 0) AS "Net Settlement"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Net Settlement": {
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
{"row": 3, "col":10, "size_x":4, "size_y":3}
```

#### Question: Platform Fee Rate %

Supporting KPI — tong phi san / gross revenue trong ky loc.

```sql
SELECT
    ROUND(
        (
            COALESCE(SUM(ABS(service_fee)), 0)
            + COALESCE(SUM(ABS(payment_fee)), 0)
            + COALESCE(SUM(ABS(fixed_fee)), 0)
            + COALESCE(SUM(ABS(infrastructure_fee)), 0)
            + COALESCE(SUM(ABS(voucher_xtra_fee)), 0)
        ) * 1.0 / NULLIF(SUM(gross_revenue), 0),
        4
    ) AS "Platform Fee Rate %"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Platform Fee Rate %": {
        "number_style": "percent",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

#### 📝 Text: Fee Breakdown Heading

## Phan tich co cau phi — loai phi nao chiem nhieu nhat?

```json metabase-pos
{"row": 8, "col":0, "size_x":18, "size_y":1}
```

#### Question: Fee Breakdown

Ranking cac loai phi theo gia tri tuyet doi — horizontal bar.

```sql
SELECT
    "Loai phi",
    "Gia tri phi (VND)"
FROM (
    SELECT 'Service Fee'       AS "Loai phi", COALESCE(SUM(ABS(service_fee)), 0)        AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
    UNION ALL
    SELECT 'Payment Fee'       AS "Loai phi", COALESCE(SUM(ABS(payment_fee)), 0)         AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
    UNION ALL
    SELECT 'Fixed Fee'         AS "Loai phi", COALESCE(SUM(ABS(fixed_fee)), 0)           AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
    UNION ALL
    SELECT 'Infrastructure Fee' AS "Loai phi", COALESCE(SUM(ABS(infrastructure_fee)), 0) AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
    UNION ALL
    SELECT 'Voucher Xtra Fee'  AS "Loai phi", COALESCE(SUM(ABS(voucher_xtra_fee)), 0)   AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
    UNION ALL
    SELECT 'VAT Tax'           AS "Loai phi", COALESCE(SUM(ABS(vat_tax)), 0)             AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
    UNION ALL
    SELECT 'Personal Income Tax' AS "Loai phi", COALESCE(SUM(ABS(personal_income_tax)), 0) AS "Gia tri phi (VND)" FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]
) fee_summary
ORDER BY "Gia tri phi (VND)" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loai phi"],
    "graph.metrics": ["Gia tri phi (VND)"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Tong phi (VND)",
    "graph.y_axis.title_text": "",
    "column_settings": {
      "Gia tri phi (VND)": {
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
{"row": 9, "col":0, "size_x":9, "size_y":6}
```

#### Question: Revenue to Settlement Waterfall

Gross Revenue bi an mon boi tung loai phi, con lai Net Settlement — waterfall chart.

```sql
SELECT
    "Buoc",
    "Gia tri (VND)"
FROM (
    VALUES
        (1, 'Gross Revenue',       (SELECT COALESCE(SUM(gross_revenue), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (2, 'Service Fee',         (SELECT -COALESCE(SUM(ABS(service_fee)), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (3, 'Payment Fee',         (SELECT -COALESCE(SUM(ABS(payment_fee)), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (4, 'Fixed Fee',           (SELECT -COALESCE(SUM(ABS(fixed_fee)), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (5, 'Infrastructure Fee',  (SELECT -COALESCE(SUM(ABS(infrastructure_fee)), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (6, 'Voucher Xtra Fee',    (SELECT -COALESCE(SUM(ABS(voucher_xtra_fee)), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (7, 'Taxes',               (SELECT -(COALESCE(SUM(ABS(vat_tax)), 0) + COALESCE(SUM(ABS(personal_income_tax)), 0)) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]])),
        (8, 'Net Settlement',      (SELECT COALESCE(SUM(net_settlement), 0) FROM int_shopee_order_fees WHERE payout_released_at IS NOT NULL [[AND {{date_range}}]] [[AND {{order_type}}]]))
) AS waterfall_data("Thu tu", "Buoc", "Gia tri (VND)")
ORDER BY "Thu tu"
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": ["Buoc"],
    "graph.metrics": ["Gia tri (VND)"],
    "waterfall.increase_color": "#84BB4C",
    "waterfall.decrease_color": "#EF8C8C",
    "waterfall.total_color": "#509EE3",
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Gia tri (VND)": {
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
{"row": 9, "col":9, "size_x":9, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** int_shopee_order_fees · **Cadence:** payout-period · **Scope:** payout_released_at IS NOT NULL · **Caveats:** Shopee fee data only
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Trends & Details


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{order_type}}]]
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
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Trend Heading

## Xu huong settlement — margin dang cai thien hay xau di?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Settlement Margin Trend

Settlement margin % theo tung thang — line chart voi reference line 75%.

```sql
SELECT
    date_trunc('month', payout_released_at) AS "Thang",
    ROUND(
        SUM(net_settlement) * 1.0 / NULLIF(SUM(gross_revenue), 0),
        4
    ) AS "Settlement Margin %"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
GROUP BY date_trunc('month', payout_released_at)
ORDER BY "Thang"
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Settlement Margin %"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Settlement Margin (%)",
    "graph.goal_value": 0.75,
    "graph.show_goal": true,
    "graph.goal_label": "Muc tieu 75%",
    "series_settings": {
      "Settlement Margin %": { "color": "#509EE3" }
    },
    "column_settings": {
      "Settlement Margin %": {
        "number_style": "percent",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Fee Composition Trend

Co cau phi theo tung thang — stacked bar theo loai phi.

```sql
SELECT
    date_trunc('month', payout_released_at) AS "Thang",
    COALESCE(SUM(ABS(service_fee)), 0)         AS "Service Fee",
    COALESCE(SUM(ABS(payment_fee)), 0)          AS "Payment Fee",
    COALESCE(SUM(ABS(fixed_fee)), 0)            AS "Fixed Fee",
    COALESCE(SUM(ABS(infrastructure_fee)), 0)   AS "Infrastructure Fee",
    COALESCE(SUM(ABS(voucher_xtra_fee)), 0)     AS "Voucher Xtra Fee"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
GROUP BY date_trunc('month', payout_released_at)
ORDER BY "Thang"
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Service Fee", "Payment Fee", "Fixed Fee", "Infrastructure Fee", "Voucher Xtra Fee"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Tong phi (VND)",
    "series_settings": {
      "Service Fee":         { "color": "#509EE3" },
      "Payment Fee":         { "color": "#88BDE6" },
      "Fixed Fee":           { "color": "#A989C5" },
      "Infrastructure Fee":  { "color": "#F2A86F" },
      "Voucher Xtra Fee":    { "color": "#F9D45C" }
    },
    "column_settings": {
      "Service Fee":         { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Payment Fee":         { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Fixed Fee":           { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Infrastructure Fee":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Voucher Xtra Fee":    { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Low Settlement Orders Heading

## Chi tiet don hang — don nao co settlement thap nhat?

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders with Lowest Settlement

Bottom 20 don hang theo settlement % — conditional formatting <50% red.

```sql
SELECT
    order_code                                                      AS "Ma don hang",
    order_placed_at                                                 AS "Ngay dat hang",
    payout_released_at                                              AS "Ngay phat hanh",
    order_type                                                      AS "Loai don",
    payment_method                                                  AS "Phuong thuc thanh toan",
    buyer_username                                                  AS "Nguoi mua",
    gross_revenue                                                   AS "Gross Revenue (VND)",
    COALESCE(ABS(service_fee), 0)
        + COALESCE(ABS(payment_fee), 0)
        + COALESCE(ABS(fixed_fee), 0)
        + COALESCE(ABS(infrastructure_fee), 0)
        + COALESCE(ABS(voucher_xtra_fee), 0)
        + COALESCE(ABS(vat_tax), 0)
        + COALESCE(ABS(personal_income_tax), 0)                    AS "Tong phi (VND)",
    net_settlement                                                  AS "Net Settlement (VND)",
    ROUND(
        net_settlement * 1.0 / NULLIF(gross_revenue, 0),
        4
    )                                                               AS "Settlement %"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
ORDER BY "Settlement %" ASC NULLS LAST
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
      {
        "columns": ["Settlement %"],
        "type": "single",
        "operator": "<",
        "value": 0.5,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "[\"name\",\"Ma don hang\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Ma don hang}}"
        }
      },
      "Gross Revenue (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Tong phi (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Net Settlement (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Settlement %": {
        "number_style": "percent",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Product Settlement Heading

## Hieu qua theo san pham — san pham nao bi mat margin nhieu nhat tren Shopee?

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Product Settlement Summary

Revenue, settlement, margin % theo san pham — conditional: <60% red, >80% green.

```sql
SELECT
    items.product_name                                                          AS "San pham",
    COUNT(DISTINCT items.order_code)                                            AS "So don",
    COALESCE(SUM(fees.gross_revenue), 0)                                        AS "Gross Revenue (VND)",
    COALESCE(SUM(fees.net_settlement), 0)                                       AS "Net Settlement (VND)",
    ROUND(
        SUM(fees.net_settlement) * 1.0 / NULLIF(SUM(fees.gross_revenue), 0),
        4
    )                                                                           AS "Settlement Margin %",
    COALESCE(SUM(ABS(fees.service_fee)), 0)
        + COALESCE(SUM(ABS(fees.payment_fee)), 0)
        + COALESCE(SUM(ABS(fees.fixed_fee)), 0)
        + COALESCE(SUM(ABS(fees.infrastructure_fee)), 0)
        + COALESCE(SUM(ABS(fees.voucher_xtra_fee)), 0)                          AS "Tong phi san (VND)"
FROM int_shopee_order_items items
INNER JOIN int_shopee_order_fees fees ON items.order_code = fees.order_code
WHERE fees.payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
GROUP BY items.product_name
ORDER BY "Settlement Margin %" ASC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
      {
        "columns": ["Settlement Margin %"],
        "type": "single",
        "operator": "<",
        "value": 0.6,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Settlement Margin %"],
        "type": "single",
        "operator": ">",
        "value": 0.8,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Gross Revenue (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Net Settlement (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Tong phi san (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Settlement Margin %": {
        "number_style": "percent",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 9 }
```

---


#### 📝 Text: Source & Freshness

**Source:** int_shopee_order_fees · **Cadence:** payout-period · **Scope:** payout_released_at IS NOT NULL · **Caveats:** Shopee fee data only
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Shopee P&L Cascade


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{order_type}}]]
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
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: PnL Cascade Heading

## Shopee P&L Cascade — chi phi that su va diem hoa von theo don hang

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: PnL Caveat

**Luu y:** Du lieu nay join Shopee fees (int_shopee_order_fees) voi MISA COGS (fact_order_economics). Don hang has_cogs=FALSE khong co COGS → true_margin se bi inflation. Chi giai thich duoc tren tap mau co MISA match.

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Shopee Margin vs COGS Scatter

Phan tan don hang theo order_value va true_margin — phat hien diem hoa von. True margin = (net_settlement - cogs_amount) / gross_revenue. Mau xanh = co loi nhuan, do = lo.

```sql
WITH order_buckets AS (
    SELECT
        fees.order_code,
        fees.gross_revenue,
        fees.net_settlement,
        COALESCE(econ.cogs_amount, 0)                                           AS cogs_amount,
        econ.has_cogs,
        CASE
            WHEN fees.gross_revenue < 100000  THEN '< 100K'
            WHEN fees.gross_revenue < 200000  THEN '100K-200K'
            WHEN fees.gross_revenue < 500000  THEN '200K-500K'
            WHEN fees.gross_revenue < 1000000 THEN '500K-1M'
            ELSE '> 1M'
        END                                                                     AS order_value_bucket,
        CASE
            WHEN fees.gross_revenue < 100000  THEN 50000
            WHEN fees.gross_revenue < 200000  THEN 150000
            WHEN fees.gross_revenue < 500000  THEN 350000
            WHEN fees.gross_revenue < 1000000 THEN 750000
            ELSE 1500000
        END                                                                     AS bucket_midpoint
    FROM int_shopee_order_fees fees
    LEFT JOIN fact_order_economics econ ON fees.order_code = econ.order_code
    WHERE fees.payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{order_type}}]]
)
SELECT
    order_value_bucket                                                           AS "Nhom gia tri don hang",
    bucket_midpoint                                                              AS "Gia tri trung binh (VND)",
    ROUND(
        (SUM(net_settlement) - SUM(cogs_amount)) * 1.0
        / NULLIF(SUM(gross_revenue), 0),
        4
    )                                                                            AS "True Margin %",
    COUNT(*)                                                                     AS "So don hang",
    SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END)                                   AS "Don co COGS (MISA)"
FROM order_buckets
GROUP BY order_value_bucket, bucket_midpoint
ORDER BY bucket_midpoint
```

```json metabase-viz
{
  "display": "scatter",
  "visualization_settings": {
    "graph.dimensions": ["Gia tri trung binh (VND)"],
    "graph.metrics": ["True Margin %"],
    "scatter.bubble": "So don hang",
    "graph.x_axis.title_text": "Gia tri don hang trung binh (VND)",
    "graph.y_axis.title_text": "True Margin % (sau Shopee fees + COGS)",
    "graph.goal_value": 0,
    "graph.show_goal": true,
    "graph.goal_label": "Diem hoa von (0%)",
    "series_settings": {
      "True Margin %": { "color": "#509EE3" }
    },
    "column_settings": {
      "True Margin %": {
        "number_style": "percent",
        "decimals": 1
      },
      "Gia tri trung binh (VND)": {
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
{ "row": 4, "col": 0, "size_x": 12, "size_y": 8 }
```

#### Question: Cost Waterfall % of Net Revenue

Ty le % cua tung loai chi phi so voi net_revenue — horizontal bar de thay loai phi nao "can" margin nhieu nhat. Tinh tren tap don hang co MISA COGS match.

```sql
WITH base AS (
    SELECT
        NULLIF(SUM(econ.net_revenue), 0)                                        AS total_net_revenue,
        COALESCE(SUM(econ.cogs_amount), 0)                                      AS total_cogs,
        COALESCE(SUM(ABS(fees.service_fee)), 0)                                 AS total_service_fee,
        COALESCE(SUM(ABS(fees.payment_fee)), 0)                                 AS total_payment_fee,
        COALESCE(SUM(ABS(fees.fixed_fee)), 0)                                   AS total_fixed_fee,
        COALESCE(SUM(ABS(fees.infrastructure_fee)), 0)                          AS total_infra_fee,
        COALESCE(SUM(ABS(fees.voucher_xtra_fee)), 0)                            AS total_xtra_fee,
        COALESCE(SUM(ABS(fees.vat_tax)) + SUM(ABS(fees.personal_income_tax)), 0) AS total_taxes,
        COALESCE(SUM(econ.gross_profit - (econ.net_revenue - fees.net_settlement)), 0) AS total_net_profit
    FROM int_shopee_order_fees fees
    INNER JOIN fact_order_economics econ ON fees.order_code = econ.order_code
    WHERE fees.payout_released_at IS NOT NULL
      AND econ.has_cogs = TRUE
      [[AND {{date_range}}]]
      [[AND {{order_type}}]]
)
SELECT
    "Khoan muc",
    ROUND("Phan tram" * 100, 2) AS "% cua Net Revenue"
FROM (
    SELECT 'COGS (Hang hoa)'     AS "Khoan muc", total_cogs / total_net_revenue AS "Phan tram", 1 AS sort_order FROM base
    UNION ALL
    SELECT 'Service Fee',        total_service_fee / total_net_revenue,          2 FROM base
    UNION ALL
    SELECT 'Payment Fee',        total_payment_fee / total_net_revenue,          3 FROM base
    UNION ALL
    SELECT 'Fixed Fee',          total_fixed_fee / total_net_revenue,            4 FROM base
    UNION ALL
    SELECT 'Infrastructure Fee', total_infra_fee / total_net_revenue,            5 FROM base
    UNION ALL
    SELECT 'Voucher Xtra Fee',   total_xtra_fee / total_net_revenue,             6 FROM base
    UNION ALL
    SELECT 'Taxes',              total_taxes / total_net_revenue,                7 FROM base
) breakdown
ORDER BY sort_order
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Khoan muc"],
    "graph.metrics": ["% cua Net Revenue"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "% cua Net Revenue",
    "graph.y_axis.title_text": "",
    "column_settings": {
      "% cua Net Revenue": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 12, "size_x": 6, "size_y": 8 }
```

#### Question: Orders Below Breakeven (True Margin < 0)

So don hang lo that su sau khi tinh COGS + phi Shopee. Chi hien thi don co MISA match (has_cogs=TRUE).

```sql
SELECT
    fees.order_code                                                             AS "Ma don hang",
    fees.payout_released_at                                                     AS "Ngay phat hanh",
    fees.gross_revenue                                                          AS "Gross Revenue (VND)",
    fees.net_settlement                                                         AS "Net Settlement (VND)",
    COALESCE(econ.cogs_amount, 0)                                               AS "COGS (VND)",
    fees.net_settlement - COALESCE(econ.cogs_amount, 0)                         AS "True Profit (VND)",
    ROUND(
        (fees.net_settlement - COALESCE(econ.cogs_amount, 0)) * 1.0
        / NULLIF(fees.gross_revenue, 0),
        4
    )                                                                           AS "True Margin %"
FROM int_shopee_order_fees fees
INNER JOIN fact_order_economics econ ON fees.order_code = econ.order_code
WHERE fees.payout_released_at IS NOT NULL
  AND econ.has_cogs = TRUE
  AND (fees.net_settlement - COALESCE(econ.cogs_amount, 0)) < 0
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
ORDER BY "True Profit (VND)" ASC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
      {
        "columns": ["True Margin %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "[\"name\",\"Ma don hang\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Ma don hang}}"
        }
      },
      "Gross Revenue (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Net Settlement (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "COGS (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "True Profit (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "True Margin %": {
        "number_style": "percent",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** int_shopee_order_fees · **Cadence:** payout-period · **Scope:** payout_released_at IS NOT NULL · **Caveats:** Shopee fee data only
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```
