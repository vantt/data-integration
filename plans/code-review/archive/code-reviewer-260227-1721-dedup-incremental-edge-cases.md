# Code Review: Transformation Deduplication & Incremental Logic
**Date:** 2026-02-27
**Scope:** 7 targeted edge cases in `transformation/models/`
**Files reviewed:** `stg_sapo_orders.sql`, `src_sapo_orders.sql`, `stg_sapo_customers.sql`, `stg_sapo_accounts.sql`, `dim_products.sql`, `dim_customers_base.sql`, `fact_orders.sql`, `int_customer_metrics.sql`

---

## Edge Case Findings

---

### 1. ROW_NUMBER tie-breaking with identical timestamps

**Status: Handled**

**Evidence:**
- `stg_sapo_orders.sql` lines 54-62: three-level sort on `(event_timestamp DESC, ingest_method CASE DESC)`
- `stg_sapo_customers.sql` lines 42-48: same three-level sort pattern
- `stg_sapo_accounts.sql` lines 35-41: same pattern

**Tiebreaker precedence:** `webhook` (3) > `history_log` (2) > other/batch (1).

**Residual risk (low):** If two records share identical `event_timestamp` AND identical `ingest_method`, the winner is non-deterministic (DuckDB window function ordering is not stable within a tie). In practice this is extremely unlikely for webhook events but is theoretically possible for batch ingestion where multiple records for the same `entity_id` are created in the same run.

`src_sapo_orders.sql` (the view) has **no tiebreaker** — only `ORDER BY event_timestamp DESC` (line 35). This is a lower-risk path since it feeds into the staging model which re-deduplicates, but the view itself is non-deterministic on timestamp ties.

**Impact:** Low. Practical exposure only if batch writes duplicate `entity_id` rows with the same timestamp.

---

### 2. Double dedup: different entity_ids, same order_id, different data

**Status: Partial**

**Evidence - `stg_sapo_orders.sql` lines 93-105:**
```sql
final_dedup_keys AS (
    SELECT entity_id, event_timestamp, ingest_method
    FROM pre_dedup_source
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_id
        ORDER BY event_timestamp DESC, modified_on DESC
    ) = 1
)
```

**What is handled:** When multiple `entity_id`s share the same `order_id`, the record with the latest `event_timestamp`, then latest `modified_on`, wins. This is deterministic in the common case.

**What is not deterministic:**
- If two entity_ids have the identical `event_timestamp` AND identical `modified_on`, the winner is undefined (no further tiebreaker).
- `modified_on` is extracted from JSON as a string (line 85: `json_extract_string(s.payload, '$.modified_on') as modified_on`) and sorted lexicographically, not as TIMESTAMP. ISO-8601 strings sort correctly, but any format deviation (e.g., Vietnamese locale timestamps) would produce wrong ordering silently.

**Impact:** Medium. The string-vs-timestamp sort on `modified_on` is a latent bug. If Sapo ever returns a non-ISO datetime for `modified_on`, the "wrong" entity wins and the data silently corrupts.

---

### 3. Late-arriving data with earlier timestamp skipped by incremental

**Status: Unhandled**

**Evidence — all three incremental staging models:**
- `stg_sapo_orders.sql` line 42: `WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})`
- `stg_sapo_customers.sql` line 30: identical pattern
- `stg_sapo_accounts.sql` line 23: identical pattern

**The problem:** The incremental filter is a strict `>` against `MAX(event_timestamp)` of the destination table. Any record that arrives late with an `event_timestamp` older than the current max is silently dropped. This is a classic late-arrival problem with `MAX`-watermark incrementals.

**`dim_customers_base.sql` lines 63-65:**
```sql
{% if is_incremental() %}
WHERE updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```
Uses `>=` (inclusive) not `>`, slightly better but still misses records whose `updated_at` is earlier than the current max.

**Scenarios that cause silent data loss:**
- History log run is delayed and delivers records with old timestamps after a webhook already advanced the watermark.
- A Sapo API backfill delivers corrected historical records.
- Clock skew between ingestion workers.

**Impact:** High. Silent data loss with no error or warning. The only recovery path is a full refresh (`dbt run --full-refresh`), which is expensive. No alerting or monitoring mechanism is present to detect this.

---

### 4. delete+insert race condition during concurrent dbt runs

**Status: Handled (by constraint, not by code)**

**Evidence:**
- All three staging models use `incremental_strategy='delete+insert'` (lines 4 in each).
- DuckDB enforces single-writer semantics at the file/database level. Concurrent writes to the same DuckDB file are serialized or fail with a lock error.

**No application-level locking or concurrency guard is present in the SQL.** Safety comes entirely from DuckDB's architecture.

**Residual risk (low-medium):** If the pipeline is ever migrated to a multi-writer database (PostgreSQL, BigQuery, Snowflake), the `delete+insert` strategy without transaction isolation would introduce a window where a read between the delete and insert returns zero rows. DuckDB prevents this today; the code provides no portability safeguard.

**Impact:** Low in current DuckDB context. Medium if the database layer changes.

---

### 5. "Last Record Wins" staleness in dim_products

**Status: Partial**

**Evidence — `dim_products.sql` lines 11-25:**
```sql
ranked_products AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY product_id, variant_id
            ORDER BY extracted_at DESC
        ) as rn
    FROM order_items
    WHERE product_id IS NOT NULL
)
```

**What is handled:** Comment at line 12 acknowledges the strategy and its limitation. Unknown product sentinel row is provided via `UNION ALL` at line 51.

**What is not handled:** If the most recent order item contains NULL product attributes (e.g., `product_name IS NULL`, `unit_price = 0`), those nulls overwrite previously good data. There is no `COALESCE`-based fallback to a prior good record.

Specifically for `unit_price`: `last_sold_price` (line 43) will be 0 or NULL if the latest item had a zero/missing price. Downstream models consuming `dim_products.last_sold_price` would receive corrupt data without any error.

The TODO comment on line 14 ("Update this when we have a dedicated Product Sync") confirms this is a known architectural gap.

**Impact:** Medium. Data corruption is silent; zero prices propagate to `fact_sales` / `fact_orders` without warning. Risk increases as catalog grows and old orders reference products later modified or deleted.

---

### 6. First-run bootstrap: dim_customers_base empty when fact_orders runs

**Status: Handled**

**Evidence — `fact_orders.sql` lines 12-14, 23, 78:**
```sql
valid_customers AS (
    SELECT customer_key FROM {{ ref('dim_customers_base') }}
),
...
COALESCE(vc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key,
...
LEFT JOIN valid_customers vc ON ... = vc.customer_key
```

**Why it is safe:** `fact_orders` uses a `LEFT JOIN` to `dim_customers_base`, not an `INNER JOIN`. The `COALESCE` wraps the result, falling back to the `'Unknown'` surrogate key when no match is found. On first run when `dim_customers_base` is empty, every order gets `customer_key = md5('Unknown')` — no failure, no data loss.

**`dim_customers_base.sql` lines 67-86:** An `Unknown` sentinel row is appended via `UNION ALL`, ensuring the unknown key always exists in the dimension.

**Minor note:** The incremental filter in `dim_customers_base` uses `updated_at >= MAX(updated_at)` — on first run this branch is not taken (full load), so no bootstrap issue there either.

**Impact:** None. Handled correctly.

---

### 7. Customer metrics with zero orders

**Status: Handled**

**Evidence — `int_customer_metrics.sql`:**
- The model sources from `fact_orders` and aggregates only customers who have orders (`GROUP BY customer_key` after joining `fact_orders`).
- Customers with zero orders are simply absent from this intermediate table — no NULL LTV or division-by-zero is possible.
- `frequency` uses `COUNT(DISTINCT order_id)` — always >= 1 for any row produced, never 0.
- `monetary_value` uses `SUM(gmv)` — returns NULL only if all `gmv` values are NULL (not zero-order case), and `SUM` never divides.
- No division operations anywhere in the model.

**Downstream `dim_customers`** (not reviewed here) would need to handle customers that don't appear in `int_customer_metrics` — a `LEFT JOIN` pattern there would be the correct approach.

**Impact:** None within this model. Verify `dim_customers` uses `LEFT JOIN` on `int_customer_metrics`.

---

## Summary Table

| # | Edge Case | Status | Severity |
|---|-----------|--------|----------|
| 1 | ROW_NUMBER tie on identical timestamp + ingest_method | Partial | Low |
| 2 | Double dedup: `modified_on` sorted as string not timestamp | Partial | Medium |
| 3 | Late-arriving data silently dropped by MAX watermark | **Unhandled** | **High** |
| 4 | delete+insert race condition | Handled (DuckDB constraint) | Low |
| 5 | dim_products last-record-wins overwrites good data with nulls | Partial | Medium |
| 6 | First-run bootstrap with empty dim_customers_base | Handled | None |
| 7 | Customer metrics with zero orders | Handled | None |

---

## Recommended Actions (priority order)

1. **[High] Late-arriving data (edge case 3):** Switch incremental filter from strict `>` MAX watermark to a lookback window, e.g., `WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }}) - INTERVAL 24 HOURS`. Accept some re-processing overhead to catch late arrivals. Document the chosen SLA.

2. **[Medium] `modified_on` string sort (edge case 2):** Cast `modified_on` to TIMESTAMP before using it as a sort key in `final_dedup_keys`:
   ```sql
   ORDER BY event_timestamp DESC, try_cast(modified_on AS TIMESTAMP) DESC
   ```
   Add a `NULLS LAST` clause to handle rows where `modified_on` is absent.

3. **[Medium] dim_products null attribute overwrite (edge case 5):** Add null-safety to `ranked_products` by using `FIRST_VALUE(product_name IGNORE NULLS) OVER (PARTITION BY product_id, variant_id ORDER BY extracted_at DESC)` per column, or filter `WHERE product_name IS NOT NULL AND unit_price > 0` before the ranking.

4. **[Low] src_sapo_orders.sql tiebreaker (edge case 1):** Add `ingest_method` CASE tiebreaker to the view's `ROW_NUMBER` ORDER BY, consistent with the staging model pattern.

5. **[Low] Portability note (edge case 4):** Add a code comment to the incremental staging models noting that `delete+insert` safety depends on DuckDB single-writer semantics. Flag as a migration concern.

---

## Unresolved Questions

- Does `dim_customers` use `LEFT JOIN` on `int_customer_metrics`? If it uses `INNER JOIN`, customers with zero orders are silently excluded from the customer dimension (not reviewed).
- What is the accepted SLA for late-arriving data? The correct lookback window for the incremental filter depends on this.
- Is `modified_on` in Sapo API responses always ISO-8601 format? If locale-dependent formats are possible, the string-sort risk in edge case 2 is higher.
- `dim_products` is not materialized as `incremental` — it does a full rebuild on each run from `std_order_items`. At scale, this will become expensive. Confirm whether this is intentional given the "no dedicated product sync" TODO.
