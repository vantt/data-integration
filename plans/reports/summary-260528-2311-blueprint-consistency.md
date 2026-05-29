# Blueprint Consistency Check — Master Summary
Generated: 2026-05-28T23:11 ICT

## Overview

- **Total dashboards checked**: 37 (active, non-archived)
- **With blueprint**: 35
- **No blueprint** (skip): 2 (id 1 "E-commerce Insights", id 73 "Welcome to ChPulse BI")
- **Legacy (no scope suffix)**: 12 (ids 79–92) — not checked, pending archival

## Inconsistency Summary

| Status | Count |
|---|---|
| MATCH | 31 |
| MINOR_DIFF | 2 |
| MAJOR_DIFF | 2 |
| NO_BLUEPRINT | 2 |

---

## MAJOR_DIFF — Cần xử lý ngay

### 1. Sales Monthly Business Review [All] (id: 31)
**Blueprint**: `docs/analytics-handbook/blueprints/sales_monthly_review.md`

- Missing tab in Metabase: **"P&L Hàng Tháng"** (tab thứ 5)
- 4 missing questions:
  - `Monthly Net Profit vs Last Month`
  - `Gross Margin % vs Last Month`
  - `Gross Margin % Trend (12M)`
  - `Channel Profit Contribution (Top 10)`
- 4 fewer text cards (17 vs 21 in blueprint)

### 2. Order Detail [Retail] (id: 38)
**Blueprint**: `docs/analytics-handbook/blueprints/order_detail.md`

- Chỉ có 1 question (`Chu kỳ báo cáo`), thiếu 4 core questions:
  - `Order Header`
  - `Order Economics`
  - `Line Items`
  - `Payments`
- Text card scaffolding còn nguyên (5 text cards) — cần redeploy questions từ blueprint

---

## MINOR_DIFF — Có thể bỏ qua hoặc cleanup

### 3. Channel Profitability Monthly [Cross] (id: 33)
**Blueprint**: `docs/analytics-handbook/blueprints/channel_profitability_monthly.md`

- Missing 1 text card (Blueprint 7 / Metabase 6)
- Tabs + questions hoàn toàn khớp

### 4. Product Profitability [All] (id: 36)
**Blueprint**: `docs/analytics-handbook/blueprints/product_profitability.md`

- 1 extra text card trong Metabase (Blueprint 5 / Metabase 6)
- Likely stale source/freshness footer

---

## Notable Observations (không phải inconsistency)

### Product Inventory Health [All] (id: 94)
- Blueprint dùng `size_x: 24` (24-col grid) nhưng Metabase standard là 18-col
- Content đầy đủ — nên review layout trong browser

### Welcome to ChPulse BI (id: 73)
- Metabase API trả về tên bị corrupt: `"Welcome to Ch?Pulse BI"` (emoji ❓ bị mất)
- Chỉ ảnh hưởng API response, UI display bình thường

---

## Dashboards Không Có Blueprint

| ID | Tên | Ghi chú |
|---|---|---|
| 1 | E-commerce Insights | Sample Metabase data, không cần blueprint |
| 73 | Welcome to ChPulse BI | Onboarding landing page |

---

## Legacy Dashboards (không có scope suffix — ids 79–92)

Đây là các dashboard cũ, chưa được archive:

| ID | Tên |
|---|---|
| 79 | Sales Monthly Business Review |
| 82 | Channel Profitability Monthly |
| 83 | Customer Intelligence Monthly |
| 84 | Customer Retention & Lifecycle |
| 85 | Social Commerce Operations |
| 86 | Finance P&L Dashboard |
| 87 | Ingestion Health Monitor |
| 88 | Logistics Operations Center |
| 89 | Order Detail |
| 90 | Order Listing |
| 91 | Order Profitability |
| 92 | Product Profitability |

Các dashboard này là bản cũ của dashboards có scope suffix (không có blueprint tương ứng).
**Khuyến nghị**: Archive hoặc delete để tránh nhầm lẫn.

---

## Full Dashboard × Blueprint Map

| ID | Dashboard | Blueprint | Status |
|---|---|---|---|
| 8 | Sales Ops Weekly Review [Retail] | sales_ops_weekly_review.md | MATCH |
| 9 | Sales Ops Monthly Summary [Retail] | sales_ops_monthly_summary.md | MATCH |
| 13 | Marketing Monthly Analysis [Retail] | marketing_monthly_analysis.md | MATCH |
| 14 | Customer Retention & Lifecycle [Retail] | customer_retention_dashboard.md | MATCH |
| 15 | Customer Intelligence Monthly [Cross] | customer_intelligence_monthly.md | MATCH |
| 26 | Order Listing [Retail] | order_listing.md | MATCH |
| 27 | Social Commerce Operations [Retail] | customer_support_social_commerce.md | MATCH |
| 28 | Logistics Operations Center [All] | logistics_operations.md | MATCH |
| 30 | Product Performance [Cross] | product_performance.md | MATCH |
| 31 | Sales Monthly Business Review [All] | sales_monthly_review.md | **MAJOR_DIFF** |
| 32 | Shopee Channel Economics [Cross] | shopee_channel_economics.md | MATCH |
| 33 | Channel Profitability Monthly [Cross] | channel_profitability_monthly.md | MINOR_DIFF |
| 34 | Finance P&L [All] | finance_pl.md | MATCH |
| 35 | Order Profitability [All] | order_profitability.md | MATCH |
| 36 | Product Profitability [All] | product_profitability.md | MINOR_DIFF |
| 37 | Marketing ROI [Retail] | marketing_roi.md | MATCH |
| 38 | Order Detail [Retail] | order_detail.md | **MAJOR_DIFF** |
| 40 | Ingestion Health Monitor [Internal] | ingestion_health.md | MATCH |
| 41 | Daily Sales [Retail] | sales_daily_operation.md | MATCH |
| 42 | Yesterday's Sales [Retail] | sales_yesterday_operation.md | MATCH |
| 43 | CEO Weekly Pulse [All] | ceo_weekly_pulse.md | MATCH |
| 44 | CEO Monthly Scorecard [All] | ceo_monthly_scorecard.md | MATCH |
| 46 | Promotion Analysis [Retail] | sales_promotion_analysis.md | MATCH |
| 47 | Marketing Weekly Tracker [Retail] | marketing_weekly_tracker.md | MATCH |
| 48 | Customer Operational [Retail] | customer_operational_dashboard.md | MATCH |
| 49 | B2B Daily Sales [B2B] | b2b_sales_daily.md | MATCH |
| 50 | B2B Orders Tracking [B2B] | b2b_orders_tracking.md | MATCH |
| 51 | US CrossBorder Daily [US] | us_crossborder_operations.md | MATCH |
| 74 | Cost Ledger Analyzer [All] | finance_cost_ledger.md | MATCH |
| 75 | Return Impact Analysis [All] | finance_return_impact.md | MATCH |
| 76 | Product Cost-to-Margin Heatmap [Cross] | finance_product_cost_margin.md | MATCH |
| 77 | Channel P&L Deep Dive [Cross] | finance_channel_pl.md | MATCH |
| 78 | Accounting Reconciliation Cockpit [Internal] | finance_accounting_recon.md | MATCH |
| 94 | Product Inventory Health [All] | product_inventory.md | MATCH |
| 95 | Finance Services Revenue [All] | finance_services_revenue.md | MATCH |
