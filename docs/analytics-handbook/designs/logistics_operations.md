---
title: "Logistics Operations Center"
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/logistics.md]
---

## Design Spec: Logistics Operations Center

### Brief

- **Audience:** Operations Manager — giam sat xu ly don hang hang ngay, revisit nhieu lan trong ngay
- **Time budget:** 10-15 min working session across 3 tabs, revisit nhieu lan trong ngay
- **Primary question:** "Pipeline don hang hom nay dang chay the nao so voi hom qua?"
- **Decision enabled:** Phat hien don bi nghen (stuck), dieu chinh nhan su/uu tien xu ly, escalate don qua han
- **Comparison frame:** DoD (today vs yesterday) — real-time so sanh
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/logistics.md](../domains/logistics.md)

### Data Availability Notes

| Data Element | Status | Source | Notes |
|---|---|---|---|
| Order status, fulfillment_status | Available | `fact_orders` | OPEN, COMPLETED, CANCELLED, ARCHIVED, DRAFT |
| `first_shipped_at` | Available | `fact_orders` via `std_fulfillments` | First shipment timestamp per order |
| `time_to_complete_hours` | Available | `fact_orders` | `date_diff('hour', created_at, completed_at)` |
| `order_timestamp` (created_at) | Available | `fact_orders` | Order creation timestamp |
| Carrier-level data | **Planned** | No `dim_carriers` or `fact_shipments` | Cannot break down by carrier |
| Delivery timestamps | **Planned** | No delivery tracking | Cannot compute delivery time |
| Per-fulfillment detail | **Planned** | No `fact_fulfillments` mart | Only first shipment available |

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude draft orders | `status != 'DRAFT'` | All cards | Drafts not yet in pipeline |
| Exclude cancelled for speed metrics | `status != 'CANCELLED'` | Speed & throughput cards | Cancelled orders skew processing time |

**Interactive Filters:** Khong co — Operational Cockpit real-time, zero-interaction.

### Views

Multi-view — 3 views:
1. Tong quan (Pipeline Overview)
2. Toc do xu ly (Processing Speed)
3. Chi tiet & Nhan vien (Details & Staff)

---

### View 1 — Tong quan Pipeline

**Narrative flow:** "Suc khoe pipeline?" -> "Don dang o buoc nao?" -> "Fulfillment rate hom nay?" -> "Don moi theo gio?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Giam sat pipeline don hang — hom nay dang xu ly the nao?" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 2 | B | Fulfillment Rate | hero | gauge | positive/warning/negative (zones: 95-100/85-94/0-84) | one-third x medium, prominent | Ty le don da xuat kho / tong don eligible | vs benchmark (zones) |
| 3 | B | Total Orders Today | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Tong don hom nay | vs previous period (DoD %) |
| 4 | B | Shipped Orders | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Don da xuat kho | vs previous period (DoD %) |
| 5 | B | Avg Time to Complete | supporting | single-value-with-trend | secondary, positive/negative (DoD, inverted: lower=good) | one-quarter x short, standard | Thoi gian hoan thanh TB (gio) | vs previous period (DoD %) |
| 6 | C | "Phan bo trang thai don hang" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Order Status Funnel | breakdown | funnel | series-1..series-5 | half x medium | Drop-off theo tung buoc pipeline | sequential conversion |
| 8 | D | Fulfillment Status Breakdown | breakdown | donut | series-1..series-4 | half x medium | Ty le fulfilled/unfulfilled/partial | composition |
| 9 | E | "Luong don theo gio hom nay" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 10 | F | Hourly Order Intake | trend | multi-line-chart | primary (Today) + muted (Yesterday) | two-thirds x medium | Peak hours, real-time pattern | vs previous period (DoD overlay) |
| 11 | F | Cumulative Orders | trend | multi-line-chart | accent (Today) + muted (Yesterday) | one-third x medium | Running total don hang | vs previous period (DoD overlay) |

---

### View 2 — Toc do xu ly

**Narrative flow:** "Don dang xu ly nhanh hay cham?" -> "Xu huong toc do?" -> "Gio nao xu ly nhanh nhat?" -> "Don bi nghen o dau?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 12 | A | "Hieu suat xu ly don hang — toc do va bottleneck" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | B | Avg Hours to First Ship | hero | single-value-with-trend | primary, positive/negative (DoD, inverted: lower=good) | one-third x short, prominent | Thoi gian TB tu tao don den xuat kho dau tien | vs previous period (DoD %) |
| 14 | B | Same-Day Ship Rate | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Ty le don xuat kho cung ngay | vs previous period (DoD %) |
| 15 | B | Orders Pending > 24h | supporting | single-value | negative (khi > 0), neutral (khi = 0) | one-quarter x short, standard | Don bi nghen > 24h | — |
| 16 | B | Completed Today | supporting | single-value-with-trend | secondary, positive/negative (DoD) | one-quarter x short, standard | Don hoan thanh hom nay | vs previous period (DoD %) |
| 17 | C | "Xu huong toc do xu ly theo gio" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 18 | D | Hourly Avg Processing Time | trend | multi-line-chart | primary (Today) + muted (Yesterday) | two-thirds x medium | Bien dong thoi gian xu ly theo gio | vs previous period (DoD overlay) |
| 19 | D | Throughput Heatmap | breakdown | heatmap | conditional-range | one-third x medium | Cuong do xuat kho theo ngay x gio | intensity matrix |
| 20 | E | "Don hang bi nghen (OPEN > 24h)" | annotation | text-annotation | structural | full-width x minimal | Section heading — escalation zone | — |
| 21 | F | Stuck Orders Detail | detail | data-table-formatted | conditional-below on age_hours (>24h red, >12h yellow) | full-width x medium, compact | Danh sach don OPEN qua 24h, sap xep theo thoi gian cho | — |

---

### View 3 — Chi tiet & Nhan vien

**Narrative flow:** "Ai dang xu ly tot?" -> "Hieu suat theo nhan vien?" -> "Chi tiet tung don?"

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 22 | A | "Hieu suat nhan vien xu ly don" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | B | Staff Performance — Orders Processed | breakdown | horizontal-bar | primary | half x medium | Ranking nhan vien theo so don xu ly | rank/position |
| 24 | B | Staff Performance — Avg Processing Time | breakdown | horizontal-bar | secondary | half x medium | Ranking nhan vien theo toc do xu ly | rank/position |
| 25 | C | "Chi tiet don hang hom nay" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 26 | D | Order Detail Table | detail | data-table-formatted | conditional-above/conditional-below on status | full-width x tall, compact | Full detail don hang: ma don, trang thai, thoi gian, nhan vien | — |
| 27 | E | "Source: fact_orders · Updated hourly · Excludes drafts" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

---

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Fulfillment Rate (gauge) | Drop below warning zone | < 85% | Check Stuck Orders Detail, identify bottleneck status |
| Avg Hours to First Ship | Spike | DoD > +30% | Review orders pending > 24h, check staff allocation |
| Orders Pending > 24h | Any non-zero value | > 0 | Immediately review Stuck Orders Detail table, escalate oldest orders |
| Same-Day Ship Rate | Drop | DoD < -10% | Investigate hourly processing time trend for slowdowns |
| Hourly Order Intake | Unusual spike | > 2x yesterday same hour | Alert warehouse to prepare for higher volume |
| Staff Performance | Uneven distribution | Top performer > 3x bottom | Rebalance assignment, investigate blocking issues |
| Stuck Orders Detail | High count | > 5 orders stuck | Escalate to Operations Manager, check system/inventory issues |

### Summary

| Aspect | Value |
|--------|-------|
| Total cards | 27 (17 data + 10 annotations) |
| Views | 3 (Pipeline Overview, Processing Speed, Details & Staff) |
| Hero cards | 2 (Fulfillment Rate gauge in View 1, Avg Hours to First Ship in View 2) |
| Annotations | 10 section headings + 1 footer |
| Archetype compliance | Operational Cockpit — multi-view, working session, zero-filter |
| Comparison frame | DoD throughout, gauge zones for Fulfillment Rate |
| Planned metrics | Carrier breakdown, delivery time, per-fulfillment detail (see Data Availability) |
