# Metabase Visualization Catalog

> **Purpose**: Translation tables bridging Analytics Design (standard vocab) and Metabase implementation.
> Engineer reads this during Phase 7-8 to convert Design Spec tokens into Metabase-specific settings.

---

## 1. Viz Type Translation

| # | Standard Term | Metabase `display` | Settings Notes |
|---|--------------|-------------------|----------------|
| 1 | `single-value` | `scalar` | Default scalar behavior |
| 2 | `single-value-with-trend` | `smartscalar` | + `scalar.comparisons`. UI label: "Trend". **REQUIRES time-series query** (`GROUP BY` date column). Native-SQL widgets returning single-row `(current, comparison)` columns will FAIL with "Group only by a time field" error. For non-time-series widgets, fall back to plain `scalar`. |
| 3 | `progress-toward-goal` | `progress` | + `progress.goal`, `progress.color` |
| 4 | `gauge` | `gauge` | + `gauge.segments` (min/max/color per zone) |
| 5 | `line-chart` | `line` | Single series |
| 6 | `multi-line-chart` | `line` | Multiple series via `graph.dimensions` |
| 7 | `area-chart` | `area` | Default (no stack) |
| 8 | `stacked-area` | `area` | + `stackable.stack_type: "stacked"` |
| 9 | `vertical-bar` | `bar` | Default bar |
| 10 | `horizontal-bar` | `row` | Metabase uses `row` for horizontal bars |
| 11 | `stacked-bar` | `bar` | + `stackable.stack_type: "stacked"` |
| 12 | `grouped-bar` | `bar` | Grouped mode (default when multiple series, no stack) |
| 13 | `stacked-bar-time` | `bar` | + `stackable.stack_type: "stacked"` + time x-axis |
| 14 | `combo-chart` | `combo` | Mixed line+bar via `series_settings` |
| 15 | `donut` | `pie` | Metabase uses `pie` for donut |
| 16 | `funnel` | `funnel` | |
| 17 | `waterfall` | `waterfall` | |
| 18 | `data-table` | `table` | Default table |
| 19 | `data-table-formatted` | `table` | + `table.column_formatting` (conditional) |
| 20 | `pivot-table` | `pivot` | |
| 21 | `scatter-plot` | `scatter` | |
| 22 | `geographic-map` | `map` | |
| 23 | `heatmap` | `pivot` | **Fallback**: pivot + conditional formatting as intensity |
| 24 | `sparkline` | `scalar` | **Fallback**: scalar + trend comparison |
| 25 | `text-annotation` | *(text dashcard)* | Not a card — text content in dashboard |
| — | `view-group` | *(dashboard tab)* | `### 📑 Tab:` in blueprint. Tabs + dashcards in single PUT. |

### Limitations & Fallbacks

| Standard Term | Limitation | Fallback | Document in Blueprint |
|--------------|-----------|----------|----------------------|
| `heatmap` | No native heatmap | `pivot` + conditional formatting gradient | "Design: heatmap → Metabase: pivot + formatting" |
| `sparkline` | No native sparkline | `scalar` + `scalar.comparisons` trend | "Design: sparkline → Metabase: scalar + trend" |

---

## 2. Color Token → Hex Mapping

### Status Colors

| Token | Hex | Metabase Name |
|-------|-----|---------------|
| `positive` | `#84BB4C` | Green |
| `negative` | `#EF8C8C` | Red |
| `warning` | `#F9D45C` | Yellow |
| `neutral` | `#98D9D9` | Teal — metric trung tính |

### Structural Colors

| Token | Hex | Use |
|-------|-----|-----|
| `structural` | `#949AAB` | Muted gray — text annotations, headings |

### Hierarchy Colors

| Token | Hex | Use |
|-------|-----|-----|
| `primary` | `#509EE3` | Metabase blue — brand primary |
| `secondary` | `#88BDE6` | Lighter blue |
| `muted` | `#C2D2E9` | Very light, background |
| `accent` | `#7172AD` | Deep purple — stand-out highlight |

### Series Colors

| Token | Hex | Metabase Palette Slot |
|-------|-----|-----------------------|
| `series-1` | `#509EE3` | Slot 1 |
| `series-2` | `#88BDE6` | Slot 2 |
| `series-3` | `#A989C5` | Slot 3 |
| `series-4` | `#F2A86F` | Slot 4 (orange — avoids overlap with `negative` red) |
| `series-5` | `#F9D45C` | Slot 5 |
| `series-emphasis` | `#509EE3` | Use `primary` hex; pair with `muted` (#C2D2E9) for other series |

### Conditional Colors

| Token | Hex / Config | Use |
|-------|-------------|-----|
| `conditional-above` | `#84BB4C` | Table conditional formatting (above threshold) |
| `conditional-below` | `#EF8C8C` | Table conditional formatting (below threshold) |
| `conditional-range` | `#FFFFFF` → `#509EE3` | Gradient: `table.column_formatting` with `type: "range"` |

### Rules

- Tokens **within the same group** must map to different hex values.
- Cross-group overlap is acceptable (e.g., `series-1` = `primary` is OK — they appear on different elements).
- These are Metabase defaults. Customize per brand palette if needed.

---

## 3. Size Token → Grid Mapping

### Card Width (Metabase grid = 18 columns)

| Token | `size_x` | Notes |
|-------|----------|-------|
| `full-width` | `18` | |
| `two-thirds` | `12` | |
| `half` | `9` | |
| `one-third` | `6` | |
| `one-quarter` | `4` | Use `5` only for 3 cards in 14-col layout (rare) |
| `one-sixth` | `3` | |

### Card Height

| Token | `size_y` | Notes |
|-------|----------|-------|
| `tall` | `9` | Use `10` for funnel/bar with >10 categories |
| `medium` | `6` | Use `5` for charts with <7 data points |
| `short` | `3` | Use `4` for scalar cards needing subtitle |
| `minimal` | `1` | Use `2` for multi-line text annotations |

### Text/Number Size

| Token | Metabase Implementation |
|-------|------------------------|
| `prominent` | Scalar with large card — Metabase auto-sizes text to fill |
| `standard` | Default chart/table text rendering |
| `compact` | Table with `table.cell_height: "compact"` (if available) |
| `caption` | Card description/subtitle field |

### Role-Based Size Defaults (fallback when Design Spec doesn't specify)

| Role | Default `size_x` × `size_y` | Notes |
|------|------------------------------|-------|
| Hero (gauge/progress) | `6 × 5` | 1/3 width, medium height |
| Hero (scalar+trend) | `6 × 4` | 1/3 width, short-medium |
| Supporting KPI | `4 × 3` | 1/4 width; use `3 × 3` if row has 6 cards |
| Trend (line/area) | `12 × 6` | 2/3 width; use `18` if only card in row |
| Breakdown (bar/donut) | `9 × 6` | 1/2 width; use `12` if labels need space |
| Detail (table) | `18 × 8` | Full width; use `10` if >10 visible rows |
| Annotation (text) | `18 × 1` | Full width; use `2` for multi-line text |

**Priority**: Design Spec explicit size tokens > Role-based defaults.

---

## 4. Reverse Disambiguation (Capture → Standard Term)

When capturing a live dashboard back to standard vocabulary, many standard terms share a Metabase `display` value. Use these rules to disambiguate:

| Metabase `display` | Check | Standard Term |
|--------------------|---------|----|
| `bar` | `stackable.stack_type: "stacked"` + time x-axis | `stacked-bar-time` |
| `bar` | `stackable.stack_type: "stacked"` + categorical x-axis | `stacked-bar` |
| `bar` | grouped (multiple series, no stack) | `grouped-bar` |
| `bar` | default (single series, no stack) | `vertical-bar` |
| `area` | `stackable.stack_type: "stacked"` | `stacked-area` |
| `area` | default | `area-chart` |
| `line` | ≥2 series | `multi-line-chart` |
| `line` | 1 series | `line-chart` |
| `smartscalar` | (always has `scalar.comparisons`) | `single-value-with-trend` |
| `scalar` | — | `single-value` |
| `table` | has `table.column_formatting` | `data-table-formatted` |
| `table` | default | `data-table` |
| `pivot` | has conditional formatting (intensity encoding) | `heatmap` |
| `pivot` | default | `pivot-table` |
| `pie` | — | `donut` |
| `progress` | — | `progress-toward-goal` |
| `gauge` | — | `gauge` |
| text dashcard | — | `text-annotation` |
| dashboard tab | — | `view-group` |

**Guardrail**: Reverse-generated design specs MUST have `status: draft-from-capture` in frontmatter and MUST include the standard Design Spec definition block immediately after the `## Design Spec: ...` title.

---

## 5. JSON Templates

### smartscalar + trend (single-value-with-trend) — TIME-SERIES ONLY

> **Prerequisite**: SQL must return a date column + a metric column (e.g. `SELECT day, SUM(revenue) GROUP BY day`). Metabase computes `insights` from the date dimension and uses `previousValue` automatically. The `anotherColumn` pattern below works only when a date column is also present in the result.

```json
{
  "display": "smartscalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "<comparison_column_name>",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "<main_column>": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

**Note**: Native SQL queries do NOT support `periodsAgo`. Calculate previous period in SQL CTE and use `"type": "anotherColumn"`.

### gauge

```json
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 40, "color": "#EF8C8C", "label": "Behind" },
      { "min": 40, "max": 70, "color": "#F9D45C", "label": "On Track" },
      { "min": 70, "max": 100, "color": "#84BB4C", "label": "Ahead" }
    ]
  }
}
```

**Note**: Gauge needs a single value. SQL should return ONE number (e.g., achievement %).

### horizontal-bar (row)

```json
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["<category_column>"],
    "graph.metrics": ["<measure_column>"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5"],
    "graph.x_axis.title_text": "<axis label>",
    "column_settings": {
      "<measure_column>": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

### stacked-bar-time

```json
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["<time_column>", "<category_column>"],
    "graph.metrics": ["<measure_column>"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "<measure label>"
  }
}
```

### progress-toward-goal

```json
{
  "display": "progress",
  "visualization_settings": {
    "progress.goal": 500000000,
    "progress.color": "#84BB4C"
  }
}
```

### table + conditional formatting (data-table-formatted)

```json
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["<column_name>"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["<column_name>"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

---

## 6. Filter Type Mapping

Design Spec filter types → Metabase parameter types:

| Design Spec Filter Type | Metabase Parameter `type` | SQL Template Tag |
|------------------------|--------------------------|------------------|
| `date/range` | `date/all-options` | `{{date_filter}}` (field filter) |
| `category/single-select` | `string/=` | `{{category}}` |
| `category/multi-select` | `string/=` | `{{category}}` (Metabase handles multi) |
| `text/search` | `string/contains` | `{{search_text}}` |
| `number/range` | `number/between` | `{{min_value}}`, `{{max_value}}` |

**SQL syntax**: Use `[[AND {{filter}}]]` for optional clauses — when filter is empty, clause is skipped.

**Parameter mappings**: Each dashcard needs `parameter_mappings` to wire dashboard parameters → card template tags.
