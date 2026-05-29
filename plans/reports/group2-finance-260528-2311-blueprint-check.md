# Blueprint Consistency Check — Finance Group
Generated: 2026-05-28 16:18:56

## Summary
- Checked: 8 dashboards
- MATCH: 7
- MINOR_DIFF: 1
- MAJOR_DIFF: 0
- NO_BLUEPRINT: 0
- NO_DASHBOARD: 0

---

## Dashboard Details

### Finance P&L [All] (id: 34) — MATCH

**Blueprint tabs**: P&L Overview, Channel Profitability, Shopee Economics
**Metabase tabs**: P&L Overview, Channel Profitability, Shopee Economics

**Blueprint questions** (16 unique): Chu kỳ báo cáo ×3, Net Revenue MTD, COGS MTD, Gross Profit MTD, Gross Margin Percent, Revenue vs COGS Trend, Revenue Waterfall, Margin by Channel, Revenue vs COGS by Channel, COGS Ratio Trend, Shopee Settlement MTD, Settlement Margin Percent, Platform Fee Rate, Shopee Gross Revenue, Shopee Fee Breakdown, Revenue to Settlement Waterfall
**Metabase questions** (16 unique): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 9 / Metabase 9

---

### Channel P&L Deep Dive [Cross] (id: 77) — MATCH

**Blueprint tabs**: P&L Waterfall, Channel Scorecard, Margin Heatmap, Variance Analysis, Loss-Leader Alert
**Metabase tabs**: P&L Waterfall, Channel Scorecard, Margin Heatmap, Variance Analysis, Loss-Leader Alert

**Blueprint questions** (9 unique + 5× Chu kỳ báo cáo): P&L Waterfall — All Channels, Channel Scorecard Table, Net Margin Heatmap — Channel × Month, Channel MoM Variance Table, Net Margin Trend by Channel (with Budget Target), Loss Leader Channel Count, Total Loss Exposure, Loss Leader Detail Table
**Metabase questions** (9 unique + 5× Chu kỳ báo cáo): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 10 / Metabase 10

---

### Return Impact Analysis [All] (id: 75) — MATCH

**Blueprint tabs**: KPI Overview, Channel Analysis, Return Reasons, Cohort & Trend, Return-prone SKUs
**Metabase tabs**: KPI Overview, Channel Analysis, Return Reasons, Cohort & Trend, Return-prone SKUs

**Blueprint questions** (15 unique + 5× Chu kỳ báo cáo): Return Rate MTD, Refund Liability MTD, Days-to-Return Histogram (KPI), Top Return Reason MTD, Return Rate by Channel, Channel Return Detail Table, Top 10 Return Reasons by Revenue Impact, Return Reason by Volume, Daily Return Count Last 90 Days, Return Lag Cohort Table, Top 20 SKUs by Refund Amount (MTD), Top 20 SKUs by Return Rate (MTD), Return Reason × Top SKUs Matrix, SKU Action Table (Prescriptive)
**Metabase questions** (15 unique + 5× Chu kỳ báo cáo): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 14 / Metabase 14

---

### Cost Ledger Analyzer [All] (id: 74) — MATCH

**Blueprint tabs**: none (single-page dashboard)
**Metabase tabs**: none

**Blueprint questions** (10): Chu kỳ báo cáo, Total Costs MTD, COGS Ratio MTD, Platform Fees Ratio MTD, Voucher Subsidy Ratio MTD, Cost Composition by Month, Platform Fees Ratio Trend (6 Months), Top 20 Channels by Total Cost, Cost Breakdown Donut MTD, Cost by Channel Category — Stacked Bar
**Metabase questions** (10): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 1 / Metabase 1

---

### Product Cost-to-Margin Heatmap [Cross] (id: 76) — MATCH

**Blueprint tabs**: none (single-page dashboard)
**Metabase tabs**: none

**Blueprint questions** (10): Chu kỳ báo cáo, Total SKUs Sold, Avg Margin %, Margin Outlier Count, COGS Variance Alert Count, SKU Margin vs Revenue Scatter, Top 50 SKU Detail Table, Margin Distribution Histogram, COGS Variance Alert Table, SKU Margin by Channel
**Metabase questions** (10): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 6 / Metabase 6

---

### Accounting Reconciliation Cockpit [Internal] (id: 78) — MATCH

**Blueprint tabs**: Recon Status Overview, Exception Table, Drift Trend, Reconciliation Funnel
**Metabase tabs**: Recon Status Overview, Exception Table, Drift Trend, Reconciliation Funnel

**Blueprint questions** (15 unique + 4× Chu kỳ báo cáo): MISA Coverage % — All Time, Unmatched Rate % — All Time, Shopee Fee Coverage %, Unmatched Orders Count (Last 30 Days), Recon Status Distribution, Recon Status Donut, Revenue at Risk by Recon Status, Unmatched Orders — Missing MISA Invoice, Shopee Orders Missing Fee Data, Daily Unmatched % Trend (Last 30 Days), Daily Orders Volume vs Unmatched Count, Reconciliation Funnel — Completed Orders, MISA Coverage by Channel, Recon Coverage Trend by Month
**Metabase questions** (15 unique + 4× Chu kỳ báo cáo): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 8 / Metabase 8

---

### Finance Services Revenue [All] (id: 95) — MATCH

**Blueprint tabs**: Tổng Quan, US HR Services, Kiểm Tra Dịch Vụ Khác
**Metabase tabs**: Tổng Quan, US HR Services, Kiểm Tra Dịch Vụ Khác

**Blueprint questions** (13 unique + 3× Chu kỳ báo cáo): Doanh Thu Dịch Vụ MTD, Dịch Vụ Active (Số lượng), Dịch Vụ YTD, Dịch Vụ % Tổng Doanh Thu, Xu Hướng Doanh Thu Dịch Vụ 12 Tháng, Phân Bổ Doanh Thu Theo Loại Dịch Vụ, Top 5 Dịch Vụ Tháng Này, US HR Revenue MTD (DVCCNS + DVCCNS1), Xu Hướng DVCCNS + DVCCNS1 — 24 Tháng, DVCCNS vs DVCCNS1 — Breakdown, Danh Sách Dịch Vụ Active/Inactive, Điều Chỉnh CPBH Theo Tháng
**Metabase questions** (13 unique + 3× Chu kỳ báo cáo): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 7 / Metabase 7

---

### Channel Profitability Monthly [Cross] (id: 33) — MINOR_DIFF

**Blueprint tabs**: Channel Overview, Trends & Product Detail
**Metabase tabs**: Channel Overview, Trends & Product Detail

**Blueprint questions** (11 unique + 2× Chu kỳ báo cáo): Gross Margin %, Total Revenue, Total COGS, Total Gross Profit, Margin by Channel, Revenue vs COGS by Channel, Margin Trend by Channel, Revenue Mix Trend, Top Products by Profit, Low-Margin Products
**Metabase questions** (11 unique + 2× Chu kỳ báo cáo): same set

**Missing from Metabase**: none
**Extra in Metabase**: none
**Text cards**: Blueprint 7 / Metabase 6

**Note**: Text card count off by 1. Blueprint has 7 text cards (Boi canh mua vu, Tab Overview Heading, Channel Comparison Heading, Source & Freshness ×2, Trends Heading, Product Detail Heading). Metabase has 6. One text card likely missing — probable candidate: "Trends Heading" (tab 2, row 0) or "Tab Overview Heading" (tab 1). All questions and tabs match exactly.

---

## Methodology Notes
- Question names compared as unique sets (case-insensitive, normalized). "Chu kỳ báo cáo" per-tab instances are counted once in unique set — count match confirmed separately by total dashcard count.
- Text cards = dashcards where `card_id` is null (virtual/markdown cards).
- Metabase API: `GET /api/dashboard/{id}` → `dashcards` array.
- Blueprint source: `docs/analytics-handbook/blueprints/finance_*.md` + `channel_profitability_monthly.md`.
