---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - is_active_order
  - filter_has_cogs
  - channel_net_profit
  - discount_sensitivity
database: "Sapo"
---

# 📘 Blueprint: Monthly · Customer Profitability [Retail]

> **Database:** `Sapo`
> **Collection ID:** 99
> **Role:** CMO, Finance-Marketing
> **Archetype:** Strategic Review (monthly cadence, 2 tabs)

Monthly deep-dive into customer profitability and margin-gated channel analysis. Audience: CMO/Finance-Marketing. Story: which channels/segments are profitable, discount-dependency margin impact, Shopee = lowest margin + worst retention → migrate to owned.

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md)
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`is_active_order`](../semantic/segments.md#is_active_order) · [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs) · [`channel_net_profit`](../semantic/metrics.md) · [`discount_sensitivity`](../domains/customer.md)
>
> **Margin framing:** contribution margin (channel_net_margin_pct / channel_net_profit) as primary — NOT fully_loaded (overhead is revenue-weighted, an artifact at this grain).

## 📂 Collection: Marketing & Customers > 👥 Customer

---

### 🖥️ Dashboard: Monthly · Customer Profitability [Retail]

**Description**: Monthly contribution-margin and discount-dependency analysis for CMO/Finance-Marketing. Two tabs: channel retention × margin story (Shopee lowest margin + worst retention → migrate to owned), discount-dependency restructure signal (98.5% PROMO_DEPENDENT, margin impact).

---

### 📑 Tab: Channel × Retention × Margin

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Cửa sổ: 90 ngày gần nhất  ·  Đến: ' || strftime(current_date, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Channel net margin % — Shopee channels are margin-lowest; owned channels profitable

# Channel net margin % — Shopee channels are margin-lowest; owned channels profitable

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Net Margin % by Channel

Channel net margin (after platform fees) last 90 days. Use contribution margin — not fully-loaded overhead which distorts channel comparison at order grain.

```sql
SELECT
  ch.channel_name                             AS "Kênh",
  COUNT(*)                                    AS "Đơn",
  ROUND(AVG(e.channel_net_margin_pct) * 100, 1) AS "Channel Net Margin %",
  ROUND(SUM(e.channel_net_profit) / 1e6, 1)  AS "Lợi nhuận (triệu)"
FROM fact_order_economics e
JOIN dim_channels ch ON e.channel_key = ch.channel_key
WHERE e.scope_retail
  AND e.has_cogs
  AND e.is_active_order
  AND e.date_key >= CAST(strftime(current_date - INTERVAL '90 days', '%Y%m%d') AS INTEGER)
GROUP BY 1
HAVING COUNT(*) >= 5
ORDER BY 3
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kênh"],
    "graph.metrics": ["Channel Net Margin %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Channel Net Margin %",
    "graph.y_axis.title_text": "",
    "table.column_formatting": [
      {
        "columns": ["Channel Net Margin %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Channel Net Margin %": { "suffix": "%" },
      "Lợi nhuận (triệu)": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 12, "size_y": 9 }
```

#### ❓ Question: Repeat Rate by Channel

Customers with >1 order, grouped by acquisition channel. Low Shopee repeat = low loyalty.

```sql
WITH channel_orders AS (
  SELECT
    ch.channel_name                                           AS channel_name,
    o.customer_key,
    COUNT(DISTINCT o.order_id)                                AS order_count
  FROM fact_orders o
  JOIN dim_channels ch ON o.channel_key = ch.channel_key
  WHERE o.scope_retail
    AND o.is_active_order
  GROUP BY 1, 2
)
SELECT
  channel_name                                                AS "Kênh",
  COUNT(*)                                                    AS "Khách hàng",
  ROUND(COUNT(CASE WHEN order_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS "Repeat %"
FROM channel_orders
GROUP BY 1
HAVING COUNT(*) >= 5
ORDER BY 3
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kênh"],
    "graph.metrics": ["Repeat %"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Repeat Purchase Rate %",
    "column_settings": {
      "Repeat %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 9 }
```

#### 📝 Text: Channel comparison table — retention × margin × order share

# Channel comparison table — retention × margin × order share

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel × Repeat Rate × Contribution Margin

Side-by-side: repeat rate + channel net margin + order share. The Shopee = low-retention + low-margin contrast in one table.

```sql
WITH orders_total AS (
  SELECT COUNT(*) AS total_orders
  FROM fact_order_economics
  WHERE scope_retail AND is_active_order
    AND date_key >= CAST(strftime(current_date - INTERVAL '90 days', '%Y%m%d') AS INTEGER)
),
channel_stats AS (
  SELECT
    ch.channel_name                                         AS channel_name,
    COUNT(DISTINCT e.order_id)                              AS order_count,
    COUNT(DISTINCT o.customer_key)                          AS customer_count,
    ROUND(AVG(e.channel_net_margin_pct) * 100, 1)          AS channel_net_margin_pct,
    ROUND(SUM(e.channel_net_profit) / 1e6, 1)              AS net_profit_mil
  FROM fact_order_economics e
  JOIN dim_channels ch ON e.channel_key = ch.channel_key
  JOIN fact_orders o ON e.order_id = o.order_id
  WHERE e.scope_retail AND e.has_cogs AND e.is_active_order
    AND e.date_key >= CAST(strftime(current_date - INTERVAL '90 days', '%Y%m%d') AS INTEGER)
  GROUP BY 1
),
repeat_stats AS (
  SELECT
    ch.channel_name,
    ROUND(COUNT(CASE WHEN cust_orders.order_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS repeat_pct
  FROM (
    SELECT o.customer_key, ch2.channel_name, COUNT(DISTINCT o.order_id) AS order_count
    FROM fact_orders o
    JOIN dim_channels ch2 ON o.channel_key = ch2.channel_key
    WHERE o.scope_retail AND o.is_active_order
    GROUP BY 1, 2
  ) cust_orders
  JOIN dim_channels ch ON cust_orders.channel_name = ch.channel_name
  GROUP BY 1
)
SELECT
  cs.channel_name                                           AS "Kênh",
  cs.order_count                                            AS "Đơn (90d)",
  ROUND(cs.order_count * 100.0 / ot.total_orders, 1)       AS "Order Share %",
  rs.repeat_pct                                             AS "Repeat %",
  cs.channel_net_margin_pct                                 AS "Channel Net Margin %",
  cs.net_profit_mil                                         AS "Net Profit (triệu)"
FROM channel_stats cs
JOIN repeat_stats rs ON cs.channel_name = rs.channel_name
CROSS JOIN orders_total ot
WHERE cs.order_count >= 5
ORDER BY cs.order_count DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Channel Net Margin %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Channel Net Margin %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Repeat %"],
        "type": "single",
        "operator": ">=",
        "value": 30,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Repeat %"],
        "type": "single",
        "operator": "<",
        "value": 15,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Channel Net Margin %": { "suffix": "%" },
      "Repeat %": { "suffix": "%" },
      "Order Share %": { "suffix": "%" },
      "Net Profit (triệu)": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 7 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_order_economics + fact_orders + dim_channels · **Scope:** scope_retail AND has_cogs AND is_active_order · **Window:** 90 days rolling · **Cadence:** monthly review · ⚠️ channel_net_margin only available for orders with has_cogs (~65% coverage); fully_loaded_margin penalizes large orders (overhead allocation artifact at order grain) — channel_net_margin preferred for channel comparison.
<!-- text-id:source-freshness-channel -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 2 }
```

---

### 📑 Tab: Discount-Dependency × Margin

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Snapshot khách hàng: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  All-time (dim_customers không theo ngày)'
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Discount dependency analysis — 98.5% of retail base is PROMO_DEPENDENT

# Discount dependency analysis — 98.5% of retail base is PROMO_DEPENDENT

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Sensitivity Distribution

Share of retail customers by discount dependency. PROMO_DEPENDENT dominates — no full-price cohort to protect.

```sql
SELECT
  COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu') AS "Nhóm nhạy cảm giá",
  COUNT(*)                                            AS "Khách hàng",
  ROUND(COUNT(*) * 100.0 / NULLIF(
    (SELECT COUNT(*) FROM dim_customers WHERE customer_type = 'RETAIL' AND customer_id != 'Unknown'), 0
  ), 1)                                               AS "% Tổng"
FROM dim_customers
WHERE customer_type = 'RETAIL'
  AND customer_id != 'Unknown'
GROUP BY 1
ORDER BY
  CASE COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu')
    WHEN 'PROMO_DEPENDENT' THEN 1
    WHEN 'PROMO_MIXED'     THEN 2
    WHEN 'FULL_PRICE'      THEN 3
    ELSE 4
  END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Nhóm nhạy cảm giá",
    "pie.metric": "Khách hàng",
    "pie.colors": {
      "PROMO_DEPENDENT":     "#EF8C8C",
      "PROMO_MIXED":         "#F9D45C",
      "FULL_PRICE":          "#84BB4C",
      "Chưa đủ dữ liệu":    "#C2D2E9"
    },
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Avg Contribution Margin by Discount Sensitivity

Margin contrast: PROMO_DEPENDENT = margin-negative; FULL_PRICE positive.

```sql
SELECT
  COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu') AS "Nhóm nhạy cảm giá",
  COUNT(*)                                            AS "Khách hàng",
  ROUND(AVG(lifetime_contribution_margin) / 1000.0, 0) AS "Avg Contribution (K VND)",
  COUNT(CASE WHEN is_margin_negative THEN 1 END)      AS "Margin âm"
FROM dim_customers
WHERE customer_type = 'RETAIL'
  AND customer_id != 'Unknown'
GROUP BY 1
ORDER BY
  CASE COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu')
    WHEN 'PROMO_DEPENDENT' THEN 1
    WHEN 'PROMO_MIXED'     THEN 2
    WHEN 'FULL_PRICE'      THEN 3
    ELSE 4
  END
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhóm nhạy cảm giá"],
    "graph.metrics": ["Avg Contribution (K VND)"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Avg Contribution Margin (K VND)",
    "column_settings": {
      "Avg Contribution (K VND)": { "suffix": "K" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Key KPIs — PROMO_DEPENDENT revenue leakage and margin-negative customer count

# Key KPIs — PROMO_DEPENDENT revenue leakage and margin-negative customer count

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: PROMO_DEPENDENT — Discount % of Gross Revenue

Share of gross revenue consumed by discounts for PROMO_DEPENDENT customers.

```sql
WITH promo_dep AS (
  SELECT
    o.customer_key,
    SUM(o.gross_revenue)    AS gross_rev,
    SUM(o.discount_amount)  AS disc_amt
  FROM fact_orders o
  JOIN dim_customers c ON o.customer_key = c.customer_key
  WHERE o.scope_retail
    AND o.is_active_order
    AND c.discount_sensitivity = 'PROMO_DEPENDENT'
    AND c.customer_id != 'Unknown'
  GROUP BY 1
)
SELECT
  ROUND(SUM(disc_amt) * 100.0 / NULLIF(SUM(gross_rev), 0), 1) AS "Discount % of Gross (PROMO_DEP)"
FROM promo_dep
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Discount % of Gross (PROMO_DEP)": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Margin-Negative Retail Customers

Count of retail customers with negative lifetime contribution margin.

```sql
SELECT COUNT(*) AS "Margin-Negative Customers"
FROM dim_customers
WHERE customer_type = 'RETAIL'
  AND customer_id != 'Unknown'
  AND is_margin_negative = true
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 10, "col": 6, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: PROMO_DEPENDENT Retail Customers

Total retail customers classified as promo-dependent.

```sql
SELECT COUNT(*) AS "PROMO_DEPENDENT Customers"
FROM dim_customers
WHERE customer_type = 'RETAIL'
  AND customer_id != 'Unknown'
  AND discount_sensitivity = 'PROMO_DEPENDENT'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 10, "col": 12, "size_x": 6, "size_y": 3 }
```

#### 📝 Text: Discount sensitivity × margin detail — segment-level breakdown

# Discount sensitivity × margin detail — segment-level breakdown

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Sensitivity × Value Tier × Margin Detail

Full breakdown: sensitivity × value group × margin health.

```sql
SELECT
  COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu') AS "Nhạy cảm giá",
  value_group                                         AS "Tier",
  COUNT(*)                                            AS "Khách hàng",
  COUNT(CASE WHEN is_margin_negative THEN 1 END)      AS "Margin âm",
  ROUND(COUNT(CASE WHEN is_margin_negative THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS "% Margin âm",
  ROUND(AVG(lifetime_contribution_margin) / 1000.0, 0) AS "Avg Contrib. (K)",
  ROUND(AVG(lifetime_value) / 1000.0, 0)             AS "Avg LTV (K)"
FROM dim_customers
WHERE customer_type = 'RETAIL'
  AND customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY
  CASE COALESCE(discount_sensitivity, 'Chưa đủ dữ liệu')
    WHEN 'PROMO_DEPENDENT' THEN 1
    WHEN 'PROMO_MIXED'     THEN 2
    WHEN 'FULL_PRICE'      THEN 3
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
    "table.column_formatting": [
      {
        "columns": ["% Margin âm"],
        "type": "single",
        "operator": ">=",
        "value": 50,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Avg Contrib. (K)"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Avg Contrib. (K)"],
        "type": "single",
        "operator": ">=",
        "value": 5000,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Avg Contrib. (K)": { "suffix": "K VND" },
      "Avg LTV (K)": { "suffix": "K VND" },
      "% Margin âm": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** dim_customers + fact_orders · **Scope:** scope_retail (customer_type='RETAIL') · **Cadence:** monthly snapshot · ⚠️ discount_sensitivity NULL for ~78% of base (single-purchase customers with insufficient order history). PROMO_MIXED has only 1 customer in current data — use for structural insight only, not individual targeting.
<!-- text-id:source-freshness-discount -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 2 }
```
