# Shopee Channel Economics Blueprint

**Design Spec**: [Shopee Channel Economics](../designs/shopee_channel_economics.md)

Kiem tra chi phi ban hang Shopee — ty le tien thuc nhan sau phi san, phan tich co cau phi, xu huong MoM, va chi tiet don hang/san pham bi mat margin nhieu nhat.

## 📂 Collection: Operations > Periodic Reviews

### Dashboard: Shopee Channel Economics

**Description**: Phan tich kinh te kenh Shopee — settlement margin, co cau phi san, xu huong theo thang, va chi tiet don hang/san pham co settlement thap nhat.

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

#### 📝 Text: Overview Heading

## Monitor chi phi ban hang Shopee — ty le tien thuc nhan sau phi san

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 5 }
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
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
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
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
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
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

#### Question: Chu ky bao cao

Hien thi pham vi ngay payout thuc te trong ky dang xem — tu ngay den ngay.

```sql
SELECT
    STRFTIME(MIN(payout_released_at), '%d/%m/%Y') AS "Tu ngay",
    STRFTIME(MAX(payout_released_at), '%d/%m/%Y') AS "Den ngay"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{order_type}}]]
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact"
  }
}
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 12, "size_y": 2 }
```

#### 📝 Text: Fee Breakdown Heading

## Phan tich co cau phi — loai phi nao chiem nhieu nhat?

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 7, "col": 0, "size_x": 9, "size_y": 6 }
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
{ "row": 7, "col": 9, "size_x": 9, "size_y": 6 }
```

---

### 📑 Tab: Trends & Details

#### 📝 Text: Trend Heading

## Xu huong settlement — margin dang cai thien hay xau di?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
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
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Low Settlement Orders Heading

## Chi tiet don hang — don nao co settlement thap nhat?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Product Settlement Heading

## Hieu qua theo san pham — san pham nao bi mat margin nhieu nhat tren Shopee?

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 18, "col": 0, "size_x": 18, "size_y": 9 }
```
