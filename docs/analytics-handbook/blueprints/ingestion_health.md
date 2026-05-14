# 📘 Blueprint: Ingestion Health Monitor

**Design Spec**: [ingestion_health.md](../designs/ingestion_health.md)
**Playbook**: [ingestion_health.md](../playbooks/ingestion_health.md)

> **Target Collection:** `Operations > Daily Monitoring`
> **Role:** Data Engineer / Ops
> **Archetype:** Operational Cockpit
> **Database:** `Ingestion Health` (DuckDB — `/app/data_lake/monitoring/ingestion_health.duckdb`)

Monitoring wall for ingestion pipeline: per-source SLA status tiles, recon drift alerts, 30-day volume trends, and failure log. Answers "did data move today, is volume sane, is anything drifting?" in < 10 seconds.

## 📂 Collection: Operations > Daily Monitoring

### 🖥️ Dashboard: Ingestion Health Monitor

**Description**: Pipeline trust wall — SLA status per source, recon drift alerts, 30-day volume trends, and failure triage across 3 tabs.

---

### 📑 Tab: Tổng quan

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Trend 30 ngày: ' ||
  strftime(current_date - 29, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Trạng thái pipeline — tất cả nguồn dữ liệu hôm nay

# Trạng thái pipeline — tất cả nguồn dữ liệu hôm nay

```json metabase-pos
{"row":1, "col":0, "size_x":18, "size_y":1}
```

#### Question: Sapo Orders — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_orders_batch_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_orders_batch_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 28,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 21,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":2, "col":0, "size_x":6, "size_y":3}
```

#### Question: Sapo Customers — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_customers_batch_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_customers_batch_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 28,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 21,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":2, "col":6, "size_x":6, "size_y":3}
```

#### Question: Sapo Products — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_products_batch_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_products_batch_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 28,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 21,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":2, "col":12, "size_x":6, "size_y":3}
```

#### Question: Sapo Accounts — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_accounts_batch_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_accounts_batch_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 28,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 21,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":5, "col":0, "size_x":6, "size_y":3}
```

#### Question: Sapo Webhook — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

Hero card — highest frequency realtime asset (12h SLA).

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_webhook_consumer_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_webhook_consumer_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 12,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 9,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":5, "col":6, "size_x":6, "size_y":3}
```

#### Question: Sapo History Log — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_history_log_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sapo/sapo_history_log_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 12,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 9,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":5, "col":12, "size_x":6, "size_y":3}
```

#### Question: Google Sheets Targets — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sheets/sheets_targets_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sheets/sheets_targets_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 48,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 36,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":8, "col":0, "size_x":6, "size_y":3}
```

#### Question: Google Sheets Marketing Spend — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'sheets/sheets_marketing_spend_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'sheets/sheets_marketing_spend_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 48,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 36,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":8, "col":6, "size_x":6, "size_y":3}
```

#### Question: MISA File Drop — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

SLA = 192h (8 days). Warning at 144h (75%).

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'misa_amis/misa_sales_file_drop_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'misa_amis/misa_sales_file_drop_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 192,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 144,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":8, "col":12, "size_x":6, "size_y":3}
```

#### Question: Shopee File Drop — Trạng thái

**Domain Reference**: [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = 'shopee/shopee_income_file_drop_asset' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = 'shopee/shopee_income_file_drop_asset' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Giờ từ lần chạy OK",
    "table.column_formatting": [
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 48,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Giờ từ lần chạy OK"],
        "type": "single",
        "operator": ">=",
        "value": 36,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":11, "col":0, "size_x":6, "size_y":3}
```

---

#### 📝 Text: Reconciliation drift — chênh lệch nguồn vs đích

# Reconciliation drift — chênh lệch nguồn vs đích

```json metabase-pos
{"row":14, "col":0, "size_x":18, "size_y":1}
```

#### Question: Drift — Sapo Orders

**Domain Reference**: [Recon Drift](../domains/operations.md#4-recon-drift)

```sql
SELECT
    COALESCE(CAST(r.metadata_json->>'source_count' AS BIGINT), 0) AS "Source Count",
    COALESCE(CAST(r.metadata_json->>'dest_count'   AS BIGINT), 0) AS "Dest Count",
    COALESCE(ROUND(CAST(r.metadata_json->>'drift_pct' AS DOUBLE), 3), 999) AS "Drift %"
FROM (
    SELECT metadata_json FROM ingestion_runs
    WHERE asset_key = 'recon/sapo_orders_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
    ORDER BY run_started_at DESC LIMIT 1
) r
UNION ALL SELECT 0, 0, 999 WHERE NOT EXISTS (
    SELECT 1 FROM ingestion_runs
    WHERE asset_key = 'recon/sapo_orders_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
)
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Drift %",
    "table.column_formatting": [
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 1,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":15, "col":0, "size_x":5, "size_y":3}
```

#### Question: Drift — Sapo Customers

**Domain Reference**: [Recon Drift](../domains/operations.md#4-recon-drift)

```sql
SELECT
    COALESCE(CAST(r.metadata_json->>'source_count' AS BIGINT), 0) AS "Source Count",
    COALESCE(CAST(r.metadata_json->>'dest_count'   AS BIGINT), 0) AS "Dest Count",
    COALESCE(ROUND(CAST(r.metadata_json->>'drift_pct' AS DOUBLE), 3), 999) AS "Drift %"
FROM (
    SELECT metadata_json FROM ingestion_runs
    WHERE asset_key = 'recon/sapo_customers_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
    ORDER BY run_started_at DESC LIMIT 1
) r
UNION ALL SELECT 0, 0, 999 WHERE NOT EXISTS (
    SELECT 1 FROM ingestion_runs
    WHERE asset_key = 'recon/sapo_customers_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
)
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Drift %",
    "table.column_formatting": [
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 1,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":15, "col":5, "size_x":4, "size_y":3}
```

#### Question: Drift — MISA

**Domain Reference**: [Recon Drift](../domains/operations.md#4-recon-drift)

```sql
SELECT
    COALESCE(CAST(r.metadata_json->>'source_count' AS BIGINT), 0) AS "Source Count",
    COALESCE(CAST(r.metadata_json->>'dest_count'   AS BIGINT), 0) AS "Dest Count",
    COALESCE(ROUND(CAST(r.metadata_json->>'drift_pct' AS DOUBLE), 3), 999) AS "Drift %"
FROM (
    SELECT metadata_json FROM ingestion_runs
    WHERE asset_key = 'recon/misa_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
    ORDER BY run_started_at DESC LIMIT 1
) r
UNION ALL SELECT 0, 0, 999 WHERE NOT EXISTS (
    SELECT 1 FROM ingestion_runs
    WHERE asset_key = 'recon/misa_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
)
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Drift %",
    "table.column_formatting": [
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 1,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":15, "col":9, "size_x":4, "size_y":3}
```

#### Question: Drift — Shopee

**Domain Reference**: [Recon Drift](../domains/operations.md#4-recon-drift)

```sql
SELECT
    COALESCE(CAST(r.metadata_json->>'source_count' AS BIGINT), 0) AS "Source Count",
    COALESCE(CAST(r.metadata_json->>'dest_count'   AS BIGINT), 0) AS "Dest Count",
    COALESCE(ROUND(CAST(r.metadata_json->>'drift_pct' AS DOUBLE), 3), 999) AS "Drift %"
FROM (
    SELECT metadata_json FROM ingestion_runs
    WHERE asset_key = 'recon/shopee_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
    ORDER BY run_started_at DESC LIMIT 1
) r
UNION ALL SELECT 0, 0, 999 WHERE NOT EXISTS (
    SELECT 1 FROM ingestion_runs
    WHERE asset_key = 'recon/shopee_daily'
      AND status IN ('success', 'partial')
      AND metadata_json IS NOT NULL
)
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Drift %",
    "table.column_formatting": [
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 1,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Drift %"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row":15, "col":13, "size_x":5, "size_y":3}
```

---

#### 📝 Text: Lịch sử chạy theo ngày — phát hiện ngày Dagster scheduler dừng

# Lịch sử chạy theo ngày — phát hiện ngày Dagster scheduler dừng

```json metabase-pos
{"row":18, "col":0, "size_x":18, "size_y":1}
```

#### Question: Run Count per Day (30d)

**Domain Reference**: [Run Success Rate (7d)](../domains/operations.md#5-run-success-rate-7d)

```sql
SELECT
    date_trunc('day', run_started_at) AS "Ngày",
    COUNT(*)                           AS "Tổng runs",
    COUNT(CASE WHEN status IN ('success', 'partial') THEN 1 END) AS "OK",
    COUNT(CASE WHEN status IN ('failed', 'skipped')  THEN 1 END) AS "Lỗi"
FROM ingestion_runs
WHERE run_started_at >= now() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["OK", "Lỗi"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#84BB4C", "#EF8C8C"],
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Số runs"
  }
}
```

```json metabase-pos
{"row":19, "col":0, "size_x":18, "size_y":6}
```

---

### 📑 Tab: Volume & Trend

#### 📝 Text: Volume rows_written theo nguồn — 30 ngày gần nhất

# Volume rows_written theo nguồn — 30 ngày gần nhất

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Sapo Batch — Volume 30d

**Domain Reference**: [Ingestion Volume](../domains/operations.md#2-ingestion-volume)

```sql
SELECT
    date_trunc('day', run_started_at) AS "Ngày",
    SUM(CASE WHEN asset_key = 'sapo/sapo_orders_batch_asset'    THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Orders",
    SUM(CASE WHEN asset_key = 'sapo/sapo_customers_batch_asset' THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Customers",
    SUM(CASE WHEN asset_key = 'sapo/sapo_products_batch_asset'  THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Products",
    SUM(CASE WHEN asset_key = 'sapo/sapo_accounts_batch_asset'  THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Accounts"
FROM ingestion_runs
WHERE asset_key IN (
    'sapo/sapo_orders_batch_asset',
    'sapo/sapo_customers_batch_asset',
    'sapo/sapo_products_batch_asset',
    'sapo/sapo_accounts_batch_asset'
  )
  AND status IN ('success', 'partial')
  AND run_started_at >= now() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["Orders", "Customers", "Products", "Accounts"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#7172AD"],
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Rows Written"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 18, "size_y": 6 }
```

#### Question: Sapo Realtime & Incremental — Volume 30d

**Domain Reference**: [Ingestion Volume](../domains/operations.md#2-ingestion-volume)

```sql
SELECT
    date_trunc('day', run_started_at) AS "Ngày",
    SUM(CASE WHEN asset_key = 'sapo/sapo_webhook_consumer_asset' THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Webhook",
    SUM(CASE WHEN asset_key = 'sapo/sapo_history_log_asset'      THEN COALESCE(rows_written, 0) ELSE 0 END) AS "History Log"
FROM ingestion_runs
WHERE asset_key IN (
    'sapo/sapo_webhook_consumer_asset',
    'sapo/sapo_history_log_asset'
  )
  AND status IN ('success', 'partial')
  AND run_started_at >= now() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["Webhook", "History Log"],
    "graph.colors": ["#84BB4C", "#98D9D9"],
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Rows Written"
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 6 }
```

#### Question: External Sources — Volume 30d

**Domain Reference**: [Ingestion Volume](../domains/operations.md#2-ingestion-volume)

Sheets, MISA, Shopee — irregular cadence file-drop sources.

```sql
SELECT
    date_trunc('day', run_started_at) AS "Ngày",
    SUM(CASE WHEN asset_key = 'sheets/sheets_targets_asset'           THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Sheets Targets",
    SUM(CASE WHEN asset_key = 'sheets/sheets_marketing_spend_asset'   THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Sheets Mktg Spend",
    SUM(CASE WHEN asset_key = 'misa_amis/misa_sales_file_drop_asset'  THEN COALESCE(rows_written, 0) ELSE 0 END) AS "MISA",
    SUM(CASE WHEN asset_key = 'shopee/shopee_income_file_drop_asset'  THEN COALESCE(rows_written, 0) ELSE 0 END) AS "Shopee"
FROM ingestion_runs
WHERE asset_key IN (
    'sheets/sheets_targets_asset',
    'sheets/sheets_marketing_spend_asset',
    'misa_amis/misa_sales_file_drop_asset',
    'shopee/shopee_income_file_drop_asset'
  )
  AND status IN ('success', 'partial')
  AND run_started_at >= now() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Ngày"],
    "graph.metrics": ["Sheets Targets", "Sheets Mktg Spend", "MISA", "Shopee"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#509EE3", "#88BDE6", "#F9D45C", "#EF8C8C"],
    "graph.x_axis.title_text": "Ngày",
    "graph.y_axis.title_text": "Rows Written"
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Tỷ lệ thành công 7 ngày — phát hiện asset liên tục thất bại

# Tỷ lệ thành công 7 ngày — phát hiện asset liên tục thất bại

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Success Rate per Asset (7d)

**Domain Reference**: [Run Success Rate (7d)](../domains/operations.md#5-run-success-rate-7d)

```sql
SELECT
    asset_key                                                        AS "Asset",
    COUNT(*)                                                         AS "Tổng runs",
    COUNT(CASE WHEN status IN ('success', 'partial') THEN 1 END)    AS "OK",
    COUNT(CASE WHEN status IN ('failed', 'skipped')  THEN 1 END)    AS "Lỗi",
    ROUND(
        COUNT(CASE WHEN status IN ('success', 'partial') THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    )                                                                AS "Success %"
FROM ingestion_runs
WHERE run_started_at >= now() - INTERVAL '7 days'
GROUP BY asset_key
ORDER BY "Success %" ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Success %"],
        "type": "single",
        "operator": "<",
        "value": 80,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Success %"],
        "type": "single",
        "operator": "<",
        "value": 95,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 8 }
```

---

### 📑 Tab: Failures & Detail

#### 📝 Text: Runs thất bại và bị bỏ qua — 7 ngày gần nhất

# Runs thất bại và bị bỏ qua — 7 ngày gần nhất

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Runs Failed or Skipped (7d)

**Domain Reference**: [Run Success Rate (7d)](../domains/operations.md#5-run-success-rate-7d)

```sql
SELECT
    run_started_at                                          AS "Bắt đầu",
    asset_key                                               AS "Asset",
    status                                                  AS "Trạng thái",
    ROUND(duration_s, 1)                                   AS "Thời gian (s)",
    COALESCE(rows_fetched, 0)                              AS "Rows Fetched",
    COALESCE(rows_written, 0)                              AS "Rows Written",
    run_id                                                  AS "Run ID"
FROM ingestion_runs
WHERE status IN ('failed', 'skipped')
  AND run_started_at >= now() - INTERVAL '7 days'
ORDER BY run_started_at DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Trạng thái"],
        "type": "single",
        "operator": "=",
        "value": "failed",
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Trạng thái"],
        "type": "single",
        "operator": "=",
        "value": "skipped",
        "color": "#F9D45C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: Log đầy đủ tất cả runs — 200 runs gần nhất

# Log đầy đủ tất cả runs — 200 runs gần nhất

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Full Run Log (200 runs)

**Domain Reference**: [Ingestion Volume](../domains/operations.md#2-ingestion-volume), [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness)

```sql
SELECT
    run_started_at                          AS "Bắt đầu",
    run_ended_at                            AS "Kết thúc",
    asset_key                               AS "Asset",
    status                                  AS "Trạng thái",
    ROUND(duration_s, 1)                   AS "Thời gian (s)",
    COALESCE(rows_fetched, 0)              AS "Rows Fetched",
    COALESCE(rows_written, 0)              AS "Rows Written",
    COALESCE(rows_new, 0)                  AS "Rows New",
    COALESCE(rows_updated, 0)              AS "Rows Updated",
    cursor_before                           AS "Cursor Before",
    cursor_after                            AS "Cursor After",
    run_id                                  AS "Run ID"
FROM ingestion_runs
ORDER BY run_started_at DESC
LIMIT 200
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Trạng thái"],
        "type": "single",
        "operator": "=",
        "value": "failed",
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Trạng thái"],
        "type": "single",
        "operator": "=",
        "value": "skipped",
        "color": "#F9D45C",
        "highlight_row": false
      },
      {
        "columns": ["Trạng thái"],
        "type": "single",
        "operator": "=",
        "value": "success",
        "color": "#84BB4C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Footer

Source: ingestion_health.duckdb · ingestion_runs · Refreshed on each Dagster run · SLA ref: orchestration/config/ingestion_sla.yaml

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```
