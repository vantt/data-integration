# Codebase Edge Case Verification Report

**Date:** 2026-02-27 17:15
**Scope:** Full codebase (Ingestion, Transformation, Orchestration, Webhooks, Scripts)
**Method:** Ultrathink → 6 parallel code-reviewer agents

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total edge cases verified | 40 |
| Handled | 13 ✅ |
| Unhandled | 7 ❌ |
| Partial | 20 ⚠️ |

### Critical/High Severity Issues: 10

---

## Unhandled Edge Cases (Need Fix)

| # | Edge Case | File(s) | Severity | Category |
|---|-----------|---------|----------|----------|
| 1 | **429 rate limit — Retry-After header never read, backoff caps at 10s** | `ingestion/src/sapo/*.py` | High | Ingestion |
| 2 | **Duplicate webhook events — append mode with primary_key doesn't dedup** | `ingestion/src/sapo/webhook_consumer.py` | High | Webhook |
| 3 | **Batch ACK return value never checked — silent re-ingestion after timeout** | `webhook_consumer/*/client.py`, `ingestion/src/sapo/webhook_consumer.py` | High | Webhook |
| 4 | **D1 queue overflow — no backpressure, no depth guard on INSERT** | `webhook_receiver/cloudflareD1/src/index.ts` | High | Webhook |
| 5 | **Late-arriving data silently dropped by MAX watermark** | `stg_sapo_orders.sql`, `stg_sapo_customers.sql`, `stg_sapo_accounts.sql` | High | Transformation |
| 6 | **Duplicate columns in unnest models — build-breaking** | `stg_sapo_fulfillments.sql`, `stg_sapo_payments.sql`, `stg_sapo_order_items.sql` | Critical | Transformation |
| 7 | **ACK before load — message deleted from D1 before dlt load completes** | `ingestion/src/sapo/webhook_consumer.py` | High | Webhook |

## Partial Handling (Need Review)

| # | Edge Case | File(s) | Severity | Issue |
|---|-----------|---------|----------|-------|
| 1 | Cookie lock concurrent write race | `shared_cookie_manager.py` | Medium | Two writers share `.tmp` file, last wins |
| 2 | Session expiry mid-pagination | `orders.py`, `customers.py`, `accounts.py` | High | Login refresh exists but no tenacity coverage on login failure |
| 3 | Empty page = premature pagination stop | Same | High | Transient empty API response terminates fetch silently |
| 4 | Pipeline state after partial load | `pipeline_runner.py` | Medium | No cursor rollback; `--limit` flag silently ignored |
| 5 | Google Sheets NaN→"nan" string | `gsheet_marketing_spend.py` | High | `astype(str)` on NaN corrupts FK joins; hardcoded "2026" year |
| 6 | Webhook encoding "auto" mode | `utils.ts` | Medium | Hex sig without prefix treated as base64, opaque error |
| 7 | ROW_NUMBER tiebreaker missing in `src_sapo_orders` | `src_sapo_orders.sql` | Low | Non-deterministic but re-deduped downstream |
| 8 | `modified_on` sorted as string not TIMESTAMP | `stg_sapo_orders.sql` | Medium | Lexicographic sort; breaks on non-ISO formats |
| 9 | dim_products null overwrite | `dim_products.sql` | Medium | Latest order item with NULL name/price overwrites good data |
| 10 | Empty array unnesting drops orders | `stg_sapo_fulfillments/payments/order_items.sql` | Medium | No guard for `'[]'` or `'null'` string values |
| 11 | Surrogate key NULL collisions | `fact_payments.sql`, `fact_orders.sql` | Medium | NULL `payment_id` / `location_id` → same hash |
| 12 | Serving DB runs on partial dbt failure | `orchestration/assets/serving.py` | Medium | No check for incomplete marts |
| 13 | Venv path Windows-specific | `orchestration/assets/serving.py` | Low | Falls back silently on Linux |
| 14 | Env comment parsing dead code | `orchestration/assets/utils.py` | Low | `KEY=value#comment` includes `#comment` |
| 15 | SQL injection via f-strings | `generate_serving_db.py`, `sync_seeds.py` | Medium | Table names from filesystem interpolated into SQL |
| 16 | Cookie files plaintext, no chmod | `shared_cookie_manager.py` | Medium | Session tokens world-readable |
| 17 | DB connection leaks (no try/finally) | All scripts using DuckDB | Medium | Write lock held on crash |
| 18 | Unknown entity ACK-before-validate bug | `webhook_consumer.py` | Medium | msg_id ACKed before entity_id validation; malformed msg lost silently |
| 19 | Parquet GC race on Linux | `generate_serving_db.py` | Low | No file locking on Linux |
| 20 | `query_lake.py` accepts raw SQL from argv | `query_lake.py` | Low | Manual-only script |

## Handled Edge Cases ✅

| # | Edge Case | Notes |
|---|-----------|-------|
| 1 | HMAC missing/empty signature | Guard returns 401 HMAC_MISSING |
| 2 | HMAC timing attack | `crypto.subtle.verify` (constant-time) |
| 3 | Credential .env gitignored | All .env files excluded |
| 4 | Unknown entity dynamic table | dlt handles via `with_table_name()` |
| 5 | First-run bootstrap empty dim_customers_base | LEFT JOIN + Unknown sentinel |
| 6 | Customer metrics zero orders | Absent from output, no div-by-zero |
| 7 | delete+insert race (DuckDB) | Single-writer architecture prevents |
| 8 | Dagster asset materialization order | Upstream keys correctly injected |
| 9 | dbt asset key translation | All 5 sources mapped |
| 10 | Empty rolling directories | Early return, drops view |
| 11 | Unmapped CASE status values | All CASE have ELSE clause |
| 12 | Type mismatch JSON→columns | TRY_CAST used throughout |
| 13 | Stale lock files blocking pipelines | OS-managed locks, 10s timeout |

---

## Priority Fix Recommendations

### P0 — Critical (Build-Breaking)
1. **Remove duplicate column definitions** in `stg_sapo_fulfillments.sql`, `stg_sapo_payments.sql`, `stg_sapo_order_items.sql`

### P1 — High Severity
2. **Late-arriving data**: Add lookback window to incremental watermark (`- INTERVAL 24 HOURS`)
3. **Webhook dedup**: Add payload_hash-based dedup or use merge disposition instead of append
4. **Batch ACK**: Check return value; implement dead-letter queue for failed ACKs
5. **ACK timing**: Move ACK to post-load hook (dlt supports this)
6. **Rate limit**: Read `Retry-After` header; extend tenacity budget
7. **Google Sheets NaN**: Replace `astype(str)` with proper null handling; remove hardcoded year

### P2 — Medium Severity
8. **D1 backpressure**: Add queue depth check before INSERT
9. **Surrogate key NULLs**: Add COALESCE in `fact_payments.sql` and `fact_orders.sql`
10. **dim_products staleness**: Filter nulls before ranking or use IGNORE NULLS
11. **`modified_on` sort**: Cast to TIMESTAMP before ORDER BY
12. **DB connection leaks**: Wrap all scripts in `with` or `try/finally`
13. **SQL injection**: Allowlist table names in `generate_serving_db.py`
14. **Cookie permissions**: Add `os.chmod(0o600)` on cookie files
15. **Serving partial failure**: Validate all expected marts exist before building serving DB

### P3 — Low Severity
16. Add tiebreaker to `src_sapo_orders.sql` ROW_NUMBER
17. Fix dead code in env comment parsing
18. Add portability comment for delete+insert strategy

---

## Unresolved Questions

1. Does Sapo API return `Retry-After` header with 429? What's the documented rate limit?
2. What is the accepted late-arrival SLA? Determines lookback window size
3. Are `modified_on` values always ISO-8601 from Sapo?
4. What DuckDB version is deployed? Malformed JSON error behavior varies
5. Is `query_lake.py` ever called programmatically or only manually?
6. What is the D1 row/storage limit for the webhook deployment?
7. Is `'CASH' as payment_method_type` in `std_payments.sql` a known placeholder?
8. Does `dim_customers` use LEFT JOIN on `int_customer_metrics`?

---

## Individual Reports

- [Ingestion Edge Cases](code-reviewer-260227-1721-ingestion-edge-cases.md)
- [Webhook Edge Cases](code-reviewer-260227-1721-webhook-edge-cases.md)
- [Dedup & Incremental Edge Cases](code-reviewer-260227-1721-dedup-incremental-edge-cases.md)
- [JSON Handling & Type Safety](code-reviewer-260227-1721-json-handling-type-safety.md)
- [Orchestration Edge Cases](code-reviewer-260227-1721-orchestration-edge-cases.md)
- [Security Edge Cases](code-reviewer-260227-1721-security-edge-cases.md)
