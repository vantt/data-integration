# Research: Tool-Agnostic Design Spec Format (v2 — Deep Research)

**Date**: 2026-05-27  
**Status**: Complete  
**Sub-reports**: `researcher-260527-2348-dashboard-json-formats.md`, `researcher-260527-2348-dashboard-definition-formats.md`, `researcher-260527-visualization-type-mapping.md`

---

## 1. Gap Analysis: Current Design Spec vs Blueprint

### What Design Spec already covers (sufficient)

| Aspect | Coverage | Example |
|--------|----------|---------|
| Viz type | 25 standard terms | `single-value-with-trend` |
| Color | Semantic tokens | `primary`, `positive`, `warning` |
| Size | Semantic tokens | `one-third × short` |
| Card role | 6 roles | `hero`, `supporting`, `trend` |
| Comparison intent | Descriptive | "vs previous period (DoD %)" |
| Narrative flow | Per-view | "Sức khỏe? → KPIs? → Giờ?" |
| Action map | Signal → action table | "Revenue DoD < -15% → check channels" |

### What Design Spec lacks (gap to bridge)

| Aspect | In Blueprint | Missing from Design Spec | Severity |
|--------|-------------|-------------------------|----------|
| **SQL queries** | Full SQL per widget | None | CRITICAL — can't generate without query |
| **Grid positions** | `row/col/size_x/size_y` | Only relative tokens | LOW — calculable from tokens |
| **Number formatting** | `column_settings` | None | HIGH — VND/%, decimals, compact |
| **Comparison config** | `scalar.comparisons` | Only text description | HIGH — need column name, label |
| **Conditional formatting** | `table.column_formatting` | None | MEDIUM — need column, op, value, color |
| **Chart axis config** | `graph.dimensions/metrics` | Implicit from viz type | MEDIUM — which columns → X/Y axis |
| **Gauge segments** | `gauge.segments` | "3 zones" described | MEDIUM — need min/max/color per zone |
| **Filter config** | `metabase-filter` JSON | Generic | LOW — need slug, type, default |
| **Tab mandatory widgets** | Chu kỳ báo cáo, Source & Freshness | Not declared | MEDIUM |

---

## 2. Cross-BI-Tool Deep Analysis

### 2.1 Grid System Compatibility

All major tools converge on x/y/w/h grid. Column counts differ but our **percentage-based tokens** convert cleanly:

| Tool | Grid Cols | Height Unit | `half` maps to | `one-third` maps to |
|------|-----------|-------------|----------------|---------------------|
| **Metabase** | 18 | row units | 9 | 6 |
| **Superset** | 12 | pixels | 6 | 4 |
| **Grafana** | 24 | 30px units | 12 | 8 |
| **Looker** | 24 | tile units | 12 | 8 |
| **Lightdash** | CSS grid | flexible | 50% | 33% |
| **Power BI** | pixels | pixels | 50% | 33% |
| **Evidence** | markdown flow | implicit | `<Grid cols=2>` | `<Grid cols=3>` |

**Key insight**: Our size tokens (`half`, `one-third`, `one-quarter`, `one-sixth`, `two-thirds`, `full-width`) are inherently percentage-based — they convert to ANY grid system via `token_percentage × grid_cols`. This is already solved.

Height tokens need per-tool mapping:

| Token | Metabase (size_y) | Grafana (h) | Superset (px) | Semantic |
|-------|-------------------|-------------|---------------|----------|
| `minimal` | 1 | 2 | 30 | Text annotation |
| `short` | 3 | 4 | 120 | KPI scalar |
| `medium` | 6 | 8 | 240 | Chart |
| `tall` | 8 | 12 | 360 | Detailed table |

### 2.2 Viz Type Cross-Compatibility Matrix (25 terms × 6 tools)

| Standard Term | Metabase | Superset | Grafana | Looker | Power BI | Coverage |
|---|---|---|---|---|---|---|
| `single-value` | `scalar` | `big_number_total` | `stat` | `single_value` | `Card` | 5/5 |
| `single-value-with-trend` | `scalar`+comparisons | `big_number` | ⚠️ `stat`+sparkline | ❌ | `KPI` | 3/5 |
| `progress-toward-goal` | `progress` | ❌ | ⚠️ `gauge` | ❌ | ❌ | 1/5 |
| `gauge` | `gauge` | `gauge` | `bargauge` | ❌ | `Gauge` | 4/5 |
| `line-chart` | `line` | `echarts_timeseries_line` | `timeseries` | `looker_line` | `Line chart` | 5/5 |
| `multi-line-chart` | `line` | `echarts_timeseries_line` | `timeseries` | `looker_line` | `Line chart` | 5/5 |
| `area-chart` | `area` | `echarts_timeseries_area` | `timeseries` | ❌ | `Area chart` | 4/5 |
| `stacked-area` | `area`+stack | `echarts_timeseries_area`+stack | `timeseries`+stack | ❌ | `Area chart` | 4/5 |
| `vertical-bar` | `bar` | `echarts_timeseries_bar` | `timeseries` | `looker_column` | `Column chart` | 5/5 |
| `horizontal-bar` | `row` | `echarts_timeseries_bar`+orient | `timeseries` | `looker_bar` | `Bar chart` | 5/5 |
| `stacked-bar` | `bar`+stack | `echarts_timeseries_bar`+stack | `timeseries`+stack | `looker_column`+stack | `Stacked bar` | 5/5 |
| `grouped-bar` | `bar`(default) | `echarts_timeseries_bar` | `timeseries` | `looker_column` | `Clustered column` | 5/5 |
| `stacked-bar-time` | `bar`+stack+time | `echarts_timeseries_bar`+stack | `timeseries`+stack | `looker_column`+stack | `Stacked bar` | 5/5 |
| `combo-chart` | `combo` | `mixed_timeseries` | ❌ | ❌ | `Combo chart` | 3/5 |
| `donut` | `pie` | `pie` | `piechart` | `looker_pie` | `Pie chart` | 5/5 |
| `funnel` | `funnel` | `funnel` | ❌ | `looker_funnel` | `Funnel chart` | 4/5 |
| `waterfall` | `waterfall` | `waterfall` | ❌ | ❌ | `Waterfall chart` | 3/5 |
| `data-table` | `table` | `table` | `table` | `looker_grid` | `Table` | 5/5 |
| `data-table-formatted` | `table`+formatting | `table`+formatting | `table`+overrides | `looker_grid` | `Table` | 5/5 |
| `pivot-table` | `pivot` | `pivot_table_v2` | ❌ | ❌ | `Matrix visual` | 3/5 |
| `scatter-plot` | `scatter` | `echarts_timeseries_scatter` | ❌ | `looker_scatter` | `Scatter chart` | 4/5 |
| `geographic-map` | `map` | `mapbox`/`country_map` | `geomap` | `looker_geo_choropleth` | `Map` | 5/5 |
| `heatmap` | ⚠️ `pivot`+formatting | `heatmap` | ❌ | ❌ | ⚠️ Matrix+formatting | 2/5 |
| `sparkline` | ❌ | ❌ | ⚠️ `stat`+sparkline | ❌ | ❌ | 0/5 |
| `text-annotation` | text dashcard | `markdown` | `text` | `text` | `Text box` | 5/5 |

**Summary**: 18/25 types (72%) have native support in ALL 5 tools. 7 types need fallbacks in some tools — handled by `fallback` field in widget-config.

### 2.3 Data Binding Paradigms

Three paradigms exist across BI tools:

| Paradigm | Tools | How data flows |
|----------|-------|---------------|
| **SQL-direct** | Metabase, Superset, Grafana, Redash | Raw SQL query per widget |
| **Model-reference** | Looker, Lightdash | `explore` → `measure`/`dimension` |
| **Markdown-embedded** | Evidence.dev | Named SQL blocks referenced by components |

Our spec should support SQL-direct primarily (matches our DuckDB stack), with optional `model_ref` for future model-based tools:

```yaml
# Primary: SQL block above widget-config (unchanged)
# Optional: model reference in widget-config
model_ref:
  explore: orders
  measures: [net_revenue]
  dimensions: [order_date]
```

### 2.4 Filter Abstraction

| Concept | Metabase | Superset | Grafana | Looker |
|---------|----------|----------|---------|--------|
| Global filter def | `#### Filter:` + `metabase-filter` | `native_filter_configuration` | `templating.list` | `filters:` section |
| Filter types | `date/all-options`, `string/=` | `filter_select`, `filter_range` | `query`, `interval`, `custom` | `date_filter`, `field_filter` |
| Binding to widgets | Template tag `{{slug}}` in SQL | `targets` array → chart IDs | Variable `$variable` in SQL | `listen:` on tiles |
| Default value | `default` field | `configuration.default` | `current.value` | `default_value` |

**Common denominator**: All tools have `name`, `type`, `default`, and a binding mechanism. Our proposed filter spec covers this:

```yaml
filters:
  - name: "Date Range"
    slug: date_range
    type: date-range        # Abstract: date-range | single-select | multi-select | number-range | text
    default: last_7_days    # Abstract: last_7_days | today | this_month | custom
    applies_to: all         # all | [W5, W7, W17]
    field_ref: fact_orders.order_timestamp   # Semantic ref for model-based tools
```

### 2.5 Styling Compatibility

**Number formatting** — universal concept, different serialization:

| Our Spec | Metabase | Superset | Grafana | Evidence |
|----------|----------|----------|---------|----------|
| `style: currency` | `number_style: "currency"` | D3: `$,.0f` | `unit: "currencyVND"` | `fmt="$,.0f"` |
| `currency: VND` | `currency: "VND"` | `currencyCode: "VND"` | `unit: "currencyVND"` | custom locale |
| `decimals: 0` | `decimals: 0` | D3: `,.0f` | `decimals: 0` | `fmt=".0f"` |
| `compact: true` | `compact: true` | D3: `~s` | `unit: "short"` | `compact` prop |

**Conditional formatting** — universal concept:

| Our Spec | Metabase | Superset | Grafana |
|----------|----------|----------|---------|
| `operator: ">="` | `table.column_formatting[].operator` | Chart params (varies) | `fieldConfig.defaults.thresholds.steps` |
| `value: 20` | `value: 20` | threshold value | `value: 20` |
| `color: positive` | `color: "#84BB4C"` | `color: "#84BB4C"` | `color: "green"` |

All tools support the same logical model; only serialization differs.

### 2.6 What CANNOT Be Ported (Genuine Non-Portables)

| Feature | Why not portable | Recommendation |
|---------|-----------------|----------------|
| Drill-through / click actions | Completely different per tool | Don't abstract — use `overrides` |
| Row-level security | Tool-specific auth model | Out of spec scope |
| Caching strategy | Tool-managed | Out of spec scope |
| User permissions | Tool-specific | Out of spec scope |
| Embedding config | Different SDKs | Out of spec scope |
| Real-time refresh | Different mechanisms | Out of spec scope |
| Tool-specific viz features | e.g., Metabase `scalar.comparisons` vs Grafana `graphMode` | Use `overrides` escape hatch |

---

## 3. Enhanced Format Design (v2)

### 3.1 Architecture Principle: Three-Layer Spec

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 1: Composition (HUMAN-OPTIMIZED)                       │
│  → Composition table, Brief, Action Map, Narrative Flow      │
│  → Read by: humans, reviewers, stakeholders                  │
│  → Unchanged from current Design Spec                        │
├──────────────────────────────────────────────────────────────┤
│ Layer 2: Widget Details (MACHINE-PARSEABLE)                   │
│  → SQL + widget-config YAML per widget                       │
│  → Read by: conversion scripts                               │
│  → NEW — bridges gap between spec and blueprint              │
├──────────────────────────────────────────────────────────────┤
│ Layer 3: Tool Overrides (ESCAPE HATCH)                       │
│  → Per-tool settings in widget-config YAML                   │
│  → Read by: tool-specific converter only                     │
│  → Keeps Layer 2 clean while handling edge cases             │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Document Structure

```
---
title: [Dashboard Title]
archetype: [Executive Pulse / Operational Cockpit / Exploratory Tool]
status: [final / draft / draft-from-capture]
last_modified: YYYY-MM-DD
domain_refs: [domains/sales.md]
sql_dialect: duckdb                          ← NEW
grid_base: 18                                ← NEW (default 18, for reference)
---

## Design Spec: [Title]

### Brief                                    (unchanged)
### Constraints & Filters                    (enhanced — structured filter YAML)
### Views                                    (unchanged)
### Composition                              (unchanged — overview table)
### Action Map                               (unchanged)

### Widget Details                           ← NEW
#### W:{widget-slug}                         ← per-widget section
(SQL + widget-config YAML)

### Tab Standards                            ← NEW
(Chu kỳ báo cáo + Source & Freshness)

### Dashboard Finish Checklist               (unchanged)
```

### 3.3 Widget ID Strategy

Use **stable slug IDs** (not sequential numbers) — robust against reordering:

```markdown
#### W:net-revenue
#### W:health-score
#### W:hourly-sales-trend
#### W:section-health           ← text annotation
```

Composition table references these IDs:

| ID | Row | Card | Role | Viz Type | ... |
|----|-----|------|------|----------|-----|
| `W:section-health` | A | "Đánh giá sức khỏe..." | annotation | text-annotation | ... |
| `W:health-score` | B | Health Score | supporting | gauge | ... |
| `W:net-revenue` | D | Net Revenue | hero | single-value-with-trend | ... |

### 3.4 Widget-Config Schema (v2 — Full Reference)

```yaml
# =====================================================
# DATA BINDING
# =====================================================
# Primary: SQL block (``` sql) above this YAML block
# Optional: model reference for non-SQL tools
model_ref:
  explore: <explore_name>
  measures: [<measure_names>]
  dimensions: [<dimension_names>]

# =====================================================
# VIZ-TYPE-SPECIFIC CONFIG
# =====================================================

# --- single-value-with-trend ---
comparison:
  type: another-column | previous-period | vs-target
  column: "<SQL result column>"
  label: "<display label>"
  positive_direction: up | down       # is increase good (up) or bad (down)?

# --- gauge ---
gauge:
  segments:
    - range: [<min>, <max>]
      color: <color-token>
      label: "<zone label>"

# --- charts (line, bar, area, combo, scatter) ---
chart:
  dimensions: ["<x-axis column>"]
  metrics: ["<y-axis columns>"]
  colors: [<color-tokens>]
  x_label: "<axis title>"
  y_label: "<axis title>"
  stack: none | stacked | normalized
  orientation: vertical | horizontal
  series_type:                          # combo charts only
    "<series>": line | bar | area

# --- tables ---
table:
  pivot: true | false
  hidden_columns: ["<col>"]
  columns: ["<ordered visible columns>"]

# --- pie/donut ---
pie:
  dimension: ["<category column>"]
  metric: "<value column>"
  style: pie | donut

# --- progress ---
progress:
  goal: <number>
  color: <color-token>

# --- funnel ---
funnel:
  dimension: "<step column>"
  metric: "<value column>"

# --- waterfall ---
waterfall:
  dimension: "<category column>"
  metric: "<value column>"

# =====================================================
# FORMATTING (any viz type)
# =====================================================
format:
  "<column_name>":
    style: currency | percent | number | plain
    currency: VND | USD | EUR | ...
    decimals: <int>
    compact: true | false

# =====================================================
# CONDITIONAL FORMATTING (data-table-formatted)
# =====================================================
conditional_format:
  - columns: ["<col>"]
    operator: ">=" | "<" | "=" | "between" | "is-null"
    value: <number | [min, max]>
    color: <color-token>                # semantic, NOT hex
    highlight_row: true | false

# =====================================================
# FALLBACK (for viz types not universal)
# =====================================================
fallback:
  if_unsupported: <alternative-standard-viz-term>
  notes: "<when/why to fallback>"

# =====================================================
# PER-TOOL OVERRIDES (escape hatch)
# =====================================================
overrides:
  metabase:
    <any Metabase visualization_settings key>: <value>
  superset:
    <any Superset chart params key>: <value>
  grafana:
    <any Grafana fieldConfig/options key>: <value>
```

### 3.5 Concrete Examples

#### Example 1: Scalar KPI — Net Revenue

```markdown
#### W:net-revenue

**Domain**: [Net Revenue](../domains/sales.md#2-net-revenue)

‍```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date
        THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day'
        THEN o.net_revenue END), 0) as "Hôm qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND c.customer_type = 'RETAIL'
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
‍```

‍```yaml widget-config
comparison:
  type: another-column
  column: "Hôm qua"
  label: "vs hôm qua"
  positive_direction: up

format:
  "Net Revenue":
    style: currency
    currency: VND
    decimals: 0
    compact: true
‍```
```

**Conversion output per tool**:

| Tool | Generated output |
|------|-----------------|
| Metabase | `"display": "scalar", "scalar.comparisons": [{type: "anotherColumn", column: "Hôm qua"}], "column_settings": {"Net Revenue": {number_style: "currency", currency: "VND"}}` |
| Superset | `"viz_type": "big_number_total", "metric": "Net Revenue", "number_format": "$,.0f", "currency_format": {"currencyCode": "VND"}` |
| Grafana | `"type": "stat", "fieldConfig.defaults.unit": "currencyVND", "options.graphMode": "none"` |
| Evidence | `<BigValue data={net_revenue} value=Net_Revenue fmt="$,.0f" comparison=Hôm_qua />` |

#### Example 2: Gauge — Health Score

```markdown
#### W:health-score

‍```sql
WITH ... SELECT revenue_score + orders_score + loyalty_score + aov_score as "Health Score" FROM scores
‍```

‍```yaml widget-config
gauge:
  segments:
    - range: [0, 49]
      color: negative
      label: "Báo động"
    - range: [49, 74]
      color: warning
      label: "Chú ý"
    - range: [74, 100]
      color: positive
      label: "Khỏe mạnh"

fallback:
  if_unsupported: single-value
  notes: "Looker has no gauge; display as number with conditional color"
‍```
```

#### Example 3: Line Chart — Hourly Sales Trend

```markdown
#### W:hourly-sales-trend

‍```sql
WITH current_sales AS (...), previous_sales AS (...)
SELECT hour_of_day as "Hour", sales_today as "Hôm nay", sales_yesterday as "Hôm qua"
FROM ...
‍```

‍```yaml widget-config
chart:
  dimensions: ["Hour"]
  metrics: ["Hôm nay", "Hôm qua"]
  colors: [primary, muted]
  x_label: "Giờ trong ngày"
  y_label: "Doanh thu"
‍```
```

#### Example 4: Table with Conditional Formatting

```markdown
#### W:health-breakdown

‍```sql
SELECT 'Doanh thu (WoW)' as "Thành phần", rev_wow as "Thay đổi %",
       rev_sc as "Điểm", ... as "Status"
FROM ...
‍```

‍```yaml widget-config
table:
  pivot: false
  hidden_columns: ["sort"]
  columns: ["Thành phần", "Thay đổi %", "Điểm", "Status"]

conditional_format:
  - columns: ["Điểm"]
    operator: ">="
    value: 20
    color: positive
    highlight_row: true
  - columns: ["Điểm"]
    operator: "<"
    value: 12
    color: negative
    highlight_row: true
‍```
```

#### Example 5: Text Annotation

```markdown
#### W:section-health

*(Text annotations derive content from composition table — no SQL or config needed)*
```

### 3.6 Enhanced Filter Section

```markdown
### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Retail only | `customer_type = 'RETAIL'` | All widgets | Dashboard scope |
| Sales channels | `is_sales_channel = true` | All widgets | Exclude internal |

**Interactive Filters:**

‍```yaml filters
- name: "Date Range"
  slug: date_range
  type: date-range
  default: last_7_days
  applies_to: all
  field_ref: fact_orders.order_timestamp

- name: "Channel"
  slug: channel
  type: single-select
  default: null
  applies_to: [W:revenue-by-channel, W:channel-performance]
  field_ref: dim_channels.channel_name
‍```

*(Nếu không có filter: ghi "Không có — [Archetype] cần zero-interaction")*
```

### 3.7 Tab Standards Section

```markdown
### Tab Standards

**Chu kỳ báo cáo** (auto-injected, every tab, row 0):
- Cadence: daily
- Template: `📅 Hôm nay: {today} · Hôm qua: {yesterday}`
- Size: full-width × 2

**Source & Freshness** (every tab, last row):
- Content per tab: declared as last annotation in each view's composition table
- Size: full-width × minimal
```

---

## 4. Conversion Architecture (Multi-Tool)

### 4.1 Flow Diagram

```
                         Design Spec (source of truth)
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
             [Metabase     [Superset    [Evidence
              Converter]    Converter]   Converter]
                    │           │           │
          reads:    │           │           │
          VIZ_CATALOG_*.md     │           │
          + size→grid algo     │           │
                    ▼           ▼           ▼
             Blueprint     Dashboard    Evidence
             (*.md)        JSON         Page (*.md)
                    │           │           │
                    ▼           ▼           ▼
             deploy_from   superset     evidence
             _markdown.js  import CLI   dev server
                    │           │           │
                    ▼           ▼           ▼
              Metabase     Superset     Evidence
```

### 4.2 Shared Parser + Per-Tool Adapter

```
design-spec-parser.js          ← NEW (shared across all converters)
  ├── parse frontmatter
  ├── parse composition table
  ├── parse widget details (SQL + YAML)
  ├── parse filters YAML
  ├── parse tab standards
  └── return: DesignSpec object

convert-to-metabase.js         ← NEW (replaces manual blueprint authoring)
  ├── reads: METABASE_VIZ_CATALOG.md
  ├── maps: viz types, colors, sizes
  ├── generates: Blueprint markdown
  └── applies: overrides.metabase

convert-to-superset.py         ← FUTURE
  ├── reads: SUPERSET_VIZ_CATALOG.md (new)
  ├── maps: viz types, params, filters
  └── generates: Dashboard JSON for import

convert-to-evidence.py         ← FUTURE (low effort — markdown→markdown)
  ├── reads: EVIDENCE_VIZ_CATALOG.md (new)
  ├── maps: viz types → Evidence components
  └── generates: Evidence .md page
```

### 4.3 Size Token → Grid Position Algorithm

Width mapping (percentage → any grid):

```
token_to_cols(token, grid_cols):
  ratios = {
    "full-width": 1.0,
    "two-thirds": 2/3,
    "half": 1/2,
    "one-third": 1/3,
    "one-quarter": 1/4,
    "one-sixth": 1/6
  }
  return round(ratios[token] * grid_cols)
```

Row calculation:
1. Group widgets by Row letter (A, B, C...) from composition table
2. For each row, calculate `col` by accumulating widths left-to-right
3. Calculate `row` by accumulating max heights of preceding rows
4. Validate: total width per row must equal grid_cols

### 4.4 VIZ_CATALOG Pattern (per tool)

Each target tool has its own catalog file. Same structure as existing `METABASE_VIZ_CATALOG.md`:

```markdown
# {TOOL}_VIZ_CATALOG.md

## Viz Type Translation
| Standard Term | {Tool} Type | Settings Notes |
|---|---|---|

## Color Token → {Tool} Color
| Token | {Tool} Value | Notes |
|---|---|---|

## Number Format Mapping
| Our Format | {Tool} Format | Example |
|---|---|---|
```

Currently exists: `METABASE_VIZ_CATALOG.md` (complete).
To create when needed: `SUPERSET_VIZ_CATALOG.md`, `GRAFANA_VIZ_CATALOG.md`, `EVIDENCE_VIZ_CATALOG.md`.

### 4.5 Conversion Effort per Tool

| Target | Effort | Complexity | Why |
|--------|--------|------------|-----|
| **Metabase** | 2-3 days | Medium | VIZ_CATALOG exists; generate blueprint markdown |
| **Evidence** | 1-2 days | Low | Markdown → markdown; SQL → SQL; components map directly |
| **Superset** | 3-5 days | High | Complex position JSON hierarchy; D3 format strings; filter targets |
| **Grafana** | 2-3 days | Medium | Simple panel JSON; but weak analytics viz coverage |
| **Looker** | N/A | Very High | Requires LookML model — not SQL-compatible |
| **Power BI** | N/A | Very High | Requires DAX + data model — not SQL-compatible |

**Recommended priority**: Metabase (current) → Evidence (preview/second target) → Superset (likely migration) → Grafana (if needed).

---

## 5. Trade-offs and Decisions

### 5.1 Blueprint: Keep or Eliminate?

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| A: Eliminate entirely | Single source, no drift | Lose deploy snapshot; capture script broken | ❌ |
| **B: Keep as generated artifact** | Inspectable; capture unchanged; git diff | Two files (one auto-gen) | ✅ Recommended |
| C: Keep both hand-authored | Familiar | Drift, dual maintenance, lock-in | ❌ Status quo pain |

**Decision**: Design Spec = source of truth (hand-authored). Blueprint = generated (never hand-edit). Check both into git.

### 5.2 SQL Dialect

Design Spec SQL is DuckDB-specific. If switching databases:
- SQL must be rewritten regardless (not a BI-tool problem)
- Declare `sql_dialect: duckdb` in frontmatter
- Converters can flag dialect-incompatible functions

### 5.3 Widget IDs: Slugs vs Numbers

| Approach | Example | Pros | Cons |
|----------|---------|------|------|
| Sequential `W5` | `#### W5: Net Revenue` | Simple, compact | Renumbering cascade on reorder |
| **Stable slug `W:net-revenue`** | `#### W:net-revenue` | Stable, readable, no cascade | Slightly verbose |

**Decision**: Use slug-based IDs (`W:{kebab-case-slug}`). Matches composition table.

### 5.4 Evidence.dev Alignment

Evidence.dev philosophy (markdown + SQL + declarative components) is strikingly similar to our enhanced Design Spec. Benefits of Evidence converter:
- **Preview**: Designers see live dashboard before Metabase deploy
- **Validation**: SQL syntax errors caught in Evidence dev server
- **Second target**: Zero-effort second deployment option
- **Documentation**: Evidence pages double as living documentation

---

## 6. Migration Strategy

### Phase 1: Build Parser + Metabase Converter (week 1)

1. `design-spec-parser.js` — parse enhanced Design Spec format
2. `convert-to-metabase.js` — generate Metabase blueprint from parsed spec
3. Validate with `sales_daily_operation` — enhanced spec → generated blueprint should match existing

### Phase 2: Migrate Existing Dashboards (gradual)

1. Pick high-value dashboards first (daily ops, weekly review)
2. Add `### Widget Details` sections to existing Design Specs
3. Verify generated blueprints match existing ones
4. Mark manually-authored blueprints as `status: legacy`

### Phase 3: Build Additional Converters (on-demand)

Only build when migration target is concrete — don't over-invest speculatively.

---

## 7. Summary

| Question | Answer |
|----------|--------|
| Does the spec generalize across BI tools? | **Yes** — 18/25 viz types universal; grid tokens convert to any column count; number formatting maps cleanly |
| Where does portability BREAK? | Drill-through, RLS, caching, embedding, tool-specific viz features → handled by `overrides` escape hatch |
| Best data binding approach? | SQL-primary (matches our stack) + optional `model_ref` for model-based tools |
| Widget ID strategy? | Slug-based (`W:{slug}`) for stability across reorders |
| Most likely migration targets? | Superset (SQL-based, OSS) > Evidence (markdown-native) > Grafana (monitoring) |
| Evidence.dev alignment? | Strong — could be built as first additional converter for live preview |
| Effort for full multi-tool? | Metabase: 2-3d; Evidence: 1-2d; Superset: 3-5d; total ~8-10 days for 3 tools |

### Unresolved Questions

1. **SQL dialect portability**: Should we maintain dialect-specific SQL variants per database (DuckDB vs Postgres)? Or rely on dbt's compilation layer?
2. **Capture → Design Spec**: Should `capture_dashboard.js` generate enhanced Design Spec directly instead of blueprint? (Reverse flow)
3. **Partial deploys**: Can conversion support deploying a single widget change without full blueprint regeneration?
4. **Semantic layer integration**: If dbt Semantic Layer is adopted later, should `model_ref` reference dbt metrics? Or keep SQL-primary?
5. **Comparison config portability**: `single-value-with-trend` only works natively in 3/5 tools. Should we define a universal fallback (e.g., two side-by-side scalars)?
