---
title: "Marketing Monthly Analysis (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/sales.md, domains/customer.md]
---

## Design Spec: Marketing Monthly Analysis (Redesign)

### Brief

- **Audience:** Marketing Manager, Brand Manager, CMO — 3rd-5th of each month, working session
- **Time budget:** 20-30 min across 4 tabs. Tab 1 for monthly pulse (5-7 min), Tab 2-4 for deep-dive
- **Primary question:** "Thang nay marketing hieu qua the nao? Kenh nao dang grow, khach hang co khoe, campaign co ROI, brand nao can push?"
- **Decision enabled:** Dieu chinh ngan sach kenh, chien luoc acquisition, campaign planning thang toi, brand marketing priorities
- **Comparison frame:** MoM (this month vs previous month) + YoY (vs same month last year) + 6-month trends
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer.md](../domains/customer.md)

### Redesign Rationale

Dashboard hien tai co nhieu van de:

1. **Khong co tabs** — 16 cards tren 1 view, flat, khong phan tang
2. **Hero khong ro** — Monthly Revenue la plain scalar, khong noi bat
3. **KPIs thieu MoM/YoY** — chi hien con so, khong co trend/comparison
4. **0 annotations** — khong co narrative flow, khong co section headings
5. **Tables thieu conditional formatting** — khong highlight van de can chu y
6. **Channel Brand va Market/Segment** — dung donut nho, thieu context
7. **Cohort Retention** — pivot table thieu color formatting
8. **Khong co combo chart** — miss co hoi the hien dual-metric correlation

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude current incomplete month | `order_timestamp < date_trunc('month', current_date)` | All cards | Thang hien tai chua ket thuc — so sanh khong cong bang |
| Exclude cancelled/voided | `status NOT IN ('CANCELLED', 'Voided')` | Revenue/order cards | Chi tinh don hop le |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last closed month | All cards | Xem thang cu hon |
| Channel Category | category/single-select | All | All cards | Ecommerce / Offline focus |
| Brand (Channel) | category/single-select | All | Channel & Brand tab | Filter by channel_brand |

### Views

Multi-view — 4 views:
1. Monthly Pulse (Tong quan thang)
2. Channel & Brand Strategy (Kenh & Thuong hieu)
3. Customer Intelligence (Khach hang)
4. Campaigns & Products (Khuyen mai & San pham)

---

### View 1 — Monthly Pulse

**Narrative flow:** "Thang nay the nao?" -> "KPIs chinh va so sanh MoM?" -> "Xu huong 6 thang?" -> "Kenh nao dang chiem uu the?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Marketing Monthly Review" | annotation | text-annotation | structural | full-width x minimal | Subtitle: "Marketing Manager — Thang qua hieu qua the nao? — Last closed month" | — |
| 2 | B | Monthly Net Revenue | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Doanh thu thuan thang — con so quan trong nhat | vs previous period (MoM %) + YoY % |
| 3 | B | Total Orders | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Tong don hang | vs previous period (MoM %) |
| 4 | B | New Customers | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Khach moi thang nay — acquisition health | vs previous period (MoM %) |
| 5 | B | AOV | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Gia tri trung binh moi don | vs previous period (MoM %) |
| 6 | C | Discount Rate % | supporting | gauge | positive/warning/negative (zones: 0-10/10-15/15-100) | one-third x medium | Ty le chiet khau — target < 15%, canh bao 10-15% | vs benchmark (zones) |
| 7 | C | Revenue Trend (6M) | trend | combo-chart | primary (bar: revenue) + accent (line: MoM growth %) | two-thirds x medium | Doanh thu 6 thang + growth rate — momentum dang tang hay giam? | vs previous period (MoM %) |
| 8 | D | "Tong quan kenh ban hang" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Kenh nao dang drive revenue?" | — |
| 9 | E | Channel Revenue Share | breakdown | donut | series-1..series-5 | one-third x medium | Ty trong doanh thu theo kenh — composition snapshot | composition |
| 10 | E | Revenue by Channel (MoM) | breakdown | grouped-bar | series-1 (this month) + series-2 (last month) | two-thirds x medium | So sanh doanh thu kenh thang nay vs thang truoc — kenh nao tang/giam? | vs previous period (side-by-side) |

---

### View 2 — Channel & Brand Strategy

**Narrative flow:** "Cau truc kenh thay doi the nao trong 6 thang?" -> "Platform nao hieu qua?" -> "Brand nao dang drive growth?" -> "Market va segment chia the nao?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 11 | A | "Xu huong cau truc kenh (6 thang)" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Ecommerce vs Offline dang shift the nao?" | — |
| 12 | B | Channel Mix Trend (6M) | trend | stacked-area | series-1..series-5 | full-width x medium | Doanh thu kenh 6 thang stacked — thay structural shift | composition over time |
| 13 | C | "Hieu suat tung Platform" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Platform nao mang lai nhieu revenue, don, khach moi nhat?" | — |
| 14 | D | Platform Performance Matrix | detail | data-table-formatted | conditional-above on MoM Revenue % (> 10% = positive), conditional-below (< -10% = negative) | full-width x medium, compact | Platform, Revenue, Orders, AOV, New Customers, MoM Rev %, MoM Orders % — highlight platform tang/giam manh | vs previous period (MoM %) |
| 15 | E | "Thuong hieu kenh & Portfolio" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Channel brand nao chiem ty trong lon nhat?" | — |
| 16 | F | Channel Brand Revenue | breakdown | horizontal-bar | primary + muted | two-thirds x medium | Top channel brands ranked by revenue — JPC, Fine Japan, etc. | rank/position |
| 17 | F | Revenue by Market | breakdown | donut | series-1 (Domestic), series-2 (Export) | one-third x medium | Domestic vs Export split | composition |
| 18 | G | "Thuong hieu san pham" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Brand nao dang grow, brand nao can push marketing?" | — |
| 19 | H | Brand Performance Summary | detail | data-table-formatted | conditional-above on MoM % (> 15% = positive), conditional-below on MoM % (< -15% = negative) | two-thirds x medium, compact | Brand, Revenue, Units, Orders, AOV, MoM % — highlight brand growth/decline | vs previous period (MoM %) |
| 20 | H | Revenue by Customer Segment | breakdown | donut | series-1 (B2C), series-2 (B2B) | one-third x medium | B2C vs B2B revenue split | composition |

---

### View 3 — Customer Intelligence

**Narrative flow:** "Acquisition thang nay the nao?" -> "Kenh nao mang khach moi?" -> "Segment khach hang co on dinh?" -> "Cohort retention ra sao?" -> "Bao nhieu khach at risk?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 21 | A | "Customer Acquisition — Khach moi thang nay" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Chi phi co khach moi co hieu qua? Kenh nao tot nhat?" | — |
| 22 | B | New Customers (Month) | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Tong khach moi thang — hero cua tab nay | vs previous period (MoM %) |
| 23 | B | Returning Customers | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-third x short, standard | Khach quay lai — retention signal | vs previous period (MoM %) |
| 24 | B | New vs Returning Revenue Share | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-third x short, standard | % revenue tu khach moi — acquisition quality | vs previous period (MoM %) |
| 25 | C | New Customer Acquisition Trend (6M) | trend | combo-chart | primary (bar: new customers) + accent (line: MoM growth %) | two-thirds x medium | Khach moi 6 thang + growth rate — dang tang hay giam? | vs previous period (growth line) |
| 26 | C | New Customers by Channel | breakdown | horizontal-bar | series-1..series-N | one-third x medium | Ranking kenh theo so khach moi thang nay | rank/position |
| 27 | D | "Segment & Retention Health" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Segment khach hang co on dinh? Retention co cai thien?" | — |
| 28 | E | At Risk Customers | supporting | single-value-with-trend | negative (count), positive/negative (MoM change) | one-third x short, prominent | So khach at risk — canh bao churn | vs previous period (MoM %) |
| 29 | E | Churn Rate % | supporting | gauge | positive/warning/negative (zones: 0-5/5-15/15-100) | one-third x short | Ty le churn — target < 5% | vs benchmark (zones) |
| 30 | E | Active Customer Rate % | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-third x short, standard | % khach active trong 30 ngay | vs previous period (MoM %) |
| 31 | F | Customer Segment Movement | detail | data-table-formatted | conditional-above on MoM Count Change (> 0 for VIP = positive), conditional-below (< 0 for VIP = negative) | half x medium, compact | Segment, Status, Count, LTV, MoM Count Change — highlight segment tang/giam | vs previous period (MoM) |
| 32 | F | Cohort Retention Heatmap | detail | pivot-table | conditional-range (intensity: 0-100, white to primary) | half x medium, compact | Month-0 to Month-6 retention by cohort — color intensity = retention % | vs benchmark (cohort comparison) |

---

### View 4 — Campaigns & Products

**Narrative flow:** "Campaign thang nay ROI the nao?" -> "Discount co an margin khong?" -> "San pham nao chay nhat?" -> "Dia ly va timing?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 33 | A | "Campaign & Promotion ROI" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Promotion nao mang lai gia tri? Discount co qua tay?" | — |
| 34 | B | Total Discount Amount | supporting | single-value-with-trend | warning, positive/negative (MoM, lower=positive) | one-third x short, prominent | Tong chiet khau thang — dang tang hay giam? | vs previous period (MoM %) |
| 35 | B | Discounted Order % | supporting | single-value-with-trend | secondary, positive/negative (MoM, lower=positive) | one-third x short, standard | % don co chiet khau | vs previous period (MoM %) |
| 36 | B | Avg Discount Depth | supporting | single-value-with-trend | secondary, positive/negative (MoM, lower=positive) | one-third x short, standard | Do sau chiet khau trung binh | vs previous period (MoM %) |
| 37 | C | Promotion Leaderboard | detail | data-table-formatted | conditional-above on Revenue (top 3 = accent) | full-width x medium, compact | Promo Code, Usage, Revenue, Avg Discount %, Promo AOV vs Non-Promo AOV — highlight top 3 | rank/position |
| 38 | D | Discount Trend (6M) | trend | line-chart | warning + muted (goal line at 15%) | half x medium | Ty le discount 6 thang — target < 15% | vs target (goal line) |
| 39 | D | Revenue: Discounted vs Full-Price (6M) | trend | stacked-bar-time | series-1 (Full-Price = primary), series-2 (Discounted = warning) | half x medium | Revenue split 6 thang — proportion thay doi the nao? | composition over time |
| 40 | E | "San pham & Thuong hieu" | annotation | text-annotation | structural | full-width x minimal | Section heading — "San pham nao drive revenue? Brand nao can attention?" | — |
| 41 | F | Top 15 Products by Revenue | detail | data-table-formatted | conditional-above on MoM Change % (> 20% = positive), conditional-below (< -20% = negative) | full-width x medium, compact | Product, Brand, Units, Revenue, MoM Change % — highlight san pham tang/giam manh | vs previous period (MoM %) |
| 42 | G | "Dia ly & Thoi gian dat hang" | annotation | text-annotation | structural | full-width x minimal | Section heading — "Khach hang o dau? Khi nao ho dat hang?" | — |
| 43 | H | Revenue by Province (Top 10) | breakdown | horizontal-bar | primary + muted | half x medium | Top 10 tinh thanh theo revenue | rank/position |
| 44 | H | Order Heatmap — Day x Hour | breakdown | pivot-table | conditional-range (intensity: low=muted, high=accent) | half x medium | Ngay x Gio — peak ordering windows cho marketing scheduling | intensity pattern |

---

### Summary of Changes

| Aspect | Before (Current Blueprint) | After (Redesign) |
|--------|---------------------------|------------------|
| Views | 1 single view (16 cards) | 4 tabs: Monthly Pulse, Channel & Brand, Customer Intelligence, Campaigns & Products |
| Annotations | 0 | 12 section headings with descriptive content |
| Hero | Monthly Revenue as plain scalar | Net Revenue with MoM+YoY trend (Tab 1), New Customers with MoM (Tab 3) |
| KPI comparisons | None — plain scalars | MoM % on all KPI cards, YoY on revenue, gauge for discount rate & churn |
| Channel analysis | 1 stacked area + 1 table | Stacked area + grouped bar MoM + donut share + formatted matrix + brand bar |
| Customer section | 1 bar + 1 bar + 1 table + 1 pivot | 3 KPIs + combo chart + ranking bar + segment table + retention heatmap + at-risk gauge |
| Campaign section | 1 table only | 3 KPIs + leaderboard table + discount trend with goal line + stacked revenue split |
| Product section | 2 plain tables | Formatted table with MoM + Brand x Channel removed (moved to Tab 2) |
| Geographic | 1 bar + 1 heatmap table | Bar + pivot heatmap with color intensity |
| Combo charts | 0 | 2 (revenue trend + acquisition trend with growth lines) |
| Conditional formatting | 0 | 8 cards with conditional formatting |
| Gauges | 0 | 2 (discount rate, churn rate) |
| Total cards | 16 | 44 (across 4 tabs — avg 11 per tab) |
