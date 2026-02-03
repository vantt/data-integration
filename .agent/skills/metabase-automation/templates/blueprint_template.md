# 📘 Data Warehouse Blueprint

This document serves as the **Single Source of Truth** for our analytics environment.
It is parsed effectively by the `deploy_from_markdown.js` script to configure Metabase automatically.

## 📝 Syntax Guide

- **Headings**: define structure (`## Collection`, `### Dashboard`, `### Model`).
- **Code Blocks**: define executable logic (`sql`, `json metabase-viz`, `json metabase-model`).
- **Text**: provides context and discussion (ignored by the parser).

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
  "size_x": 4,
  "size_y": 4
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
  "x_axis": "run_date",
  "y_axis": "avg"
}
```
