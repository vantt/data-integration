---
title: Product Profitability
archetype: Operational Cockpit
status: final
last_modified: 2026-04-10
domain_refs: [domains/finance.md, domains/product.md]
---

## Design Spec: Product Profitability

### Brief

- **Audience:** Merchandising, Sales Director — review san pham hang thang
- **Time budget:** 10-15 phut, working session de ra quyet dinh product mix
- **Primary question:** San pham nao tao margin cao nhat va san pham nao dang keo loi nhuan xuong?
- **Decision enabled:** Dieu chinh gia ban, ngung kinh doanh san pham lo, uu tien push san pham margin cao
- **Comparison frame:** Cross-product ranking, vs threshold (40% margin), cross-channel per product
- **Archetype:** Operational Cockpit (single view, data-dense)
- **Domain references:** [domains/finance.md](../domains/finance.md), [domains/product.md](../domains/product.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude promo lines | `NOT is_promo_line` | All cards | Gift/promo items distort margin |
| Revenue > 0 | `revenue_net_of_discount > 0` | Ranking cards | Avoid division by zero |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Period | date/range | Last 3 months | All cards | View different accounting periods |
| Channel | category/single-select | All | All cards | Isolate channel for product analysis |

### Views

Single view (10 cards)

### Composition

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "San pham nao tao lai, san pham nao keo xuong?" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Total Products | supporting | single-value | neutral | one-quarter × short, standard | So san pham co data COGS | — |
| 3 | B | Avg Margin % | hero | single-value-with-trend | primary, prominent | one-quarter × short, prominent | Margin trung binh san pham | vs previous period |
| 4 | B | Highest Margin Product | supporting | single-value | positive | one-quarter × short, standard | San pham margin cao nhat | — |
| 5 | B | Lowest Margin Product | supporting | single-value | negative | one-quarter × short, standard | San pham margin thap nhat | — |
| 6 | C | "Top 20 san pham theo lai gop" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Top Products by Profit | breakdown | horizontal-bar | primary | half × medium, standard | Ranking san pham dong gop lai gop | rank |
| 8 | D | Bottom Margin Products | breakdown | horizontal-bar | negative | half × medium, standard | San pham margin thap nhat | rank (bottom) |
| 9 | E | "Chi tiet san pham — margin, doanh thu, gia von theo kenh" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 10 | F | Product Detail Table | detail | data-table-formatted | conditional-below (<25% red) / conditional-above (>50% green) | full-width × tall, compact | Full product breakdown | rank + threshold |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Avg Margin % | Drop MoM | < -5 diem % | Review product mix shift, kiem tra COGS tang |
| Bottom Margin Products | Product margin < 15% | San pham chiem > 5% revenue | Review gia ban hoac ngung ban qua kenh do |
| Top Products by Profit | Concentration | Top 3 chiem > 60% tong profit | Rui ro tap trung — da dang hoa product mix |
| Product Detail Table | Margin < 0% | San pham lo | Kiem tra COGS, xem co nhap sai gia khong |

<!--
Dashboard Finish Checklist:
- [x] Hero card prominent
- [x] Row widths: B=4+4+4+4+2=18 (adjusted), D=9+9=18, F=18 ✓
- [x] Card count: 10, within Cockpit limit
- [x] Semantic tokens only
- [x] Action Map complete
-->
