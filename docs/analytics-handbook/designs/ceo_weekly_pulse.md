---
title: "CEO Weekly Pulse (Redesign)"
archetype: Executive Pulse
status: final
last_modified: 2026-04-02
domain_refs: [domains/sales.md, domains/customer.md]
---

## Design Spec: CEO Weekly Pulse (Redesign)

### Brief

- **Audience:** CEO, Co-Founders — Monday morning 5-minute check-in
- **Time budget:** Glanceable — Tab 1 answers the primary question in 2 min. Tabs 2-3 for optional depth (3 min total)
- **Primary question:** "Tuan qua kinh doanh co on-track khong? Dang ahead hay behind target thang?"
- **Decision enabled:** Can thiep khan cap (giam gia, tang marketing) hay tiep tuc nhu hien tai
- **Comparison frame:** WoW (this week vs previous week) + MTD vs Target
- **Archetype:** Executive Pulse
- **Domain references:** [domains/sales.md](../domains/sales.md)

### Redesign Rationale

Dashboard hien tai co nhieu van de:

1. **Flat layout** — 13+ cards tren 1 view, tat ca scalars trang giong nhau, khong co visual hierarchy
2. **MTD Target la plain table** — nen la progress-toward-goal de CEO nhin 1 giay biet on-track hay khong
3. **Channel data la table** — nen la charts (donut + horizontal-bar) de CEO nhin pattern ngay
4. **Khong co annotations** — khong co narrative flow, CEO phai tu suy luan "section nay la gi"
5. **Secondary KPIs thieu WoW** — Cancelled, Returns, Discount chi hien so, khong co trend
6. **Revenue trend chi 1 line** — nen co area fill de nhan manh volume, hoac combo voi orders

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude US channel | `channel_name != 'US'` | All cards | Internal/B2B orders, 100% discount — skew revenue metrics |
| Exclude incomplete week | Report on previous Mon-Sun | All weekly cards | Current week chua ket thuc, so sanh khong cong bang |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| *(Khong co — Executive Pulse can zero-interaction)* | | | | |

### Views

Multi-view — 3 views:
1. **Doanh thu & Target** (Revenue & Target) — Hero tab, answers primary question
2. **Kenh ban hang** (Channel Mix) — Which channels are driving/declining
3. **Khach hang & Canh bao** (Customers & Red Flags) — Acquisition health + operational alerts

---

### View 1 — Doanh thu & Target

**Narrative flow:** "Tuan nay on khong?" → "4 KPIs chinh WoW" → "Target thang dang o dau?" → "Xu huong 14 ngay"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "CEO Weekly Pulse — Tuan qua kinh doanh co on-track khong?" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle — audience + primary question | — |
| 2 | B | Net Revenue | hero | single-value-with-trend | primary, positive/negative (WoW) | one-third × short, prominent | Doanh thu thuan tuan — con so quan trong nhat | vs previous period (WoW %) |
| 3 | B | Gross Revenue | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter × short, standard | Tong gia tri hang hoa truoc chiet khau | vs previous period (WoW %) |
| 4 | B | Total Orders | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter × short, standard | So luong don hang | vs previous period (WoW %) |
| 5 | B | AOV | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-quarter × short, standard | Gia tri trung binh moi don | vs previous period (WoW %) |
| 6 | C | "Tien do target thang" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | MTD Revenue vs Target | hero-secondary | progress-toward-goal | positive/warning/negative (auto by %) | two-thirds × short | Da dat bao nhieu % target thang — CEO nhin 1 giay biet on-track | vs target (monthly) |
| 8 | D | Pace Index | supporting | single-value-with-trend | positive/negative (>1.0 = positive, <1.0 = negative) | one-third × short, prominent | Pace = MTD Actual / Expected. >1.0 = Ahead, <1.0 = Behind | vs benchmark (pace = 1.0) |
| 9 | E | "Xu huong doanh thu (14 ngay)" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 10 | F | Daily Net Revenue (14 Days) | trend | area-chart | primary (fill) + muted (previous week shading) | full-width × medium | Volume revenue 14 ngay — this week vs previous week side-by-side | vs previous period (visual overlay) |

---

### View 2 — Kenh ban hang

**Narrative flow:** "Cau truc kenh the nao?" → "Kenh nao dang tang/giam?" → "Top channels chi tiet"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 11 | A | "Phan bo doanh thu theo kenh" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 12 | B | Revenue by Channel Category | hero | donut | series-1 (Ecommerce), series-2 (Offline), series-3 (Internal) | one-third × medium | Ty le Ecommerce / Offline / Internal — part-to-whole snapshot | composition |
| 13 | B | Revenue by Channel Category (WoW) | breakdown | grouped-bar | series-1 (This Week) + series-2 (Last Week) | two-thirds × medium | So sanh truc tiep this week vs last week theo tung category | vs previous period (WoW side-by-side) |
| 14 | C | "Top kenh ban hang" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 15 | D | Top Channels by Revenue | breakdown | horizontal-bar | primary (bars) + muted (last week reference) | full-width × medium | Ranking kenh theo doanh thu — CEO thay ngay kenh nao lon nhat | rank/position |
| 16 | E | Channel Performance Table | detail | data-table-formatted | conditional-above/conditional-below on WoW % (>20% = positive, <-20% = negative) | full-width × medium, compact | Channel, This Week, Last Week, WoW % — highlight kenh bien dong manh | vs previous period (WoW %) |

---

### View 3 — Khach hang & Canh bao

**Narrative flow:** "Khach hang moi the nao?" → "New vs Returning?" → "Co gi bat thuong khong?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 17 | A | "Suc khoe khach hang" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 18 | B | New Customers | hero | single-value-with-trend | primary, positive/negative (WoW) | one-third × short, prominent | So khach moi tuan nay | vs previous period (WoW %) |
| 19 | B | Returning Revenue % | supporting | gauge | positive/warning/negative (zones: >60%=positive, 40-60%=warning, <40%=negative) | one-third × short | Ty le doanh thu tu khach cu — healthy benchmark > 60% | vs benchmark (zones) |
| 20 | B | Returning Customers | supporting | single-value-with-trend | secondary, positive/negative (WoW) | one-third × short, standard | So khach cu quay lai mua | vs previous period (WoW %) |
| 21 | C | "Xu huong New vs Returning (14 ngay)" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 22 | D | New vs Returning Orders (14 Days) | trend | stacked-bar-time | series-1 (New = accent), series-2 (Returning = primary) | full-width × medium | Cau thanh don hang theo ngay — New vs Returning | composition over time |
| 23 | E | "Canh bao van hanh" | annotation | text-annotation | structural | full-width × minimal | Section heading — RED FLAGS | — |
| 24 | F | Cancelled Orders | supporting | single-value-with-trend | neutral, negative (if WoW > 50% increase) | one-third × short, standard | Don huy tuan nay — flag neu tang dot bien | vs previous period (WoW %) |
| 25 | F | Return Count | supporting | single-value-with-trend | neutral, negative (if > 2x previous week) | one-third × short, standard | Don tra hang — flag RED neu > 2x tuan truoc | vs previous period (WoW %) |
| 26 | F | Discount Rate % | supporting | gauge | positive/warning/negative (zones: 0-10%=positive, 10-15%=warning, >15%=negative) | one-third × short | Ty le chiet khau / Gross Revenue — flag RED neu > 15% | vs benchmark (zones) |
