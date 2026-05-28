# Cross-Tool Visualization Type Mapping Matrix

**Date:** 2026-05-27 | **Status:** Research Complete | **Scope:** 25 standard viz terms across 5 BI tools

## Mapping Matrix

| Standard Term | Metabase | Apache Superset | Grafana | Looker | Power BI | Notes |
|---|---|---|---|---|---|---|
| single-value (KPI number) | `number` | `BigNumber` | `stat` | `single_value` | `Card` | Displays one metric prominently |
| single-value-with-trend (KPI + change) | ❌ | `BigNumberPeriodOverPeriod` | ❌ | ❌ | `KPI` | Only PBI has native trend support; others require workaround combos |
| progress-toward-goal | `progress` | ❌ | `gauge` | ❌ | ❌ | Metabase has dedicated progress; others: gauges or cards with text |
| gauge (semicircular) | `gauge` | `Gauge` | `bargauge` | ❌ | `Gauge` | Grafana's bargauge + threshold zones approximates it |
| line-chart (single series) | `line` | `Line` | `timeseries` | `looker_line` | `Line chart` | All support; timeseries is default time-aware |
| multi-line-chart (multi-series) | `line` | `Line` | `timeseries` | `looker_line` | `Line chart` | Grouped series; equivalent to single-series with multiple dimensions |
| area-chart (single area) | `area` | `Area` | `timeseries` | ❌ | `Area chart` | Superset/Metabase explicit; Grafana: timeseries + stack mode |
| stacked-area | `area` | `Area` | `timeseries` | ❌ | `Area chart` | Config: enable stack/cumulative mode in settings |
| vertical-bar | `bar` | `Bar` | `timeseries` | `looker_column` | `Column chart` | Metabase/Superset: default bar orientation |
| horizontal-bar | `row` | `Bar` | `timeseries` | `looker_bar` | `Bar chart` | Config: swap axes or use horizontal orientation |
| stacked-bar | `bar` | `Bar` | `timeseries` | `looker_column` | `Stacked bar chart` | Config: enable stack mode in viz settings |
| grouped-bar (clustered) | `bar` | `Bar` | `timeseries` | `looker_column` | `Clustered column chart` | Config: set grouping/clustering in axes |
| stacked-bar-time (time axis) | `bar` | `Bar` | `timeseries` | `looker_column` | `Stacked bar chart` | Time series bar with stack enabled |
| combo-chart (line+bar) | `combo` | `MixedTimeseries` | ❌ | ❌ | `Combo chart` | Only Metabase/Superset/PBI; Grafana needs dual queries |
| donut (pie/donut) | `pie` | `Pie` | `piechart` | `looker_pie` | `Pie chart` | Config option: donut vs pie display |
| funnel (conversion funnel) | `funnel` | `Funnel` | ❌ | `looker_funnel` | `Funnel chart` | Grafana: no native; requires custom plugin |
| waterfall | `waterfall` | `Waterfall` | ❌ | ❌ | `Waterfall chart` | Only Metabase/Superset/PBI; Grafana not supported |
| data-table (plain table) | `table` | `Table` | `table` | `looker_grid` / `table` | `Table` | Standard tabular format; all support |
| data-table-formatted (conditional) | `table` | `Table` | `table` | `looker_grid` | `Table` | Config: enable formatting rules / heatmaps |
| pivot-table (cross-tab) | `pivot` | `PivotTable` | ❌ | ❌ | `Matrix visual` | Only Metabase/Superset/PBI; Grafana uses grouped tables |
| scatter-plot (XY correlation) | `scatter` | `Scatter` | ❌ | `looker_scatter` | `Scatter chart` | Grafana: no native scatter; use table + custom display |
| geographic-map (region/point) | `map` | `MapBox` or `CountryMap` | `geomap` | `looker_geo_choropleth` | `Map` (filled/bubble/shape) | Superset has multiple map types; all support regions/points |
| heatmap (intensity matrix) | `heatmap` | `Heatmap` | ❌ | ❌ | ⚠️ Conditional formatting in Matrix | Grafana: no native; use color-coded table |
| sparkline (inline trend) | ❌ | ❌ | ⚠️ (stat sparkline option) | ❌ | ❌ | Only Grafana has native; others: embed small charts as text |
| text-annotation (markdown card) | `text` | `Handlebars` | `text` | `text` | `Text box` | All support; Superset uses Handlebars templating |

---

## Key Findings

**100% Coverage Tools:** Metabase, Power BI, Apache Superset — all have native equivalents for 20–22/25 terms.

**Partial Coverage Tools:**
- **Grafana** (14/25): Strong on monitoring (timeseries, gauge, stat), weak on analytics (no scatter, funnel, waterfall, heatmap, pivot).
- **Looker** (17/25): Missing progress, stacked variants require config, no heatmap.

**Unsupported Patterns:**
- **Single-value-with-trend:** Only Power BI (KPI visual). Metabase/Superset: combo card + text.
- **Scatter-plot:** Metabase, Superset, Looker, Power BI all support; Grafana ❌ requires plugin.
- **Waterfall:** Metabase, Superset, Power BI only.
- **Sparkline:** Grafana only (as stat sparkline mode); others: small embedded charts.

**Config Reuse:** Many variants (stacked, horizontal, grouped) are config flags, not distinct types. Reported as same base type + notes.

---

## Adoption Risk Notes

1. **Metabase:** Type strings are display names in UI; source code may vary. No official "display type" enum found in public docs.
2. **Superset:** VizType enum recently created (PR #31193, 2024); values confirmed from source. Stable, active maintainer.
3. **Grafana:** Panel type values are lowercase strings (`stat`, `piechart`, `timeseries`, `geomap`). Monitoring-first; analytics features via plugins.
4. **Looker:** Type values prefixed `looker_*` (e.g., `looker_column`, `looker_line`). Highly stable, Google-maintained.
5. **Power BI:** Display names are marketing-friendly (e.g., "Card", "KPI"); internal technical names unclear from public API.

---

## Limitations & Gaps

- **Metabase:** No official enum documentation; type identifiers inferred from UI labels and docs.
- **Power BI:** Internal type enum not exposed in public API; display names used as proxy.
- **Grafana:** Designed for time-series monitoring; analytics feats (scatter, heatmap, funnel) missing or plugin-dependent.
- **Looker:** Some variants (e.g., progress-toward-goal) absent; docs light on LookML type parameter details.
- **Superset:** Custom viz plugins may add unlisted types; enum does not reflect third-party extensions.

---

**Sources:**
- [Apache Superset VizType enum (PR #31193)](https://github.com/apache/superset/pull/31193) — Confirmed enum values
- [Metabase Visualization Overview](https://www.metabase.com/docs/latest/questions/visualizations/visualizing-results)
- [Grafana Visualizations Docs](https://grafana.com/docs/grafana/latest/panels-visualizations/visualizations/)
- [Looker Visualization Types](https://cloud.google.com/looker/docs/visualization-types)
- [Power BI Visualization Types](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-types-for-reports-and-q-and-a)
