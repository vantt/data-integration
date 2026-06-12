# Plan — Deep / Multi-Dimensional Cohort Analytics

> Design CHỐT (§5 `handoff-prompt.md`). Spec v1 locked. Build new alongside → validate → retire (gate user).
> Status tracker — cập nhật tới đâu ghi tới đó.

## Phases

| Phase | Mô tả | Status |
|---|---|---|
| P0 | Discuss → chốt design (§5 handoff) | ✅ DONE (2026-06-12) |
| P1 | Domain doc: "Cohort Framework" context vào `domains/customer.md` — axis/metric/min-size | ✅ DONE (2026-06-12) |
| P2 | Pipeline: `int_customer_entry_attributes` + `mart_cohort_retention` (long-format) | ✅ DONE (2026-06-12) |
| P3 | Boards: "Cohort Explorer" table (Marketing & Customers › 👥 Customer) | ✅ DONE (2026-06-12) |
| P4 | Validate (real Dagster run + verify olap.duckdb) | ✅ DONE (2026-06-12) |
| P4b | Board: "Cohort Calendar Trend" multi-line wall-clock view (dashboard #112) | ✅ DONE (2026-06-12) |
| P5 | Retire/gộp board cũ (gate user) | ✅ DONE (2026-06-12) |

## Spec v1 (từ §5)
- **Mart:** `mart_cohort_retention` long-format — `cohort_dimension, cohort_value, window_type, period_n, cohort_size, active, retention_pct, revenue_retention, repeat_rate`. 1 bảng mọi axis; UNION ALL per axis; KHÔNG re-derive (L122).
- **Min cohort size ≥ 10** (ẩn nhóm nhỏ hơn).
- **Axes single:** first_order_month · entry_product · entry_category · acquisition_channel · basket_size (1 vs ≥2) · entry_value_band.
- **Composite (2, pre-approved):** `entry_product × acquisition_channel`, `basket_size × entry_value_band`.
- **Window: CẢ HAI** — relative M0/M1/M2… (primary) + calendar month. Cột `window_type`.
- **Metric v1:** retention_pct + revenue_retention + repeat_rate. Margin (realized, L125) + basket-expansion/cross-category = **v2**.
- **Viz:** TABLE + conditional formatting. Scope **retail**.
- **Market-basket (FBT):** PHASE SAU, không chặn v1.

## Bài học áp dụng
L122 (no re-derive pre-computed) · L125 (realized_margin_pct) · L123 (date field-filter vỡ trên SQL aliased) · [[feedback_dim_customers_incremental_full_refresh]] · [[feedback_metabase_redeploy_use_skill]].

## P1 Log
- 2026-06-12: ✅ Thêm `## Context: Cohort Framework` vào `docs/analytics-handbook/domains/customer.md` (giữa Retention & Engagement và Segmentation). Nội dung: mental model (axis × metric, entry-point, cohort_size = mẫu số, min-size=10), Context Overview + Q1, bảng 6 axis single + 2 composite duyệt trước, 2 window_type (relative/calendar), bảng metric (v1: retention_pct/revenue_retention/repeat_rate; v2: realized_margin/basket-expansion), architecture long-format `mart_cohort_retention`, 6 Common Misunderstandings (tension: cohort_size mẫu số, min-size suppression, entry_product≠product_affinity, relative≠calendar, realized≠gross margin, composite cardinality). Cập nhật header date + cross-link từ Retention Rate #5. Áp L122/L125.
- **Next:** P2 — `int_customer_entry_attributes` (1 dòng/khách: entry product/category/channel/basket_size/value_band) + `mart_cohort_retention` (long-format, UNION ALL per axis). Cần verify cột nguồn (fact_sales order-line, dim_customers entry-key) trước khi build model.

## P2 Log
- 2026-06-12: ✅ Tạo 2 model + schema.yml. Fixes: (1) xóa dead CTE entry_lines, (2) bỏ `fs.status` filter (fact_sales không có cột status — inherited scope via INNER JOIN first_orders), (3) `FORMAT(DATE, '%Y-%m')` → `STRFTIME('%Y-%m', date)` (DuckDB syntax), (4) mkdir rolling dir dùng `sh -c` (Git Bash path translation bug). Real build: PASS=7 (int×3 + mart×4). Verified in olap.duckdb: 9,181 rows, 8 axes, M+0=100%, M+1 3–17% (consistent với retention-leak §2.3). Serving view registered via bootstrap_serving_views.py.
- **Next:** P3 — "Cohort Explorer" Metabase dashboard. Table viz + conditional formatting. Filter: cohort_dimension + window_type + metric. Dashboard trong Marketing & Customers › 👥 Customer.

## P3 Log
- 2026-06-12: ✅ Blueprint `docs/analytics-handbook/blueprints/cohort_explorer.md` + deploy. Dashboard #111 "Cohort Explorer [Retail]" in 👥 Customer collection (id=99). 3 cards: (1) Cohort Retention Matrix (pre-pivoted M0–M12, red→yellow→green conditional formatting), (2) Cohort Value Summary (Repeat Rate + revenue retention M0–M6), (3) Cohort Data Table (long-format, both window types). Filters: cohort_dimension (field_id=1793) + window_type (field_id=1795). Deployed via deploy_from_markdown.js.
- **Next:** P4 — Validate via real Dagster nightly run. Verify mart_cohort_retention row count in olap.duckdb post-run, open dashboard to confirm data flows through.

## P4 Log — Validate + Bug Fix
- 2026-06-12: ✅ Triggered selective Dagster run (runId=5765fc89) targeting `int_customer_entry_attributes` + `mart_cohort_retention`. Run succeeded. Code location reload required first (manifest pre-parsed at startup; assets now visible after reload). 
- **Bug found & fixed:** 1,067 customers (20.8%) had `first_order_total=0` from 7 `is_sales_channel=FALSE` internal channels (US=830, Other=135, Quà Tặng=23, Unknown, Gosumo, Test Sản Phẩm, Ưu đãi Nhân Viên). All labeled `channel_category='Internal'`. Fix: added `INNER JOIN dim_channels ch ... AND ch.is_sales_channel=TRUE` to `first_orders` CTE (int_customer_entry_attributes) AND `activity` CTE (mart_cohort_retention) to exclude internal-arrangement orders from both entry attribution and retention tracking.
- **After fix:** int_customer_entry_attributes 5,119→4,081 rows; zero_first_order_total 1,067→95 (residual: legitimate promotions from real channels); mart_cohort_retention 9,181→7,061 rows; US channel eliminated.
- **Next:** P4b — Cohort Calendar Trend dashboard.

## P4b Log — Cohort Calendar Trend
- 2026-06-12: ✅ Blueprint `docs/analytics-handbook/blueprints/cohort_calendar_trend.md` + deploy. Dashboard #112 "Cohort Calendar Trend [Retail]" in 👥 Customer collection (id=99). 2 multi-line cards: (1) Retention % by Calendar Month (card 2386), (2) Revenue by Calendar Month (card 2387). Filter: cohort_dimension (field_id=1793, default=first_order_month). Correctness verified: cohort 2023-01 at 2023-01 = 100%, subsequent months drop to 2–13% (consistent with relative window M+1 rates). Upper-triangular structure confirmed (758 rows, 62 cohorts × calendar months 2021-05→2026-06).
- **Next:** P5 — Retire/gộp board cũ.

## P5 Log — Retire old cohort cards
- 2026-06-12: ✅ Removed dashcards #3528 (Cohort Retention Heatmap) + #3529 (Revenue by Cohort Layer Cake) from dashboard #105 "Weekly · Customer Retention & Cohorts [Retail]". Both superseded by #111 Cohort Explorer + #112 Cohort Calendar Trend. #105 retained with remaining 40 cards (lifecycle, retention waterfall, purchase frequency, reactivation).
