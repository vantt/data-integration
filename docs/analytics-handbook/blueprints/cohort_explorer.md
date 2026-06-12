---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - mart_cohort_retention
---

# 📘 Blueprint: Cohort Explorer [Retail]

> **Target Collection:** `Marketing & Customers > 👥 Customer`
> **Design Spec:** `plans/260612-1337-cohort-analytics-handoff/handoff-prompt.md` (§5 spec v1)
> **Role:** Marketing Manager, Customer Success
> **Archetype:** Analytical — on-demand cohort exploration
> **Database:** Sapo

## Semantic Contract

> **Scope:** `scope_retail` — pre-filtered in mart (cohort_size ≥ 10, customer_type=RETAIL).
> **Source:** `mart_cohort_retention` — long-format, 1 row per (cohort_dimension × cohort_value × window_type × period_n).
> **Metric v1:** retention_pct · revenue_retention · repeat_rate. Margin = v2.

---

## 📂 Collection: Marketing & Customers > 👥 Customer

Multi-dimensional cohort analytics — compare retention, revenue, and repeat rate across every customer entry path.

---

### 🖥️ Dashboard: Cohort Explorer [Retail]

**Description**: Multi-axis cohort explorer. Pick cohort_dimension to compare how different entry paths (first product, channel, basket size, value band, composite) drive long-term retention and revenue. Retail scope; min cohort size = 10.

---

#### Filter: Cohort Dimension

```json metabase-filter
{
  "slug": "cohort_dimension",
  "type": "string/=",
  "field_id": 1793
}
```

---

#### Filter: Window Type

```json metabase-filter
{
  "slug": "window_type",
  "type": "string/=",
  "field_id": 1795
}
```

---

#### 📝 Text: Select cohort dimension — compare retention and revenue by entry path (product / channel / basket / value band)

# Select cohort dimension — compare entry path retention

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

#### ❓ Question: Cohort Retention Matrix

Retention % by cohort × period M0–M12. Pre-pivoted for relative window only (period_n=0..12 integers). window_type hardcoded to 'relative' — calendar window uses YYYY-MM period_n which makes the CASE WHEN pivot meaningless. Use the Data Table below for calendar window.

```sql
SELECT
    cohort_value                                                      AS "Cohort",
    MAX(cohort_size)                                                  AS "Size",
    MAX(CASE WHEN period_n = '0'  THEN ROUND(retention_pct, 1) END)  AS "M0",
    MAX(CASE WHEN period_n = '1'  THEN ROUND(retention_pct, 1) END)  AS "M1",
    MAX(CASE WHEN period_n = '2'  THEN ROUND(retention_pct, 1) END)  AS "M2",
    MAX(CASE WHEN period_n = '3'  THEN ROUND(retention_pct, 1) END)  AS "M3",
    MAX(CASE WHEN period_n = '4'  THEN ROUND(retention_pct, 1) END)  AS "M4",
    MAX(CASE WHEN period_n = '5'  THEN ROUND(retention_pct, 1) END)  AS "M5",
    MAX(CASE WHEN period_n = '6'  THEN ROUND(retention_pct, 1) END)  AS "M6",
    MAX(CASE WHEN period_n = '7'  THEN ROUND(retention_pct, 1) END)  AS "M7",
    MAX(CASE WHEN period_n = '8'  THEN ROUND(retention_pct, 1) END)  AS "M8",
    MAX(CASE WHEN period_n = '9'  THEN ROUND(retention_pct, 1) END)  AS "M9",
    MAX(CASE WHEN period_n = '10' THEN ROUND(retention_pct, 1) END)  AS "M10",
    MAX(CASE WHEN period_n = '11' THEN ROUND(retention_pct, 1) END)  AS "M11",
    MAX(CASE WHEN period_n = '12' THEN ROUND(retention_pct, 1) END)  AS "M12"
FROM main_marts.mart_cohort_retention
WHERE 1=1
  [[AND {{cohort_dimension}}]]
  AND window_type = 'relative'
GROUP BY cohort_value
ORDER BY cohort_value
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      }
    ]
  }
}
```

```json metabase-pos
{
  "row": 1,
  "col": 0,
  "size_x": 18,
  "size_y": 10
}
```

---

#### 📝 Text: Revenue retention and repeat rate by cohort — which entry path builds lasting value?

# Revenue retention & repeat rate by entry path

```json metabase-pos
{
  "row": 11,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

#### ❓ Question: Cohort Value Summary

Revenue retention (vs M0) + repeat rate per cohort. M0–M6 pivoted. Repeat Rate = % of cohort who ever placed a 2nd order. window_type hardcoded to 'relative' (same reason as Retention Matrix — calendar YYYY-MM period_n invalidates CASE WHEN pivot).

```sql
SELECT
    cohort_value                                                               AS "Cohort",
    MAX(cohort_size)                                                           AS "Size",
    MAX(repeat_customers)                                                      AS "Repeat Buyers",
    ROUND(MAX(repeat_customers) * 100.0 / NULLIF(MAX(cohort_size), 0), 1)     AS "Repeat Rate %",
    MAX(CASE WHEN period_n = '1'  THEN ROUND(retention_pct, 1) END)           AS "M1 Ret %",
    MAX(CASE WHEN period_n = '0'  THEN ROUND(revenue_retention * 100, 1) END) AS "M0 Rev",
    MAX(CASE WHEN period_n = '1'  THEN ROUND(revenue_retention * 100, 1) END) AS "M1 Rev",
    MAX(CASE WHEN period_n = '2'  THEN ROUND(revenue_retention * 100, 1) END) AS "M2 Rev",
    MAX(CASE WHEN period_n = '3'  THEN ROUND(revenue_retention * 100, 1) END) AS "M3 Rev",
    MAX(CASE WHEN period_n = '4'  THEN ROUND(revenue_retention * 100, 1) END) AS "M4 Rev",
    MAX(CASE WHEN period_n = '5'  THEN ROUND(revenue_retention * 100, 1) END) AS "M5 Rev",
    MAX(CASE WHEN period_n = '6'  THEN ROUND(revenue_retention * 100, 1) END) AS "M6 Rev"
FROM main_marts.mart_cohort_retention
WHERE 1=1
  [[AND {{cohort_dimension}}]]
  AND window_type = 'relative'
GROUP BY cohort_value
ORDER BY "Repeat Rate %" DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Repeat Rate %", "M1 Ret %"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 60
      },
      {
        "columns": ["M0 Rev", "M1 Rev", "M2 Rev", "M3 Rev", "M4 Rev", "M5 Rev", "M6 Rev"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 150
      }
    ]
  }
}
```

```json metabase-pos
{
  "row": 12,
  "col": 0,
  "size_x": 18,
  "size_y": 9
}
```

---

#### 📝 Text: Full data table — all metrics × all periods (use for calendar window or detailed drill-down)

# Full data table — all metrics, all periods

```json metabase-pos
{
  "row": 21,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

#### ❓ Question: Cohort Data Table

Full long-format table — all metrics, all periods. Use with window_type=calendar to see wall-clock trends. Sortable by any column.

```sql
SELECT
    cohort_value                          AS "Cohort",
    period_n                              AS "Period",
    cohort_size                           AS "Size",
    active                                AS "Active",
    ROUND(retention_pct, 1)               AS "Retention %",
    revenue                               AS "Revenue",
    ROUND(revenue_retention * 100, 1)     AS "Rev Retention %",
    repeat_customers                      AS "Repeat Buyers",
    ROUND(repeat_rate, 1)                 AS "Repeat Rate %"
FROM main_marts.mart_cohort_retention
WHERE 1=1
  [[AND {{cohort_dimension}}]]
  [[AND {{window_type}}]]
ORDER BY cohort_value, period_n
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Retention %"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      },
      {
        "columns": ["Repeat Rate %"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 60
      }
    ],
    "column_settings": {
      "Revenue": {
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
  "row": 22,
  "col": 0,
  "size_x": 18,
  "size_y": 10
}
```
