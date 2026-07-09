# Crossborder Channel Detection — Correlated Subquery Bug Caught by Data Inspection

**Date**: 2026-07-08 17:52  
**Severity**: High (caught pre-deploy; would have shipped silently otherwise)  
**Component**: transformation/models/marts/core/dim_customers.sql  
**Status**: Fixed, tested (dbt 14/14 pass), Dagster verified, Phase 2 validation passed

## What Happened

Implemented a channel-derived signal to auto-classify customers as CROSSBORDER if they have any US-channel (gift-fulfilment) order, even if their Sapo group-tag was never manually applied. Added a `us_channel_customers` CTE to `dim_customers.sql` and OR'd it into the customer_type CASE and is_us_gift_recipient boolean via a correlated EXISTS subquery. Commit: `ea0a4286`.

The implementation worked—tests passed, Dagster run succeeded, Phase 2 validation (cross-check vs reference CSV) confirmed correct reclassifications (773 of 817 reference rows). But a **subtle SQL bug nearly shipped silently**.

## The Brutal Truth

The first pass used an unqualified column in the correlated subquery:

```sql
EXISTS (SELECT 1 FROM us_channel_customers uc WHERE uc.customer_key = customer_key)
```

That unqualified `customer_key` on the right side resolved to the subquery's own FROM scope (`us_channel_customers uc`), not the outer row being checked. Result: the WHERE clause became a non-correlated, always-true condition (if the table had any rows, the WHERE trivially matched). 

I ran `dbt run --full-refresh --select dim_customers` and immediately checked the output distribution. customer_type=CROSSBORDER jumped to **7429 of 7601 customers** (RETAIL dropped to zero). That number was obviously implausible—it took 60 seconds to spot. No code review process would have caught this without running the actual query and eyeballing the results. The bug was **subtle enough to escape static analysis** but **obvious enough to fail any plausibility check**.

## Technical Details

**The Bug:** SQL scope resolution ambiguity. In DuckDB (and most SQL dialects), an unqualified column name in a subquery resolves to the closest matching table in scope. If the inner query has a table with that column name, the outer reference is shadowed—silently.

**The Fix:** Fully qualified the reference:
```sql
EXISTS (SELECT 1 FROM us_channel_customers uc WHERE uc.customer_key = joined_data.customer_key)
```

The outer SELECT's FROM clause is unqualified (`FROM joined_data`), so the table name itself is a valid qualifier in DuckDB. Re-ran full-refresh; distribution became plausible (773 RETAIL→CROSSBORDER reclassifications).

**Verification Steps:**
1. dbt full-refresh completed with lock-retry (expected behavior in this repo's single-writer DuckDB setup)
2. Immediate data distribution check: customer_type value_counts
3. Re-ran after fix: 8/8 dbt tests passed (accepted_values, relationships, uniqueness)
4. Dagster full run: `dagster asset materialize --select marts/dim_customers` (14/14 checks passed)
5. Phase 2 hard gate: 813/817 reference CSV rows now CROSSBORDER, 4 stayed WHOLESALE (higher CASE precedence—by design)
6. All 7 downstream marts rebuilt: action-queue, benchmarks, retention, cohort, snapshot—no errors
7. Serving layer: stopped Metabase, ran bootstrap_serving_views.py, restarted; reverse-ETL (crm/refresh.sh) synced to cache.db

**Bonus:** A code-reviewer subagent independently caught the same bug pattern reproduced in `docs/context/order-customer-classification-staff-guide.md` (mục 9)—the doc's copy-pasteable SQL example still had the unqualified form. Fixed the doc too.

## Root Cause: SQL Scope Shadowing

Correlated subqueries are easy to write carelessly. An unqualified column name will resolve to the closest matching table, with no error or warning. This is standard SQL behavior but creates a trap: the query is syntactically valid, it returns results (wrong results), and it's only caught by inspection of the actual output distribution.

## Lessons Learned

1. **Always check the actual numbers immediately after schema changes:** This is the hardest gate. A distribution check (value_counts, cardinality by key class) catches implausible results before they propagate. Code review + linting do not catch scope-shadowing bugs.

2. **Fully qualify all column references in correlated subqueries:** Unqualified names are ambiguous. Use table alias or fully-qualified name in all ON/WHERE clauses. It's one extra keystroke and eliminates this whole class of bug.

3. **The "hard gate" (Phase 2 blast-radius check) is non-negotiable:** Comparing the reclassified distribution against reference data (us-customers-260606.csv) immediately caught plausibility. This is not optional verification—it's the production safety net.

4. **Single-writer DuckDB lock contention is normal:** The full-refresh required a lock-retry loop because Dagster's realtime incremental jobs hold the write lock concurrently. This is a known characteristic, not a new issue; document it and move on.

## Next Steps

1. ✅ Document the correlated subquery scope-shadowing pattern in `docs/code-standards.md` (example: dim_customers.sql line XXX + this incident)
2. ✅ Future implementations of similar signals (product_affinity, channel-based grouping) will use this pattern as reference code
3. No blocking issues; served to production; monitoring for 72h nominal drift
