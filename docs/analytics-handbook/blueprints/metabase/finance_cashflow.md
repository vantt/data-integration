---
primary_scope: none
scope_indicator: "[Finance]"
layer: L2
uses_concepts: [fact_cash_movement, fact_account_balance_monthly, dim_gl_account, cashflow_line, is_internal_transfer]
last_modified: 2026-07-03
---

# Finance Cashflow Blueprint

Dashboard dong tien van hanh (operational cashflow) — so du quy, dong thu, dong chi, va co cau chi tieu theo cashflow_line. Danh cho CFO/Ke toan trong MBR hang thang. Phase-03: deployable against fact_cash_movement + fact_account_balance_monthly.

## Deploy Command

```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow.md
```

## Prerequisites

1. `main_marts.fact_cash_movement` materialized (Dagster asset run)
2. `main_marts.fact_account_balance_monthly` materialized — OR fallback derivation from fact_cash_movement (see Card 1 SQL notes)
3. Stop Metabase → run `python bootstrap_serving_views.py` → restart Metabase (required after new mart)
4. After deploy: sync Metabase database schema, then look up `field_id` for `period_month` column in `fact_cash_movement` via `/api/table/:id/query_metadata` and update `field_id` in the filter block below, then redeploy

## Segmentation Scope

No `scope_sales` / `scope_retail` — this is a GL-level cashflow report. All queries draw from `main_marts.fact_cash_movement` and `main_marts.fact_account_balance_monthly`.

`WHERE NOT is_internal_transfer` is mandatory on all thu/chi cards (June recon: excludes 299M internal transfer; net thu 464.4M / chi 434.0M / net +30.4M).

## 📂 Collection: Finance

### 🖥️ Dashboard: Finance Cashflow

**Description**: Dong tien van hanh — so du quy, thu chi, va co cau chi tieu theo cashflow_line. MoM trend. Danh cho CFO/Ke toan trong MBR hang thang.

> **Database:** Sapo

---

#### Filter: Period

```json metabase-filter
{
  "slug": "period_month",
  "type": "date/all-options",
  "default": "past6months",
  "field_id": 2369
}
```

---

### 📑 Tab: Tong quan

#### ❓ Question: Chu ky bao cao

```sql
WITH filter_bounds AS (
    SELECT MIN(period_month) AS p_start, MAX(period_month) AS p_end
    FROM main_marts.fact_cash_movement
    WHERE 1=1
      [[AND {{period_month}}]]
),
period_adj AS (
    SELECT
        date_trunc('month', p_start)::DATE AS p_start,
        (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE AS p_end,
        (p_end - p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER) * 12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start, '%d/%m/%Y') || ' – ' || strftime(p_end, '%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime((p_start - (n_months::VARCHAR || ' months')::INTERVAL)::DATE, '%d/%m/%Y') ||
    ' – ' || strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: KPI Heading

## So du va dong tien — ket qua ky nay

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: So du quy cuoi ky

Hero scalar — tong so du tat ca tai khoan tien mat cuoi ky. Source: fact_account_balance_monthly WHERE is_cash. Fallback: MAX(running_balance) per cash_account per period in fact_cash_movement if fact_account_balance_monthly not yet materialized.

```sql
-- period_bounds derives date range via fact_cash_movement (field filter only injects into that table).
-- fact_account_balance_monthly is filtered by derived p_to (closing balance at end of period).
WITH period_bounds AS (
    SELECT MIN(period_month) AS p_from, MAX(period_month) AS p_to
    FROM main_marts.fact_cash_movement
    WHERE 1=1
      [[AND {{period_month}}]]
)
SELECT COALESCE(SUM(b.closing_balance), 0) AS "So du quy cuoi ky"
FROM main_marts.fact_account_balance_monthly b
JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
CROSS JOIN period_bounds
WHERE g.is_cash = true
  AND b.period_month = period_bounds.p_to
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "So du quy cuoi ky": {
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
{ "row": 3, "col": 0, "size_x": 5, "size_y": 4 }
```

#### ❓ Question: Dong tien rong

Supporting KPI — tong inflow tru outflow, exclude internal transfers.

```sql
SELECT
    COALESCE(SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END), 0)
  - COALESCE(SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END), 0)
    AS "Dong tien rong"
FROM main_marts.fact_cash_movement
WHERE NOT is_internal_transfer
  [[AND {{period_month}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Dong tien rong": {
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
{ "row": 3, "col": 5, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Tong thu

Supporting KPI — tong inflow, exclude internal transfers.

```sql
SELECT COALESCE(SUM(amount), 0) AS "Tong thu"
FROM main_marts.fact_cash_movement
WHERE direction = 'inflow'
  AND NOT is_internal_transfer
  [[AND {{period_month}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong thu": {
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
{ "row": 3, "col": 9, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Tong chi

Supporting KPI — tong outflow, exclude internal transfers.

```sql
SELECT COALESCE(SUM(amount), 0) AS "Tong chi"
FROM main_marts.fact_cash_movement
WHERE direction = 'outflow'
  AND NOT is_internal_transfer
  [[AND {{period_month}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong chi": {
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
{ "row": 3, "col": 13, "size_x": 5, "size_y": 4 }
```

#### 📝 Text: Waterfall Heading

## Cau truc dong tien — tu so du dau ky den cuoi ky

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Cashflow Waterfall

Waterfall — so du dau ky → cac cashflow_line net (inflow+, outflow−) → so du cuoi ky. Exclude internal transfers. Rows derived by UNION of opening balance, per-line net movements, and closing balance.

NOTE: Metabase `waterfall` display IS supported (catalog row 17, display: "waterfall"). Used here with same pattern as finance_pl.md "Revenue Waterfall".

```sql
-- period_bounds derives date range via fact_cash_movement (field filter injects only into that table).
-- opening: balance at p_from (start of period), closing: balance at p_to (end of period).
-- movements: net signed_amount across full p_from..p_to range.
WITH period_bounds AS (
    SELECT MIN(period_month) AS p_from, MAX(period_month) AS p_to
    FROM main_marts.fact_cash_movement
    WHERE 1=1
      [[AND {{period_month}}]]
),
opening AS (
    SELECT
        0                                   AS sort_order,
        'So du dau ky'                      AS "Khoan muc",
        COALESCE(SUM(b.opening_balance), 0) AS "Gia tri"
    FROM main_marts.fact_account_balance_monthly b
    JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
    CROSS JOIN period_bounds
    WHERE g.is_cash = true
      AND b.period_month = period_bounds.p_from
),
movements AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY cashflow_line) + 1 AS sort_order,
        cashflow_line                                   AS "Khoan muc",
        SUM(signed_amount)                              AS "Gia tri"
    FROM main_marts.fact_cash_movement
    CROSS JOIN period_bounds
    WHERE NOT is_internal_transfer
      AND period_month BETWEEN period_bounds.p_from AND period_bounds.p_to
    GROUP BY cashflow_line
    HAVING SUM(signed_amount) <> 0
),
closing AS (
    SELECT
        999                                  AS sort_order,
        'So du cuoi ky'                      AS "Khoan muc",
        COALESCE(SUM(b.closing_balance), 0)  AS "Gia tri"
    FROM main_marts.fact_account_balance_monthly b
    JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
    CROSS JOIN period_bounds
    WHERE g.is_cash = true
      AND b.period_month = period_bounds.p_to
)
SELECT "Khoan muc", "Gia tri"
FROM (
    SELECT sort_order, "Khoan muc", "Gia tri" FROM opening
    UNION ALL
    SELECT sort_order, "Khoan muc", "Gia tri" FROM movements
    UNION ALL
    SELECT sort_order, "Khoan muc", "Gia tri" FROM closing
) t
ORDER BY sort_order
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 7 }
```

#### 📝 Text: Trend Heading

## Xu huong so du va dong tien theo thang

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: So du quy theo thang

Line chart — so du tai khoan tien mat (SUM closing_balance WHERE is_cash) theo period_month. Fixed 13-month window cho xu huong toan canh. Fallback if fact_account_balance_monthly missing: derive from MAX(running_balance) per cash_account per period_month in fact_cash_movement.

```sql
-- Primary
SELECT
    b.period_month                AS "Thang",
    SUM(b.closing_balance)        AS "So du cuoi ky"
FROM main_marts.fact_account_balance_monthly b
JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
WHERE g.is_cash = true
  AND b.period_month >= date_trunc('month', current_date) - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["So du cuoi ky"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "So du cuoi ky": {
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
{ "row": 16, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: Thu chi theo thang (Combo)

Combo — SUM(amount) thu (bar xanh) va chi (bar do) theo period_month + net (line). Exclude internal transfers. Fixed 13-month window.

```sql
SELECT
    period_month                                                               AS "Thang",
    SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END)               AS "Tong thu",
    SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END)               AS "Tong chi",
    SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END)
  - SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END)               AS "Dong tien rong"
FROM main_marts.fact_cash_movement
WHERE NOT is_internal_transfer
  AND period_month >= date_trunc('month', current_date) - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Tong thu", "Tong chi", "Dong tien rong"],
    "series_settings": {
      "Tong thu":      { "display": "bar",  "color": "#84BB4C" },
      "Tong chi":      { "display": "bar",  "color": "#EF8C8C" },
      "Dong tien rong": { "display": "line", "color": "#509EE3" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Tong thu":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Tong chi":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Dong tien rong": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 22, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: Do tuoi du lieu

```sql
SELECT
    CASE WHEN MAX(period_month) < date_trunc('month', current_date) - INTERVAL '1 month'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — '
         ELSE ''
    END
    || '🕐 Kỳ mới nhất: ' || strftime(MAX(period_month), '%m/%Y')
    || '  ·  Số bút toán: ' || COUNT(*)::VARCHAR
    AS "Độ tươi dữ liệu"
FROM main_marts.fact_cash_movement
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Source Freshness Tong quan

**Source:** main_marts.fact_cash_movement + main_marts.fact_account_balance_monthly · **Cadence:** monthly (MISA GL) · **Scope:** All GL cash accounts (dim_gl_account.is_cash=true) · **Caveats:** is_internal_transfer=true transactions excluded from thu/chi totals (June recon: 299M excluded)
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: Chi tiet dong tien

#### ❓ Question: Chu ky bao cao

```sql
WITH filter_bounds AS (
    SELECT MIN(period_month) AS p_start, MAX(period_month) AS p_end
    FROM main_marts.fact_cash_movement
    WHERE 1=1
      [[AND {{period_month}}]]
),
period_adj AS (
    SELECT
        date_trunc('month', p_start)::DATE AS p_start,
        (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE AS p_end,
        (p_end - p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER) * 12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start, '%d/%m/%Y') || ' – ' || strftime(p_end, '%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime((p_start - (n_months::VARCHAR || ' months')::INTERVAL)::DATE, '%d/%m/%Y') ||
    ' – ' || strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Pivot Heading

## Co cau dong tien theo cashflow_line va thang

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Pivot cashflow line x thang

Crosstab — rows = (cashflow_line, direction), columns = period_month (MM/YYYY), values = SUM(amount). Exclude internal transfers. Uses DuckDB native PIVOT to avoid Metabase v0.60.x pivot result_metadata off-by-one bug (pivot-grouping column shifts all column types on every execution).

```sql
-- DuckDB native PIVOT: crosstab cashflow_line x direction x month.
-- Field filter injects into main_marts.fact_cash_movement (fully qualified) — no Binder Error.
-- display:table avoids Metabase pivot result_metadata corruption bug (v0.60.x).
PIVOT (
    SELECT
        cashflow_line                       AS "Cashflow Line",
        direction                           AS "Huong",
        strftime(period_month, '%m/%Y')     AS "Thang",
        amount
    FROM main_marts.fact_cash_movement
    WHERE NOT is_internal_transfer
      [[AND {{period_month}}]]
)
ON "Thang"
USING SUM(amount)
GROUP BY "Cashflow Line", "Huong"
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Chi Heading

## Co cau chi tieu — hang muc nao chiem nhieu nhat?

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Co cau chi theo cashflow_line

Horizontal bar — SUM(amount) outflow theo cashflow_line, sorted desc. Exclude internal transfers. Color-coded bang series mau.

```sql
SELECT
    cashflow_line              AS "Cashflow Line",
    SUM(amount)                AS "Tong chi"
FROM main_marts.fact_cash_movement
WHERE direction = 'outflow'
  AND NOT is_internal_transfer
  [[AND {{period_month}}]]
GROUP BY 1
HAVING SUM(amount) > 0
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Cashflow Line"],
    "graph.metrics": ["Tong chi"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#F2A86F", "#F9D45C", "#EF8C8C", "#98D9D9"],
    "graph.x_axis.title_text": "Tong chi (VND)",
    "column_settings": {
      "Tong chi": {
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
{ "row": 13, "col": 0, "size_x": 18, "size_y": 7 }
```

#### ❓ Question: Do tuoi du lieu

```sql
SELECT
    CASE WHEN MAX(period_month) < date_trunc('month', current_date) - INTERVAL '1 month'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — '
         ELSE ''
    END
    || '🕐 Kỳ mới nhất: ' || strftime(MAX(period_month), '%m/%Y')
    || '  ·  Số bút toán: ' || COUNT(*)::VARCHAR
    AS "Độ tươi dữ liệu"
FROM main_marts.fact_cash_movement
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Source Freshness Chi tiet

**Source:** main_marts.fact_cash_movement · **Cadence:** monthly (MISA GL) · **Scope:** direction='outflow' AND NOT is_internal_transfer · **Caveats:** cashflow_line values come from MISA account mapping; unmapped accounts appear as NULL
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

---

## Phase-04 Extensions (not yet deployable)

> These cards require `fact_cashflow_budget` mart (not yet built). DO NOT include in deploy until mart is materialized and bootstrap_serving_views.py re-run.

### Card 3 Budget Columns (Pivot table enhancement)

Add budget column to pivot: join `main_marts.fact_cashflow_budget` ON (cashflow_line, period_month) to show actual vs budget vs variance columns per period_month. Requires `fact_cashflow_budget` with columns: cashflow_line, period_month, budget_amount.

### Card 4 Forecast Dashed Line (So du theo thang)

Add a forecast series to "So du quy theo thang" line chart: dashed line from `fact_cashflow_budget` aggregated as projected cumulative balance. Metabase workaround: UNION actual + forecast in SQL with a `series_type` column, then use `series_settings` to style forecast series differently (dashed not natively supported — use lighter color + note in card description).

Both extensions blocked on: `fact_cashflow_budget` mart design + Dagster asset + bootstrap step.
