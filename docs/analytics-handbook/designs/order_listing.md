---
title: Order Listing
archetype: Operational Cockpit
status: final
last_modified: 2026-04-09
domain_refs: [domains/sales.md]
playbook_ref: playbooks/orders_list_reconciliation.md
---

## Design Spec: Order Listing

### Brief

- **Audience:** Store Managers, Sales Ops, Data Team — daily operational check
- **Time budget:** 10-15 min, daily morning/evening
- **Primary question:** "Dữ liệu đơn hàng trong BI có khớp với Sapo không?"
- **Decision enabled:** Identify data gaps, flag anomalies for investigation, cross-check counts/amounts with source system
- **Comparison frame:** DoD (vs previous day) for KPIs; BI totals vs Sapo admin (manual cross-reference)
- **Archetype:** Operational Cockpit
- **Domain references:** [domains/sales.md](../domains/sales.md)

### Core Principle: Tab Parity (NON-NEGOTIABLE)

**All 3 tabs (Today / Yesterday / By Date) MUST be byte-identical in structure, visual treatment, and narrative.** Only the underlying date predicate differs:

| Tab | Date Predicate | Filter Visible |
|-----|----------------|---------------|
| Today | `order_date = current_date` | none |
| Yesterday | `order_date = current_date - 1` | none |
| By Date | `order_date = {{date_filter}}` (default today) | Date picker |

**Drift prevention rule:** When adding or editing ANY card/annotation on one tab, the exact same change MUST be replicated on the other two tabs in the same commit. Section annotations, footers, Row A narrative cards, KPIs, tables — all must be mirrored. The blueprint deploy script is the single source of truth; never hand-edit one tab in the Metabase UI.

**Historical drift found 2026-04-09** (the reason for this redesign):
- Today tab had 4 section annotations + 0 footer
- Yesterday tab had 0 annotations
- By Date tab had 1 footer only, 0 section annotations
- Data cards themselves were consistent (same viz types, same sizes, same positions)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude cancelled/voided from revenue | `status NOT IN ('CANCELLED', 'Voided')` | Revenue KPIs, Channel breakdown | Cancelled orders should not inflate revenue totals |
| Include cancelled in Total Orders count | no filter on `status` | `Total Orders` KPI | Order count is a reconciliation number — must match Sapo's raw count including cancelled |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date | date/single | today | All cards (By Date tab only) | Flexible date lookup for reconciliation |

### Views

Multi-view: `Today`, `Yesterday`, `By Date` — identical structure per tab, only date predicate differs. **Tab Parity rule** applies (see above).

### Composition

Row widths sum to full-width = 18 columns. Section row letters advance alphabetically top-to-bottom.

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | **Reconciliation Checklist** — "Đối chiếu BI vs Sapo: (1) So Total Orders với Sapo Admin > Đơn hàng cùng ngày. (2) So Net Revenue và Total Collected. (3) Kiểm tra DoD arrow bất thường. (4) Quét Flagged Orders. (5) Nếu lệch > 1 đơn → mở Order Detail List, search order code trên Sapo." | annotation | text-callout | structural (bordered) | full-width × 2 rows | User affordance — explicit reconciliation workflow on-screen | — |
| 2 | A | **Data Freshness** — `MAX(ingested_at)` or `current_timestamp - MAX(fact_orders.updated_at)` | annotation | single-value-label | muted (green if < 2h, amber if 2-6h, red if > 6h) | one-sixth × 2 rows | "Data last synced X min ago" — tells user if reconciliation is meaningful | — |
| 3 | B | **"▸ Tổng quan đơn hàng — số cần đối soát với Sapo"** | annotation | text-heading (h3) | structural | full-width × 1 row | Section heading, imperative | — |
| 4 | C | Total Orders | hero | single-value-with-trend | primary | 6 cols × 4 rows, prominent | Total count for reconciliation (INCLUDES cancelled — must match Sapo raw count) | vs previous day (DoD) |
| 5 | C | Net Revenue | supporting | single-value-with-trend | primary | 4 cols × 4 rows, prominent | Main revenue metric | vs previous day (DoD) |
| 6 | C | Total Collected | supporting | single-value-with-trend | primary | 4 cols × 4 rows, prominent | Accounting reconciliation | vs previous day (DoD) |
| 7 | C | Gross Revenue | supporting | single-value-with-trend | muted | 4 cols × 4 rows, prominent | Reference: pre-discount total | vs previous day (DoD) |
| 8 | D | Total Discount | supporting | single-value-with-trend | warning | 6 cols × 4 rows, compact | Discount monitoring | vs previous day (DoD) |
| 9 | D | Cancelled Orders | supporting | single-value-with-trend | negative | 6 cols × 4 rows, compact | Exception count (sub-count of Total Orders) | vs previous day (DoD) |
| 10 | D | Returns | supporting | single-value-with-trend | negative | 6 cols × 4 rows, compact | Exception count | vs previous day (DoD) |
| 11 | E | **"▸ Phân bổ theo chiều — phát hiện lệch trạng thái, thanh toán, kênh"** | annotation | text-heading (h3) | structural | full-width × 1 row | Section heading, imperative | — |
| 12 | F | Orders by Status | breakdown | donut | series-1..n | 6 cols × 6 rows | Status distribution — part-to-whole, spot OPEN/CANCELLED spikes | — |
| 13 | F | Orders by Payment Status | breakdown | donut | series-1..n | 6 cols × 6 rows | Payment reconciliation — unpaid/refunded detection | — |
| 14 | F | Orders by Channel | breakdown | horizontal-bar | series-emphasis | 6 cols × 6 rows | Channel completeness — ranked, detect missing channels | — |
| 15 | G | **"▸ Đơn bất thường — cần mở Sapo xác minh từng dòng"** | annotation | text-heading (h3) | structural | full-width × 1 row | Section heading, imperative | — |
| 16 | H | Flagged Orders | detail | data-table-formatted | negative highlight | full-width × 5 rows | Anomalies (100% Discount, Negative Revenue, Discount > Gross, Completed-but-Unpaid, Refunded) | — |
| 17 | I | **"▸ Chi tiết đơn hàng — search order code trên Sapo nếu lệch"** | annotation | text-heading (h3) | structural | full-width × 1 row | Section heading, imperative | — |
| 18 | J | Order Detail List | detail | data-table-formatted | structural | full-width × 10 rows, compact | Full order listing for line-by-line reconciliation | — |
| 19 | K | **Footer** — "Source: `fact_orders` · dbt updates every 10 min via Dagster incremental job · Filter: status NOT IN (CANCELLED, Voided) for revenue KPIs · Playbook: [orders_list_reconciliation](../playbooks/orders_list_reconciliation.md) · For help: #data-team" | annotation | text-footer | muted | full-width × 1 row | Provenance + escalation path | — |

**Row widths verification:**
- Row A: 18 (checklist) — actually split as 15 (checklist) + 3 (freshness); sums to 18 ✅
- Row B: 18 (annotation) ✅
- Row C: 6 + 4 + 4 + 4 = 18 ✅
- Row D: 6 + 6 + 6 = 18 ✅
- Row E: 18 (annotation) ✅
- Row F: 6 + 6 + 6 = 18 ✅
- Row G: 18 (annotation) ✅
- Row H: 18 (flagged table) ✅
- Row I: 18 (annotation) ✅
- Row J: 18 (detail table) ✅
- Row K: 18 (footer) ✅

**Total height per tab:** 2 (Row A) + 1 + 4 + 4 + 1 + 6 + 1 + 5 + 1 + 10 + 1 = **36 rows**. Cockpit density limit is ~40 rows/view → within budget.

### Delta from Live Dashboard (what to change)

| Change | Tabs affected | Rationale |
|--------|--------------|-----------|
| **Add Row A (Reconciliation Checklist + Data Freshness)** | All 3 tabs | Eliminates "what do I do with this?" friction; surfaces staleness risk |
| **Add all 4 section headings + footer to Yesterday tab** | Yesterday only (currently has 0 annotations) | Harmonize with Today |
| **Add all 4 section headings to By Date tab** | By Date (currently has 1 footer only) | Harmonize with Today |
| **Rewrite section heading text** | All 3 tabs | Imperative voice with reconciliation-specific hints ("cần mở Sapo xác minh...") replaces passive descriptions ("Điều tra đơn bất thường...") |
| **Add footer to Today tab** | Today only (currently no footer) | Harmonize — all 3 tabs need provenance + escalation path |
| **Standardize footer text** | All 3 tabs | Current By Date footer says "Updated daily" which is WRONG — Dagster incremental runs every 10 min. Fix this lie. |
| **Data Freshness scalar** | All 3 tabs (new card, new SQL) | New: surface data-platform lag as a first-class signal. Query: `SELECT NOW() - MAX(updated_at) FROM fact_orders` or pipe from Dagster metadata if available. |

**Blueprint impact:** Moderate. Requires:
- New SQL card for Data Freshness (single scalar with conditional formatting)
- New text card rows (Row A checklist, Row K footer) — 2 new cards per tab × 3 tabs = 6 new text cards
- Rewrite of 4 section annotation text cards per tab × 3 tabs (Today already has 4, Yesterday/By Date need fresh ones) = 12 text cards touched
- No changes to the 12 data cards themselves (their MBQL queries and viz settings are already correct and identical across tabs)

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| **Data Freshness** | Stale data | Age > 2h | STOP reconciliation — data may be mid-ingest. Check Dagster realtime job status before continuing. |
| **Data Freshness** | Very stale | Age > 6h | Escalate to Data Team immediately — pipeline likely broken |
| **Total Orders** | Count mismatch with Sapo | `BI count != Sapo admin count` | (1) Verify Sapo filter = all statuses, same date. (2) If still off: check Dagster `sapo_realtime_sync_job` for failures. (3) If multi-day gap: run `sapo_nightly_reconciliation_job` manually. |
| **Net Revenue** | Revenue gap | > 5% vs Sapo | Review `status NOT IN ('CANCELLED', 'Voided')` filter. Check discount logic in `fact_orders.net_revenue` computation. |
| **Cancelled Orders** | Spike | DoD > +50% | Cross-check channels with high cancel — may be operational (stock-out, fraud block) or ingestion (stuck-pending flips). |
| **Returns** | Spike | DoD > +50% | Check products driving returns; contact logistics if physical issue. |
| **Orders by Channel** | Missing channel | Channel count < expected | Likely ingestion gap for that channel — check `sapo_webhook_consumer_asset` logs. |
| **Flagged Orders** | Any rows | Rows > 0 | Open each flagged row → search order code on Sapo → classify as data-bug, real-anomaly, or user-error. Report data bugs to Data Team. |
| **Orders by Status** | Unusual distribution | Any status > 30% unexpected | Confirm system state, check pipeline processing timeline. |

### Visual Language Notes

- **Color tokens only** — never hex codes. Use `primary`, `muted`, `warning`, `negative`, `structural`, `series-N`.
- **Size hierarchy:** `Total Orders` (hero, 6 cols) > other KPIs (supporting, 4 or 6 cols) > section annotations (1 row tall) > detail tables.
- **Icon prefix `▸`** on section headings gives visual anchor for skimming without adding chart-junk.
- **Data Freshness card** uses conditional color semantics (green/amber/red) — the only card allowed to change color based on value, because it's a health signal not a metric.
- **No pie chart > 6 slices** — Orders by Status with 7+ statuses must collapse to top-5 + "Other".

### Dashboard Finish Checklist

- [x] Every card has a title per Title Discipline
- [x] Every KPI has ≥1 comparison (DoD)
- [x] Text annotations use imperative voice with Sapo-reconciliation hints
- [x] No orphan cards
- [x] Action Map covers every card with a signal meaningful for reconciliation
- [x] Hero card (Total Orders) in first KPI row, prominent (6 cols)
- [x] Row widths sum = full-width (18 cols) — verified row-by-row above
- [x] Density within Cockpit limit (~16 data cards + annotations + freshness = 14 data cards + 6 annotations per tab)
- [x] Each tab has ≥1 section divider — now 4 dividers + 1 footer + Row A, consistent across all 3 tabs
- [x] Color tokens consistent — no hex codes
- [x] Size hierarchy clear: hero > supporting > detail
- [x] **Tab Parity invariant explicit** in spec (new for 2026-04-09)
- [x] **Data Freshness** card added as first-class health signal (new)
- [x] **Reconciliation Checklist** card on Row A replaces implicit workflow knowledge (new)

### Open Questions

1. **Data Freshness source of truth** — should the card read `MAX(fact_orders.updated_at)` (dbt output lag) or pull from Dagster metadata (actual pipeline finish time)? The former is simpler but may lag dbt by several minutes; the latter is accurate but requires a Dagster metadata exposure. Recommend starting with `MAX(updated_at)` and upgrading later if needed.
2. **Today tab's `current_date` semantics in DuckDB + `TimeZone = 'Asia/Ho_Chi_Minh'`** — need to verify the date predicate evaluates in VN timezone, not UTC. Quick test: open Today tab at 00h05 VN → `Total Orders` should show ~0 orders, not yesterday's total.
3. **Tab Parity enforcement** — should we add a deploy-time assertion in `deploy_from_markdown.js` that blocks deploys where the 3 tabs diverge in text annotation set? This would mechanically prevent drift recurrence.
