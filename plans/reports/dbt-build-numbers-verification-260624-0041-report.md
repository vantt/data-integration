# dbt Build — Numbers Verification Report

**Date:** 2026-06-24 · **Goal:** verify the transformation fixes produce correct numbers in the live warehouse/serving DB.

## How it was verified
- `transformation/` is **volume-mounted** into `data_platform`; the container already runs our corrected models (`std_payments.sql` etc. confirmed present in-container).
- Manual `dbt build --select +tag:mart` collided with the warehouse single-writer lock: **Dagster is continuously building** `dbt build --select fqn:*` (scheduled), already using our mounted code. So the fixes are being built by Dagster on every scheduled run.
- Verified by querying the **serving DB** (`olap.duckdb`, read-only) + catching warehouse read windows.

## Results

| Fix | Status | Evidence |
|---|---|---|
| `gross_profit`/`gross_margin_pct` NULL when `has_cogs=FALSE` (M1) | ✅ **LIVE & correct** | `fact_order_economics`: total 15532, gross_profit NULL = 1615, has_cogs = 13917 → NULL count == no-cogs count exactly |
| `scope_retail` / `scope_b2b` B2B exclusion (H2) | ✅ **healthy** | `fact_orders`: retail 7833 / b2b 3429 / neither 4270 — mutually exclusive, no double-count |
| `dim_customers_base` Unknown sentinel uniqueness (new test) | ✅ **passes** | exactly **1** Unknown sentinel row |
| `date_key` explicit ICT cast (C1) | ✅ **sane** | range 20210520 → 20260623 (ICT-aligned, no misdate artifacts) |
| Mart health | ✅ | fact_orders 15532 · dim_customers 7571 · fact_order_economics 15532 · fact_sales 27569 |
| `std_payments` CASH→seed (C2) + `payment_behavior` | ⚠️ **code-correct but INERT** | seed has `COD→cod`, filter is `='cod'` (match ✓), BUT `std_payments` & `stg_sapo_v2_payments` = **0 rows**. payment_behavior is uniformly PREPAID(5970)/NULL(1601) because **no payment data is ingested**, not the old hardcode. Full-refresh will NOT change this until payment ingestion is restored. |
| `int_customer_metrics` watermark (H3) | ✅ structural | parse-clean; correct watermark semantics; not visible in aggregate snapshot |

## Key finding — payment pipeline is empty
`stg_sapo_v2_payments` = 0 rows → `std_payments` = 0 rows → every customer falls to the `COALESCE(..., 'PAYMENT_PREPAID')` default. This is a **pre-existing upstream data-availability gap** (consistent with the known "fact_payments empty" issue), NOT a regression from our fix. The C2 audit finding ("hardcoded CASH corrupts payment_behavior") overstated impact — with zero payment rows the hardcode never mattered. **The CASH fix is correct and will work the moment payment ingestion lands.**

## Side fix applied this session
- **Compose `CRM_REFRESH_TOKEN` breakage** (introduced by the hardening commit): `crm` service has no `env_file:` and interpolates secrets from root `.env`; our `${CRM_REFRESH_TOKEN:?...}` failed because root `.env` lacked the var. Fixed by adding `CRM_REFRESH_TOKEN` to root `.env` (gitignored, copied from `.env.docker`). `docker compose config -q` now passes.
- ⚠️ Token value is still the weak default `change-me-crm-refresh` in both files — **rotate to a strong value in `.env` AND `.env.docker`**.

## Recommendations / next steps
1. **payment_behavior**: don't full-refresh for it — fix **payment ingestion** first (`stg_sapo_v2_payments` empty). Separate investigation: is the Sapo payment entity being ingested at all?
2. To get a definitive **dbt test pass/fail** (371 tests + new sentinel test), check the **Dagster UI** run status, or pause schedules for one clean manual `dbt build` (warehouse is otherwise continuously locked).
3. Rotate `CRM_REFRESH_TOKEN` (currently weak default).
4. After the next Dagster build + `build_serving_db`, the serving numbers above already reflect the corrected logic (gross_profit confirmed) — no extra deploy needed for those.

## Unresolved questions
1. Is Sapo payment data supposed to be ingested? `stg_sapo_v2_payments` empty — either payments aren't pulled, or the source/staging filter drops them. Needs an ingestion-side check.
2. dbt full test-suite pass/fail not captured (Dagster holds the lock continuously) — confirm via Dagster UI.
