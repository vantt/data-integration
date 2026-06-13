---
name: Evidence Automation
description: Generate and deploy Evidence.dev dashboard pages from Design Specs or Playbooks. Produces .md pages in evidence/pages/ — no API needed, deploy = docker rebuild.
---

# Evidence Automation Skill

> **Location**: `.skills/evidence-automation/` — Evidence.dev page generator.
> Input: Design Spec (Phase 0-6 output) or Playbook. Output: Evidence `.md` page files in `evidence/pages/`.
> Deploy: `docker compose up -d --build evidence` OR `docker compose exec evidence sh -c "npm run build"` for data-only refresh.

## Architecture

```
Playbook → [evidence-automation] → evidence/pages/<slug>/*.md → docker rebuild → evidence.lan.fwg.vn
```

- No deploy script needed — Evidence pages ARE the executable artifact
- Blueprint analog: `evidence/pages/<slug>/index.md` (Tab 1), `channels.md` (Tab 2), etc.
- Data source: `olap.duckdb` via DuckDB connector at `evidence/sources/datalake/connection.yaml`
- All SQL uses schema-qualified tables: `main_marts.fact_orders`, `main_marts.dim_channels`, etc.

## Project Structure

```
evidence/
├── package.json                        # Evidence CLI (@evidence-dev/evidence)
├── evidence.plugins.yaml               # DuckDB connector plugin
├── sources/
│   └── datalake/
│       └── connection.yaml             # DuckDB → olap.duckdb
└── pages/
    ├── index.md                        # Landing page
    └── <dashboard-slug>/
        ├── index.md                    # Tab 1 (primary view)
        ├── <tab2-slug>.md              # Tab 2
        └── <tab3-slug>.md              # Tab 3
```

## Page Syntax

### SQL Block

```markdown
```sql query_name
SELECT col1, col2 FROM main_marts.fact_orders WHERE ...
```
```

Result available as `{query_name}` — array of row objects.

### Components

| Metabase display | Evidence component | Notes |
|---|---|---|
| `scalar` (single value) | `<BigValue>` | Use `comparison` + `comparisonTitle` for WoW |
| `area` / `line` | `<AreaChart>` / `<LineChart>` | `x=` date col, `y=` metric col |
| `bar` (vertical) | `<BarChart>` | `type="grouped"` for multi-series |
| `bar` (horizontal) = `row` | `<BarChart swapXY=true>` | |
| `bar` (stacked) | `<BarChart type="stacked">` | Use `series=` for category breakdown |
| `table` | `<DataTable>` | `rows=25` for pagination |
| `pie` / `donut` | No native — use `<BarChart type="proportional">` or `<DataTable>` | |
| `gauge` / `progress` | `<BigValue>` + threshold note in markdown | No native gauge |

### BigValue WoW pattern

```markdown
```sql kpi
WITH tw AS (SELECT SUM(net_revenue) AS val FROM main_marts.fact_orders WHERE scope_sales AND is_active_order AND <this_week_window>),
     lw AS (SELECT SUM(net_revenue) AS val FROM main_marts.fact_orders WHERE scope_sales AND is_active_order AND <last_week_window>)
SELECT tw.val AS metric, lw.val AS metric_lw FROM tw, lw
```

<BigValue data={kpi} value="metric" comparison="metric_lw" comparisonTitle="Tuần trước" title="Net Revenue (₫)" fmt="0,0" />
```

- `comparison` takes the **absolute** prior-period value — Evidence calculates % delta automatically
- `upIsGood=false` for metrics where lower is better (cancellations, returns, discount rate)

### Navigation between tabs

```markdown
<a href="/dashboard-slug">Tab 1</a> · <a href="/dashboard-slug/tab2">Tab 2</a>
```

### Inline value in text

```markdown
> <Value data={query} value="column_name" />
```

## SQL Rules

1. **Always schema-qualify**: `main_marts.fact_orders`, `main_marts.dim_channels`, `main_marts.dim_customers`, `main_marts.fact_targets`, `main_marts.fact_order_economics`, `main_marts.fact_order_returns`
2. **Scope filter**: `WHERE scope_sales AND is_active_order` (pre-computed boolean columns in `fact_orders`)
3. **Time windows**:
   - This week (Mon-to-date): `ordered_at >= date_trunc('week', current_date) AND ordered_at < current_date + INTERVAL '1 day'`
   - Last week (Mon–Sun): `ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days' AND ordered_at < date_trunc('week', current_date)`
   - MTD: `ordered_at >= date_trunc('month', current_date) AND ordered_at < current_date`
4. **Timezone**: olap.duckdb session uses `TimeZone = Asia/Ho_Chi_Minh`. Use `AT TIME ZONE 'Asia/Ho_Chi_Minh'` for display formatting only.
5. **Combine WoW KPIs into one query** when multiple scalars share the same time window — reduces build time.

## Format Reference

| Value type | `fmt=` | Example |
|---|---|---|
| VND integer | `"0,0"` | 1,234,567,890 |
| VND compact | N/A (use full) | — |
| Percentage (pre-computed) | `"0.0"` | 25.3 (show "%" in title) |
| Ratio (e.g. Pace Index) | `"0.00"` | 1.05 |
| Count | (omit) | 42 |

## Deploy Commands

```bash
# First deploy (build image + start):
docker compose up -d --build evidence

# Refresh data only (pages unchanged):
docker compose exec evidence sh -c "npm run build"
docker compose restart evidence

# View logs:
docker compose logs -f evidence

# Rebuild after editing pages:
docker compose restart evidence
# (CMD = npm run build && npm run preview — rebuild on every restart)
```

## Limitations vs Metabase

| Feature | Metabase | Evidence |
|---|---|---|
| Cross-filtering | ✅ | ❌ |
| Email alerts | ✅ | ❌ |
| Gauge / progress bar | ✅ | ❌ (use BigValue) |
| PDF export | ❌ (Enterprise) | ✅ Built-in |
| Static shareable URL | ❌ | ✅ |
| Tabs | ✅ Native | Separate pages with nav links |
| Data freshness | Live query | Build-time snapshot |

## Example Blueprint Reference

Existing CEO Weekly Pulse Evidence pages:
- `evidence/pages/ceo-weekly-pulse/index.md` — Tab 1: Revenue & Target
- `evidence/pages/ceo-weekly-pulse/channels.md` — Tab 2: Channel analysis
- `evidence/pages/ceo-weekly-pulse/customers.md` — Tab 3: Customers & Alerts
