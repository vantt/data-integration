# PM Report — Channel-Based CROSSBORDER Customer Detection

Plan: `plans/260708-1628-crossborder-channel-detection/` | Status: **completed** (all 3 phases) | Date: 2026-07-08

## Summary

Added channel-derived signal (`fact_orders` JOIN `dim_channels` WHERE `channel_name='US'`, non-cancelled) OR'd into `dim_customers.customer_type`'s CROSSBORDER branch + `is_us_gift_recipient`. Deployed to production (full-refresh + downstream marts + Metabase serving + CRM cache), verified via real Dagster asset run.

## Phase completion

| Phase | Status | Key result |
|---|---|---|
| 1. Channel-Based Detection Logic | Done | SQL + docs shipped; 1 real bug caught+fixed (see below) |
| 2. Blast-Radius Validation | Done | Hard gate PASSED: 773 reclassified vs 817 CSV rows |
| 3. Downstream Refresh and Serving Sync | Done | Metabase + CRM cache both confirmed synced |

## Measured numbers

- customer_type: RETAIL 6675→5902, CROSSBORDER 754→1527, WHOLESALE 161 (unchanged), PARTNER 11 (unchanged)
- Only transition type observed: RETAIL→CROSSBORDER (773 rows) — no precedence violations
- CSV cross-check (`us-customers-260606.csv`, 817 rows): 813 now CROSSBORDER, 4 WHOLESALE-by-design with `is_us_gift_recipient=TRUE`
- 7 downstream marts rebuilt, non-zero row counts; 0/773 reclassified customers remain in `mart_customer_action_queue`/`mart_customer_sku_action_queue`
- Real Dagster asset run (`marts/dim_customers`): 14/14 dbt tests/checks PASS, 0 errors
- Metabase serving (`serving/olap.duckdb`) + CRM `cache.db` (`wh_customer_tier`) both confirmed matching warehouse distribution

## Bug caught during execution (not shipped)

First implementation: `EXISTS (SELECT 1 FROM us_channel_customers uc WHERE uc.customer_key = customer_key)` — unqualified `customer_key` self-correlated inside the subquery's own scope instead of the outer row, making the condition true for every customer (CROSSBORDER 7429/7601, RETAIL→0). Caught immediately after the first full-refresh by inspecting the distribution — exactly the failure mode Phase 2's hard gate was designed for, caught even before formally running the gate check. Fixed by qualifying `uc.customer_key = joined_data.customer_key`. `code-reviewer` subagent independently caught the same unqualified-reference mistake reproduced in the staff-guide's illustrative SQL snippet (mục 9) — fixed.

## Plan doc inaccuracy corrected

Plan's Key Constraints originally cited `wh_customer_base.customer_type` (`cache_schema.sql:136`) as the CRM sync target. Verified against live `cache.db`: `wh_customer_base` has no `customer_type` column — it actually lives in `wh_customer_tier`. Didn't block anything (reverse-ETL syncs both tables correctly regardless), corrected in `plan.md` Key Constraints + Acceptance Criteria.

## Docs updated

- `transformation/models/marts/core/dim_customers.sql` (code)
- `transformation/models/marts/schema.yml` (column description)
- `docs/context/order-customer-classification-staff-guide.md` (mục 8.2/9/12 — full logic + verified numbers)
- `docs/context/customer-segmentation.md` (summary note, points to staff-guide for detail)
- `plans/260708-1628-crossborder-channel-detection/{plan.md,phase-01,phase-02,phase-03}.md` (status + checkboxes + completion notes)

## Unresolved questions

None — all Unresolved Questions in the plan were closed during validation; no new ones surfaced during implementation.

## Next step

Awaiting user decision on whether to commit (see conversation) — not yet committed to git.
