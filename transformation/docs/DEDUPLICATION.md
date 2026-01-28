# Deduplication Strategy

> Strict Late Materialization for memory-efficient deduplication in DuckDB

## The Problem

With multiple ingestion channels (batch, webhook, history log), the same entity may appear multiple times in raw data. We need to deduplicate to a single "truth" row per entity.

**Challenges:**
1. DuckDB is memory-bound (no disk spill by default)
2. Full payload is large (JSON with nested objects)
3. Window functions need entire partition in memory

## The Solution: Strict Late Materialization

Instead of applying window functions to full rows, we:

1. **First:** Rank using only key columns (lightweight)
2. **Then:** Filter to winners
3. **Finally:** Join back to get full payload

### Standard Approach (Memory-Heavy)

```sql
-- BAD: Loads full payload into window function
WITH ranked AS (
    SELECT
        *,  -- Full payload loaded
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY event_timestamp DESC
        ) as rn
    FROM source
)
SELECT * FROM ranked WHERE rn = 1
```

**Problem:** DuckDB loads entire `payload` column for all rows into memory for the window function.

### Strict Late Materialization (Memory-Efficient)

```sql
-- GOOD: Only keys in window function
WITH ranked_keys AS (
    SELECT
        entity_id,
        _dlt_id,  -- Unique row identifier
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC,
                CASE ingest_method
                    WHEN 'webhook' THEN 3
                    WHEN 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM {{ source('sapo_raw', 'order') }}
),

winners AS (
    SELECT entity_id, _dlt_id
    FROM ranked_keys
    WHERE rn = 1
)

-- Join back to get full payload
SELECT src.*
FROM {{ source('sapo_raw', 'order') }} src
INNER JOIN winners w
    ON src._dlt_id = w._dlt_id
```

**Benefit:** Window function processes only lightweight columns. Full payload fetched only for winning rows.

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

### stg_sapo_orders

```sql
{{ config(
    materialized='view',
    tags=['staging', 'orders', 'otp']
) }}

WITH source AS (
    SELECT * FROM {{ ref('src_sapo_orders') }}
),

-- Step 1: Lightweight ranking
ranked_keys AS (
    SELECT
        entity_id,
        _dlt_id,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC,
                CASE ingest_method
                    WHEN 'webhook' THEN 3
                    WHEN 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM source
),

-- Step 2: Get winner IDs
winners AS (
    SELECT _dlt_id
    FROM ranked_keys
    WHERE rn = 1
),

-- Step 3: Fetch full data for winners only
deduplicated AS (
    SELECT s.*
    FROM source s
    INNER JOIN winners w ON s._dlt_id = w._dlt_id
)

-- Step 4: Extract and transform
SELECT
    CAST(entity_id AS VARCHAR) AS order_id,
    payload->>'code' AS order_code,
    payload->>'status' AS status,
    payload->>'payment_status' AS payment_status,
    payload->>'fulfillment_status' AS fulfillment_status,
    CAST(payload->>'total' AS DECIMAL(15, 2)) AS total,
    CAST(payload->>'total_discount' AS DECIMAL(15, 2)) AS total_discount,
    CAST(payload->>'total' AS DECIMAL(15, 2))
        - CAST(payload->>'total_discount' AS DECIMAL(15, 2)) AS net_total,
    payload->>'customer_id' AS customer_id,
    payload->>'location_id' AS location_id,
    CAST(payload->>'created_on' AS TIMESTAMP) AS created_at,
    CAST(payload->>'modified_on' AS TIMESTAMP) AS modified_at,
    event_timestamp,
    ingest_method
FROM deduplicated
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
-- Should return 0 rows
SELECT entity_id, COUNT(*) as cnt
FROM {{ ref('stg_sapo_orders') }}
GROUP BY entity_id
HAVING COUNT(*) > 1;
```

### Check Deduplication Stats

```sql
-- Compare raw vs deduplicated counts
SELECT
    'raw' as layer,
    COUNT(*) as total,
    COUNT(DISTINCT entity_id) as unique_entities
FROM {{ ref('src_sapo_orders') }}

UNION ALL

SELECT
    'staged',
    COUNT(*),
    COUNT(DISTINCT order_id)
FROM {{ ref('stg_sapo_orders') }};
```

### Check Source Distribution

```sql
-- See which sources won
SELECT
    ingest_method,
    COUNT(*) as winners
FROM {{ ref('stg_sapo_orders') }}
GROUP BY ingest_method;
```

---

## Troubleshooting

### Issue: Out of Memory

**Symptoms:** DuckDB crashes during window function

**Solutions:**
1. Verify Strict Late Materialization is used
2. Reduce memory limit: `memory_limit: '2GB'`
3. Process in batches by time partition

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
