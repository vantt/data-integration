# Deferred: JSON Handling & Type Safety

**Source:** `archive/code-reviewer-260227-1721-json-handling-type-safety.md`
**Deferred on:** 2026-04-03
**Priority:** Low

---

## 1. Malformed JSON Guard

**Original Edge Case #1 — Medium severity**

**Problem:** `json_extract_string(payload, '$.field')` has no upstream guard against corrupt/truncated JSON payloads. If Sapo webhook delivers invalid JSON, DuckDB may return NULL for all fields or raise a parse error that fails the entire model run.

**Files:** `stg_sapo_orders.sql`, `stg_sapo_customers.sql`

**Proposed fix:** Wrap payload in `TRY_CAST(payload AS JSON)` in source models to isolate malformed rows before extraction.

**Why deferred:** Low real-world risk — Sapo API sends valid JSON. Would add complexity to every staging model. Revisit if ingestion errors observed in production.

---

## 2. Null/Missing JSON Field COALESCE

**Original Edge Case #2 — Low-Medium severity**

**Problem:** ~50+ `json_extract_string` calls have no COALESCE/default — they emit NULL directly for missing keys.

**Files:** All `stg_sapo_*.sql` models

**Why deferred:** DuckDB's `json_extract_string` returns NULL for missing keys — this is correct, expected behavior. Adding COALESCE everywhere would add noise with no benefit. Critical fields (`order_id`, `customer_id`, etc.) now have `not_null` dbt tests in `staging/schema.yml` to catch systematic failures.

---

## 3. Hardcoded Payment Method Type

**Not from original edge cases — noted during review**

**Problem:** `std_payments.sql:21` has `'CASH' as payment_method_type` — every payment shows as CASH regardless of actual method.

**File:** `transformation/models/staging/standard/std_payments.sql`

**Proposed fix:** Join `payment_method_id` with a reference table (`ref_payment_methods`) to resolve actual method type.

**Why deferred:** Not a JSON/type-safety issue. Requires reference data that may not exist yet.

---

## 4. New Status Observability

**Original Edge Case #5 — noted as gap**

**Problem:** CASE ELSE defaults silently absorb unknown Sapo statuses. No alerting when new status values appear from API changes.

**Files:** `std_orders.sql`, `std_fulfillments.sql`, `std_payments.sql`

**Proposed fix:** Add dbt `accepted_values` tests with `warn` severity (already exists at standard layer in `schema.yml`). Consider adding a monitoring query that flags rows hitting ELSE clauses.

**Why deferred:** Not a data integrity issue — just observability. Standard layer already has `accepted_values` tests.
