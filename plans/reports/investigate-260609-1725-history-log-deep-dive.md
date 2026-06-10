# Sapo history_log Pipeline — Deep Dive Investigation
*Date: 2026-06-09*

---

## 1. Raw Sapo Log Item Structure

Fields from `/admin/settings/get_logs` API (source: code analysis of `history_log.py`):

| Field | Used in code | Persisted where |
|-------|-------------|-----------------|
| `id` | `item.get("id")` → `original_event_id` | sync_metadata |
| `occurAt` | incremental cursor, `event_timestamp` | envelope top-level |
| `rootId` | entity fetch, `entity_id` | envelope top-level |
| `rootType` | entity dispatch / registry lookup | envelope `entity_type` |
| `actionName` | `event_type` | envelope top-level |
| `actorName` | persisted | sync_metadata.actor_name |
| `description` | persisted (raw HTML) | sync_metadata.description |
| `uri` | parent entity resolution (`customer_address`) | NOT persisted |

Fields mentioned in registry comments but NOT in envelope:
- `uri` — only used transiently to resolve parent entity ID; not saved

---

## 2. Ingestion Code Analysis

### history_log() function flow

1. **Auth**: Uses `get_sapo_client()` — cookie-based session (same as orders batch pipeline)
2. **Pagination**: GET `/admin/settings/get_logs?page=N&limit=page_size` — API returns newest-first (DESC)
3. **Incremental state**: `dlt.sources.incremental("sync_metadata.event_timestamp")` — tracks `last_value` as ISO 8601 string; string comparison is safe for ISO 8601
4. **Early stop**: stops when `consecutive_old_items >= min_overlap_items` (default 50) — safety buffer to handle out-of-order events
5. **Entity fetch**: for each new log item → calls `/admin/{api_resource}/{root_id}.json` to get **current snapshot** of the entity
6. **Unwrap**: API returns `{"order": {...}}` — single-key wrapper is unwrapped before storing
7. **Routing**: `dlt.mark.with_table_name(env, table_name)` — routes to per-entity-type tables in `sapo_raw` dataset

### Envelope Schema Fields

```
entity_id         TEXT (PARTITION primary_key)
entity_type       TEXT
ingest_method     TEXT = "history_log" (PARTITION)
event_type        TEXT  ← actionName from log
event_timestamp   TIMESTAMP ← occurAt from log
payload_hash      TEXT  ← MD5 of sorted JSON
year              TEXT (PARTITION)
month             TEXT (PARTITION)
payload           JSON  ← full entity snapshot at time of event
sync_metadata     JSON  ← 7 fields (see section 3)
```

### URI-based Parent Resolution

`customer_address` log items have `rootId = address_id` but the API has no standalone address endpoint. Resolution:
- `log.uri` = `/admin/customers/{customer_id}/addresses.json`
- Code strips `/addresses.json` → becomes `/admin/customers/{customer_id}.json`
- Fetches parent customer; stores as `entity_type = "customer"`
- `entity_id` = parent customer's `id` (not the address id)

### actionName (event_type) Filtering

**No filtering** in code — all actionNames are processed. Only ENTITY_REGISTRY controls which entity types are skipped (via `"resolve": "skip"`). For orders, all events pass through.

---

## 3. sync_metadata — Current vs Proposed

| Field | Currently persisted? | Importance | Notes |
|-------|---------------------|------------|-------|
| `source_system` | YES | low | always "sapo" |
| `source` | YES | low | always "history_log" |
| `event_timestamp` | YES | high | duplicate of top-level field |
| `processing_timestamp` | YES | medium | UTC naive string (missing TZ) |
| `original_event_id` | YES | high | Sapo log `id` — useful for dedup/audit |
| `actor_name` | YES | medium | human name, not ID — can change |
| `description` | YES | low | raw HTML, only 2 distinct values (`Cập nhật đơn hàng`, `Thêm mới đơn hàng`) |
| `uri` | NO | medium | could help reconstruct original log context |
| `root_type` | NO | medium | log's `rootType` before normalization |
| `root_id` | NO | medium | original `rootId` (before parent resolution) |
| `actor_id` | NO | high | if available from API — stable vs actor_name |
| `page_num` | NO | low | debug only |

**Key gap**: `processing_timestamp` is stored without TZ as UTC-naive ISO string (`2026-04-12T21:18:06.053930`). Should be `{ts}Z` or `{ts}+00:00` for clarity.

---

## 4. Payload Top-Level Structure

Full key list from actual parquet data (Query 2):

**IDs & codes**: `id`, `tenant_id`, `location_id`, `code`, `contact_id`, `account_id`, `assignee_id`, `customer_id`, `source_id`, `price_list_id`, `process_status_id`, `reason_cancel_id`, `expected_payment_method_id`, `expected_delivery_provider_id`, `from_order_return_id`

**Timestamps**: `created_on`, `modified_on`, `issued_on`, `ship_on`, `ship_on_min`, `ship_on_max`, `finalized_on`, `finished_on`, `completed_on`, `cancelled_on`

**Status flags**: `status`, `payment_status`, `fulfillment_status`, `packed_status`, `received_status`, `print_status`, `return_status`, `interconnection_status`, `einvoice_status`

**Financials**: `total`, `total_discount`, `total_tax`, `delivery_fee`, `order_discount_rate`, `order_discount_value`, `order_discount_amount`, `discount_reason`, `total_order_exchange_amount`, `allow_no_refund_order_exchange_amount`

**Nested objects**: `customer_data`, `billing_address`, `shipping_address`, `assignee`

**Nested arrays**: `order_line_items`, `fulfillments`, `payments`, `discount_items`, `prepayments`, `order_returns`, `promotion_redemptions`

**Other**: `note`, `tags`, `channel`, `tax_treatment`, `business_version`, `create_invoice`, `reference_number`, `reference_url`, `email`, `phone_number`, `order_coupon_code`, `order_return_exchange`

**Note**: `financial_status` in `src_sapo_orders_v2.sql` maps to `payload.payment_status` (not `financial_status` — that field does not exist in Sapo payload).

---

## 5. description Distinct Values

Only **2 distinct values** exist in the entire dataset (3,006 + 1,051 events):

| Count | Stripped text | Semantic group | event_type |
|-------|--------------|----------------|------------|
| 3,006 | Cập nhật đơn hàng | Order updated | update |
| 1,051 | Thêm mới đơn hàng | New order added | add |

The `description` field is generic — it does NOT capture sub-operations like "cancelled", "shipped", "payment received". Operation semantics must be inferred from payload status fields.

---

## 6. Coverage Analysis (Jan–Jun 2026)

| Month | history_log distinct orders | fact_orders total | Coverage % | history_log events |
|-------|-----------------------------|-------------------|------------|-------------------|
| 2026-01 | 175 | 170 | ~103%* | 662 |
| 2026-02 | 117 | 115 | ~102%* | 493 |
| 2026-03 | 205 | 196 | ~105%* | 853 |
| 2026-04 | 148 | 148 | 100% | 765 |
| 2026-05 | 186 | 178 | ~104%* | 877 |
| 2026-06 | 89 | 83 | ~107%* | 407 |

*>100% means history_log has events for orders whose `ordered_at` falls in an adjacent month (partition by `event_timestamp` not `created_on`). fact_orders counts by `ordered_at` (ICT), history_log partitions by `occurAt` (UTC). Cross-month boundary orders cause apparent overcounting.

**Key finding**: history_log covers almost the same orders as fact_orders for the overlapping period — the pipeline is working. history_log started in Dec 2025 (6 events over 2 orders — initial test run).

---

## 7. Payload Status Fields Analysis

| status | payment_status | fulfillment_status | count |
|--------|---------------|-------------------|-------|
| completed | (null) | shipped | 1,842 |
| finalized | (null) | shipped | 1,042 |
| cancelled | (null) | unshipped | 502 |
| finalized | (null) | unshipped | 497 |
| draft | (null) | unshipped | 174 |

**Note**: `financial_status` query returned null for all rows — Sapo uses `payment_status` not `financial_status` at the payload top level. The `src_sapo_orders_v2.sql` model reads `$.payment_status` as `financial_status` — that is correct.

Status semantics:
- `completed` + `shipped` = delivered, revenue recognized
- `finalized` + `shipped` = in-transit / handed to carrier
- `finalized` + `unshipped` = order confirmed, not yet shipped
- `cancelled` + `unshipped` = cancelled before fulfillment
- `draft` + `unshipped` = pending confirmation

---

## 8. Reconstruction Capability Assessment

### From payload alone (current design):

| Operation | Can reconstruct? | How |
|-----------|-----------------|-----|
| Order created | Partial — check `created_on ≈ event_timestamp` | Not reliable; "add" event_type from log captures first-seen |
| Order cancelled | YES | `status = 'cancelled'` + `cancelled_on IS NOT NULL` |
| Order completed | YES | `status = 'completed'` + `completed_on IS NOT NULL` |
| Order finalized | YES | `status = 'finalized'` + `finalized_on IS NOT NULL` |
| Item shipped | YES | `fulfillment_status = 'shipped'` + fulfillments[].shipped_on |
| Payment received | Partial | `payment_status = 'paid'` but exact payment timestamp needs `payments[]` array |
| Staff who acted | YES | `sync_metadata.actor_name` (name, not ID) |
| Prior state (before change) | NO | snapshot-only model; no diff/delta stored |

### Critical gap — snapshot not delta:

Each history_log event stores the entity's **current state** at the time Sapo triggered the log, NOT what changed. To know "what changed", you must compare consecutive snapshots for the same `entity_id`. This is feasible in dbt but not implemented.

### Event count distribution:
- 91 orders have only 1 event (first-capture only)
- Most orders: 2–10 events
- Some high-activity orders: up to 31 events

---

## 9. Recommendations

### Fields to add to sync_metadata

1. **`root_type`** — the raw `rootType` from log (before lowercasing/normalization). Cost: near zero. Benefit: audit trail for entity resolution bugs.
2. **`root_id`** — raw `rootId` from log (before parent resolution). Same cost/benefit as above.
3. **`action_name`** — same as `event_type` but stored in sync_metadata for completeness (currently only top-level). Low cost.
4. Fix **`processing_timestamp`** — append `Z` suffix: `datetime.utcnow().isoformat() + "Z"`. Zero cost.

### Fields NOT worth adding

- `page_num` — ephemeral, not meaningful post-ingest
- `uri` — derivable from entity_type + entity_id
- `actor_id` — not available in the log API (only `actorName`)

### Cost/benefit of enriching ingestion

| Enhancement | Effort | Benefit |
|-------------|--------|---------|
| Fix processing_timestamp TZ suffix | Trivial | Correctness |
| Add root_type/root_id to sync_metadata | 2 lines | Audit trail |
| Store `uri` field | 2 lines | Minor |
| Add delta/diff logic (before vs after) | High | Would require fetching BEFORE state, extra API call per event — doubles rate limit exposure. Not worth it. |
| Add `actor_id` | N/A | Not in Sapo log API response |

### Structural observations

1. **Dedup priority in src_sapo_orders_v2**: `history_log` priority = 2, `webhook` = 3 (higher = preferred). This means webhook beats history_log when both exist for same order. Correct behavior.

2. **Partition explosion**: 677 parquet files for ~4,057 events (June 2026). Each incremental dlt run creates new files per partition. Month=4 alone has many files. Consider periodic compaction.

3. **Incremental cursor on `sync_metadata.event_timestamp`**: This is a JSON path cursor, meaning dlt reads the field from nested JSON. Works correctly but dependent on exact JSON key name — fragile if sync_metadata schema changes.

4. **Status field mapping**: `src_sapo_orders_v2` reads `$.payment_status` as `financial_status` — correct. Verified: `fact_orders.payment_status` has **0 NULLs** on 890 rows (2026+), 3 distinct values: `PAID` (596), `UNPAID` (293), `PARTIALLY_PAID` (1). No downstream breakage.

---

## Unresolved Questions

1. ~~**financial_status NULL**~~ — **RESOLVED 2026-06-09**: `fact_orders.payment_status` confirmed non-NULL (0/890 NULLs). Pipeline reads `$.payment_status` correctly.

2. **Dec 2025 partition** — only 6 events over 2 orders. Was this an initial test run? Is there a full backfill for 2024–2025 historical data, or does history_log coverage genuinely start Jan 2026?

3. **`add` event for already-completed/cancelled orders** — many `add` events show `status = 'completed'` or `cancelled`. This suggests the log captures events when Sapo's backfill runs over pre-existing orders, not just at order creation time. Could indicate duplication with batch ingestion.

4. **Partition compaction** — 677 files for ~4K events is high. Is there a compaction job scheduled, or will file count keep growing unbounded?
