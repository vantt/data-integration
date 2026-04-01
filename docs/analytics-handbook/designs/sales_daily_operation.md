---
title: "Daily Sales Dashboard (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-01
domain_refs: [domains/sales.md]
---

## Design Spec: Daily Sales Dashboard (Redesign)

### Brief

- **Audience:** Store Managers, Sales Team — real-time monitoring xuyen suot ngay lam viec
- **Time budget:** 5-10 min working session across 4 tabs, revisit nhieu lan trong ngay
- **Primary question:** "Hom nay kinh doanh dang the nao so voi hom qua?"
- **Decision enabled:** Dieu chinh truc tiep trong ngay: day kenh yeu, bo sung hang, follow up khach
- **Comparison frame:** DoD (today vs yesterday) — real-time so sanh
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md)

### Redesign Rationale

Cung van de voi Yesterday's dashboard (xem designs/sales_yesterday_operation.md). Ap dung cung pattern redesign:

1. Thieu narrative flow (0 annotations)
2. Hero khong ro (Health Score scalar nho)
3. KPIs thieu DoD comparison tich hop
4. Pie chart bi lam dung (4 pie charts)
5. Tab Tong quan qua tai (15+ cards khong phan tang)
6. DoD Comparison table thua (nen tich hop vao KPI cards)

### Constraints & Filters

**Business Constraints:** Khong co.

**Interactive Filters:** Khong co — Operational Cockpit real-time, zero-interaction.

### Views

Multi-view — 4 views:
1. Tong quan (Overview)
2. Kenh ban hang (Channels)
3. San pham (Products)
4. Khach hang & Thanh toan (Customers & Payments)

---

### View 1 — Tong quan

**Narrative flow:** "Suc khoe kinh doanh?" -> "KPIs hom nay?" -> "Chi so phu?" -> "Xu huong theo gio?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Suc khoe kinh doanh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 2 | B | Health Score | supporting | gauge | positive/warning/negative (zones: 75-100/50-74/0-49) | one-third x medium | Diem suc khoe 0-100 | vs benchmark (zones) |
| 3 | B | Health Breakdown | detail | data-table-formatted | conditional-above/conditional-below on Diem column | two-thirds x medium, compact | Chi tiet 4 thanh phan | vs previous period (WoW) |
| 4 | C | "Ket qua hom nay (real-time)" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 5 | D | Net Revenue | hero | single-value-with-trend | primary, positive/negative (DoD) | one-third x short, prominent | Doanh thu thuan hom nay | vs previous period (DoD %) |
| 6 | D | Gross Revenue | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Doanh thu gop | vs previous period (DoD %) |
| 7 | D | Total Orders | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Volume don hang | vs previous period (DoD %) |
| 8 | D | AOV | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Hieu qua moi don | vs previous period (DoD %) |
| 9 | E | "Chi so phu" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | F | New Customers | supporting | single-value | neutral | one-sixth x short | Khach mua lan dau | — |
| 11 | F | Returning Customers | supporting | single-value | neutral | one-sixth x short | Khach quay lai | — |
| 12 | F | Returns | supporting | single-value | negative (khi > 0) | one-sixth x short | Don tra hang | — |
| 13 | F | Total Collected | supporting | single-value | neutral | one-sixth x short | Tong thu gom VAT | — |
| 14 | F | Discount Rate % | supporting | single-value | neutral | one-sixth x short | Ty le don co CK | — |
| 15 | F | Items/Order | supporting | single-value | neutral | one-sixth x short | So SP/don | — |
| 16 | G | "Doanh thu theo gio" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 17 | H | Hourly Sales Trend | trend | multi-line-chart | primary (Today) + muted (Yesterday) | two-thirds x medium | Peak hours, real-time pattern | vs previous period (DoD overlay) |
| 18 | H | Cumulative Revenue | trend | multi-line-chart | accent (Today) + muted (Yesterday) | one-third x medium | Running total | vs previous period (DoD overlay) |

---

### View 2 — Kenh ban hang

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 19 | A | "Doanh thu theo kenh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | B | Revenue by Channel | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking kenh | rank/position |
| 21 | B | Revenue by Channel Category | breakdown | vertical-bar | series-1..series-3 | half x medium | Online vs Offline vs Internal | categorical |
| 22 | C | "Hieu suat kenh so voi hom qua" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | D | Channel Performance vs Yesterday | detail | data-table-formatted | conditional-above/conditional-below on Change % | full-width x medium | Highlight kenh sut giam | vs previous period (DoD) |
| 24 | E | "Doanh thu theo chi nhanh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 25 | F | Sales by Branch | detail | data-table | neutral | full-width x medium | Revenue/orders/AOV theo chi nhanh | rank/position |

---

### View 3 — San pham

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 26 | A | "Top 10 san pham ban chay" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 27 | B | Top 10 Products by Revenue | breakdown | horizontal-bar | primary | half x medium | Ranking theo doanh thu | rank/position |
| 28 | B | Top 10 Products by Quantity | breakdown | horizontal-bar | secondary | half x medium | Ranking theo so luong | rank/position |
| 29 | C | "Phan bo theo loai san pham" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 30 | D | Revenue by Product Type | breakdown | horizontal-bar | series-1..series-N | half x medium | Loai SP dong gop | rank/position |
| 31 | D | Product Performance Table | detail | data-table | neutral | half x tall | Chi tiet san pham | — |

---

### View 4 — Khach hang & Thanh toan

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 32 | A | "Chan dung khach hang hom nay" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 33 | B | Returning Rate % | supporting | single-value | positive/warning | one-sixth x short | Ty le khach quay lai | vs benchmark |
| 34 | B | At Risk Customers | supporting | single-value | warning | one-sixth x short | Khach co nguy co mat | — |
| 35 | B | New vs Returning | breakdown | vertical-bar | series-1 + series-2 | two-thirds x medium | New vs Returning | categorical |
| 36 | C | Revenue by Segment | breakdown | vertical-bar | series-1..series-N | full-width x medium | VIP/Loyal/Regular | categorical |
| 37 | D | "Thanh toan & Chiet khau" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 38 | E | Orders by Status | breakdown | donut | series-1..series-4 | half x medium | Phan bo trang thai | composition |
| 39 | E | Payment Method | breakdown | donut | series-1..series-5 | half x medium | Phan bo PTTT | composition |
| 40 | F | Discount Impact | detail | data-table | neutral | full-width x short | Tong quan chiet khau | — |

---

### Summary of Changes

| Aspect | Before | After |
|--------|--------|-------|
| Annotations | 0 | 11 section headings |
| Hero | Unclear | Net Revenue with DoD trend |
| Health Score | scalar | gauge with 3 color zones |
| KPI comparisons | Separate DoD table | Integrated into 4 KPIs |
| Pie charts | 4 | 2 donuts (Status, Payment) |
| Rankings | Tables/vertical bars | horizontal-bars |
| Conditional formatting | None | Health Breakdown + Channel table |
| Labels | English | Vietnamese |
| Currency | Plain numbers | VND compact |
