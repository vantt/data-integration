# Re-evaluation: February 2026 Code Review Report

**Date:** 2026-04-03
**Scope:** Verify 27 issues from 2026-02-27 review against current codebase
**Fix commits evaluated:** f7b0ee1, a1b780c, 6e7b643, 0f98f82, a5cdaa0

---

## UNHANDLED Items (7)

### U1. 429 Rate Limit - Retry-After header never read
**Status: FIXED**
**Evidence:** All three sources (`orders.py:176`, `customers.py:170-175`, `accounts.py:132-137`) now read `Retry-After` header with `int(response.headers.get('Retry-After', 60))` and sleep accordingly. Default fallback is 60s (not capped at 10s).

### U2. Duplicate webhook events - append mode with primary_key doesn't dedup
**Status: STILL OPEN**
**Evidence:** `webhook_consumer.py:65-66` still uses `write_disposition="append"` with `primary_key="entity_id"`. In dlt, `append` mode ignores `primary_key` for dedup -- only `merge` disposition deduplicates. Same entity_id webhook events will produce duplicate rows.
**Action:** Change to `write_disposition="merge"` or handle dedup downstream (currently `src_sapo_orders.sql` does dedup by `entity_id` via ROW_NUMBER, so this is **mitigated at SQL layer** but wastes storage).

### U3. Batch ACK return value never checked
**Status: PARTIALLY FIXED**
**Evidence:** `webhook_consumer.py:50-55` -- `batch_ack()` now has proper error handling with `response.raise_for_status()` and prints success/error. However, the return value is still not checked by the caller at line 209 (`client.batch_ack(ids_to_ack)` -- no return value captured, no exception propagation since it's caught internally). If ACK fails, messages will be re-ingested on next poll (at-least-once) but no error is raised to the pipeline.
**Action:** Consider re-raising the exception from `batch_ack()` or returning a boolean so the pipeline can log/alert on ACK failures.

### U4. D1 queue overflow - no backpressure, no depth guard
**Status: STILL OPEN**
**Evidence:** `index.ts:155-159` -- `handleWebhook()` performs a straight INSERT with no queue depth check. No `SELECT COUNT(*)` guard, no backpressure mechanism. Under burst webhook traffic, D1 could accumulate unbounded rows.
**Action:** Add a depth guard (e.g., reject with 503 if queue > threshold) or implement a TTL-based cleanup.

### U5. Late-arriving data silently dropped by MAX watermark
**Status: FIXED**
**Evidence:** All three `src_` models (`src_sapo_orders.sql:35`, `src_sapo_customers.sql:28`, `src_sapo_accounts.sql:28`) now use a 7-day lookback window:
```sql
WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
```
This means late-arriving data within 7 days is captured. Combined with `delete+insert` incremental strategy and business dedup via ROW_NUMBER + QUALIFY, late arrivals are properly handled.

### U6. Duplicate columns in unnest models - build-breaking
**Status: FIXED**
**Evidence:** `stg_sapo_fulfillments.sql`, `stg_sapo_payments.sql`, `stg_sapo_order_items.sql` all use clean column selections from `json_extract_string()` on unnested JSON. No duplicate column names observed. The unnest models reference `src_sapo_orders` and select only the specific JSON arrays they need. Column names are distinct across all three files.

### U7. ACK before load - message deleted from D1 before dlt load completes
**Status: STILL OPEN**
**Evidence:** `webhook_consumer.py:197-209` -- The code acknowledges (deletes from D1) at the end of the generator function, after yielding items. However, as the comments in the code itself note (lines 196-206), this is "at-most-once" risk: if `pipeline.run()` crashes during load phase, data is lost because it was already ACKed.
**Action:** Implement post-load ACK using dlt state or a separate acknowledgment step after `pipeline.run()` succeeds.

---

## PARTIAL Items (20)

### P1. Cookie lock concurrent write race
**Status: FIXED**
**Evidence:** `shared_cookie_manager.py:212-247` -- `_write_cookie_file()` now uses `tempfile.mkstemp()` for unique temp files per write (eliminates concurrent collision), acquires exclusive file lock during write, and uses `os.replace()` for atomic rename. Both NTFS and POSIX safe.

### P2. Session expiry mid-pagination
**Status: FIXED**
**Evidence:** All three sources (`orders.py:162-172`, `customers.py:158-168`, `accounts.py:125-130`) now detect 401/403 responses mid-pagination and call `client.refresh_session(current_session)` to refresh cookies. If refresh fails, raises `HTTPError`.

### P3. Empty page = premature pagination stop
**Status: STILL OPEN**
**Evidence:** `orders.py:192-194`, `customers.py:188-190`, `accounts.py:150-151` -- when `orders_data` (or equivalent) is empty, all three files `break` immediately. If the API returns an empty page due to a transient error or pagination gap, the pipeline stops prematurely. No retry or confirmation logic.
**Action:** Consider retrying once on empty page or checking API metadata (total count) before stopping.

### P4. Pipeline state after partial load
**Status: PARTIALLY FIXED**
**Evidence:** `pipeline_runner.py:80-100` -- retry logic exists with exponential backoff (3 attempts), and on final failure the exception is re-raised (not swallowed). However, dlt's incremental state (`last_value`) may have been partially updated during a failed run. If the pipeline partially loaded data and then crashed, the next run's `last_value` might skip some records.
**Action:** This is inherent to dlt's state management. The 7-day lookback window in src_ models mitigates this for the transformation layer.

### P5. Google Sheets NaN -> "nan" string
**Status: FIXED**
**Evidence:** `gsheet_marketing_spend.py:158` -- `df['source_id'] = df['source_id'].where(df['source_id'].notna())` preserves NaN as actual null/NaN instead of casting to string "nan". The `fillna(0)` on line 151 only applies to numeric columns (`spend_amount`, `clicks`, `impressions`), not to FK columns.

### P6. Webhook encoding "auto" mode
**Status: FIXED**
**Evidence:** `config.ts:23-30` -- Known sources (sapo, github) have explicit encoding (`base64`, `hex` respectively). `auto` mode only applies to `DEFAULT_CONFIG` (line 37) for unknown sources. The `index.ts:90-104` auto-detection heuristic is reasonable: checks for `sha256=` prefix for hex, defaults to base64 otherwise.

### P7. ROW_NUMBER tiebreaker missing in src_sapo_orders
**Status: FIXED**
**Evidence:** `src_sapo_orders.sql:42-53` -- ROW_NUMBER has proper tiebreaker:
```sql
ORDER BY event_timestamp DESC,
    CASE WHEN ingest_method = 'webhook' THEN 3
         WHEN ingest_method = 'history_log' THEN 2
         ELSE 1
    END DESC
```
Plus business dedup at line 158-161 uses `event_timestamp DESC, try_cast(modified_on AS TIMESTAMP) DESC NULLS LAST`.

### P8. modified_on sorted as string not TIMESTAMP
**Status: FIXED**
**Evidence:** `src_sapo_orders.sql:160` -- `try_cast(modified_on AS TIMESTAMP) DESC NULLS LAST`. Same pattern in `src_sapo_customers.sql:102` and `src_sapo_accounts.sql:81`. All cast `modified_on` to TIMESTAMP before sorting.

### P9. dim_products null overwrite
**Status: STILL OPEN**
**Evidence:** `dim_products.sql:19-30` -- "Last Record Wins" strategy uses `ROW_NUMBER() OVER (PARTITION BY product_id, variant_id ORDER BY extracted_at DESC)`. If the latest order item has NULL for `product_name` or other fields (e.g., data quality issue), it overwrites a previously valid name. No `COALESCE` with prior values.
**Action:** Use `COALESCE` in SELECT or filter `WHERE product_name IS NOT NULL` more aggressively, or use a "last non-null" strategy.

### P10. Empty array unnesting drops orders
**Status: FIXED**
**Evidence:** All three unnest models filter before unnesting:
- `stg_sapo_fulfillments.sql:25-26`: `WHERE fulfillments_json IS NOT NULL AND fulfillments_json NOT IN ('[]', 'null', '')`
- `stg_sapo_payments.sql:25-26`: Same pattern for `payments_json`
- `stg_sapo_order_items.sql:25-26`: Same pattern for `order_line_items_json`
These are separate models from `stg_sapo_orders`, so orders without line items/payments/fulfillments are not dropped from the main orders flow.

### P11. Surrogate key NULL collisions
**Status: FIXED**
**Evidence:** `fact_payments.sql:11` -- `coalesce(cast(payment_id as varchar), 'Unknown')` inside surrogate key generation. `fact_orders.sql` uses similar `coalesce(..., 'Unknown')` patterns throughout (lines 31, 50, 60, etc.). NULL values are coalesced to 'Unknown' before hashing, preventing NULL collision in surrogate keys.

### P12. Serving DB runs on partial dbt failure
**Status: PARTIALLY FIXED**
**Evidence:** `serving.py:47-59` -- After running the script, it checks stdout for "error" keywords and logs warnings. However, it does NOT block execution -- it still returns `Output(value="Serving DB Updated")` even with warnings. The serving DB will be generated from whatever dbt managed to export, potentially with stale/missing tables.
**Action:** Consider failing the asset (raising an exception) when dbt errors are detected, or at minimum marking the output as degraded.

### P13. Venv path Windows-specific
**Status: FIXED**
**Evidence:** `serving.py:14-18` -- Platform detection with `sys.platform == "win32"` selects `Scripts/python.exe` on Windows, `bin/python` on Linux. Falls back to `sys.executable` if neither exists.

### P14. Env comment parsing dead code
**Status: FIXED**
**Evidence:** `utils.py:35-47` -- The `.env.local` parser now properly handles inline comments. For quoted values, it finds the closing quote and strips the rest. For unquoted values, it strips at first `#` character. This is functional, not dead code.

### P15. SQL injection via f-strings
**Status: PARTIALLY FIXED**
**Evidence:**
- `generate_serving_db.py:96-100` -- **FIXED**: Table names validated against `TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')` allowlist before interpolation into SQL.
- `sync_seeds.py:26,88` -- **FIXED**: CSV-sourced IDs validated against `_ID_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')` before use in SQL.
- `generate_serving_db.py:130-132` -- The `portable_glob` path is still interpolated via f-string into SQL (`'{portable_glob}'`). This path is derived from environment variables, not user input, so risk is low but not zero.

### P16. Cookie files plaintext, no chmod
**Status: FIXED**
**Evidence:** `shared_cookie_manager.py:130-132` -- Directory gets `chmod 0o700` on Linux. `shared_cookie_manager.py:240-241` -- Cookie file gets `chmod 0o600` on Linux after write. Windows is skipped (no-op) which is acceptable since NTFS ACLs are the norm there.

### P17. DB connection leaks (no try/finally)
**Status: PARTIALLY FIXED**
**Evidence:**
- `sync_seeds.py:20,110` -- **FIXED**: Uses `try/finally` with `con.close()`.
- `generate_serving_db.py:77,151-152` -- **FIXED**: Connection closed at end, with `if con: con.close()`.
- `query_lake.py:15,37-38` -- **FIXED**: Uses `try/finally` with `if con: con.close()`.
- `generate_serving_db.py:77-84` -- **EDGE CASE**: If `con = duckdb.connect()` succeeds but an exception occurs between line 77 and the final `con.close()` at line 151, and that exception is not in the try block... actually, the code has `try/except` at line 77 and then continues. If a later unhandled exception occurs in the loop (line 98-149), `con.close()` at line 151 would still execute since it's not in a try/finally. If an exception propagates out, connection leaks.

### P18. Unknown entity ACK-before-validate bug
**Status: STILL OPEN**
**Evidence:** `webhook_consumer.py:99-104` -- Message ID is added to `ids_to_ack` BEFORE validation/parsing. If the message has an unknown entity type (line 118 -- falls through to `et_lower`), or if payload parsing fails (line 129 `continue`), or if inner_payload has no entity_id (line 149 `continue`), the message ID is still in `ids_to_ack` and will be ACKed/deleted at line 209. This means invalid/unparseable messages are silently deleted from D1 with no way to retry or inspect them.
**Action:** Move `ids_to_ack.append(msg_id)` to after successful envelope construction (before `yield`), or maintain a separate list for failed messages.

### P19. Parquet GC race on Linux
**Status: PARTIALLY FIXED**
**Evidence:** `generate_serving_db.py:28-54` -- `garbage_collect()` now catches `PermissionError` (line 44) and `OSError` (line 46) with a retry-after-delay pattern. On Linux, if a file is being read by another process during deletion, the retry catches it and skips. However, there's still a TOCTOU race: between `get_latest_file()` (line 105) and `garbage_collect()` (line 149), a new file could appear, making the "latest" file outdated. Practically low risk given dbt export cadence.

### P20. query_lake.py accepts raw SQL from argv
**Status: STILL OPEN**
**Evidence:** `query_lake.py:43-44` -- `user_query = sys.argv[1]` is passed directly to `con.execute(query)` at line 19. No sanitization, no read-only mode, no allowlist. This is a CLI developer tool, not exposed to external users, but it can execute arbitrary DuckDB commands including writes/deletes.
**Action:** Consider adding `con.execute("SET access_mode = 'read_only'")` before running user queries, or at minimum document the risk.

---

## Summary

| Category | Total | FIXED | PARTIALLY FIXED | STILL OPEN | N/A |
|----------|-------|-------|-----------------|------------|-----|
| UNHANDLED | 7 | 3 | 1 | 3 | 0 |
| PARTIAL | 20 | 12 | 4 | 4 | 0 |
| **Total** | **27** | **15** | **5** | **7** | **0** |

### Remaining Critical Issues (Require Action)
1. **U4** - D1 queue overflow (no backpressure)
2. **U7** - ACK before load (at-most-once data loss risk)
3. **P18** - Unknown entity ACK-before-validate (silent data deletion)

### Remaining Medium Issues
4. **U2** - Webhook dedup relies on downstream SQL (mitigated but wasteful)
5. **U3** - Batch ACK failure silently swallowed
6. **P3** - Empty page premature stop
7. **P9** - dim_products null overwrite
8. **P12** - Serving DB proceeds on partial dbt failure
9. **P17** - generate_serving_db.py connection leak edge case
10. **P19** - Parquet GC TOCTOU race (low risk)

### Remaining Low Issues
11. **P4** - Pipeline state after partial load (mitigated by 7-day window)
12. **P15** - Env-var-derived path in f-string SQL (low risk)
13. **P20** - query_lake.py raw SQL from argv (dev-only tool)

---

## Unresolved Questions
- Is the D1 webhook queue expected to receive burst traffic that could trigger overflow (U4)?
- Is at-most-once acceptable for webhook data, or is at-least-once required (U7)?
- Should the serving layer asset hard-fail on dbt errors rather than warn (P12)?
