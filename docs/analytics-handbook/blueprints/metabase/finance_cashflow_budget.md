---
primary_scope: none
scope_indicator: "[Finance]"
layer: L2
uses_concepts: [mart_cashflow_budget_vs_actual, mart_cashflow_forecast, mart_cashflow_reserve_status, mart_cash_surplus_allocation, dim_cash_allocation_policy, fact_cashflow_budget]
last_modified: 2026-07-04
---

# Finance Budget vs Actual Blueprint

Dashboard ngan sach vs thuc te dong tien: ke hoach chi/thu theo cashflow_line, du bao so du quy, theo doi quy du phong va phan bo thang du. Phase-04 extension cua Finance Cashflow (phase-03). Danh cho CFO/Ke toan trong MBR hang thang va lap ke hoach tai chinh.

## Deploy Command

```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md
```

## Prerequisites

1. Phase 04 dbt models materialized: `fact_cashflow_budget`, `mart_cashflow_budget_vs_actual`, `mart_cashflow_forecast`, `mart_cashflow_reserve_status`, `mart_cash_surplus_allocation`, `dim_cash_allocation_policy`
2. Stop Metabase -> `python scripts/provisioning/bootstrap_serving_views.py` -> start Metabase (expose new marts to DuckDB serving layer)
3. Admin -> Databases -> Sapo -> **Sync database schema now**
4. Verify field_id via `/api/table/:id/query_metadata` — live values confirmed below:

| Placeholder | Field |
|-------------|-------|
| `2482` | `main_marts.mart_cashflow_budget_vs_actual.period_month` |
| `2481` | `main_marts.mart_cashflow_budget_vs_actual.cashflow_line` |
| `2491` | `main_marts.mart_cashflow_forecast.period_month` |

5. First deploy creates text-input filters (functional). After setting real field_ids above: redeploy for date/string pickers.

## Semantic Contract

No `scope_sales` / `scope_retail` — this is GL cashflow reporting. All queries draw from finance phase-04 marts. `is_internal_transfer` is already filtered at mart layer — no need in blueprint SQL.

## SQL Column Alias Convention

All column aliases use ASCII identifiers to avoid encoding issues with Metabase visualization_settings JSON keys. Vietnamese labels appear in card titles and descriptions only.

---

## 📂 Collection: Finance

### 🖥️ Dashboard: Finance Budget vs Actual

**Description**: Ngan sach vs thuc te dong tien: ke hoach per cashflow_line, variance, du bao so du quy, quy du phong va phan bo thang du. Phase-04 Finance. MBR hang thang.

> **Database:** Sapo

---

#### Filter: Ky (Period Month)

```json metabase-filter
{
  "slug": "period_month",
  "type": "date/all-options",
  "default": "past1months",
  "field_id": "2482"
}
```

#### Filter: Cashflow Line

```json metabase-filter
{
  "slug": "cashflow_line",
  "type": "string/=",
  "field_id": "2481"
}
```

---

### 📑 Tab: Budget vs Actual

#### ❓ Question: Chu ky bao cao

Text scalar hien thi ky bao cao hien tai va ky truoc do. Tinh n_months tu diff cua period filter.

```sql
WITH filter_bounds AS (
    SELECT MIN(period_month) AS p_start, MAX(period_month) AS p_end
    FROM main_marts.mart_cashflow_budget_vs_actual
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
    'Ky nay: ' || strftime(p_start, '%d/%m/%Y') || ' - ' || strftime(p_end, '%d/%m/%Y') ||
    '  |  Ky truoc: ' ||
    strftime((p_start - (n_months::VARCHAR || ' months')::INTERVAL)::DATE, '%d/%m/%Y') ||
    ' - ' || strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu_ky"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: A - KPI Scorecard Heading

## Ngan sach vs Thuc te - Tong hop ky

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A1 - Tong ke hoach

Tong ke hoach (inflow + outflow) theo ky filter. Dung lam anchor de danh gia quy mo ngan sach.

```sql
SELECT COALESCE(SUM(planned_amount), 0) AS "Ke_hoach"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE 1=1
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Ke_hoach\"]": {
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
{ "row": 3, "col": 0, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: A1 - Tong thuc te

Tong thuc te CHI trong pham vi ke hoach (coverage='both' — line co ca ke hoach va thuc te). Budget hien chi phu 5/15 cashflow_line; loai actual_only de so sanh dung cap voi "Tong ke hoach". Xem card "A1 - Ngoai ke hoach" cho phan thuc te khong co budget.

```sql
SELECT COALESCE(SUM(actual_amount), 0) AS "Thuc_te"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE coverage = 'both'
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Thuc_te\"]": {
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
{ "row": 3, "col": 4, "size_x": 3, "size_y": 4 }
```

#### ❓ Question: A1 - Chenh lech

Variance = actual - ke hoach, CHI trong pham vi ke hoach (coverage='both'). Duong (+) = thu vuot hoac chi tiet kiem. Am (-) = thu hut hoac boi chi.

```sql
SELECT COALESCE(SUM(actual_amount) - SUM(planned_amount), 0) AS "Chenh_lech"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE coverage = 'both'
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Chenh_lech\"]": {
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
{ "row": 3, "col": 7, "size_x": 3, "size_y": 4 }
```

#### ❓ Question: A1 - Ti le thuc hien

Attainment % = actual / ke hoach * 100, CHI trong pham vi ke hoach (coverage='both') — line khong co budget se lam attainment vo nghia neu tinh chung. Tinh lai tu SUM de tranh trung binh per-row.

```sql
SELECT ROUND(
    COALESCE(SUM(actual_amount), 0) * 100.0
    / NULLIF(SUM(planned_amount), 0), 1
) AS "Ti_le_pct"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE coverage = 'both'
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Ti_le_pct\"]": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: A1 - Ngoai ke hoach

Tong thuc te cua cac cashflow_line KHONG co trong budget sheet (coverage='actual_only') — Thue, tam ung, ton kho, noi bo, ... Tach rieng khoi "Tong thuc te" de tien khong bien mat khoi tam nhin dashboard. Card nay lon bat thuong so voi "Tong ke hoach" la tin hieu nen bo sung them line vao budget sheet (finance them dan qua thoi gian).

```sql
SELECT COALESCE(SUM(actual_amount), 0) AS "Ngoai_ke_hoach"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE coverage = 'actual_only'
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Ngoai_ke_hoach\"]": {
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
{ "row": 3, "col": 14, "size_x": 4, "size_y": 4 }
```

#### 📝 Text: A2 - Bar Chart Heading

## Budget vs Actual theo Cashflow Line

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A2 - Budget vs Actual theo Cashflow Line

Grouped bar: ke hoach vs thuc te per cashflow_line. Aggregate across directions (inflow + outflow) cho cai nhin tong the quy mo per line. Filter theo ky va line dropdown.

```sql
SELECT
    cashflow_line                   AS "Line",
    SUM(planned_amount)             AS "Ke_hoach",
    SUM(actual_amount)              AS "Thuc_te"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE 1=1
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
GROUP BY 1
HAVING SUM(planned_amount) > 0 OR SUM(actual_amount) > 0
ORDER BY SUM(planned_amount) DESC NULLS LAST
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Line"],
    "graph.metrics": ["Ke_hoach", "Thuc_te"],
    "series_settings": {
      "Ke_hoach": { "color": "#88BDE6" },
      "Thuc_te":  { "color": "#509EE3" }
    },
    "stackable.stack_type": null,
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "[\"name\",\"Ke_hoach\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Thuc_te\"]":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 7 }
```

#### 📝 Text: A3 - Variance Table Heading

## Bang chenh lech chi tiet - Ke hoach, Thuc te, Variance

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A3 - Bang chenh lech chi tiet

Variance table per (cashflow_line, direction). Coverage='both' (co ca ke hoach va thuc te) sap xep len truoc; coverage='actual_only' (khong co budget, variance/attainment se NULL) xuong duoi — phan biet ro line nao dang duoc lap ke hoach. Trong tung nhom, sort by abs(variance_pct) desc de noi bat lines lech nhat. Conditional formatting: variance_pct < -10 -> do (boi chi / hut thu), > 10 -> xanh (tiet kiem / vuot thu).

```sql
SELECT
    cashflow_line           AS "Line",
    direction               AS "Dir",
    coverage                AS "Coverage",
    planned_amount          AS "Ke_hoach",
    actual_amount           AS "Thuc_te",
    variance_amount         AS "Chenh_lech",
    variance_pct            AS "Pct_CL",
    attainment_pct          AS "Pct_TH"
FROM main_marts.mart_cashflow_budget_vs_actual
WHERE 1=1
  [[AND {{period_month}}]]
  [[AND {{cashflow_line}}]]
ORDER BY
    CASE coverage WHEN 'both' THEN 0 ELSE 1 END ASC,
    ABS(COALESCE(variance_pct, 0)) DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"Ke_hoach\"]":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Thuc_te\"]":   { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Chenh_lech\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Pct_CL\"]":    { "number_style": "percent", "decimals": 1, "scale": 0.01 },
      "[\"name\",\"Pct_TH\"]":    { "number_style": "percent", "decimals": 1, "scale": 0.01 }
    }
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: A4 - Forecast Heading

## Du bao so du quy - Thuc te + Ke hoach tuong lai

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A4 - Du bao so du quy

Dual-series line: "So_du_thuc_te" (actual, mau xanh dam) + "Du_bao_so_du" (projected, mau xanh nhat). Cac thang thuc te co projected_balance=NULL -> series projected tu nhien chi hien thi tu thang anchor tro di. No dashboard filter — cua so tu dong bao gom toan bo lich su actual + tuong lai co budget.

```sql
SELECT
    period_month            AS "Thang",
    actual_balance          AS "So_du_thuc_te",
    projected_balance       AS "Du_bao_so_du"
FROM main_marts.mart_cashflow_forecast
WHERE row_type IN ('actual', 'forecast')
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["So_du_thuc_te", "Du_bao_so_du"],
    "series_settings": {
      "So_du_thuc_te": { "color": "#509EE3", "line.marker_enabled": true },
      "Du_bao_so_du":  { "color": "#84BB4C", "line.marker_enabled": false }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "[\"name\",\"So_du_thuc_te\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Du_bao_so_du\"]":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 7 }
```

#### ❓ Question: Do tuoi du lieu BvA

```sql
SELECT
    CASE WHEN MAX(period_month) < date_trunc('month', current_date) - INTERVAL '1 month'
         THEN 'WARNING: Data may be stale'
         ELSE 'BvA latest: ' || strftime(MAX(period_month), '%m/%Y')
    END
    || '  |  Budget rows: ' || COUNT(*)::VARCHAR
    AS "Data_Freshness"
FROM main_marts.mart_cashflow_budget_vs_actual
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Source Freshness BvA

**Source:** main_marts.mart_cashflow_budget_vs_actual · main_marts.mart_cashflow_forecast · **Cadence:** monthly (dbt seed tu Google Sheet + MISA GL actuals) · **Scope:** Tat ca cashflow_lines co ngan sach hoac thuc te; is_internal_transfer da exclude o mart layer · **Caveats:** Cac lines khong co budget -> coverage='actual_only'; thang tuong lai khong co actual -> coverage='budget_only'; attainment_pct=NULL khi planned_amount=0 · Budget hien chi phu 5/15 cashflow_line — cac scorecard "Tong thuc te / Chenh lech / Ti le thuc hien" (A1) da scope theo coverage='both' de attainment % khong bi lech; phan thuc te ngoai budget hien rieng o card "A1 - Ngoai ke hoach" (coverage='actual_only'), khong bi mat khoi dashboard
<!-- text-id:source-freshness-bva -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: Reserve & Allocation

#### ❓ Question: Chu ky bao cao Reserve

```sql
SELECT
    CASE WHEN MAX(period_month) < date_trunc('month', current_date) - INTERVAL '1 month'
         THEN 'WARNING: Data may be stale'
         ELSE 'Allocation latest: ' || strftime(MAX(period_month), '%m/%Y')
    END AS "Status"
FROM main_marts.mart_cash_surplus_allocation
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: B1 - Free Cash Heading

## Tien mat tu do - Thang du sau phan bo tat ca bucket

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B1 - Tien mat tu do

Scalar: allocated_amount cho bucket='free_cash' cua ky moi nhat trong mart_cash_surplus_allocation. Day la phan tien con lai sau khi da phan bo cho tat ca reserve bucket theo chinh sach Waterfall.

```sql
SELECT COALESCE(SUM(allocated_amount), 0) AS "Free_cash"
FROM main_marts.mart_cash_surplus_allocation
WHERE bucket = 'free_cash'
  AND period_month = (
      SELECT MAX(period_month)
      FROM main_marts.mart_cash_surplus_allocation
  )
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Free_cash\"]": {
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
{ "row": 3, "col": 0, "size_x": 6, "size_y": 4 }
```

#### 📝 Text: B2 - Reserve Status Heading

## Tinh trang cac quy du phong - Tien do tich luy

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B2 - Tinh trang du phong

Table: tien do tich luy tung hang muc reserve: da tich luy, muc tieu, % hoan thanh, con thieu, can them moi thang, han chot. Sorted by pct_done asc de uu tien hien thi cac hang muc lag nhat.

```sql
SELECT
    cashflow_line       AS "Line",
    item_label          AS "Item",
    item_target         AS "Target",
    accumulated_plan    AS "Tich_luy",
    gap_remaining       AS "Con_thieu",
    pct_done            AS "Pct_done",
    required_monthly_adj AS "Can_them_thang"
FROM main_marts.mart_cashflow_reserve_status
ORDER BY pct_done ASC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"Target\"]":          { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Tich_luy\"]":        { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Con_thieu\"]":       { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Can_them_thang\"]":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "[\"name\",\"Pct_done\"]":        { "number_style": "percent", "decimals": 1, "scale": 0.01 }
    },
    "table.column_formatting": [
      {
        "columns": ["Pct_done"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 1,
        "mid_type": "custom",
        "mid_value": 0.5
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: B3 - Allocation History Heading

## Phan bo thang du tien mat theo thang - Waterfall theo bucket

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B3 - Phan bo thang du theo bucket

Stacked bar: allocated_amount per bucket per thang. Mau sac phan biet tung bucket (tax_reserve, equipment_reserve, free_cash, ...). Hien thi toan bo lich su khong filter — thay xu huong phan bo va thang nao thang du nhieu/it.

```sql
SELECT
    period_month,
    bucket,
    allocated_amount
FROM main_marts.mart_cash_surplus_allocation
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["period_month", "bucket"],
    "graph.metrics": ["allocated_amount"],
    "stackable.stack_type": "stacked",
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "[\"name\",\"allocated_amount\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: B4 - Policy Log Heading

## Lich su chinh sach phan bo - Waterfall rules

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B4 - Chinh sach phan bo

Table: toan bo lich su policy (bao gom ca da het hieu luc). Khong filter — day la audit log cua cac lan thay doi quy tac phan bo. Sorted by priority asc, effective_from desc de thay policy hien hanh truoc.

```sql
SELECT
    priority        AS "Priority",
    bucket          AS "Bucket",
    rule_type       AS "Rule_type",
    value           AS "Value",
    effective_from  AS "From_date",
    effective_to    AS "To_date",
    notes           AS "Notes"
FROM main_marts.dim_cash_allocation_policy
ORDER BY priority ASC, effective_from DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"Value\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 8 }
```

#### ❓ Question: Do tuoi du lieu Reserve

```sql
SELECT
    'Reserve items: ' || (
        SELECT COUNT(*)::VARCHAR FROM main_marts.mart_cashflow_reserve_status
    ) || ' muc' ||
    '  |  Policy from: ' || COALESCE(
        strftime(MAX(effective_from), '%d/%m/%Y'),
        'N/A'
    )
    AS "Data_Freshness"
FROM main_marts.dim_cash_allocation_policy
WHERE effective_to IS NULL
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Source Freshness Reserve

**Source:** main_marts.mart_cashflow_reserve_status · main_marts.mart_cash_surplus_allocation · main_marts.dim_cash_allocation_policy · **Cadence:** monthly (dbt seed tu Google Sheet ALLOCATION_POLICY + BUDGET_ITEMS) · **Scope:** item_type='reserve' cho B2; tat ca surplus allocation buckets cho B3; toan bo lich su policy cho B4 · **Caveats:** dim_cash_allocation_policy la append-only — dong effective_to IS NULL = policy dang ap dung; value=NULL voi rule_type='from_plan' hoac 'remainder' la binh thuong
<!-- text-id:source-freshness-reserve -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```
