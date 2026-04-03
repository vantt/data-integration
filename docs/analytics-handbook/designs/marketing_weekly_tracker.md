---
title: "Marketing Weekly Tracker (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/sales.md, domains/customer.md, domains/customer_support.md]
---

## Design Spec: Marketing Weekly Tracker (Redesign)

### Brief

- **Audience:** Marketing Manager, Brand Manager — Monday morning working session
- **Time budget:** 15-25 min across 3 tabs. Tab 1 for channel pulse (5 min), Tab 2-3 for deep-dive
- **Primary question:** "Kenh nao hieu qua nhat tuan nay? Khach moi tu dau? Promotion co dang kiem soat?"
- **Decision enabled:** Dieu chinh ngan sach kenh, tang/giam promotion, doi chien luoc acquisition
- **Comparison frame:** WoW (this week vs previous week) — marketing weekly rhythm
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer.md](../domains/customer.md), [domains/customer_support.md](../domains/customer_support.md)

### Redesign Rationale

Dashboard hien tai co nhieu van de:

1. **Khong co narrative flow** — 0 annotations, 15 cards xep phat khong phan tang
2. **KPIs thieu WoW** — chi hien con so tuan nay, khong co trend/comparison
3. **Single view qua tai** — 15+ cards tren 1 view cho Operational Cockpit
4. **Hero khong ro** — Weekly Revenue la scalar nho, khong noi bat
5. **Thieu charts tu playbook** — New vs Returning Split, Social by Platform, Brand Performance chua implement
6. **Discount Rate khong co canh bao** — scalar don gian, khong co zone/threshold
7. **Pie chart cho Brand** — nen la donut (cleaner) voi max 5 slices
8. **Tables thieu conditional formatting** — khong highlight kenh tang/giam manh

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude cancelled/voided | `status NOT IN ('CANCELLED', 'Voided')` | All revenue/order cards | Don huy khong tinh vao performance |
| Exclude current incomplete week | `order_timestamp < date_trunc('week', current_date)` | All cards | Tuan hien tai chua ket thuc — so sanh khong cong bang |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last 7 days (prev Mon-Sun) | All cards | Xem tuan cu hon |
| Channel Category | category/single-select | All | All cards | Loc Ecommerce / Offline / All |
| Brand (Channel) | category/single-select | All | All cards | Loc theo channel_brand (JPC, Fine Japan, The Healthy Us) |

### Views

Multi-view — 3 views:
1. Hieu suat Kenh (Channel Performance)
2. Khach hang & Acquisition (Customers)
3. Promotion & Social Commerce

---

### View 1 — Hieu suat Kenh

**Narrative flow:** "Tuan nay doanh thu the nao?" -> "Ecommerce vs Offline ai manh hon?" -> "Kenh nao drive nhieu nhat?" -> "Chi tiet tung kenh WoW?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Danh gia hieu suat kenh tuan — kenh nao hieu qua, kenh nao can dieu chinh?" | annotation | text-annotation | structural | full-width x minimal | Section heading — subtitle: "Marketing — Kenh nao hieu qua nhat tuan nay?" | — |
| 2 | B | Weekly Revenue | hero | single-value-with-trend | primary, positive/negative (WoW) | one-third x short, prominent | Tong doanh thu thuan tuan — con so quan trong nhat | vs previous period (WoW %) |
| 3 | B | Ecommerce Revenue | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Doanh thu tu cac kenh ecommerce | vs previous period (WoW %) |
| 4 | B | Offline Revenue | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Doanh thu tu kenh offline (POS) | vs previous period (WoW %) |
| 5 | B | Ecom Share % | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Ty trong ecommerce trong tong doanh thu | vs previous period (WoW pp) |
| 6 | C | "Theo doi xu huong Ecommerce vs Offline — momentum va crossover" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Ecommerce vs Offline Trend | trend | multi-line-chart | series-1 (Ecommerce) + series-2 (Offline) | two-thirds x medium | Xu huong doanh thu hang ngay 2 kenh — spot crossover va momentum | vs previous period (visual overlay) |
| 8 | D | Revenue by Brand | breakdown | donut | series-1..series-5 | one-third x medium | Ty trong doanh thu theo brand (JPC, Fine Japan, etc.) — max 5 slices | composition |
| 9 | E | "Xac dinh platform hieu qua — ranking doanh thu va volume" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | F | Revenue by Platform | breakdown | horizontal-bar | primary | half x medium | Ranking platform theo doanh thu — Shopee, Lazada, TikTok, POS, etc. | rank/position |
| 11 | F | Orders by Platform | breakdown | horizontal-bar | secondary | half x medium | Ranking platform theo so don — so sanh voi revenue ranking | rank/position |
| 12 | G | "So sanh chi tiet kenh WoW — highlight bien dong > 20%" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | H | Channel Performance Table | detail | data-table-formatted | conditional-above/conditional-below on WoW Revenue % (> 20% = positive, < -20% = negative) | full-width x medium, compact | Channel, Orders, Revenue, AOV, WoW Revenue %, WoW Orders % — highlight kenh bien dong > 20% | vs previous period (WoW) |

---

### View 2 — Khach hang & Acquisition

**Narrative flow:** "Tuan nay co bao nhieu khach moi?" -> "Khach moi tu kenh nao?" -> "New vs Returning dong gop the nao?" -> "Xu huong acquisition 14 ngay?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 14 | A | "Danh gia acquisition tuan — bao nhieu khach moi va tu dau?" | annotation | text-annotation | structural | full-width x minimal | Section heading — subtitle: "Tuan nay co bao nhieu khach moi va tu dau?" | — |
| 15 | B | New Customers | hero | single-value-with-trend | primary, positive/negative (WoW) | one-third x short, prominent | So khach moi tuan nay — metric acquisition quan trong nhat | vs previous period (WoW %) |
| 16 | B | Returning Customers | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Khach quay lai mua tuan nay | vs previous period (WoW %) |
| 17 | B | New Customer Revenue | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Doanh thu tu khach moi | vs previous period (WoW %) |
| 18 | B | New Customer Share % | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Ty trong doanh thu khach moi / tong doanh thu | vs previous period (WoW pp) |
| 19 | C | "Xac dinh kenh acquisition hieu qua nhat" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | D | New Customers by Channel | breakdown | horizontal-bar | primary | half x medium | Ranking kenh theo so khach moi — xac dinh kenh acquisition hieu qua | rank/position |
| 21 | D | New vs Returning Revenue | breakdown | stacked-bar | series-1 (New = accent) + series-2 (Returning = muted) | half x medium | Dong gop doanh thu New vs Returning theo ngay — 7 ngay | composition |
| 22 | E | "Theo doi xu huong acquisition 14 ngay — volume va chat luong" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | F | New Customer Acquisition Trend | trend | combo-chart | primary (New Customers bars) + accent (AOV line) | two-thirds x medium | Volume khach moi hang ngay + AOV khach moi — spot correlation | vs previous period (visual) |
| 24 | F | Customer Type Split | breakdown | donut | series-1 (New) + series-2 (Returning) | one-third x medium | Ty le khach moi vs khach cu tuan nay | composition |

---

### View 3 — Promotion & Social Commerce

**Narrative flow:** "Discount co dang kiem soat?" -> "Promotion nao hieu qua?" -> "Social commerce tuan nay?" -> "San pham nao ban tot nhat?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 25 | A | "Kiem soat chi phi khuyen mai — discount co hop ly?" | annotation | text-annotation | structural | full-width x minimal | Section heading — subtitle: "Discount co dang kiem soat? Promotion nao hieu qua?" | — |
| 26 | B | Discount Rate % | hero | gauge | positive/warning/negative (zones: 0-10/10-15/15-30) | one-third x short | Ty le chiet khau toan he thong — target < 15% | vs benchmark (zones) |
| 27 | B | Discounted Orders % | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Ty le don co chiet khau | vs previous period (WoW pp) |
| 28 | B | Avg Discount Amount | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter x short, standard | Gia tri chiet khau trung binh moi don | vs previous period (WoW %) |
| 29 | B | Total Discount Given | supporting | single-value-with-trend | secondary, negative/positive (WoW — giam = tot) | one-quarter x short, standard | Tong tien chiet khau da cap | vs previous period (WoW %) |
| 30 | C | "Danh gia hieu suat promotion — promo nao mang lai gia tri?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 31 | D | Discounted vs Full Price | breakdown | donut | series-1 (Full Price = primary) + series-2 (Discounted = warning) | one-third x medium | Ty le don Discounted vs Full Price | composition |
| 32 | D | Promotion Leaderboard | detail | data-table-formatted | conditional-above on Avg Discount % (> 20% = warning) | two-thirds x medium, compact | Top 10 promo: Code, Usage, Revenue, Avg Discount % — flag high-discount promos | rank/position |
| 33 | E | "Theo doi hieu suat Social Commerce — Facebook vs Zalo" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 34 | F | Social Revenue | supporting | single-value-with-trend | primary, positive/negative (WoW) | one-third x short, prominent | Doanh thu social commerce | vs previous period (WoW %) |
| 35 | F | Social Orders | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-third x short, standard | So don tu social | vs previous period (WoW %) |
| 36 | F | Social AOV | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-third x short, standard | AOV kenh social — so voi AOV chung | vs previous period (WoW %) |
| 37 | G | Social Revenue by Platform | breakdown | horizontal-bar | series-1 (Facebook) + series-2 (Zalo) | half x medium | So sanh Facebook vs Zalo — revenue + orders | rank/position |
| 38 | G | Top 10 Products This Week | detail | data-table-formatted | conditional-above on Revenue (top 3 = accent) | half x medium, compact | Product, Brand, Units, Revenue — highlight top 3 | rank/position |
| 39 | H | "Source: fact_orders · dim_channels · Updated weekly (Mon-Sun) · Excludes cancelled/voided" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Weekly Revenue (hero) | Drop | WoW < -10% | Drill View 1 — xac dinh kenh/platform nao giam |
| Ecom Share % | Shift | WoW change > 5pp | Kiem tra co event offline hay ecom issue |
| Channel Performance Table | Kenh sut giam | Any channel WoW Revenue < -20% | Review marketing spend, stock, competitive activity |
| New Customers (hero) | Drop | WoW < -15% | Review acquisition budget, kiem tra channel attribution |
| New Customer Share % | Quality concern | < 20% | Heavy retention — can tang acquisition spend |
| Discount Rate % (gauge) | Vuot nguong | > 15% | Review promo portfolio, kiem tra discount abuse |
| Promotion Leaderboard | Low ROI | Avg Discount % > 20% voi Usage < 50 | Stop hoac dieu chinh promotion khong hieu qua |
| Social Revenue | Drop | WoW < -20% | Kiem tra content schedule, tin nhan chua doc, staff allocation |

### Summary of Changes

| Aspect | Before (Current Blueprint) | After (Redesign) |
|--------|---------------------------|------------------|
| Views | 1 single view (15 cards) | 3 tabs: Kenh, Khach hang, Promotion & Social |
| Annotations | 0 | 13 section headings with descriptive content |
| Hero | Unclear (plain scalar) | Tab 1: Weekly Revenue WoW. Tab 2: New Customers WoW. Tab 3: Discount Rate gauge |
| KPI comparisons | None — plain scalars | WoW % integrated into all KPI cards |
| Discount Rate | Plain scalar with suffix | Gauge with 3 color zones (10/15/30) |
| Ecom vs Offline Trend | Basic 2-line chart | Multi-line chart with clear series colors |
| Brand split | Pie chart | Donut (max 5 slices, cleaner) |
| Channel detail | Basic table | Formatted table with WoW conditional highlighting (>20%) |
| Customer section | 2 basic charts | 6 cards: KPI row + breakdown + trend combo + donut |
| New cards added | — | Ecom Share %, Returning Customers, New Customer Revenue, New Customer Share %, Customer Type Split, New vs Returning Revenue, Social AOV, Social by Platform, Discount detail KPIs |
| Promotion table | Top 5 basic table | Top 10 formatted table with discount % warning |
| Platform analysis | 1 revenue bar | 2 bars side-by-side: Revenue + Orders by Platform |
| Conditional formatting | None | 4 cards with conditional formatting |
| Total cards | 15 | 38 (across 3 tabs — avg 12-13 per tab) |

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (WoW)
- [x] Text annotations dung imperative voice
- [x] Khong co card orphan
- [x] Action Map day du
- [x] Hero card o row dau tien, noi bat nhat
- [x] Row widths sum = full-width (18 cols)
- [x] Density trong gioi han Cockpit (max 16/view): V1=13, V2=11, V3=14
- [x] Moi view co it nhat 1 section divider
- [x] Color tokens nhat quan
- [x] Size hierarchy ro: hero > supporting > detail
- [x] Number formatting nhat quan: VND compact, percentage 1 decimal
