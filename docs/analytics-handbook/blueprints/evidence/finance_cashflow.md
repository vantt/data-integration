---
primary_scope: none
scope_indicator: "[Finance]"
layer: L2
uses_concepts: [fact_cash_movement, fact_account_balance_monthly, dim_gl_account, cashflow_line, is_internal_transfer]
last_modified: 2026-07-03
---

# Finance Cashflow Blueprint (Evidence)

Evidence.dev port of [blueprints/metabase/finance_cashflow.md](../metabase/finance_cashflow.md).
Same domain metrics, same recon anchor — deployment mechanics and a few
chart types differ because Evidence has no field-filter widget, waterfall,
combo, pivot, or heatmap component (see Deviations below).

Implements the [design spec](../../designs/finance_cashflow.md) redesign
(2026-07-03): View 1 unchanged in intent (widened trend window 12→24 months,
added a YoY companion line near the hero KPI), View 2 "Xu hướng nhiều năm"
added as a 3rd tab — YTD-vs-YTD, full-history balance trend, annual thu/chi,
seasonality (CF7), and multi-year cashflow_line composition (CF5-CF7 in
[domains/finance.md](../../domains/finance.md)). View 2 self-gates on a
`years_observed` caveat banner since the MISA GL multi-year backfill
(2022→present) is still being ingested by a separate process — as of
2026-07-03 the mart only has 2025-01→2026-06 (6 months), so YoY/YTD/seasonality
cards render but show the low-confidence caveat until history lands.

## Deploy Notes

**Prerequisites**

1. `main_marts.fact_cash_movement` and `main_marts.fact_account_balance_monthly` materialized and exposed as serving views (verified present 2026-07-03).
2. Source `.sql` files in `evidence/sources/datalake/`: `fact_cash_movement.sql`, `fact_account_balance_monthly.sql`, `dim_gl_account.sql` (select only columns the page needs, per skill rule).
3. Page lives at `evidence/pages/finance-cashflow/index.md`.
4. Linked from `evidence/pages/index.md`.

**Deploy command**

```bash
docker compose restart evidence
```

## Deviations From the Metabase Blueprint

| Metabase feature | Evidence approximation | Why |
|---|---|---|
| `period_month` field filter (interactive) | `<Dropdown name=period_month>` (View 1) — scorecard/Sankey/waterfall-table/top-chi query templated with `${inputs.period_month.value}`, resolved client-side by the in-browser WASM DuckDB (no server round-trip, no rebuild needed to browse any month already in the build's data). Default = latest month (dropdown sorted DESC, first row auto-selected). View 1 trend charts still fixed 24-month rolling window (unaffected by the dropdown, by design — see in-page note). | Evidence has no server-side live filter widget like Metabase's field filter, but it does ship a client-side query engine that makes `${inputs.x}`-templated SQL genuinely interactive |
| `waterfall` display | `SankeyDiagram` (thu → quỹ → chi) + `DataTable` for opening/closing balance | No waterfall component in Evidence, but `SankeyDiagram` exists (undocumented in internal viz vocabulary) and reads better than a bar-chart approximation for flow composition |
| `combo` display (thu/chi bars + net line) | Grouped `BarChart` (thu/chi) + separate `LineChart` (net) | No combo/mixed-series component |
| `pivot` display (cashflow_line × tháng) | Flat `DataTable` with `search=true` | No dynamic pivot component |
| `heatmap` display (năm × tháng seasonality, View 2) | `BarChart` of `seasonality_index` (avg net_cash_flow per calendar month) + flat `DataTable` (nam, thang_so, dong_tien_rong) for raw lookup | No heatmap component in Evidence; bar + table conveys the same "which months run high/low" signal without color-intensity encoding |
| Interactive `year_range` filter (View 2, per design spec) | Not implemented — all View 2 charts show full available history | Evidence has no interactive filter widget (same root cause as `period_month` above); revisit if Evidence adds parameterized queries |

Each deviation has an inline `<p>` note on the page itself so a reader isn't
left wondering why a chart looks different from the Metabase version.

## Business Rules (unchanged from Metabase blueprint / playbook)

- `WHERE NOT is_internal_transfer` is mandatory on every thu/chi query — hardcoded exclusion, not a user filter. Skipping it inflates thu/chi ~64% (June-2026 recon: 299M internal transfers).
- `cash_balance` comes from `fact_account_balance_monthly` filtered `is_cash = true` (accounts 111x/112x), not from `fact_cash_movement.running_balance`.
- `cashflow_line` taxonomy is prefix-derived in `dim_gl_account` — provisional, pending finance sign-off (same caveat as Metabase blueprint and playbook).

## Recon Anchor (June 2026) — use to sanity-check the build

| Item | Expected |
|------|----------|
| Opening balance | 134.2M VND |
| cash_inflow | 464.4M VND |
| cash_outflow | 434.0M VND |
| net_cash_flow | +30.4M VND |
| cash_balance (closing) | 164.5M VND |
| Internal transfers (excluded) | 299M VND |

## Page Body

The full content below is deployed verbatim to `evidence/pages/finance-cashflow/index.md`.

````markdown
---
title: Finance Cashflow
full_width: true
---

# Finance Cashflow

> **Scope:** GL cash accounts (111x tiền mặt / 112x tiền gửi ngân hàng) · Internal transfers giữa các tài khoản tiền luôn bị loại trừ khỏi thu/chi

```sql period_month_options
SELECT DISTINCT
    strftime(period_month, '%Y-%m-01') AS period_month_value,
    strftime(period_month, '%m/%Y')    AS period_month_label
FROM main_marts.fact_cash_movement
ORDER BY period_month DESC
```

```sql cashflow_kpi
WITH latest AS (
    SELECT DATE '${inputs.period_month.value}' AS p
),
cur AS (
    SELECT
        COALESCE(SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END), 0) AS cash_inflow,
        COALESCE(SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END), 0) AS cash_outflow,
        COALESCE(SUM(signed_amount), 0)                                          AS net_cash_flow
    FROM main_marts.fact_cash_movement
    CROSS JOIN latest
    WHERE NOT is_internal_transfer AND period_month = latest.p
),
prev AS (
    SELECT
        COALESCE(SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END), 0) AS cash_inflow_prev,
        COALESCE(SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END), 0) AS cash_outflow_prev,
        COALESCE(SUM(signed_amount), 0)                                          AS net_cash_flow_prev
    FROM main_marts.fact_cash_movement
    CROSS JOIN latest
    WHERE NOT is_internal_transfer AND period_month = latest.p - INTERVAL '1 month'
),
bal_cur AS (
    SELECT COALESCE(SUM(b.closing_balance), 0) AS cash_balance
    FROM main_marts.fact_account_balance_monthly b
    JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
    CROSS JOIN latest
    WHERE g.is_cash AND b.period_month = latest.p
),
bal_prev AS (
    SELECT COALESCE(SUM(b.closing_balance), 0) AS cash_balance_prev
    FROM main_marts.fact_account_balance_monthly b
    JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
    CROSS JOIN latest
    WHERE g.is_cash AND b.period_month = latest.p - INTERVAL '1 month'
)
SELECT
    latest.p AS period_month,
    cur.cash_inflow, cur.cash_outflow, cur.net_cash_flow,
    prev.cash_inflow_prev, prev.cash_outflow_prev, prev.net_cash_flow_prev,
    bal_cur.cash_balance, bal_prev.cash_balance_prev
FROM latest, cur, prev, bal_cur, bal_prev
```

```sql period_label
SELECT '📅 Kỳ báo cáo: ' || strftime(DATE '${inputs.period_month.value}', '%m/%Y')
       || '  ·  Kỳ trước: ' || strftime(DATE '${inputs.period_month.value}' - INTERVAL '1 month', '%m/%Y') AS label
```

```sql yoy_companion
WITH monthly AS (
    SELECT period_month, SUM(signed_amount) AS net_cash_flow
    FROM main_marts.fact_cash_movement
    WHERE NOT is_internal_transfer
    GROUP BY period_month
),
lagged AS (
    SELECT
        period_month,
        net_cash_flow,
        LAG(net_cash_flow, 12) OVER (ORDER BY period_month) AS net_cash_flow_yoy
    FROM monthly
)
SELECT
    period_month,
    CASE
        WHEN net_cash_flow_yoy IS NULL THEN '📊 So cùng kỳ năm trước: chưa đủ 13 tháng dữ liệu liên tục (đang chờ backfill MISA GL 2022-2025) — xem tab "Xu hướng nhiều năm" khi có đủ dữ liệu.'
        ELSE '📊 So cùng kỳ năm trước (' || strftime(period_month - INTERVAL '12 months', '%m/%Y') || '): '
             || (CASE WHEN net_cash_flow - net_cash_flow_yoy >= 0 THEN '+' ELSE '' END)
             || ROUND((net_cash_flow - net_cash_flow_yoy) / 1000000.0, 1)::VARCHAR || 'M VNĐ ('
             || (CASE WHEN net_cash_flow - net_cash_flow_yoy >= 0 THEN '+' ELSE '' END)
             || ROUND((net_cash_flow - net_cash_flow_yoy) * 100.0 / NULLIF(ABS(net_cash_flow_yoy), 0), 1)::VARCHAR || '%)'
    END AS yoy_text
FROM lagged
WHERE period_month = DATE '${inputs.period_month.value}'
```

```sql cashflow_waterfall
WITH latest AS (
    SELECT DATE '${inputs.period_month.value}' AS p
),
opening AS (
    SELECT 0 AS sort_order, 'Số dư đầu kỳ' AS khoan_muc, COALESCE(SUM(b.opening_balance), 0) AS gia_tri
    FROM main_marts.fact_account_balance_monthly b
    JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
    CROSS JOIN latest
    WHERE g.is_cash AND b.period_month = latest.p
),
movements AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY cashflow_line) + 1 AS sort_order,
        cashflow_line                                   AS khoan_muc,
        SUM(signed_amount)                              AS gia_tri
    FROM main_marts.fact_cash_movement
    CROSS JOIN latest
    WHERE NOT is_internal_transfer AND period_month = latest.p
    GROUP BY cashflow_line
    HAVING SUM(signed_amount) <> 0
),
closing AS (
    SELECT 999 AS sort_order, 'Số dư cuối kỳ' AS khoan_muc, COALESCE(SUM(b.closing_balance), 0) AS gia_tri
    FROM main_marts.fact_account_balance_monthly b
    JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
    CROSS JOIN latest
    WHERE g.is_cash AND b.period_month = latest.p
)
SELECT khoan_muc, gia_tri FROM (
    SELECT * FROM opening
    UNION ALL
    SELECT * FROM movements
    UNION ALL
    SELECT * FROM closing
) t
ORDER BY sort_order
```

```sql cashflow_sankey
WITH latest AS (
    SELECT DATE '${inputs.period_month.value}' AS p
),
inflow AS (
    SELECT
        cashflow_line              AS source,
        'Quỹ tiền mặt/ngân hàng'   AS target,
        SUM(amount)                AS value
    FROM main_marts.fact_cash_movement
    CROSS JOIN latest
    WHERE direction = 'inflow' AND NOT is_internal_transfer AND period_month = latest.p
    GROUP BY cashflow_line
    HAVING SUM(amount) > 0
),
outflow AS (
    SELECT
        'Quỹ tiền mặt/ngân hàng'   AS source,
        cashflow_line              AS target,
        SUM(amount)                AS value
    FROM main_marts.fact_cash_movement
    CROSS JOIN latest
    WHERE direction = 'outflow' AND NOT is_internal_transfer AND period_month = latest.p
    GROUP BY cashflow_line
    HAVING SUM(amount) > 0
)
SELECT source, target, value FROM inflow
UNION ALL
SELECT source, target, value FROM outflow
```

```sql balance_trend
SELECT
    b.period_month         AS thang,
    SUM(b.closing_balance) AS so_du_cuoi_ky
FROM main_marts.fact_account_balance_monthly b
JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
WHERE g.is_cash
  AND b.period_month >= date_trunc('month', current_date) - INTERVAL '24 months'
GROUP BY 1
ORDER BY 1
```

```sql cashflow_monthly
SELECT
    period_month                                                  AS thang,
    SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END)  AS tong_thu,
    SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END)  AS tong_chi,
    SUM(signed_amount)                                            AS dong_tien_rong
FROM main_marts.fact_cash_movement
WHERE NOT is_internal_transfer
  AND period_month >= date_trunc('month', current_date) - INTERVAL '24 months'
GROUP BY 1
ORDER BY 1
```

```sql cashflow_by_line_month
SELECT
    cashflow_line AS "Cashflow Line",
    period_month  AS "Tháng",
    direction     AS "Hướng",
    SUM(amount)   AS "Số tiền"
FROM main_marts.fact_cash_movement
WHERE NOT is_internal_transfer
  AND period_month >= date_trunc('month', current_date) - INTERVAL '24 months'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
```

```sql chi_breakdown
WITH latest AS (
    SELECT DATE '${inputs.period_month.value}' AS p
)
SELECT
    cashflow_line AS khoan_muc,
    SUM(amount)   AS tong_chi
FROM main_marts.fact_cash_movement
CROSS JOIN latest
WHERE direction = 'outflow' AND NOT is_internal_transfer AND period_month = latest.p
GROUP BY 1
HAVING SUM(amount) > 0
ORDER BY 2 DESC
```

```sql data_freshness
SELECT
    CASE WHEN MAX(period_month) < date_trunc('month', current_date) - INTERVAL '1 month'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — ' ELSE '' END
    || '🕐 Kỳ mới nhất: ' || strftime(MAX(period_month), '%m/%Y')
    || '  ·  Số bút toán: ' || COUNT(*)::VARCHAR
    AS freshness_msg
FROM main_marts.fact_cash_movement
```

```sql multiyear_caveat
WITH avail AS (
    SELECT
        COUNT(DISTINCT EXTRACT(year FROM period_month))::INT AS years_observed,
        MIN(period_month) AS earliest_month,
        MAX(period_month) AS latest_month
    FROM main_marts.fact_cash_movement
)
SELECT
    years_observed,
    earliest_month,
    latest_month,
    CASE
        WHEN years_observed < 2 THEN
            '⚠️ Chỉ có dữ liệu ' || strftime(earliest_month, '%m/%Y') || ' → ' || strftime(latest_month, '%m/%Y')
            || ' — YoY / Lũy kế YTD / mùa vụ bên dưới CHƯA đủ tin cậy (đang chờ backfill MISA GL 2022-2025 ingest xong).'
        WHEN years_observed < 3 THEN
            '⚠️ Có ' || years_observed::VARCHAR || ' năm dữ liệu (' || strftime(earliest_month, '%m/%Y') || ' → ' || strftime(latest_month, '%m/%Y')
            || ') — YoY / Lũy kế YTD dùng được, nhưng mùa vụ (chart bên dưới) cần ≥3 năm mới đáng tin.'
        ELSE
            '✅ Có ' || years_observed::VARCHAR || ' năm dữ liệu (' || strftime(earliest_month, '%m/%Y') || ' → ' || strftime(latest_month, '%m/%Y')
            || ') — đủ tin cậy cho YoY / Lũy kế YTD / mùa vụ.'
    END AS caveat_msg
FROM avail
```

```sql ytd_kpi
WITH monthly AS (
    SELECT
        period_month,
        SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END) AS cash_inflow,
        SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END) AS cash_outflow,
        SUM(signed_amount)                                          AS net_cash_flow
    FROM main_marts.fact_cash_movement
    WHERE NOT is_internal_transfer
    GROUP BY period_month
),
bounds AS (
    SELECT
        EXTRACT(year  FROM MAX(period_month))::INT AS cur_year,
        EXTRACT(month FROM MAX(period_month))::INT AS cur_month
    FROM monthly
),
cur AS (
    SELECT
        COALESCE(SUM(cash_inflow), 0)  AS cash_inflow_ytd,
        COALESCE(SUM(cash_outflow), 0) AS cash_outflow_ytd,
        COALESCE(SUM(net_cash_flow), 0) AS net_cash_flow_ytd
    FROM monthly, bounds
    WHERE EXTRACT(year FROM period_month) = bounds.cur_year
      AND EXTRACT(month FROM period_month) <= bounds.cur_month
),
prev AS (
    SELECT
        COALESCE(SUM(cash_inflow), 0)  AS cash_inflow_ytd_prev,
        COALESCE(SUM(cash_outflow), 0) AS cash_outflow_ytd_prev,
        COALESCE(SUM(net_cash_flow), 0) AS net_cash_flow_ytd_prev
    FROM monthly, bounds
    WHERE EXTRACT(year FROM period_month) = bounds.cur_year - 1
      AND EXTRACT(month FROM period_month) <= bounds.cur_month
)
SELECT
    bounds.cur_year, bounds.cur_month,
    cur.cash_inflow_ytd, cur.cash_outflow_ytd, cur.net_cash_flow_ytd,
    prev.cash_inflow_ytd_prev, prev.cash_outflow_ytd_prev, prev.net_cash_flow_ytd_prev
FROM bounds, cur, prev
```

```sql ytd_label
SELECT
    'Lũy kế từ tháng 1 → ' || strftime(MAX(period_month), '%m/%Y') || ' · so với cùng mốc năm trước' AS label
FROM main_marts.fact_cash_movement
```

```sql balance_trend_full
SELECT
    b.period_month         AS thang,
    SUM(b.closing_balance) AS so_du_cuoi_ky
FROM main_marts.fact_account_balance_monthly b
JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
WHERE g.is_cash
GROUP BY 1
ORDER BY 1
```

```sql annual_summary
WITH yearly AS (
    SELECT
        EXTRACT(year FROM period_month)::INT AS nam,
        SUM(CASE WHEN direction = 'inflow'  THEN amount ELSE 0 END) AS tong_thu,
        SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0 END) AS tong_chi,
        SUM(signed_amount)                                          AS dong_tien_rong
    FROM main_marts.fact_cash_movement
    WHERE NOT is_internal_transfer
    GROUP BY 1
)
SELECT
    nam, tong_thu, tong_chi, dong_tien_rong,
    ROUND(
        (dong_tien_rong - LAG(dong_tien_rong) OVER (ORDER BY nam)) * 100.0
        / NULLIF(ABS(LAG(dong_tien_rong) OVER (ORDER BY nam)), 0)
    , 1) AS yoy_pct
FROM yearly
ORDER BY nam
```

```sql seasonality_index
WITH monthly AS (
    SELECT period_month, SUM(signed_amount) AS net_cash_flow
    FROM main_marts.fact_cash_movement
    WHERE NOT is_internal_transfer
    GROUP BY period_month
)
SELECT
    EXTRACT(month FROM period_month)::INT AS thang_so,
    'Tháng ' || EXTRACT(month FROM period_month)::VARCHAR AS thang_nhan,
    AVG(net_cash_flow)                                    AS chi_so_mua_vu,
    COUNT(*)                                               AS years_observed
FROM monthly
GROUP BY 1, 2
ORDER BY 1
```

```sql seasonality_detail
SELECT
    EXTRACT(year FROM period_month)::INT  AS nam,
    EXTRACT(month FROM period_month)::INT AS thang_so,
    SUM(signed_amount)                    AS dong_tien_rong
FROM main_marts.fact_cash_movement
WHERE NOT is_internal_transfer
GROUP BY 1, 2
ORDER BY 1, 2
```

```sql outflow_by_line_year
SELECT
    EXTRACT(year FROM period_month)::INT AS nam,
    COALESCE(cashflow_line, 'Khác')      AS khoan_muc,
    SUM(amount)                          AS tong_chi
FROM main_marts.fact_cash_movement
WHERE direction = 'outflow' AND NOT is_internal_transfer
GROUP BY 1, 2
HAVING SUM(amount) > 0
ORDER BY 1, 2
```

```sql outflow_growth_rank
WITH yearly AS (
    SELECT
        EXTRACT(year FROM period_month)::INT AS nam,
        COALESCE(cashflow_line, 'Khác')      AS khoan_muc,
        SUM(amount)                          AS tong_chi
    FROM main_marts.fact_cash_movement
    WHERE direction = 'outflow' AND NOT is_internal_transfer
    GROUP BY 1, 2
),
yoy AS (
    SELECT
        nam, khoan_muc, tong_chi,
        (tong_chi - LAG(tong_chi) OVER (PARTITION BY khoan_muc ORDER BY nam)) * 100.0
            / NULLIF(LAG(tong_chi) OVER (PARTITION BY khoan_muc ORDER BY nam), 0) AS yoy_growth_pct
    FROM yearly
)
SELECT
    khoan_muc,
    ROUND(AVG(yoy_growth_pct), 1) AS avg_yoy_growth_pct,
    COUNT(*)                     AS years_with_growth_data
FROM yoy
WHERE yoy_growth_pct IS NOT NULL
GROUP BY khoan_muc
ORDER BY avg_yoy_growth_pct DESC
LIMIT 10
```

<Tabs id="cashflow">

<Tab label="📊 Tổng quan">

<Dropdown
    data={period_month_options}
    name=period_month
    value=period_month_value
    label=period_month_label
    title="Kỳ báo cáo"
/>

> <Value data={period_label} column="label" />

<p style="font-size:0.75rem; color:#888;">Scorecard, Sankey và bảng đầu/cuối kỳ bên dưới đổi theo kỳ chọn ở dropdown. Riêng phần "Xu hướng theo tháng" (2 chart cuối trang) luôn hiện 24 tháng gần nhất tính theo ngày thật, không đổi theo dropdown.</p>

<Grid cols={4}>
  <BigValue data={cashflow_kpi} value="cash_balance"   comparison="cash_balance_prev"   comparisonTitle="Tháng trước" title="Số dư quỹ (₫)"    fmt="#,##0" />
  <BigValue data={cashflow_kpi} value="net_cash_flow"  comparison="net_cash_flow_prev"  comparisonTitle="Tháng trước" title="Dòng tiền ròng (₫)" fmt="#,##0" />
  <BigValue data={cashflow_kpi} value="cash_inflow"    comparison="cash_inflow_prev"    comparisonTitle="Tháng trước" title="Tổng thu (₫)"     fmt="#,##0" />
  <BigValue data={cashflow_kpi} value="cash_outflow"   comparison="cash_outflow_prev"   comparisonTitle="Tháng trước" title="Tổng chi (₫)"     fmt="#,##0" upIsGood=false />
</Grid>

> <Value data={yoy_companion} column="yoy_text" />

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Dòng tiền chảy vào/ra quỹ — theo cashflow_line (kỳ đã chọn)</p>

<SankeyDiagram
    data={cashflow_sankey}
    linkLabels="value"
    linkColor="gradient"
    valueFmt="#,##0"
    chartAreaHeight={380}
/>

<p style="font-weight:600; font-size:0.875rem; margin:1rem 0 0.5rem;">Chi tiết số dư đầu kỳ → cuối kỳ</p>

<DataTable data={cashflow_waterfall} rows=10 />

<p style="font-size:0.75rem; color:#888;">Evidence không có biểu đồ waterfall gốc — thay bằng Sankey diagram (thu → quỹ → chi) + bảng chi tiết số dư đầu/cuối kỳ (bản Metabase dùng waterfall thật).</p>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Xu hướng số dư và dòng tiền theo tháng (24 tháng gần nhất — full history: xem tab "Xu hướng nhiều năm")</p>

<Grid cols={2}>
  <LineChart
      data={balance_trend}
      x="thang"
      y="so_du_cuoi_ky"
      title="Số dư quỹ theo tháng (₫)"
      yAxisTitle="₫"
  />
  <BarChart
      data={cashflow_monthly}
      x="thang"
      y={["tong_thu", "tong_chi"]}
      type="grouped"
      title="Thu / Chi theo tháng (₫)"
      yAxisTitle="₫"
  />
</Grid>

<LineChart
    data={cashflow_monthly}
    x="thang"
    y="dong_tien_rong"
    title="Dòng tiền ròng theo tháng (₫)"
    yAxisTitle="₫"
/>

<p style="font-size:0.75rem; color:#888;">Evidence không có combo chart (bar + line chung trục) — tách thành 2 chart riêng (bản Metabase dùng combo). Window mặc định nới từ 12 → 24 tháng (trước đây chỉ có 6 tháng data; vẫn giữ glanceable, full history đã chuyển sang tab riêng).</p>

> <Value data={data_freshness} column="freshness_msg" />

</Tab>

<Tab label="🔍 Chi tiết dòng tiền">

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Cơ cấu dòng tiền theo cashflow_line và tháng (24 tháng gần nhất)</p>

<DataTable data={cashflow_by_line_month} rows=25 search=true />

<p style="font-size:0.75rem; color:#888;">Evidence DataTable không pivot cột động như Metabase — bảng phẳng, dùng search/sort để lọc.</p>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Cơ cấu chi tiêu — hạng mục nào chiếm nhiều nhất? (kỳ đã chọn)</p>

<BarChart
    data={chi_breakdown}
    x="khoan_muc"
    y="tong_chi"
    swapXY=true
    title=""
    yAxisTitle="Tổng chi (₫)"
    fmt="#,##0"
/>

> <Value data={data_freshness} column="freshness_msg" />

</Tab>

<Tab label="📈 Xu hướng nhiều năm">

> <Value data={multiyear_caveat} column="caveat_msg" />

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Lũy kế từ đầu năm (YTD) vs cùng mốc năm trước</p>

> <Value data={ytd_label} column="label" />

<Grid cols={3}>
  <BigValue data={ytd_kpi} value="net_cash_flow_ytd"  comparison="net_cash_flow_ytd_prev"  comparisonTitle="YTD năm trước" title="Lũy kế dòng tiền ròng YTD (₫)" fmt="#,##0" />
  <BigValue data={ytd_kpi} value="cash_inflow_ytd"    comparison="cash_inflow_ytd_prev"    comparisonTitle="YTD năm trước" title="Tổng thu YTD (₫)"           fmt="#,##0" />
  <BigValue data={ytd_kpi} value="cash_outflow_ytd"   comparison="cash_outflow_ytd_prev"   comparisonTitle="YTD năm trước" title="Tổng chi YTD (₫)"           fmt="#,##0" upIsGood=false />
</Grid>

<p style="font-size:0.75rem; color:#888;">So YTD vs YTD (cùng cắt ở tháng hiện tại của mỗi năm) — không so YTD năm nay với tổng cả năm ngoái, vì năm nay chưa kết thúc.</p>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Số dư quỹ — toàn bộ lịch sử (không giới hạn 24 tháng)</p>

<AreaChart
    data={balance_trend_full}
    x="thang"
    y="so_du_cuoi_ky"
    title=""
    yAxisTitle="₫"
/>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Thu / chi theo năm — tăng trưởng YoY</p>

<Grid cols={2}>
  <BarChart
      data={annual_summary}
      x="nam"
      y={["tong_thu", "tong_chi"]}
      type="grouped"
      title="Thu / Chi theo năm (₫)"
      yAxisTitle="₫"
  />
  <DataTable data={annual_summary} rows=10>
    <Column id="nam" title="Năm" />
    <Column id="tong_thu" title="Tổng thu" fmt="#,##0" />
    <Column id="tong_chi" title="Tổng chi" fmt="#,##0" />
    <Column id="dong_tien_rong" title="Dòng tiền ròng" fmt="#,##0" />
    <Column id="yoy_pct" title="YoY %" fmt="0.0" />
  </DataTable>
</Grid>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Mùa vụ dòng tiền — tháng nào lịch sử luôn cao/thấp?</p>

<BarChart
    data={seasonality_index}
    x="thang_so"
    y="chi_so_mua_vu"
    title=""
    yAxisTitle="Trung bình dòng tiền ròng (₫)"
    fmt="#,##0"
/>

<DataTable data={seasonality_detail} rows=15 search=true>
  <Column id="nam" title="Năm" />
  <Column id="thang_so" title="Tháng" />
  <Column id="dong_tien_rong" title="Dòng tiền ròng" fmt="#,##0" />
</DataTable>

<p style="font-size:0.75rem; color:#888;">Evidence không có heatmap gốc — thay bằng bar chart trung bình theo tháng dương lịch (chi_so_mua_vu, gộp qua các năm) + bảng chi tiết năm×tháng để tra số liệu gốc (bản Metabase dùng heatmap thật). Chỉ số này đáng tin khi ≥3 năm dữ liệu — xem caveat đầu tab.</p>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Cơ cấu chi theo cashflow_line qua các năm — khoản nào tăng trưởng cấu trúc?</p>

<Grid cols={2}>
  <BarChart
      data={outflow_by_line_year}
      x="nam"
      y="tong_chi"
      series="khoan_muc"
      type="stacked"
      title="Cơ cấu chi theo năm (₫)"
      yAxisTitle="₫"
  />
  <BarChart
      data={outflow_growth_rank}
      x="khoan_muc"
      y="avg_yoy_growth_pct"
      swapXY=true
      title="Tốc độ tăng trưởng YoY trung bình theo cashflow_line (%)"
      yAxisTitle="%"
  />
</Grid>

<p style="font-size:0.75rem; color:#888;">Ranking bên phải theo TỐC ĐỘ tăng trưởng YoY trung bình, không phải theo tổng giá trị — khác bảng "Top khoản chi" ở tab Chi tiết dòng tiền (ranking theo tổng chi tháng hiện tại).</p>

<p style="font-weight:600; font-size:0.875rem; margin:1rem 0 0.5rem;">Chi tiết theo cashflow_line × năm</p>

<DataTable data={outflow_by_line_year} rows=25 search=true>
  <Column id="khoan_muc" title="Cashflow Line" />
  <Column id="nam" title="Năm" />
  <Column id="tong_chi" title="Tổng chi" fmt="#,##0" />
</DataTable>

</Tab>

</Tabs>

---

<p style="font-size:0.75rem; color: #888;">Source: fact_cash_movement · fact_account_balance_monthly · dim_gl_account · Cadence: monthly (MISA GL); tab "Xu hướng nhiều năm" đọc quarterly/annual · is_internal_transfer luôn bị loại khỏi thu/chi</p>
````

## Open Questions

Carried over unresolved from the playbook (not evidence-specific):

1. `cashflow_line` taxonomy sign-off — who is the owner, target date?
2. `111` (tiền mặt) vs `112` (ngân hàng) split — does the CFO audience want separate views, or ALL combined is enough?
