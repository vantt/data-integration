---
title: Channel Profitability Monthly
archetype: Executive Pulse
status: final
last_modified: 2026-04-10
domain_refs: [domains/finance.md, domains/product.md]
---

## Design Spec: Channel Profitability Monthly

### Brief

- **Audience:** CEO, Finance, Sales Director — review trong buổi MBR hàng tháng
- **Time budget:** 5-10 phút, glanceable overview rồi drill-down nếu cần
- **Primary question:** Kênh nào tạo margin cao nhất và kênh nào đang ăn mòn lợi nhuận?
- **Decision enabled:** Điều chỉnh product mix theo kênh, chính sách giá, phân bổ traffic
- **Comparison frame:** MoM (tháng này vs tháng trước), cross-channel (kênh vs kênh), vs threshold (40% margin)
- **Archetype:** Executive Pulse (2 views, glanceable → optional drill-down)
- **Domain references:** [domains/finance.md](../domains/finance.md), [domains/product.md](../domains/product.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude promo lines | `NOT is_promo_line` | All cards | Gift/promo items have zero revenue, distort margin |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Period | date/range | Last 3 months | All cards | View different accounting periods |
| Channel | category/single-select | All | All cards | Isolate specific channel for analysis |

### Views

Multi-view: **Channel Overview**, **Trends & Product Detail**

---

### Composition — View 1: Channel Overview

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Biên lợi nhuận gộp theo kênh — kênh nào hiệu quả nhất?" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Gross Margin % | hero | gauge | positive (>40%) / warning (25-40%) / negative (<25%) | one-third × medium, prominent | Biên lãi gộp tổng — on-track hay không? | vs threshold (40%) |
| 3 | B | Total Revenue | supporting | single-value-with-trend | primary | one-quarter × short, standard | Tổng doanh thu MISA kỳ này | vs previous period (MoM) |
| 4 | B | Total COGS | supporting | single-value-with-trend | negative | one-quarter × short, standard | Tổng giá vốn kỳ này | vs previous period (MoM) |
| 5 | B | Total Gross Profit | supporting | single-value-with-trend | positive / negative (based on MoM) | one-quarter × short, standard | Lãi gộp tuyệt đối | vs previous period (MoM) |
| 6 | C | "So sánh hiệu quả giữa các kênh bán hàng" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Margin by Channel | breakdown | horizontal-bar | conditional-above (>40% green) / conditional-below (<25% red) | half × medium, standard | Ranking kênh theo margin % | rank + vs threshold |
| 8 | D | Revenue vs COGS by Channel | breakdown | grouped-bar | series-1 (revenue) + series-2 (COGS) | half × medium, standard | Scale doanh thu vs giá vốn từng kênh | cross-channel |

### Composition — View 2: Trends & Product Detail

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 9 | A | "Xu hướng margin theo kênh — kênh nào đang cải thiện?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 10 | B | Margin Trend by Channel | trend | multi-line-chart | series-1..series-4 (per channel) + muted (reference 40%) | half × medium, standard | Hướng đi margin từng kênh qua các tháng | vs threshold (40% line) + MoM |
| 11 | B | Revenue Mix Trend | trend | stacked-bar-time | series-1..series-4 | half × medium, standard | Tỷ trọng doanh thu từng kênh thay đổi thế nào | composition over time |
| 12 | C | "Sản phẩm ảnh hưởng lợi nhuận — sản phẩm nào tạo lãi, sản phẩm nào kéo xuống?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 13 | D | Top Products by Profit | breakdown | horizontal-bar | primary | half × medium, standard | Top 15 sản phẩm đóng góp lãi gộp nhiều nhất | rank |
| 14 | D | Low-Margin Products | detail | data-table-formatted | conditional-below (<15% red) / conditional-above (>40% green) | half × tall, compact | Sản phẩm margin < 25%, cần review giá/nguồn cung | rank (bottom N) |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Gross Margin % | Red zone | < 25% | Khẩn cấp: review giá vốn tăng hay giá bán giảm. Kiểm tra nhà cung cấp. |
| Gross Margin % | Warning zone | 25-40% | Monitor tháng sau, kiểm tra product mix shift. |
| Margin by Channel | Gap > 15 điểm % | Kênh cao nhất vs thấp nhất chênh > 15% | Đánh giá chiến lược: đẩy traffic sang kênh margin cao? |
| Margin by Channel | ECOM < DAILY - 10% | ECOM margin thấp hơn DAILY đáng kể | Phí sàn ăn mòn margin → xem Shopee Channel Economics dashboard. |
| Margin Trend by Channel | Downward 3+ months | Bất kỳ kênh nào giảm liên tục | Deep dive: product mix thay đổi? COGS tăng? Discount nhiều? |
| Low-Margin Products | Product margin < 15% | Sản phẩm chiếm > 5% revenue mà margin < 15% | Review giá bán hoặc ngừng bán qua kênh đó. |

<!--
Dashboard Finish Checklist:
- [x] Hero card (Gross Margin %) top-left, gauge, prominent — visually dominant
- [x] Every KPI has comparison: vs threshold, vs previous period, rank, composition
- [x] Row widths: B=6+4+4+4=18, D=9+9=18, others full-width ✓
- [x] Card count: View 1=8, View 2=6 → total 14, within Pulse extended limit (2 views × 10)
- [x] Semantic color tokens only — no hex
- [x] Semantic size tokens only — no pixels
- [x] Annotations specific and imperative
- [x] Action Map complete for all signal cards
- [x] Number formatting: VND currency, % with 1 decimal
- [x] Cross-reference to Shopee Channel Economics for ECOM drill-down
-->
