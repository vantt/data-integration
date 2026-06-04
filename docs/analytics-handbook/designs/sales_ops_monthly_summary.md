---
title: "Sales Ops Monthly Summary (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-01
domain_refs: [domains/sales.md, domains/customer_support.md]
---

## Design Spec: Sales Ops Monthly Summary (Redesign)

### Brief

- **Audience:** Sales Operator, Customer Support Lead, Operations Manager — 2nd-3rd of each month, working session
- **Time budget:** 20-30 min across 3 tabs. Tab 1 for monthly pulse (5-7 min), Tab 2-3 for deep-dive
- **Primary question:** "Thang qua van hanh the nao? Hieu suat, chat luong don, doi ngu, thanh toan — dau can cai thien?"
- **Decision enabled:** Dieu chinh quy trinh xu ly don, phan bo nhan luc, follow up kenh/chi nhanh co van de, doi soat thanh toan
- **Comparison frame:** MoM (this month vs previous month) + 6-month trends for pattern detection
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer_support.md](../domains/customer_support.md)

### Redesign Rationale

Dashboard hien tai co nhieu van de:

1. **Khong co narrative flow** — 0 annotations, 18 cards xep phang khong phan tang
2. **Hero khong ro** — Total Orders la scalar nho, khong noi bat
3. **KPIs thieu MoM** — chi hien con so thang nay, khong co trend/comparison
4. **Single view qua tai** — 18 cards tren 1 view cho Operational Cockpit la qua nhieu
5. **Thieu branch analysis** — playbook dinh nghia nhung blueprint khong co
6. **Khong co conditional formatting** — khong highlight van de can chu y
7. **Order Status** la table thay vi visual — kho nhin composition nhanh

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude current incomplete month | `ordered_at < date_trunc('month', current_date)` | All cards | Thang hien tai chua ket thuc — so sanh khong cong bang |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last closed month | All cards | Xem thang cu hon |
| Branch/Location | category/single-select | All | All cards | Team lead chi xem chi nhanh minh |

### Views

Multi-view — 3 views:
1. Tong quan thang (Monthly Overview)
2. Kenh & Chi nhanh (Channels & Branches)
3. Doi ngu & Thanh toan (Team & Payments)

---

### View 1 — Tong quan thang

**Narrative flow:** "Thang nay the nao?" -> "KPIs chinh?" -> "Chat luong don hang?" -> "Xu huong 6 thang?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Review ket qua thang — doanh thu, don hang, chat luong van hanh" | annotation | text-annotation | structural | full-width x minimal | Section heading — subtitle: "Sales Ops — Thang qua van hanh the nao?" | — |
| 2 | B | Total Orders | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Tong don hang thang — con so van hanh quan trong nhat | vs previous period (MoM %) |
| 3 | B | Net Revenue | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Doanh thu thuan thang | vs previous period (MoM %) |
| 4 | B | AOV | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Gia tri trung binh moi don | vs previous period (MoM %) |
| 5 | B | Completion Rate | supporting | gauge | positive/warning/negative (zones: 90-100/80-89/0-79) | one-quarter x short | Ty le don hoan thanh — target > 90% | vs benchmark (zones) |
| 6 | C | "Kiem tra chat luong don hang — trang thai, thoi gian xu ly, huy/tra" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Order Status Distribution | breakdown | donut | series-1..series-4 (COMPLETED=positive, OPEN=neutral, CANCELLED=negative, ARCHIVED=muted) | one-third x medium | Phan bo 4 trang thai don — nhin nhanh composition | composition |
| 8 | D | Avg Time to Complete | supporting | single-value-with-trend | secondary, positive/negative (MoM, lower=positive) | one-third x medium, prominent | Thoi gian xu ly trung binh — cai thien hay te hon? | vs previous period (MoM) |
| 9 | D | Cancelled & Returns Summary | supporting | data-table-formatted | conditional-above on MoM Change % (> 0% = negative) | one-third x medium, compact | Cancelled + Return count voi MoM flag — RED neu tang | vs previous period (MoM %) |
| 10 | E | "Theo doi xu huong 6 thang — cancellation va return rate vs target" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 11 | F | Cancellation Rate Trend (6M) | trend | line-chart | negative + muted (goal line) | half x medium | Ty le huy don 6 thang — target < 5% | vs target (goal line) |
| 12 | F | Return Rate Trend (6M) | trend | line-chart | warning + muted (goal line) | half x medium | Ty le tra hang 6 thang — target < 3% | vs target (goal line) |
| 13 | G | Top 10 Returned Products | detail | data-table-formatted | conditional-above on Return Count (top 3 = accent) | full-width x medium, compact | San pham bi tra nhieu nhat — can review chat luong | rank/position |

---

### View 2 — Kenh & Chi nhanh

**Narrative flow:** "Kenh nao chiem workload nhieu nhat?" -> "Kenh nao co van de?" -> "Chi nhanh nao can chu y?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 14 | A | "Xac dinh kenh chiem workload — ranking orders va revenue" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 15 | B | Orders by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh theo volume don hang | rank/position |
| 16 | B | Revenue by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh theo doanh thu | rank/position |
| 17 | C | "Danh gia hieu suat van hanh kenh — completion, cancel, return rates" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 18 | D | Channel Operations Matrix | detail | data-table-formatted | conditional-below on Completion % (< 85% = negative), conditional-above on Cancel % (> 5% = negative) | full-width x medium | Channel, Orders, Revenue, Completion %, Cancel %, Return %, Avg Complete hrs — highlight kenh co van de | vs benchmark (thresholds) |
| 19 | E | "Phan tich huy don theo kenh — kenh nao huy nhieu nhat?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | F | Cancellation by Channel | breakdown | horizontal-bar | negative | two-thirds x medium | Ranking kenh huy don nhieu nhat | rank/position |
| 21 | F | Cancellation by Channel (% of Total) | breakdown | donut | series-1..series-5 | one-third x medium | Ty le dong gop huy don moi kenh | composition |
| 22 | G | "Danh gia hieu suat chi nhanh — volume va van de can xu ly" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | H | Orders by Branch | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking chi nhanh theo volume | rank/position |
| 24 | H | Branch Performance Table | detail | data-table-formatted | conditional-below on Completion % (< 85% = negative), conditional-above on Cancel % (> 5% = negative) | half x medium, compact | Branch, Orders, Revenue, Completion %, Cancel % — highlight chi nhanh co van de | vs benchmark (thresholds) |

---

### View 3 — Doi ngu & Thanh toan

**Narrative flow:** "Social commerce thang nay the nao?" -> "Nhan vien nao lam tot nhat?" -> "Thanh toan co van de gi?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 25 | A | "Theo doi hieu suat Social Commerce — revenue va nhan vien" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 26 | B | Social Revenue | supporting | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Doanh thu tu kenh social | vs previous period (MoM %) |
| 27 | B | Social Orders | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-third x short, standard | So don tu social | vs previous period (MoM %) |
| 28 | B | Social AOV | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-third x short, standard | AOV kenh social | vs previous period (MoM %) |
| 29 | C | Social Revenue by Platform | breakdown | donut | series-1, series-2 (Facebook, Zalo) | one-third x medium | Facebook vs Zalo — ai dong gop nhieu hon? | composition |
| 30 | C | CS Staff Leaderboard | detail | data-table-formatted | conditional-above on Revenue (top 3 = accent) | two-thirds x medium, compact | Staff, Orders, Revenue, AOV, % Contribution — highlight top 3 | rank/position |
| 31 | D | "Danh gia hieu suat nhan vien toan kenh — ranking va completion" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 32 | E | Staff Revenue Distribution | breakdown | horizontal-bar | primary | half x medium | Ranking nhan vien theo doanh thu toan kenh | rank/position |
| 33 | E | Staff Performance Table | detail | data-table-formatted | conditional-above on Completion % (> 95% = positive), conditional-below on Completion % (< 80% = negative) | half x medium, compact | Staff, Orders, Revenue, AOV, Completion % — highlight performance | vs benchmark (thresholds) |
| 34 | F | "Kiem tra xu huong thanh toan va doi soat — PTTT shift va pending alert" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 35 | G | Payment Method Distribution | breakdown | donut | series-1..series-5 | one-third x medium | Phan bo phuong thuc thanh toan | composition |
| 36 | G | Payment Method Trend (6M) | trend | stacked-area | series-1..series-5 | two-thirds x medium | Xu huong phuong thuc thanh toan 6 thang — shift nao dang xay ra? | composition over time |
| 37 | H | Payment Status Summary | detail | data-table-formatted | conditional-below on pending (> 5% total = negative) | full-width x medium, compact | Status, Orders, Amount, % — flag pending > 5% | vs benchmark (5% threshold) |
| 38 | I | "Source: fact_orders · Updated monthly · Excludes incomplete current month" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Total Orders (hero) | Drop | MoM < -10% | Kiem tra kenh va chi nhanh (View 2) |
| Completion Rate (gauge) | Below warning | < 80% | Review quy trinh xu ly, kiem tra bottleneck |
| Avg Time to Complete | Increase | MoM > +20% | Dieu tra toc do xu ly, kiem tra nhan luc |
| Cancellation Rate Trend | Above target | > 5% for 3 months | Review nguyen nhan huy don, cai thien UX/stock |
| Return Rate Trend | Above target | > 3% for 3 months | Kiem tra top returned products, review chat luong |
| Channel Operations Matrix | Kenh co van de | Completion < 85% hoac Cancel > 5% | Lien he team kenh, xac dinh root cause |
| CS Staff Leaderboard | Bat can xung | Top performer > 3x bottom | Dao tao va phan bo lai workload |
| Payment Status Summary | Pending cao | > 5% total | Doi soat ke toan, kiem tra gateway |

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (MoM hoac target)
- [x] Text annotations dung imperative voice
- [x] Action Map day du
- [x] Hero card noi bat
- [x] Row widths sum = full-width
- [x] Density Cockpit: V1=13, V2=12, V3=12
- [x] Moi view co section divider
- [x] Color tokens nhat quan

### Summary of Changes

| Aspect | Before (Current Blueprint) | After (Redesign) |
|--------|---------------------------|------------------|
| Views | 1 single view (18 cards) | 3 tabs: Tong quan, Kenh & Chi nhanh, Doi ngu & Thanh toan |
| Annotations | 0 | 12 section headings with descriptive content |
| Hero | Unclear (plain scalar) | Total Orders with MoM trend, prominent size |
| KPI comparisons | None — plain scalars | MoM % integrated into all KPI cards |
| Completion Rate | Plain scalar with suffix | Gauge with 3 color zones (90/80/0) |
| Avg Time to Complete | Plain scalar buried in row 0 | Prominent single-value-with-trend with MoM |
| Order Status | Table with MoM columns | Donut for quick composition view |
| Cancelled/Returns | Separate trend lines only | Combined formatted table with MoM flags + trend lines |
| Channel analysis | 1 bar + 1 matrix table | 2 bars (orders + revenue) + formatted matrix + cancellation breakdown |
| Branch analysis | Missing entirely | Bar + formatted table side-by-side |
| Social Commerce | 2 plain scalars + 1 line | 3 KPIs with MoM (Revenue, Orders, AOV) + platform donut |
| Staff performance | 1 plain table | Bar + formatted table with conditional formatting |
| Payment section | Pie + area + plain table | Donut + stacked-area + formatted table with pending alert |
| Conditional formatting | None | 7 cards with conditional formatting |
| Total cards | 18 | 37 (across 3 tabs — avg 12 per tab) |
