# Research Report: BI Tool Dashboard Definition Formats

**Date**: 2026-05-27 | **Duration**: Cross-tool analysis

## Executive Summary

BI tools define dashboards using proprietary serialization formats (XML, YAML, JSON), but convergence exists around 5 core structural concepts: **grid-based layout**, **mark/chart-type taxonomy**, **scoped filtering**, **styling metadata**, and **data source binding**. Vega-Lite + Grafana's layout schema form the most portable foundation for a tool-agnostic spec.

---

## Common Grid/Layout Patterns

**Convergence**: All tools use **rectangular cell-based positioning** with x/y coordinates and width/height dimensions.

| Tool | Grid Model | Storage | Units |
|------|-----------|---------|-------|
| **Tableau** | Dashboard zones with layout memory | XML `<layout>` | pixels |
| **Looker** | 24-column grid (newspaper) or tile-based with dynamic rows | YAML `layout: tile \| newspaper \| static` | tile_size units |
| **Power BI** | Canvas-based visual containers with x/y/z coordinates | JSON Layout.json | normalized coords |
| **Superset** | 2D position grid | JSON `position_json` | grid cells |
| **Metabase** | Grid with row/col + sizeX/sizeY | JSON `col, row, sizeX, sizeY` | grid units |
| **Grafana** | 4 layout types: GridLayout (custom), AutoGridLayout, RowsLayout, TabsLayout | JSON `gridPos: {x, y, w, h}` | grid cells |

**Key insight**: Divergence in **units** (pixels vs normalized vs grid cells) but **identical concept**: x, y, width, height. Vega-Lite + Grafana normalize to grid cells (0-24 or 0-12 range), which is adoption-friendly.

---

## Common Viz Type Taxonomy

**Convergence**: Chart types cluster into **7 families** across all tools.

| Family | Examples | Cardinality |
|--------|----------|------------|
| **Table** | Table, Pivot Table | 2-3 variants |
| **Line/Area** | Line, Area, Stacked Area | 3-5 variants |
| **Bar/Column** | Bar, Column, Waterfall, Histogram | 5-7 variants |
| **Scatter/Bubble** | Scatter, Bubble, Map (spatial) | 2-3 variants |
| **Pie/Donut** | Pie, Donut, Gauge, Funnel | 4-5 variants |
| **Stat/KPI** | Number, Text, Gauge, Scorecard | 3-4 variants |
| **Map/Geo** | Choropleth, Marker Map | 2-3 variants |

**Divergence**: Semantic naming differs (Metabase "scalar" = Looker "single_value" = Power BI "card"). **Vega-Lite mark types** (`bar, line, point, area, text, tick`) + Grafana's panel-plugin system provide bridges.

---

## Common Filter Patterns

**Convergence**: Two-level scoping emerges.

| Scope | Definition |
|-------|-----------|
| **Global Filter** | Applied to all cards/visuals (dashboard-level) |
| **Scoped Filter** | Applied to subset of visuals (native_filter_configuration in Superset, filter roles in Tableau) |

**Storage patterns**:
- **Tableau**: Filter elements group sequentially in XML, mapped to worksheets
- **Looker**: Dashboard parameters YAML, applied via `param_key` references in tiles
- **Power BI**: Layout.json defines filter visuals + target chart IDs
- **Superset**: `native_filter_configuration` + `chartsInScope` array (IDs) + `scope.excluded`
- **Metabase**: Dashboard `parameters` + dashcard-level filter bindings (underdocumented API)
- **Grafana**: Template variables + field override rules per panel

**Pain point**: Filter export/import breaks scoping (Superset issue #19944). **Cross-tool implication**: scoping must be explicit in the spec, with a stable visual ID namespace.

---

## Common Styling Patterns

**Convergence**: CSS-like property model (colors, fonts, number formats, conditional formatting).

| Styling Type | Tools | Storage |
|--------------|-------|---------|
| **Colors/Palette** | All | Hex codes or named palette keys |
| **Fonts** | Tableau, Looker, Power BI | Font family + size + weight |
| **Number Format** | All | Format strings (e.g., `#,##0.00`) |
| **Conditional Formatting** | Power BI, Looker, Superset | Rule arrays: `[{condition, color}]` |
| **Axis Labels/Legends** | All | Show/hide flags + custom text |

**Key insight**: Metabase `visualization_settings` (JSON key-value pairs like `"table.pivot_column"`) and Grafana `fieldConfig` + `options` separate structural config from visual styling. This dual-layer model is mature and reusable.

---

## Open Standard Candidates

### 1. **Vega-Lite / Vega** (STRONGEST)
- **Maturity**: Industry standard for declarative visualization grammar
- **Coverage**: Mark types, data encoding, transforms, legends, scales — NOT dashboard layouts
- **Adoption**: Supported natively in Observable, Altair (Python), used in Superset
- **Gap**: No dashboard/grid-layout spec; primarily single-view or multi-view composition (layer, concat, facet)
- **Fit**: Excellent for defining individual viz specs within a dashboard (Vega-Lite as chart definition layer)

### 2. **Grafana Dashboard JSON Schema** (STRONG)
- **Maturity**: v2 schema released; widely documented
- **Coverage**: GridLayout with x/y/w/h, TabsLayout, AutoGridLayout — layout-focused
- **Adoption**: Grafana as observability standard; JSON schema generation tooling available
- **Strengths**: Panel plugin extensibility, field overrides per panel
- **Gap**: Designed for observability (time-series, logs); weaker on exploratory BI (pivot tables, cross-filters)

### 3. **Apache ECharts Option Format** (MODERATE)
- **Coverage**: Dataset model, axis definitions, series encoding — strong for charting
- **Adoption**: High in China; growing in open-source dashboards (e.g., Superset can emit ECharts)
- **Gap**: No built-in dashboard layout or filter model; chart-focused only
- **Fit**: Good for chart specifications; inadequate for dashboard orchestration

### 4. **dbt Semantic Layer / MetricFlow** (MODERATE for metrics, not layout)
- **Strength**: Centralized metric definitions (YAML-based), enforces consistency across tools
- **Coverage**: Metrics, dimensions, entities, time grains — semantic layer only
- **Gap**: Does NOT define dashboard layout, visualizations, or filters; solves the data contract problem, not the UI problem
- **Fit**: Complementary to layout spec; combine both for full dashboard-as-code

### 5. **OpenMetrics / OpenTelemetry** (LOW for BI dashboards)
- **Focus**: Metric **emission** and **collection** standards (time-series format)
- **Not applicable**: No visualization, layout, or filtering concepts
- **Utility**: Relevant only if dashboards consume Prometheus/OpenMetrics data sources

---

## Gaps & Divergences

| Problem | Impact | Severity |
|---------|--------|----------|
| **No cross-tool viz type mapping** | Gauge in one tool ≠ gauge in another (different ranges, thresholds, styling) | HIGH |
| **Filter scoping unstable in exports** | Importing a dashboard resets all filter targets | HIGH |
| **Styling model tool-specific** | Conditional formatting rules don't port across tools | MEDIUM |
| **Data source binding opaque** | SQL queries, model refs, dataset paths are tool-dependent | HIGH |
| **Layout unit mismatch** | Pixels vs. grid cells vs. normalized coords require conversion | MEDIUM |
| **No standard for parameter/variable propagation** | Looker params ≠ Metabase parameters ≠ Tableau filters structurally | MEDIUM |

---

## Recommendation: Layered Foundation

**Best approach: DO NOT aim for a single tool-agnostic format. Instead, design a THREE-LAYER spec**:

### Layer 1: **Dashboard Shell** (Grafana JSON Schema v2)
- Use Grafana's `gridPos` (x, y, w, h) and `layout` (grid/tabs/rows) concepts
- Standardize on a 24-column, row-based grid (Grafana default)
- Extend with `dashboardMetadata` for tool-specific overrides

### Layer 2: **Visualization Definition** (Vega-Lite for exploratory BI, ECharts for real-time)
- Embed Vega-Lite specs for standard charts (bars, lines, scatter, pie, tables)
- Allow `customVizType: "echarts" | "vega-lite" | "tool-native"` for tool-specific renderers
- Map viz types to enum: `BAR | LINE | SCATTER | PIE | TABLE | STAT | GAUGE | MAP`

### Layer 3: **Semantic Contract** (dbt Semantic Layer / MetricFlow)
- Define metrics, dimensions, and measure bindings once
- Dashboards reference semantic layer by metric ID, not raw SQL
- Enables dashboard portability + metric consistency

### Example Integration:
```yaml
# dashboard.yml (Layer 1 + 2)
title: Sales Dashboard
layout: grid
gridPos: {columns: 24}
dashcards:
  - id: sales_revenue
    title: Monthly Revenue
    gridPos: {x: 0, y: 0, w: 12, h: 8}
    vizType: LINE
    spec:  # Layer 2: Vega-Lite spec OR ECharts option
      $ref: "vega-lite://line-chart-with-tooltip"
    metricBinding:  # Layer 3: Semantic reference
      metric: revenue_total
      dimensions: [month, region]
      filters: [region: NA]
  - id: top_products
    title: Top 10 Products
    gridPos: {x: 12, y: 0, w: 12, h: 8}
    vizType: TABLE
    metricBinding:
      metric: order_count
      dimensions: [product_name]
      orderBy: [order_count DESC]
      limit: 10
```

---

## Unresolved Questions

1. **How to standardize thresholds in gauge/KPI visuals?** (currently per-tool)
2. **Should the spec support embedded SQL, or enforce semantic layer references only?**
3. **How to version individual metrics within a dashboard spec?** (dbt semantic layer versions entire project, not per-metric)
4. **Are row-based layouts (Looker "newspaper") or column-based (Metabase) the better default?**
5. **How to handle inter-card drill-through / cross-filtering** (not covered in any standard)?

---

## Sources
- [Tableau Document Schemas](https://github.com/tableau/tableau-document-schemas)
- [Tableau XML Workbook Structure](https://medium.com/@yaron.lirase/unraveling-tableau-workbook-structure-twbx-twb-bdc3b2a93492)
- [Looker LookML Dashboard Docs](https://docs.cloud.google.com/looker/docs/reference/param-lookml-dashboard)
- [Looker Grid Layout Documentation](https://docs.cloud.google.com/looker/docs/building-lookml-dashboards)
- [Power BI PBIX Layout JSON Analysis](https://medium.com/@gelo.blancada/dissecting-a-power-bi-dashboard-1e5017e69974)
- [Superset Dashboard JSON Structure](https://restack.io/docs/superset-knowledge-superset-dashboard-json-metadata)
- [Superset Filter Scoping Issues](https://github.com/apache/superset/issues/19944)
- [Metabase Dashboard API](https://www.metabase.com/docs/latest/api)
- [Grafana Dashboard JSON Schema v2](https://grafana.com/docs/grafana/latest/as-code/observability-as-code/schema-v2/)
- [Grafana Dashboard Specification](https://github.com/grafana/dashboard-spec)
- [Vega-Lite Specification](https://vega.github.io/vega-lite/docs/spec.html)
- [Apache ECharts Option Format](https://echarts.apache.org/en/option.html)
- [dbt Semantic Layer](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl)
- [dbt Semantic Layer at Scale](https://b-eye.com/blog/dbt-semantic-layer-scale/)
- [OpenMetrics Specification](https://openmetrics.io/)
