# Incremental Loading Strategies

> Cursor-based incremental loading and state management

## Overview

The ingestion layer uses cursor-based incremental loading to efficiently sync data without re-fetching everything. Each pipeline maintains its own state tracking the last processed record.

## Cursor Types

### Time-Based Cursor

Used when source provides reliable timestamps.

```python
@dlt.source
def sapo_orders(
    modified_on: dlt.sources.incremental[str] = dlt.sources.incremental(
        cursor_path="modified_on",
        initial_value="2024-01-01T00:00:00Z"
    )
):
    # dlt tracks max(modified_on) across runs
    # Next run starts from that point
```

**Advantages:**
- Simple to implement
- Reliable for immutable timestamps

**Challenges:**
- Late-arriving data may be missed
- Clock skew between systems

### ID-Based Cursor

Used for monotonically increasing IDs.

```python
@dlt.source
def history_log(
    log_id: dlt.sources.incremental[int] = dlt.sources.incremental(
        cursor_path="id",
        initial_value=0
    )
):
    pass
```

### ACK-Based (Webhooks)

Used for message queue patterns.

```python
def process_webhooks():
    messages = buffer.poll(limit=1000)  # Locked

    for msg in messages:
        write_to_parquet(msg)

    buffer.ack_batch([m.id for m in messages])  # Remove from queue
```

---

## Pipeline Cursor Configuration

### Orders Pipeline

| Setting | Value | Rationale |
|---------|-------|-----------|
| Cursor | `modified_on` | Captures updates reliably |
| Initial | 30 days ago | Reasonable backfill window |
| Direction | ASC | Process oldest first |

```python
modified_on: dlt.sources.incremental[str] = dlt.sources.incremental(
    cursor_path="modified_on",
    initial_value=(datetime.now() - timedelta(days=30)).isoformat()
)
```

### Customers Pipeline

| Setting | Value | Rationale |
|---------|-------|-----------|
| Cursor | `created_on` | Updates unreliable via batch |
| Initial | 90 days ago | Longer backfill for new customers |

> **Note:** Customer updates are captured via webhooks and history log, not batch sync.

### History Log Pipeline

| Setting | Value | Rationale |
|---------|-------|-----------|
| Cursor | `occur_at` | Event occurrence time |
| Lookback | 24 hours | Safety buffer for missed events |

```python
occur_at: dlt.sources.incremental[str] = dlt.sources.incremental(
    cursor_path="occur_at",
    initial_value=(datetime.now() - timedelta(hours=24)).isoformat()
)
```

---

## State Management

### State Location

```
ingestion/.dlt/pipelines/{pipeline_name}/
├── state/
│   └── {destination}_state.json
├── trace.json
└── schemas/
```

### View Current State

```python
import dlt

pipeline = dlt.pipeline(pipeline_name='sapo_orders')

# Get incremental state
state = pipeline.state
sources = state.get('sources', {})
sapo_state = sources.get('sapo_orders', {})

print(f"Last modified_on cursor: {sapo_state.get('modified_on')}")
```

### Reset State

```bash
# Full reset - re-sync from initial_value
rm -rf .dlt/pipelines/sapo_orders/

# Partial reset - modify cursor manually
python -c "
import dlt
pipeline = dlt.pipeline(pipeline_name='sapo_orders')
# Use dlt's state management API if available
"
```

### Backup State

```bash
# Before risky operations
cp -r .dlt/pipelines/ .dlt/pipelines.backup/

# Restore if needed
rm -rf .dlt/pipelines/
cp -r .dlt/pipelines.backup/ .dlt/pipelines/
```

---

## Handling Edge Cases

### Late-Arriving Data

Data with timestamps older than the cursor might be missed.

**Solution 1: Lookback Window**

```python
# Subtract buffer from cursor
cursor_with_buffer = cursor_value - timedelta(hours=1)
```

**Solution 2: History Log Gap Filling**

```
Batch Sync (cursor: modified_on)
     │
     │ May miss late-arriving data
     ▼
History Log (runs every 10 min)
     │
     │ Catches missed events
     ▼
Deduplication in Staging
     │
     │ Ensures single truth
     ▼
Clean Data
```

### Duplicate Records

Multiple channels may deliver the same event.

**Solution: Append-Only + Dedup at Transform**

```
webhook (order 123, 10:30)  ──┐
                              ├──► Staging Layer ──► Deduplicated
history_log (order 123, 10:30) ──┘
```

### Out-of-Order Events

Events may arrive out of chronological order.

**Solution: event_timestamp + Source Priority**

```sql
ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY
        event_timestamp DESC,
        CASE ingest_method
            WHEN 'webhook' THEN 3      -- Most reliable
            WHEN 'history_log' THEN 2
            WHEN 'batch_sync' THEN 1   -- Least priority
        END DESC
) = 1
```

---

## Backfill Strategies

### Initial Backfill

```bash
# Backfill last 90 days
python run_orders_batch.py --backfill --days 90

# Specific date range
python run_orders_batch.py --from "2025-01-01" --to "2025-12-31"
```

### Re-Backfill (After Schema Change)

```bash
# 1. Remove existing partition
rm -rf data_lake/sapo_raw/order/ingest_method=batch_sync/year=2025/

# 2. Reset pipeline state
rm -rf .dlt/pipelines/sapo_orders/

# 3. Re-backfill
python run_orders_batch.py --backfill --days 365

# 4. Full refresh transformation
python transformation/scripts/run_dbt.py run --full-refresh
```

### Partial Re-Sync

```bash
# Only re-sync specific month
python run_orders_batch.py \
    --from "2026-01-01T00:00:00Z" \
    --to "2026-01-31T23:59:59Z"
```

---

## Monitoring Incremental Progress

### Check Cursor Progress

```python
import dlt

pipeline = dlt.pipeline(pipeline_name='sapo_orders')
trace = pipeline.last_trace

if trace:
    print(f"Started: {trace.started_at}")
    print(f"Finished: {trace.finished_at}")
    print(f"Records: {trace.last_normalize_info}")
```

### Data Freshness Query

```sql
-- Check latest data by ingest method
SELECT
    ingest_method,
    MAX(event_timestamp) as latest,
    COUNT(*) as total_records
FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
GROUP BY ingest_method
ORDER BY latest DESC;
```

### Gap Detection

```sql
-- Find date gaps in data
WITH dates AS (
    SELECT DISTINCT DATE(event_timestamp) as dt
    FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
),
expected AS (
    SELECT UNNEST(generate_series(
        (SELECT MIN(dt) FROM dates),
        (SELECT MAX(dt) FROM dates),
        INTERVAL 1 DAY
    ))::DATE as dt
)
SELECT e.dt as missing_date
FROM expected e
LEFT JOIN dates d ON e.dt = d.dt
WHERE d.dt IS NULL
ORDER BY e.dt;
```

---

## Best Practices

1. **Always use incremental** unless dataset is tiny
2. **Set reasonable initial_value** - not too far back
3. **Implement lookback buffer** for late-arriving data
4. **Use history log** as safety net for batch sync
5. **Monitor cursor progress** regularly
6. **Backup state** before major operations
7. **Test backfill** in non-prod first

---

## Related

- [Pipelines](./PIPELINES.md)
- [Configuration](./CONFIGURATION.md)
- [Data Flow](../../docs/architecture/data-flow.md)
