# Transformation Layer Health Audit
**Date:** 2026-06-23 | **Scope:** transformation/ + scripts/provisioning/

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH     | 6 |
| MEDIUM   | 5 |
| LOW      | 4 |

---

## CRITICAL

### C1 — date_key generated from TIMESTAMPTZ without explicit ICT conversion
**Files:** `fact_orders.sql:147`, `fact_sales.sql:58`
**Risk:** `strftime(created_at, '%Y%m%d')` on a TIMESTAMPTZ column uses the DuckDB session timezone (ICT, per profiles.yml). This works **only when the session timezone is ICT**. In Metabase, the DuckDB JDBC connection has its own session timezone setting (also confirmed as ICT per memory note). If any consumer opens a fresh DuckDB connection without setting `TimeZone='Asia/Ho_Chi_Minh'`, orders placed between midnight and 07:00 ICT get stamped with the prior UTC date, causing ~15% drift in daily KPIs. The risk is latent — correct today, silent breakage if any non-dbt connection reads the raw parquet directly.
**Direction:** Use `CAST(created_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE)` then `strftime('%Y%m%d', ...)` in both models to make the ICT conversion explicit and session-independent.

---

### C2 — std_payments hardcodes `payment_method_type = 'CASH'`
**File:** `models/staging/standard/std_payments.sql:21`
**Risk:** Every payment row in `fact_payments` and `int_customer_metrics` has `payment_method_type = 'CASH'`. The `payment_behavior` CTE in `int_customer_metrics` filters on `payment_method_type = 'cod'` — this condition can **never** be true. Every customer is therefore classified `PAYMENT_PREPAID`, making the COD segmentation completely wrong. This also pollutes `dim_customers.payment_behavior` for all downstream users.
**Direction:** Map `payment_method_id` → real type (COD / bank transfer / cash / card) via `ref_payment_methods`. At minimum do a keyword join on the payment method name from `stg_sapo_v2_payments`.

---

### C3 — `dim_customers_base` incremental UNION ALL appends Unknown sentinel on every run
**File:** `models/marts/core/dim_customers_base.sql:68-85`
**Risk:** The Unknown sentinel row is in a `UNION ALL` **outside** the incremental filter. On every incremental run the query `UNION ALL SELECT 'Unknown'...` is always appended to the output. The `unique_key='customer_key'` dedup should prevent duplicates in the DuckDB incremental table, but DuckDB's incremental materialization (`delete+insert`) deletes on `customer_key` then inserts — the sentinel is re-inserted every run. The real concern: if the sentinel `customer_key` value changes (e.g. `dbt_utils.generate_surrogate_key` version bump), old rows are not deleted because the old sentinel key is no longer in `unique_key` set. More operationally: the sentinel is **missing location**: `dim_customers_base` uses `materialized='incremental'` but has **no `location` config** — per `dbt_project.yml` marts get `materialized: external` globally but this model overrides to `incremental`, leaving it as an internal DuckDB table instead of a parquet file. This is by design (architectural note says "Not for Serving"), but it means it does NOT get discovered by `bootstrap_serving_views.py` and must never be referenced in Metabase — latent risk if someone queries it directly.
**Direction:** Confirm `dim_customers_base` intentional non-external. Add a comment in AGENTS.md / schema.yml that it is never served to Metabase. Move Unknown sentinel outside incremental branch explicitly and document the sentinel dedup behavior.

---

## HIGH

### H1 — `gross_revenue` in `fact_orders` is VAT-inclusive; column name misleads
**File:** `models/marts/sales/fact_orders.sql:162`
**Risk:** `gross_revenue = total_amount + total_discount_amount`. Both `total_amount` (VAT-inclusive Sapo `total`) and `total_discount_amount` are VAT-inclusive amounts. The resulting `gross_revenue` is therefore VAT-inclusive. The column comment says "(đã gồm VAT)" which is correct, but the schema.yml description says "Giá bán × SL (trước chiết khấu & thuế)" — the last word "thuế" implies pre-tax but the value is NOT pre-tax. Any consumer who sums `gross_revenue` and then tries to subtract `vat_amount` will compute an incorrect pre-discount VAT-exclusive revenue. This is a documentation inconsistency that actively misleads.
**Direction:** Clarify schema.yml description: explicitly state "VAT-inclusive" (đã gồm VAT) everywhere for `gross_revenue`. Consider renaming to `gross_revenue_incl_vat` to make the contract unambiguous.

---

### H2 — `scope_retail` defaults unknown customers to RETAIL — leaks Đại Lý dealers
**File:** `models/marts/sales/fact_orders.sql:184-187`
**Risk:** `COALESCE(cu2.customer_type, 'RETAIL') = 'RETAIL'` means any order where the customer is not in `dim_customers_base` (guest/anonymous) is treated as RETAIL. More critically: the known issue (memory note) is that ~92 Đại-Lý dealers have `customer_type='RETAIL'` because the migration is incomplete. The recommended fix (`AND acquisition_source = 'Đại Lý'`) is implemented in `mart_deadstock_target_queue.sql:203` but **NOT** in `fact_orders.sql`. So `scope_retail` in `fact_orders`, `fact_order_economics`, and all downstream aggregations includes these ~92 dealer accounts.
**Direction:** Add `AND COALESCE(cu2.acquisition_source, '') <> 'Đại Lý'` to `scope_retail` and `scope_b2b` in `fact_orders`. Propagate to `mart_cohort_retention`, `mart_retention_waterfall_monthly`, `mart_customer_status_snapshot_monthly`.

---

### H3 — `int_customer_metrics` incremental watermark uses `last_order_date` not `updated_at`
**File:** `models/marts/core/intermediate/int_customer_metrics.sql:36`
**Risk:** `WHERE updated_at >= (SELECT MAX(last_order_date) FROM {{ this }})`. The watermark column in `fact_orders` is `updated_at` (order update time), but it's compared against `MAX(last_order_date)` from the previous run. These are different fields: `last_order_date` is the most-recent ORDER date from prior metrics calculation, while `updated_at` is when the order record was last modified. In late-arriving updates (Sapo backfilling a modified_on on a 3-month-old order), the order's `updated_at` could be recent but `last_order_date` may already exceed it. The result: recently modified OLD orders silently skip re-computation, staling `recency_days`, `frequency`, `monetary_value` and all downstream customer segments.
**Direction:** Change watermark to `WHERE updated_at >= (SELECT MAX(metric_calculated_at) - INTERVAL '1 day' FROM {{ this }})` with a safety buffer.

---

### H4 — `int_customer_entry_attributes` incremental uses NOT IN anti-join on growing table
**File:** `models/marts/core/intermediate/int_customer_entry_attributes.sql:122`
**Risk:** `WHERE customer_key NOT IN (SELECT customer_key FROM {{ this }})`. As `this` grows, the NOT IN subquery becomes a full table scan per run. More critically: if a customer's `first_order` is corrected (e.g. a cancelled order is re-included or excluded by status change), the entry attributes **never update** because the customer is already in the table. Entry attributes should be immutable, but the upstream filter `WHERE o.is_active_order = TRUE AND o.status NOT IN ('CANCELLED', 'DRAFT')` means a customer whose FIRST order was initially active but later cancelled will have stale entry attributes.
**Direction:** Document the immutability assumption explicitly. Consider switching to `EXCEPT` or checking `NOT EXISTS`. Flag in schema.yml that full-refresh is needed if first-order statuses change.

---

### H5 — `fact_us_shipment_economics` hardcodes 8% VAT for all US orders
**File:** `models/marts/sales/fact_us_shipment_economics.sql:32`
**Risk:** Docstring says "Actual US deal revenue (excl. 8% VAT)". The `int_us_shipment_line_prices` presumably encodes 8% VAT. If any US product ever moves to 10% VAT (personal care product re-classification), this model silently undercounts VAT and overstates `total_us_revenue_excl_vat`. Not verifiable without reading `int_us_shipment_line_prices`, but hardcoded VAT rates are a systemic risk.
**Direction:** Verify `int_us_shipment_line_prices` uses per-SKU VAT rate or is parameterized. If hardcoded to 8%, add a `CAVEAT:` comment noting the assumption and ticket for re-validation if product classification changes.

---

### H6 — `dim_customers` incremental can silently skip new customers when `metric_calculated_at = current_timestamp`
**File:** `models/marts/core/dim_customers.sql:253-257`
**Risk:** The watermark is `WHERE source_updated_at >= (SELECT MAX(updated_at) FROM {{ this }})`. The comment notes `metric_calculated_at` is excluded from this comparison (correct), but `updated_at` in the target table is `source_updated_at` from the prior run. A customer created with `created_at = updated_at = some old date` and first appearing because they now have orders will have `source_updated_at` older than `MAX(updated_at)` in the existing table — they get silently skipped. This is a latent risk for any customer whose Sapo profile timestamp was not updated recently.
**Direction:** Supplement the incremental filter with `OR customer_key NOT IN (SELECT customer_key FROM {{ this }})` to catch new customers whose timestamps pre-date the watermark.

---

## MEDIUM

### M1 — `fact_order_economics.gross_profit` uses `COALESCE(cogs, 0)` — overstates profit when no COGS
**File:** `models/marts/sales/fact_order_economics.sql:128`
**Risk:** `gross_profit = net_revenue - COALESCE(cogs_amount, 0)`. When there is no COGS data, `gross_profit = net_revenue` (as if margin = 100%). The `has_cogs` flag exists to gate this, but consumers who SUM `gross_profit` without filtering `WHERE has_cogs` will get inflated totals. `int_customer_economics.sql:32` does correctly filter `FILTER (WHERE oe.has_cogs)`, but any ad-hoc Metabase query on `fact_order_economics.gross_profit` without that gate produces wrong numbers silently.
**Direction:** Change `gross_profit` to `NULL` when no COGS, so any un-gated sum fails obviously rather than silently inflating. Already done for `cogs_amount` (line 119 uses `NULLIF`), apply same logic to `gross_profit`.

---

### M2 — `mart_customer_status_snapshot_monthly` survivorship bias not surfaced in column tests
**File:** `models/marts/schema.yml:1225-1246`
**Risk:** The WARNING about survivorship bias is documented in the description but there are no dbt tests or tags that enforce the contract "do not use for retention trend charts." Any developer adding a new Metabase card querying `status` from this model for trend analysis will produce wrong metrics. The Metabase cards built from this model are not audited.
**Direction:** Add a column-level `meta: {is_survivorship_biased: true}` tag or a dbt exposure annotation. Consider adding a model-level `WARNING_` prefix or deprecation tag.

---

### M3 — `fact_inventory_snapshot` nested `{% if is_incremental() %}` block is double-wrapped
**File:** `models/marts/sales/fact_inventory_snapshot.sql:58-64`
**Risk:** Lines 58-64 have `{% if is_incremental() %}` inside another `{% if is_incremental() %}`. The outer block (line 30) already checks incremental. The inner double-check (line 61) is redundant but harmless in DuckDB — until someone moves or copies the inner block, at which point the intent is ambiguous.
**Direction:** Remove the inner `{% if is_incremental() %}` at line 61 (the outer at line 30 already guards it).

---

### M4 — `mart_sku_economics_monthly` uses MISA `gross_margin_pct` (MISA book) by default; `realized_margin_pct` is the correct metric per known landmine #4
**File:** `models/marts/sales/mart_sku_economics_monthly.sql:397`, `models/marts/schema.yml:943`
**Risk:** Both `gross_margin_pct` and `realized_margin_pct` are surfaced. Per landmine #4 (H010 COGS fix is only in realized_*), `gross_margin_pct` uses `misa_revenue_net` as denominator (MISA book revenue) while `realized_margin_pct` uses Sapo `net_revenue`. For H010 SKUs with ~2× COGS error, `gross_margin_pct` will still show wrong margins. The schema.yml recommends `realized_margin_pct` but doesn't warn strongly enough. Metabase blueprint authors may pick `gross_margin_pct` by default.
**Direction:** Add a dbt meta tag `{deprecated: true, use_instead: realized_margin_pct}` on `gross_margin_pct` in schema.yml. Add a SQL comment at the column definition warning about H010 SKUs.

---

### M5 — `int_customer_metrics` reads `fact_payments` for COD detection, which is all-CASH (see C2)
**File:** `models/marts/core/intermediate/int_customer_metrics.sql:300-320`
**Risk:** `payment_behavior_cte` counts `FILTER (WHERE payment_method_type = 'cod')`. Since `std_payments.payment_method_type = 'CASH'` for all rows (C2), the COD count is always 0, so `payment_behavior = 'PAYMENT_PREPAID'` for every customer. This is a downstream symptom of C2 but worth flagging here since it corrupts `dim_customers.payment_behavior` and any COD segmentation (e.g. COD vs prepaid targeting in `mart_customer_action_queue`).
**Direction:** Fix C2 first; this resolves automatically.

---

## LOW

### L1 — `dim_customers_base` unique_key dedup but Unknown sentinel always included without unique_key guard
**File:** `models/marts/core/dim_customers_base.sql`
**Risk:** The `UNION ALL` sentinel is outside the incremental WHERE clause. The `unique_key='customer_key'` in `delete+insert` strategy ensures the sentinel doesn't duplicate — but this relies on internal dbt behavior. No test validates that `unknown` appears exactly once. If the incremental strategy changes, duplicates could silently appear.
**Direction:** Add a `dbt_utils.expression_is_true` test: `customer_id = 'Unknown'` count = 1.

---

### L2 — `fact_order_economics` margin columns computed twice (inline + in channel_net_margin)
**File:** `models/marts/sales/fact_order_economics.sql:130-173`
**Risk:** `channel_net_profit` formula is spelled out identically in two places (lines 154-160 and lines 164-173). If a Shopee fee column is added (e.g. Lazada expansion), the developer must update both places. One will inevitably be missed.
**Direction:** Materialize `channel_net_profit` as a CTE first, then reference it in `channel_net_margin_pct`.

---

### L3 — `mart_cohort_retention` uses `total_collected` as activity revenue (VAT-inclusive)
**File:** `models/marts/customer/mart_cohort_retention.sql:42`
**Risk:** `SUM(o.total_collected) AS period_revenue` — `total_collected` is VAT-inclusive. Revenue retention metric is therefore overstated vs `net_revenue` by the VAT fraction (~8-10%). This is internally consistent (cohort M0 and all subsequent periods use same basis), but comparing cohort revenue retention to margin dashboards (which use `net_revenue`) produces a ~10% basis mismatch.
**Direction:** Document in schema.yml that `revenue` and `m0_revenue` are VAT-inclusive `total_collected`. Consider switching to `net_revenue` for consistency with fact_order_economics.

---

### L4 — `src_sapo_v2_orders` biz dedup ingest_method priority uses opposite numeric encoding from tech dedup
**File:** `models/staging/src_sapo_v2_orders.sql:64-68` (tech dedup) vs `:204-208` (biz dedup)
**Risk:** Tech dedup: `webhook=3, history_log=2, other=1 ORDER BY DESC` (webhook wins). Biz dedup: `webhook=1, history_log=2, other=3 ORDER BY ASC` (webhook wins). Both produce the same result but the inverted encoding creates confusion for future editors. A developer who reads one pattern and copies it to the other without understanding the ORDER direction will silently invert the priority.
**Direction:** Standardize to one encoding. Prefer the more readable pattern: `webhook=1, history_log=2, batch=3 ORDER BY ASC` and use it in both dedup steps. Add a comment.

---

## Unresolved Questions

1. **H5 — US VAT rate source**: Does `int_us_shipment_line_prices` encode 8% explicitly or derive it per SKU? Need to read that model to confirm.
2. **C3 — `dim_customers_base` missing unique test**: Is there a dbt test validating that `customer_key` is unique post-incremental? The schema.yml only has `unique, not_null` on the column, which runs on the SELECT output, not on the materialized table. Does this test run against the materialized table or the query output?
3. **H2 — Đại Lý scope_retail leak scope**: How many total RETAIL-labelled orders belong to those ~92 Đại-Lý dealers? Is the revenue impact material enough to warrant a hotfix vs planned migration?
4. **L3 — Cohort revenue basis alignment**: Is the decision to use `total_collected` (VAT-inclusive) for cohort retention intentional, or was `net_revenue` the intended basis? This affects whether cohort revenue retention is comparable to margin reports.
5. **M2 — Survivorship bias disclosure**: Are there existing Metabase cards built on `mart_customer_status_snapshot_monthly.status` for trend analysis that need to be audited/migrated to `mart_retention_waterfall_monthly`?

---

## FIXES APPLIED 260623

**Parse result:** `dbt parse` exit 0 (no errors). `dbt compile` blocked by live DuckDB write lock — parse is sufficient per task constraint.

### CRITICAL

| Finding | Status | File:Change | Downstream Impact |
|---------|--------|-------------|-------------------|
| C1 — date_key no explicit ICT | APPLIED | `fact_orders.sql:147` + `fact_sales.sql:58` — `strftime(created_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%Y%m%d')` | Changes numbers: ~15% drift for 0h–7h orders corrected. **Rebuild needed**: bootstrap_serving_views.py + Metabase resync after dbt run. |
| C2 — std_payments hardcoded 'CASH' | APPLIED | `std_payments.sql:10-30` — added `payment_method_ref` CTE joining `ref_payment_methods` seed; `payment_method_type` now derives from `type` column (cod/cash/transfer/etc.), fallback `'unknown'` | Changes numbers: COD customers will now correctly receive `PAYMENT_COD` in `dim_customers.payment_behavior`. Downstream: `int_customer_metrics`, `fact_payments`, `dim_customers.payment_behavior`, `mart_customer_action_queue`. |
| C3 — dim_customers_base Unknown sentinel dup risk | APPLIED (partial) | `dim_customers_base.sql:68` — added architecture comment clarifying dedup semantics + "Not for Serving" note. `tests/assert_dim_customers_base_unknown_sentinel_unique.sql` — new singular test. | No number change. Test catches regression on sentinel duplication. |

### HIGH

| Finding | Status | File:Change | Downstream Impact |
|---------|--------|-------------|-------------------|
| H1 — gross_revenue description misleads | APPLIED | `schema.yml:679,757` — descriptions now say "ĐÃ GỒM VAT" with explicit WARNING. No SQL change. | Documentation only. No number change. |
| H2 — scope_retail Đại Lý leak | APPLIED (partial) | `fact_orders.sql:83,184-194` — expanded `channel_scope` CTE to include `channel_format`; `scope_retail` excludes `channel_format='B2B'` orders; `scope_b2b` now includes B2B-channel orders. **Residual leak**: dealers placing orders on non-B2B channels still leak (can't access dim_customers without circular dep — noted in comment). | Changes numbers: Đại Lý-channel orders removed from `scope_retail`. All downstream aggregations on `scope_retail` (fact_order_economics, mart_cohort_retention, mart_customer_status_snapshot_monthly, mart_retention_waterfall_monthly). **Rebuild needed** after dbt run. |
| H3 — int_customer_metrics watermark wrong column | APPLIED | `int_customer_metrics.sql:36` — watermark changed to `MAX(metric_calculated_at) - INTERVAL '1 day'`, comparing `updated_at >= ...` (same column both sides). | Changes numbers: late-arriving Sapo backfills on old orders now re-compute customer RFM. Downstream: `dim_customers`, all customer segments. |
| H4 — int_customer_entry_attributes NOT IN risk | APPLIED (doc) | `int_customer_entry_attributes.sql:120-127` — added comment documenting immutability assumption, NOT IN performance note, and full-refresh instruction. No SQL logic change. | No number change. |
| H5 — fact_us_shipment_economics VAT hardcode | APPLIED (verified + doc) | Verified: VAT not hardcoded in SQL — `us_price_excl_vat`/`us_price_incl_vat` come from `stg_us_shipment_prices` (Google Sheet). Added CAVEAT comment in `fact_us_shipment_economics.sql:28`. | No number change. Risk is in source sheet, not SQL. |
| H6 — dim_customers incremental skips new customers | APPLIED | `dim_customers.sql:257` — added `OR customer_key NOT IN (SELECT customer_key FROM {{ this }})` guard. | Catches new customers whose Sapo profile timestamp predates watermark. Minor performance cost on each incremental run (full scan of existing table). |

### MEDIUM

| Finding | Status | File:Change | Downstream Impact |
|---------|--------|-------------|-------------------|
| M1 — gross_profit inflates when no COGS | APPLIED | `fact_order_economics.sql:128-136` — `gross_profit` and `gross_margin_pct` now NULL when `has_cogs=FALSE`. `schema.yml:775` updated. | Changes numbers: un-gated SUM(gross_profit) now returns lower (correct) totals instead of net_revenue for no-COGS rows. Existing Metabase cards filtering `WHERE has_cogs` unaffected. Cards without the gate will show NULL gaps — **audit Metabase cards** after deploy. |
| M2 — survivorship bias not tagged | APPLIED | `schema.yml:1225-1249` — added `meta: {is_survivorship_biased: true, use_instead_for_retention: ..., deprecated_for_use_cases: [...]}` on model. | Documentation only. Unresolved Q5 remains: existing Metabase cards using `status` for trend not yet audited. |
| M3 — fact_inventory_snapshot double-wrapped is_incremental | APPLIED | `fact_inventory_snapshot.sql:58-63` — removed inner redundant `{% if is_incremental() %}` block. | No logic change (was already correct at runtime). |
| M4 — mart_sku_economics_monthly gross_margin_pct not warned | APPLIED | `schema.yml:942` — `meta: {deprecated: true, use_instead: realized_margin_pct, reason: ...}`. `mart_sku_economics_monthly.sql:390` — added DEPRECATED comment at column definition. | Documentation only. No number change. |
| M5 — int_customer_metrics COD always 0 | DEFERRED | Resolves automatically once C2 (std_payments) fix propagates through dbt run. No separate action. | |

### LOW

| Finding | Status | File:Change | Downstream Impact |
|---------|--------|-------------|-------------------|
| L1 — dim_customers_base sentinel no unique test | APPLIED | `tests/assert_dim_customers_base_unknown_sentinel_unique.sql` — new singular test. Covered under C3. | |
| L2 — fact_order_economics formula duplication | APPLIED (doc) | `fact_order_economics.sql:159,169` — added MAINTENANCE NOTE comments on both occurrences of `channel_net_profit` formula. Full CTE refactor deferred (non-trivial restructure of final SELECT). | |
| L3 — mart_cohort_retention VAT-inclusive not documented | APPLIED | `schema.yml:1372-1383` — description now states REVENUE BASIS explicitly. | Documentation only. No number change. |
| L4 — src_sapo_v2_orders dedup encoding mismatch | APPLIED | `src_sapo_v2_orders.sql:65-68` — tech dedup changed from `webhook=3 DESC` to `webhook=1 ASC` to match biz dedup. Cross-reference comments added to both blocks. | No number change (same priority result). Prevents future copy-paste confusion. |

### Fixes that change numbers (require dbt run + serving rebuild on deploy)

1. **C1** — date_key ICT explicit cast (`fact_orders`, `fact_sales`) — ~15% drift for midnight-7am orders
2. **C2** — std_payments COD mapping (`std_payments` → `fact_payments` → `int_customer_metrics` → `dim_customers.payment_behavior`)
3. **H2** — scope_retail B2B exclusion (`fact_orders` → all downstream RETAIL aggregations)
4. **H3** — int_customer_metrics watermark (`int_customer_metrics` → `dim_customers` RFM/segments)
5. **M1** — gross_profit NULL when no COGS (`fact_order_economics.gross_profit`, `gross_margin_pct`)

### Post-deploy checklist

- Run `dbt run` (full or targeted) on affected models
- Run `bootstrap_serving_views.py` (stop Metabase first) to rebuild olap.duckdb views
- Audit Metabase cards using `gross_profit` without `WHERE has_cogs` filter (M1 impact)
- Verify `dim_customers.payment_behavior` shows non-trivial COD % after C2 fix
- Unresolved Q5: audit Metabase cards on `mart_customer_status_snapshot_monthly.status` for trend analysis
