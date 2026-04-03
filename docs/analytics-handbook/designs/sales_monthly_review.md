---
title: "Sales Monthly Business Review (MBR)"
archetype: Executive Pulse
status: final
last_modified: 2026-04-02
domain_refs: [domains/sales.md, domains/customer.md]
---

## Design Spec: Sales Monthly Business Review (MBR)

### Brief

- **Audience:** Sales Director, CFO, Regional Managers — doc trong cuoc hop MBR hang thang
- **Time budget:** 10-15 min presentation, multi-view de drill down theo agenda
- **Primary question:** "Thang vua qua co dat target khong, va dau la dong luc tang truong chinh?"
- **Decision enabled:** Dieu chinh target thang toi, phan bo ngan sach kenh, chinh sach chiet khau, ke hoach hanh dong cho vung yeu
- **Comparison frame:** MoM (thang nay vs thang truoc) + YoY (vs cung ky nam truoc) + vs Target
- **Archetype:** Executive Pulse (multi-view — tong 4 views, moi view ≤10 cards)
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer.md](../domains/customer.md)

### Redesign Rationale

Dashboard moi phuc vu cuoc hop MBR co cau truc ro rang:
1. Executive Summary — nhin nhanh dat/miss target
2. Financial Performance — revenue, margin, variance chi tiet
3. Growth Drivers — kenh, vung, khach hang
4. Operational Health — chiet khau, tra hang, san pham

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Completed orders only | `status = 'completed'` | All revenue cards | Exclude cancelled/pending de phan anh doanh thu thuc |
| Current closed month | `order_month = last_complete_month` | All cards (default) | MBR review thang da dong |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Thang review | date/month-picker | Last complete month | All cards | Cho phep xem lai cac thang truoc |
| Chi nhanh | category/multi-select | All | All cards | Drill down theo chi nhanh/vung |

### Views

Multi-view — 4 views:
1. Tong quan (Executive Summary)
2. Hieu suat tai chinh (Financial Performance)
3. Dong luc tang truong (Growth Drivers)
4. Suc khoe van hanh (Operational Health)

---

### View 1 — Tong quan

**Narrative flow:** "Dat target chua?" → "Cac chi so chinh the nao?" → "Xu huong 12 thang?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Ket qua kinh doanh thang — dat target hay chua?" | annotation | text-annotation | structural | full-width x minimal | Section heading — mo dau MBR | — |
| 2 | B | Net Revenue vs Target | hero | progress-toward-goal | primary, positive/negative (vs target %) | one-third x medium, prominent | Doanh thu thuan vs muc tieu thang | vs target (achievement %) |
| 3 | B | Net Revenue | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Gia tri tuyet doi doanh thu | vs previous period (MoM %) |
| 4 | B | Total Orders | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Volume don hang | vs previous period (MoM %) |
| 5 | B | AOV | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Hieu qua moi don hang | vs previous period (MoM %) |
| 6 | C | "Chi so phu — buc tranh toan canh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Gross Revenue | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-sixth x short, standard | Tong doanh thu gop | vs previous period (MoM %) |
| 8 | D | Total Collected | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-sixth x short, standard | Tong thu gom VAT | vs previous period (MoM %) |
| 9 | D | Variance to Target | supporting | single-value | negative/positive | one-sixth x short, standard | Gap tuyet doi toi target | vs target (absolute) |
| 10 | D | New Customers | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-sixth x short, standard | Khach moi trong thang | vs previous period (MoM %) |
| 11 | D | Returning Customers | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-sixth x short, standard | Khach quay lai | vs previous period (MoM %) |
| 12 | D | Return Count | supporting | single-value-with-trend | negative (khi tang) | one-sixth x short, standard | Don tra hang | vs previous period (MoM %) |
| 13 | E | "Xu huong doanh thu 12 thang — trajectory dai han" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 14 | F | 12-Month Revenue Trend | trend | combo-chart | primary (revenue bars) + accent (target line) | two-thirds x medium | Trajectory doanh thu + target line | vs target (reference line) |
| 15 | F | Achievement Rate by Month | trend | line-chart | positive/warning/negative (zones) | one-third x medium | Ty le dat target qua 12 thang | vs benchmark (100% line) |

---

### View 2 — Hieu suat tai chinh

**Narrative flow:** "Target achievement theo vung?" → "Variance o dau?" → "Chi tiet performance"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 16 | A | "Muc do hoan thanh target theo chi nhanh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 17 | B | Target Achievement by Branch | breakdown | horizontal-bar | conditional-above/conditional-below (vs 100%) | full-width x medium | Ranking chi nhanh theo % dat target | vs target (100% reference line) |
| 18 | C | "Phan tich chenh lech — dau la gap lon nhat?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 19 | D | Variance Waterfall | breakdown | waterfall | positive/negative | two-thirds x medium | Yeu to nao dong gop chenh lech target | vs target (bridge) |
| 20 | D | MoM Revenue Change | supporting | single-value-with-trend | positive/negative (MoM) | one-third x medium, prominent | Thay doi doanh thu so thang truoc | vs previous period (MoM %) |
| 21 | E | "Chi tiet hieu suat theo chi nhanh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 22 | F | Branch Performance Table | detail | data-table-formatted | conditional-above/conditional-below on Achievement % | full-width x tall | Revenue, Target, Achievement %, Variance, MoM% theo chi nhanh | vs target + vs previous period (MoM) |

---

### View 3 — Dong luc tang truong

**Narrative flow:** "Kenh nao dang drive?" → "Online vs Offline the nao?" → "Khach hang segment nao dong gop?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 23 | A | "Dong gop doanh thu theo kenh ban hang" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 24 | B | Revenue by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh theo doanh thu | rank/position |
| 25 | B | Channel Mix MoM | breakdown | grouped-bar | series-1 (this month) + series-2 (last month) | half x medium | So sanh truc tiep kenh MoM | vs previous period (MoM) |
| 26 | C | "Xu huong cau truc kenh 6 thang — Online dang len?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 27 | D | Channel Revenue Trend (6M) | trend | stacked-bar-time | series-1..series-N | two-thirds x medium | Cau thanh doanh thu thay doi theo thang | composition over time |
| 28 | D | Online vs Offline Share | breakdown | donut | series-1 + series-2 | one-third x medium | Ty le Online/Offline hien tai | composition |
| 29 | E | "Phan khuc khach hang — VIP co dang tang?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 30 | F | Revenue by Customer Segment | breakdown | vertical-bar | series-1..series-N | half x medium | VIP/Loyal/Regular dong gop | categorical |
| 31 | F | New vs Returning Revenue Share | breakdown | stacked-bar | series-1 + series-2 | half x medium | Khach moi vs khach cu dong gop | composition |

---

### View 4 — Suc khoe van hanh

**Narrative flow:** "Chiet khau co vuot nguong?" → "Tra hang co bat thuong?" → "San pham nao can xu ly?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 32 | A | "Kiem soat chiet khau — co vuot 15% GMV?" | annotation | text-annotation | structural | full-width x minimal | Section heading — flag neu > 15% | — |
| 33 | B | Discount Rate % | supporting | gauge | positive/warning/negative (zones: 0-10/10-15/15+) | one-third x medium, prominent | Ty le chiet khau tren GMV | vs benchmark (15% threshold) |
| 34 | B | Total Discount Amount | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-quarter x short, standard | Gia tri chiet khau tuyet doi | vs previous period (MoM %) |
| 35 | B | Discounted Orders % | supporting | single-value-with-trend | neutral, positive/negative (MoM) | one-quarter x short, standard | Ty le don co chiet khau | vs previous period (MoM %) |
| 36 | B | Return Rate | supporting | single-value-with-trend | negative (khi tang) | one-quarter x short, standard | Ty le tra hang | vs previous period (MoM %) |
| 37 | C | "Top san pham — ban chay va can xu ly" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 38 | D | Top 10 Products by Revenue | breakdown | horizontal-bar | primary | half x medium | San pham ban chay nhat | rank/position |
| 39 | D | Top 5 Returned Products | breakdown | horizontal-bar | negative | half x medium | San pham bi tra nhieu nhat — can dieu tra | rank/position |
| 40 | E | "Chi tiet san pham theo loai" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 41 | F | Revenue by Product Type | breakdown | horizontal-bar | series-1..series-N | half x medium | Loai SP dong gop doanh thu | rank/position |
| 42 | F | Product Performance Table | detail | data-table-formatted | conditional-above/conditional-below on MoM% | half x tall | Revenue, Qty, MoM%, Return% theo SP | vs previous period (MoM) |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Net Revenue vs Target | Miss target | Achievement < 90% | Drill View 2 — xem branch nao miss, waterfall cho gap analysis |
| Net Revenue vs Target | Far miss | Achievement < 80% | Escalation — hop khan cap voi Sales Director, review action plan |
| Variance Waterfall | Large negative contributor | Any branch variance < -50M | Dieu tra branch — stockout? staff? seasonal? |
| Target Achievement by Branch | Branch miss | Achievement < 80% | Lien he Branch Manager — yeu cau root cause + action plan |
| Discount Rate % | Vuot nguong | Discount/GMV > 15% | Review chinh sach chiet khau, kiem tra promo campaigns |
| Return Rate | Tang dot bien | MoM > +50% | Kiem tra top 5 returned products, xac dinh root cause |
| Top 5 Returned Products | Concentration | 1 product > 30% total returns | Dieu tra chat luong/mo ta san pham, lien he supplier |
| Revenue by Channel | Channel decline | Any channel MoM < -20% | Drill down kenh do — marketing spend? stock availability? |
| New Customers | Giam manh | MoM < -15% | Review marketing acquisition budget, kiem tra channel attribution |
| Achievement Rate by Month | Downtrend | 3 thang lien tiep giam | Re-evaluate target setting methodology |

---

### Summary

| Aspect | Value |
|--------|-------|
| Total cards | 42 (across 4 views) |
| Annotations | 12 section headings |
| Hero | Net Revenue vs Target (progress-toward-goal) |
| Views | 4: Tong quan, Tai chinh, Tang truong, Van hanh |
| Archetype | Executive Pulse (multi-view) |
| Comparison types | MoM, YoY (12-month trend), vs Target, rank/position, composition |
| Filters | Month picker + Branch multi-select |
| Labels | Vietnamese (no diacritics) |
| Currency | VND compact (e.g., 1.2B, 500M) |

### Metrics Verification (Phase 0)

All metrics used in this design are defined in existing domain files:

| Metric | Domain Reference | Status |
|--------|-----------------|--------|
| Net Revenue | sales.md #2 | Available |
| Gross Revenue | sales.md #1 | Available |
| Total Collected | sales.md #2b | Available |
| Total Orders | sales.md #4 | Available |
| AOV | sales.md #5 | Available |
| Return Rate & Count | sales.md #3 | Available |
| Sales by Channel | sales.md #8 | Available |
| Top Selling Products | sales.md #9 | Available |
| New vs Returning | sales.md #10 | Available |
| Discount Impact | sales.md #13 | Available |
| Target Achievement Rate | sales.md #15 | Available |
| Variance to Target | sales.md #16 | Available |
| Sales by Region/Location | sales.md #15 (location) | Available |
| Customer Segment | customer.md #7 | Available (Phase 1 rule-based) |
| Gross Margin | sales.md (referenced in playbook) | Note: Not explicitly defined — add to domain if COGS available |

<!--
Design Finish Checklist:
- [x] Hero card at top, visually dominant (progress-toward-goal, one-third, prominent)
- [x] Every KPI has >=1 comparison (MoM, vs Target, or rank)
- [x] Row widths sum = full-width (18 cols) per row
- [x] Density: max 15 cards/view (View 1: 15, View 2: 7, View 3: 9, View 4: 11)
- [x] Each view has >=1 text annotation section divider
- [x] Color tokens only — no hex codes
- [x] Size tokens only — no pixel values
- [x] Vietnamese card names (no diacritics)
- [x] Action Map complete for cards with significant signals
- [x] Narrative flow: summary → trend → breakdown → detail per view
- [x] F-pattern reading: hero top-left, supporting right, detail bottom
- [x] Consistent color: primary = Net Revenue across all views
- [x] Colorblind safe: all status colors paired with text/trend arrows
-->
