---
title: "Design Spec v2 Format — Detailed Specification"
status: reference
created: 2026-05-28
updated: 2026-05-28
---

See [research-foundation.md](research-foundation.md) for sources.

## 1. Frontmatter v2 Schema

```yaml
---
title: Daily Sales Dashboard [Retail]
spec_version: 2                          # NEW
archetype: Operational Cockpit
status: final | draft | draft-from-capture
last_modified: 2026-05-28
domain_refs: [domains/sales.md]
sql_dialect: duckdb                       # NEW — relevant when inline SQL present
grid_base: 18                             # NEW — reference grid (deployer scales)
scope: retail                             # NEW — common filter macro

# Dashboard-wide defaults (inheritable by widgets)
defaults:
  number_format:                          # NEW — DRY for common formatting
    currency: VND
    decimals: 0
    compact: true
  comparison_frame: previous-day          # NEW — DRY for KPI cards
  color_scheme:
    positive: positive
    negative: negative

# Tab standards intent (deployer renders tool-native widgets)
tab_standards:                            # NEW
  period_header:
    cadence: daily                        # daily | weekly | monthly
    template: "📅 Hôm nay: {today} · Hôm qua: {yesterday}"
  source_freshness:
    per_tab: true                         # text per tab (declared in tab section)
---
```

---

## 2. Section Ordering (preserved)

1. `## Design Spec: {Title}` + definition block (unchanged from current template)
2. `### Brief` (unchanged — human-readable description)
3. `### Constraints & Filters` (enhanced — structured YAML for interactive filters)
4. `### Views` (unchanged — list of tabs)
5. `### Composition` (composition table — adds Widget ID column)
6. `### Widget Details` (NEW — per-widget SQL/metric_ref + config YAML)
7. `### Tab Standards` (NEW — per-tab declarations for source/freshness)
8. `### Action Map` (unchanged)
9. `### Dashboard Finish Checklist` (unchanged)

---

## 3. Widget ID Strategy

Slug-based: `W:net-revenue`. ASCII kebab-case only. Dashboard-local uniqueness.

Regex: `^W:[a-z0-9-]+$`

Widget IDs used for:
- Cross-referencing between Composition table and Widget Details section
- Parser deduplication check
- Filter auto-wiring by slug in deployer
- Round-trip identity (capture → spec → deploy → capture diff)

---

## 4. Widget Details — Hybrid Data Binding

```markdown
#### W:net-revenue

**Domain**: [Net Revenue](../domains/sales.md#2-net-revenue)

```yaml widget-config
# Option A: Metric reference (endgame — Phase 4+)
data:
  metric: net_revenue from sales
  dimensions: [order_date]
  filters:
    - { field: customer_type, op: '=', value: RETAIL }
    - { field: is_sales_channel, op: '=', value: true }
  comparisons:
    - { type: previous-period, label: "vs hôm qua" }

# Option B: Inline SQL (stepping stone — Phase 2-3)
# data:
#   sql_dialect: duckdb
#   sql: |
#     SELECT COALESCE(SUM(CASE WHEN ...), 0) as "Net Revenue", ...

# Viz-type-specific (single-value-with-trend)
viz:
  type: single-value-with-trend
  format: { inherit_from: defaults }       # uses dashboard defaults
  positive_direction: up

# Position (semantic — converter computes grid)
layout:
  row: D                                   # composition table row
  width: one-third
  height: short
  text_size: prominent

# Optional escape hatch
overrides:
  metabase:
    column_settings:
      "Net Revenue":
        scale: 0.000001                    # rare Metabase-specific tweak
```
```

The `widget-config` YAML block is the **machine-parseable layer**. Composition table is human overview.

**Phase guidance**:
- Phase 0-3: use Option B (inline SQL). All migrated specs start here.
- Phase 4+: migrate to Option A as aggregation engine matures (widget-by-widget).
- Both modes coexist in same spec — no hard cutover required.

---

## 5. Composition Table (with Widget ID column)

| # | Widget ID | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----------|-----|------|------|----------|-------|------|---------------|------------|
| 5 | `W:net-revenue` | D | Net Revenue | hero | single-value-with-trend | primary | one-third × short | Doanh thu hôm nay | DoD |

**Backward compat**: Old 8-column tables (without Widget ID) still supported by parser (v1 compat). Parser auto-detects column count:
- 8 columns → v1, Widget ID auto-derived via slugification of card name
- 9 columns → v2, explicit Widget ID used

---

## 6. Tab Standards — Intent vs Implementation

Tab Standards are **intent** declared in spec frontmatter. Each tool implements natively.

### Spec declaration (tool-agnostic)

```yaml
tab_standards:
  period_header:
    cadence: daily
    template: "📅 Hôm nay: {today} · Hôm qua: {yesterday}"
  source_freshness:
    per_tab: true
```

Per-tab in `### Tab Standards` section:

```markdown
### Tab Standards

**Tab: Tổng quan**
- Source: fact_orders · Updated real-time · Excludes cancelled/voided orders
```

### Per-tool rendering

| Tool | period_header rendering |
|------|-------------------------|
| Metabase | Scalar question with SQL `strftime(current_date, ...)` at row 0, full-width × 2 |
| Evidence | `<DateRange/>` component or markdown header |
| Superset | Markdown widget at top, dynamic date inserted via Jinja |
| Looker | `text:` element with templated dashboard parameter |

Spec stays clean; deployers handle tool quirks.

---

## 7. Semantic Layer Migration Path (Phase 4+)

### Stage 0 (Phase 0-3): Inline SQL everywhere

- All migrated specs use `data: { sql_dialect: duckdb, sql: ... }`
- Captures from existing blueprints preserve SQL verbatim
- Domain files unchanged

### Stage 1 (Phase 4 spike): Simple metric refs

- Domain files add executable metric block (YAML inside markdown):
  ```yaml
  metric_def:
    name: net_revenue
    base_model: fact_orders
    measure: SUM(net_revenue)
    default_filters:
      - is_sales_channel = true
    time_dimension: order_timestamp
  ```
- Aggregation engine handles SUM/COUNT/AVG + dimensions + filters + time grain
- Migrate 5 simple widgets first, validate engine

### Stage 2 (Phase 4 main): Comparison engine

- Generator handles previous-period, year-over-year, vs-target
- Migrate KPI-heavy dashboards

### Stage 3 (Phase 4 stretch): Complex metrics

- Composite metrics (Health Score = weighted sum of components)
- May defer to dbt MetricFlow if engine grows too complex

### Stage 4 (Future): Looker/Lightdash deployers

- Once metric_ref is dominant, emit LookML measure refs instead of SQL
- True tool-agnostic at last
