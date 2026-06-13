---
name: Evidence Automation
description: Generate and deploy Evidence.dev dashboard pages from Design Specs or Playbooks. Produces .md pages in evidence/pages/ — no API needed, deploy = docker restart.
---

# Evidence Automation Skill

> **Location**: `.skills/evidence-automation/` — Evidence.dev page generator.
> Input: Design Spec (Phase 0-6 output) or Playbook. Output: Evidence `.md` page files in `evidence/pages/`.
> Deploy: `docker compose restart evidence` (CMD = cp → sources → build → preview on every restart).

## Architecture — CRITICAL

Evidence has **two separate DuckDB contexts**. Confusing them causes silent query failures:

```
olap.duckdb (container mount at /app/var/data_lake/serving/)
  │
  └── cp → /app/sources/datalake/olap-serving.duckdb      [CMD step 1]
              │
              └── npm run sources                          [CMD step 2]
                    ↓
                  Node.js @duckdb/node-api connector
                  runs each .sql file in sources/datalake/
                  writes results as parquet → static/data/main_marts/
                    │
                    └── npm run build                      [CMD step 3]
                          ↓
                        WASM DuckDB (@duckdb/duckdb-wasm)
                        loads parquets → creates views main_marts.*
                        prerenders all page SQL inline queries
                          │
                          └── npm run preview              [CMD step 4]
                                serves static build on port 3000
```

**Key constraint:** Page inline SQL (`\`\`\`sql block\`\`\``) runs against WASM DuckDB, which only knows tables from precomputed parquets — NOT from `olap-serving.duckdb` directly.

### Source name = WASM schema

The `name:` field in `connection.yaml` becomes the schema in WASM DuckDB.
Current config: `name: main_marts` → WASM creates `main_marts` schema → `FROM main_marts.fact_orders` resolves.

### SQL source files → mart tables

Each mart table used in page SQL **must** have a `.sql` file in `sources/datalake/`:

```
sources/datalake/
├── connection.yaml          ← name: main_marts, filename: olap-serving.duckdb
├── fact_orders.sql          → main_marts.fact_orders in WASM DuckDB
├── dim_customers.sql        → main_marts.dim_customers
├── dim_channels.sql         → main_marts.dim_channels
├── fact_targets.sql         → main_marts.fact_targets
├── fact_order_economics.sql → main_marts.fact_order_economics
└── fact_order_returns.sql   → main_marts.fact_order_returns
```

SQL file format — select only columns needed by pages (keeps parquet lean):
```sql
SELECT order_id, ordered_at, net_revenue, scope_sales, is_active_order, ...
FROM main_marts.fact_orders
```

**When adding a new mart table to a page**: create the `.sql` file first, then restart.

## Project Structure

```
evidence/
├── package.json
├── evidence.config.yaml
├── sources/
│   └── datalake/
│       ├── connection.yaml        # name: main_marts, filename: olap-serving.duckdb
│       ├── fact_orders.sql
│       ├── dim_customers.sql
│       └── ...                    # one .sql per mart table
└── pages/
    ├── index.md
    └── <dashboard-slug>/
        ├── index.md               # Tab 1
        ├── <tab2>.md              # Tab 2
        └── <tab3>.md              # Tab 3
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

| Display type | Evidence component | Notes |
|---|---|---|
| Single value | `<BigValue>` | Use `comparison` + `comparisonTitle` for WoW |
| Area / line chart | `<AreaChart>` / `<LineChart>` | `x=` date col, `y=` metric col |
| Bar chart (vertical) | `<BarChart>` | `type="grouped"` for multi-series |
| Bar chart (horizontal) | `<BarChart swapXY=true>` | |
| Bar chart (stacked) | `<BarChart type="stacked">` | Use `series=` for category column |
| Table | `<DataTable>` | `rows=25` for pagination |

### BigValue WoW pattern

```markdown
```sql kpi
WITH tw AS (SELECT SUM(net_revenue) AS val FROM main_marts.fact_orders
            WHERE scope_sales AND is_active_order AND <this_week_window>),
     lw AS (SELECT SUM(net_revenue) AS val FROM main_marts.fact_orders
            WHERE scope_sales AND is_active_order AND <last_week_window>)
SELECT tw.val AS metric, lw.val AS metric_lw FROM tw, lw
```

<BigValue data={kpi} value="metric" comparison="metric_lw" comparisonTitle="Tuần trước" title="Net Revenue (₫)" fmt="#,##0" />
```

- `comparison` = prior-period **absolute** value — Evidence calculates % delta automatically
- `upIsGood=false` for metrics where lower is better (cancellations, returns, discount rate)

### Inline value in text

```markdown
> <Value data={query} column="column_name" />
```

**Note:** `column=` NOT `value=` — using `value=` throws a prop warning and the value is ignored.

### Navigation between tabs

```markdown
<a href="/dashboard-slug">Tab 1</a> · <a href="/dashboard-slug/tab2">Tab 2</a>
```

## SQL Rules

1. **Always schema-qualify**: `main_marts.fact_orders`, `main_marts.dim_channels`, etc.
2. **Scope filter**: `WHERE scope_sales AND is_active_order` for active sales orders
3. **Time windows** (olap.duckdb TimeZone = Asia/Ho_Chi_Minh, timestamps are ICT):
   - This week (Mon-to-date): `ordered_at >= date_trunc('week', current_date) AND ordered_at < current_date + INTERVAL '1 day'`
   - Last week (Mon–Sun): `ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days' AND ordered_at < date_trunc('week', current_date)`
   - MTD: `ordered_at >= date_trunc('month', current_date) AND ordered_at < current_date`
4. **Display formatting**: `strftime(ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%d/%m %H:%M')`
5. **Combine WoW KPIs** into one query when multiple scalars share the same time window — reduces build time.

## Format Strings — SSF (Excel-style, NOT numeral.js)

Evidence uses the `ssf` package (SpreadSheet Formatter). Use Excel format strings, NOT numeral.js.

| Value type | `fmt=` | Renders as |
|---|---|---|
| VND integer | `"#,##0"` | 1,234,567,890 |
| Percentage (pre-computed) | `"0.0"` | 25.3 (put "%" in title) |
| Ratio / index | `"0.00"` | 1.05 |
| Count | (omit fmt) | 42 |

**Common mistake:** `fmt="0,0"` is numeral.js syntax → Evidence throws `unsupported format` error.

## Deploy Commands

```bash
# First deploy (build image):
docker compose up -d --build evidence

# After editing pages or SQL source files (triggers full rebuild):
docker compose restart evidence

# View logs:
docker compose logs -f evidence

# Check sources manifest (verify parquets were generated):
docker exec evidence cat /app/.evidence/template/static/data/manifest.json
```

**Build time estimate:** ~2-3 min (sources step: ~15s per mart table, build: ~60-90s).

## Adding a New Dashboard

1. Identify which mart tables are needed
2. Check `sources/datalake/` — add `.sql` files for any missing tables
3. Create `evidence/pages/<dashboard-slug>/index.md` (and additional tab pages)
4. `docker compose restart evidence`

## Existing Dashboards

- `evidence/pages/ceo-weekly-pulse/index.md` — Revenue & Target
- `evidence/pages/ceo-weekly-pulse/channels.md` — Channel analysis
- `evidence/pages/ceo-weekly-pulse/customers.md` — Customers & Alerts

## Limitations vs Metabase

| Feature | Metabase | Evidence |
|---|---|---|
| Cross-filtering | ✅ | ❌ |
| Email alerts | ✅ | ❌ |
| Gauge / progress bar | ✅ | ❌ (use BigValue) |
| Static shareable URL | ❌ | ✅ |
| Tabs | ✅ Native | Separate pages with nav links |
| Data freshness | Live query | Build-time snapshot (refresh = restart) |
| Offline / no auth | ❌ | ✅ |
