# Envelope Schema

Unified data structure shared by all raw entities in `sapo_raw` Delta Lake tables.

## Overview

Every entity in the raw data lake is wrapped in a consistent **envelope** — the outer structural container that holds metadata, partitioning info, and the actual entity payload.

```
┌─────────────────────────────────────────────────────┐
│  ENVELOPE (Shared by all entities)                  │
├─────────────────────────────────────────────────────┤
│ entity_id (PK)                                      │
│ entity_type                                         │
│ payload (JSON) ← Entity-specific data               │
│ sync_metadata (JSON) ← Audit trail                  │
│ ingest_method (PARTITION)                           │
│ event_type                                          │
│ event_timestamp (TIMESTAMPTZ)                       │
│ payload_hash                                        │
│ year (PARTITION)                                    │
│ month (PARTITION)                                   │
│ _dlt_load_id, _dlt_id (dlt framework)               │
└─────────────────────────────────────────────────────┘
```

## Column Definitions

### Identity & Type

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `entity_id` | VARCHAR | NO | **Natural primary key** — Unique identifier for the entity instance (e.g., order ID = "12345678", customer ID = "9876543"). Combined with `entity_type` for row uniqueness. |
| `entity_type` | VARCHAR | NO | Type of entity (e.g., `order`, `customer`, `fulfillment`, `product`). Maps to the API resource (e.g., `order` → `/admin/orders/{id}.json`). |

### Data Content

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `payload` | JSON | NO | **Full entity snapshot** — Complete data structure from Sapo JSON API or upstream system. See entity-specific reference docs for structure. Includes all nested objects and arrays (e.g., `order_line_items`, `fulfillments`, `payments`). |
| `sync_metadata` | JSON | YES | **Audit trail** — Source system context. Fields: `source` (e.g., "sapo_api"), `sync_timestamp`, `actor` (who triggered the sync), `raw_api_url` (exact API endpoint used). Used to track data lineage and debug ingestion issues. |

### Event Tracking

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `event_type` | VARCHAR | NO | Action type — what happened to the entity: `create` (new entity), `update` (existing entity modified). Enables change detection and historical replay. |
| `event_timestamp` | TIMESTAMPTZ | NO | **CRITICAL: When the event occurred** — Timestamps creation/modification time in the **source system (Sapo)**, NOT the ingest time. Stored as TIMESTAMPTZ (UTC-aware). **Never cast to naive TIMESTAMP.** Used for correct date-key assignment at serving layer (Asia/Ho_Chi_Minh conversions happen in Metabase, not here). |

### Data Quality & Deduplication

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `payload_hash` | VARCHAR | NO | **MD5 hash of payload JSON** — Excludes envelope columns. Used for efficient deduplication and change detection. If two rows have same `entity_id`, `entity_type`, `event_timestamp` but different `payload_hash`, the payload actually changed. |

### Partitioning

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `ingest_method` | VARCHAR | NO | **PARTITION column** — How entity was ingested: `history_log` (incremental change feed), `text` (batch full sync), `webhook` (event-driven), `google_sheet` (manual external data). Critical for separation of concerns and change tracking. Partition enabled queries to isolate sources. |
| `year` | VARCHAR | NO | **PARTITION column** — Extracted from `event_timestamp` (YYYY format, e.g., "2026"). Enables year-level query optimization. |
| `month` | VARCHAR | NO | **PARTITION column** — Extracted from `event_timestamp` (MM format, e.g., "01"). Combined with `year` for monthly partitioning. Typical query filters on `year='2026' AND month='01'`. |

### dlt Framework

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `_dlt_load_id` | VARCHAR | NO | **dlt framework** — Load batch identifier. Tracks which ingestion run created this record. Multiple rows may share the same `_dlt_load_id` if ingested together. Used to track data lineage and identify issues during a specific pipeline run. |
| `_dlt_id` | VARCHAR | NO | **dlt framework** — Unique row identifier assigned by dlt pipeline. Primary key at the row level (distinct from entity `entity_id`). Used by dlt for internal deduplication. |

## Design Principles

### 1. Single Schema for All Entities

All entities (order, customer, fulfillment, product, etc.) use the **same envelope structure**. Differentiation happens via `entity_type` and the `payload` JSON content. This enables:

- **Unified deduplication logic** — Single query to find duplicates across all entity types
- **Consistent audit trail** — Same metadata fields for all entities
- **Flexible extensibility** — New entities added without schema changes (just new `entity_type` values)

### 2. Timezone Awareness is Critical

**`event_timestamp` MUST be TIMESTAMPTZ (not naive TIMESTAMP).**

Why:
- Orders placed at 2:00 AM Asia/Ho_Chi_Minh (UTC+7) = 19:00 UTC previous day
- Naive TIMESTAMP loses this info → wrong date_key assignment for 0h–7h orders
- Metabase does timezone conversion at query time; the raw table must preserve the original zone info

**Example:**
```
Order placed: 2026-01-28 02:30:00 Asia/Ho_Chi_Minh
event_timestamp (stored as TIMESTAMPTZ): 2026-01-27 19:30:00+00:00
date_key at serving layer (Metabase): 20260128 (correct, because we convert to Asia/Ho_Chi_Minh TZ)

If event_timestamp were naive (2026-01-27): date_key = 20260127 (WRONG)
```

### 3. Payload is Entity-Specific; Envelope is Standard

The envelope provides the **where, when, how, and from what**. The `payload` contains the **what**.

```json
{
  "entity_id": "12345678",
  "entity_type": "order",
  "event_timestamp": "2026-01-28T10:30:00+00:00",
  "event_type": "update",
  "ingest_method": "history_log",
  "payload": {
    "id": 12345678,
    "code": "SON000001",
    "status": "finalized",
    "order_line_items": [...],
    "fulfillments": [...],
    ...
  }
}
```

See entity-specific docs for `payload` structure (e.g., [Core Entities](./core-entities.md), [Logistics & Inventory](./logistics-inventory.md)).

### 4. Denormalization for Historical Accuracy

**Order payloads include snapshots:**

- `customer_data` — Full customer state at order creation time
- `account` fields — Sales staff name/email at order time
- `order_line_items` — Line item details with prices and discounts at order time

These snapshots may **not match** the current `customer` or `account` entity if those were updated after the order was placed.

**For analytics:** Use order-embedded snapshots for historical fact tables, not joins to current dimensions. This ensures reports reflect data as it was when the order happened, not as it is today.

## Common Patterns

### Deduplication

**Goal:** Keep the most recent version of each entity.

```sql
SELECT * FROM sapo_raw.order
WHERE ROW_NUMBER() OVER (
    PARTITION BY entity_id, entity_type
    ORDER BY event_timestamp DESC, _dlt_id DESC
) = 1
```

**By `event_timestamp` DESC:** Most recent event first.
**By `_dlt_id` DESC:** Break ties when multiple events happen at same timestamp (keeps last ingested).

### Change Detection

Compare `payload_hash` across `event_timestamp` to identify **actual** field changes:

```sql
WITH orders_with_lag AS (
  SELECT
    entity_id,
    event_timestamp,
    payload_hash,
    LAG(payload_hash) OVER (PARTITION BY entity_id ORDER BY event_timestamp) AS prev_hash
  FROM sapo_raw.order
)
SELECT * FROM orders_with_lag
WHERE payload_hash != COALESCE(prev_hash, '')
-- Only rows where payload actually changed
```

### Partitioned Queries

Always filter on partition columns for performance:

```sql
SELECT COUNT(*) FROM sapo_raw.order
WHERE year = '2026' AND month IN ('01', '02', '03')
  AND ingest_method = 'history_log'
-- Only scans partitions for Q1 2026 history log data
```

## Related Documentation

- **[Core Business Entities](./core-entities.md)** — `order`, `customer`, `product`, `account` payloads
- **[Logistics & Inventory](./logistics-inventory.md)** — `fulfillment`, `purchase_order`, `order_return`, `stock_adjustment` payloads
- **[Reference Data](./reference-data.md)** — `customer_group`, `price_list` payloads
- **[Raw Data Sources Reference](../raw-data-sources.md)** — Complete technical specification
