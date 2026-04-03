# Plan: JSON Handling & Type Safety — Remaining Fixes

**Date:** 2026-04-03
**Source:** `plans/code-review/code-reviewer-260227-1721-json-handling-type-safety.md`
**Status:** Complete

---

## Re-Assessment Summary

Verified all 6 original edge cases against current codebase. 3 fully fixed, 3 partially remain.

| # | Edge Case | Original | Current | Action |
|---|-----------|----------|---------|--------|
| 1 | Malformed JSON in payload | ⚠️ Partial | ⚠️ Same | Low priority — defer |
| 2 | Null/missing JSON fields | ⚠️ Partial | ⚠️ Same | Low priority — defer |
| 3 | Duplicate columns (build-breaking) | ⚠️ Critical | ✅ Fixed | None |
| 3b | Empty array unnesting | ⚠️ High | ⚠️ Same | **Fix** |
| 4 | Surrogate key NULL collisions | ⚠️ Medium | ⚠️ Same | **Fix** |
| 5 | Unmapped CASE status | ✅ Handled | ✅ Same | None |
| 6 | Type mismatch (TRY_CAST) | ✅ Handled | ✅ Same | None |

**Additionally confirmed:**
- `std_payments.sql:21` still has hardcoded `'CASH' as payment_method_type` — placeholder, not a JSON/type-safety issue but worth noting
- `fact_sales.sql:28` has same `location_id` surrogate key pattern without coalesce (mirrors `fact_orders.sql:50`)
- Staging sapo models have NO `schema.yml` — only `standard/schema.yml` exists

---

## Phase 1: Empty Array Guard (High Priority)

**Problem:** `from_json('[]', '["JSON"]')` produces zero rows → orders with empty arrays silently vanish from staging.

**Files:**
- `transformation/models/staging/stg_sapo_fulfillments.sql` (line 24)
- `transformation/models/staging/stg_sapo_payments.sql` (line 24)
- `transformation/models/staging/stg_sapo_order_items.sql` (line 25)

**Change:** Add empty array/null literal filter to each WHERE clause.

```sql
-- Before:
WHERE fulfillments_json IS NOT NULL

-- After:
WHERE fulfillments_json IS NOT NULL
  AND fulfillments_json NOT IN ('[]', 'null', '')
```

Apply same pattern to `payments_json` and `order_line_items_json`.

- [x] `stg_sapo_fulfillments.sql` — add empty array guard
- [x] `stg_sapo_payments.sql` — add empty array guard
- [x] `stg_sapo_order_items.sql` — add empty array guard

---

## Phase 2: Surrogate Key COALESCE (Medium Priority)

**Problem:** NULL input to `generate_surrogate_key` hashes to fixed empty-string hash → key collisions across all NULL rows.

### 2a. `fact_payments.sql` lines 11, 13

```sql
-- Before:
{{ dbt_utils.generate_surrogate_key(['payment_id']) }} as payment_key,
{{ dbt_utils.generate_surrogate_key(['payment_method_id']) }} as payment_method_key,

-- After:
{{ dbt_utils.generate_surrogate_key(["coalesce(cast(payment_id as varchar), 'Unknown')"]) }} as payment_key,
{{ dbt_utils.generate_surrogate_key(["coalesce(cast(payment_method_id as varchar), 'Unknown')"]) }} as payment_method_key,
```

> Note: `payment_id` should never be NULL in practice (has `not_null` test at std layer), but defensive coding at mart layer costs nothing.

### 2b. `fact_orders.sql` line 50

```sql
-- Before:
{{ dbt_utils.generate_surrogate_key(['location_id']) }} as branch_location_key,

-- After:
{{ dbt_utils.generate_surrogate_key(["coalesce(cast(location_id as varchar), 'Unknown')"]) }} as branch_location_key,
```

### 2c. `fact_sales.sql` line 28

```sql
-- Before:
{{ dbt_utils.generate_surrogate_key(['cast(o.location_id as string)']) }} as branch_location_key,

-- After:
{{ dbt_utils.generate_surrogate_key(["coalesce(cast(o.location_id as string), 'Unknown')"]) }} as branch_location_key,
```

- [x] `fact_payments.sql` — coalesce `payment_id` and `payment_method_id`
- [x] `fact_orders.sql` — coalesce `location_id`
- [x] `fact_sales.sql` — coalesce `location_id`

---

## Phase 3: Staging Schema Tests (Low Priority)

**Problem:** No `schema.yml` for `stg_sapo_*` models — silent data quality failures go undetected.

**Action:** Create `transformation/models/staging/schema.yml` with `not_null` tests on critical fields.

```yaml
version: 2

models:
  - name: stg_sapo_orders
    columns:
      - name: order_id
        tests: [not_null]

  - name: stg_sapo_order_items
    columns:
      - name: item_id
        tests: [not_null]
      - name: order_id
        tests: [not_null]

  - name: stg_sapo_payments
    columns:
      - name: payment_id
        tests: [not_null]
      - name: amount
        tests: [not_null]

  - name: stg_sapo_fulfillments
    columns:
      - name: fulfillment_id
        tests: [not_null]

  - name: stg_sapo_customers
    columns:
      - name: customer_id
        tests: [not_null]
```

- [x] Create `transformation/models/staging/schema.yml`

---

## Deferred (Not Planned)

| Item | Reason |
|------|--------|
| Malformed JSON guard (`TRY_CAST(payload AS JSON)`) | Low real-world risk; Sapo API sends valid JSON. Would add complexity to every staging model. Revisit if ingestion errors observed. |
| Missing field COALESCE on 50+ `json_extract_string` calls | DuckDB returns NULL for missing keys — this is correct behavior. Adding COALESCE everywhere adds noise with no benefit. |
| `std_payments.sql` hardcoded `'CASH'` | Not a JSON/type-safety issue. Tracked separately. |
| New status observability alerts | Nice-to-have, not a data integrity issue. |

---

## Validation

After all changes:
1. `dbt compile` — verify no syntax errors
2. `dbt test` — verify new staging tests pass
3. Spot-check: query `stg_sapo_fulfillments` for orders known to have 0 fulfillments — confirm they no longer appear (they shouldn't have appeared before either, but now the WHERE is explicit)
