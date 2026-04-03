# Code Review: JSON Handling & Type Safety

**Date:** 2026-02-27
**Resolved:** 2026-04-03
**Scope:** `transformation/models/staging/` (sapo + standard) + `transformation/models/marts/`
**Focus:** 6 specific edge cases

---

## Edge Case Results

---

### 1. Malformed JSON in payload fields

**Files:** `stg_sapo_orders.sql`, `stg_sapo_customers.sql`

**Status: ⚠️ Partial**

**Evidence:**
- `stg_sapo_orders.sql` uses `json_extract_string(payload, '$.id')` directly (line 84, 136) — no `TRY_CAST` on the JSON extraction itself, only on the downstream numeric conversions (lines 149–151).
- `stg_sapo_customers.sql` same pattern — raw `json_extract_string` with no guard on malformed payload.
- DuckDB's `json_extract_string` does NOT throw on malformed JSON in all versions — behavior is version-dependent (may return NULL or error).
- The `TRY_CAST` wrappers on numeric fields (e.g. `try_cast(... as DECIMAL(18,2))`) guard against bad *values* but not against a corrupt *payload string* that breaks JSON parsing entirely.

**Impact:** Medium. If a webhook delivers a truncated or invalid JSON blob, DuckDB may silently return NULL for all extracted fields or raise a parse error that fails the entire model run. No row-level error isolation exists.

---

### 2. Null/missing JSON fields in `json_extract_string`

**Files:** All staging models under `transformation/models/staging/` (sapo)

**Status: ⚠️ Partial**

**Evidence:**
- `json_extract_string` returns NULL for missing keys — this is DuckDB-correct behavior and is implicitly relied upon throughout.
- Some fields have explicit COALESCE protection:
  - `stg_sapo_orders.sql` line 180: `coalesce(json_extract_string(payload, '$.shipping_address.province'), json_extract_string(payload, '$.shipping_address.city'))`
  - `stg_sapo_customers.sql` line 82: `coalesce(json_extract_string(payload, '$.sex'), json_extract_string(payload, '$.gender'))`
  - `stg_sapo_customers.sql` line 88: `coalesce(json_extract_string(payload, '$.addresses[0].province'), json_extract_string(payload, '$.addresses[0].city'))`
- However, the majority of ~50+ extracted fields in `stg_sapo_orders.sql` have NO COALESCE/default — they emit NULL directly (e.g. `order_id`, `order_code`, `financial_status`, all timestamp fields).
- `stg_sapo_fulfillments.sql`, `stg_sapo_payments.sql`, `stg_sapo_order_items.sql`: all extracted fields are bare `json_extract_string(...)` with no NULL handling.

**Impact:** Low-Medium. Downstream NULLs flow into marts where most are handled via COALESCE in key generation. But critical fields like `order_id` going NULL is a silent data quality failure with no explicit guard or test at staging level.

---

### 3. Empty array unnesting produces zero rows (inner join data loss)

**Files:** `stg_sapo_fulfillments.sql`, `stg_sapo_payments.sql`, `stg_sapo_order_items.sql`

**Status: ⚠️ Partial**

**Evidence:**
- All three models use `WHERE json_extract_string(payload, '$.fulfillments/payments/order_line_items') IS NOT NULL` before unnesting — this filters out orders where the field is completely absent.
- However, this WHERE clause does NOT handle:
  - Empty arrays (`[]`): `json_extract_string(payload, '$.fulfillments')` on `[]` returns `'[]'` (not NULL) → passes the filter → `from_json('[]', '["JSON"]')` produces zero rows → orders with empty arrays silently drop out.
  - The string `'null'` as a JSON literal (valid JSON null): also non-NULL string, passes filter, but `from_json('null', '["JSON"]')` may error or return 0 rows depending on DuckDB version.
- Result: orders with 0 fulfillments, 0 payments, or 0 line items **are completely absent** from the staging tables.
- Note: `stg_sapo_fulfillments.sql` and `stg_sapo_payments.sql` both have **duplicate column definitions** that will cause DuckDB compile errors:
  - `stg_sapo_fulfillments.sql` lines 29-31: `fulfillment_json` defined twice in the same SELECT
  - `stg_sapo_fulfillments.sql` lines 62-63: `modified_on` defined twice in the outer SELECT
  - `stg_sapo_payments.sql` lines 29-31: `payment_json` defined twice
  - `stg_sapo_payments.sql` lines 61-62: `paid_on` defined twice
  - `stg_sapo_order_items.sql` lines 28-29: `order_id` and `order_code` defined twice

**Impact:** High. The duplicate column definitions are **build-breaking bugs** — these models will fail to compile. The empty-array data loss is also real but secondary to the compilation failure.

---

### 4. Surrogate key generation with NULL columns

**Files:** All dimension/fact models under `transformation/models/marts/`

**Status: ✅ Handled**

**Evidence:**
- `dbt_utils.generate_surrogate_key` with the DuckDB adapter coalesces NULL inputs to empty string `''` before hashing (standard dbt_utils behavior using `coalesce(col, '')`).
- Explicit `coalesce` protection is used at all critical key generation points:
  - `fact_orders.sql` line 26: `coalesce(shipping_province, '')`, `coalesce(shipping_district, '')` etc.
  - `fact_orders.sql` line 41: `coalesce(json_extract_string(...), 'Unknown')`
  - `dim_geography.sql` line 55: `coalesce(province,'')`, `coalesce(district,'')`, etc.
  - `dim_customers_base.sql` line 70, `dim_staff.sql` line 28: explicit Unknown sentinel rows for unmatched joins.
- Potential exception: `fact_payments.sql` line 13: `generate_surrogate_key(['payment_method_id'])` with no explicit coalesce — if `payment_method_id` is NULL (payment with no method), the key hashes to the empty-string hash, potentially colliding across all NULL-method payments. Same on line 11 for `payment_id`.
- `fact_orders.sql` line 42: `generate_surrogate_key(['location_id'])` — no coalesce; NULL `location_id` produces a fixed hash that collides in `dim_branch_location`.

**Impact:** Medium (for the uncoalesced cases). Most are protected but two specific cases in `fact_payments.sql` and `fact_orders.sql` can produce key collisions.

---

### 5. Unmapped status values in CASE statements (fall-through to NULL)

**Files:** `std_orders.sql`, `std_fulfillments.sql`, `std_payments.sql`

**Status: ✅ Handled**

**Evidence:**
- `std_orders.sql` lines 43–49 (`status` CASE): `ELSE 'OPEN'` — new/unknown statuses default to OPEN.
- `std_orders.sql` lines 51–58 (`payment_status` CASE): `ELSE 'UNPAID'` — unknown financial statuses default to UNPAID.
- `std_orders.sql` lines 63–90 (`fulfillment_status` CASE): `ELSE 'IN_PROGRESS'` — unknown states default to IN_PROGRESS.
- `std_fulfillments.sql` lines 21–28 (`status` CASE): `ELSE 'PENDING'` — unknown fulfillment statuses default to PENDING.
- `std_payments.sql` lines 26–33 (`status` CASE): `ELSE 'PENDING'` — unknown payment statuses default to PENDING.

All CASE statements have ELSE clauses. No NULL fall-through possible.

**Impact:** None for null-fall-through. However, the defaults may silently misclassify new Sapo statuses (e.g. a new status 'processing' from Sapo API upgrade would appear as 'OPEN'/'PENDING'/'IN_PROGRESS' without any alert). This is an observability gap, not a data loss issue.

---

### 6. Type mismatch between JSON extracted strings and target columns

**File:** `stg_sapo_orders.sql`, `std_orders.sql`

**Status: ✅ Handled**

**Evidence:**
- All numeric fields use `TRY_CAST(...as DECIMAL(18,2))` or `TRY_CAST(...as INTEGER)`:
  - `stg_sapo_orders.sql` lines 149–151: `try_cast(... as DECIMAL(18,2))` for total, discount, tax.
  - `stg_sapo_customers.sql` lines 95–98: `try_cast` for all numeric fields.
  - `stg_sapo_order_items.sql` lines 53–58: `try_cast` for quantity, price, amounts.
- All timestamp fields use `TRY_CAST(...as TIMESTAMP)` at the std_ layer:
  - `std_orders.sql` lines 35–40: `try_cast(created_on as TIMESTAMP)` etc.
  - `std_fulfillments.sql` lines 37–38, `std_payments.sql` lines 37–38.
- `TRY_CAST` returns NULL on failure instead of erroring — all bad numeric strings (e.g. `"N/A"`, empty string) become NULL silently.

**Impact:** Low. Handled correctly. Silent NULL on bad cast is acceptable behavior for staging but there are no dbt tests (`not_null`) on key financial columns (`total_amount`, `amount`) to catch systematic cast failures.

---

## Summary Table

| # | Edge Case | Status | Severity |
|---|-----------|--------|----------|
| 1 | Malformed JSON in payload | ⚠️ Partial | Medium | ⏳ Deferred |
| 2 | Null/missing JSON fields | ⚠️ Partial | Low-Medium | ⏳ Deferred |
| 3 | Empty array unnesting / data loss | ⚠️ Partial + build-breaking duplicates | **High** | ✅ Fixed 2026-04-03 |
| 4 | Surrogate key with NULL columns | ✅ Handled (2 edge cases remain) | Medium | ✅ Fixed 2026-04-03 |
| 5 | Unmapped CASE status fall-through | ✅ Handled | Low | ✅ No action needed |
| 6 | Type mismatch on JSON extractions | ✅ Handled | Low | ✅ No action needed |

---

## Critical Bugs Found

**Build-breaking duplicate column definitions** (Edge Case 3):

- `stg_sapo_fulfillments.sql`:
  - Line 29 and 31: `fulfillment_json` selected twice in `unnested_fulfillments` CTE
  - Line 62 and 63: `modified_on` selected twice in final SELECT
- `stg_sapo_payments.sql`:
  - Line 29 and 31: `payment_json` selected twice in `unnested_payments` CTE
  - Line 61 and 62: `paid_on` selected twice in final SELECT
- `stg_sapo_order_items.sql`:
  - Lines 28–29: `order_id` selected twice; lines 29–30: `order_code` selected twice in `unnested_items` CTE

These will cause DuckDB/dbt to error on model compilation. These appear to be copy-paste artifacts.

---

## Recommended Actions

1. ~~**[Critical] Fix duplicate column definitions**~~ — ✅ Fixed prior to 2026-04-03
2. ~~**[High] Handle empty array case**~~ — ✅ Fixed 2026-04-03: added `NOT IN ('[]', 'null', '')` guards
3. ~~**[Medium] Add coalesce to `fact_payments.sql`**~~ — ✅ Fixed 2026-04-03: wrapped in `coalesce(..., 'Unknown')`
4. ~~**[Medium] Add coalesce to `fact_orders.sql`**~~ — ✅ Fixed 2026-04-03 (also fixed `fact_sales.sql`)
5. ~~**[Low] Add dbt `not_null` tests**~~ — ✅ Fixed 2026-04-03: created `staging/schema.yml`
6. **[Low] Consider `TRY_CAST(payload AS JSON)` wrapper** — ⏳ Deferred (see `code-reviewer-260227-1721-json-handling-deferred.md`)

---

## Unresolved Questions

- What DuckDB version is in use? `json_extract_string` error behavior on malformed JSON differs across versions (pre/post 0.9).
- Are dbt tests defined in schema.yml for these staging models? Not reviewed here — tests on `order_id` uniqueness/not_null would catch several of the above issues at run time.
- Is the `std_payments.sql` hardcoded `'CASH' as payment_method_type` (line 21) a known placeholder or production gap? Every payment shows as CASH regardless of actual method.
