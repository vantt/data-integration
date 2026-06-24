# fact_orders time_key ICT Fix — Agent Report
**Date:** 2026-06-24 | **File changed:** `transformation/models/marts/sales/fact_orders.sql`

---

## 1. Before → After SQL

**Line 150 (before):**
```sql
(extract(hour from created_at) * 100) + extract(minute from created_at) as time_key,
```

**Line 150 (after):**
```sql
(extract(hour from created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') * 100) + extract(minute from created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') as time_key,  -- ICT hour+minute, mirrors date_key TZ conversion
```

Output shape unchanged: INTEGER `HHMM` (e.g. 0830, 2345). Comment added mirroring `date_key`'s ICT note.

---

## 2. Materialization — Full-Refresh Required?

**Materialization: `external` (parquet)**

From `dbt_project.yml`:
```yaml
marts:
  +materialized: external
  +options:
    format: "parquet"
```

`fact_orders` `config()` specifies `options: {format: parquet}` and `location: get_rolling_location()` — no `incremental` override; it inherits `external`.

**External materialization behavior:** dbt writes the entire result set to parquet on every `dbt run`. There is no incremental state. Every `dbt run --select fact_orders` rewrites all rows.

**`--full-refresh` NOT needed** — the `external` adapter always replaces the file on every run. There is no incremental delta to flush. A plain `dbt run --select fact_orders` fixes ALL historical rows.

---

## 3. Downstream Consumer Blast Radius

### 3a. dbt models joining `time_key`

| Model | File | Notes |
|-------|------|-------|
| `dim_time` | `models/marts/core/dim_time.sql:23` | **Source of truth** — defines `time_key` via UTC `time_val` loop. No bug here, it's a pure dimension. |
| `fact_sales` | `models/marts/sales/fact_sales.sql:61` | **Has same UTC bug** — `(extract(hour from o.created_at) * 100) + extract(minute from o.created_at) as time_key`. SEPARATE fix needed. |

> **Note:** `fact_sales` carries the identical UTC-hour bug on its own `time_key` column. It derives its own `time_key` independently (does NOT join `fact_orders`). That model needs the same fix applied to line 61 — out of scope for this task but flagged.

### 3b. CRM / detailView (`crm/`)

`crm/src/adapters/outbound/duckdb/order_sql.py` line 76:
```sql
LEFT JOIN dim_time dt ON fo.time_key = dt.time_key
```
Surfaces `dt.time_of_day_24`, `dt.day_period`, `dt.is_business_hour`, `dt.is_peak_hour` to the CRM order detail view (`order_context_tab.html`). These four `dim_time` attributes will be wrong for ~30% of orders (17:00–23:59 ICT) until `fact_orders` is rebuilt.

### 3c. Metabase blueprints / Rill

No `time_key` or `dim_time` references found in:
- `docs/analytics-handbook/blueprints/` — 0 matches
- `rill/` — 0 matches

The archived doc at `docs/archive/data_pipeline.md:517` references `dim_time` in historical example SQL — not a live consumer.

### 3d. Summary blast radius

| Consumer | Impact | Fix needed after dbt run? |
|----------|--------|--------------------------|
| CRM order detail view (`day_period`, `is_business_hour`, `is_peak_hour`, `time_of_day_24`) | Wrong for ~30% orders until parquet rebuilt | Auto-corrects once `fact_orders` parquet rebuilt + crm serving view reloaded |
| `fact_sales.time_key` | Same UTC bug, independent column | Separate fix required (not done here) |
| Metabase dashboards | No direct `time_key` usage found | No action needed |
| Rill | No `time_key` usage found | No action needed |

---

## 4. dbt Validation Result

### `dbt parse`
```
11:08:19  Running with dbt=1.11.8
11:08:19  Registered adapter: duckdb=1.10.1
11:08:20  Performance info: /app/transformation/target/perf_info.json
```
Exit 0 — no errors.

### `dbt compile --select fact_orders`
```
11:08:25  Running with dbt=1.11.8
11:08:26  Registered adapter: duckdb=1.10.1
11:08:27  Found 121 models, 371 data tests, 9 seeds, 25 sources, 3 exposures, 593 macros
11:08:27  Concurrency: 1 threads (target='dev')
Compiled node 'fact_orders' is: [... full SQL emitted ...]
```

Compiled output confirms the fix at the `time_key` line:
```sql
(extract(hour from created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') * 100) + extract(minute from created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') as time_key,
```
Exit 0 — SQL is valid.

---

## 5. Apply Runbook (for human to execute)

### Prerequisites
- `data_platform` Docker container running
- Metabase stopped or read-only access acceptable during parquet rebuild

### Step 1 — Rebuild fact_orders parquet

```bash
docker exec data_platform dbt run \
  --select fact_orders \
  --project-dir /app/transformation \
  --profiles-dir /app/transformation
```

This rewrites the entire parquet file (all historical rows corrected — no `--full-refresh` needed; external adapter always does a full rewrite).

### Step 2 — Rebuild serving views (DuckDB bootstrap)

Per memory note: after any mart column change, stop Metabase first and run the bootstrap serving views script.

```bash
# Stop Metabase to release DuckDB read lock
docker stop metabase

# Re-run serving view bootstrap
docker exec data_platform python /app/bootstrap_serving_views.py

# Restart Metabase
docker start metabase
```

### Step 3 — Rebuild CRM container (crm/sync baked in image)

Per memory note `[New CRM-consumed mart needs 2 manual deploy steps]`: crm sync logic is baked in image.

```bash
docker compose up -d --build crm
```

### Step 4 — Verify

Spot-check an order created between 17:00–23:59 ICT in CRM detail view. `day_period` should now show "Evening"/"Night" rather than "Afternoon"/"Evening" (UTC+7 shift). `is_business_hour` should be `false` for post-18:00 ICT orders.

### Optional — Fix fact_sales (same bug, separate task)

`fact_sales.sql` line 61 has the identical UTC bug. Apply same fix:
```sql
-- Before:
(extract(hour from o.created_at) * 100) + extract(minute from o.created_at) as time_key,
-- After:
(extract(hour from o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') * 100) + extract(minute from o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') as time_key,  -- ICT hour+minute, mirrors date_key TZ conversion
```
Then run `dbt run --select fact_sales`.

---

## Unresolved Questions

- `fact_sales` same bug — in scope for this agent? (flagged but not fixed per task constraints)
- Does `bootstrap_serving_views.py` path differ between dev/prod container layouts? Verify actual script path before running.
