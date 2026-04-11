---
title: Marketing ROI
archetype: Operational Cockpit
status: final
last_modified: 2026-04-10
domain_refs: [domains/finance.md, domains/sales.md]
---

## Design Spec: Marketing ROI

### Brief

- **Audience:** CMO, Marketing Manager — review hieu qua chi tieu quang cao
- **Time budget:** 10 phut, review weekly/monthly
- **Primary question:** Chi X dong quang cao → thu Y dong doanh thu → ROAS bao nhieu?
- **Decision enabled:** Tang/giam budget theo kenh, dung/tiep campaign
- **Comparison frame:** Cross-channel ROAS, spend vs revenue trend, CPC/CPM benchmarks
- **Archetype:** Operational Cockpit (single view)
- **Domain references:** [domains/finance.md](../domains/finance.md), [domains/sales.md](../domains/sales.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Sales channels only | `is_sales_channel = true` | Revenue cards | Exclude internal/system channels |
| Completed orders | `status = 'COMPLETED'` | Revenue cards | Only settled revenue |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last 30 days | All cards | View different periods |

### Views

Single view (9 cards)

### Composition

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Marketing ROI — chi tieu vs doanh thu theo kenh" | annotation | text-annotation | structural | full-width × minimal | Dashboard subtitle | — |
| 2 | B | Total Spend | supporting | single-value | neutral | one-third × short, standard | Tong chi phi marketing | — |
| 3 | B | Total Revenue | supporting | single-value | primary | one-third × short, standard | Tong doanh thu tu cac kenh co spend | — |
| 4 | B | Blended ROAS | hero | single-value | positive (>3x) / warning (1-3x) / negative (<1x) | one-third × short, prominent | ROAS tong hop | vs threshold |
| 5 | C | "Chi tieu va doanh thu theo thoi gian" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 6 | D | Spend vs Revenue Trend | trend | combo-chart | series-1 (revenue bar) + series-2 (spend line) | full-width × medium, standard | Xu huong spend vs revenue theo thang | time trend |
| 7 | E | "Hieu qua theo kenh quang cao" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 8 | F | Channel Marketing Table | detail | data-table-formatted | conditional-above (ROAS>3 green) / conditional-below (ROAS<1 red) | full-width × medium, compact | Spend, revenue, ROAS, CPC, CPM per channel | rank + threshold |
| 9 | G | ROAS by Channel | breakdown | horizontal-bar | conditional-above / conditional-below | full-width × medium, standard | Ranking kenh theo ROAS | rank |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Blended ROAS | Below 1x | ROAS < 1.0 | Dung cac campaign lo — review targeting |
| Blended ROAS | Warning | ROAS 1-3x | Toi uu creative/targeting, A/B test |
| Channel Marketing Table | CPC tang > 50% MoM | Chi phi per click tang manh | Review keyword bidding, pause underperforming ads |
| ROAS by Channel | Channel ROAS < 1x | Kenh nao spend nhieu ma revenue it | Cut budget kenh do, chuyen sang kenh ROAS cao |
