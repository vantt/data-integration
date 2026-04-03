---
title: "Product Performance"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/product.md, domains/sales.md]
---

## Design Spec: Product Performance

### Brief

- **Audience:** Merchandising, Management — review product sales velocity va revenue contribution theo tuan/thang
- **Time budget:** 15-20 min working session across 3 views
- **Primary question:** "San pham nao dang ban chay, loai nao dong gop nhieu nhat, va xu huong thay doi the nao?"
- **Decision enabled:** Dieu chinh product mix, day manh san pham tiem nang, giam san pham yeu
- **Comparison frame:** MoM (thang nay vs thang truoc) — phu hop voi merchandising cadence
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/product.md](../domains/product.md), [domains/sales.md](../domains/sales.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Confirmed orders only | `status != 'cancelled'` | All cards | Cancelled orders khong phan anh product performance thuc te |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Khoang thoi gian | date/range | Last 30 Days | All cards | Cho phep so sanh nhieu khoang thoi gian |
| Loai san pham | category/single-select | All | All cards | Drill-down vao loai san pham cu the |
| Kenh ban hang | category/single-select | All | All cards | So sanh product mix theo kenh |

### Views

Multi-view — 3 views:
1. Tong quan (Overview)
2. Phan tich loai san pham (Category Analysis)
3. San pham ban chay & ban cham (Top/Bottom Products)

---

### View 1 — Tong quan

**Narrative flow:** "Doanh thu san pham dang the nao?" -> "Chi so ban hang chinh?" -> "Xu huong doanh thu theo thoi gian?" -> "Dong gop theo loai san pham?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Review hieu suat san pham thang — doanh thu, velocity, va xu huong MoM" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 2 | B | Doanh thu san pham | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Tong doanh thu tu san pham | vs previous period (MoM %) |
| 3 | B | So luong ban | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Tong quantity sold | vs previous period (MoM %) |
| 4 | B | So san pham ban duoc | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Distinct products co sales | vs previous period (MoM %) |
| 5 | B | Doanh thu trung binh/san pham | supporting | single-value-with-trend | secondary, positive/negative (MoM) | one-quarter x short, standard | Revenue per distinct product | vs previous period (MoM %) |
| 6 | C | "Phan tich xu huong doanh thu san pham — momentum MoM" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Doanh thu san pham theo ngay | trend | multi-line-chart | primary (This month) + muted (Last month) | two-thirds x medium | Trend doanh thu hang ngay, overlay MoM | vs previous period (MoM overlay) |
| 8 | D | So luong ban theo ngay | trend | multi-line-chart | secondary (This month) + muted (Last month) | one-third x medium | Trend quantity hang ngay | vs previous period (MoM overlay) |
| 9 | E | "Xac dinh dong gop theo loai san pham — ranking va composition" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | F | Doanh thu theo loai san pham | breakdown | horizontal-bar | series-1..series-N | half x medium | Ranking loai SP theo doanh thu | rank/position |
| 11 | F | Ty trong doanh thu theo loai san pham | breakdown | donut | series-1..series-5 | half x medium | Phan bo % doanh thu theo loai SP | composition |

---

### View 2 — Phan tich loai san pham

**Narrative flow:** "Loai san pham nao tang truong, loai nao sut giam?" -> "Xu huong category mix thay doi the nao?" -> "Chi tiet theo loai?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 12 | A | "Danh gia tang truong theo loai san pham — dieu chinh product mix" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | B | Tang truong doanh thu theo loai SP | breakdown | horizontal-bar | conditional-above/conditional-below | full-width x medium | MoM % change by category — highlight tang/giam | vs previous period (MoM %) |
| 14 | C | "Theo doi category mix shift — loai nao dang chiem uu the?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 15 | D | Category Mix Trend | trend | stacked-area | series-1..series-N | full-width x medium | Cau thanh doanh thu theo loai SP qua thoi gian | composition over time |
| 16 | E | "Review chi tiet loai san pham — highlight tang/giam manh" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 17 | F | Bang hieu suat loai san pham | detail | data-table-formatted | conditional-above/conditional-below on MoM % | full-width x tall | Loai SP, Doanh thu, So luong, Revenue/unit, MoM % — highlight tang/giam | vs previous period (MoM) |

---

### View 3 — San pham ban chay & ban cham

**Narrative flow:** "San pham nao ban chay nhat?" -> "San pham nao co toc do ban cao nhat?" -> "San pham nao dang sut giam?" -> "Chi tiet san pham"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 18 | A | "Xac dinh top 20 san pham ban chay — focus marketing va stock" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 19 | B | Top 20 SP theo doanh thu | breakdown | horizontal-bar | primary | half x tall | Ranking san pham theo revenue | rank/position |
| 20 | B | Top 20 SP theo so luong | breakdown | horizontal-bar | secondary | half x tall | Ranking san pham theo quantity | rank/position |
| 21 | C | "Canh bao som — san pham tang truong va sut giam manh nhat" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 22 | D | Top 10 SP tang truong MoM | breakdown | horizontal-bar | positive | half x medium | San pham co % tang truong cao nhat | vs previous period (MoM %) |
| 23 | D | Top 10 SP sut giam MoM | breakdown | horizontal-bar | negative | half x medium | San pham co % sut giam lon nhat | vs previous period (MoM %) |
| 24 | E | "Phan tich velocity — san pham nao quay nhanh nhat?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 25 | F | Top 20 SP theo daily velocity | breakdown | horizontal-bar | accent | full-width x medium | Units/day — san pham quay nhanh | rank/position |
| 26 | G | "Tra cuu chi tiet san pham — tim kiem, sap xep, loc tu do" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 27 | H | Bang chi tiet san pham | detail | data-table-formatted | conditional-above/conditional-below on MoM % | full-width x tall | Ten SP, Loai, Doanh thu, So luong, Velocity, MoM % | vs previous period (MoM) |
| 28 | I | "Source: fact_orders · dim_products · Updated daily · Excludes cancelled orders" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Doanh thu san pham (hero) | Drop | MoM < -10% | Kiem tra breakdown theo loai SP va kenh — xac dinh nguon giam |
| Doanh thu san pham (hero) | Spike | MoM > +20% | Xac minh co phai do promotion hay seasonal — khong dua ra ket luan som |
| Tang truong doanh thu theo loai SP | Category decline | MoM < -15% cho bat ky loai nao | Review product mix, kiem tra ton kho, co hoi thay the |
| Top 10 SP sut giam MoM | Rapid decline | MoM < -30% | Canh bao Merchandising, kiem tra co phai do het hang hay trend thi truong |
| Top 20 SP theo daily velocity | Low velocity | < 1 unit/day cho san pham chu luc | Review gia ban, vi tri trung bay, chien luoc marketing |
| Bang chi tiet san pham | New product missing | SP moi khong xuat hien trong top | Kiem tra listing, gia, va kenh phan phoi |

### Dashboard Finish Checklist

- [x] Moi card co title theo Title Discipline
- [x] Moi KPI co it nhat 1 comparison (MoM cho tat ca)
- [x] Text annotations dung imperative voice
- [x] Khong co card orphan
- [x] Action Map day du cho cards co signal quan trong
- [x] Hero card o row dau tien, noi bat nhat (one-third, prominent)
- [x] Row widths sum = full-width (18 cols)
- [x] Density trong gioi han Cockpit (max 16 cards/view): V1=11, V2=6, V3=10
- [x] Moi view co it nhat 1 section divider
- [x] Scroll depth phu hop Cockpit (max 2-3 scrolls)
- [x] Color tokens nhat quan toan dashboard
- [x] Khong dung > 5 mau distinct trong 1 view
- [x] Size hierarchy ro: hero > supporting > detail
- [x] Number formatting nhat quan: VND compact (1.2M), quantity (#), percentage (1 decimal)
