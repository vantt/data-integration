---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - mart_cohort_retention
---

# 📘 Blueprint: Cohort Calendar Trend [Retail]

> **Target Collection:** `Marketing & Customers > 👥 Customer`
> **Role:** Marketing Manager, Customer Success
> **Archetype:** Trend — wall-clock retention across actual calendar months
> **Database:** Sapo

## Semantic Contract

> **Scope:** `scope_retail` — pre-filtered in mart (cohort_size ≥ 10, customer_type=RETAIL).
> **Source:** `mart_cohort_retention` where `window_type='calendar'` — period_n = 'YYYY-MM'.
> **Read:** How is each cohort (entry product / channel / etc.) performing *right now* vs. prior months?
> **Metric v1:** retention_pct · revenue. Margin = v2.

---

## 📂 Collection: Marketing & Customers > 👥 Customer

Calendar-view cohort retention — track wall-clock retention and revenue trends month by month for each entry cohort.

---

### 🖥️ Dashboard: Cohort Calendar Trend [Retail]

**Description**: Wall-clock retention view. Pick cohort_dimension to see how each cohort (product / channel / value band) retains customers over actual calendar months — not relative M+1/M+2 offsets. Use alongside Cohort Explorer for the relative view.

---

#### Filter: Cohort Dimension

```json metabase-filter
{
  "slug": "cohort_dimension",
  "type": "string/=",
  "field_id": 1793,
  "default": ["first_order_month"]
}
```

---


#### 📝 Text: Select cohort dimension to see wall-clock retention trends by entry path (product / channel / basket / value band)

# Retention trends by calendar month

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

#### ❓ Question: Retention % by Calendar Month

Monthly active retention rate for each cohort, plotted over actual calendar months. A downward trend means that cohort is losing customers over time; a flat or rising trend signals strong loyalty.

```sql
SELECT
    period_n                        AS "Month",
    cohort_value                    AS "Cohort",
    ROUND(retention_pct, 1)         AS "Retention %"
FROM main_marts.mart_cohort_retention
WHERE window_type = 'calendar'
  [[AND {{cohort_dimension}}]]
ORDER BY period_n, cohort_value
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Month", "Cohort"],
    "graph.metrics": ["Retention %"],
    "graph.y_axis.title_text": "Retention %",
    "graph.x_axis.title_text": "Calendar Month"
  }
}
```

```json metabase-pos
{
  "row": 1,
  "col": 0,
  "size_x": 18,
  "size_y": 9
}
```

---

#### 📝 Text: Revenue by calendar month — which cohorts sustain or grow spend over time?

# Revenue trends by calendar month

```json metabase-pos
{
  "row": 10,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

#### ❓ Question: Revenue by Calendar Month

Monthly revenue contribution per cohort over actual calendar months. Helps identify which entry cohorts drive sustained revenue vs. one-time spikes.

```sql
SELECT
    period_n                        AS "Month",
    cohort_value                    AS "Cohort",
    revenue                         AS "Revenue"
FROM main_marts.mart_cohort_retention
WHERE window_type = 'calendar'
  [[AND {{cohort_dimension}}]]
ORDER BY period_n, cohort_value
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Month", "Cohort"],
    "graph.metrics": ["Revenue"],
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": "Calendar Month",
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
  "row": 11,
  "col": 0,
  "size_x": 18,
  "size_y": 9
}
```
