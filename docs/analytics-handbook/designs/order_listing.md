---
title: Order Listing
archetype: Operational Cockpit
status: final
last_modified: 2026-04-01
domain_refs: [domains/sales.md]
---

## Design Spec: Order Listing

### Brief

- **Audience:** Store Managers, Sales Ops, Data Team — daily operational check
- **Time budget:** 10-15 min, daily morning/evening
- **Primary question:** "Du lieu don hang trong BI co khop voi Sapo khong?"
- **Decision enabled:** Identify data gaps, flag anomalies for investigation, cross-check counts/amounts with source system
- **Comparison frame:** DoD (vs previous day) for KPIs; BI totals vs Sapo admin (manual cross-reference)
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude cancelled/voided from revenue | `status NOT IN ('CANCELLED', 'Voided')` | Revenue KPIs, Channel breakdown | Cancelled orders should not inflate revenue totals |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date | date/single | today | All cards (By Date tab only) | Flexible date lookup for reconciliation |

### Views

Multi-view: Today, Yesterday, By Date
(Identical structure per tab, only date filter differs)

### Composition

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Tong Quan Don Hang" | annotation | text-annotation | structural | full-width x minimal | Section heading | -- |
| 2 | B | Total Orders | hero | single-value-with-trend | primary | one-third x short, prominent | Total count for reconciliation | vs previous day (DoD) |
| 3 | B | Net Revenue | supporting | single-value-with-trend | primary | one-quarter x short, prominent | Main revenue metric | vs previous day (DoD) |
| 4 | B | Total Collected | supporting | single-value-with-trend | primary | one-quarter x short, prominent | Accounting reconciliation | vs previous day (DoD) |
| 5 | B | Gross Revenue | supporting | single-value-with-trend | muted | one-quarter x short, prominent | Reference: pre-discount total | vs previous day (DoD) |
| 6 | C | Total Discount | supporting | single-value-with-trend | warning | one-third x short, compact | Discount monitoring | vs previous day (DoD) |
| 7 | C | Cancelled Orders | supporting | single-value-with-trend | negative | one-third x short, compact | Exception count | vs previous day (DoD) |
| 8 | C | Returns | supporting | single-value-with-trend | negative | one-third x short, compact | Exception count | vs previous day (DoD) |
| 9 | D | "Phan Bo Theo Chieu" | annotation | text-annotation | structural | full-width x minimal | Section heading | -- |
| 10 | E | Orders by Status | breakdown | donut | series-1,series-2,series-3 | one-third x medium | Status distribution - part-to-whole | -- |
| 11 | E | Orders by Payment Status | breakdown | donut | series-1,series-2,series-3 | one-third x medium | Payment reconciliation - part-to-whole | -- |
| 12 | E | Orders by Channel | breakdown | horizontal-bar | series-emphasis | one-third x medium | Channel completeness - ranked | -- |
| 13 | F | "Canh Bao" | annotation | text-annotation | structural | full-width x minimal | Section heading | -- |
| 14 | G | Flagged Orders | detail | data-table-formatted | negative | full-width x medium | Anomalies requiring investigation | -- |
| 15 | H | "Chi Tiet Doi Soat" | annotation | text-annotation | structural | full-width x minimal | Section heading | -- |
| 16 | I | Order Detail List | detail | data-table-formatted | structural | full-width x tall, compact | Full order listing for line-by-line reconciliation | -- |
