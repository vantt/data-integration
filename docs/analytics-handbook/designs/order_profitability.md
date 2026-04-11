---
title: Order Profitability
archetype: Executive Pulse
status: final
last_modified: 2026-04-10
domain_refs: [domains/finance.md]
---

## Design Spec: Order Profitability

### Brief

- **Audience:** CEO, CFO, Sales Director — review lợi nhuận đơn hàng hàng tháng
- **Time budget:** 5-10 phút, glanceable overview rồi drill-down chi tiết đơn
- **Primary question:** Mỗi đơn hàng lãi/lỗ bao nhiêu và kênh nào tạo channel net profit cao nhất?
- **Decision enabled:** Tối ưu product mix, chiến lược kênh, kiểm soát giá vốn
- **Comparison frame:** Cross-channel, vs threshold (50% gross margin), Shopee vs non-Shopee
- **Archetype:** Executive Pulse (2 views)
- **Domain references:** [domains/finance.md](../domains/finance.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Completed orders only | `status = 'COMPLETED'` | All cards | Draft/cancelled orders have no settled revenue |
| COGS available | `has_cogs = true` | All cards except total orders KPI | Only orders with MISA COGS data are meaningful for P&L |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last 3 months | All cards | View different periods |
| Channel | category/single-select | All | All cards | Isolate specific channel |

### Views

Multi-view: **P&L Overview**, **Order Detail**

### Composition — View 1: P&L Overview

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Lợi nhuận đơn hàng — tổng quan P&L theo kênh" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Avg Gross Margin % | hero | gauge | positive (>50%) / warning (35-50%) / negative (<35%) | one-third × medium, prominent | Biên lãi gộp trung bình — on-track? | vs threshold (50%) |
| 3 | B | Total Gross Profit | supporting | single-value-with-trend | primary | one-quarter × short, standard | Tổng lãi gộp kỳ này | vs previous period |
| 4 | B | Total Channel Net Profit | supporting | single-value-with-trend | positive / negative | one-quarter × short, standard | Lãi ròng sau phí sàn | vs previous period |
| 5 | B | Orders with COGS | supporting | single-value | neutral | one-quarter × short, standard | Số đơn có MISA data (coverage) | — |
| 6 | C | "Lợi nhuận theo kênh — kênh nào tạo giá trị?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Channel Net Margin % | breakdown | horizontal-bar | conditional-above (>50% green) / conditional-below (<25% red) | half × medium, standard | Ranking kênh theo channel net margin | rank + vs threshold |
| 8 | D | Revenue vs COGS vs Fees | breakdown | stacked-bar | series-1 (gross profit) + series-2 (COGS) + series-3 (shopee fees) | half × medium, standard | Cost structure per channel | composition |

### Composition — View 2: Order Detail

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 9 | A | "Chi tiết P&L từng đơn — đơn nào lãi nhiều, đơn nào lỗ?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 10 | B | Margin Distribution | trend | vertical-bar | primary + muted (reference 50%) | half × medium, standard | Phân bố margin — đa số đơn nằm ở vùng nào | histogram |
| 11 | B | Profit by Date | trend | line-chart | primary | half × medium, standard | Xu hướng gross profit theo ngày | trend over time |
| 12 | C | "Danh sách đơn hàng — sắp xếp theo lãi/lỗ" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 13 | D | Order P&L Table | detail | data-table-formatted | conditional-below (margin <20% red) / conditional-above (>50% green) | full-width × tall, compact | Chi tiết từng đơn: revenue, COGS, profit, margin, fees | rank |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Avg Gross Margin % | Red zone | < 35% | Review COGS tăng hay giá bán giảm. Kiểm tra product mix. |
| Channel Net Margin % | Shopee net margin < 30% | Phí sàn ăn mòn lợi nhuận | Xem Shopee Channel Economics, cân nhắc giảm traffic Shopee |
| Channel Net Margin % | Gap > 20 điểm % | Kênh lệch quá lớn | Đẩy traffic sang kênh margin cao |
| Order P&L Table | Orders with margin < 0% | Đơn hàng lỗ | Kiểm tra nguyên nhân: COGS sai? Discount quá sâu? |
| Margin Distribution | >30% orders below 25% | Nhiều đơn margin thấp | Review product pricing strategy |

<!--
Dashboard Finish Checklist:
- [x] Hero card (Avg Gross Margin %) top-left, gauge, prominent
- [x] Every KPI has comparison: vs threshold, vs previous period, rank
- [x] Row widths: B=6+4+4+4=18, D=9+9=18 ✓
- [x] Card count: View 1=8, View 2=5 → total 13
- [x] Semantic color tokens only
- [x] Semantic size tokens only
- [x] Annotations specific
- [x] Action Map complete
-->
