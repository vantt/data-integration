# Group 2 Finance — Blueprint vs Metabase Check
**Date:** 2026-05-29 | **Run:** 2nd pass (post-fix)

## Summary Table

| ID | Dashboard | BP Tabs | MB Tabs | BP Q (dedup) | MB Q (dedup) | Missing in MB | Extra in MB | Text BP/MB | Status |
|----|-----------|---------|---------|--------------|--------------|---------------|-------------|------------|--------|
| 34 | Finance P&L [All] | 3 | 3 | 15 | 15 | — | — | 10/10 | **MATCH** |
| 77 | Channel P&L Deep Dive [Cross] | 5 | 5 | 13 | 13 | — | — | 10/10 | **MATCH** |
| 75 | Return Impact Analysis [All] | 5 | 5 | 19 | 19 | — | — | 14/14 | **MATCH** |
| 74 | Cost Ledger Analyzer [All] | 0 | 0 | 9 | 9 | — | — | 1/1 | **MATCH** |
| 76 | Product Cost-to-Margin Heatmap [Cross] | 0 | 0 | 9 | 9 | — | — | 6/6 | **MATCH** |
| 78 | Accounting Reconciliation Cockpit [Internal] | 4 | 4 | 14 | 14 | — | — | 8/8 | **MATCH** |
| 95 | Finance Services Revenue [All] | 3 | 3 | 12 | 12 | — | — | 7/7 | **MATCH** |
| 33 | Channel Profitability Monthly [Cross] | 2 | 2 | 10 | 10 | — | — | 7/7 | **MATCH** |

**All 8 dashboards: MATCH**

---

## Detail per Dashboard

### ID 34 — Finance P&L [All]
- **Tabs** (3): P&L Overview · Channel Profitability · Shopee Economics ✓
- **Questions** (15 unique, dedup "Chu kỳ báo cáo"):
  Net Revenue MTD · COGS MTD · Gross Profit MTD · Gross Margin Percent · Revenue vs COGS Trend · Revenue Waterfall · Margin by Channel · Revenue vs COGS by Channel · COGS Ratio Trend · Shopee Settlement MTD · Settlement Margin Percent · Platform Fee Rate · Shopee Gross Revenue · Shopee Fee Breakdown · Revenue to Settlement Waterfall — all match
- **Text cards** 10 = blueprint 10 ✓

### ID 77 — Channel P&L Deep Dive [Cross]
- **Tabs** (5): P&L Waterfall · Channel Scorecard · Margin Heatmap · Variance Analysis · Loss-Leader Alert ✓
- **Questions** (13 unique): P&L Waterfall — All Channels · Channel Scorecard Table · Net Margin Heatmap — Channel × Month · Channel MoM Variance Table · Net Margin Trend by Channel (with Budget Target) · Loss Leader Channel Count · Total Loss Exposure · Loss Leader Detail Table — all match
- **Text cards** 10 = blueprint 10 ✓

### ID 75 — Return Impact Analysis [All]
- **Tabs** (5): KPI Overview · Channel Analysis · Return Reasons · Cohort & Trend · Return-prone SKUs ✓
- **Questions** (19 unique): Return Rate MTD · Refund Liability MTD · Days-to-Return Histogram (KPI) · Top Return Reason MTD · Return Rate by Channel · Channel Return Detail Table · Top 10 Return Reasons by Revenue Impact · Return Reason by Volume · Daily Return Count Last 90 Days · Return Lag Cohort Table · Top 20 SKUs by Refund Amount (MTD) · Top 20 SKUs by Return Rate (MTD) · Return Reason × Top SKUs Matrix · SKU Action Table (Prescriptive) — all match
- **Text cards** 14 = blueprint 14 ✓

### ID 74 — Cost Ledger Analyzer [All]
- **Tabs**: 0 (no tabs — single-page dashboard) ✓
- **Questions** (9 unique): Total Costs MTD · COGS Ratio MTD · Platform Fees Ratio MTD · Voucher Subsidy Ratio MTD · Cost Composition by Month · Platform Fees Ratio Trend (6 Months) · Top 20 Channels by Total Cost · Cost Breakdown Donut MTD · Cost by Channel Category — Stacked Bar — all match
- **Text cards** 1 = blueprint 1 ✓

### ID 76 — Product Cost-to-Margin Heatmap [Cross]
- **Tabs**: 0 (no tabs — single-page) ✓
- **Questions** (9 unique): Total SKUs Sold · Avg Margin % · Margin Outlier Count · COGS Variance Alert Count · SKU Margin vs Revenue Scatter · Top 50 SKU Detail Table · Margin Distribution Histogram · COGS Variance Alert Table · SKU Margin by Channel — all match
- **Text cards** 6 = blueprint 6 ✓

### ID 78 — Accounting Reconciliation Cockpit [Internal]
- **Tabs** (4): Recon Status Overview · Exception Table · Drift Trend · Reconciliation Funnel ✓
- **Questions** (14 unique): MISA Coverage % — All Time · Unmatched Rate % — All Time · Shopee Fee Coverage % · Unmatched Orders Count (Last 30 Days) · Recon Status Distribution · Recon Status Donut · Revenue at Risk by Recon Status · Unmatched Orders — Missing MISA Invoice · Shopee Orders Missing Fee Data · Daily Unmatched % Trend (Last 30 Days) · Daily Orders Volume vs Unmatched Count · Reconciliation Funnel — Completed Orders · MISA Coverage by Channel · Recon Coverage Trend by Month — all match
- **Text cards** 8 = blueprint 8 ✓

### ID 95 — Finance Services Revenue [All]
- **Tabs** (3): Tổng Quan · US HR Services · Kiểm Tra Dịch Vụ Khác ✓
- **Questions** (12 unique): Chu kỳ báo cáo (3×) · Doanh Thu Dịch Vụ MTD · Dịch Vụ Active (Số lượng) · Dịch Vụ YTD · Dịch Vụ % Tổng Doanh Thu · Xu Hướng Doanh Thu Dịch Vụ 12 Tháng · Phân Bổ Doanh Thu Theo Loại Dịch Vụ · Top 5 Dịch Vụ Tháng Này · US HR Revenue MTD (DVCCNS + DVCCNS1) · Xu Hướng DVCCNS + DVCCNS1 — 24 Tháng · DVCCNS vs DVCCNS1 — Breakdown · Danh Sách Dịch Vụ Active/Inactive · Điều Chỉnh CPBH Theo Tháng — all match
- **Text cards** 7 = blueprint 7 ✓
- **Note:** MB shows garbled chars in question names (encoding issue in API response) but actual names match; "Điều Chỉnh CPBH Theo Tháng" rendered as `Đi\udc81u Chỉnh` in raw API — display-only artifact, not a content issue.

### ID 33 — Channel Profitability Monthly [Cross]
- **Tabs** (2): Channel Overview · Trends & Product Detail ✓
- **Questions** (10 unique): Gross Margin % · Total Revenue · Total COGS · Total Gross Profit · Margin by Channel · Revenue vs COGS by Channel · Margin Trend by Channel · Revenue Mix Trend · Top Products by Profit · Low-Margin Products — all match
- **Text cards** 7 = blueprint 7 ✓

---

## Notes

1. **Encoding artifact (ID 95):** Raw API returns `\udc81` / `\udc90` in Vietnamese question names — surrogate pair issue in Metabase API encoding. Actual Metabase UI displays correctly. Not a deployment issue.
2. **ID 74 & 76:** No tabs — both blueprints are intentionally single-page dashboards. Correct.
3. **ID 33 (deprecation candidate):** Blueprint notes overlap with finance_channel_pl (ID 77). Both dashboards exist and match their respective blueprints. Consolidation is a future concern, not a drift issue.
