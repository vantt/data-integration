---
title: Shopee Channel Economics
archetype: Operational Cockpit
status: final
last_modified: 2026-04-10
domain_refs: [domains/finance.md]
---

## Design Spec: Shopee Channel Economics

### Brief

- **Audience:** Sales Ops, CS Lead — kiểm tra chi phí Shopee trong review tuần/tháng
- **Time budget:** 10-15 phút, trong buổi review periodic
- **Primary question:** Shopee đang giữ lại bao nhiêu % doanh thu của chúng ta?
- **Decision enabled:** Tối ưu giá bán, đánh giá lại chi phí dịch vụ Shopee, escalate nếu margin giảm
- **Comparison frame:** MoM (tháng này vs tháng trước), vs threshold (75% settlement target)
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/finance.md](../domains/finance.md) > Shopee Platform Economics

### Constraints & Filters

**Business Constraints** — luôn áp dụng, hardcode trong SQL:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Only released payouts | `payout_released_at IS NOT NULL` | All cards | Unreleased payouts have incomplete fee data |

**Interactive Filters** — user có thể thay đổi:

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Payout period | date/range | Last 30 days | All cards | View different payout periods |
| Order type | category/single-select | All | All cards (optional) | Isolate normal vs return orders |

### Views

Multi-view: **Settlement Overview**, **Trends & Details**

---

### Composition — View 1: Settlement Overview

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Monitor chi phí bán hàng Shopee — tỷ lệ tiền thực nhận sau phí sàn" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Settlement Margin % | hero | gauge | positive (>75%) / warning (60-75%) / negative (<60%) | one-third × medium, prominent | Shopee giữ lại bao nhiêu % — on-track hay không? | vs threshold (75%) |
| 3 | B | Gross Revenue | supporting | single-value-with-trend | primary | one-quarter × short, standard | Tổng doanh thu Shopee kỳ này | vs previous period |
| 4 | B | Net Settlement | supporting | single-value-with-trend | secondary | one-quarter × short, standard | Tiền thực nhận từ Shopee | vs previous period |
| 5 | B | Platform Fee Rate % | supporting | single-value-with-trend | negative (>20%) / warning (15-20%) / neutral (<15%) | one-quarter × short, standard | Tổng phí sàn trên doanh thu | vs previous period |
| 6 | C | "Phân tích cơ cấu phí — loại phí nào chiếm nhiều nhất?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Fee Breakdown | breakdown | horizontal-bar | series-1..series-7 | half × medium, standard | Ranking loại phí theo giá trị tuyệt đối | rank |
| 8 | D | Revenue → Settlement Flow | breakdown | waterfall | positive + negative | half × medium, standard | Gross Revenue bị ăn mòn bởi loại phí nào, còn lại Net Settlement | additive composition |

### Composition — View 2: Trends & Details

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 9 | A | "Xu hướng settlement — margin đang cải thiện hay xấu đi?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 10 | B | Settlement Margin Trend | trend | line-chart | primary + muted (reference line 75%) | half × medium, standard | Hướng đi margin theo tháng | vs threshold (75% line) |
| 11 | B | Fee Composition Trend | trend | stacked-bar-time | series-1..series-5 | half × medium, standard | Cấu thành phí thay đổi qua từng tháng | composition over time |
| 12 | C | "Chi tiết đơn hàng — đơn nào có settlement thấp nhất?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 13 | D | Orders with Lowest Settlement | detail | data-table-formatted | conditional-below (<50% red) | full-width × tall, compact | Bottom 20 đơn hàng theo settlement %, drill-down investigation | rank (bottom N) |
| 14 | E | "Hiệu quả theo sản phẩm — sản phẩm nào bị mất margin nhiều nhất trên Shopee?" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 15 | F | Product Settlement Summary | detail | data-table-formatted | conditional-below (<60% margin red), conditional-above (>80% green) | full-width × tall, compact | Revenue, settlement, margin % theo sản phẩm | rank by margin % |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Settlement Margin % | Drop to red zone | < 60% | Kiểm tra fee breakdown — loại phí nào tăng bất thường. Escalate Finance. |
| Settlement Margin % | Warning zone | 60-75% | Monitor tuần tới, so sánh với fee composition trend. |
| Platform Fee Rate % | Spike | > 20% hoặc MoM tăng > 3 điểm % | Liên hệ Shopee kiểm tra tier phí, chương trình mới. |
| Settlement Margin Trend | Downward 3+ tháng liên tiếp | Margin giảm liên tục | Đánh giá lại chiến lược Shopee: tăng giá, giảm dịch vụ phụ, hoặc chuyển traffic sang kênh khác. |
| Orders with Lowest Settlement | Đơn hàng < 50% settlement | settlement_margin < 50% | Kiểm tra từng đơn: voucher lớn? Hoàn hàng? Phí Xtra? |
| Product Settlement Summary | Sản phẩm margin < 60% | gross_margin < 60% cho sản phẩm | Review giá bán sản phẩm đó trên Shopee, so sánh với giá kênh khác. |

<!--
Dashboard Finish Checklist:
- [x] Hero card (Settlement Margin %) ở row đầu tiên, visually dominant (one-third, gauge, prominent)
- [x] Mỗi KPI có ≥1 comparison (vs threshold, vs previous period, rank)
- [x] Row widths = full-width: B=6+4+4+4=18, D=9+9=18, others full-width
- [x] Max 15 cards (8 view1 + 7 view2) — within Cockpit limit of 16
- [x] Color tokens only — no hex codes
- [x] Size tokens only — no pixel values
- [x] Status colors paired with thresholds (gauge zones, conditional formatting)
- [x] Annotations use imperative voice, specific content
- [x] Action Map covers all signal cards
- [x] Number formatting: VND currency, % with 1 decimal
-->
