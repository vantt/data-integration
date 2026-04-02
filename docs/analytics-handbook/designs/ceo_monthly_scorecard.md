---
title: CEO Monthly Scorecard
archetype: Executive Pulse
status: final
last_modified: 2026-04-02
domain_refs: [domains/sales.md, domains/customer.md, domains/finance.md]
---

## Design Spec: CEO Monthly Scorecard

### Brief

- **Audience:** CEO, Co-Founders, Board — đọc 1 lần/tháng vào đầu tháng
- **Time budget:** 5–10 phút, chia 3 tab, mỗi tab ~2-3 phút
- **Primary question:** "Tháng vừa rồi kinh doanh thế nào? Có đạt target không?"
- **Decision enabled:** Điều chỉnh chiến lược tháng tới — tăng tốc hay co cụm, đầu tư kênh nào, sản phẩm nào cần hành động
- **Comparison frame:** MoM (tháng này vs tháng trước) + YoY (vs cùng kỳ năm trước) + vs Target
- **Archetype:** Executive Pulse (multi-view — 3 tabs, ~25 cards tổng)
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer.md](../domains/customer.md), [domains/finance.md](../domains/finance.md)

### Constraints & Filters

**Business Constraints** — luôn áp dụng, hardcode trong SQL:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude US channel | `channel_name != 'US'` | All cards | Internal/Export orders, 100% discount — skew revenue metrics |
| Exclude cancelled/voided | `status NOT IN ('CANCELLED', 'Voided')` | Revenue/order cards | Only confirmed orders |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| *Không có* | — | — | — | Executive Pulse — fixed month, zero-interaction |

### Views

Multi-view — 3 tabs:
1. **Hiệu suất tháng** — Hero KPIs, target achievement, revenue trend, waterfall
2. **Kênh & Khách hàng** — Channel analysis, customer portfolio health
3. **Sản phẩm & Vận hành** — Product mix, operational efficiency

---

### Composition — Tab 1: Hiệu suất tháng

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Tháng {MM/YYYY} — Báo cáo hiệu suất kinh doanh tổng hợp" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle — period context | — |
| 2 | B | Monthly Net Revenue | hero | single-value-with-trend | primary, positive/negative (MoM direction) | one-third × short, prominent | Con số quan trọng nhất — doanh thu thuần tháng | vs Previous Month (MoM %) |
| 3 | B | Monthly GMV | supporting | single-value-with-trend | secondary, positive/negative | one-quarter × short, standard | Quy mô giao dịch trước chiết khấu | vs Previous Month |
| 4 | B | Total Orders | supporting | single-value-with-trend | secondary, positive/negative | one-quarter × short, standard | Volume đơn hàng | vs Previous Month |
| 5 | B | AOV | supporting | single-value-with-trend | secondary, positive/negative | one-quarter × short, standard | Giá trị trung bình đơn hàng | vs Previous Month |
| 6 | C | Unique Customers | supporting | single-value-with-trend | secondary, positive/negative | one-third × short, standard | Độ rộng tệp khách hàng | vs Previous Month |
| 7 | C | Target Achievement | supporting | progress-toward-goal | positive/warning/negative (by zone) | one-third × short, standard | Đạt bao nhiêu % mục tiêu doanh thu | vs Target |
| 8 | C | Target Variance | supporting | single-value | positive/negative (above/below) | one-third × short, standard | Gap tuyệt đối so với target | vs Target |
| 9 | D | "Doanh thu theo tuần vs Mục tiêu tháng" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 10 | E | Revenue vs Target (Weekly) | trend | combo-chart | primary (actual bar) + muted (target line, dashed) | two-thirds × medium | Pace trong tháng — actual bar vs cumulative target line | vs Target |
| 11 | E | 6-Month Revenue Trend | trend | multi-line-chart | primary (Net Revenue) + secondary (Gross Revenue) | one-third × medium | Trajectory 6 tháng — đang lên hay xuống | vs Previous Months |
| 12 | F | "Cấu trúc doanh thu — Từ GMV đến Net Revenue" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 13 | G | Revenue Waterfall | breakdown | waterfall | positive (GMV, Net) + negative (Discounts, Returns) | full-width × medium | Yếu tố nào ăn mòn doanh thu — discount vs returns | Composition |

---

### Composition — Tab 2: Kênh & Khách hàng

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 14 | A | "Hiệu suất kênh bán hàng tháng {MM/YYYY}" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 15 | B | Revenue by Channel Category | breakdown | donut | series-1..series-3 | one-third × medium | Tỷ trọng Ecommerce vs Offline vs Internal | Composition |
| 16 | B | Channel Performance Table | detail | data-table-formatted | conditional-above/conditional-below (MoM %) | two-thirds × medium | Chi tiết kênh — Revenue, Orders, AOV, MoM % | vs Previous Month |
| 17 | C | "Xu hướng cấu trúc kênh 6 tháng" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 18 | D | Channel Mix Trend (6M) | trend | stacked-area | series-1..series-3 | full-width × medium | Structural shift — kênh nào đang grow/shrink share | vs Previous Months |
| 19 | E | "Danh mục khách hàng tháng {MM/YYYY}" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 20 | F | New Customers | supporting | single-value-with-trend | positive/negative | one-third × short, standard | Khách mới acquire được | vs Previous Month |
| 21 | F | At Risk Customers | supporting | single-value | warning/negative | one-third × short, standard | Khách sắp mất — cần hành động | Threshold flag |
| 22 | F | Churned Customers | supporting | single-value | negative/neutral | one-third × short, standard | Khách đã mất | Threshold flag |
| 23 | G | Customer Segment Distribution | breakdown | donut | series-1..series-3 | one-third × medium | Tỷ lệ VIP / Loyal / Regular | Composition |
| 24 | G | Revenue by Customer Segment | breakdown | horizontal-bar | series-1..series-3 | two-thirds × medium | Revenue contribution per segment — VIP drives bao nhiêu % | Rank |

---

### Composition — Tab 3: Sản phẩm & Vận hành

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 25 | A | "Top sản phẩm & thương hiệu tháng {MM/YYYY}" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 26 | B | Top 10 Products by Revenue | detail | data-table-formatted | conditional-above/conditional-below (MoM %) | full-width × tall | Sản phẩm nào drive growth, sản phẩm nào suy giảm | vs Previous Month (MoM %) |
| 27 | C | Revenue by Brand | breakdown | horizontal-bar | primary + muted | full-width × medium | Brand nào đang mạnh nhất | Rank |
| 28 | D | "Hiệu quả vận hành tháng {MM/YYYY}" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 29 | E | Discount Rate % | supporting | single-value-with-trend | warning/negative (>15% flag RED) | one-third × short, standard | Chiết khấu ăn bao nhiêu % doanh thu | vs Previous Month + Threshold (15%) |
| 30 | E | Total Discount Amount | supporting | single-value | neutral | one-third × short, standard | Tổng chiết khấu tuyệt đối (VND) | — |
| 31 | E | Return Count | supporting | single-value-with-trend | warning/negative | one-third × short, standard | Số đơn trả hàng | vs Previous Month |
| 32 | F | "Phân tích doanh thu — Từ GMV đến Net Revenue" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 33 | G | Revenue Breakdown Table | detail | data-table | neutral | full-width × short | GMV → Discounts → Returns → Net — dạng bảng chi tiết | Composition |

---

### Visual Polish Checklist

- [x] No 3D charts
- [x] No dual-pie/donut (donuts are on separate tabs)
- [x] Y-axis starts at 0 for bar charts
- [x] Max 5-7 colors per chart (max 3 channel categories)
- [x] No unnecessary gridlines
- [x] Legend only when >1 series
- [x] All charts have descriptive titles
- [x] Number formatting consistent (VND currency, 1 decimal for %)
- [x] Date format consistent (MM/YYYY for months)
- [x] Row width = full-width for all rows
- [x] Hero visually dominant (one-third + prominent)
- [x] Related cards adjacent
- [x] Color is never sole communication channel (all trends have ▲/▼ + %)
- [x] Colorblind safe (text labels always present)
- [x] Max 2 status colors per card
- [x] Consistent color meaning across tabs
- [x] Every KPI has ≥1 comparison
- [x] Source/timestamp via footer annotation where needed
