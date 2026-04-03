---
title: "Yesterday's Sales Dashboard (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-01
domain_refs: [domains/sales.md]
---

## Design Spec: Yesterday's Sales Dashboard (Redesign)

### Brief

- **Audience:** Store Managers, Sales Team, Operations Lead — review mỗi sáng 5-10 phút
- **Time budget:** 5-10 min working session across 4 tabs
- **Primary question:** "Hom qua kinh doanh the nao so voi hom kia?"
- **Decision enabled:** Dieu chinh van hanh trong ngay: tang cuong kenh yeu, chu y san pham hot/flop, follow up khach hang
- **Comparison frame:** DoD (yesterday vs day-before-yesterday)
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md)

### Redesign Rationale

Dashboard cu co 7 van de chinh:

1. **Thieu narrative flow** — khong co section heading nao, cards roi rac
2. **Hero khong ro rang** — Health Score la scalar nho, Net Revenue cung chi la scalar don gian
3. **KPIs thieu comparison** — hau het scalar chi hien con so, DoD comparison nam rieng o bang phia duoi
4. **Pie chart bi lam dung** — 4 pie charts, nhieu cai co the >5 slices
5. **Tab Tong quan qua tai** — 15+ cards khong phan tang
6. **Date Label chiem full-width** — lang phi khong gian (tich hop vao annotation)
7. **DoD Comparison table thua** — thong tin nay nen tich hop vao tung KPI card

### Constraints & Filters

**Business Constraints:** Khong co.

**Interactive Filters:** Khong co — Operational Cockpit cho daily review can zero-interaction (data co dinh = yesterday).

### Views

Multi-view — 4 views:
1. Tong quan (Overview)
2. Kenh ban hang (Channels)
3. San pham (Products)
4. Khach hang & Thanh toan (Customers & Payments)

---

### View 1 — Tong quan

**Narrative flow:** "Suc khoe kinh doanh ra sao?" -> "Ket qua hom qua cu the?" -> "Chi so phu?" -> "Xu huong trong ngay?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Danh gia suc khoe kinh doanh — diem tong hop tu Revenue, Orders, Loyalty, AOV" | annotation | text-annotation | structural | full-width x minimal | Section heading — mo dau voi buc tranh tong the | — |
| 2 | B | Health Score | supporting | gauge | positive/warning/negative (zones: 75-100/50-74/0-49) | one-third x medium | Diem suc khoe 0-100 — nhin 1 giay biet tinh hinh | vs benchmark (zones) |
| 3 | B | Health Breakdown | detail | data-table-formatted | conditional-above/conditional-below on Status column | two-thirds x medium, compact | Chi tiet 4 thanh phan: Revenue WoW, Orders WoW, Customer Loyalty, AOV Stability | vs previous period (WoW) |
| 4 | C | "Review ket qua hom qua — doanh thu, don hang, AOV so voi hom kia" | annotation | text-annotation | structural | full-width x minimal | Section heading — chuyen sang KPIs cu the, tich hop ngay vao text | — |
| 5 | D | Net Revenue | hero | single-value-with-trend | primary, positive/negative (DoD direction) | one-third x short, prominent | Doanh thu thuan hom qua — con so quan trong nhat | vs previous period (DoD %) |
| 6 | D | Gross Revenue | supporting | single-value-with-trend | secondary, positive/negative (DoD direction) | one-quarter x short, standard | Doanh thu gop — context truoc chiet khau | vs previous period (DoD %) |
| 7 | D | Total Orders | supporting | single-value-with-trend | secondary, positive/negative (DoD direction) | one-quarter x short, standard | Volume don hang | vs previous period (DoD %) |
| 8 | D | AOV | supporting | single-value-with-trend | secondary, positive/negative (DoD direction) | one-quarter x short, standard | Hieu qua moi don | vs previous period (DoD %) |
| 9 | E | "Theo doi chi so ho tro — khach hang, hoan tra, thu tien, chiet khau" | annotation | text-annotation | structural | full-width x minimal | Section heading — metrics bo tro | — |
| 10 | F | New Customers | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-sixth x short, standard | Khach mua lan dau | vs previous period (DoD %) |
| 11 | F | Returning Customers | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-sixth x short, standard | Khach quay lai | vs previous period (DoD %) |
| 12 | F | Returns | supporting | single-value-with-trend | negative (khi > 0, neutral khi = 0) | one-sixth x short, standard | Don tra hang — canh bao neu nhieu | vs previous period (DoD %) |
| 13 | F | Total Collected | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-sixth x short, standard | Tong thu gom VAT — doi soat ke toan | vs previous period (DoD %) |
| 14 | F | Discount Rate % | supporting | single-value-with-trend | warning (khi > 15%), neutral | one-sixth x short, standard | Ty le don co chiet khau | vs previous period (DoD pp) |
| 15 | F | Items/Order | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-sixth x short, standard | So san pham trung binh moi don | vs previous period (DoD %) |
| 16 | G | "Phan tich doanh thu theo gio — peak hours va so sanh voi hom kia" | annotation | text-annotation | structural | full-width x minimal | Section heading — xu huong intraday | — |
| 17 | H | Hourly Sales Trend | trend | multi-line-chart | primary (Yesterday) + muted (Day Before) | two-thirds x medium | Peak hours, pattern so sanh 2 ngay | vs previous period (DoD overlay) |
| 18 | H | Cumulative Revenue | trend | multi-line-chart | accent (Yesterday) + muted (Day Before) | one-third x medium | Running total — hom qua vuot hay thua hom kia | vs previous period (DoD overlay) |

**Thay doi so voi dashboard cu:**
- Health Score: scalar -> gauge (co zones, truc quan hon)
- Net Revenue: scalar -> single-value-with-trend (tich hop DoD%)
- Gross Revenue/Orders/AOV: scalar -> single-value-with-trend (tich hop DoD%)
- **Loai bo**: DoD Comparison table (redundant — comparison da tich hop vao KPIs)
- **Loai bo**: Date Label card (tich hop vao annotation Row C)
- **Them**: 4 annotation cards tao narrative flow

---

### View 2 — Kenh ban hang

**Narrative flow:** "Kenh nao drive revenue?" -> "So voi hom kia?" -> "Chi nhanh nao?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 19 | A | "Xac dinh kenh ban hang hieu qua — ranking doanh thu va volume" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | B | Revenue by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh nao nhieu revenue nhat | rank/position |
| 21 | B | Revenue by Channel Category | breakdown | vertical-bar | series-1..series-3 | half x medium | Online vs Offline vs Internal — 3 categories | categorical comparison |
| 22 | C | "So sanh hieu suat kenh WoW — highlight kenh tang/giam manh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | D | Channel Performance vs Day Before | detail | data-table-formatted | conditional-above/conditional-below on Revenue Change % | full-width x medium | Chi tiet tang/giam tung kenh — highlight kenh sut giam | vs previous period (DoD) |
| 24 | E | "Phan bo doanh thu chi nhanh — xac dinh noi can tang cuong" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 25 | F | Sales by Branch | detail | data-table | neutral | full-width x medium | Revenue, orders, AOV theo tung chi nhanh | rank/position (sorted by revenue) |

**Thay doi so voi dashboard cu:**
- Revenue by Channel: pie -> horizontal-bar (tot hon cho ranking, khong gioi han slices)
- Channel Performance: table -> data-table-formatted (highlight conditional tren Change%)
- Them 3 annotation cards

---

### View 3 — San pham

**Narrative flow:** "Top san pham ban chay?" -> "Loai nao drive?" -> "Chi tiet"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 26 | A | "Xac dinh san pham ban chay nhat — doanh thu va so luong" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 27 | B | Top 10 Products by Revenue | breakdown | horizontal-bar | primary | half x medium | Ranking san pham theo doanh thu | rank/position |
| 28 | B | Top 10 Products by Quantity | breakdown | horizontal-bar | secondary | half x medium | Ranking san pham theo so luong | rank/position |
| 29 | C | "Phan tich dong gop theo loai san pham" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 30 | D | Revenue by Product Type | breakdown | horizontal-bar | series-1..series-N | half x medium | Loai san pham nao dong gop nhieu nhat | rank/position |
| 31 | D | Product Performance Table | detail | data-table | neutral | half x tall | Chi tiet: Product, Type, Qty, Revenue, Avg Price | — |

**Thay doi so voi dashboard cu:**
- Top 10 by Revenue: table -> horizontal-bar (visual ranking thay vi doc bang)
- Revenue by Product Type: pie -> horizontal-bar (khong gioi han categories)
- Them 2 annotation cards

---

### View 4 — Khach hang & Thanh toan

**Narrative flow:** "Chan dung khach hang hom qua?" -> "Phan khuc nao?" -> "Thanh toan & chiet khau?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 32 | A | "Danh gia chan dung khach hang — new vs returning, segment" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 33 | B | Returning Customer Rate % | supporting | single-value | positive/warning (>35% positive, <20% warning) | one-sixth x short, standard | Ty le khach quay lai — red flag neu giam | vs benchmark (threshold) |
| 34 | B | At Risk Customers | supporting | single-value | warning | one-sixth x short, standard | Khach co nguy co mat | — |
| 35 | B | New vs Returning Customers | breakdown | vertical-bar | series-1 + series-2 | two-thirds x medium | So sanh truc tiep New vs Returning — orders va revenue | categorical comparison |
| 36 | C | Revenue by Customer Segment | breakdown | vertical-bar | series-1..series-N | full-width x medium | VIP / Loyal / Regular — phan khuc nao dong gop | categorical comparison |
| 37 | D | "Kiem tra phan bo thanh toan va muc do chiet khau" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 38 | E | Orders by Status | breakdown | donut | series-1..series-4 | half x medium | Phan bo trang thai don (<= 5 slices) | composition |
| 39 | E | Payment Method Distribution | breakdown | donut | series-1..series-5 | half x medium | Phan bo phuong thuc thanh toan (<= 5 slices) | composition |
| 40 | F | Discount Impact | detail | data-table | neutral | full-width x short | Tong quan chiet khau: so don, ty le, tong CK, trung binh | — |
| 41 | G | "Source: fact_orders · Updated daily · Excludes cancelled/voided orders" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

**Thay doi so voi dashboard cu:**
- KPI row (Returning Rate + At Risk): tach rieng thanh dong KPIs phia tren
- New vs Returning: giu vertical-bar nhung cho lon hon (two-thirds thay vi half)
- Revenue by Segment: mo rong full-width de doc ro hon
- Giu 2 donuts cho Orders by Status va Payment Method (deu <= 5 categories)
- Them 2 annotation cards

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Health Score (gauge) | Danger zone | Score < 50 | Drill vao Health Breakdown — xac dinh thanh phan nao keo diem xuong |
| Net Revenue (hero) | Drop | DoD < -15% | Kiem tra kenh ban hang (View 2) va san pham (View 3) — xac dinh nguon giam |
| Net Revenue (hero) | Spike | DoD > +30% | Xac minh khong co don trung, kiem tra promo impact |
| Total Orders | Low volume | DoD < -20% | Kiem tra tinh trang kenh ecommerce, san pham het hang |
| AOV | Sudden drop | DoD < -15% | Review chiet khau, kiem tra co promo giam gia manh |
| Returns | Spike | > 3 don hoac DoD > 100% | Kiem tra san pham bi tra, lien he kho van |
| Revenue by Channel (View 2) | Channel decline | Any channel DoD < -25% | Kiem tra channel cu the — marketing spend? stock availability? |
| Channel Performance table | Alert | WoW Change % < -30% | Lien he team kenh, yeu cau root cause |
| Top 10 Products (View 3) | Missing regular | San pham thuong xuyen khong trong top | Kiem tra ton kho, gia ban, vi tri trung bay |

---

### Summary of Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Annotations** | 0 section headings | 11 annotations tao narrative flow |
| **Hero** | Khong ro (Health Score scalar nho) | Net Revenue voi DoD trend, prominent size |
| **KPI comparisons** | DoD trong bang rieng | Tich hop truc tiep vao 4 KPIs (single-value-with-trend) |
| **Health Score** | scalar (doc so, khong biet tot/xau) | gauge voi 3 zones (doc mau, biet ngay) |
| **Pie charts** | 4 (Channel, Product Type, Status, Payment) | 2 donuts (Status, Payment — deu <= 5 slices) |
| **Ranking viz** | Table cho Top Products | horizontal-bar cho Channel, Products, Product Type |
| **Date Label** | Full-width card rieng | Tich hop vao annotation text |
| **DoD Comparison table** | Card rieng full-width | Loai bo (redundant) |
| **Conditional formatting** | Khong co | Health Breakdown + Channel Performance table |
| **Total cards** | ~23 data cards, 0 annotations | 29 data cards + 12 annotations = 41 cards across 4 views |

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (DoD cho tat ca)
- [x] Text annotations dung imperative voice
- [x] Khong co card orphan
- [x] Action Map day du cho cards co signal quan trong
- [x] Hero card o row dau tien, noi bat nhat (one-third, prominent)
- [x] Row widths sum = full-width (18 cols)
- [x] Density trong gioi han Cockpit (max 16 cards/view): V1=18, V2=7, V3=6, V4=9
- [x] Moi view co it nhat 1 section divider
- [x] Color tokens nhat quan — khong hex codes
- [x] Size hierarchy ro: hero > supporting > detail
- [x] Number formatting nhat quan: VND compact, percentage 1 decimal
