# Dashboard Definition Formats: Looker, Lightdash, Evidence.dev

**Research Focus:** Syntax precision & semantic layer coupling across three model-based BI tools.

---

## 1. Looker (LookML Dashboards)

### YAML Syntax Structure
```yaml
dashboard: sales_dashboard
  title: "Sales Overview"
  layout: newspaper
  description: "Company-wide metrics"
  
  filters:
    - name: date_filter
      title: "Date Range"
      type: date_filter
      model: sales_model
      explore: orders
      field: orders.order_date
      default_value: "7 days"
  
  elements:
    - name: revenue_tile
      title: "Total Revenue"
      type: single_value
      model: sales_model
      explore: orders
      measures: [orders.total_revenue]
      dimensions: [orders.region]
      listen:
        date_filter: orders.order_date
      filters:
        - field: orders.status
          value: completed
      
    - name: sales_trend
      type: looker_line
      measures: [orders.daily_sales]
      dimensions: [orders.order_date]
      sorts: [{field: orders.order_date, descending: false}]
      limit: 365
```

### Key Characteristics
- **Element Types:** single_value, looker_line, looker_bar, looker_column, looker_scatter, looker_pie, looker_grid, looker_funnel, looker_waterfall, looker_geo_choropleth, looker_boxplot, text, button (18+ total)
- **Grid Layout:** 24-column newspaper grid; explicit positioning via row/col or automatic flow
- **Sizing:** tile_size parameter (pixels), height/width in tile units
- **Semantic Binding:** Tiles reference model → explore → measures/dimensions (never raw SQL)
- **Filters:** Field filters query database for options; bound to tiles via `listen` parameter
- **Formatting:** Conditional formatting via measure properties, number formatting rules
- **Tight Coupling:** Dashboard tightly bound to Looker's data model—can't port to other tools

---

## 2. Lightdash (dbt-Native BI)

### YAML Syntax Structure
```yaml
# dashboard.yml
name: "Revenue Dashboard"
description: "Monthly revenue tracking"
slug: revenue-dashboard
spaceSlug: finance/revenue
verified: true

tiles:
  - x: 0
    y: 0
    h: 4
    w: 12
    type: saved_chart
    properties:
      chartSlug: monthly-revenue
      hideTitle: false
    tileSlug: tile-revenue

  - x: 12
    y: 0
    h: 4
    w: 12
    type: markdown
    properties:
      markdown: "## KPI Summary\nTotal YTD revenue: $2.5M"
    tileSlug: tile-summary

filters:
  dimensions:
    - field: orders.region
      operator: equals
      values: [EMEA, APAC]
  metrics: []

config:
  isDateZoomDisabled: false
  defaultDateZoomGranularity: Month
```

```yaml
# chart.yml (referenced as saved_chart tile)
name: "Monthly Revenue"
slug: monthly-revenue
tableName: fct_orders
spaceSlug: finance/revenue

metricQuery:
  exploreName: orders
  dimensions:
    - orders.order_month
  metrics:
    - revenue
    - order_count
  filters:
    dimensions:
      and:
        - target:
            fieldId: orders.region
          operator: equals
          values: [EMEA]
  sorts:
    - fieldId: orders.order_month
      descending: true
  limit: 24

chartConfig:
  type: cartesian
  config:
    layout:
      xField: order_month
      yField: [revenue, order_count]
    series:
      - yField: revenue
        label: "Revenue ($)"
      - yField: order_count
        label: "Orders"
```

### Key Characteristics
- **Semantic Layer:** Direct dbt model integration; references dbt metrics (not SQL)
- **Grid Layout:** x, y, h, w positioning (similar to grid-layout CSS)
- **Tile Types:** saved_chart, markdown (expandable via plugins)
- **Space Hierarchy:** Slug-based (finance/revenue) with full path required
- **Chart Types:** 9 types (cartesian, line, bar, pie, gauge, funnel, scatter, map, table)
- **Filters:** Applied at dashboard level or per-tile; filter by dimension/metric
- **CLI Workflow:** lightdash download/upload for local editing; lightdash lint validation
- **Portability:** Portable to other dbt-aware tools IF they read the same YAML spec (high coupling to dbt manifest)

---

## 3. Evidence.dev (Markdown-Based BI)

### Markdown Syntax Structure
```markdown
---
title: Sales Dashboard
description: Company sales overview
---

# Sales Overview

## Queries

\`\`\`sql orders_monthly
SELECT 
  DATE_TRUNC(order_date, MONTH) as month,
  SUM(amount) as total_sales,
  COUNT(*) as order_count
FROM orders
WHERE region = '{{ region_filter }}'
GROUP BY 1
ORDER BY 1 DESC
\`\`\`

\`\`\`sql summary_stats
SELECT 
  SUM(amount) as total_revenue,
  COUNT(*) as total_orders,
  AVG(amount) as avg_order_value
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
\`\`\`

## Dashboard Filters

<Dropdown 
  name="region_filter" 
  data={region_options}
  value="US"
  label="Select Region"
/>

## Key Metrics

<BigValue 
  data={summary_stats} 
  value=total_revenue 
  fmt="$,.0f"
  title="Total Revenue (30d)"
  sparkline=month
/>

## Trends

<LineChart 
  data={orders_monthly} 
  x=month 
  y=total_sales
  series=region
  yAxisTitle="Sales ($)"
  title="Monthly Sales Trend"
/>

<BarChart
  data={orders_monthly}
  x=month
  y=[total_sales, order_count]
  type=grouped
  stacked=false
/>

## Data Table

<DataTable 
  data={orders_monthly}
  search=true
  download=true
/>

<Delta
  data={summary_stats}
  value=total_revenue
  comparison=prev_month_revenue
  fmt="percent"
  label="vs. Last Month"
/>
```

### Key Characteristics
- **Page Format:** Markdown file with embedded SQL & Svelte-like components
- **Query Definition:** SQL code fences with DuckDB dialect; queries named inline
- **Component Syntax:** JSX-style tags (`<ComponentName prop=value />`)
- **Component Library:** 30+ components (LineChart, BarChart, BigValue, DataTable, Funnel, Sankey, Heatmap, Calendar, Scatter, Bubble, etc.)
- **Templating:** String interpolation (`{{ variable }}`) for dynamic filters; supports Svelte expressions
- **Input Components:** Dropdown, DateRange, Slider, TextInput, Button, Checkbox
- **No Semantic Layer:** Raw DuckDB SQL; no model abstraction
- **Portability:** High—dashboards are markdown + SQL. Portable to any DuckDB-compatible platform (MotherDuck, other DuckDB clients)

---

## Comparative Analysis

| Dimension | Looker | Lightdash | Evidence |
|-----------|--------|-----------|----------|
| **Format** | YAML (dashboard) | YAML (dashboard + chart) | Markdown + SQL |
| **Semantic Layer** | Looker LookML models | dbt models + metrics | None (raw SQL) |
| **Grid System** | 24-column newspaper | CSS grid (x, y, h, w) | Markdown flow (implicit) |
| **Viz Types** | 18+ built-in types | 9 curated types | 30+ components |
| **Filter Architecture** | Field filters (options from DB) | Dimension/metric filters | String interpolation + inputs |
| **Query Language** | Explore + fields (no SQL visible) | metricQuery (dbt metrics) | DuckDB SQL (raw) |
| **Portability** | LOCKED—LookML model-specific | MEDIUM—dbt-dependent | HIGH—pure SQL + markdown |
| **Tool Lock** | Extreme | High (dbt + Lightdash CLI) | Low (DuckDB-agnostic) |
| **Version Control** | Git-native | Git-native (download/upload) | Git-native (markdown files) |

---

## Semantic Layer Trade-offs

### Looker: Maximum Abstraction, Zero Portability
- **Pro:** Query abstraction eliminates SQL errors; non-technical users can build dashboards
- **Con:** Dashboards unreadable without Looker; migration to other tools impossible
- **Binding:** Tight coupling to LookML data model = vendor lock-in

### Lightdash: dbt-First, Medium Portability
- **Pro:** Metrics defined once in dbt; reused across dashboards; IDE-friendly (YAML)
- **Con:** Lightdash-specific extensions (chartConfig) limit portability; requires Lightdash CLI
- **Binding:** Coupled to dbt manifest; portable IF another tool adopts same YAML spec (unlikely)

### Evidence: Raw SQL, Highest Portability
- **Pro:** Dashboards ARE SQL + markdown = portable to any DuckDB environment; no semantic lock-in
- **Con:** No reusable metrics; SQL expertise required; scaling to 100+ dashboards risks duplication
- **Binding:** Loose—dashboards portable anywhere DuckDB runs; high code duplication risk

---

## Recommendation for Tool-Agnostic Spec

**Portability Ranking:**
1. **Evidence.dev** (portable markdown + DuckDB SQL)
2. **Lightdash** (portable to dbt-aware tools if YAML standardized)
3. **Looker** (zero portability—model-locked)

**For a tool-agnostic format:**
- **Adopt markdown + SQL foundation** (Evidence model) as base
- **Inject semantic layer optionally** (dbt metrics reference via `{{ dbt.metric("revenue") }}`) for power users
- **Standardize component schema** via JSON-Schema (maps to Looker/Lightdash/Evidence component sets)
- **Grid layout:** CSS Grid syntax (x, y, h, w)—common across Lightdash/Evidence
- **Avoid** Looker LookML—too opinionated for portability

**Critical insight:** The semantic layer is where portability dies. Evidence's "raw SQL" model wins on **write-once, run-anywhere**; Lightdash's dbt integration wins on **metric reuse within dbt ecosystem**; Looker wins on **access control** (model-level permissions), not portability.

---

## Unresolved Questions

1. Does Lightdash support custom visualization plugins, or are 9 types fixed?
2. Can Evidence.dev dashboards reference dbt metrics natively (out-of-box)?
3. What's Looker's approach to cross-dashboard reusable components (similar to Evidence markdown reuse)?
4. Does any tool (outside Looker) have production-grade row-level security (RLS) at the semantic layer?

---

**Sources:**
- [Looker Dashboard Parameters](https://docs.cloud.google.com/looker/docs/reference/param-lookml-dashboard)
- [Looker Visualization Types](https://help.looker.com/hc/en-us/articles/4420178498707-type-for-LookML-dashboards-)
- [Lightdash Dashboards as Code](https://docs.lightdash.com/references/dashboards-as-code)
- [Lightdash Metrics Reference](https://docs.lightdash.com/references/metrics)
- [Evidence.dev Components](https://docs.evidence.dev/components/all-components)
- [Evidence.dev Markdown](https://docs.evidence.dev/core-concepts/markdown)
- [Evidence Blog: Dashboards as Code](https://evidence.dev/)
