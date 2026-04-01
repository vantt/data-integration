---
title: "Customer Operational Dashboard (Redesign)"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/customer.md]
---

## Design Spec: Customer Operational Dashboard (Redesign)

### Brief

- **Audience:** Customer Success Manager, Sales Ops — daily operational check, working session
- **Time budget:** 15-25 min across 3 tabs. Tab 1 for health pulse (5 min), Tab 2-3 for deep-dive and action
- **Primary question:** "Customer base khoe khong? Ai can cham soc ngay?"
- **Decision enabled:** Uu tien outreach VIP, phan hoi at-risk truoc khi churn, danh gia kenh acquisition, chien dich reactivation
- **Comparison frame:** Rolling 30-day vs previous 30-day for MAU; MoM for acquisition; current state for segments
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/customer.md](../domains/customer.md)

### Redesign Rationale

Dashboard hien tai co nhieu van de:

1. **KPIs thieu context** — 4 scalar khong co trend/comparison, chi hien con so tran
2. **Single view qua tai** — 13 cards tren 1 view, khong co narrative flow
3. **0 annotations** — khong co section heading, reader khong biet dang nhin gi
4. **Tables qua nhieu** — 5/13 cards la table khong co conditional formatting
5. **Thieu composition views** — khong co donut hay gauge cho nhin nhanh ty le
6. **Status Trend SQL sai** — tinh recency tu current_date cho moi thang, sai logic
7. **Khong co New vs Returning** — thieu metric quan trong cho growth quality
8. **Khong co Churned Recovery** — thieu danh sach hanh dong cho churn prevention

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude Unknown customers | `customer_id != 'Unknown'` | All cards using dim_customers | Dummy records, skew counts |
| Exclude cancelled/voided orders | `status NOT IN ('CANCELLED', 'Voided')` | All cards using fact_orders | Cancelled orders not real activity |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Khong co — Operational Cockpit daily check, zero-interaction design | | | | |

### Views

Multi-view — 3 views:
1. Tong quan (Overview)
2. Kenh & Dia ly (Channels & Geography)
3. Watchlist & Hanh dong (Action)

---

### View 1 — Tong quan

**Narrative flow:** "Customer base hien tai the nao?" -> "Phan bo trang thai & segment?" -> "Xu huong 6 thang?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Tong quan khach hang — Customer Health" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 2 | B | MAU (Monthly Active Customers) | hero | single-value-with-trend | primary, positive/negative (vs prev 30d) | one-third x short, prominent | Khach hang hoat dong 30 ngay gan nhat — con so van hanh quan trong nhat | vs previous period (rolling 30d) |
| 3 | B | New Customers (MTD) | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Khach moi thang nay | vs previous period (MoM) |
| 4 | B | At Risk Customers | supporting | single-value | warning | one-quarter x short, standard | So khach 31-90 ngay chua mua — can outreach | — (current state) |
| 5 | B | Churned Customers | supporting | single-value | negative | one-quarter x short, standard | So khach >90 ngay chua mua — da mat | — (current state) |
| 6 | C | "Phan bo trang thai & Segment" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Customer Status Distribution | breakdown | donut | series-1=positive (Active), series-2=warning (At Risk), series-3=negative (Churned) | one-third x medium | Active / At Risk / Churned — nhin nhanh composition | composition |
| 8 | D | Customer Segment Distribution | breakdown | donut | series-1=accent (VIP), series-2=primary (Loyal), series-3=muted (Regular) | one-third x medium | VIP / Loyal / Regular — gia tri phan bo | composition |
| 9 | D | Active Rate | supporting | gauge | positive/warning/negative (zones: 30-100% green, 15-30% yellow, 0-15% red) | one-third x medium | Ty le khach Active trong tong — target >30% | vs benchmark (zones) |
| 10 | E | "Xu huong 6 thang" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 11 | F | New vs Returning Customers (6M) | trend | stacked-area | series-1=primary (New), series-2=secondary (Returning) | half x medium | Growth quality — bao nhieu la khach moi vs quay lai? | composition over time |
| 12 | F | Monthly Active Customers Trend (6M) | trend | line-chart | primary | half x medium | MAU trend 6 thang — dang tang hay giam? | vs previous period (implicit) |

---

### View 2 — Kenh & Dia ly

**Narrative flow:** "Khach moi den tu dau va tang the nao?" -> "Kenh nao hieu qua nhat?" -> "Dia ly phan bo the nao?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 13 | A | "Xu huong khach hang moi (6 thang)" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 14 | B | Customer Acquisition Trend (6M) | trend | combo-chart | primary (bar: New Customers) + accent (line: MoM %) | full-width x medium | Luong khach moi theo thang kem tang truong MoM | vs previous period (MoM % line) |
| 15 | C | "Kenh acquisition (thang truoc)" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 16 | D | New Customers by Channel | breakdown | horizontal-bar | primary | half x medium | Ranking kenh theo so khach moi | rank/position |
| 17 | D | First-Order Revenue by Channel | breakdown | horizontal-bar | secondary | half x medium | Doanh thu don dau theo kenh — kenh nao mang khach co gia tri? | rank/position |
| 18 | E | "Phan bo dia ly" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 19 | F | Top 15 Provinces by Customers | breakdown | horizontal-bar | primary | half x medium | Ranking tinh theo so khach | rank/position |
| 20 | F | Top 15 Provinces by LTV | breakdown | horizontal-bar | accent | half x medium | Ranking tinh theo gia tri — tinh nao co khach gia tri cao? | rank/position |

---

### View 3 — Watchlist & Hanh dong

**Narrative flow:** "Segment health tong the?" -> "VIP nao can cham soc?" -> "At Risk nao uu tien?" -> "Churned nao co the recover?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 21 | A | "RFM Segment Health Matrix" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 22 | B | Segment x Status Health Matrix | detail | data-table-formatted | conditional-below on Active % (<50% = negative), conditional-above on At-Risk LTV (>5M = warning) | full-width x medium, compact | Cross-tab Segment x Status — dau la diem nong? | vs benchmark (thresholds) |
| 23 | C | "VIP Watchlist — Cham soc chu dong" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 24 | D | VIP Customer Watchlist | detail | data-table-formatted | conditional-above on Days Since Last Order (>60 = negative, >30 = warning) | full-width x tall, compact | VIP sort by recency — ai sap mat? Goi ngay! | vs benchmark (30/60 day thresholds) |
| 25 | E | "At-Risk Reactivation Priority" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 26 | F | At-Risk Reactivation Priority | detail | data-table-formatted | conditional-above on LTV (>5M = accent) | full-width x tall, compact | At-Risk sort by LTV — khach nao gia tri nhat can giu? | rank/position |
| 27 | G | "Churned High-Value — Co hoi recovery" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 28 | H | Churned High-Value Customers | detail | data-table-formatted | conditional-above on LTV (>5M = accent) | full-width x tall, compact | Churned 91-180 ngay, LTV >1M — dang chay recovery campaign? | vs benchmark (LTV threshold) |

---

### Summary of Changes

| Aspect | Before | After |
|--------|--------|-------|
| Views | 1 single view (13 cards) | 3 tabs: Tong quan, Kenh & Dia ly, Watchlist |
| Annotations | 0 | 10 section headings with descriptive content |
| Hero | Plain scalar (no trend) | MAU with rolling 30-day comparison |
| KPI comparisons | None — plain scalars | MoM on MAU + New Customers |
| Composition views | 0 | 2 donuts (status + segment) + 1 gauge (active rate) + 1 stacked area |
| Channel analysis | 1 bar chart | 2 horizontal bars (volume + revenue) |
| Geographic analysis | 1 vertical bar | 2 horizontal bars (count + LTV) |
| Status trend | Wrong SQL (recency from current_date) | New vs Returning stacked area + MAU line |
| Segment Health | Plain table | Formatted table with conditional colors |
| Watchlists | 2 plain tables | 3 formatted tables with conditional formatting + action-oriented sort |
| New: Churned Recovery | Missing | Churned high-value table for recovery campaigns |
| New: Acquisition Combo | Missing | Combo chart with bars + MoM % growth line |
| Conditional formatting | None | 4 tables with conditional formatting |
| Total cards | 13 | 28 (across 3 tabs — avg ~9 per tab) |
