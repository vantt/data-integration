# 📘 Data Warehouse Blueprint

This document serves as the **Single Source of Truth** for our analytics environment.
It is parsed effectively by the `deploy_from_markdown.js` script to configure Metabase automatically.

## 📝 Syntax Guide

- **Headings**: define structure (`## Collection`, `### Dashboard`, `### Model`, `### 📑 Tab`).
- **Code Blocks**: define executable logic (`sql`, `json metabase-viz`, `json metabase-model`).
- **Text**: provides context and discussion (ignored by the parser).

### Heading Hierarchy

| Heading | Purpose | Example |
|---------|---------|---------|
| `## 📂 Collection:` | Target collection (supports nesting with `>`) | `## 📂 Collection: Operations > Daily Monitoring` |
| `### 🧊 Model:` | Metabase Model (dataset) | `### 🧊 Model: Today's Orders` |
| `### 🖥️ Dashboard:` | Dashboard definition | `### 🖥️ Dashboard: Daily Sales` |
| `### 📑 Tab:` | Dashboard tab (groups questions) | `### 📑 Tab: Overview` |
| `#### ❓ Question:` | Card/question on a dashboard | `#### ❓ Question: Revenue` |
| `#### 📏 Metric:` | Metric on a model | `#### 📏 Metric: Average Build Time` |

### Code Block Types

| Block | Purpose |
|-------|---------|
| `` ```sql `` | SQL query for question/model |
| `` ```json metabase-viz `` | Visualization settings (display type, colors, axes) |
| `` ```json metabase-pos `` | Dashboard position (`row`, `col`, `size_x`, `size_y`) |
| `` ```json metabase-model `` | Model metadata (description, column settings) |

### Tab Support

Tabs organize dashboard cards into separate views. Place `### 📑 Tab:` headers between the `### Dashboard:` header and its `#### Question:` blocks. All questions after a tab header belong to that tab until the next tab header.

**Rules:**
- Tabs are optional — dashboards without tab headers work as a single flat layout
- Every question must be under a tab if tabs are used (questions before any tab header have no tab)
- Tab positions reset per tab — each tab has its own `row`/`col` grid starting at (0,0)
- Tabs and cards are deployed in a single API call to Metabase

---

## 📂 Collection: Engineering Analytics

This collection contains internal metrics for the data engineering team.

### 🧊 Model: Dbt Manifest

Wraps the `dbt_manifest` table to track model build times.

```sql
SELECT * FROM public.dbt_manifest
```

#### 📏 Metric: Average Build Time

Tracks performance regression.

```sql --metric
AVG(build_time_seconds)
```

#### ⚙️ Settings

Metadata for the model columns.

```json metabase-model
{
  "description": "Logs from dbt runs.",
  "columns": {
    "build_time_seconds": {
      "display_name": "Build Time (s)",
      "semantic_type": "type/Quantity"
    },
    "status": { "display_name": "Run Status", "semantic_type": "type/Category" }
  }
}
```

---

### 🖥️ Dashboard: Data Pipeline Health

**Description**: monitors the health of our dbt pipelines.

### 📑 Tab: Overview

#### ❓ Question: Recent Failed Runs

Lists the last 10 failed model runs.

```sql
SELECT model_name, error_message, run_started_at
FROM public.dbt_run_results
WHERE status = 'error'
ORDER BY run_started_at DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_column": "model_name"
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Build Time Trend

Line chart of average build time over the last 30 days.

```sql
SELECT run_date::date, avg(build_time)
FROM public.daily_build_stats
GROUP BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["run_date"],
    "graph.metrics": ["avg"]
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 12,
  "size_x": 6,
  "size_y": 6
}
```

### 📑 Tab: Details

#### ❓ Question: All Runs This Week

Full run history for the current week.

```sql
SELECT model_name, status, build_time_seconds, run_started_at
FROM public.dbt_run_results
WHERE run_started_at >= current_date - INTERVAL '7 days'
ORDER BY run_started_at DESC
```

```json metabase-viz
{
  "display": "table"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```
