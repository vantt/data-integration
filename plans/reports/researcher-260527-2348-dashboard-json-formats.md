# Dashboard JSON Export Formats: Superset vs Grafana

**Scope:** Exported dashboard JSON structures for SQL-based BI tools; converter-level detail.  
**Sources:** Official docs, GitHub repos, real dashboard examples.  
**Date:** 2026-05-27

---

## Apache Superset Dashboard Export

### Grid Layout: `position_json`

Superset uses a hierarchical flat object structure. Grid width = 12 columns (not standard 24). Each component is identified by a prefixed UUID.

**Position JSON Structure:**
```json
{
  "GRID_ID": {
    "type": "GRID",
    "id": "GRID_ID",
    "children": ["ROW-Abc123", "ROW-Def456"]
  },
  "ROW-Abc123": {
    "type": "ROW",
    "id": "ROW-Abc123",
    "children": ["CHART-Chart1", "CHART-Chart2"],
    "meta": {
      "height": 49
    }
  },
  "CHART-Chart1": {
    "type": "CHART",
    "id": "CHART-Chart1",
    "meta": {
      "chartId": 87,
      "height": 49,
      "width": 3,
      "sliceName": "Chart Title"
    },
    "parents": ["ROOT_ID", "GRID_ID", "ROW-Abc123"]
  }
}
```

**Key points:**
- Grid cols = 12 (total row width)
- Chart width expressed in col units (1-12)
- Height in pixel units
- Every component tracks `parents` list for hierarchy
- Container types: GRID, ROW, CHART, MARKDOWN, TABS, HEADER, COLUMN

### Visualization Types (viz_type Enum)

**Common types:**
- `big_number` — scalar KPI (no trend)
- `big_number_total` — scalar with aggregation
- `echarts_timeseries_line` — time series line chart
- `echarts_timeseries_bar` — time series bar chart
- `echarts_timeseries_area` — area/stacked area
- `echarts_timeseries_scatter` — scatter plot
- `table` — table visualization
- `pie` — pie chart
- `gauge` — gauge visualization
- `funnel` — funnel chart
- `waterfall` — waterfall chart
- `echarts_box_plot` — box plot (statistical)
- `area` — legacy area chart
- `filter_box` — native filter UI component

### Chart Params JSON

For **big_number_total**:
```json
{
  "viz_type": "big_number_total",
  "metric": {
    "label": "Revenue",
    "expressionType": "SIMPLE",
    "sqlExpression": null,
    "column": {
      "id": 12,
      "columnName": "amount"
    },
    "aggregate": "SUM"
  },
  "number_format": "$,.0f",  // D3-style format
  "currency_format": {
    "currencyCode": "USD",
    "symbolPosition": "prefix"
  },
  "subheader": "Total Sales",
  "header_font_size": 0.4,
  "subheader_font_size": 0.15
}
```

For **echarts_timeseries_line**:
```json
{
  "viz_type": "echarts_timeseries_line",
  "datasource": "1__table",
  "granularity": "PT1H",
  "time_range": "Last 30 days",
  "metrics": [
    {
      "label": "Orders",
      "column": {"columnName": "order_count"},
      "aggregate": "SUM"
    }
  ],
  "groupby": ["region"],
  "colorScheme": "supersetColors",
  "logAxis": false,
  "xAxisLabel": "Date",
  "yAxisLabel": "Count",
  "markerEnabled": true,
  "seriesType": "line",
  "stack": false,
  "forecastEnabled": false,
  "annotationLayers": []
}
```

### Filters: `native_filter_configuration`

Stored in `json_metadata` under `native_filter_configuration`:
```json
{
  "native_filter_configuration": [
    {
      "id": "FILTER_nqQh3m",
      "name": "Region",
      "type": "filter_select",
      "configuration": {
        "datasource": {
          "id": 1,
          "type": "table"
        },
        "sqlExpression": null,
        "column": "region",
        "multiple": true,
        "allowClear": true
      },
      "targets": [
        {
          "datasetUUID": "dataset-uuid-1",
          "column": {"name": "region"}
        }
      ]
    }
  ],
  "chartsInScope": [87, 108, 109],  // chart IDs affected
  "expandedScopes": {}
}
```

**Filter types:**
- `filter_select` — multi-select dropdown
- `filter_range` — date/numeric range slider
- `filter_time` — time granularity picker
- `filter_search` — text search

### Data Binding

Dashboard export includes separate `slices` array:
```json
{
  "slices": [
    {
      "slice_id": 87,
      "slice_name": "30D PRs Source",
      "viz_type": "pie",
      "datasource_id": 5,
      "datasource_type": "table",
      "datasource_name": "github_events",
      "query_context": { /* raw SQL */ },
      "params": { /* viz params */ }
    }
  ]
}
```

Charts reference datasource by ID; native filters bind via column name + datasource UUID.

### Tabs

Dashboard tabs represented as separate TAB containers in `position_json`:
```json
{
  "TABS-Container": {
    "type": "TABS",
    "id": "TABS-Container",
    "children": ["TAB-First", "TAB-Second"]
  },
  "TAB-First": {
    "type": "TAB",
    "id": "TAB-First",
    "meta": {"tabLabel": "Overview"},
    "children": ["ROW-Charts"]
  }
}
```

---

## Grafana Dashboard JSON Model

### Grid: `gridPos`

Dashboard width = **24 columns** (fixed). Row height = **30px per unit**.

**Panel with gridPos:**
```json
{
  "panels": [
    {
      "id": 1,
      "type": "stat",
      "title": "Total Revenue",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 6,  // 1-24
        "h": 4   // 30px per unit (4*30=120px)
      },
      "datasource": {
        "type": "postgres",
        "uid": "ds-postgres-prod"
      }
    }
  ]
}
```

**gridPos notes:**
- x: 0-24 (position from left)
- y: row position (auto-gravity corrects upward gaps)
- w, h: dimensions in grid units
- Overlapping panels allowed; gravity reflows layout

### Panel Types

**Core types:**
- `stat` — KPI/metric display (big number equivalent)
- `gauge` — gauge visualization
- `timeseries` — time series (replaces graph)
- `barchart` — bar chart (new unified viz)
- `piechart` — pie chart
- `table` — table
- `text` — markdown/HTML text
- `row` — collapsible section (type="row")
- `status-history` — event timeline

### Panel Config: `fieldConfig` + `options`

**Stat panel (KPI) example:**
```json
{
  "type": "stat",
  "fieldConfig": {
    "defaults": {
      "color": {
        "mode": "thresholds"
      },
      "unit": "currencyUSD",
      "decimals": 0,
      "min": 0,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {
            "color": "green",
            "value": null
          },
          {
            "color": "yellow",
            "value": 50000
          },
          {
            "color": "red",
            "value": 100000
          }
        ]
      },
      "mappings": [
        {
          "type": "value",
          "options": {
            "0": {
              "text": "No Data",
              "color": "gray"
            }
          }
        }
      ]
    },
    "overrides": [
      {
        "matcher": {"id": "byName", "options": "Revenue"},
        "properties": [
          {
            "id": "unit",
            "value": "currencyUSD"
          },
          {
            "id": "color",
            "value": {"mode": "fixed", "fixedColor": "blue"}
          }
        ]
      }
    ]
  },
  "options": {
    "textMode": "auto",
    "colorMode": "value",
    "graphMode": "area",
    "justifyMode": "auto",
    "orientation": "auto"
  }
}
```

**Timeseries panel example:**
```json
{
  "type": "timeseries",
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "custom": {
        "lineWidth": 2,
        "lineInterpolation": "linear",
        "showPoints": "auto",
        "spanNulls": true,
        "fillOpacity": 0,
        "gradientMode": "none",
        "hideFrom": {
          "tooltip": false,
          "viz": false,
          "legend": false
        }
      },
      "color": {
        "mode": "palette-classic"
      }
    },
    "overrides": []
  },
  "options": {
    "tooltip": {
      "mode": "multi",
      "sort": "none"
    },
    "legend": {
      "calcs": ["mean", "lastNotNull"],
      "displayMode": "table",
      "placement": "bottom"
    }
  }
}
```

### Variables/Filters: `templating`

```json
{
  "templating": {
    "list": [
      {
        "name": "region",
        "type": "query",
        "datasource": {
          "type": "postgres",
          "uid": "ds-postgres-prod"
        },
        "query": "SELECT DISTINCT region FROM orders ORDER BY region",
        "refresh": 1,
        "multi": true,
        "includeAll": true,
        "allValue": null,
        "current": {
          "text": ["All"],
          "value": ["$__all"]
        },
        "options": [
          {"text": "All", "value": "$__all", "selected": true},
          {"text": "East", "value": "East", "selected": false},
          {"text": "West", "value": "West", "selected": false}
        ],
        "sort": 1
      },
      {
        "name": "time_range",
        "type": "interval",
        "current": {
          "text": "1h",
          "value": "1h"
        },
        "options": [
          {"text": "5m", "value": "5m"},
          {"text": "1h", "value": "1h"},
          {"text": "1d", "value": "1d"}
        ]
      }
    ]
  }
}
```

**Variable types:**
- `query` — dropdown from SQL/datasource
- `interval` — time interval picker
- `custom` — fixed list of values
- `adhoc` — dynamic filter UI

### Data Source Reference

Panels reference datasources by `uid` (not id):
```json
{
  "datasource": {
    "type": "postgres",
    "uid": "prometheus-prod",
    "name": "Prometheus Production"
  },
  "targets": [
    {
      "refId": "A",
      "expr": "rate(http_requests_total[5m])",
      "legendFormat": "{{method}}"
    }
  ]
}
```

---

## Conversion Considerations

| Aspect | Superset | Grafana | Challenge |
|--------|----------|---------|-----------|
| **Grid cols** | 12 | 24 | Scale x coordinates by 2x |
| **Height units** | Pixels | 30px per unit | 1 Grafana unit ≈ 30px |
| **Container types** | ROW, CHART, MARKDOWN, TABS | panel type field | Map Superset ROW → Grafana row panel |
| **KPI display** | big_number (params) | stat (fieldConfig) | Extract formatting from params → fieldConfig |
| **Filters** | native_filter_configuration | templating → query type | Map filter type + datasource |
| **Data bind** | chartId + datasource_id | uid (string) | Resolve datasource references |
| **Thresholds** | In params (chart-specific) | In fieldConfig.defaults | Standardize threshold structure |
| **Number format** | D3 format strings ($,.0f) | Grafana unit system | Convert D3 → Grafana unit codes |

---

## Unresolved Questions

1. **Superset: conditional formatting beyond thresholds** — How are color rules (e.g., "if value > X and date is recent") expressed in params?
2. **Grafana: panel-specific overrides precedence** — When a field has both default config and override, what's the exact merge order?
3. **Both: SQL query versioning** — Do exports preserve query history or only current state?
4. **Superset: tabs nested layout** — Can tabs contain rows that contain tabs (nested tabs)?
5. **Grafana: variable scope** — Are variables always dashboard-wide or can they be scoped to specific panels?

---

## Sources

- [Apache Superset GitHub Dashboard System](https://deepwiki.com/apache/superset/3.3-dashboard-system)
- [Superset Dashboard Export Structure (GitHub PR)](https://github.com/apache/superset/pull/5543/files)
- [Superset Community Dashboard Example (Preset GitHub)](https://github.com/preset-io/github-actions/blob/master/SupersetCommunityDashboard.json)
- [Grafana Dashboard JSON Model](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)
- [Grafana Dashboard Spec Repository](https://github.com/grafana/dashboard-spec)
- [Grafana Configure Standard Options](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/configure-standard-options/)
- [Grafana Configure Field Overrides](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/configure-overrides/)
- [Superset Native Filters Documentation](https://www.restack.io/docs/superset-knowledge-superset-dashboard-json-metadata)
- [ECharts Form Data Configuration](https://tessl.io/registry/tessl/npm-superset-ui--plugin-chart-echarts/0.20.0/files/docs/form-data.md)
