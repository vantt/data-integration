# Deduplication Strategy

> 2-level deduplication in the src_ extraction layer for memory-efficient processing in DuckDB

## The Problem

With multiple ingestion channels (batch, webhook, history log), the same entity may appear multiple times in raw data. We need to deduplicate to a single "truth" row per entity.

**Challenges:**
1. DuckDB is memory-bound (limited spill-to-disk)
2. Full payload is large (JSON with nested objects, KB-MB per row)
3. Window functions carry all columns in memory during sort
4. 1 dbt model = 1 SQL query = 1 memory budget (CTEs don't materialize to disk)

## The Solution: 2-Level Dedup in src_ (Incremental Extraction)

All deduplication happens in `src_` models (INCREMENTAL tables), which:
1. Read raw parquet with payload
2. **Tech dedup** by `entity_id` (remove duplicate ingestions)
3. Extract JSON fields → payload discarded
4. **Biz dedup** by business key (e.g. `order_id`) on flat data → negligible memory

This produces 1 row per business entity with all fields extracted. Downstream `stg_` and `std_` models work with flat data only — no payload, no dedup.

### Why Both Dedup Levels in src_ (Not Split Across src_/stg_)

- Tech dedup (entity_id): removes same event ingested via multiple channels
- Biz dedup (order_id): keeps latest version when same order has multiple events
- Biz dedup runs on **flat extracted data** (no payload) → negligible additional memory
- If biz dedup were in stg_, unnest models reading src_ would see multiple versions of the same order → **data inconsistency**

### Current Implementation (src_sapo_orders)

```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo']
) }}

-- Step 1: Read raw data (incremental window)
WITH raw_data AS (
    SELECT entity_id, entity_type, event_timestamp, ingest_method, payload
    FROM {{ source('sapo_raw', 'order') }}
    {% if is_incremental() %}
    WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
    {% endif %}
),

-- Step 2: Tech dedup — one row per entity_id (latest event, webhook priority)
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY event_timestamp DESC,
                CASE WHEN ingest_method = 'webhook' THEN 3
                     WHEN ingest_method = 'history_log' THEN 2
                     ELSE 1 END DESC
        ) AS rn
    FROM raw_data
),

-- Step 3: JSON extraction — payload read once, then discarded
extracted AS (
    SELECT
        entity_id, entity_type, event_timestamp, ingest_method,
        json_extract_string(payload, '$.id') as order_id,
        json_extract_string(payload, '$.modified_on') as modified_on,
        -- ... 50+ scalar fields ...
        json_extract_string(payload, '$.order_line_items') as order_line_items_json,
        json_extract_string(payload, '$.payments') as payments_json,
        json_extract_string(payload, '$.fulfillments') as fulfillments_json
    FROM deduped
    WHERE rn = 1
)

-- Step 4: Biz dedup — one row per order_id (flat data, no payload)
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY event_timestamp DESC, modified_on DESC
) = 1
```

**Memory profile:**
- Parquet scan (7-day window, with payload): ~500MB
- ROW_NUMBER tech dedup (sorts rows carrying payload): ~200MB
- JSON extraction (streaming, payload freed after): ~300MB
- ROW_NUMBER biz dedup (flat data only): ~100MB
- **Peak: ~1.1GB** (well under 5GB limit)

---

## Deduplication Logic

### Priority Rules

When multiple records exist for the same entity:

1. **Latest event_timestamp wins** (most recent business event)
2. **Source priority as tie-breaker:**
   - `webhook` (3) - Most authoritative real-time
   - `history_log` (2) - Gap-filling, also reliable
   - `batch_sync` (1) - Scheduled snapshot, lowest priority

### SQL Implementation

```sql
ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY
        -- Rule 1: Latest business event
        event_timestamp DESC,
        -- Rule 2: Source priority (tie-breaker)
        CASE ingest_method
            WHEN 'webhook' THEN 3
            WHEN 'history_log' THEN 2
            WHEN 'batch_sync' THEN 1
            ELSE 0
        END DESC,
        -- Rule 3: Latest processing time (final tie-breaker)
        _dlt_load_id DESC
) = 1
```

### Why This Order?

| Scenario | Resolution |
|----------|------------|
| Same entity, different times | Latest event_timestamp wins |
| Same entity, same timestamp, different sources | Webhook > History > Batch |
| Exact duplicates | Latest load wins |

---

## Model Examples

### stg_sapo_orders (VIEW — enrichment only, no dedup)

```sql
{{ config(materialized='view', tags=['staging', 'orders']) }}

-- All dedup (tech + biz) already done in src_sapo_orders.
-- This model only adds enrichment joins.

WITH orders AS (
    SELECT * FROM {{ ref('src_sapo_orders') }}
),

mapped_tags AS (
    SELECT id, mapping_tag
    FROM {{ ref('ref_order_sources') }}
    WHERE mapping_tag IS NOT NULL
)

SELECT
    o.*,
    coalesce(cast(mt.id as string), cast(o.source_id as string)) as final_source_id,
    pm.name as payment_method_name,
    s.name as source_name,
    l.name as location_name
FROM orders o
LEFT JOIN mapped_tags mt ON o.tags LIKE '%' || mt.mapping_tag || '%'
LEFT JOIN {{ ref('ref_payment_methods') }} pm ON try_cast(o.payment_method_id as BIGINT) = pm.id
LEFT JOIN {{ ref('ref_order_sources') }} s ON coalesce(cast(mt.id as string), cast(o.source_id as string)) = cast(s.id as string)
LEFT JOIN {{ ref('ref_branch_locations') }} l ON try_cast(o.location_id as BIGINT) = l.id
```

---

## Memory Optimization

### Additional Techniques

**1. Partition Pruning**

```sql
-- Filter early to reduce data scanned
WHERE year >= '2025' AND month >= '01'
```

**2. Column Selection**

```sql
-- Only select needed columns from source
SELECT entity_id, event_timestamp, payload->>'status'
-- NOT: SELECT *
```

**3. Incremental Processing**

```sql
{{ config(materialized='incremental') }}

{% if is_incremental() %}
WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
{% endif %}
```

### Memory Settings

```sql
-- In dbt model config or DuckDB connection
{{ config(
    duckdb_config={
        'memory_limit': '4GB',
        'threads': 4
    }
) }}
```

---

## Verification

### Check for Duplicates

```sql
-- Should return 0 rows (src_ already deduped by order_id)
SELECT order_id, COUNT(*) as cnt
FROM {{ ref('src_sapo_orders') }}
GROUP BY order_id
HAVING COUNT(*) > 1;
```

### Check Deduplication Stats

```sql
-- Compare raw vs src_ (both dedup levels applied)
SELECT
    'raw' as layer,
    COUNT(*) as total,
    COUNT(DISTINCT entity_id) as unique_entities
FROM {{ source('sapo_raw', 'order') }}

UNION ALL

SELECT
    'src (deduped)',
    COUNT(*),
    COUNT(DISTINCT order_id)
FROM {{ ref('src_sapo_orders') }};
```

### Check Source Distribution

```sql
-- See which ingest methods won after dedup
SELECT
    ingest_method,
    COUNT(*) as winners
FROM {{ ref('src_sapo_orders') }}
GROUP BY ingest_method;
```

---

## Troubleshooting

### Issue: Out of Memory

**Symptoms:** DuckDB crashes during window function or JSON extraction

**Solutions:**
1. Ensure src_ model is INCREMENTAL with 7-day lookback window (not full scan)
2. Ensure payload is discarded after JSON extraction (not carried to biz dedup step)
3. Reduce memory_limit to force earlier spill-to-disk (e.g. 4-5GB)
4. For full refresh: may need temporarily higher memory_limit
5. See `docs/troubleshooting_duckdb_oom_stg_sapo_orders.md` for detailed history

### Issue: Wrong Record Selected

**Symptoms:** Older/wrong version appearing in staging

**Check:**
1. Verify `event_timestamp` is correct
2. Check `ingest_method` priority
3. Review raw data for anomalies

```sql
-- Debug specific entity
SELECT entity_id, event_timestamp, ingest_method, _dlt_id
FROM src_sapo_orders
WHERE entity_id = '12345'
ORDER BY event_timestamp DESC;
```

---

## Related

- [Models Catalog](./MODELS.md)
- [Testing](./TESTING.md)
- [Data Flow](../../docs/DATA_FLOW.md)
