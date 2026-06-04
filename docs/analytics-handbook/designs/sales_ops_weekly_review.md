---
title: "Sales Ops Weekly Review (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-01
domain_refs: [domains/sales.md, domains/customer_support.md]
---

## Design Spec: Sales Ops Weekly Review (Redesign)

### Brief

- **Audience:** Sales Operator, Customer Support Lead, Store Manager — Monday morning working session
- **Time budget:** 10-20 min across 3 tabs. Tab 1 for quick pulse (5 min), Tab 2-3 for deep-dive
- **Primary question:** "Tuan qua van hanh co on khong? Don hang, kenh ban, team, thanh toan — dau can chu y?"
- **Decision enabled:** Dieu phoi nhan luc theo kenh/chi nhanh, follow up don huy/tra, danh gia performance nhan vien
- **Comparison frame:** WoW (this week vs previous week) — operational weekly rhythm
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer_support.md](../domains/customer_support.md)

### Redesign Rationale

Dashboard hien tai co nhieu van de:

1. **Khong co narrative flow** — 0 annotations, 16 cards xep phat khong phan tang
2. **Hero khong ro** — Total Orders la scalar nho, khong noi bat
3. **KPIs thieu WoW** — chi hien con so tuan nay, khong co trend/comparison
4. **Single view qua tai** — 16+ cards tren 1 view cho Operational Cockpit
5. **Peak Hour** render bang pivot table — nen la heatmap
6. **Payment section** lac long, khong co conditional formatting canh bao

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude current incomplete week | `ordered_at < date_trunc('week', current_date)` | All cards | Tuan hien tai chua ket thuc — so sanh khong cong bang |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last 7 days (prev Mon-Sun) | All cards | Xem tuan cu hon |
| Branch/Location | category/single-select | All | All cards | Team lead chi xem chi nhanh minh |

### Views

Multi-view — 3 views:
1. Tong quan tuan (Weekly Overview)
2. Kenh & Chi nhanh (Channels & Branches)
3. Doi ngu & Thanh toan (Team & Payments)

---

### View 1 — Tong quan tuan

**Narrative flow:** "Tuan nay on khong?" → "KPIs chinh?" → "Trang thai don hang?" → "Xu huong hang ngay va gio cao diem?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Review ket qua tuan — doanh thu, don hang, chat luong xu ly" | annotation | text-annotation | structural | full-width x minimal | Section heading — subtitle: "Sales Ops — Tuan qua van hanh co on khong?" | — |
| 2 | B | Total Orders | hero | single-value-with-trend | primary, positive/negative (WoW) | one-third x short, prominent | Tong don hang tuan — con so van hanh quan trong nhat | vs previous period (WoW %) |
| 3 | B | Net Revenue | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Doanh thu thuan | vs previous period (WoW %) |
| 4 | B | AOV | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Gia tri trung binh moi don | vs previous period (WoW %) |
| 5 | B | Completed % | supporting | gauge | positive/warning/negative (zones: 90-100/80-89/0-79) | one-quarter x short | Ty le don hoan thanh — target > 90% | vs benchmark (zones) |
| 6 | C | "Kiem tra trang thai don hang — completion rate va cancelled/returns" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Order Status Distribution | breakdown | donut | series-1..series-4 (COMPLETED=positive, OPEN=neutral, CANCELLED=negative, ARCHIVED=muted) | one-third x medium | Phan bo 4 trang thai don | composition |
| 8 | D | Fulfilment Status Breakdown | breakdown | horizontal-bar | series-1..series-N | one-third x medium | Ranking trang thai giao hang | rank/position |
| 9 | D | Cancelled & Returns | supporting | data-table-formatted | conditional-above on WoW Change % (> 100% = negative) | one-third x medium, compact | Cancelled + Return count voi WoW flag — RED neu tang > 2x | vs previous period (WoW %) |
| 10 | E | "Phan tich xu huong 14 ngay — volume, AOV, va gio cao diem" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 11 | F | Daily Orders (14 days) | trend | combo-chart | primary (this week bars) + muted (last week bars) + accent (AOV line) | two-thirds x medium | Volume + AOV trend 14 ngay — spot day-of-week patterns | vs previous period (WoW overlay) |
| 12 | F | Peak Hour Heatmap | breakdown | heatmap | conditional-range (low=muted, high=accent) | one-third x medium | Cuong do don hang theo gio x thu — plan ca truc | intensity matrix |

---

### View 2 — Kenh & Chi nhanh

**Narrative flow:** "Kenh nao chiem workload nhieu nhat?" → "Kenh nao tang/giam dot bien?" → "Chi nhanh nao ban nhieu nhat?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 13 | A | "Xac dinh kenh chiem workload — ranking orders va revenue" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 14 | B | Orders by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh theo volume don hang | rank/position |
| 15 | B | Revenue by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh theo doanh thu | rank/position |
| 16 | C | "So sanh hieu suat kenh WoW — highlight bien dong > 30%" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 17 | D | Channel Performance Table | detail | data-table-formatted | conditional-above/conditional-below on WoW Change % | full-width x medium | Channel, Orders, Revenue, AOV, WoW Orders %, WoW Revenue % — highlight kenh bien dong > 30% | vs previous period (WoW) |
| 18 | E | "Danh gia hieu suat chi nhanh — volume va WoW change" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 19 | F | Orders by Branch | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking chi nhanh theo volume | rank/position |
| 20 | F | Branch Performance Table | detail | data-table-formatted | conditional-above/conditional-below on WoW Change % | half x medium, compact | Branch, Orders, Revenue, WoW Orders % | vs previous period (WoW) |

---

### View 3 — Doi ngu & Thanh toan

**Narrative flow:** "Social commerce tuan nay the nao?" → "Nhan vien nao ban tot nhat?" → "Thanh toan co van de gi?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 21 | A | "Theo doi hieu suat Social Commerce — revenue, orders, AOV" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 22 | B | Social Revenue | supporting | single-value-with-trend | primary, positive/negative (WoW) | one-third x short, prominent | Doanh thu tu kenh social | vs previous period (WoW %) |
| 23 | B | Social Orders | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-third x short, standard | So don tu social | vs previous period (WoW %) |
| 24 | B | Social AOV | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-third x short, standard | AOV kenh social — so voi AOV chung | vs previous period (WoW %) |
| 25 | C | "Danh gia hieu suat nhan vien — ranking doanh thu va top social" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 26 | D | Staff Revenue (All Channels) | breakdown | horizontal-bar | primary | half x medium | Ranking nhan vien theo doanh thu toan kenh | rank/position |
| 27 | D | Top Staff — Social Channels | detail | data-table-formatted | conditional-above on Revenue (top 3 = accent) | half x medium, compact | Staff, Orders, Revenue, AOV — chi social channels | rank/position |
| 28 | E | "Kiem tra thanh toan va doi soat — phan bo PTTT va pending alert" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 29 | F | Payment Method Distribution | breakdown | donut | series-1..series-5 | one-third x medium | Phan bo phuong thuc thanh toan | composition |
| 30 | F | Payment Status Summary | detail | data-table-formatted | conditional-below on pending (> 5% total = negative) | two-thirds x medium, compact | Status, Orders, Amount — flag pending > 5% | vs benchmark (5% threshold) |
| 31 | G | "Source: fact_orders · Updated weekly (Mon-Sun) · Excludes incomplete current week" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Total Orders (hero) | Drop | WoW < -15% | Kiem tra kenh ban hang (View 2), kiem tra co ngay le/event |
| Completed % (gauge) | Below warning | < 80% | Kiem tra don bi nghen, review quy trinh xu ly |
| Cancelled & Returns | Spike | WoW Change > 100% | Dieu tra don huy theo kenh, kiem tra chat luong san pham |
| Peak Hour Heatmap | Shift | Peak gio thay doi so tuan truoc | Dieu chinh lich truc nhan vien |
| Channel Performance Table | Kenh sut giam | WoW Change > 30% | Lien he team kenh, xac dinh nguyen nhan |
| Social Revenue | Drop | WoW < -20% | Kiem tra tin nhan chua doc, bai dang, staff online |
| Payment Status Summary | Pending cao | Pending > 5% total | Doi soat voi ke toan, kiem tra gateway |

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (WoW)
- [x] Text annotations dung imperative voice
- [x] Action Map day du
- [x] Hero card noi bat (one-third, prominent)
- [x] Row widths sum = full-width (18 cols)
- [x] Density Cockpit: V1=12, V2=8, V3=10
- [x] Moi view co section divider
- [x] Color tokens nhat quan

### Summary of Changes

| Aspect | Before (Current Blueprint) | After (Redesign) |
|--------|---------------------------|------------------|
| Views | 1 single view (16 cards) | 3 tabs: Tong quan, Kenh & Chi nhanh, Doi ngu & Thanh toan |
| Annotations | 0 | 10 section headings with descriptive content |
| Hero | Unclear (plain scalar) | Total Orders with WoW trend, prominent size |
| KPI comparisons | None — plain scalars | WoW % integrated into all KPI cards |
| Completed % | Plain scalar with suffix | Gauge with 3 color zones (90/80/0) |
| Daily Orders | Simple bar | Combo-chart: orders bars (this/last week) + AOV line |
| Peak Hour | Pivot table | Heatmap with conditional-range color |
| Cancelled/Returns | 2 separate scalars | Combined formatted table with WoW flags |
| Channel analysis | 1 bar + no detail | 2 bars (orders + revenue) + formatted WoW table |
| Branch analysis | 1 bar alone | Bar + formatted WoW table side-by-side |
| Social Commerce | 2 plain scalars | 3 KPIs with WoW (Revenue, Orders, AOV) |
| Staff performance | 1 full-width bar | Bar + formatted table side-by-side |
| Payment section | Pie + plain table | Donut + formatted table with pending threshold alert |
| Conditional formatting | None | 5 cards with conditional formatting |
| Total cards | 16 | 30 (across 3 tabs — avg 10 per tab) |
