---
primary_scope: none
scope_indicator: "[Finance]"
layer: L2
uses_concepts: [mart_cashflow_budget_vs_actual, mart_cashflow_forecast, mart_cashflow_reserve_status, mart_cash_surplus_allocation, dim_cash_allocation_policy, fact_cashflow_budget]
last_modified: 2026-07-04
---

# Finance Budget vs Actual Blueprint

Dashboard ngân sách vs thực tế dòng tiền � kế hoạch chi/thu theo cashflow_line, dự báo s� dư quỹ, theo dõi quỹ dự phòng và phân b�" thặng dư. Phase-04 extension của Finance Cashflow (phase-03). Dành cho CFO/Kế toán trong MBR hàng tháng và lập kế hoạch tài chính.

## Deploy Command

```bash
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md
```

## Prerequisites

1. Phase 04 dbt models �ã materialized: `fact_cashflow_budget`, `mart_cashflow_budget_vs_actual`, `mart_cashflow_forecast`, `mart_cashflow_reserve_status`, `mart_cash_surplus_allocation`, `dim_cash_allocation_policy`
2. Stop Metabase �  `python scripts/provisioning/bootstrap_serving_views.py` �  start Metabase (expose new marts to DuckDB serving layer)
3. Admin �  Databases �  Sapo �  **Sync database schema now**
4. Tra field_id sau sync qua `/api/table/:id/query_metadata` � cập nhật 3 placeholder dư�:i �ây r�i redeploy:

| Placeholder | Field |
|-------------|-------|
| `2482` | `main_marts.mart_cashflow_budget_vs_actual.period_month` |
| `2481` | `main_marts.mart_cashflow_budget_vs_actual.cashflow_line` |
| `2491` | `main_marts.mart_cashflow_forecast.period_month` |

5. Lần deploy �ầu (v�:i placeholder) tạo filter dạng text input � functional nhưng relative-date sẽ không hoạt ��"ng. Sau khi cập nhật field_id thật: `node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md`

## Semantic Contract

Không có `scope_sales` / `scope_retail` � báo cáo GL cashflow. Tất cả queries draw từ marts finance phase-04. `is_internal_transfer` �ã �ược lọc �x mart layer � không cần thêm trong blueprint SQL.

---

## 📂 Collection: Finance

### 🖥️ Dashboard: Finance Budget vs Actual

**Description**: Ngân sách vs thực tế dòng tiền � kế hoạch per cashflow_line, variance, dự báo s� dư quỹ, quỹ dự phòng và phân b�" thặng dư. Phase-04 Finance. MBR hàng tháng.

> **Database:** Sapo

---

#### Filter: Kỳ (Period Month)

```json metabase-filter
{
  "slug": "period_month",
  "type": "date/all-options",
  "default": "thismonth",
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
    '�x& Kỳ này: ' || strftime(p_start, '%d/%m/%Y') || ' � ' || strftime(p_end, '%d/%m/%Y') ||
    '  ·  Kỳ trư�:c: ' ||
    strftime((p_start - (n_months::VARCHAR || ' months')::INTERVAL)::DATE, '%d/%m/%Y') ||
    ' � ' || strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### �x� Text: A � KPI Scorecard Heading

## Ngân sách vs Thực tế � T�"ng hợp kỳ

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A1 � Tong ke hoach

T�"ng kế hoạch (inflow + outflow) theo kỳ filter. Dùng làm anchor �Ồ �ánh giá quy mô ngân sách.

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
{ "row": 3, "col": 0, "size_x": 5, "size_y": 4 }
```

#### ❓ Question: A1 � Tong thuc te

T�"ng thực tế theo kỳ filter. So sánh v�:i kế hoạch �  xem thực hi�!n.

```sql
SELECT COALESCE(SUM(actual_amount), 0) AS "Thuc_te"
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
{ "row": 3, "col": 5, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: A1 � Chenh lech

Variance = actual �� kế hoạch. Dương (+) = thu vượt hoặc chi tiết ki�!m. �m (��) = thu hụt hoặc b�"i chi.

```sql
SELECT COALESCE(SUM(actual_amount) - SUM(planned_amount), 0) AS "Chênh l�!ch"
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
      "Chênh l�!ch": {
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

#### ❓ Question: A1 � Ti le thuc hien

Attainment % = actual / kế hoạch � 100. Tính lại từ SUM �Ồ tránh trung bình per-row.

```sql
SELECT ROUND(
    COALESCE(SUM(actual_amount), 0) * 100.0
    / NULLIF(SUM(planned_amount), 0), 1
) AS "T�0 l�! thực hi�!n %"
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
      "T�0 l�! thực hi�!n %": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 13, "size_x": 5, "size_y": 4 }
```

#### �x� Text: A2 � Bar Chart Heading

## Budget vs Actual theo Cashflow Line

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A2 � Budget vs Actual theo Cashflow Line

Grouped bar � kế hoạch vs thực tế per cashflow_line. Aggregate across directions (inflow + outflow) cho cái nhìn t�"ng thỒ quy mô per line. Filter theo kỳ và line dropdown.

```sql
SELECT
    cashflow_line                   AS "Cashflow Line",
    SUM(planned_amount)             AS "Kế hoạch",
    SUM(actual_amount)              AS "Thực tế"
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
    "graph.dimensions": ["Cashflow Line"],
    "graph.metrics": ["Kế hoạch", "Thực tế"],
    "series_settings": {
      "Kế hoạch": { "color": "#88BDE6" },
      "Thực tế":  { "color": "#509EE3" }
    },
    "stackable.stack_type": null,
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Kế hoạch": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Thực tế":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 7 }
```

#### �x� Text: A3 � Variance Table Heading

## Bảng chênh l�!ch chi tiết � Kế hoạch, Thực tế, Variance

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A3 � Bang chenh lech chi tiet

Variance table per (cashflow_line, direction). Conditional formatting: variance_pct < ��10 �  �ỏ (b�"i chi / hụt thu), > 10 �  xanh (tiết ki�!m / vượt thu). Sorted by abs(variance_pct) desc �Ồ n�"i bật lines l�!ch nhất.

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
{ "row": 16, "col": 0, "size_x": 18, "size_y": 9 }
```

#### �x� Text: A4 � Forecast Heading

## Dự báo s� dư quỹ � Thực tế + Kế hoạch tương lai

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: A4 � Du bao so du quy

Dual-series line � "S� dư thực tế" (actual, màu xanh �ậm) + "Dự báo s� dư" (projected, màu xanh nhạt). Các tháng thực tế có projected_balance=NULL �  series projected tự nhiên ch�0 hiỒn th�9 từ tháng anchor tr�x �i. No dashboard filter � cửa s�" tự ��"ng bao g�m toàn b�" l�9ch sử actual + tương lai có budget.

```sql
SELECT
    period_month            AS "Tháng",
    actual_balance          AS "S� dư thực tế",
    projected_balance       AS "Dự báo s� dư"
FROM main_marts.mart_cashflow_forecast
WHERE row_type IN ('actual', 'forecast')
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Tháng"],
    "graph.metrics": ["S� dư thực tế", "Dự báo s� dư"],
    "series_settings": {
      "S� dư thực tế": { "color": "#509EE3", "line.marker_enabled": true },
      "Dự báo s� dư":  { "color": "#84BB4C", "line.marker_enabled": false }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "S� dư thực tế": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Dự báo s� dư":  { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
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
         THEN '�a�️ DỮ LI� U C� TH� CŨ � '
         ELSE ''
    END
    || '�x"� BvA m�:i nhất: ' || strftime(MAX(period_month), '%m/%Y')
    || '  ·  S� dòng ngân sách: ' || COUNT(*)::VARCHAR
    AS "Đ�" tươi dữ li�!u"
FROM main_marts.mart_cashflow_budget_vs_actual
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```

#### �x� Text: Source Freshness BvA

**Source:** main_marts.mart_cashflow_budget_vs_actual · main_marts.mart_cashflow_forecast · **Cadence:** monthly (dbt seed từ Google Sheet + MISA GL actuals) · **Scope:** Tất cả cashflow_lines có ngân sách hoặc thực tế; is_internal_transfer �ã exclude �x mart layer · **Caveats:** Các lines không có budget �  coverage='actual_only'; tháng tương lai không có actual �  coverage='budget_only'; attainment_pct=NULL khi planned_amount=0
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
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ ⚠️'
         ELSE '✅ Dữ liệu cập nhật: ' || strftime(MAX(period_month), '%Y-%m')
    END AS status
FROM main_marts.mart_cash_surplus_allocation
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### �x� Text: B1 � Free Cash Heading

## Tiền mặt tự do � Thặng dư sau phân b�" tất cả bucket

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B1 � Tien mat tu do

Scalar � allocated_amount cho bucket='free_cash' của kỳ m�:i nhất trong mart_cash_surplus_allocation. Đây là phần tiền còn lại sau khi �ã phân b�" cho tất cả reserve bucket theo chính sách Waterfall.

```sql
SELECT COALESCE(SUM(allocated_amount), 0) AS "Tiền mặt tự do"
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
      "Tiền mặt tự do": {
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

#### �x� Text: B2 � Reserve Status Heading

## Tình trạng các quỹ dự phòng � Tiến ��" tích lũy

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B2 � Tinh trang du phong

Table � tiến ��" tích lũy từng hạng mục reserve: �ã tích lũy, mục tiêu, % hoàn thành, còn thiếu, cần thêm m�i tháng, hạn chót. Sorted by pct_done asc �Ồ ưu tiên hiỒn th�9 các hạng mục lag nhất.

```sql
SELECT
    item_label              AS "Hạng mục",
    accumulated_plan        AS "Đã tích lũy",
    item_target             AS "Mục tiêu",
    pct_done                AS "% Hoàn thành",
    gap_remaining           AS "Còn thiếu",
    required_monthly_adj    AS "Cần thêm/tháng",
    target_month            AS "Hạn chót"
FROM main_marts.mart_cashflow_reserve_status
ORDER BY COALESCE(pct_done, 0) ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Đã tích lũy":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Mục tiêu":         { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Còn thiếu":        { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Cần thêm/tháng":   { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "% Hoàn thành":     { "number_style": "percent", "decimals": 1, "scale": 0.01 }
    },
    "table.column_formatting": [
      {
        "columns": ["% Hoàn thành"],
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

#### �x� Text: B3 � Allocation History Heading

## Phân b�" thặng dư tiền mặt theo tháng � Waterfall theo bucket

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B3 � Phan bo thang du theo bucket

Stacked bar � allocated_amount per bucket per tháng. Màu sắc phân bi�!t từng bucket (tax_reserve, equipment_reserve, free_cash, ⬦). HiỒn th�9 toàn b�" l�9ch sử không filter � thấy xu hư�:ng phân b�" và tháng nào thặng dư nhiều/ít.

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

#### �x� Text: B4 � Policy Log Heading

## L�9ch sử chính sách phân b�" � Waterfall rules

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: B4 � Chinh sach phan bo

Table � toàn b�" l�9ch sử policy (bao g�m cả �ã hết hi�!u lực). Không filter � �ây là audit log của các lần thay ��"i quy tắc phân b�". Sorted by priority asc, effective_from desc �Ồ thấy policy hi�!n hành trư�:c.

```sql
SELECT
    priority        AS "Ưu tiên",
    bucket          AS "Bucket",
    rule_type       AS "Loại quy tắc",
    value           AS "Giá tr�9",
    effective_from  AS "Từ ngày",
    effective_to    AS "Đến ngày",
    notes           AS "Ghi chú"
FROM main_marts.dim_cash_allocation_policy
ORDER BY priority ASC, effective_from DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Giá tr�9": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
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
    '�x"� Reserve items: ' || (
        SELECT COUNT(*)::VARCHAR FROM main_marts.mart_cashflow_reserve_status
    ) || ' mục' ||
    '  ·  Chính sách hi�!u lực từ: ' || COALESCE(
        strftime(MAX(effective_from), '%d/%m/%Y'),
        'N/A'
    )
    AS "Đ�" tươi dữ li�!u"
FROM main_marts.dim_cash_allocation_policy
WHERE effective_to IS NULL
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```

#### �x� Text: Source Freshness Reserve

**Source:** main_marts.mart_cashflow_reserve_status · main_marts.mart_cash_surplus_allocation · main_marts.dim_cash_allocation_policy · **Cadence:** monthly (dbt seed từ Google Sheet ALLOCATION_POLICY + BUDGET_ITEMS) · **Scope:** item_type='reserve' cho B2; tất cả surplus allocation buckets cho B3; toàn b�" l�9ch sử policy cho B4 · **Caveats:** dim_cash_allocation_policy là append-only � dòng effective_to IS NULL = policy �ang áp dụng; value=NULL v�:i rule_type='from_plan' hoặc 'remainder' là bình thường
<!-- text-id:source-freshness-reserve -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

