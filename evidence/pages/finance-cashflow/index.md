---
title: Finance Cashflow
---

# Finance Cashflow

> **Scope:** GL cash accounts (111x tiền mặt / 112x tiền gửi ngân hàng) · Internal transfers giữa các tài khoản tiền luôn bị loại trừ khỏi thu/chi

```sql cashflow_kpi
WITH latest AS (
    SELECT MAX(period_month) AS p FROM main_marts.fact_cash_movement
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
SELECT '📅 Kỳ báo cáo: ' || strftime(MAX(period_month), '%m/%Y')
       || '  ·  Kỳ trước: ' || strftime(MAX(period_month) - INTERVAL '1 month', '%m/%Y') AS label
FROM main_marts.fact_cash_movement
```

```sql cashflow_waterfall
WITH latest AS (
    SELECT MAX(period_month) AS p FROM main_marts.fact_cash_movement
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

```sql balance_trend
SELECT
    b.period_month         AS thang,
    SUM(b.closing_balance) AS so_du_cuoi_ky
FROM main_marts.fact_account_balance_monthly b
JOIN main_marts.dim_gl_account g ON b.account_code = g.account_code
WHERE g.is_cash
  AND b.period_month >= date_trunc('month', current_date) - INTERVAL '12 months'
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
  AND period_month >= date_trunc('month', current_date) - INTERVAL '12 months'
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
  AND period_month >= date_trunc('month', current_date) - INTERVAL '12 months'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
```

```sql chi_breakdown
WITH latest AS (
    SELECT MAX(period_month) AS p FROM main_marts.fact_cash_movement
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

<Tabs id="cashflow">

<Tab label="📊 Tổng quan">

> <Value data={period_label} column="label" />

<Grid cols={4}>
  <BigValue data={cashflow_kpi} value="cash_balance"   comparison="cash_balance_prev"   comparisonTitle="Tháng trước" title="Số dư quỹ (₫)"    fmt="#,##0" />
  <BigValue data={cashflow_kpi} value="net_cash_flow"  comparison="net_cash_flow_prev"  comparisonTitle="Tháng trước" title="Dòng tiền ròng (₫)" fmt="#,##0" />
  <BigValue data={cashflow_kpi} value="cash_inflow"    comparison="cash_inflow_prev"    comparisonTitle="Tháng trước" title="Tổng thu (₫)"     fmt="#,##0" />
  <BigValue data={cashflow_kpi} value="cash_outflow"   comparison="cash_outflow_prev"   comparisonTitle="Tháng trước" title="Tổng chi (₫)"     fmt="#,##0" upIsGood=false />
</Grid>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Cấu trúc dòng tiền — từ số dư đầu kỳ đến cuối kỳ (tháng mới nhất)</p>

<BarChart
    data={cashflow_waterfall}
    x="khoan_muc"
    y="gia_tri"
    swapXY=true
    title=""
    yAxisTitle="₫"
    fmt="#,##0"
/>

<DataTable data={cashflow_waterfall} rows=10 />

<p style="font-size:0.75rem; color:#888;">Evidence không có biểu đồ waterfall gốc — thay bằng bar chart + bảng chi tiết (bản Metabase dùng waterfall thật).</p>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Xu hướng số dư và dòng tiền theo tháng (12 tháng gần nhất)</p>

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

<p style="font-size:0.75rem; color:#888;">Evidence không có combo chart (bar + line chung trục) — tách thành 2 chart riêng (bản Metabase dùng combo).</p>

> <Value data={data_freshness} column="freshness_msg" />

</Tab>

<Tab label="🔍 Chi tiết dòng tiền">

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Cơ cấu dòng tiền theo cashflow_line và tháng (12 tháng gần nhất)</p>

<DataTable data={cashflow_by_line_month} rows=25 search=true />

<p style="font-size:0.75rem; color:#888;">Evidence DataTable không pivot cột động như Metabase — bảng phẳng, dùng search/sort để lọc.</p>

---

<p style="font-weight:600; font-size:0.875rem; margin-bottom:0.5rem;">Cơ cấu chi tiêu — hạng mục nào chiếm nhiều nhất? (tháng mới nhất)</p>

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

</Tabs>

---

<p style="font-size:0.75rem; color: #888;">Source: fact_cash_movement · fact_account_balance_monthly · dim_gl_account · Cadence: monthly (MISA GL) · is_internal_transfer luôn bị loại khỏi thu/chi</p>
