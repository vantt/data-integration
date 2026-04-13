# Source Entities Reference

Complete documentation of all source entities ingested into `sapo_raw` with envelope schema, ingest methods, and payload structures.

## Quick Links

- **[Envelope Schema Overview](./envelope-schema.md)** — Shared outer structure for all raw entities
- **[Core Business Entities](./core-entities.md)** — `order`, `customer`, `product`, `account`
- **[Logistics & Inventory](./logistics-inventory.md)** — `fulfillment`, `purchase_order`, `order_return`, `stock_adjustment`
- **[Reference Data](./reference-data.md)** — `customer_group`, `price_list`
- **[External Sources](./external-sources.md)** — `marketing_spend_raw`, `targets_raw`, `unknown` (catch-all)

## Ingest Methods

| Method | Data Freshness | Use Case |
|--------|-----------------|----------|
| **history_log** | Real-time (30s intervals) | Source of truth for incremental changes |
| **text** (batch) | Daily full sync | Backup/validation for core entities |
| **webhook** | Event-driven (milliseconds) | Live order updates |
| **google_sheet** | Manual or automated | Marketing spend, sales targets |

## Current Data State

| Entity | Rows (Approx) | Ingest Methods | Status |
|--------|---------------|----------------|--------|
| **order** | ~10,000 | history_log, text, webhook | Active |
| **customer** | ~1,000 | history_log, text | Active |
| **product** | ~1,000 | history_log, text | Active |
| **account** | ~50 | history_log, text | Active |
| **fulfillment** | ~3 | history_log | Recently started |
| **unknown** | ~4,600 | webhook | Misrouted orders |
| **marketing_spend_raw** | ~8 | google_sheet | Manual upload |
| **targets_raw** | ~8 | google_sheet | Manual upload |
| **purchase_order** | 0 | history_log | Awaiting events |
| **order_return** | 0 | history_log | Awaiting events |
| **stock_adjustment** | 0 | history_log | Awaiting events |
| **customer_group** | 0 | history_log | Awaiting events |
| **price_list** | 0 | history_log | Awaiting events |

## Key Concepts

### Envelope Schema

All `sapo_raw` entities share a unified **envelope** wrapping entity-specific JSON payloads:

```
entity_id, entity_type, payload (JSON), sync_metadata (JSON),
ingest_method (partition), event_type, event_timestamp (TIMESTAMPTZ),
payload_hash, year (partition), month (partition),
_dlt_load_id, _dlt_id
```

**Critical:** `event_timestamp` is TIMESTAMPTZ (UTC-aware) — never cast to naive TIMESTAMP to preserve timezone info for date-key calculations.

### Denormalization & Snapshots

Order payloads include snapshots of `customer_data`, `account` details, and line items **at order creation time**. These snapshots may not match current customer/account state. For historical accuracy, always use order-embedded snapshots, not joins to current dimensions.

### Related Documentation

- **[Data Dictionary](../data-dictionary.md)** — Staging models, dimensions, facts
- **[Raw Data Sources Reference](../raw-data-sources.md)** — Comprehensive technical reference
- **[Data Flow Diagram](../data-flow.md)** — Entity relationships and pipeline stages
- **[System Architecture](../overview.md)** — Overall system design
